"""
Tests for Phase 4C: Session and Signal Performance Optimization.

Validates that:
1. First-time record navigation populates selected_ids in request.session.
2. Repeated identical GET requests do not modify request.session (avoiding UPDATE django_session).
3. Changing filters/queries updates request.session with new selected_ids.
4. Saving Session instances does not trigger automation or workflow introspection (0 pg_class queries).
5. Saving CRM business models (e.g. Account, Lead) still invokes automations and workflows.
"""

from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.models import Session
from finlo_crm.accounts.views import AccountListView
from finlo_crm.accounts.models import Account
from finlo.contrib.automations.signals import (
    trigger_automations_on_save,
)
from finlo.contrib.workflow.signals import trigger_workflow_rules_on_save
from finlo.registry.feature import FEATURE_REGISTRY

User = get_user_model()


class SessionAndSignalOptimizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        self.rf = RequestFactory()
        self.middleware = SessionMiddleware(lambda r: None)

    def test_first_time_navigation_stores_selected_ids(self):
        """First request with a new session correctly populates selected IDs."""
        req = self.rf.get("/crm/accounts/accounts-list-view/?section=people", HTTP_HX_REQUEST="true")
        req.user = self.user
        req._skip_header_context = True
        self.middleware.process_request(req)

        view = AccountListView.as_view()
        resp = view(req)
        self.middleware.process_response(req, resp)

        session_key = "list_view_queryset_ids_account"
        self.assertIn(session_key, req.session)
        self.assertIsInstance(req.session[session_key], list)
        self.assertTrue(len(req.session[session_key]) > 0)

    def test_repeated_identical_get_does_not_modify_session(self):
        """A repeated GET with identical selected IDs does not mark session.modified."""
        # Setup session with current IDs
        req1 = self.rf.get("/crm/accounts/accounts-list-view/?section=people", HTTP_HX_REQUEST="true")
        req1.user = self.user
        req1._skip_header_context = True
        self.middleware.process_request(req1)
        view = AccountListView.as_view()
        resp1 = view(req1)
        self.middleware.process_response(req1, resp1)
        session_id = req1.session.session_key

        # Second request using saved session
        req2 = self.rf.get("/crm/accounts/accounts-list-view/?section=people", HTTP_HX_REQUEST="true")
        req2.user = self.user
        req2._skip_header_context = True
        req2.COOKIES["sessionid"] = session_id
        self.middleware.process_request(req2)

        self.assertFalse(req2.session.modified)
        _resp2 = view(req2)
        # Verify session.modified remains False after view execution
        self.assertFalse(req2.session.modified)

    def test_changing_filters_updates_session(self):
        """Changing filters/query parameters updates session when selected IDs change."""
        req = self.rf.get("/crm/accounts/accounts-list-view/?section=people", HTTP_HX_REQUEST="true")
        req.user = self.user
        req._skip_header_context = True
        self.middleware.process_request(req)

        # Pre-seed session with dummy IDs that don't match reality
        session_key = "list_view_queryset_ids_account"
        req.session[session_key] = [999999991, 999999992]
        req.session.modified = False

        view = AccountListView.as_view()
        _resp = view(req)

        # Session should be marked modified and contain the new IDs
        self.assertTrue(req.session.modified)
        self.assertNotEqual(req.session[session_key], [999999991, 999999992])

    def test_session_save_does_not_trigger_introspection(self):
        """Session model saves are ignored by automation and workflow signals without introspection."""
        dummy_session = Session(session_key="test_session_xyz")

        with patch("finlo.contrib.automations.signals.is_running_migrations") as mock_auto_mig, \
             patch("finlo.contrib.workflow.signals.is_running_migrations") as mock_wf_mig:
            trigger_automations_on_save(sender=Session, instance=dummy_session, created=False)
            trigger_workflow_rules_on_save(sender=Session, instance=dummy_session, created=False)

            # Neither should have checked migrations / table_names
            mock_auto_mig.assert_not_called()
            mock_wf_mig.assert_not_called()

    def test_crm_business_model_is_processed_by_signals(self):
        """CRM models in FEATURE_REGISTRY['automation_models'] and ['workflow_models'] pass sender checks."""
        allowed_auto = FEATURE_REGISTRY.get("automation_models", [])
        allowed_wf = FEATURE_REGISTRY.get("workflow_models", [])

        self.assertIn(Account, allowed_auto)
        self.assertIn(Account, allowed_wf)
        self.assertNotIn(Session, allowed_auto)
        self.assertNotIn(Session, allowed_wf)

        account = Account.objects.first()
        if account:
            with patch("finlo.contrib.automations.signals.is_running_migrations", return_value=False) as mock_auto_mig, \
                 patch("finlo.contrib.workflow.signals.is_running_migrations", return_value=False) as mock_wf_mig:
                trigger_automations_on_save(sender=Account, instance=account, created=False)
                trigger_workflow_rules_on_save(sender=Account, instance=account, created=False)

                # For CRM models, migration checks ARE called
                mock_auto_mig.assert_called_once()
                mock_wf_mig.assert_called_once()

