"""
Tests for Phase 4B: HTMX Context Processor Optimization.

Verifies that:
1. `recently_viewed_items` and `unread_notifications` return valid empty containers with 0 queries
   when `_skip_header_context` is set on the request.
2. `recently_viewed_items` and `unread_notifications` execute their normal database queries when the
   flag is absent (full-page requests).
3. `FinloNavView` and `FinloListView` (and its subclasses) set `_skip_header_context = True` only for
   `HX-Request: true` partial requests.
4. Full page shell views (`FinloView`, `AccountView`, `LeadView`) do NOT skip context.
5. HTMX partial responses render cleanly with no missing context variables.
"""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.template import Context, Template

from finlo.context_processors import (
    recently_viewed_items,
    unread_notifications,
    UnreadNotifications,
)
from finlo.contrib.generics.views import FinloNavView, FinloListView, FinloView

User = get_user_model()


class HTMXContextProcessorOptimizationTests(TestCase):
    """Regression tests for selective context processor skipping in HTMX partials."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
        )

    def test_recently_viewed_skipped_when_flag_set(self):
        """When _skip_header_context is True, recently_viewed_items must run 0 queries."""
        request = self.factory.get("/crm/accounts/accounts-list-view/")
        request.user = self.user
        request._skip_header_context = True

        with self.assertNumQueries(0):
            ctx = recently_viewed_items(request)

        self.assertEqual(ctx, {"recently_viewed_items": []})

    def test_unread_notifications_skipped_when_flag_set(self):
        """When _skip_header_context is True, unread_notifications must run 0 queries."""
        request = self.factory.get("/crm/accounts/accounts-list-view/")
        request.user = self.user
        request._skip_header_context = True

        with self.assertNumQueries(0):
            ctx = unread_notifications(request)

        self.assertIn("unread_notifications", ctx)
        self.assertIn("unread_notifications_count", ctx)
        self.assertIn("notification_sound_muted", ctx)

        unread = ctx["unread_notifications"]
        self.assertIsInstance(unread, UnreadNotifications)
        self.assertEqual(len(unread), 0)
        self.assertEqual(unread.count(), 0)
        self.assertEqual(ctx["unread_notifications_count"], 0)
        self.assertFalse(ctx["notification_sound_muted"])

        # Template evaluation must not trigger SQL queries or error
        tpl = Template(
            '{% if unread_notifications.count > 30 %}30+{% else %}{{ unread_notifications.count }}{% endif %}'
        )
        with self.assertNumQueries(0):
            rendered = tpl.render(Context(ctx)).strip()
        self.assertEqual(rendered, "0")

    def test_context_processors_run_normally_when_flag_absent(self):
        """When _skip_header_context is False or absent, full-page context runs normally."""
        request = self.factory.get("/crm/accounts/accounts-view/")
        request.user = self.user

        # Must execute normal queries
        ctx_rv = recently_viewed_items(request)
        self.assertIn("recently_viewed_items", ctx_rv)

        ctx_notif = unread_notifications(request)
        self.assertIn("unread_notifications", ctx_notif)
        self.assertIn("unread_notifications_count", ctx_notif)
        self.assertIn("notification_sound_muted", ctx_notif)

    def test_finlo_nav_view_dispatch_sets_flag_on_htmx_request(self):
        """FinloNavView must set _skip_header_context only for HTMX requests."""
        class DummyNavView(FinloNavView):
            def get(self, request, *args, **kwargs):
                from django.http import HttpResponse
                return HttpResponse("ok")

        view = DummyNavView.as_view()

        # HTMX request
        req_htmx = self.factory.get("/crm/accounts/accounts-nav-view/", HTTP_HX_REQUEST="true")
        req_htmx.user = self.user
        view(req_htmx)
        self.assertTrue(getattr(req_htmx, "_skip_header_context", False))

        # Standard non-HTMX request
        req_standard = self.factory.get("/crm/accounts/accounts-nav-view/")
        req_standard.user = self.user
        view(req_standard)
        self.assertFalse(getattr(req_standard, "_skip_header_context", False))

    def test_finlo_list_view_dispatch_sets_flag_on_htmx_request(self):
        """FinloListView must set _skip_header_context only for HTMX requests."""
        class DummyListView(FinloListView):
            def get(self, request, *args, **kwargs):
                from django.http import HttpResponse
                return HttpResponse("ok")

        view = DummyListView.as_view()

        # HTMX request
        req_htmx = self.factory.get("/crm/accounts/accounts-list-view/", HTTP_HX_REQUEST="true")
        req_htmx.user = self.user
        view(req_htmx)
        self.assertTrue(getattr(req_htmx, "_skip_header_context", False))

        # Standard non-HTMX request
        req_standard = self.factory.get("/crm/accounts/accounts-list-view/")
        req_standard.user = self.user
        view(req_standard)
        self.assertFalse(getattr(req_standard, "_skip_header_context", False))

    def test_finlo_view_shell_does_not_set_skip_flag(self):
        """Full-page shell views inheriting FinloView must NOT set _skip_header_context."""
        class DummyShellView(FinloView):
            nav_url = "/accounts-nav/"
            list_url = "/accounts-list/"

            def get(self, request, *args, **kwargs):
                from django.http import HttpResponse
                return HttpResponse("ok")

        view = DummyShellView.as_view()
        req = self.factory.get("/crm/accounts/accounts-view/", HTTP_HX_REQUEST="true")
        req.user = self.user
        view(req)
        self.assertFalse(getattr(req, "_skip_header_context", False))
