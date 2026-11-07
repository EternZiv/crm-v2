# Settings list shell (`settings/settings_list_shell.html`)

Shared HTMX layout for **Settings → list** pages (roles, branches, lead stages, mail templates, automations, and similar). Introduced to deduplicate the repeated `#navBar` + `#mainSession` pattern across ~30 settings modules.

For **My Settings** list pages, use the companion shell [My Settings list shell](#my-settings-list-shell-my_settings_list_shellhtml) below.

---

## Admin settings shell (`settings_list_shell.html`)

Extends `settings/settings.html` and defines:

| Element | ID | HTMX load |
|---------|-----|-----------|
| Navbar partial | `#navBar` | `hx-get="{{ nav_url }}"` on `load` |
| Main content | `#mainSession` | `hx-get="{{ layout_url }}"` on `load` |

Optional query passthrough: `{{ request.GET.urlencode }}` on both requests. When the navbar filter form triggers a reload, `filter_form` is appended so the list partial can react.

```django
{% extends "settings/settings.html" %}
{% block settings %}
    <div id="{{ view_id|default:'settings-view' }}" class="h-full flex flex-col">
        {% include "messages.html" %}
        <div id="navBar" hx-get="{{ nav_url }}?..." hx-trigger="load"></div>
        <div id="mainSession" hx-get="{{ layout_url }}?..." hx-trigger="load"></div>
    </div>
{% endblock %}
```

---

## My Settings list shell (`my_settings_list_shell.html`)

Same HTMX contract as the admin shell, but extends **`settings/my_settings.html`** and fills the **`{% block my_settings %}`** slot (sidebar profile + my-settings menu).

| Element | Notes |
|---------|--------|
| Root id | `{{ view_id|default:'my-settings-view' }}` |
| `#navBar` / `#mainSession` | Same as admin shell; uses `layout_url` from `FinloView.get_layout_url()` |

### Views using `my_settings_list_shell.html` (v1.13.8)

| View | Module | `view_id` (when set) |
|------|--------|----------------------|
| `ShortKeyView` | `finlo.contrib.keys` | — |
| `UserHolidayView` | `finlo.contrib.core` | — |
| `UserLoginHistoryView` | `finlo.contrib.core` | — |
| `OpportunityTeamView` | `finlo_crm.opportunities` | — |

Example:

```python
class UserLoginHistoryView(LoginRequiredMixin, FinloView):
    template_name = "settings/my_settings_list_shell.html"
    nav_url = reverse_lazy("core:user_login_history_nav")
    list_url = reverse_lazy("core:user_login_history_list")
```

Do **not** copy `#navBar` / `#mainSession` into a per-app wrapper template — point `template_name` at one of the two shells.

---

## View wiring (`FinloView`)

Subclass **`FinloView`** and set:

| Attribute | Required | Purpose |
|-----------|----------|---------|
| `template_name` | Yes | `"settings/settings_list_shell.html"` or `"settings/my_settings_list_shell.html"` |
| `nav_url` | Yes | HTMX endpoint for navbar (`FinloNavView`) |
| `list_url` | Usually | Default layout loaded into `#mainSession` |
| `view_id` | Recommended | Stable root element id (e.g. `leads-status-view`) |

`FinloView.get_layout_url()` picks `list_url`, or another layout URL when `?layout=` is present (kanban, group_by, etc.). Settings pages typically expose only `list_url`.

### Example (lead stages — admin settings)

```python
class LeadsStageView(LoginRequiredMixin, FinloView):
    template_name = "settings/settings_list_shell.html"
    view_id = "leads-status-view"
    nav_url = reverse_lazy("leads:lead_stage_nav_view")
    list_url = reverse_lazy("leads:lead_stage_list_view")
```

### Example (matching rules — core contrib)

```python
class MatchingRulesView(LoginRequiredMixin, FinloView):
    template_name = "settings/settings_list_shell.html"
    view_id = "matching-rules-view"
    nav_url = reverse_lazy("duplicates:matching_rules_nav")
    list_url = reverse_lazy("duplicates:matching_rules_list")
```

---

## Modules using the admin shell (v1.13.8)

Includes: `finlo.contrib.core` (roles, branches, departments, recycle bin, team/partner/customer roles), `finlo.contrib.mail`, `finlo.contrib.notifications`, `finlo.contrib.automations`, `finlo.contrib.workflow`, `finlo.contrib.cadences`, `finlo.contrib.duplicates`, `finlo.contrib.process`, and CRM apps (`leads`, `opportunities`, `forecast`, `scoring_rules`).

When adding a new **admin** settings list page, use `settings_list_shell.html`. For **My Settings** lists, use `my_settings_list_shell.html`.

---

## Empty states on settings pages

Prerequisite and no-data UI on settings shells often uses [shared empty-state partials](../../../templates/components/empty_state.md) (`activate_company.html` or `empty_state.html`) instead of inline SVG markup.

---

## Related documentation

- [`FinloView`](../generics/views/core.md#-finloview)
- [Core app index](core_app.md)
- [My Settings menu](../menu/my_settings_menu.md)
- [Empty-state partials](../../../templates/components/empty_state.md)
