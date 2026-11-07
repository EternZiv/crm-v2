# Model `_inherit_model` extensions

Extend existing `FinloCoreModel` subclasses from a separate app without editing the target app's migrations. Platform tests use `_inherit_model = "core.Department"`; CRM apps commonly use paths such as `leads.Lead`.

| Mechanism | Doc | Package |
|-----------|-----|---------|
| **`_inherit_model`** — add DB columns to existing models | This document (below) | `finlo/extension/models/` |
| **`_inherit_form`** — extend create/edit forms | [forms/inherit.md](../forms/inherit.md) | `finlo/extension/forms/` |
| **`_inherit_list`** — extend `FinloListView` list columns and hooks | [list/inherit.md](../list/inherit.md) | `finlo/extension/list/` |
| **`_inherit_filter`** — extend `FinloFilterSet` filtersets | [filter/inherit.md](../filter/inherit.md) | `finlo/extension/filter/` |
| **`_inherit_nav`** — extend `FinloNavView` nav bars | [nav/inherit.md](../nav/inherit.md) | `finlo/extension/nav/` |
| **`_inherit_formatter`** — extend date/time format & parse | [formatting/inherit.md](../formatting/inherit.md) | `finlo/extension/formatting/` |
| **`_inherit_view`** — extend Finlo `View` subclasses | [view/inherit.md](../view/inherit.md) | `finlo/extension/view/` |

See [Extension index](../inherit.md) for kanban, detail, and full package layout.

## Typical extension app

```text
my_lead_extensions/
├── apps.py               # AppLauncher; auto_import_modules includes "filters"
├── models.py             # _inherit_model = "leads.Lead"
├── forms.py              # _inherit_form = "finlo_crm.leads.forms.LeadSingleForm"
├── filters.py            # _inherit_filter = "finlo_crm.leads.filters.LeadFilter"
├── navbars.py            # _inherit_nav = "finlo_crm.leads.views.core.LeadNavbar"
├── lists.py              # _inherit_list = "finlo_crm.leads.views.core.LeadListView"
├── kanbans.py / details.py
└── migrations/
```

```python
# local_settings.py
INSTALLED_APPS += ["my_lead_extensions"]  # after finlo_crm.* is OK
```

## Bootstrap: models vs forms vs views

Model extensions do **not** use `ready()` for field injection; they use the metaclass and import-time migration patching. Form and view extensions are composed at startup via `bootstrap_extensions()` in `finlo/urls/project.py`, and again at runtime where needed (`resolve_form_class`, view `as_view()` wrappers).

| | **Model** | **Form** | **Filter** | **Nav** | **List** | **Kanban** | **Detail** |
|--|-----------|----------|------------|-------|----------|------------|------------|
| **Hook** | `ExtensionModelBase` | `apply_form_extensions()` | `apply_filter_extensions()` | `apply_nav_extensions()` | `apply_list_extensions()` | `apply_kanban_extensions()` | `apply_detail_extensions()` |
| **Startup** | N/A | `bootstrap_extensions()` | same | same | same | same | same |
| **Runtime** | ORM | `resolve_form_class()` | `resolve_filterset_class()` | `resolve_nav_view_class()` | `resolve_list_view_class()` | `resolve_kanban_view_class()` | `resolve_detail_view_class()` |
| **Registers when** | `models.py` | `forms.py` | `filters.py` | `navbars.py` | `lists.py` | `kanbans.py` | `details.py` |
| **Cache module** | — | `forms/cache.py` | `filter/cache.py` | `nav/cache.py` | `list/cache.py` | `kanban/cache.py` | `detail/cache.py` |

See [Extension index](../inherit.md#bootstrap) and [Registration and cache invalidation](../inherit.md#registration-and-cache-invalidation).

### Model extension flow (no `ready()` step)

1. **`finlo/contrib/core/models/base.py`** sets `metaclass=ExtensionModelBase` on `FinloCoreModel`.
2. **`import finlo.extension`** runs `_patch_migration_autodetectors()` (patches `makemigrations` / `migrate`).
3. Your app loads **`models.py`**; classes with `_inherit_model = "leads.Lead"` register with the metaclass.
4. Django registers **`leads.Lead`** → injected fields are attached to the target model.

### Form extension flow

1. Your app loads **`forms.py`**; `FormExtension` subclasses register in `FORM_EXTENSION_REGISTRY`.
2. **`finlo/urls/project.py`** calls `bootstrap_extensions()` → `apply_form_extensions(force=True)`.
3. **`FinloSingleFormView` / `FinloMultiStepFormView` / `finlo.views.generic.FormView`** call `resolve_form_class()` in `get_form_class()`.

### Filter extension flow

1. Your app loads **`filters.py`**; `FilterExtension` subclasses register in `FILTER_EXTENSION_REGISTRY`.
2. **`bootstrap_extensions()`** → `apply_filter_extensions(force=True)`.
3. **`FinloListView.get_filterset_class()`** returns `LeadFilterExtended` when registered.
4. **`_get_model_fields()`** skips names in composed `Meta.exclude` → `filter_row.html` options.

### Nav extension flow

1. Your app loads **`navbars.py`**; `NavExtension` subclasses register in `NAV_EXTENSION_REGISTRY`.
2. **`bootstrap_extensions()`** → `apply_nav_extensions(force=True)`.
3. **`FinloNavView.as_view()`** resolves `LeadNavbarExtended` on each `#navBar` HTMX request.

### List extension flow

1. Your app loads **`lists.py`**; `ListExtension` subclasses register in `LIST_EXTENSION_REGISTRY`.
2. **`bootstrap_extensions()`** → `apply_list_extensions(force=True)`.
3. **`FinloListView.as_view()`** resolves the composed list view on each HTTP request.

### Formatter extension flow

1. Your app loads **`formatters.py`**; `DateTimeFormatterExtension` subclasses register in `FORMATTER_EXTENSION_REGISTRY`.
2. **`bootstrap_extensions()`** → `apply_formatter_extensions(force=True)`.
3. Template tags call `get_datetime_formatter()` → composed `DateTimeFormatter`.

Extension authors add `models.py`, `forms.py`, `filters.py`, `lists.py`, `formatters.py`, etc., and `INSTALLED_APPS += [...]` in client settings — they do **not** edit Finlo core.

### Import note

Avoid `import finlo.extension` from `finlo/__init__.py` during early startup (`AppRegistryNotReady`). Model migration patching depends on importing `finlo.extension` via `FinloCoreModel` or `CoreConfig`.

## Architecture

See [Plan_FINLO_INHERIT_MIGRATION.md](../../../Plan_FINLO_INHERIT_MIGRATION.md) for HR → CRM mapping and design decisions.

---

# Model extension (`_inherit_model`)

Extend existing Finlo models with new database columns **without** modifying core app migrations.

**Related:** [Form extensions (`_inherit_form`)](../forms/inherit.md)

## Quick start

```python
# my_lead_extensions/models.py
from finlo.db import models
from finlo.contrib.core.models import FinloCoreModel
from finlo.utils.translation import gettext_lazy as _


class LeadExtension(FinloCoreModel):
    _inherit_model = "leads.Lead"

    industry_code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_("Industry Code"),
    )
```

```python
# my_lead_extensions/apps.py
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class MyLeadExtensionsConfig(AppLauncher):
    name = "my_lead_extensions"
    verbose_name = _("Lead Extensions")
    auto_import_modules = ["models", "forms"]  # forms if you use _inherit_form
```

```python
# local_settings.py
INSTALLED_APPS += ["my_lead_extensions"]  # after finlo_crm.leads
```

```bash
python manage.py makemigrations my_lead_extensions
python manage.py migrate
```

Migrations are written to **your extension app only** — `leads/migrations/` must not receive extension-owned DDL.

## Rules

| Topic | Rule |
|-------|------|
| Base class | `FinloCoreModel` |
| `_inherit_model` format | `"app_label.ModelName"` e.g. `"leads.Lead"` — metaclass registers lazy ops with `model_name.lower()` |
| `clean()` | Do not call `super().clean()`; target `clean()` runs first |
| App order | Extension apps **after** target app in `INSTALLED_APPS` (required for metaclass registration); use client `local_settings.py` only |
| Removal | `python manage.py migrate my_lead_extensions zero` then uninstall app |
| Imports | `from finlo.db import models`, `transaction`, `connection` as needed (not `django.db.models` / `django.db.transaction` / `django.db.connection`) |

## NOT NULL columns on existing tables

If you add a non-nullable field **without** `null=True`, **without** `db_default=`, and **without** `default=`, Django prompts for a temporary default via `MigrationQuestioner.ask_not_null_addition`.

**`FinloAutodetector`** mirrors Django’s `_generate_added_field` for injected fields (`InjectField`), including `preserve_default` and questioner calls. Older builds could pass `makemigrations` but fail `migrate` with `NOT NULL constraint failed`.

Until migrations are regenerated with the current autodetector, prefer:

```python
industry_name = models.CharField(max_length=100, default="", blank=True)
# or null=True, blank=True
```

**`unique=True`** on a new NOT NULL column with a single placeholder default (e.g. `""`) is unsafe when many rows already exist — backfill in a later migration.

## Dict attributes (e.g. `PROPERTY_LABELS`)

Plain `dict` class attributes declared directly on the extension class — not a `Field`, not callable — are merged onto the target model too (e.g. `PROPERTY_LABELS`, `SORT_FIELD_MAPPING`). If the target model already defines the same dict name on itself, the extension's entries are merged in (`{**existing, **extra}`) rather than replacing it, so multiple extension apps can each contribute labels for their own injected fields/methods without clobbering one another.

```python
class LeadExtension(FinloCoreModel):
    _inherit_model = "leads.Lead"

    PROPERTY_LABELS = {"industry_code": "Industry Code"}

    industry_code = models.CharField(max_length=20, null=True, blank=True)
```

## Overriding attributes of an existing target field (`_field_overrides`)

Some third-party models (e.g. the `login_history` pip package) don't set `verbose_name` on their fields, so Django falls back to the raw field name in exports/column labels. Rather than reaching into `TargetModel._meta.get_field(...)` directly from extension code, declare `_field_overrides` — a `{field_name: {attr: value}}` mapping — and `ExtensionModelBase` applies it the same way it applies fields/methods/dicts, via the registered `lazy_model_operation` hook:

```python
class LoginHistoryDisplayExtension(FinloCoreModel):
    _inherit_model = "login_history.LoginHistory"

    _field_overrides = {
        "ip": {"verbose_name": _("IP")},
    }
```

`_field_overrides` is a plain class attribute (not a `Field` or method), so unlike `contributed_dicts` it is read directly off the namespace rather than type-sniffed — this keeps it from colliding with a genuine dict-valued attribute an extension wants merged onto the target (e.g. `PROPERTY_LABELS`). Only attributes on an **existing** target field are overridden; it cannot add a new field (use a real `Field` attribute for that) or create a field that doesn't exist on the target (silently skipped if `get_field()` raises).

## Alter and remove injected columns

| Operation | Finlo behavior |
|-----------|------------------|
| Add column | `InjectField` in **extension** app (`_generate_added_field`) |
| Alter column | `AlterField` → `AlterInjectedField` in extension app when field is in `INJECTION_MAP` |
| Remove column | `RemoveField` → `RemoveInjectedField` in extension app |

**Never** keep `leads/migrations/000X_alter_lead_<field>.py` or `remove_lead_<field>` for injected columns — delete unapplied core-app files and regenerate under `my_lead_extensions` only.

Ownership for remove/alter is resolved from **`INJECTION_MAP`** or existing **`InjectField`** ops on disk (so you can remove the field from the extension class and still get a safe `RemoveInjectedField`).

## Implementation package (`finlo/extension/models/`)

```text
finlo/extension/
├── __init__.py              # re-exports model API; patches makemigrations/migrate
└── models/
    ├── __init__.py          # ExtensionModelBase, FinloAutodetector, InjectField, …
    ├── registry.py          # INJECTION_MAP, lookup_injection_owner()
    ├── migration_ops.py     # InjectField, AlterInjectedField, RemoveInjectedField
    ├── autodetect.py        # FinloAutodetector
    ├── metaclass.py         # ExtensionModelBase (on FinloCoreModel)
    └── tests.py
```

`FinloCoreModel` uses `metaclass=ExtensionModelBase` in `finlo/contrib/core/models/base.py`.

The metaclass treats Finlo fields (`from finlo.db import models`) as Django `Field` subclasses.

## Public API

```python
from finlo.extension import (
    ExtensionModelBase,
    EXTENSION_REGISTRY,
    INJECTION_MAP,
    InjectField,
    AlterInjectedField,
    RemoveInjectedField,
    FinloAutodetector,
)
```

## Bootstrap (models)

`FinloAutodetector` is patched when **`finlo.extension`** is imported (see [Bootstrap: models vs forms vs lists](#bootstrap-models-vs-forms-vs-lists) above). Field injection does not require `CoreConfig.ready()`.

## Pair with form, filter, and list extensions

Model `_inherit_model` adds DB columns. UI belongs in extension apps:

- [**Form extensions**](../forms/inherit.md) — `_inherit_form` on concrete CRM forms (e.g. `LeadSingleForm`)
- [**Filter extensions**](../filter/inherit.md) — `_inherit_filter` on concrete filtersets (e.g. `LeadFilter` `exclude_append` / `search_fields_append`)
- [**Nav extensions**](../nav/inherit.md) — `_inherit_nav` on concrete nav views (e.g. `LeadNavbar` `column_selector_exclude_fields_append`)
- [**List extensions**](../list/inherit.md) — `_inherit_list` on concrete list views (e.g. `LeadListView` `columns_insert`)
- [**Formatter extensions**](../formatting/inherit.md) — `_inherit_formatter` on `DateTimeFormatter`
- [**View extensions**](../view/inherit.md) — `_inherit_view` on Finlo `View` subclasses
