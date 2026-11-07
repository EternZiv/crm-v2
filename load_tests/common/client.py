"""
Finlo CRM Client Adapter for Locust with HTMX & CSRF Support.
"""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger("finlo_loadtest")


class FinloClientMixin:
    """
    Mixin for Locust HttpUser to handle Finlo-specific HTMX partials,
    CSRF token propagation, and metrics labeling.
    """

    def get_csrf_token(self) -> str:
        """Extract current csrf token from cookies or session."""
        cookies = self.client.cookies.get_dict()
        return cookies.get("csrftoken", "")

    def get_full(
        self,
        url: str,
        name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ):
        """Perform a standard full-page GET request."""
        req_headers = headers.copy() if headers else {}
        req_headers.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        metric_name = name or f"[FULL] {url}"
        return self.client.get(url, headers=req_headers, name=metric_name, **kwargs)

    def get_htmx(
        self,
        url: str,
        target: str = "#mainContent",
        current_url: Optional[str] = None,
        name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ):
        """
        Perform an HTMX partial GET request with explicit Finlo HTMX headers.
        """
        req_headers = headers.copy() if headers else {}
        req_headers.update({
            "HX-Request": "true",
            "HX-Target": target,
            "HX-Current-URL": current_url or url,
            "Accept": "text/html, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        })

        csrf = self.get_csrf_token()
        if csrf:
            req_headers["X-CSRFToken"] = csrf

        metric_name = name or f"[HTMX] {url}"
        return self.client.get(url, headers=req_headers, name=metric_name, **kwargs)

    def post_full(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ):
        """Perform a standard form POST request with CSRF."""
        req_headers = headers.copy() if headers else {}
        csrf = self.get_csrf_token()
        if csrf:
            req_headers["X-CSRFToken"] = csrf

        post_data = data.copy() if data else {}
        if csrf and "csrfmiddlewaretoken" not in post_data:
            post_data["csrfmiddlewaretoken"] = csrf

        metric_name = name or f"[POST FULL] {url}"
        return self.client.post(url, data=post_data, headers=req_headers, name=metric_name, **kwargs)

    def post_htmx(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        target: str = "#mainContent",
        current_url: Optional[str] = None,
        name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ):
        """Perform an HTMX partial POST request with CSRF and HTMX headers."""
        req_headers = headers.copy() if headers else {}
        csrf = self.get_csrf_token()

        req_headers.update({
            "HX-Request": "true",
            "HX-Target": target,
            "HX-Current-URL": current_url or url,
            "Accept": "text/html, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        })

        if csrf:
            req_headers["X-CSRFToken"] = csrf

        post_data = data.copy() if data else {}
        if csrf and "csrfmiddlewaretoken" not in post_data:
            post_data["csrfmiddlewaretoken"] = csrf

        metric_name = name or f"[POST HTMX] {url}"
        return self.client.post(url, data=post_data, headers=req_headers, name=metric_name, **kwargs)
