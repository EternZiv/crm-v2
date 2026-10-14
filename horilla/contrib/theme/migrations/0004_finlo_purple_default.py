from django.db import migrations


PURPLE_THEME = {
    "name": "Finlo Purple Theme (Default)",
    "description": "Purple theme matching the Finlo CRM brand",
    "primary_50": "#F8F8FD",
    "primary_100": "#F0F1FA",
    "primary_200": "#E6E8F7",
    "primary_300": "#D5D8F0",
    "primary_400": "#BCC1E5",
    "primary_500": "#9BA2D7",
    "primary_600": "#7C87C2",
    "primary_700": "#6873AE",
    "primary_800": "#515D98",
    "primary_900": "#38436F",
    "dark_300": "#515151",
    "secondary_400": "#BCC1E5",
    "secondary_500": "#9BA2D7",
    "secondary_600": "#7C87C2",
}

RED_THEME = {
    "name": "Coral Red Theme (Default)",
    "description": "Warm coral-red based theme",
    "primary_50": "#f6f6f6",
    "primary_100": "#FFF5F1",
    "primary_200": "#FEF6F5",
    "primary_300": "#FCEDEB",
    "primary_400": "#FBE5E1",
    "primary_500": "#F7C8C1",
    "primary_600": "#E54F38",
    "primary_700": "#ce4732",
    "primary_800": "#AC3B2A",
    "primary_900": "#672419",
    "dark_300": "#501C14",
    "secondary_400": "#FBE5E1",
    "secondary_500": "#F7C8C1",
    "secondary_600": "#E54F38",
}


def rebrand_default_theme(apps, schema_editor):
    Theme = apps.get_model("theme", "HorillaColorTheme")
    Theme.objects.filter(name=RED_THEME["name"]).update(**PURPLE_THEME)


def restore_default_theme(apps, schema_editor):
    Theme = apps.get_model("theme", "HorillaColorTheme")
    Theme.objects.filter(name=PURPLE_THEME["name"]).update(**RED_THEME)


class Migration(migrations.Migration):
    dependencies = [
        ("theme", "0003_alter_companytheme_created_at_and_more"),
    ]

    operations = [
        migrations.RunPython(rebrand_default_theme, restore_default_theme),
    ]
