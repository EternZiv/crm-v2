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
        cls.sidebar_css = (root / "static/assets/css/style.css").read_text(
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
        self.assertIn('mainContent.querySelector(".finlo-skeleton")', self.navigation_script)
        self.assertIn("const path = window.location.pathname + window.location.search", self.navigation_script)
        self.assertIn("restoreInvalidHistorySnapshot(key)", self.navigation_script)
        self.assertIn("scheduleHistoryValidation(path, Boolean(event.detail?.cacheMiss))", self.navigation_script)
        history_restore = self.navigation_script.split(
            'document.addEventListener("htmx:historyRestore"', maxsplit=1
        )[1].split("// --- Tab Visibility", maxsplit=1)[0]
        self.assertNotIn("window.location.reload()", history_restore)

    def test_history_restore_reinitializes_charts_and_clears_protected_cache_on_auth_failure(self):
        self.assertIn("function initializeRestoredDashboard(mainContent)", self.navigation_script)
        self.assertIn("initializeRestoredDashboard(mainContent);", self.navigation_script)
        self.assertIn("if (response.status === 401", self.navigation_script)
        self.assertIn("if (response.status === 403)", self.navigation_script)
        self.assertIn("clearProtectedHistoryCaches();", self.navigation_script)

    def test_history_cache_miss_shows_destination_shell_and_clears_on_failure(self):
        self.assertIn('addEventListener("htmx:historyCacheMiss"', self.navigation_script)
        self.assertIn("function showHistoryDestinationShell(path)", self.navigation_script)
        self.assertIn("function getHistoryShellType(path)", self.navigation_script)
        self.assertIn('addEventListener("htmx:historyCacheMissLoadError"', self.navigation_script)
        self.assertIn('delete mainContent.dataset.finloHistoryNavigationPending', self.navigation_script)
        self.assertIn('document.addEventListener("htmx:historyRestore"', self.navigation_script)
        self.assertIn("restoreHistorySnapshots();", self.navigation_script)

    def test_client_cache_history_entries_are_compatible_with_htmx_popstate(self):
        self.assertIn('history.pushState({ htmx: true }, "", url)', self.navigation_script)
        self.assertIn("suppressHistorySnapshot(mainContent)", self.navigation_script)

    def test_global_script_is_preserved_during_htmx_full_layout_swaps(self):
        for template in (self.index_template, self.login_template):
            global_script_tags = [
                line for line in template.splitlines()
                if "assets/js/global.js" in line
            ]
            self.assertEqual(len(global_script_tags), 1)
            self.assertIn('id="finlo-global-js"', global_script_tags[0])
            self.assertIn("hx-preserve", global_script_tags[0])

    def test_unified_sidebar_arrows_toggle_group_visibility(self):
        self.assertIn('closest("[data-nav-group-toggle]")', self.global_script)
        self.assertIn(
            "setNavGroupExpanded(sectionId, !currentlyExpanded);",
            self.global_script,
        )
        self.assertIn('group.classList.toggle("hidden", !expanded)', self.global_script)
        self.assertIn(
            ".finlo-nav-children.hidden {\n  display: none !important;",
            self.sidebar_css,
        )

