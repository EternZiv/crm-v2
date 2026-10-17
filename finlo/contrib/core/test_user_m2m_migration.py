import importlib

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TransactionTestCase


class UserManyToManyMigrationTests(TransactionTestCase):
    def test_legacy_user_columns_are_renamed_without_losing_relations(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="m2m-migration-user",
            password="test-password",
        )
        group = Group.objects.create(name="m2m-migration-group")
        permission = Permission.objects.create(
            name="Can test user permission migration",
            content_type=ContentType.objects.get_for_model(user_model),
            codename="test_user_permission_migration",
        )
        user.groups.add(group)
        user.user_permissions.add(permission)

        migration_module = importlib.import_module(
            "finlo.contrib.core.migrations."
            "0012_rename_user_permission_fk_columns"
        )
        relation_fields = ("groups", "user_permissions")

        with connection.schema_editor(atomic=False) as schema_editor:
            for field_name in relation_fields:
                through_model = user_model._meta.get_field(
                    field_name
                ).remote_field.through
                user_field = next(
                    field
                    for field in through_model._meta.local_fields
                    if field.is_relation
                    and field.remote_field.model._meta.label_lower
                    == user_model._meta.label_lower
                )
                schema_editor.execute(
                    f"ALTER TABLE {schema_editor.quote_name(through_model._meta.db_table)} "
                    f"RENAME COLUMN {schema_editor.quote_name(user_field.column)} "
                    "TO "
                    f"{schema_editor.quote_name('horillauser_id')}"
                )

            migration_module.rename_user_permission_fk_columns(
                apps, schema_editor
            )

        user.refresh_from_db()
        self.assertTrue(user.groups.filter(pk=group.pk).exists())
        self.assertTrue(user.user_permissions.filter(pk=permission.pk).exists())
        self.assertTrue(user.has_perm("core.test_user_permission_migration"))

    def test_remaining_user_m2m_columns_are_renamed(self):
        migration_module = importlib.import_module(
            "finlo.contrib.core.migrations."
            "0013_rename_remaining_user_m2m_columns"
        )
        target_tables = migration_module._get_target_tables(apps)
        self.assertTrue(len(target_tables) > 0)
        with connection.cursor() as cursor:
            for table_name in target_tables:
                columns = {
                    column.name
                    for column in connection.introspection.get_table_description(
                        cursor, table_name
                    )
                }
                if "finlouser_id" in columns:
                    self.assertNotIn("horillauser_id", columns)
