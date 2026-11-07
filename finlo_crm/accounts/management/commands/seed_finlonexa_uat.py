"""Seed an explicitly approved, synthetic FINLONEXA UAT CRM dataset."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from finlo.contrib.activity.models import Activity
from finlo.contrib.core.models import (
    Company,
    FiscalYearInstance,
    FinloAttachment,
    FinloContentType,
    Period,
    Role,
    SalesAssignment,
    SalesRegion,
    SalesTeam,
)
from finlo_crm.accounts.models import Account
from finlo_crm.campaigns.models import Campaign, CampaignMember
from finlo_crm.contacts.models import Contact, ContactAccountRelationship
from finlo_crm.forecast.models import Forecast, ForecastType
from finlo_crm.leads.authorization import assign_lead_to_bdo
from finlo_crm.leads.models import DEFAULT_LEAD_INIT_STAGES, Lead, LeadStatus
from finlo_crm.opportunities.models import (
    DEFAULT_OPPORTUNITY_INIT_STAGES,
    Opportunity,
    OpportunityContactRole,
    OpportunityStage,
)


PROJECT_REF = "gwnxxxrxameundeqqcag"
COMPANY_NAME = "FINLONEXA UAT"
SEED_PREFIX = "FINLONEXA_UAT_02F"
USER_NAMES = {
    "SUPER_ADMIN": "test_superadmin",
    "HEAD_OF_SALES": "test_head_sales",
    "RSM": "test_rsm",
    "SSM": "test_ssm",
    "ASM": "test_asm",
    "BDO": "test_bdo",
}


class Command(BaseCommand):
    help = "Preview or seed the approved FINLONEXA UAT demo dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the approved synthetic dataset; otherwise run read-only.",
        )
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Preview the tagged-record cleanup scope without deleting anything.",
        )

    def handle(self, **options):
        if options["apply"] and options["cleanup"]:
            raise CommandError(
                "--cleanup is preview-only and cannot be combined with --apply."
            )

        self._check_database_identity()
        if options["cleanup"]:
            self._preview_cleanup()
            return

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
            self._load_and_validate_uat()
            self._check_side_effect_configuration()
            self._check_seed_namespace()
            plan = self._planned_counts()

        self.stdout.write(f"Database identity: Supabase project {PROJECT_REF}, PostgreSQL")
        self.stdout.write(f"UAT company: {COMPANY_NAME} (HQ; existing)")
        self.stdout.write("No existing CRM records will be updated.")
        self._print_plan(plan, dry_run=not options["apply"])

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN ONLY. No database writes were performed. "
                    "Use --apply only for this approved plan."
                )
            )
            return

        with transaction.atomic():
            self._load_and_validate_uat()
            self._check_side_effect_configuration()
            self._check_seed_namespace()
            forecasts_before = Forecast.all_objects.filter(
                company=self.company,
                name__startswith=f"{SEED_PREFIX} Forecast",
            ).count()
            created = self._seed_dataset()
            expected_forecasts = 12
            forecast_count = Forecast.all_objects.filter(
                company=self.company,
                name__startswith=f"{SEED_PREFIX} Forecast",
            ).count()
            if forecast_count != expected_forecasts:
                raise CommandError(
                    f"Forecast invariant failed: expected {expected_forecasts}, "
                    f"found {forecast_count}; transaction rolled back."
                )
            created["Forecast"] = forecast_count - forecasts_before

        self.stdout.write(self.style.SUCCESS("UAT dataset committed successfully."))
        self.stdout.write("Records inserted during this run:")
        for label, count in created.items():
            self.stdout.write(f"  {label}: {count}")
        self.stdout.write("No unrelated records were modified or deleted.")

    def _check_database_identity(self):
        if connection.vendor != "postgresql":
            raise CommandError("Refusing to run: the configured database is not PostgreSQL.")
        identity = connection.settings_dict
        configured_identity = (
            str(identity.get("HOST", "")) + str(identity.get("USER", ""))
        ).casefold()
        if PROJECT_REF.casefold() not in configured_identity:
            raise CommandError(
                "Refusing to run: configured connection does not identify the approved "
                "Supabase project."
            )
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), version()")
            database_name, server_version = cursor.fetchone()
        if database_name != "postgres" or "PostgreSQL 17" not in server_version:
            raise CommandError(
                "Refusing to run: database name or PostgreSQL version differs from "
                "the approved preflight."
            )

    def _load_and_validate_uat(self):
        companies = list(Company.all_objects.filter(name=COMPANY_NAME))
        if len(companies) != 1 or not companies[0].hq:
            raise CommandError(
                "Expected exactly one existing FINLONEXA UAT HQ company; no setup "
                "company will be created or changed."
            )
        self.company = companies[0]

        users = list(
            apps.get_model("core", "FinloUser")
            .all_objects.filter(username__in=USER_NAMES.values())
            .select_related("role", "company")
        )
        users_by_name = {user.username: user for user in users}
        if set(users_by_name) != set(USER_NAMES.values()):
            raise CommandError("The six approved UAT accounts are not all present.")
        self.users = {}
        for role_key, username in USER_NAMES.items():
            user = users_by_name[username]
            if (
                user.company_id != self.company.pk
                or not user.is_active
                or user.is_staff
                or user.is_superuser
                or user.role is None
                or user.role.system_key != role_key
            ):
                raise CommandError(
                    f"UAT account {username} no longer matches the approved role/company state."
                )
            self.users[role_key] = user

        if Role.all_objects.filter(company=self.company).count() != 6:
            raise CommandError("The UAT company no longer has exactly six canonical roles.")
        if SalesRegion.all_objects.filter(company=self.company).count() != 1:
            raise CommandError("The approved UAT region is missing or has changed.")
        if SalesTeam.all_objects.filter(company=self.company).count() != 1:
            raise CommandError("The approved UAT team is missing or has changed.")

        assignments = list(
            SalesAssignment.all_objects.filter(
                company=self.company, is_active=True
            ).select_related("user__role", "manager", "team")
        )
        if len(assignments) != 6:
            raise CommandError("Expected six active UAT sales assignments.")
        bdo_assignment = next(
            (
                assignment
                for assignment in assignments
                if assignment.user_id == self.users["BDO"].pk
            ),
            None,
        )
        if (
            bdo_assignment is None
            or bdo_assignment.manager_id != self.users["ASM"].pk
            or bdo_assignment.team is None
            or bdo_assignment.team.area_sales_manager_id != self.users["ASM"].pk
        ):
            raise CommandError("The BDO-to-ASM UAT assignment is not intact.")

        fiscal_years = list(
            FiscalYearInstance.all_objects.filter(
                company=self.company, is_current=True
            )
        )
        if len(fiscal_years) != 1:
            raise CommandError("Expected one current UAT fiscal year.")
        periods = list(
            Period.all_objects.filter(
                company=self.company,
                quarter__fiscal_year=fiscal_years[0],
            )
            .select_related("quarter")
            .order_by("start_date")
        )
        if len(periods) < 2:
            raise CommandError(
                "At least two existing periods in the current fiscal year are required."
            )
        today = timezone.localdate()
        self.periods = periods
        existing_forecasts = list(
            Forecast.all_objects.filter(
                company=self.company,
                name__startswith=f"{SEED_PREFIX} Forecast",
            )
            .exclude(period__isnull=True)
            .select_related("period")
        )
        existing_periods = {
            forecast.period_id: forecast.period for forecast in existing_forecasts
        }
        if len(existing_periods) == 2:
            selected_periods = sorted(
                existing_periods.values(), key=lambda period: period.start_date
            )
            self.primary_period, self.secondary_period = selected_periods
        elif len(existing_periods) > 2:
            raise CommandError(
                "Tagged forecasts span more than two periods; refusing to extend "
                "the approved seed."
            )
        else:
            self.primary_period = next(
                (
                    period
                    for period in periods
                    if period.start_date <= today <= period.end_date
                ),
                periods[0],
            )
            primary_index = periods.index(self.primary_period)
            self.secondary_period = periods[(primary_index + 1) % len(periods)]

    def _check_side_effect_configuration(self):
        automation = apps.get_model("automations", "FinloAutomation")
        assignment_rule = apps.get_model("leads", "LeadAssignmentRule")
        mail_config = apps.get_model("mail", "FinloMailConfiguration")
        google_config = apps.get_model("calendar", "GoogleCalendarConfig")
        google_integration = apps.get_model("calendar", "GoogleIntegrationSetting")
        opportunity_settings = apps.get_model(
            "opportunities", "OpportunitySettings"
        )
        active_forecast_types = ForecastType.all_objects.filter(is_active=True).exclude(
            name__startswith=f"{SEED_PREFIX} Forecast"
        )

        unsafe = {
            "active automations": automation.all_objects.filter(is_active=True).count(),
            "active lead assignment rules": assignment_rule.all_objects.filter(
                is_active=True
            ).count(),
            "outgoing email configurations": mail_config.all_objects.filter(
                mail_channel="outgoing"
            ).count(),
            "Google Calendar configurations": google_config.all_objects.count(),
            "Google integration settings": google_integration.all_objects.count(),
            "team-selling enabled": opportunity_settings.all_objects.filter(
                company=self.company, team_selling_enabled=True
            ).count(),
            "unrelated active forecast types": active_forecast_types.count(),
        }
        active = {label: count for label, count in unsafe.items() if count}
        if active:
            summary = ", ".join(f"{label}: {count}" for label, count in active.items())
            raise CommandError(
                "Refusing to seed because external automation or forecast side effects "
                f"may occur ({summary})."
            )

    def _check_seed_namespace(self):
        checks = (
            (Account, "name"),
            (Contact, "email"),
            (Lead, "title"),
            (Opportunity, "name"),
            (Campaign, "campaign_name"),
            (Activity, "subject"),
            (FinloAttachment, "title"),
            (LeadStatus, "name"),
            (OpportunityStage, "name"),
            (ForecastType, "name"),
            (Forecast, "name"),
        )
        for model, field in checks:
            queryset = model.all_objects.filter(company=self.company)
            if model is Contact:
                queryset = queryset.filter(email__startswith="finlonexa_uat_02f_")
            else:
                queryset = queryset.filter(**{f"{field}__startswith": SEED_PREFIX})
            if queryset.count() > self._approved_limit(model):
                raise CommandError(
                    f"Seed namespace contains more {model._meta.label} rows than approved."
                )

        untagged_config = (
            LeadStatus.all_objects.filter(company=self.company)
            .exclude(name__startswith=SEED_PREFIX)
            .exists()
            or OpportunityStage.all_objects.filter(company=self.company)
            .exclude(name__startswith=SEED_PREFIX)
            .exists()
        )
        if untagged_config:
            raise CommandError(
                "UAT lead statuses or opportunity stages changed since preflight; "
                "refusing to reorder or update them."
            )

        untagged_forecasts = Forecast.all_objects.filter(company=self.company).exclude(
            name__startswith=f"{SEED_PREFIX} Forecast"
        )
        if untagged_forecasts.exists():
            raise CommandError(
                "UAT forecasts now include untagged rows; refusing to let forecast "
                "signals update them."
            )

        untagged_business_data = (
            Account.all_objects.filter(company=self.company)
            .exclude(name__startswith=SEED_PREFIX)
            .exists()
            or Contact.all_objects.filter(company=self.company)
            .exclude(email__startswith="finlonexa_uat_02f_")
            .exists()
            or Lead.all_objects.filter(company=self.company)
            .exclude(title__startswith=SEED_PREFIX)
            .exists()
            or Opportunity.all_objects.filter(company=self.company)
            .exclude(name__startswith=SEED_PREFIX)
            .exists()
            or Campaign.all_objects.filter(company=self.company)
            .exclude(campaign_name__startswith=SEED_PREFIX)
            .exists()
            or Activity.all_objects.filter(company=self.company)
            .exclude(subject__startswith=SEED_PREFIX)
            .exists()
            or FinloAttachment.all_objects.filter(company=self.company)
            .exclude(title__startswith=SEED_PREFIX)
            .exists()
        )
        if untagged_business_data:
            raise CommandError(
                "UAT business records now exist outside this seed namespace; refusing "
                "to mix them into demo data or forecast calculations."
            )

    @staticmethod
    def _approved_limit(model):
        limits = {
            Account: 25,
            Contact: 75,
            Lead: 100,
            Opportunity: 50,
            Campaign: 10,
            Activity: 120,
            FinloAttachment: 60,
            LeadStatus: 6,
            OpportunityStage: 10,
            ForecastType: 1,
            Forecast: 12,
        }
        return limits[model]

    def _planned_counts(self):
        return {
            "Account": 25,
            "Contact": 75,
            "ContactAccountRelationship": 75,
            "LeadStatus": 6,
            "Lead": 100,
            "OpportunityStage": 10,
            "Opportunity": 50,
            "OpportunityContactRole": 50,
            "Campaign": 10,
            "CampaignMember": 50,
            "Activity: task": 80,
            "Activity: meeting": 25,
            "Activity: call/event": 15,
            "FinloAttachment note": 60,
            "ForecastType": 1,
            "Forecast": 12,
        }

    def _print_plan(self, plan, dry_run):
        mode = "READ-ONLY DRY RUN" if dry_run else "APPROVED APPLY"
        self.stdout.write(f"{mode}: proposed tagged UAT records")
        for label, count in plan.items():
            self.stdout.write(f"  {label}: {count}")

    def _preview_cleanup(self):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
            self._load_and_validate_uat()
            counts = {
                "activities": Activity.all_objects.filter(
                    company=self.company, subject__startswith=SEED_PREFIX
                ).count(),
                "notes": FinloAttachment.all_objects.filter(
                    company=self.company, title__startswith=SEED_PREFIX
                ).count(),
                "contact/account links": ContactAccountRelationship.all_objects.filter(
                    company=self.company,
                    account__name__startswith=SEED_PREFIX,
                ).count(),
                "campaign members": CampaignMember.all_objects.filter(
                    company=self.company,
                    campaign__campaign_name__startswith=SEED_PREFIX,
                ).count(),
                "opportunity contact roles": OpportunityContactRole.all_objects.filter(
                    company=self.company,
                    opportunity__name__startswith=SEED_PREFIX,
                ).count(),
                "opportunities": Opportunity.all_objects.filter(
                    company=self.company, name__startswith=SEED_PREFIX
                ).count(),
                "leads": Lead.all_objects.filter(
                    company=self.company, title__startswith=SEED_PREFIX
                ).count(),
                "contacts": Contact.all_objects.filter(
                    company=self.company, email__startswith="finlonexa_uat_02f_"
                ).count(),
                "accounts": Account.all_objects.filter(
                    company=self.company, name__startswith=SEED_PREFIX
                ).count(),
                "campaigns": Campaign.all_objects.filter(
                    company=self.company, campaign_name__startswith=SEED_PREFIX
                ).count(),
                "forecasts": Forecast.all_objects.filter(
                    company=self.company, name__startswith=f"{SEED_PREFIX} Forecast"
                ).count(),
                "forecast types": ForecastType.all_objects.filter(
                    company=self.company, name__startswith=f"{SEED_PREFIX} Forecast"
                ).count(),
                "opportunity stages": OpportunityStage.all_objects.filter(
                    company=self.company, name__startswith=SEED_PREFIX
                ).count(),
                "lead statuses": LeadStatus.all_objects.filter(
                    company=self.company, name__startswith=SEED_PREFIX
                ).count(),
            }
        self.stdout.write("Preview only; no records were deleted:")
        for label, count in counts.items():
            self.stdout.write(f"  {label}: {count}")

    def _seed_dataset(self):
        from finlo_crm.forecast.utils import ForecastCalculator

        self.created_counts = {}
        status_map = self._create_lead_statuses()
        stage_map = self._create_opportunity_stages()
        forecast_type, _ = self._get_or_create(
            ForecastType,
            {"name": f"{SEED_PREFIX} Forecast - Expected Revenue"},
            {
                "forecast_type": "deal_revenue_expected_amount",
                "description": "Synthetic FINLONEXA UAT forecast type.",
                "created_by": self.users["SUPER_ADMIN"],
                "updated_by": self.users["SUPER_ADMIN"],
            },
        )
        accounts = self._create_accounts()
        contacts = self._create_contacts(accounts)
        leads = self._create_leads(status_map)
        campaigns = self._create_campaigns()
        opportunities = self._create_opportunities(
            accounts, contacts, campaigns, stage_map
        )
        self._create_campaign_members(campaigns, leads, contacts)
        self._create_activities(accounts, contacts, leads, opportunities)
        self._create_notes(accounts, contacts, leads, opportunities)

        calculator = ForecastCalculator(
            fiscal_year=self.primary_period.quarter.fiscal_year
        )
        for user in self.users.values():
            calculator.create_or_update_period_forecast(
                user, forecast_type, self.primary_period
            )
            calculator.create_or_update_period_forecast(
                user, forecast_type, self.secondary_period
            )

        self.created_counts["Forecast"] = 0
        return self.created_counts

    def _audit_fields(self, owner):
        return {"created_by": owner, "updated_by": owner}

    def _get_or_create(self, model, lookup, defaults, ignore_changes=()):
        manager = getattr(model, "all_objects", model.objects)
        queryset = manager.filter(company=self.company, **lookup)
        obj = queryset.first()
        if obj is not None:
            for field_name, expected in defaults.items():
                if field_name in ignore_changes:
                    continue
                actual = getattr(obj, field_name)
                field = model._meta.get_field(field_name)
                if field.is_relation and not field.many_to_many:
                    actual = getattr(obj, f"{field_name}_id")
                    expected = getattr(expected, "pk", expected)
                if actual != expected:
                    raise CommandError(
                        f"Existing tagged {model._meta.label} row conflicts with "
                        f"the approved seed definition ({field_name})."
                    )
            return obj, False

        obj = model(company=self.company, **lookup, **defaults)
        if model is Activity:
            obj._skip_google_push = True
        obj.full_clean()
        obj.save()
        label = model.__name__
        self.created_counts[label] = self.created_counts.get(label, 0) + 1
        return obj, True

    def _create_lead_statuses(self):
        result = {}
        owner = self.users["SUPER_ADMIN"]
        for definition in DEFAULT_LEAD_INIT_STAGES:
            name = f"{SEED_PREFIX} {definition['name']}"
            status, _ = self._get_or_create(
                LeadStatus,
                {"name": name},
                {
                    "order": definition["order"],
                    "probability": Decimal(str(definition["probability"])),
                    "is_final": definition["is_final"],
                    "created_by": owner,
                    "updated_by": owner,
                },
            )
            result[str(definition["name"])] = status
        return result

    def _create_opportunity_stages(self):
        result = {}
        owner = self.users["SUPER_ADMIN"]
        for definition in DEFAULT_OPPORTUNITY_INIT_STAGES:
            original_name = str(definition["name"])
            if original_name == "Closed Won":
                stage_type = "won"
            elif original_name == "Closed Lost":
                stage_type = "lost"
            else:
                stage_type = "open"
            name = f"{SEED_PREFIX} {original_name}"
            stage, _ = self._get_or_create(
                OpportunityStage,
                {"name": name},
                {
                    "order": definition["order"],
                    "probability": Decimal(str(definition["probability"])),
                    "is_final": definition["is_final"],
                    "stage_type": stage_type,
                    "created_by": owner,
                    "updated_by": owner,
                },
            )
            result[original_name] = stage
        return result

    def _create_accounts(self):
        result = []
        industries = [value for value, _ in Account.INDUSTRY_CHOICES]
        account_types = [value for value, _ in Account.ACCOUNT_TYPE_CHOICES]
        for index in range(25):
            owner = list(self.users.values())[index % 6]
            account, _ = self._get_or_create(
                Account,
                {"name": f"{SEED_PREFIX} Account {index + 1:03d}"},
                {
                    "account_number": f"UAT02F{index + 1:03d}",
                    "account_owner": owner,
                    "account_type": account_types[index % len(account_types)],
                    "account_source": "referral",
                    "annual_revenue": Decimal(500000 + index * 125000),
                    "industry": industries[index % len(industries)],
                    "number_of_employees": 10 + index * 7,
                    "billing_city": "UAT Sample City",
                    "billing_state": "UAT Sample Region",
                    "billing_zip": f"U{index + 1:04d}",
                    "website": f"https://account{index + 1:03d}.example.test",
                    "description": "Fictional FINLONEXA UAT demonstration account.",
                    **self._audit_fields(owner),
                },
            )
            result.append(account)
        return result

    def _create_contacts(self, accounts):
        result = []
        for index in range(75):
            owner = list(self.users.values())[(index + 1) % 6]
            account = accounts[index // 3]
            contact, _ = self._get_or_create(
                Contact,
                {
                    "email": (
                        f"finlonexa_uat_02f_contact{index + 1:03d}@example.test"
                    )
                },
                {
                    "first_name": f"UAT Contact {index + 1:03d}",
                    "last_name": "Example",
                    "contact_owner": owner,
                    "contact_number": self._phone(index),
                    "address_country": "US",
                    "address_state": "UAT Sample Region",
                    "address_city": "UAT Sample City",
                    "contact_source": "partner_referral",
                    "description": "Fictional FINLONEXA UAT contact.",
                    **self._audit_fields(owner),
                },
            )
            self._get_or_create(
                ContactAccountRelationship,
                {"contact": contact, "account": account},
                self._audit_fields(owner),
            )
            result.append(contact)
        return result

    def _create_leads(self, status_map):
        result = []
        owners = list(self.users.values())
        sources = [value for value, _ in Lead.LEAD_SOURCES]
        industries = [value for value, _ in Lead.INDUSTRY_CHOICES]
        for index in range(100):
            owner = owners[index % 6]
            status = list(status_map.values())[index % len(status_map)]
            lead, _ = self._get_or_create(
                Lead,
                {"title": f"{SEED_PREFIX} Lead {index + 1:03d}"},
                {
                    "first_name": f"UAT Lead {index + 1:03d}",
                    "last_name": "Example",
                    "lead_owner": owner,
                    "email": f"lead{index + 1:03d}@finlonexa-uat-02f.example.test",
                    "contact_number": self._phone(index + 25),
                    "lead_source": sources[index % len(sources)],
                    "lead_status": status,
                    "lead_company": f"{SEED_PREFIX} Prospect {index + 1:03d}",
                    "industry": industries[index % len(industries)],
                    "country": "US",
                    "state": "UAT Sample Region",
                    "city": "UAT Sample City",
                    "zip_code": f"L{index + 1:04d}",
                    "requirements": "Fictional UAT sales inquiry; no real customer data.",
                    "created_by": owner,
                    "updated_by": owner,
                },
            )
            result.append(lead)

        asm = self.users["ASM"]
        bdo = self.users["BDO"]
        for lead in result:
            if lead.lead_owner_id == asm.pk and int(lead.title[-3:]) % 2 == 0:
                assign_lead_to_bdo(lead, asm, bdo)
                if lead.lead_owner_id != asm.pk or lead.sub_owner_id != bdo.pk:
                    raise CommandError(
                        "Lead owner/sub-owner invariant failed; transaction rolled back."
                    )
        return result

    def _create_campaigns(self):
        campaigns = []
        owners = list(self.users.values())
        today = timezone.localdate()
        campaign_types = [value for value, _ in Campaign.CAMPAIGN_TYPE_CHOICES]
        statuses = [value for value, _ in Campaign.CAMPAIGN_STATUS_CHOICES]
        for index in range(10):
            owner = owners[index % 6]
            start = today + timedelta(days=(index - 5) * 14)
            campaign, _ = self._get_or_create(
                Campaign,
                {"campaign_name": f"{SEED_PREFIX} Campaign {index + 1:02d}"},
                {
                    "campaign_owner": owner,
                    "status": statuses[index % len(statuses)],
                    "campaign_type": campaign_types[index % len(campaign_types)],
                    "start_date": start,
                    "end_date": start + timedelta(days=30),
                    "expected_revenue": Decimal(25000 + index * 5000),
                    "budget_cost": Decimal(1000 + index * 250),
                    "description": "Fictional, non-communicating UAT campaign.",
                    **self._audit_fields(owner),
                },
                ignore_changes=("start_date", "end_date"),
            )
            campaigns.append(campaign)
        return campaigns

    def _create_opportunities(self, accounts, contacts, campaigns, stage_map):
        result = []
        owners = list(self.users.values())
        stages = list(stage_map.values())
        for index in range(50):
            owner = owners[index % 6]
            account_index = index % len(accounts)
            account = accounts[account_index]
            contact = contacts[account_index * 3 + (index % 3)]
            campaign = campaigns[index % len(campaigns)]
            stage = stages[index % len(stages)]
            close_date = self._date_in_period(self.primary_period, index)
            opportunity, _ = self._get_or_create(
                Opportunity,
                {"name": f"{SEED_PREFIX} Opportunity {index + 1:03d}"},
                {
                    "email": (
                        f"opportunity{index + 1:03d}@finlonexa-uat-02f.example.test"
                    ),
                    "amount": Decimal(20000 + index * 3750),
                    "quantity": Decimal("1.00"),
                    "close_date": close_date,
                    "stage": stage,
                    "description": "Fictional FINLONEXA UAT opportunity.",
                    "next_step": "Schedule a fictional UAT review.",
                    "primary_campaign_source": campaign,
                    "owner": owner,
                    "opportunity_type": "new_customer",
                    "lead_source": "campaign",
                    "account": account,
                    **self._audit_fields(owner),
                },
                ignore_changes=("close_date",),
            )
            self._get_or_create(
                OpportunityContactRole,
                {"opportunity": opportunity, "contact": contact},
                self._audit_fields(owner),
            )
            result.append(opportunity)
        return result

    def _create_campaign_members(self, campaigns, leads, contacts):
        statuses = ["planned", "sent", "responded"]
        for index in range(50):
            campaign = campaigns[index // 5]
            owner = campaign.campaign_owner
            if index % 2 == 0:
                lookup = {
                    "campaign": campaign,
                    "lead": leads[index],
                    "member_type": "lead",
                }
                defaults = {
                    "contact": None,
                    "member_status": statuses[index % len(statuses)],
                    **self._audit_fields(owner),
                }
            else:
                contact = contacts[index]
                lookup = {
                    "campaign": campaign,
                    "contact": contact,
                    "member_type": "contact",
                }
                defaults = {
                    "lead": None,
                    "member_status": statuses[index % len(statuses)],
                    **self._audit_fields(owner),
                }
            self._get_or_create(CampaignMember, lookup, defaults)

    def _create_activities(self, accounts, contacts, leads, opportunities):
        targets = [*leads, *opportunities, *accounts, *contacts]
        content_types = {
            model: FinloContentType.objects.get_for_model(model)
            for model in (Lead, Opportunity, Account, Contact)
        }
        activities = []
        specifications = (
            ("task", 80),
            ("meeting", 25),
            ("log_call", 15),
        )
        index = 0
        for activity_type, count in specifications:
            for _ in range(count):
                owner = list(self.users.values())[index % 6]
                target = targets[index % len(targets)]
                base_date = timezone.localdate() + timedelta(days=(index % 61) - 30)
                start = timezone.make_aware(
                    datetime.combine(base_date, time(hour=9 + index % 8))
                )
                due = start + timedelta(hours=1)
                suffix = f"{index + 1:03d}"
                status = (
                    "completed"
                    if index % 5 == 0
                    else ("scheduled" if activity_type != "task" else "not_started")
                )
                fields = {
                    "subject": f"{SEED_PREFIX} {activity_type.title()} {suffix}",
                    "title": f"UAT {activity_type.title()} {suffix}",
                    "description": "Fictional UAT follow-up; no message will be sent.",
                    "activity_type": activity_type,
                    "status": status,
                    "content_type": content_types[type(target)],
                    "object_id": target.pk,
                    "owner": owner,
                    "created_by": owner,
                    "updated_by": owner,
                    "start_datetime": start,
                    "end_datetime": due,
                    "due_datetime": due,
                }
                if activity_type == "task":
                    fields["task_priority"] = ["low", "medium", "high"][index % 3]
                elif activity_type == "meeting":
                    fields.update(
                        {
                            "meeting_host": owner,
                            "is_online": False,
                            "location": "FINLONEXA UAT - fictional meeting",
                        }
                    )
                else:
                    fields.update(
                        {
                            "call_type": "outbound",
                            "call_duration_seconds": 300 + index * 10,
                            "call_duration_display": "00:05:00",
                        }
                    )
                activity, _ = self._get_or_create(
                    Activity,
                    {"subject": fields.pop("subject")},
                    fields,
                    ignore_changes=(
                        "start_datetime",
                        "end_datetime",
                        "due_datetime",
                    ),
                )
                activity.assigned_to.add(owner)
                activities.append(activity)
                index += 1
        return activities

    def _create_notes(self, accounts, contacts, leads, opportunities):
        targets = [*accounts, *contacts, *leads, *opportunities]
        model_by_label = {
            "accounts": Account,
            "contacts": Contact,
            "leads": Lead,
            "opportunities": Opportunity,
        }
        content_types = {
            model: FinloContentType.objects.get_for_model(model)
            for model in model_by_label.values()
        }
        for index in range(60):
            target = targets[index % len(targets)]
            owner = list(self.users.values())[index % 6]
            self._get_or_create(
                FinloAttachment,
                {"title": f"{SEED_PREFIX} Note {index + 1:03d}"},
                {
                    "content_type": content_types[type(target)],
                    "object_id": target.pk,
                    "file": "",
                    "description": (
                        "Fictional UAT note: "
                        f"{model_by_label[type(target)._meta.app_label].__name__} "
                        f"follow-up {index + 1:03d}; no real customer data."
                    ),
                    **self._audit_fields(owner),
                },
            )

    @staticmethod
    def _date_in_period(period, index):
        available_days = max((period.end_date - period.start_date).days, 0)
        return period.start_date + timedelta(days=index % (available_days + 1))

    @staticmethod
    def _phone(index):
        return f"+1-202-555-{100 + (index % 100):04d}"
