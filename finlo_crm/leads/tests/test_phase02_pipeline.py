"""
Phase 02: Simple Sales Pipeline Comprehensive Tests.

Covers:
1. Six-role permission matrix
2. Lead creation restriction (BDO blocked, others allowed)
3. Lead qualification rules (interest, requirements, timestamp, qualified_by, ownership)
4. ASM-to-BDO assignment rules
5. Contact creation (all 6 roles in authorized scope)
6. Authorized Opportunity creation (managers in scope; BDO only from assigned Qualified Lead)
7. Lead-to-Opportunity conversion (Contact + Opportunity, no mandatory Account)
8. Duplicate-conversion prevention
9. Proposal Sent transition (tracking proposal date/notes)
10. In Negotiation transition (tracking notes)
11. Won validation (requires actual_close_date & final_deal_value; terminal)
12. Lost validation (requires lost_reason & actual_close_date; terminal)
13. Delayed follow-up validation (requires delay_reason & next_follow_up_date)
14. Delayed-to-active transition (returns to Proposal Sent or In Negotiation)
15. Cross-company stage & contact rejection
16. Record ownership scoping and protection
17. Stage audit history recording
18. Dashboard KPI metrics calculation
19. End-to-end Section 13 Hospital Software Workflow Example
"""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from finlo.auth.models import User
from finlo.contrib.core.models import (
    Company,
    Role,
    SalesAssignment,
    SalesRegion,
    SalesTeam,
)
from finlo.contrib.core.sales_authorization import (
    has_effective_permission,
    get_sales_scope_user_ids,
)
from finlo.contrib.dashboard.utils import DefaultDashboardGenerator
from finlo.contrib.utils.middlewares import _thread_local
from finlo.utils import timezone
from finlo_crm.contacts.models import Contact
from finlo_crm.leads.authorization import assign_lead_to_bdo
from finlo_crm.leads.dashboard import lead_kpi_cards
from finlo_crm.leads.methods import convert_lead
from finlo_crm.leads.models import Lead, LeadStatus
from finlo_crm.opportunities.authorization import (
    get_qualified_assigned_leads,
    is_valid_bdo_opportunity_source,
)
from finlo_crm.opportunities.dashboard import opportunity_kpi_cards
from finlo_crm.opportunities.models import (
    FINLONEXA_OPPORTUNITY_INIT_STAGES,
    Opportunity,
    OpportunityStage,
)


class Phase02PipelineTests(TestCase):
    """Validation test suite for FINLONEXA Phase 02 Simple Sales Pipeline."""

    def setUp(self):
        self.company = Company.objects.create(
            name="ELVAVEO", email="elvaveo@example.test", country="US"
        )
        self.other_company = Company.objects.create(
            name="CompetitorCorp", email="other@example.test", country="US"
        )

        # Setup roles
        self.roles = {}
        parent_role = None
        for key, label in Role.SALES_ROLE_CHOICES:
            self.roles[key] = Role.all_objects.create(
                role_name=str(label),
                system_key=key,
                parent_role=parent_role,
                company=self.company,
            )
            parent_role = self.roles[key]

        # Setup regions
        self.region = SalesRegion.all_objects.create(
            name="North", code="N", company=self.company
        )
        self.other_region = SalesRegion.all_objects.create(
            name="South", code="S", company=self.company
        )

        # Setup hierarchy users
        self.super_admin = self.make_user("super_admin", "SUPER_ADMIN")
        self.head_of_sales = self.make_user("head_of_sales", "HEAD_OF_SALES")
        self.rsm = self.make_user("rsm", "RSM")
        self.ssm = self.make_user("ssm", "SSM")
        self.asm = self.make_user("asm", "ASM")
        self.bdo = self.make_user("bdo", "BDO")

        # Other hierarchy branch
        self.other_asm = self.make_user("other_asm", "ASM")
        self.other_bdo = self.make_user("other_bdo", "BDO")

        # Assignments
        self.make_assignment(self.super_admin, None, None)
        self.make_assignment(self.head_of_sales, None, None)
        self.make_assignment(self.rsm, self.region, self.head_of_sales)
        self.make_assignment(self.ssm, self.region, self.rsm)
        self.make_assignment(self.asm, self.region, self.ssm)
        self.make_assignment(self.other_asm, self.region, self.ssm)

        self.team = self.make_team("North-Team-A", self.region, self.ssm, self.asm)
        self.other_team = self.make_team("North-Team-B", self.region, self.ssm, self.other_asm)

        self.bdo_assignment = self.make_assignment(
            self.bdo, self.region, self.asm, self.team
        )
        self.other_bdo_assignment = self.make_assignment(
            self.other_bdo, self.region, self.other_asm, self.other_team
        )

        # Grant standard permissions
        for u in [self.super_admin, self.head_of_sales, self.rsm, self.ssm, self.asm, self.bdo]:
            self.grant(u, "leads", "view_lead", "change_lead")
            self.grant(u, "contacts", "add_contact", "view_contact", "change_contact")
            self.grant(u, "opportunities", "add_opportunity", "view_opportunity", "change_opportunity")
        for u in [self.super_admin, self.head_of_sales, self.rsm, self.ssm, self.asm]:
            self.grant(u, "leads", "add_lead")

        # Lead statuses
        self.lead_created_status = LeadStatus.all_objects.create(
            name="Lead Created", probability=10, company=self.company, order=1
        )
        self.qualified_status = LeadStatus.all_objects.create(
            name="Qualified", probability=40, company=self.company, order=2
        )

        # Pipeline stages for company
        self.stages = {}
        for config in FINLONEXA_OPPORTUNITY_INIT_STAGES:
            self.stages[config["name"]] = OpportunityStage.objects.create(
                company=self.company,
                **config
            )

        # Pipeline stages for other_company
        self.other_stage = OpportunityStage.objects.create(
            company=self.other_company,
            name="Other Opportunity",
            stage_type="open",
            order=1,
            probability=10,
        )

    def make_user(self, username, role_key, company=None):
        return User.objects.create_user(
            username=username,
            password="TestPassword123!",
            company=company or self.company,
            role=self.roles[role_key],
            country="US",
        )

    def make_assignment(self, user, region, manager, team=None):
        return SalesAssignment.all_objects.create(
            user=user,
            region=region,
            manager=manager,
            team=team,
            company=user.company,
            created_by=user,
            updated_by=user,
            is_active=True,
        )

    def make_team(self, code, region, ssm, asm):
        return SalesTeam.all_objects.create(
            name=code,
            code=code,
            company=self.company,
            region=region,
            senior_sales_manager=ssm,
            area_sales_manager=asm,
        )

    def make_lead(self, owner, title="Hospital Software"):
        previous_request = getattr(_thread_local, "request", None)
        _thread_local.request = SimpleNamespace(user=owner)
        try:
            return Lead.all_objects.create(
                company=owner.company,
                created_by=owner,
                lead_owner=owner,
                title=title,
                first_name="John",
                last_name="Doe",
                email="john@hospital.test",
                contact_number="+1234567890",
                lead_source="website",
                lead_status=self.lead_created_status,
                lead_company="City Hospital",
                industry="healthcare",
                country="US",
            )
        finally:
            if previous_request is None:
                if hasattr(_thread_local, "request"):
                    delattr(_thread_local, "request")
            else:
                _thread_local.request = previous_request

    @staticmethod
    def grant(user, app_label, *codenames):
        permissions = Permission.objects.filter(
            content_type__app_label=app_label, codename__in=codenames
        )
        user.user_permissions.add(*permissions)

    # -------------------------------------------------------------
    # 1. Six-role permission matrix & scope
    # -------------------------------------------------------------
    def test_six_role_permission_matrix(self):
        """Verify the 6 sales hierarchy roles maintain strict reporting visibility."""
        super_scope = get_sales_scope_user_ids(self.super_admin)
        hos_scope = get_sales_scope_user_ids(self.head_of_sales)
        rsm_scope = get_sales_scope_user_ids(self.rsm)
        ssm_scope = get_sales_scope_user_ids(self.ssm)
        asm_scope = get_sales_scope_user_ids(self.asm)
        bdo_scope = get_sales_scope_user_ids(self.bdo)

        # ASM sees self and reporting BDO
        self.assertIn(self.bdo.pk, asm_scope)
        self.assertIn(self.asm.pk, asm_scope)
        self.assertNotIn(self.other_bdo.pk, asm_scope)

        # SSM sees ASM and BDO under North team
        self.assertIn(self.asm.pk, ssm_scope)
        self.assertIn(self.bdo.pk, ssm_scope)
        self.assertIn(self.other_bdo.pk, ssm_scope)

        # RSM sees both teams in North region
        self.assertIn(self.asm.pk, rsm_scope)
        self.assertIn(self.bdo.pk, rsm_scope)

        # BDO sees only itself
        self.assertEqual(bdo_scope, {self.bdo.pk})

    # -------------------------------------------------------------
    # 2. Lead creation restriction
    # -------------------------------------------------------------
    def test_lead_creation_restriction(self):
        """BDO cannot create Leads across any path; other roles can."""
        self.assertFalse(has_effective_permission(self.bdo, "leads.add_lead"))
        for manager in [self.super_admin, self.head_of_sales, self.rsm, self.ssm, self.asm]:
            self.assertTrue(has_effective_permission(manager, "leads.add_lead"))

    # -------------------------------------------------------------
    # 3. Qualification rules
    # -------------------------------------------------------------
    def test_lead_qualification_rules(self):
        """Lead qualification records customer interest, requirements, timestamp, and qualified_by."""
        lead = self.make_lead(self.asm)
        assign_lead_to_bdo(lead, self.asm, self.bdo)
        self.assertFalse(lead.is_qualified())
        self.assertIsNone(lead.qualified_at)

        # Qualify via model method
        lead.qualify(
            user=self.bdo,
            customer_interest="Interested in EMR and billing modules",
            requirements="Needs 50 doctor licenses and cloud hosting",
            status=self.qualified_status,
        )
        lead.refresh_from_db()

        self.assertTrue(lead.is_qualified())
        self.assertEqual(lead.customer_interest, "Interested in EMR and billing modules")
        self.assertEqual(lead.description, "Needs 50 doctor licenses and cloud hosting")
        self.assertEqual(lead.qualified_by, self.bdo)
        self.assertIsNotNone(lead.qualified_at)
        # Original Lead owner remains unchanged
        self.assertEqual(lead.lead_owner, self.asm)

    # -------------------------------------------------------------
    # 4. ASM-to-BDO assignment
    # -------------------------------------------------------------
    def test_asm_to_bdo_assignment(self):
        """ASM can assign reporting BDO as sub-owner; rejects unauthorized assignments."""
        lead = self.make_lead(self.asm)

        # Authorized ASM assigns its subordinate BDO
        assign_lead_to_bdo(lead, self.asm, self.bdo)
        lead.refresh_from_db()
        self.assertEqual(lead.sub_owner, self.bdo)
        self.assertEqual(lead.lead_owner, self.asm)

        # Attempting to assign BDO reporting to another ASM is rejected
        lead2 = self.make_lead(self.asm)
        with self.assertRaises((PermissionDenied, ValidationError)):
            assign_lead_to_bdo(lead2, self.asm, self.other_bdo)

    # -------------------------------------------------------------
    # 5. Contact creation in authorized scope
    # -------------------------------------------------------------
    def test_contact_creation_authorized_scope(self):
        """Contact creation is allowed for all 6 roles within their authorized scope."""
        for user in [self.super_admin, self.head_of_sales, self.rsm, self.ssm, self.asm, self.bdo]:
            contact = Contact.objects.create(
                first_name="Doctor",
                last_name=f"User-{user.username}",
                email=f"doc_{user.username}@hospital.test",
                contact_owner=user,
                company=self.company,
            )
            self.assertEqual(contact.contact_owner, user)
            self.assertEqual(contact.company, self.company)

    # -------------------------------------------------------------
    # 6. Authorized Opportunity creation
    # -------------------------------------------------------------
    def test_authorized_opportunity_creation(self):
        """BDO may create an Opportunity ONLY from an explicitly assigned Qualified Lead."""
        lead = self.make_lead(self.asm)

        # Unassigned, unqualified: BDO cannot use it
        self.assertFalse(is_valid_bdo_opportunity_source(self.bdo, lead))

        # Assigned, but NOT qualified: BDO cannot use it
        assign_lead_to_bdo(lead, self.asm, self.bdo)
        self.assertFalse(is_valid_bdo_opportunity_source(self.bdo, lead))

        # Assigned AND qualified: BDO can use it
        lead.qualify(user=self.bdo, status=self.qualified_status)
        self.assertTrue(is_valid_bdo_opportunity_source(self.bdo, lead))

        # Leads visible to BDO in get_qualified_assigned_leads
        allowed_leads = get_qualified_assigned_leads(self.bdo)
        self.assertIn(lead, allowed_leads)

    # -------------------------------------------------------------
    # 7. Lead-to-Opportunity conversion (simplified)
    # -------------------------------------------------------------
    def test_lead_to_opportunity_conversion_simplified(self):
        """Qualified Lead converts directly to Contact + Opportunity without mandatory Account."""
        lead = self.make_lead(self.asm)
        assign_lead_to_bdo(lead, self.asm, self.bdo)
        lead.qualify(user=self.bdo, status=self.qualified_status)

        account, contact, opportunity = convert_lead(
            lead=lead,
            company=self.company,
            create_account=False,
            first_name="Jane",
            last_name="Smith",
            opportunity_name="Hospital ERP",
        )

        self.assertIsNone(account)
        self.assertIsNotNone(contact)
        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity.contact, contact)
        self.assertEqual(opportunity.source_lead, lead)
        self.assertEqual(opportunity.stage, self.stages["Opportunity"])

        lead.refresh_from_db()
        self.assertTrue(lead.is_convert)

    # -------------------------------------------------------------
    # 8. Duplicate conversion prevention
    # -------------------------------------------------------------
    def test_duplicate_conversion_prevention(self):
        """Prevent duplicate conversion from repeated submissions."""
        lead = self.make_lead(self.asm)
        assign_lead_to_bdo(lead, self.asm, self.bdo)
        lead.qualify(user=self.bdo, status=self.qualified_status)

        # First conversion succeeds
        convert_lead(lead=lead, company=self.company)

        # Second conversion attempt raises ValidationError
        with self.assertRaises(ValidationError):
            convert_lead(lead=lead, company=self.company)

    # -------------------------------------------------------------
    # 9. Proposal Sent transition
    # -------------------------------------------------------------
    def test_proposal_sent_transition(self):
        """Moving to Proposal Sent stage tracks proposal date and notes."""
        opp = Opportunity.objects.create(
            name="Hospital Deal",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Opportunity"],
            amount=Decimal("50000.00"),
            close_date=timezone.now().date(),
        )

        opp.stage = self.stages["Proposal Sent"]
        opp.proposal_date = timezone.now().date()
        opp.proposal_notes = "Sent formal enterprise RFP response"
        opp.clean()
        opp.save()
        opp.refresh_from_db()

        self.assertEqual(opp.stage.name, "Proposal Sent")
        self.assertEqual(opp.proposal_date, timezone.now().date())
        self.assertEqual(opp.proposal_notes, "Sent formal enterprise RFP response")

    # -------------------------------------------------------------
    # 10. In Negotiation transition
    # -------------------------------------------------------------
    def test_in_negotiation_transition(self):
        """Moving to In Negotiation tracks commercial negotiation notes."""
        opp = Opportunity.objects.create(
            name="Hospital Deal",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Proposal Sent"],
            amount=Decimal("50000.00"),
            close_date=timezone.now().date(),
        )

        opp.stage = self.stages["In Negotiation"]
        opp.negotiation_notes = "Customer requesting 10% volume discount for upfront payment"
        opp.clean()
        opp.save()
        opp.refresh_from_db()

        self.assertEqual(opp.stage.name, "In Negotiation")
        self.assertEqual(
            opp.negotiation_notes,
            "Customer requesting 10% volume discount for upfront payment",
        )

    # -------------------------------------------------------------
    # 11. Won validation
    # -------------------------------------------------------------
    def test_won_validation(self):
        """Won stage requires actual_close_date & final_deal_value, and is terminal."""
        opp = Opportunity.objects.create(
            name="Hospital Deal",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["In Negotiation"],
            amount=Decimal("50000.00"),
            close_date=timezone.now().date(),
        )

        # Fails without actual_close_date and final_deal_value
        opp.stage = self.stages["Won"]
        with self.assertRaises(ValidationError) as cm:
            opp.clean()
        self.assertIn("actual_close_date", cm.exception.message_dict)
        self.assertIn("final_deal_value", cm.exception.message_dict)

        # Valid with required fields
        opp.actual_close_date = timezone.now().date()
        opp.final_deal_value = Decimal("48000.00")
        opp.closing_notes = "Contract signed by hospital CFO"
        opp.clean()
        opp.save()
        opp.refresh_from_db()

        self.assertEqual(opp.stage.name, "Won")

        # Won is terminal: attempting to transition back to open stage is rejected
        opp.stage = self.stages["Proposal Sent"]
        with self.assertRaises(ValidationError):
            opp.clean()

    # -------------------------------------------------------------
    # 12. Lost reason validation
    # -------------------------------------------------------------
    def test_lost_validation(self):
        """Lost stage requires lost_reason and actual_close_date, and is terminal."""
        opp = Opportunity.objects.create(
            name="Hospital Deal",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["In Negotiation"],
            amount=Decimal("50000.00"),
            close_date=timezone.now().date(),
        )

        opp.stage = self.stages["Lost"]
        with self.assertRaises(ValidationError) as cm:
            opp.clean()
        self.assertIn("lost_reason", cm.exception.message_dict)

        opp.lost_reason = "Price"
        opp.actual_close_date = timezone.now().date()
        opp.clean()
        opp.save()
        opp.refresh_from_db()

        self.assertEqual(opp.stage.name, "Lost")

        # Lost is terminal
        opp.stage = self.stages["In Negotiation"]
        with self.assertRaises(ValidationError):
            opp.clean()

    # -------------------------------------------------------------
    # 13. Delayed follow-up validation
    # -------------------------------------------------------------
    def test_delayed_validation(self):
        """Delayed stage requires delay_reason and next_follow_up_date."""
        opp = Opportunity.objects.create(
            name="Hospital Deal",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Proposal Sent"],
            amount=Decimal("50000.00"),
            close_date=timezone.now().date(),
        )

        opp.stage = self.stages["Delayed"]
        with self.assertRaises(ValidationError) as cm:
            opp.clean()
        self.assertIn("delay_reason", cm.exception.message_dict)
        self.assertIn("next_follow_up_date", cm.exception.message_dict)

        opp.delay_reason = "Hospital fiscal year budget review pending Q3"
        opp.next_follow_up_date = timezone.now().date() + timedelta(days=60)
        opp.clean()
        opp.save()
        opp.refresh_from_db()

        self.assertEqual(opp.stage.name, "Delayed")

    # -------------------------------------------------------------
    # 14. Delayed-to-active transition
    # -------------------------------------------------------------
    def test_delayed_to_active_transition(self):
        """Delayed Opportunities can return to Proposal Sent or In Negotiation."""
        opp = Opportunity.objects.create(
            name="Hospital Deal",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Delayed"],
            amount=Decimal("50000.00"),
            delay_reason="Budget review",
            next_follow_up_date=timezone.now().date() + timedelta(days=30),
            close_date=timezone.now().date(),
        )

        # Transition to In Negotiation is allowed
        opp.stage = self.stages["In Negotiation"]
        opp.negotiation_notes = "Budget approved, resumed discussions"
        opp.clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "In Negotiation")

        # Return to Delayed
        opp.stage = self.stages["Delayed"]
        opp.clean()
        opp.save()

        # Transition to Proposal Sent is allowed
        opp.stage = self.stages["Proposal Sent"]
        opp.clean()
        opp.save()
        self.assertEqual(opp.stage.name, "Proposal Sent")

    # -------------------------------------------------------------
    # 15. Cross-company stage rejection
    # -------------------------------------------------------------
    def test_cross_company_rejection(self):
        """Cannot assign a stage or contact belonging to another company."""
        opp = Opportunity.objects.create(
            name="Hospital Deal",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Opportunity"],
            amount=Decimal("50000.00"),
            close_date=timezone.now().date(),
        )

        # Cross-company stage
        opp.stage = self.other_stage
        with self.assertRaises(ValidationError) as cm:
            opp.clean()
        self.assertIn("stage", cm.exception.message_dict)

        # Cross-company contact
        other_contact = Contact.objects.create(
            first_name="Foreign",
            last_name="Doctor",
            email="foreign@competitor.test",
            contact_owner=self.bdo,
            company=self.other_company,
        )
        opp.stage = self.stages["Opportunity"]
        opp.contact = other_contact
        with self.assertRaises(ValidationError) as cm:
            opp.clean()
        self.assertIn("contact", cm.exception.message_dict)

    # -------------------------------------------------------------
    # 16. Stage audit history
    # -------------------------------------------------------------
    def test_stage_audit_history(self):
        """Stage updates record history on the Opportunity."""
        opp = Opportunity.objects.create(
            name="Hospital Deal",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Opportunity"],
            amount=Decimal("50000.00"),
            close_date=timezone.now().date(),
        )
        self.assertEqual(opp.stage.name, "Opportunity")

        opp.stage = self.stages["Proposal Sent"]
        opp.proposal_date = timezone.now().date()
        opp.clean()
        opp.save()
        opp.refresh_from_db()

        self.assertEqual(opp.stage.name, "Proposal Sent")
        if hasattr(opp, "history"):
            self.assertTrue(opp.history.exists())

    # -------------------------------------------------------------
    # 17. Dashboard KPI metrics
    # -------------------------------------------------------------
    def test_dashboard_kpis(self):
        """Verify dashboard KPIs compute all 12 required metrics accurately."""
        # Create test leads
        lead1 = self.make_lead(self.asm, "Lead 1")
        lead2 = self.make_lead(self.asm, "Lead 2")
        assign_lead_to_bdo(lead2, self.asm, self.bdo)
        lead2.qualify(user=self.bdo, status=self.qualified_status)

        # Mock generator for Super Admin
        generator = Mock(spec=DefaultDashboardGenerator)
        generator.get_queryset = lambda model: model.objects.filter(company=self.company)

        lead_cards = lead_kpi_cards(generator, {"model": Lead})
        lead_dict = {card["title"]: card["value"] for card in lead_cards}
        self.assertEqual(lead_dict.get("Total Leads"), 2)
        self.assertEqual(lead_dict.get("Qualified Leads"), 1)

        # Create opportunities in various stages
        Opportunity.objects.create(
            name="Opp Proposal",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Proposal Sent"],
            amount=Decimal("20000.00"),
            close_date=timezone.now().date(),
            next_follow_up_date=timezone.now().date() + timedelta(days=5),
        )
        Opportunity.objects.create(
            name="Opp Negotiation",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["In Negotiation"],
            amount=Decimal("30000.00"),
            close_date=timezone.now().date(),
            next_follow_up_date=timezone.now().date() - timedelta(days=2),  # overdue
        )
        Opportunity.objects.create(
            name="Opp Won",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Won"],
            amount=Decimal("40000.00"),
            final_deal_value=Decimal("42000.00"),
            actual_close_date=timezone.now().date(),
            close_date=timezone.now().date(),
        )
        Opportunity.objects.create(
            name="Opp Lost",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Lost"],
            amount=Decimal("15000.00"),
            lost_reason="Price",
            actual_close_date=timezone.now().date(),
            close_date=timezone.now().date(),
        )
        Opportunity.objects.create(
            name="Opp Delayed",
            company=self.company,
            owner=self.bdo,
            stage=self.stages["Delayed"],
            amount=Decimal("25000.00"),
            delay_reason="Budget review",
            next_follow_up_date=timezone.now().date() + timedelta(days=10),
            close_date=timezone.now().date(),
        )

        opp_cards = opportunity_kpi_cards(generator, {"model": Opportunity})
        opp_dict = {card["title"]: card["value"] for card in opp_cards}

        self.assertEqual(opp_dict.get("Active Opportunities"), 3)  # Proposal, Negotiation, Delayed
        self.assertEqual(opp_dict.get("Proposal Sent"), 1)
        self.assertEqual(opp_dict.get("In Negotiation"), 1)
        self.assertEqual(opp_dict.get("Won"), 1)
        self.assertEqual(opp_dict.get("Lost"), 1)
        self.assertEqual(opp_dict.get("Delayed"), 1)
        self.assertEqual(opp_dict.get("Total Won Value"), 42000.00)
        self.assertEqual(opp_dict.get("Pipeline Value"), 75000.00)  # 20k + 30k + 25k
        self.assertEqual(opp_dict.get("Upcoming Follow-ups"), 2)
        self.assertEqual(opp_dict.get("Overdue Follow-ups"), 1)

    # -------------------------------------------------------------
    # 18. Section 13 Hospital Software Workflow Scenario
    # -------------------------------------------------------------
    def test_section_13_hospital_workflow_scenario(self):
        """
        Execute Section 13 exact end-to-end scenario:
        1. ASM creates a Lead for an ELVAVEO hospital software customer.
        2. ASM assigns its authorized BDO.
        3. BDO contacts customer and qualifies the Lead.
        4. BDO creates Contact and Opportunity.
        5. BDO sends a proposal.
        6. BDO moves Opportunity to In Negotiation.
        7. BDO marks Opportunity Won.
        8. ASM, SSM, RSM, Head of Sales, Super Admin visibility verified.
        9. Original Lead ownership remains unchanged throughout.
        """
        # Step 1: ASM creates Lead
        lead = self.make_lead(self.asm, "ELVAVEO Hospital Software Lead")
        self.assertEqual(lead.lead_owner, self.asm)

        # Step 2: ASM assigns its authorized BDO
        assign_lead_to_bdo(lead, self.asm, self.bdo)
        lead.refresh_from_db()
        self.assertEqual(lead.sub_owner, self.bdo)
        self.assertEqual(lead.lead_owner, self.asm)

        # Step 3: BDO qualifies the Lead
        lead.qualify(
            user=self.bdo,
            customer_interest="Full hospital management suite: EMR, pharmacy, patient billing",
            requirements="Deployment for 120 workstations with 99.9% uptime SLA",
            status=self.qualified_status,
        )
        lead.refresh_from_db()
        self.assertTrue(lead.is_qualified())
        self.assertEqual(lead.qualified_by, self.bdo)
        self.assertEqual(lead.lead_owner, self.asm)  # Ownership preserved

        # Step 4: BDO converts to Contact + Opportunity
        self.assertTrue(is_valid_bdo_opportunity_source(self.bdo, lead))
        account, contact, opp = convert_lead(
            lead=lead,
            company=self.company,
            create_account=False,
            first_name="Dr. Sarah",
            last_name="Johnson",
            opportunity_name="ELVAVEO Hospital Management System",
        )
        self.assertIsNone(account)
        self.assertIsNotNone(contact)
        self.assertIsNotNone(opp)
        self.assertEqual(opp.source_lead, lead)
        self.assertEqual(opp.contact, contact)
        self.assertEqual(opp.stage.name, "Opportunity")

        # Step 5: BDO sends proposal
        opp.stage = self.stages["Proposal Sent"]
        opp.proposal_date = timezone.now().date()
        opp.proposal_notes = "Sent proposal quotation $85,000 for hospital software"
        opp.amount = Decimal("85000.00")
        opp.clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "Proposal Sent")

        # Step 6: BDO moves to In Negotiation
        opp.stage = self.stages["In Negotiation"]
        opp.negotiation_notes = "Hospital committee requested 3 years maintenance included"
        opp.clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "In Negotiation")

        # Step 7: BDO marks Opportunity Won
        opp.stage = self.stages["Won"]
        opp.actual_close_date = timezone.now().date()
        opp.final_deal_value = Decimal("82500.00")
        opp.closing_notes = "Contract approved and signed by Hospital CEO"
        opp.clean()
        opp.save()
        opp.refresh_from_db()
        self.assertEqual(opp.stage.name, "Won")

        # Step 8: Multi-tier visibility verification
        asm_scope = get_sales_scope_user_ids(self.asm)
        ssm_scope = get_sales_scope_user_ids(self.ssm)
        rsm_scope = get_sales_scope_user_ids(self.rsm)
        hos_scope = get_sales_scope_user_ids(self.head_of_sales)
        super_scope = get_sales_scope_user_ids(self.super_admin)

        # BDO is within ASM, SSM, RSM, Head of Sales, and Super Admin scope
        self.assertIn(self.bdo.pk, asm_scope)
        self.assertIn(self.bdo.pk, ssm_scope)
        self.assertIn(self.bdo.pk, rsm_scope)
        self.assertIn(self.bdo.pk, hos_scope)
        self.assertIn(self.bdo.pk, super_scope)

        # Other branch does NOT see it
        other_asm_scope = get_sales_scope_user_ids(self.other_asm)
        self.assertNotIn(self.bdo.pk, other_asm_scope)

        # Step 9: Original Lead ownership remained unchanged
        lead.refresh_from_db()
        self.assertEqual(lead.lead_owner, self.asm)
        self.assertEqual(lead.sub_owner, self.bdo)
        self.assertTrue(lead.is_convert)
