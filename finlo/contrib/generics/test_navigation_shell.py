"""Focused checks for immediate destination shells on HTMX navigation."""

from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class ImmediateNavigationShellTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(settings.BASE_DIR)
        cls.navigation_script = (root / "static/assets/js/navigation_history.js").read_text(
            encoding="utf-8"
        )
        cls.global_script = (root / "static/assets/js/global.js").read_text(
            encoding="utf-8"
        )
        cls.index_template = (root / "templates/index.html").read_text(
            encoding="utf-8"
        )
        cls.login_template = (root / "templates/login.html").read_text(
            encoding="utf-8"
        )

    def test_page_types_have_inert_destination_shell_templates(self):
        for shell_type in ("list", "dashboard", "generic"):
            self.assertIn(f'id="finlo-nav-shell-{shell_type}"', self.index_template)
            template_name = f"components/skeletons/navigation_{shell_type}.html"
            get_template(template_name)
            shell = (
                Path(settings.BASE_DIR)
                / "templates"
                / f"components/skeletons/navigation_{shell_type}.html"
            ).read_text(encoding="utf-8")
            self.assertIn(f'data-finlo-navigation-shell="{shell_type}"', shell)
            self.assertNotIn("animate-pulse", shell)

    def test_navigation_inserts_shell_before_htmx_response_and_records_timings(self):
        self.assertIn("showDestinationShell(link, navigation)", self.navigation_script)
        self.assertIn("mainContent.replaceChildren(template.content.cloneNode(true))", self.navigation_script)
        self.assertIn("clickAt: startedAt", self.navigation_script)
        self.assertIn("requestDispatchMs", self.navigation_script)
        self.assertIn("shellPaintMs", self.navigation_script)
        self.assertIn("usableMs", self.navigation_script)

    def test_out_of_order_navigation_responses_cannot_replace_latest_shell(self):
        self.assertIn("const navigationRequests = new WeakMap()", self.navigation_script)
        self.assertIn("navigation.id !== latestNavigationId", self.navigation_script)
        self.assertIn("event.detail.shouldSwap = false", self.navigation_script)

    def test_navigation_errors_clear_busy_state_and_offer_retry(self):
        self.assertIn("function showNavigationFailure", self.navigation_script)
        self.assertIn('retry.dataset.finloNavRetry = "true"', self.navigation_script)
        self.assertIn('mainContent.removeAttribute("aria-busy")', self.navigation_script)
        self.assertIn("d.elt.dataset.finloNavigationPending", self.global_script)

    def test_transient_shells_are_not_saved_as_htmx_history_pages(self):
        self.assertIn('historyElement.setAttribute("hx-history", "false")', self.navigation_script)
        self.assertIn("restoreHistorySnapshots()", self.navigation_script)
        self.assertIn('mainContent.querySelector("[data-finlo-navigation-shell]")', self.navigation_script)
        self.assertIn("const path = window.location.pathname + window.location.search", self.navigation_script)
        self.assertIn("window.location.reload()", self.navigation_script)

    def test_global_script_is_preserved_during_htmx_full_layout_swaps(self):
        for template in (self.index_template, self.login_template):
            global_script_tags = [
                line for line in template.splitlines()
                if "assets/js/global.js" in line
            ]
            self.assertEqual(len(global_script_tags), 1)
            self.assertIn('id="finlo-global-js"', global_script_tags[0])
            self.assertIn("hx-preserve", global_script_tags[0])

