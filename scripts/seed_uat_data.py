"""Seed disposable UAT database with FINLONEXA synthetic hierarchy and pipeline data."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DJANGO_SETTINGS_MODULE"] = "finlo.settings.local_uat"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import django
django.setup()

from decimal import Decimal
from django.contrib.auth.models import Permission
from finlo.auth.models import User
from finlo.contrib.core.models import (
    Company,
    Role,
    SalesAssignment,
    SalesRegion,
    SalesTeam,
)
from finlo_crm.leads.models import Lead, LeadStatus
from finlo_crm.opportunities.models import (
    FINLONEXA_OPPORTUNITY_INIT_STAGES,
    Opportunity,
    OpportunityStage,
)
from finlo_crm.contacts.models import Contact

def seed():
    print("Seeding UAT database...")

    # 1. Company
    company, _ = Company.objects.get_or_create(
        name="ELVAVEO",
        defaults={"email": "info@elvaveo.test", "country": "US"}
    )
    other_company, _ = Company.objects.get_or_create(
        name="Competitor Health",
        defaults={"email": "competitor@example.test", "country": "US"}
    )

    # 2. Roles
    roles = {}
    parent_role = None
    for key, label in Role.SALES_ROLE_CHOICES:
        role, _ = Role.all_objects.get_or_create(
            system_key=key,
            company=company,
            defaults={"role_name": str(label), "parent_role": parent_role}
        )
        roles[key] = role
        parent_role = role

    # 3. Regions & Teams
    region, _ = SalesRegion.all_objects.get_or_create(
        name="North Region",
        company=company,
        defaults={"code": "NR"}
    )
    other_region, _ = SalesRegion.all_objects.get_or_create(
        name="South Region",
        company=company,
        defaults={"code": "SR"}
    )

    # 4. Users
    def make_u(username, role_key, is_superuser=False):
        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.create_user(
                username=username,
                email=f"{username}@elvaveo.test",
                password="TestPassword123!",
                company=company,
                role=roles[role_key],
                country="US",
                is_superuser=is_superuser,
                is_staff=True,
            )
        else:
            user.set_password("TestPassword123!")
            user.role = roles[role_key]
            user.is_superuser = is_superuser
            user.is_staff = True
            user.save()
        return user

    super_admin = make_u("superadmin", "SUPER_ADMIN", is_superuser=True)
    hos = make_u("headofsales", "HEAD_OF_SALES")
    rsm = make_u("rsm_user", "RSM")
    ssm = make_u("ssm_user", "SSM")
    asm = make_u("asm_user", "ASM")
    bdo = make_u("bdo_user", "BDO")

    other_asm = make_u("other_asm", "ASM")
    other_bdo = make_u("other_bdo", "BDO")

    team, _ = SalesTeam.all_objects.get_or_create(
        code="TEAM-A",
        company=company,
        defaults={
            "name": "Team A",
            "region": region,
            "senior_sales_manager": ssm,
            "area_sales_manager": asm,
        }
    )
    team.region = region
    team.senior_sales_manager = ssm
    team.area_sales_manager = asm
    team.save()

    other_team, _ = SalesTeam.all_objects.get_or_create(
        code="TEAM-B",
        company=company,
        defaults={
            "name": "Team B",
            "region": region,
            "senior_sales_manager": ssm,
            "area_sales_manager": other_asm,
        }
    )
    other_team.region = region
    other_team.senior_sales_manager = ssm
    other_team.area_sales_manager = other_asm
    other_team.save()

    # 5. Sales Assignments
    def assign(u, reg, mgr, tm=None):
        a, _ = SalesAssignment.all_objects.get_or_create(
            user=u,
            company=company,
            defaults={
                "region": reg,
                "manager": mgr,
                "team": tm,
                "created_by": u,
                "updated_by": u,
                "is_active": True,
            }
        )
        a.region = reg
        a.manager = mgr
        a.team = tm
        a.is_active = True
        a.save()
        return a

    assign(super_admin, None, None)
    assign(hos, None, None)
    assign(rsm, region, hos)
    assign(ssm, region, rsm)
    assign(asm, region, ssm, None)
    assign(bdo, region, asm, team)

    assign(other_asm, region, ssm, None)
    assign(other_bdo, region, other_asm, other_team)

    # 6. Permissions
    all_users = [super_admin, hos, rsm, ssm, asm, bdo, other_asm, other_bdo]
    lead_perms = Permission.objects.filter(content_type__app_label="leads")
    opp_perms = Permission.objects.filter(content_type__app_label="opportunities")
    contact_perms = Permission.objects.filter(content_type__app_label="contacts")
    core_perms = Permission.objects.filter(content_type__app_label="core")

    for u in all_users:
        u.user_permissions.add(*lead_perms)
        u.user_permissions.add(*opp_perms)
        u.user_permissions.add(*contact_perms)
        u.user_permissions.add(*core_perms)

    # 7. Lead Statuses
    lead_created_st, _ = LeadStatus.all_objects.get_or_create(
        name="Lead Created",
        company=company,
        defaults={"probability": 10, "order": 1}
    )
    qualified_st, _ = LeadStatus.all_objects.get_or_create(
        name="Qualified",
        company=company,
        defaults={"probability": 40, "order": 2}
    )

    # 8. Opportunity Stages
    for conf in FINLONEXA_OPPORTUNITY_INIT_STAGES:
        OpportunityStage.objects.get_or_create(
            name=conf["name"],
            company=company,
            defaults=conf
        )

    # 9. Create some initial Leads and Opportunities
    lead1, _ = Lead.all_objects.get_or_create(
        title="Metro General Hospital System",
        company=company,
        defaults={
            "lead_owner": asm,
            "sub_owner": bdo,
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": "sarah.connor@metrohospital.test",
            "contact_number": "+1555019283",
            "lead_company": "Metro General Hospital",
            "lead_status": qualified_st,
            "customer_interest": "High - Needs immediate bed-management integration",
            "requirements": "500-bed facility requiring enterprise EHR & bed tracking",
            "country": "US",
            "created_by": asm,
        }
    )

    lead2, _ = Lead.all_objects.get_or_create(
        title="Riverside Clinic Software",
        company=company,
        defaults={
            "lead_owner": asm,
            "first_name": "David",
            "last_name": "Miller",
            "email": "dmiller@riverside.test",
            "contact_number": "+1555019299",
            "lead_company": "Riverside Clinic",
            "lead_status": lead_created_st,
            "country": "US",
            "created_by": asm,
        }
    )

    print("Synthetic data seeded successfully!")
    print("Users available:")
    print(" - superadmin / TestPassword123!")
    print(" - headofsales / TestPassword123!")
    print(" - rsm_user / TestPassword123!")
    print(" - ssm_user / TestPassword123!")
    print(" - asm_user / TestPassword123!")
    print(" - bdo_user / TestPassword123!")
    print(" - other_asm / TestPassword123!")
    print(" - other_bdo / TestPassword123!")

if __name__ == "__main__":
    seed()
