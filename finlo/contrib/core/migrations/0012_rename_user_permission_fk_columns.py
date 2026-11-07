from django.db import migrations


LEGACY_USER_FK_COLUMN = "horillauser_id"
USER_MANY_TO_MANY_FIELDS = ("groups", "user_permissions")


def rename_user_permission_fk_columns(apps, schema_editor):
    user_model = apps.get_model("core", "FinloUser")
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    for field_name in USER_MANY_TO_MANY_FIELDS:
        through_model = user_model._meta.get_field(field_name).remote_field.through
        table_name = through_model._meta.db_table
        if table_name not in existing_tables:
            raise RuntimeError(
                f"Expected user relation table {table_name!r} does not exist."
            )

        user_field = next(
            (
                field
                for field in through_model._meta.local_fields
                if field.is_relation
                and field.remote_field.model._meta.label_lower
                == user_model._meta.label_lower
            ),
            None,
        )
        if user_field is None:
            raise RuntimeError(
                f"Could not find the user foreign key in {table_name!r}."
            )

        current_column = user_field.column
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, table_name
                )
            }

        has_legacy_column = LEGACY_USER_FK_COLUMN in columns
        has_current_column = current_column in columns
        if has_legacy_column and not has_current_column:
            schema_editor.execute(
                f"ALTER TABLE {schema_editor.quote_name(table_name)} "
                f"RENAME COLUMN "
                f"{schema_editor.quote_name(LEGACY_USER_FK_COLUMN)} "
                f"TO {schema_editor.quote_name(current_column)}"
            )
        elif has_legacy_column or not has_current_column:
            raise RuntimeError(
                f"Unexpected user foreign-key columns in {table_name!r}: "
                f"expected {LEGACY_USER_FK_COLUMN!r} or {current_column!r}."
            )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_salesassignment_salesregion_salesteam_and_more"),
    ]

    operations = [
        migrations.RunPython(
            rename_user_permission_fk_columns,
            migrations.RunPython.noop,
        ),
    ]
