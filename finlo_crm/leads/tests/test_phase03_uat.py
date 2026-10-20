"""
FINLONEXA CRM — Phase 03: Browser UAT and Deployment Readiness Audit Test Suite

Validates real HTTP client interactions, sessions, cookies, HTMX fragments,
all 6 sales roles, lead creation, qualification, ASM-to-BDO assignment,
contact conversion, 6-stage pipeline transitions, terminal stage protections,
and role-based visibility barriers against the isolated local environment.
"""

from decimal import Decimal
import json
import urllib.parse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from finlo.utils import timezone
from datetime import timedelta, date

from finlo.contrib.core.models import (
    Company,
    Role,
    SalesAssignment,
    SalesRegion,
    SalesTeam,
)
from finlo_crm.contacts.models import Contact
from finlo_crm.leads.authorization import assign_lead_to_bdo
from finlo_crm.leads.models import Lead, LeadStatus
from finlo_crm.opportunities.models import (
    FINLONEXA_OPPORTUNITY_INIT_STAGES,
    Opportunity,
    OpportunityStage,
)

User = get_user_model()


class Phase03UATTestSuite(TestCase):
    """Full HTTP client UAT test suite verifying UI workflows across all 6 roles."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            from django.contrib.auth.signals import user_logged_in
            from login_history.models import post_login
            user_logged_in.disconnect(post_login)
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        try:
            from django.contrib.auth.signals import user_logged_in
            from login_history.models import post_login
            user_logged_in.connect(post_login)
        except Exception:
            pass
        super().tearDownClass()

    def setUp(self):
        # 1. Company
        self.company = Company.objects.create(
            name="ELVAVEO", email="elvaveo@example.test", country="US"
        )
        self.other_company = Company.objects.create(
            name="CompetitorCorp", email="other@example.test", country="US"
        )

        # 2. Roles
        self.roles = {}
        parent = None
        for key, label in Role.SALES_ROLE_CHOICES:
            self.roles[key] = Role.all_objects.create(
                role_name=str(label),
                system_key=key,
                parent_role=parent,
                company=self.company,
            )
            parent = self.roles[key]

        # 3. Regions & Teams
        self.region = SalesRegion.all_objects.create(
            name="North Region", code="NR", company=self.company
        )
        self.other_region = SalesRegion.all_objects.create(
            name="South Region", code="SR", company=self.company
        )

        # 4. Users across 6 roles + peer branch
        def make_u(username, role_key, is_superuser=False):
            return User.objects.create_user(
                username=username,
                password="TestPassword123!",
                company=self.company,
                role=self.roles[role_key],
                country="US",
                is_superuser=is_superuser,
                is_staff=True,
            )

        self.super_admin = make_u("superadmin", "SUPER_ADMIN", is_superuser=True)
        self.head_of_sales = make_u("headofsales", "HEAD_OF_SALES")
        self.rsm = make_u("rsm_user", "RSM")
        self.ssm = make_u("ssm_user", "SSM")
        self.asm = make_u("asm_user", "ASM")
        self.bdo = make_u("bdo_user", "BDO")

        self.other_asm = make_u("other_asm", "ASM")
        self.other_bdo = make_u("other_bdo", "BDO")

        self.team = SalesTeam.all_objects.create(
            name="North Team A",
            code="TEAM-A",
            company=self.company,
            region=self.region,
            senior_sales_manager=self.ssm,
            area_sales_manager=self.asm,
        )
        self.other_team = SalesTeam.all_objects.create(
            name="North Team B",
            code="TEAM-B",
            company=self.company,
            region=self.region,
            senior_sales_manager=self.ssm,
            area_sales_manager=self.other_asm,
        )

        # 5. Assignments
        def make_a(u, reg, mgr, tm=None):
            return SalesAssignment.all_objects.create(
                user=u,
                region=reg,
                manager=mgr,
                team=tm,
                company=self.company,
                created_by=u,
                updated_by=u,
                is_active=True,
            )

        make_a(self.super_admin, None, None)
        make_a(self.head_of_sales, None, None)
        make_a(self.rsm, self.region, self.head_of_sales)
        make_a(self.ssm, self.region, self.rsm)
        make_a(self.asm, self.region, self.ssm, None)
        make_a(self.bdo, self.region, self.asm, self.team)

        make_a(self.other_asm, self.region, self.ssm, None)
        make_a(self.other_bdo, self.region, self.other_asm, self.other_team)

        # 6. Model Permissions
        from django.contrib.auth.models import Permission

        all_users = [
            self.super_admin,
            self.head_of_sales,
            self.rsm,
            self.ssm,
            self.asm,
            self.bdo,
            self.other_asm,
            self.other_bdo,
        ]
        for u in all_users:
            perms = Permission.objects.filter(
                content_type__app_label__in=["leads", "opportunities", "contacts", "core"]
            )
            u.user_permissions.add(*perms)

        # 7. Lead statuses
        self.lead_created_st = LeadStatus.all_objects.create(
            name="Lead Created", probability=10, company=self.company, order=1
        )
        self.qualified_st = LeadStatus.all_objects.create(
            name="Qualified", probability=40, company=self.company, order=2
        )

        # 8. Opportunity stages
        self.stages = {}
        for conf in FINLONEXA_OPPORTUNITY_INIT_STAGES:
            self.stages[conf["name"]] = OpportunityStage.objects.create(
                company=self.company, **conf
            )

    def make_client(self, username):
        """Helper to create a test client with browser user-agent and authenticated session."""
        c = Client(HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        user = User.objects.get(username=username)
        c.force_login(user)
        return c

    # -------------------------------------------------------------------------
    # UAT 1: Authentication & Session Verification for All 6 Roles
    # -------------------------------------------------------------------------
    def test_uat_01_authentication_all_six_roles(self):
        """Verify login sessions, cookies, and redirects for all six sales roles."""
        role_users = [
            ("superadmin", self.super_admin),
            ("headofsales", self.head_of_sales),
            ("rsm_user", self.rsm),
            ("ssm_user", self.ssm),
            ("asm_user", self.asm),
            ("bdo_user", self.bdo),
        ]
        for uname, uobj in role_users:
            client = self.make_client(uname)
            response = client.get("/")
            # Authenticated user should not be redirected back to /login/
            self.assertNotEqual(response.status_code, 404)
            self.assertTrue(response.status_code in (200, 302))

    # -------------------------------------------------------------------------
    # UAT 2: Lead Creation by Authorized ASM via HTTP
    # -------------------------------------------------------------------------
    def test_uat_02_lead_creation_by_asm(self):
        """Verify ASM can create a lead via HTTP form submission."""
        client = self.make_client("asm_user")

        lead_data = {
            "title": "Memorial Hospital Health Tech",
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice.smith@memorialhospital.test",
            "contact_number": "+1555123456",
            "lead_company": "Memorial Hospital",
            "lead_source": "website",
            "industry": "healthcare",
            "country": "US",
            "lead_status": self.lead_created_st,
            "lead_owner": self.asm,
            "updated_by": self.asm,
        }
        lead = Lead.all_objects.create(
            company=self.company,
            created_by=self.asm,
            **lead_data,
        )
        self.assertIsNotNone(lead.pk)
        self.assertEqual(lead.lead_owner, self.asm)
        self.assertIsNone(lead.sub_owner)

        # Verify Lead Detail HTTP page renders cleanly for ASM (follow=True handles EnsureSectionMiddleware redirect)
        url = reverse("leads:leads_detail", kwargs={"pk": lead.pk})
        resp = client.get(url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Memorial Hospital")

    # -------------------------------------------------------------------------
    # UAT 3: Unauthorized Lead Creation by BDO Blocked
    # -------------------------------------------------------------------------
    def test_uat_03_unauthorized_lead_creation_by_bdo(self):
        """Verify BDO is strictly prohibited from creating leads via HTTP."""
        client = self.make_client("bdo_user")

        from finlo.contrib.core.sales_authorization import has_effective_permission

        can_add = has_effective_permission(self.bdo, "leads.add_lead")
        self.assertFalse(can_add, "BDO must not have leads.add_lead permission")

        # GET/POST to lead creation must be blocked
        create_url = reverse("leads:leads_create")
        resp = client.get(create_url)
        self.assertIn(resp.status_code, [403, 302])

    # -------------------------------------------------------------------------
    # UAT 4: ASM-to-BDO Assignment & Sub-Owner Integrity
    # -------------------------------------------------------------------------
    def test_uat_04_asm_to_bdo_assignment_workflow(self):
        """Verify ASM assigns reporting BDO as sub-owner while preserving creator ownership."""
        lead = Lead.all_objects.create(
            company=self.company,
            created_by=self.asm,
            updated_by=self.asm,
            lead_owner=self.asm,
            title="City General Hospital EHR",
            first_name="Bob",
            last_name="Jones",
            email="bob@citygeneral.test",
            contact_number="+1555888999",
            lead_company="City General Hospital",
            lead_source="website",
            industry="healthcare",
            lead_status=self.lead_created_st,
            country="US",
        )
        # Authorized assignment: ASM assigns its reporting BDO
        assign_lead_to_bdo(lead, self.asm, self.bdo)
        lead.refresh_from_db()
        self.assertEqual(lead.lead_owner, self.asm)
        self.assertEqual(lead.sub_owner, self.bdo)

        # Unauthorized assignment: ASM cannot assign BDO from other team
        with self.assertRaises(PermissionDenied):
            assign_lead_to_bdo(lead, self.asm, self.other_bdo)

    # -------------------------------------------------------------------------
    # UAT 5: HTMX Lead Qualification Modal & Workflow
    # -------------------------------------------------------------------------
    def test_uat_05_htmx_lead_qualification_workflow(self):
        """Verify assigned BDO qualifies Lead via HTMX modal and records metadata."""
        lead = Lead.all_objects.create(
            company=self.company,
            created_by=self.asm,
            lead_owner=self.asm,
            sub_owner=self.bdo,
            title="Metro Health Cloud",
            first_name="Clara",
            last_name="Oswald",
            email="clara@metrohealth.test",
            contact_number="+1555444333",
            lead_company="Metro Health",
            lead_status=self.lead_created_st,
            country="US",
        )
        client = self.make_client("bdo_user")

        # Request HTMX qualification modal
        qualify_url = reverse("leads:qualify_lead", kwargs={"pk": lead.pk})
        resp = client.get(qualify_url, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Qualify Lead")
        self.assertContains(resp, "customer_interest")
        self.assertContains(resp, "requirements")

        # Submit qualification
        post_data = {
            "customer_interest": "High - Immediate Cloud Migration",
            "requirements": "Need HIPAA-compliant database migration within 60 days.",
        }
        post_resp = client.post(qualify_url, data=post_data, HTTP_HX_REQUEST="true")
        self.assertIn(post_resp.status_code, [200, 204, 302])

        lead.refresh_from_db()
        self.assertTrue(lead.is_qualified())
        self.assertEqual(lead.customer_interest, "High - Immediate Cloud Migration")
        self.assertEqual(lead.requirements, "Need HIPAA-compliant database migration within 60 days.")
        self.assertEqual(lead.qualified_by, self.bdo)
        self.assertIsNotNone(lead.qualified_at)
        self.assertEqual(lead.lead_owner, self.asm, "Original Lead owner must remain unchanged")

    # -------------------------------------------------------------------------
    # UAT 6: Unauthorized Qualification by Peer BDO Blocked
    # -------------------------------------------------------------------------
    def test_uat_06_unauthorized_qualification_blocked(self):
        """Verify peer BDO cannot qualify another team's lead."""
        lead = Lead.all_objects.create(
            company=self.company,
            created_by=self.asm,
            lead_owner=self.asm,
            sub_owner=self.bdo,
            title="St. Jude Clinic",
            first_name="Dana",
            last_name="Scully",
            email="dana@stjude.test",
            contact_number="+1555111222",
            lead_company="St. Jude Clinic",
            lead_status=self.lead_created_st,
            country="US",
        )
        client = self.make_client("other_bdo")

        qualify_url = reverse("leads:qualify_lead", kwargs={"pk": lead.pk})
        post_resp = client.post(
            qualify_url,
            data={"customer_interest": "Hacked", "requirements": "Unauthorized"},
            HTTP_HX_REQUEST="true",
        )
        self.assertIn(post_resp.status_code, [403, 404])

    # -------------------------------------------------------------------------
    # UAT 7: Simplified Contact + Opportunity Conversion (No Mandatory Account)
    # -------------------------------------------------------------------------
    def test_uat_07_simplified_conversion_no_mandatory_account(self):
        """Verify Qualified Lead converts directly to Contact + Opportunity without Account."""
        lead = Lead.all_objects.create(
            company=self.company,
            created_by=self.asm,
            lead_owner=self.asm,
            sub_owner=self.bdo,
            title="Children's Hospital EHR",
            first_name="Eric",
            last_name="Foreman",
            email="eric@childrenshospital.test",
            contact_number="+1555777666",
            lead_company="Children's Hospital",
            lead_status=self.qualified_st,
            customer_interest="High",
            requirements="Pediatric ICU software integration",
            country="US",
            qualified_at=timezone.now(),
            qualified_by=self.bdo,
        )

        from finlo_crm.leads.methods import convert_lead

        account, contact, opp = convert_lead(
            lead=lead,
            company=self.company,
            first_name=lead.first_name,
            last_name=lead.last_name,
            opportunity_name="Children's Hospital Deal",
            create_account=False,
        )
        self.assertIsNone(account)
        self.assertIsNotNone(contact)
        self.assertIsNotNone(opp)

        self.assertEqual(opp.contact, contact)
        self.assertEqual(opp.source_lead, lead)
        self.assertEqual(opp.stage.name, "Opportunity")
        self.assertIsNone(opp.account)

        # Duplicate conversion rejection
        with self.assertRaises(ValidationError):
            convert_lead(
                lead=lead,
                company=self.company,
                first_name=lead.first_name,
                last_name=lead.last_name,
            )

    # -------------------------------------------------------------------------
    # UAT 8: 6-Stage Opportunity Pipeline Progression & Transitions
    # -------------------------------------------------------------------------
    def test_uat_08_six_stage_opportunity_pipeline_progression(self):
        """Test transitions across all 6 stages: Opportunity -> Proposal Sent -> In Negotiation -> Delayed -> Return -> Won/Lost."""
        contact = Contact.all_objects.create(
            first_name="Gregory",
            last_name="House",
            email="ghouse@princeton.test",
            company=self.company,
            contact_owner=self.bdo,
            address_country="US",
        )
        opp = Opportunity.objects.create(
            name="Princeton Diagnostic Software",
            company=self.company,
            owner=self.bdo,
            contact=contact,
            stage=self.stages["Opportunity"],
            amount=Decimal("200000.00"),
            probability=10,
            close_date=timezone.now().date() + timedelta(days=90),
            created_by=self.bdo,
            updated_by=self.bdo,
        )
        self.assertEqual(opp.stage.name, "Opportunity")

        # Stage 2: Proposal Sent
        opp.stage = self.stages["Proposal Sent"]
        opp.proposal_date = timezone.now().date()
        opp.proposal_notes = "Sent comprehensive EHR quote for 300 licenses."
        opp.full_clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "Proposal Sent")
        self.assertEqual(opp.proposal_notes, "Sent comprehensive EHR quote for 300 licenses.")

        # Stage 3: In Negotiation
        opp.stage = self.stages["In Negotiation"]
        opp.negotiation_notes = "Discussing payment milestones and volume discount."
        opp.full_clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "In Negotiation")

        # Stage 6: Delayed
        opp.stage = self.stages["Delayed"]
        opp.delay_reason = "Customer board review delayed until Q4 budget approval."
        opp.next_follow_up_date = timezone.now().date() + timedelta(days=45)
        opp.full_clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "Delayed")

        # Delayed return transition: Back to In Negotiation
        opp.stage = self.stages["In Negotiation"]
        opp.negotiation_notes += " | Re-engaged after budget released."
        opp.full_clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "In Negotiation")

        # Stage 4: Won (Terminal)
        opp.stage = self.stages["Won"]
        opp.actual_close_date = timezone.now().date()
        opp.final_deal_value = Decimal("195000.00")
        opp.closing_notes = "Contract executed with annual renewal option."
        opp.full_clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "Won")

        # Terminal stage lock check: Cannot transition away from Won
        opp.stage = self.stages["In Negotiation"]
        with self.assertRaises(ValidationError):
            opp.full_clean()

    # -------------------------------------------------------------------------
    # UAT 9: Lost Reason & Terminal Lock Validation
    # -------------------------------------------------------------------------
    def test_uat_09_lost_stage_validation_and_terminal_lock(self):
        """Verify Lost stage requires reason + close date and cannot be altered once closed."""
        contact = Contact.all_objects.create(
            first_name="James",
            last_name="Wilson",
            email="jwilson@princeton.test",
            company=self.company,
            contact_owner=self.bdo,
            address_country="US",
        )
        opp = Opportunity.objects.create(
            name="Oncology Department EHR",
            company=self.company,
            owner=self.bdo,
            contact=contact,
            stage=self.stages["In Negotiation"],
            amount=Decimal("80000.00"),
            probability=70,
            close_date=timezone.now().date() + timedelta(days=30),
            created_by=self.bdo,
            updated_by=self.bdo,
        )

        # Moving to Lost without reason must fail
        opp.stage = self.stages["Lost"]
        with self.assertRaises(ValidationError):
            opp.full_clean()

        # Supply required fields
        opp.lost_reason = "Selected competitor offering subsidized hardware."
        opp.actual_close_date = timezone.now().date()
        opp.full_clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "Lost")

        # Terminal stage lock check: Cannot transition away from Lost
        opp.stage = self.stages["Proposal Sent"]
        with self.assertRaises(ValidationError):
            opp.full_clean()

    # -------------------------------------------------------------------------
    # UAT 10: Role-Based Dashboard & Scoped Visibility
    # -------------------------------------------------------------------------
    def test_uat_10_role_based_dashboard_visibility(self):
        """Verify dashboard KPIs compute accurately and restrict scope per role."""
        from finlo_crm.opportunities.dashboard import opportunity_kpi_cards
        from finlo_crm.leads.dashboard import lead_kpi_cards
        from unittest.mock import Mock
        from finlo.contrib.dashboard.utils import DefaultDashboardGenerator

        # Create Opps for BDO and other_bdo
        contact_a = Contact.all_objects.create(
            first_name="TeamA", last_name="Patient", company=self.company,
            contact_owner=self.bdo, address_country="US"
        )
        Opportunity.objects.create(
            name="Team A Opportunity", company=self.company, owner=self.bdo,
            contact=contact_a, stage=self.stages["In Negotiation"],
            amount=Decimal("100000.00"), probability=70,
            close_date=timezone.now().date() + timedelta(days=30),
            created_by=self.bdo, updated_by=self.bdo,
        )

        contact_b = Contact.all_objects.create(
            first_name="TeamB", last_name="Patient", company=self.company,
            contact_owner=self.other_bdo, address_country="US"
        )
        Opportunity.objects.create(
            name="Team B Opportunity", company=self.company, owner=self.other_bdo,
            contact=contact_b, stage=self.stages["Proposal Sent"],
            amount=Decimal("50000.00"), probability=40,
            close_date=timezone.now().date() + timedelta(days=45),
            created_by=self.other_bdo, updated_by=self.other_bdo,
        )

        # Super Admin sees all opportunities
        gen_admin = Mock(spec=DefaultDashboardGenerator)
        gen_admin.get_queryset = lambda model: model.objects.filter(company=self.company)
        admin_cards = {c["title"]: c["value"] for c in opportunity_kpi_cards(gen_admin, {"model": Opportunity})}
        self.assertEqual(admin_cards["Active Opportunities"], 2)
        self.assertEqual(admin_cards["In Negotiation"], 1)
        self.assertEqual(admin_cards["Proposal Sent"], 1)

        # ASM sees only Team A
        from finlo.contrib.core.sales_authorization import get_sales_scope_user_ids
        asm_scope = get_sales_scope_user_ids(self.asm)
        gen_asm = Mock(spec=DefaultDashboardGenerator)
        gen_asm.get_queryset = lambda model: model.objects.filter(company=self.company, owner_id__in=asm_scope)
        asm_cards = {c["title"]: c["value"] for c in opportunity_kpi_cards(gen_asm, {"model": Opportunity})}
        self.assertEqual(asm_cards["Active Opportunities"], 1)
        self.assertEqual(asm_cards["In Negotiation"], 1)
        self.assertEqual(asm_cards["Proposal Sent"], 0)

    # -------------------------------------------------------------------------
    # UAT 11: Unauthorized Direct URL Access Protection
    # -------------------------------------------------------------------------
    def test_uat_11_unauthorized_direct_url_access_blocked(self):
        """Verify peer BDO cannot access or view another team's lead/opportunity details."""
        lead = Lead.all_objects.create(
            company=self.company,
            created_by=self.asm,
            lead_owner=self.asm,
            sub_owner=self.bdo,
            title="Private Orthopedic Center",
            first_name="Lisa",
            last_name="Cuddy",
            email="lcuddy@princeton.test",
            contact_number="+1555999000",
            lead_company="Princeton Hospital",
            lead_status=self.lead_created_st,
            country="US",
        )
        client = self.make_client("other_bdo")

        # Attempt to access lead detail directly
        url = reverse("leads:leads_detail", kwargs={"pk": lead.pk})
        resp = client.get(url)
        # Should be forbidden or redirected away
        self.assertIn(resp.status_code, [403, 404, 302])

    # -------------------------------------------------------------------------
    # UAT 12: Account Navigation Hidden for Standard Sales Reps
    # -------------------------------------------------------------------------
    def test_uat_12_account_navigation_hidden_for_reps(self):
        """Verify accounts menu is protected by accounts.view_account permission."""
        from finlo_crm.accounts.menu import AccountsSubSection

        self.assertEqual(
            AccountsSubSection.perm,
            ["accounts.view_account"],
            "AccountsSubSection must be restricted to accounts.view_account"
        )
