# Finlo Generics app — deep dive (`finlo.contrib.generics`)

The **generics** app is the shared **class-based view (CBV) framework**: list/kanban/card/detail/timeline/chart views, filter panels, single/multi-step forms, Select2 endpoints, and template tags that glue HTMX + Tailwind + permission checks.

---

## App startup (`apps.py`)

`GenericsConfig`:

| Setting | Value |
|---------|--------|
| `name` | `finlo.contrib.generics` |
| `label` | `generics` |
| `url_prefix` | `generics/` |
| `url_namespace` | `generics` |
| `auto_import_modules` | **`signals`** only |

There is **no `menu.py`** here—generics is infrastructure, not a user-facing module in the sidebar.

Signals typically wire universal behaviors (audit helpers, cache invalidation—read `signals.py`).

---

## Architectural layers

### Views (`finlo.contrib.generics.views`)

| Layer | Responsibility |
|-------|----------------|
| `FinloView` | Base shell integration; use with [settings list shell](../core/settings_list_shell.md) (`settings_list_shell.html` or `my_settings_list_shell.html`) for Settings list pages. |
| `FinloListView`, `FinloKanbanView`, `FinloCardView` | Data tables, boards, card grids with export + bulk actions. |
| `FinloDetailView`, `FinloDetailTabView`, `FinloSplitView` | Record detail, tabs, master/detail panes. |
| `FinloSingleFormView`, `FinloMultiFormView` | Create/update flows; targeted by **duplicates** `inject.py`. |
| `FinloChartView`, `FinloTimelineView`, `FinloGroupByView` | Analytics visualizations. |
| `helpers/*` | Column builders, edit-field widgets, filter list, Select2, timeline settings. |
| `toolkit/*` | Bulk delete/update/export, form mixin builders. |

Entry index: [views/views_init.md](views/views_init.md).

### Forms (`finlo.contrib.generics.forms`)

- `FinloModelForm`, `FinloMultiStepForm`, condition fields, field-permission mixin.
- `FinloModelForm.get_fieldsets()` for template-driven fieldset rendering (extensions use `fieldsets_insert`).
- Start here: [forms/forms_init.md](forms/forms_init.md).

### Formatting (`finlo.contrib.generics.formatting`)

- `DateTimeFormatter` — Gregorian **format and parse**; composed via [`_inherit_formatter`](../../extension/formatting/inherit.md).
- Details: [formatting/datetime.md](formatting/datetime.md).

### Filters

- `FinloFilterSet` + `OwnerFiltersetMixin` patterns: [filters.md](filters.md).

### Template tags (`templatetags/finlo_tags`)

- Actions, permissions, navigation, assets, dates, history: [templatetags/finlo_tags/finlo_tag_init.md](templatetags/finlo_tags/finlo_tag_init.md).

### Methods (`methods.py`)

- Server-side helpers shared across views (pagination, export, HTMX fragment selection).

---

## URL surface

`generics/` routes expose:

- Generic CRUD/list endpoints used when apps reuse stock patterns.
- **Select2** JSON endpoints under paths like `/generics/{app}/{model}/select2/` (see `views/helpers/select2.md`).

Reverse names always use namespace **`generics:`**—confirm exact names in `finlo/contrib/generics/urls.py`.

---

## Extension resolution (`finlo.extension`)

List, detail, navbar, card, kanban, form, formatter, and view layers resolve **composed subclasses** at runtime when extension apps register `_inherit_*` specs:

| View / form | Resolution |
|-------------|------------|
| `FinloListView.as_view()` | `resolve_list_view_class()` / `resolve_filterset_class()` |
| `FinloDetailView.as_view()` | `resolve_detail_view_class()` |
| `FinloNavView.as_view()` | `resolve_nav_view_class()` |
| `FinloSingleFormView` / `FinloMultiFormView` | `resolve_form_class()` in `get_form_class()` |
| `finlo.views.generic.FormView` | `resolve_form_class()` in `get_form_class()` ([generic.md](../../views/generic.md)) |
| `finlo.views.generic.View.as_view()` | `resolve_view_class()` ([view inherit](../../extension/view/inherit.md)) |
| Template date/time + list/bulk date parse | `get_datetime_formatter()` → composed `DateTimeFormatter` |

Target apps register URLs in `AppLauncher.ready()` before extension apps import `lists.py` / `details.py` / `navbars.py`; `bootstrap_extensions()` in `finlo/urls/project.py` composes all layers after `apps.ready`. See [../../extension/inherit.md](../../extension/inherit.md).

Platform code comments and tests use **core** examples (`UserFilter`, `UserFormSingle`, `UserListView`); CRM modules use the same APIs with `finlo_crm.*` targets.

---

## Cross-app integration via `_inherit_view`

Other apps extend generics declaratively, through `ViewExtension` (`_inherit_view`) targeting shared base classes — not by patching them at import time:

- **`finlo.contrib.duplicates.view_extensions`** — `DuplicateCheckSingleFormExtension`/`DuplicateCheckMultiStepFormExtension` extend `form_valid` on `FinloSingleFormView`/`FinloMultiStepFormView`; `DuplicateTabExtension` extends `_prepare_detail_tabs` on `FinloDetailTabView`; `DuplicateCheckBulkEditExtension` extends `UpdateAllFieldsView.check_before_save` (bulk Edit Details).
- **`finlo.contrib.cadences.view_extensions`** — `CadenceTabExtension` extends `_prepare_detail_tabs` on `FinloDetailTabView` to add the Cadence tab when applicable.

A registration on a shared base class (`FinloSingleFormView`, `FinloMultiStepFormView`, `FinloDetailTabView`) applies to every concrete subclass automatically — `resolve_view_class()` checks an exact match for the concrete class first, then falls back to checking each base class in its MRO. See `docs/finlo/extension/inherit.md`'s "Targeting a shared base class".

When debugging odd form/tab behavior, inspect `finlo.extension.view.registry.VIEW_EXTENSION_REGISTRY` for what's registered against a given target, or use `resolve_view_class()`'s debug helpers.

---

## How to build a new screen (checklist)

1. Subclass the narrowest Finlo view (`FinloListView`, …).
2. Set `model`, `filterset_class`, `form_class`, `template_name` (or rely on conventions).
3. Register URL under **your** app’s `urls.py` with `LoginRequiredMixin`.
4. Register model for features + permissions in **your** app’s `registration.py`.
5. Add menu item pointing at your named URL with `MAIN_CONTENT_HX_ATTRS` when embedding in shell.

---

## Documentation map (existing deep files)

- List / detail / kanban / chart / timeline: [views/](views/list.md)
- Toolkit (bulk ops): [views/toolkit/toolkit_init.md](views/toolkit/toolkit_init.md)
- Forms: [forms/](forms/generics.md)
- Date/time formatter: [formatting/datetime.md](formatting/datetime.md)
- Filters: [filters.md](filters.md)

---

## Related documentation

- Core permissions & models: [../core/core_app.md](../core/core_app.md)
- Duplicates integration: [../duplicates/duplicates.md](../duplicates/duplicates.md)
