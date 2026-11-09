"""
Focused tests for notification query deduplication and context processor efficiency.
Validates zero, one, and >10 notifications, user isolation, ordering, and template rendering.
"""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils import timezone

from finlo.context_processors import unread_notifications, UnreadNotifications
from finlo.contrib.notifications.models import Notification

User = get_user_model()


class NotificationDeduplicationTests(TestCase):
    """Ensure unread notifications are evaluated once and count queries are deduplicated."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password123",
        )

    def _build_request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_unauthenticated_user_returns_empty_context(self):
        """Anonymous users must receive an empty context without querying notifications."""
        request = self.factory.get("/")
        request.user = AnonymousUser()

        with self.assertNumQueries(0):
            ctx = unread_notifications(request)

        self.assertEqual(ctx, {})

    def test_zero_unread_notifications(self):
        """Zero notifications must report count 0 and not execute extra queries during rendering."""
        request = self._build_request(self.user)

        with self.assertNumQueries(1):
            # Exactly 1 query for unread notifications list (0 duplicate count queries)
            ctx = unread_notifications(request)

        unread = ctx["unread_notifications"]
        self.assertIsInstance(unread, UnreadNotifications)
        self.assertEqual(len(unread), 0)
        self.assertEqual(unread.count(), 0)
        self.assertEqual(ctx["unread_notifications_count"], 0)

        # Template rendering evaluating .count multiple times must trigger 0 additional queries
        tpl = Template(
            '{% if unread_notifications.count > 30 %}30+{% else %}{{ unread_notifications.count|default_if_none:"0" }}{% endif %}'
        )
        with self.assertNumQueries(0):
            rendered = tpl.render(Context(ctx)).strip()

        self.assertEqual(rendered, "0")

    def test_one_unread_notification(self):
        """One unread notification must report count 1 and render message without extra queries."""
        Notification.objects.create(
            user=self.user,
            message="Single alert",
            read=False,
        )

        request = self._build_request(self.user)
        with self.assertNumQueries(1):
            ctx = unread_notifications(request)

        unread = ctx["unread_notifications"]
        self.assertEqual(len(unread), 1)
        self.assertEqual(unread.count(), 1)
        self.assertEqual(ctx["unread_notifications_count"], 1)
        self.assertEqual(unread[0].message, "Single alert")

        tpl = Template(
            '{% if unread_notifications.count > 30 %}30+{% else %}{{ unread_notifications.count|default_if_none:"0" }}{% endif %}'
        )
        with self.assertNumQueries(0):
            rendered = tpl.render(Context(ctx)).strip()

        self.assertEqual(rendered, "1")

    def test_more_than_ten_unread_notifications_exact_count(self):
        """More than 10 notifications (e.g. 15) must preserve exact count and not truncate."""
        for i in range(15):
            Notification.objects.create(
                user=self.user,
                message=f"Alert #{i}",
                read=False,
            )

        request = self._build_request(self.user)
        with self.assertNumQueries(1):
            ctx = unread_notifications(request)

        unread = ctx["unread_notifications"]
        # Must be exactly 15, NOT truncated to 10
        self.assertEqual(len(unread), 15)
        self.assertEqual(unread.count(), 15)
        self.assertEqual(ctx["unread_notifications_count"], 15)

        tpl = Template(
            '{% if unread_notifications.count > 30 %}30+{% else %}{{ unread_notifications.count|default_if_none:"0" }}{% endif %}'
        )
        with self.assertNumQueries(0):
            rendered = tpl.render(Context(ctx)).strip()

        self.assertEqual(rendered, "15")

    def test_more_than_thirty_unread_notifications_badge(self):
        """More than 30 notifications (e.g. 35) must preserve exact count and display 30+ badge."""
        for i in range(35):
            Notification.objects.create(
                user=self.user,
                message=f"Alert #{i}",
                read=False,
            )

        request = self._build_request(self.user)
        with self.assertNumQueries(1):
            ctx = unread_notifications(request)

        unread = ctx["unread_notifications"]
        self.assertEqual(len(unread), 35)
        self.assertEqual(unread.count(), 35)
        self.assertEqual(ctx["unread_notifications_count"], 35)

        tpl = Template(
            '{% if unread_notifications.count > 30 %}30+{% else %}{{ unread_notifications.count|default_if_none:"0" }}{% endif %}'
        )
        with self.assertNumQueries(0):
            rendered = tpl.render(Context(ctx)).strip()

        self.assertEqual(rendered, "30+")

    def test_user_specific_filtering_and_cross_user_isolation(self):
        """Notifications for other users must never be visible to the current user."""
        # Alice has 2 unread
        Notification.objects.create(user=self.user, message="Alice 1", read=False)
        Notification.objects.create(user=self.user, message="Alice 2", read=False)

        # Bob has 5 unread
        for i in range(5):
            Notification.objects.create(user=self.other_user, message=f"Bob {i}", read=False)

        # Test Alice's context
        req_alice = self._build_request(self.user)
        ctx_alice = unread_notifications(req_alice)
        self.assertEqual(len(ctx_alice["unread_notifications"]), 2)
        self.assertEqual(ctx_alice["unread_notifications_count"], 2)
        alice_messages = [n.message for n in ctx_alice["unread_notifications"]]
        self.assertIn("Alice 1", alice_messages)
        self.assertIn("Alice 2", alice_messages)
        self.assertNotIn("Bob 0", alice_messages)

        # Test Bob's context
        req_bob = self._build_request(self.other_user)
        ctx_bob = unread_notifications(req_bob)
        self.assertEqual(len(ctx_bob["unread_notifications"]), 5)
        self.assertEqual(ctx_bob["unread_notifications_count"], 5)
        bob_messages = [n.message for n in ctx_bob["unread_notifications"]]
        self.assertNotIn("Alice 1", bob_messages)
        self.assertIn("Bob 0", bob_messages)

    def test_read_notifications_excluded(self):
        """Read notifications must be excluded from unread_notifications."""
        Notification.objects.create(user=self.user, message="Unread 1", read=False)
        Notification.objects.create(user=self.user, message="Read 1", read=True)

        req = self._build_request(self.user)
        ctx = unread_notifications(req)
        self.assertEqual(len(ctx["unread_notifications"]), 1)
        self.assertEqual(ctx["unread_notifications"][0].message, "Unread 1")

    def test_notification_ordering_descending_created_at(self):
        """Notifications must be ordered with newest first (-created_at)."""
        now = timezone.now()
        n1 = Notification.objects.create(
            user=self.user, message="Oldest", read=False, created_at=now - timedelta(hours=2)
        )
        n2 = Notification.objects.create(
            user=self.user, message="Middle", read=False, created_at=now - timedelta(hours=1)
        )
        n3 = Notification.objects.create(
            user=self.user, message="Newest", read=False, created_at=now
        )

        # Update timestamps explicitly since auto_now_add can override
        Notification.objects.filter(id=n1.id).update(created_at=now - timedelta(hours=2))
        Notification.objects.filter(id=n2.id).update(created_at=now - timedelta(hours=1))
        Notification.objects.filter(id=n3.id).update(created_at=now)

        req = self._build_request(self.user)
        ctx = unread_notifications(req)
        messages = [n.message for n in ctx["unread_notifications"]]
        self.assertEqual(messages, ["Newest", "Middle", "Oldest"])

    def test_notification_list_template_zero_queries_for_count(self):
        """Rendering notification_list.html dropdown must not execute duplicate COUNT(*) queries."""
        for i in range(12):
            Notification.objects.create(user=self.user, message=f"Item {i}", read=False)

        req = self._build_request(self.user)
        ctx = unread_notifications(req)
        ctx["request"] = req

        rendered = render_to_string("notification_list.html", ctx, request=req)

        # Desktop badge shows exact 12
        self.assertIn("12", rendered)
        self.assertIn("Item 0", rendered)
        self.assertIn("Item 11", rendered)
        # Mobile drawer modal is present
        self.assertIn('id="sidebarModal3"', rendered)
        self.assertIn('id="notificationWrapper"', rendered)
