"""Custom middleware classes for Finlo core functionalities.

This module provides middleware for:
- Setting the active company for the logged-in user.
- Managing user-specific time zones.
- Handling custom Finlo exceptions.
"""

# Standard library imports
import logging

# Third-party imports (Django)
from django.utils.deprecation import MiddlewareMixin

from finlo.menu.sub_section_menu import sub_section_menu as menu_registry
from finlo.shortcuts import redirect, render
from finlo.urls import Resolver404, resolve

# First party imports (Finlo)
from finlo.utils import timezone
from finlo.web import HttpNotFound, HttpResponse, HttpResponseNotAllowed

# Local imports
from .models import Company

logger = logging.getLogger(__name__)


class ActiveCompanyMiddleware:
    """Middleware to attach the active company to the request object."""

    def __init__(self, get_response):
        """Initialize middleware with the given get_response function."""
        self.get_response = get_response

    def __call__(self, request):
        """Set the active company for the authenticated user."""
        request.active_company = None
        request.active_theme = None
        if request.user.is_authenticated:
            company_id = request.session.get("active_company_id")
            user_company = getattr(request.user, "company", None)
            user_company_id = getattr(request.user, "company_id", None)
            if company_id:
                if user_company and user_company_id == company_id:
                    request.active_company = user_company
                else:
                    try:
                        request.active_company = Company.objects.get(id=company_id)
                    except Company.DoesNotExist:  # Fixed pylint complaint
                        request.active_company = user_company
            else:
                request.active_company = user_company

            if request.active_company:
                try:
                    from finlo.contrib.theme.models import CompanyTheme
                    request.active_theme = CompanyTheme.get_theme_for_company(request.active_company)
                except Exception:
                    pass
            if request.active_theme is None:
                try:
                    from finlo.contrib.theme.models import CompanyTheme
                    request.active_theme = CompanyTheme.get_default_theme()
                except Exception:
                    pass
        return self.get_response(request)


class TimezoneMiddleware:
    """Middleware to activate timezone based on user preferences."""

    def __init__(self, get_response):
        """Initialize middleware with the given get_response function."""
        self.get_response = get_response

    def __call__(self, request):
        """Activate or deactivate timezone depending on authentication."""
        if request.user.is_authenticated:
            tzname = getattr(request.user, "time_zone", "UTC") or "UTC"
            timezone.activate(tzname)
        else:
            timezone.deactivate()

        return self.get_response(request)


class FinloExceptionMiddleware:
    """Middleware to catch and handle Finlo-specific exceptions."""

    def __init__(self, get_response):
        """Initialize middleware with the given get_response function."""
        self.get_response = get_response

    def __call__(self, request):
        """Process requests and catch HttpNotFound exceptions."""
        try:
            return self.get_response(request)
        except HttpNotFound as exc:
            return exc.as_response(request)

    def process_exception(self, request, exception):
        """Handle HttpNotFound exceptions raised outside __call__."""
        if isinstance(exception, HttpNotFound):
            return exception.as_response(request)
        return None


class Finlo405Middleware:
    """Middleware to show a custom 405 page when DEBUG is False."""

    def __init__(self, get_response):
        """Store the next middleware or view in the chain."""
        self.get_response = get_response

    def __call__(self, request):
        """Return the response or render 405.html if method not allowed."""
        response = self.get_response(request)

        if isinstance(response, HttpResponseNotAllowed):
            """Render a custom 405 error page."""
            return render(request, "405.html", status=405)

        return response


class SVGSecurityMiddleware:
    """Middleware to add security headers for SVG files."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.endswith(".svg") and response.status_code == 200:
            response["Content-Security-Policy"] = (
                "default-src 'none'; style-src 'unsafe-inline';"
            )
            response["X-Content-Type-Options"] = "nosniff"
        return response


class HTMXRedirectMiddleware:
    """
    Middleware to handle HTMX redirects.
    Converts redirect responses for HTMX requests into HX-Redirect so HTMX performs
    a full window navigation instead of silently following redirects in the background.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        is_htmx = bool(
            request.headers.get("HX-Request") == "true"
            or request.META.get("HTTP_HX_REQUEST") == "true"
            or request.headers.get("HX-Request")
            or request.META.get("HTTP_HX_REQUEST")
        )

        if not is_htmx:
            return response

        # If this is a redirect response (301, 302, 303, 307, 308)
        if response.status_code in (301, 302, 303, 307, 308):
            # If the view already set HX-Redirect or HX-Refresh or HX-Location, preserve it
            if (
                response.has_header("HX-Redirect")
                or response.has_header("HX-Refresh")
                or response.has_header("HX-Location")
            ):
                return response

            redirect_target = (
                response.headers.get("Location")
                or getattr(response, "url", None)
            )
            if not redirect_target:
                return response

            from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

            # Check if this redirect is to the login page
            if "login" in str(redirect_target):
                # Get the current page URL from HX-Current-URL header or Referer
                current_url = (
                    request.headers.get("HX-Current-URL")
                    or request.headers.get("Referer")
                    or request.path
                )

                # Extract the path AND query from current_url so filters/section aren't lost
                current_parsed = urlparse(current_url)
                current_rel = current_parsed.path + (
                    f"?{current_parsed.query}" if current_parsed.query else ""
                )
                if not current_rel or current_rel == "/":
                    from django.conf import settings
                    current_rel = getattr(
                        settings, "DEFAULT_HOME_REDIRECT", "/dashboard/?section=home"
                    )

                parsed = urlparse(redirect_target)
                query_params = parse_qs(parsed.query)
                query_params["next"] = [current_rel]
                new_query = urlencode(query_params, doseq=True)

                redirect_target = urlunparse(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        parsed.path,
                        parsed.params,
                        new_query,
                        parsed.fragment,
                    )
                )

            # Convert to HX-Redirect
            new_response = HttpResponse(status=200)
            new_response["HX-Redirect"] = redirect_target
            return new_response

        return response


_section_path_cache = {}


def get_section_from_path(path):
    """Extract section by matching path with menu_registry URLs or app_label."""
    if path in _section_path_cache:
        return _section_path_cache[path]

    try:
        # Special case: root path mapped to home view
        try:
            resolved_root = resolve(path)
            if getattr(resolved_root, "url_name", None) == "home_view":
                _section_path_cache[path] = "home"
                return "home"
        except Resolver404:
            pass

        # First, try to match by URL
        for menu_cls in menu_registry:
            menu_url = str(getattr(menu_cls, "url", ""))
            if menu_url and path.startswith(menu_url):
                section = getattr(menu_cls, "section", None)
                if section:
                    _section_path_cache[path] = section
                    return section

        # Match by app_label
        try:
            resolved = resolve(path)
            if hasattr(resolved, "app_name") and resolved.app_name:
                for menu_cls in menu_registry:
                    if hasattr(menu_cls, "app_label"):
                        cls_app_label = getattr(menu_cls, "app_label", None)
                        if cls_app_label == resolved.app_name:
                            section = getattr(menu_cls, "section", None)
                            if section:
                                _section_path_cache[path] = section
                                return section
        except Resolver404:
            pass

    except Exception as e:
        logger.warning("Error in get_section_from_path: %s", e)

    _section_path_cache[path] = None
    return None


class EnsureSectionMiddleware(MiddlewareMixin):
    """Middleware to ensure 'section' parameter is present and valid in URLs."""

    def process_request(self, request):
        """Check and enforce 'section' parameter in GET requests."""
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        # Skip for static files, admin, root (root redirects directly to DEFAULT_HOME_REDIRECT)
        if (
            request.path == "/"
            or request.path.startswith("/static/")
            or request.path.startswith("/admin/")
            or request.path.startswith("/api/")
            or request.path.startswith("/health/")
        ):
            return None

        # Skip all POST requests (API endpoints, form submissions, etc.)
        if request.method == "POST":
            return None

        # Check if this is an HTMX request
        is_htmx = bool(
            request.headers.get("HX-Request") == "true"
            or request.META.get("HTTP_HX_REQUEST") == "true"
            or request.headers.get("HX-Request")
            or request.META.get("HTTP_HX_REQUEST")
        )

        # Check if this is an AJAX/API request
        is_ajax = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.content_type == "application/json"
            or "application/json" in request.headers.get("Accept", "")
        )

        # If it's HTMX request or AJAX request, skip all section validation/modification
        if is_htmx or is_ajax:
            return None

        # Get current section value
        current_section = request.GET.get("section", "").strip()

        # If a section is already present in the request, do not modify it.
        # Only when the section parameter is missing or empty, derive it from the path.
        if not current_section:
            section = get_section_from_path(request.path)

            # Only redirect if a valid section was found
            if section:
                query_params = request.GET.copy()
                query_params["section"] = section

                new_url = f"{request.path}?{query_params.urlencode()}"
                return redirect(new_url)

        return None

    def get_valid_sections(self):
        """Get all valid section values from menu_registry"""
        valid_sections = set()
        try:
            for menu_cls in menu_registry:
                section = getattr(menu_cls, "section", None)
                if section:
                    valid_sections.add(section)
        except Exception as e:
            logger.warning("Error getting valid sections: %s", e)

        return valid_sections

    def get_section_from_path(self, path):
        return get_section_from_path(path)
