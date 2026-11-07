from django.db import migrations


LEGACY_USER_FK_COLUMN = "horillauser_id"
CURRENT_USER_FK_COLUMN = "finlouser_id"

TARGET_TABLES = [
    "core_shifthour_assigned_users",
    "core_holiday_specific_users",
    "reports_report_shared_with",
    "dashboard_dashboardfolder_favourited_by",
    "dashboard_dashboard_favourited_by",
    "automations_horillaautomation_also_sent_to",
    "activity_activity_assigned_to",
    "activity_activity_participants",
    "reviews_reviewrule_approver_users",
    "meeting_meetingintegrationsetting_allowed_users",
    "leads_leadassignmentcondition_assign_to_users",
    "booking_bookingpage_participants",
    "calls_callintegrationsetting_allowed_users",
]


def _get_target_tables(apps):
    tables = set(TARGET_TABLES)
    try:
        user_model = apps.get_model("core", "FinloUser")
        for model in apps.get_models():
            for field in model._meta.many_to_many:
                if (
                    field.related_model
                    and field.related_model._meta.label_lower
                    == user_model._meta.label_lower
                ):
                    through = getattr(field.remote_field, "through", None)
                    if through:
                        tables.add(through._meta.db_table)
    except Exception:
        pass
    return sorted(tables)


def rename_remaining_user_m2m_columns(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())
    tables = _get_target_tables(apps)

    with connection.cursor() as cursor:
        for table_name in tables:
            if table_name not in existing_tables:
                continue

            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, table_name
                )
            }

            has_legacy = LEGACY_USER_FK_COLUMN in columns
            has_current = CURRENT_USER_FK_COLUMN in columns

            if has_legacy and not has_current:
                schema_editor.execute(
                    f"ALTER TABLE {schema_editor.quote_name(table_name)} "
                    f"RENAME COLUMN {schema_editor.quote_name(LEGACY_USER_FK_COLUMN)} "
                    f"TO {schema_editor.quote_name(CURRENT_USER_FK_COLUMN)}"
                )


def reverse_rename_remaining_user_m2m_columns(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())
    tables = _get_target_tables(apps)

    with connection.cursor() as cursor:
        for table_name in tables:
            if table_name not in existing_tables:
                continue

            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, table_name
                )
            }

            has_legacy = LEGACY_USER_FK_COLUMN in columns
            has_current = CURRENT_USER_FK_COLUMN in columns

            if has_current and not has_legacy:
                schema_editor.execute(
                    f"ALTER TABLE {schema_editor.quote_name(table_name)} "
                    f"RENAME COLUMN {schema_editor.quote_name(CURRENT_USER_FK_COLUMN)} "
                    f"TO {schema_editor.quote_name(LEGACY_USER_FK_COLUMN)}"
                )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_rename_user_permission_fk_columns"),
    ]

    operations = [
        migrations.RunPython(
            rename_remaining_user_m2m_columns,
            reverse_rename_remaining_user_m2m_columns,
        ),
    ]
