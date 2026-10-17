from django.db import migrations

TABLE_RENAMES = [
    # ================= CORE =================
    ("finlo_core_activetab", "core_activetab"),
    ("finlo_core_businesshour", "core_businesshour"),
    ("finlo_core_company", "core_company"),
    ("finlo_core_customerrole", "core_customerrole"),
    ("finlo_core_datedconversionrate", "core_datedconversionrate"),
    ("finlo_core_department", "core_department"),
    ("finlo_core_detailfieldvisibility", "core_detailfieldvisibility"),
    ("finlo_core_exportschedule", "core_exportschedule"),
    ("finlo_core_fieldpermission", "core_fieldpermission"),
    ("finlo_core_fiscalyear", "core_fiscalyear"),
    ("finlo_core_fiscalyearinstance", "core_fiscalyearinstance"),
    ("finlo_core_holiday", "core_holiday"),
    ("finlo_core_holiday_specific_users", "core_holiday_specific_users"),
    ("finlo_core_finloattachment", "core_horillaattachment"),
    ("finlo_core_finlouser", "core_horillauser"),
    ("finlo_core_finlouser_groups", "core_finlouser_groups"),
    ("finlo_core_finlouser_user_permissions", "core_finlouser_user_permissions"),
    ("finlo_core_importhistory", "core_importhistory"),
    ("finlo_core_kanbangroupby", "core_kanbangroupby"),
    ("finlo_core_listcolumnvisibility", "core_listcolumnvisibility"),
    ("finlo_core_multiplecurrency", "core_multiplecurrency"),
    ("finlo_core_partnerrole", "core_partnerrole"),
    ("finlo_core_period", "core_period"),
    ("finlo_core_pinnedview", "core_pinnedview"),
    ("finlo_core_quarter", "core_quarter"),
    ("finlo_core_quickfilter", "core_quickfilter"),
    ("finlo_core_recentlyviewed", "core_recentlyviewed"),
    ("finlo_core_recyclebin", "core_recyclebin"),
    ("finlo_core_recyclebinpolicy", "core_recyclebinpolicy"),
    ("finlo_core_role", "core_role"),
    ("finlo_core_role_permissions", "core_role_permissions"),
    ("finlo_core_savedfilterlist", "core_savedfilterlist"),
    ("finlo_core_teamrole", "core_teamrole"),
    ("finlo_core_timelinespanby", "core_timelinespanby"),
    # ================= ACTIVITY =================
    ("finlo_activity_activity", "activity_activity"),
    ("finlo_activity_activity_assigned_to", "activity_activity_assigned_to"),
    ("finlo_activity_activity_participants", "activity_activity_participants"),
    # ================= AUTOMATIONS =================
    ("finlo_automations_automationcondition", "automations_automationcondition"),
    ("finlo_automations_automationrunlog", "automations_automationrunlog"),
    ("finlo_automations_finloautomation", "automations_horillaautomation"),
    (
        "finlo_automations_finloautomation_also_sent_to",
        "automations_finloautomation_also_sent_to",
    ),
    # ================= CADENCES =================
    ("finlo_cadences_cadence", "cadences_cadence"),
    ("finlo_cadences_cadencecondition", "cadences_cadencecondition"),
    ("finlo_cadences_cadencefollowup", "cadences_cadencefollowup"),
    # ================= CALENDAR =================
    ("finlo_calendar_customcalendar", "calendar_customcalendar"),
    ("finlo_calendar_customcalendarcondition", "calendar_customcalendarcondition"),
    ("finlo_calendar_googlecalendarconfig", "calendar_googlecalendarconfig"),
    ("finlo_calendar_googleintegrationsetting", "calendar_googleintegrationsetting"),
    ("finlo_calendar_useravailability", "calendar_useravailability"),
    ("finlo_calendar_usercalendarpreference", "calendar_usercalendarpreference"),
    # ================= DASHBOARD =================
    ("finlo_dashboard_componentcriteria", "dashboard_componentcriteria"),
    ("finlo_dashboard_dashboard", "dashboard_dashboard"),
    ("finlo_dashboard_dashboard_favourited_by", "dashboard_dashboard_favourited_by"),
    ("finlo_dashboard_dashboardcomponent", "dashboard_dashboardcomponent"),
    ("finlo_dashboard_dashboardfolder", "dashboard_dashboardfolder"),
    (
        "finlo_dashboard_dashboardfolder_favourited_by",
        "dashboard_dashboardfolder_favourited_by",
    ),
    ("finlo_dashboard_defaulthomelayoutorder", "dashboard_defaulthomelayoutorder"),
    # ================= DUPLICATES =================
    ("finlo_duplicates_duplicaterule", "duplicates_duplicaterule"),
    ("finlo_duplicates_duplicaterulecondition", "duplicates_duplicaterulecondition"),
    ("finlo_duplicates_matchingrule", "duplicates_matchingrule"),
    ("finlo_duplicates_matchingrulecriteria", "duplicates_matchingrulecriteria"),
    # ================= KEYS =================
    ("finlo_keys_shortcutkey", "keys_shortcutkey"),
    # ================= MAIL =================
    ("finlo_mail_finlomail", "mail_horillamail"),
    ("finlo_mail_finlomailattachment", "mail_horillamailattachment"),
    ("finlo_mail_finlomailconfiguration", "mail_horillamailconfiguration"),
    ("finlo_mail_finlomailtemplate", "mail_horillamailtemplate"),
    # ================= NOTIFICATIONS =================
    ("finlo_notifications_notification", "notifications_notification"),
    (
        "finlo_notifications_notificationtemplate",
        "notifications_notificationtemplate",
    ),
    # ================= REPORTS =================
    ("finlo_reports_report", "reports_report"),
    ("finlo_reports_report_shared_with", "reports_report_shared_with"),
    ("finlo_reports_reportfolder", "reports_reportfolder"),
    # ================= THEME =================
    ("finlo_theme_companytheme", "theme_companytheme"),
    ("finlo_theme_finlocolortheme", "theme_horillacolortheme"),
]


def rename_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = connection.introspection.table_names()

    for old, new in TABLE_RENAMES:
        if old in existing_tables:
            schema_editor.execute(f'ALTER TABLE "{old}" RENAME TO "{new}";')


def reverse_rename_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = connection.introspection.table_names()

    for old, new in TABLE_RENAMES:
        if new in existing_tables:
            schema_editor.execute(f'ALTER TABLE "{new}" RENAME TO "{old}";')


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunPython(rename_tables, reverse_rename_tables),
    ]
