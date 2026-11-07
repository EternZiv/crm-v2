Repository coding rules. Add new topics as additional `##` sections below.

---

## Avoid direct Django usage

Finlo re-exports common Django APIs under `finlo.*` packages so app code has one consistent import path.

**Rule:** If Finlo exposes the symbol (see table below), import from Finlo. If not, import from Django or the third-party package as usual.

| Situation | Import from |
|-----------|-------------|
| Symbol listed in a Finlo package below | `finlo.<package>` |
| Symbol not re-exported by Finlo | `django.*` (or third-party) |
| Code that implements the re-export | `django.*` only inside the Finlo wrapper module |

### Finlo import map (use these instead of Django)

#### Database & ORM

| Import from | Instead of | Symbols (common) |
|-------------|------------|------------------|
| `finlo.db` | `django.db` | `models`, `transaction`, `connection` |
| `finlo.db.models.signals` | `django.db.models.signals` | `post_save`, `pre_save`, `post_delete`, `m2m_changed`, … |
| `finlo.db.models` | `django.db.models` | `Q`, `F`, `Count`, `ForeignKey`, … (via `finlo.db.models` re-export) |

Details: [docs/finlo/contrib/core/models.md](finlo/contrib/core/models.md)

#### HTTP, views, URLs

| Import from | Instead of | Symbols (common) |
|-------------|------------|------------------|
| `finlo.web` | `django.http` | `HttpResponse`, `JsonResponse`, `QueryDict`, `Http404`, `StreamingHttpResponse`, `HttpNotFound`, `RedirectResponse`, … |
| `finlo.views.generic` | `django.views.generic` | `FormView`, `View`, `TemplateView`, `ListView`, `DetailView` |
| `finlo.shortcuts` | `django.shortcuts` | `redirect`, `render`, `get_object_or_404` |
| `finlo.urls` | `django.urls` | `path`, `re_path`, `include`, `reverse`, `reverse_lazy`, `resolve` |

> **Note:** The platform package was renamed from `finlo.http` to **`finlo.web`**. The old name shadowed Python’s standard-library `http` module when Django management commands ran from inside the `finlo/` directory (for example `makemessages`). Update any remaining `from finlo.http import …` imports to `from finlo.web import …`. Do not keep a `finlo/http/` compatibility shim — it would restore the import conflict.

Details: [docs/finlo/web/web.md](finlo/web/web.md), [docs/finlo/shortcuts/shortcuts.md](finlo/shortcuts/shortcuts.md), [docs/finlo/urls/urls.md](finlo/urls/urls.md)

#### Apps, auth, exceptions

| Import from | Instead of | Symbols (common) |
|-------------|------------|------------------|
| `finlo.apps` | `django.apps` | `AppLauncher`, `AppConfig`, `apps` (registry) |
| `finlo.auth.models` | `django.contrib.auth.models` | `User` (wraps `AUTH_USER_MODEL`) |
| `finlo.core.exceptions` | `django.core.exceptions` | `ValidationError`, `PermissionDenied`, `ObjectDoesNotExist`, … |

Details: [docs/finlo/apps/apps.md](finlo/apps/apps.md), [docs/finlo/contrib/core/user_model.md](finlo/contrib/core/user_model.md), [docs/finlo/core/exceptions.md](finlo/core/exceptions.md)

#### Utilities (i18n, time, HTML, text, functional, decorators)

| Import from | Instead of | Symbols (common) |
|-------------|------------|------------------|
| `finlo.utils.translation` | `django.utils.translation` | `gettext_lazy`, `gettext`, `ngettext_lazy`, `activate`, `override`, … |
| `finlo.utils` or `finlo.utils.timezone` | `django.utils.timezone` | `timezone.now()`, `make_aware`, `localtime`, `UTC`, … |
| `finlo.utils.html` | `django.utils.html` | `format_html`, `format_html_join`, `escape`, `strip_tags`, `conditional_escape`, … |
| `finlo.utils.text` | `django.utils.text` | `slugify`, `Truncator`, `capfirst`, `get_valid_filename`, … |
| `finlo.utils.functional` | `django.utils.functional` | `cached_property`, `lazy`, `Promise`, `SimpleLazyObject`, … |
| `finlo.utils.decorators` | `django.utils.decorators` + custom | `method_decorator`, `permission_required`, `htmx_required`, `db_initialization`, … |

Details: [docs/finlo/utils/translation.md](finlo/utils/translation.md), [docs/finlo/utils/html.md](finlo/utils/html.md), [docs/finlo/utils/text.md](finlo/utils/text.md), [docs/finlo/utils/functional.md](finlo/utils/functional.md), [docs/finlo/utils/utils.md](finlo/utils/utils.md), [docs/finlo/utils/decorators.md](finlo/utils/decorators.md)

#### Framework types (not Django re-exports — still use Finlo)

| Import from | Role |
|-------------|------|
| `finlo.contrib.core.models` | `FinloCoreModel`, `CompanyFilteredManager`, … |
| `finlo.contrib.generics` | `FinloListView`, `FinloModelForm`, … |
| `finlo.menu` | `floating_menu`, `main_section_menu`, … |
| `finlo.registry.feature` | `register_model_for_feature`, `FEATURE_REGISTRY` |

When adding a new Finlo wrapper, document it under `docs/finlo/<package>/` and add a row to the tables above.

### Examples

```python
# ❌ Avoid when Finlo re-exports the symbol
from django.db import models, transaction
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.apps import apps

# ✅ Prefer — Finlo import map
from finlo.db import models, transaction
from finlo.web import HttpResponse
from finlo.urls import reverse_lazy
from finlo.shortcuts import render, redirect
from finlo.utils.translation import gettext_lazy as _
from finlo.utils import timezone
from finlo.utils.html import format_html, escape
from finlo.utils.text import slugify
from finlo.utils.functional import cached_property
from finlo.core.exceptions import ValidationError
from finlo.auth.models import User
from finlo.apps import apps, AppLauncher
from finlo.utils.decorators import permission_required, htmx_required

# ✅ OK — not wrapped by Finlo (use Django directly)
from django.db import IntegrityError, migrations
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import close_old_connections
```

### Still import from Django when Finlo does not wrap it

Examples (not exhaustive):

- `LoginRequiredMixin`, `DeleteView`, other CBV bases not re-exported
- `IntegrityError`, `migrations`, `close_old_connections`
- Third-party: `djmoney`, `rest_framework`, Channels, etc.
- Migration files: `from django.db import migrations`

### Exceptions (intentional `django.*` imports)

- **Migrations** — `from django.db import migrations` in `migrations/*.py` only.
- **Early bootstrap** — e.g. `finlo/extension/models/metaclass.py` uses Django `Field` only (no `finlo.db` at import time) to avoid `AppRegistryNotReady`; see [docs/Plan_FINLO_INHERIT_MIGRATION.md](Plan_FINLO_INHERIT_MIGRATION.md).
- **Re-export implementation** — only the Finlo wrapper module (e.g. `finlo/db/__init__.py`, `finlo/web/__init__.py`) may import the symbol from Django.
- **Gaps** — any symbol not in the Finlo package’s `__all__` / docs stays on Django.

### Import order and section comments

Group imports in this order. Use the **exact** section headers below so reviewers and tools can scan files consistently.

| Order | Section header | What goes here |
|-------|----------------|----------------|
| 1 | `# Standard library imports` | `import os`, `from pathlib import Path`, … |
| 2 | `# Third-party imports (Django)` | `django.*` only (symbols **not** re-exported by Finlo) |
| 3 | `# Third-party imports (other)` | Optional — `rest_framework`, `djmoney`, `celery`, … |
| 4 | `# First party imports (Finlo)` | **Every** `from finlo…` / `import finlo…` import |
| 5 | `# Local imports` | Same-app modules — relative imports (`.models`, `.forms`) or `finlo_crm.*` / client extension apps |

**Mandatory:** Any import whose top-level package is `finlo` (`finlo.db`, `finlo.contrib.*`, `finlo_crm` does **not** apply — that is CRM app code, usually under **Local imports**) must appear only under `# First party imports (Finlo)`, never under Django or third-party blocks.

Within **stdlib**, **Django**, and **other** sections, sort imports alphabetically by module path.

Within **`# First party imports (Finlo)`**, use **two sub-blocks** (do not mix):

| Sub-order | Packages | Notes |
|-----------|----------|--------|
| **1 — Platform** | `finlo.apps`, `finlo.auth`, `finlo.core`, `finlo.db`, `finlo.web`, `finlo.menu`, `finlo.registry`, `finlo.shortcuts`, `finlo.urls`, `finlo.utils`, … | Top-level Finlo infrastructure — **not** `finlo.contrib` |
| **2 — Contrib apps** | `finlo.contrib.*` | Always **last** in the Finlo block; contrib is a bundle of finlo apps (core, generics, mail, …) |

Sort **alphabetically by full module path** inside each sub-block. Typical platform order (all before any `finlo.contrib` line):

```text
finlo.apps → finlo.auth → finlo.core → finlo.db → finlo.web → finlo.menu
→ finlo.registry → finlo.shortcuts → finlo.urls → finlo.utils → …
```

#### Example (correct)

```python
# Standard library imports
import json
import logging

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.views.generic import DeleteView

# Third-party imports (other)
from djmoney.models.fields import MoneyField

# First party imports (Finlo)
from finlo.apps import apps
from finlo.auth.models import User
from finlo.db import models, transaction
from finlo.web import HttpResponse
from finlo.views.generic import View
from finlo.shortcuts import redirect, render
from finlo.urls import reverse_lazy
from finlo.utils import timezone
from finlo.utils.decorators import permission_required
from finlo.utils.translation import gettext_lazy as _
from finlo.contrib.core.models import FinloCoreModel
from finlo.contrib.generics.views import FinloListView

# Local imports
from .models import Lead
```

#### Anti-pattern (wrong)

```python
# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin
from finlo.db import transaction  # ❌ finlo.* must not be in Django block

# First party imports (Finlo)
from finlo.contrib.generics.views import FinloListView  # ❌ contrib before platform
from finlo.db import models
```

Use `# First party imports (Finlo)` (not `First party / Finlo` or other variants) in new and touched files.

See also [.claude/rules/finlo-coding-style.md](../.claude/rules/finlo-coding-style.md).

### Reviewer checklist

- [ ] All `finlo.*` imports are under `# First party imports (Finlo)` only.
- [ ] Within First party: platform (`finlo.db`, `finlo.auth`, `finlo.web`, …) before `finlo.contrib.*`.
- [ ] Django block contains only `django.*` (and no `finlo.*`).
- [ ] Database: `models`, `transaction`, `connection`, and model signals use `finlo.db` / `finlo.db.models.signals`.
- [ ] HTTP/views: responses and shortcuts use `finlo.web` / `finlo.shortcuts` when listed above.
- [ ] URLs: `path`, `reverse`, `reverse_lazy` use `finlo.urls`.
- [ ] i18n / time / HTML / text / functional / decorators: use `finlo.utils.translation`, `finlo.utils.timezone` (or `from finlo.utils import timezone`), `finlo.utils.html`, `finlo.utils.text`, `finlo.utils.functional`, `finlo.utils.decorators`.
- [ ] User model and registry: `finlo.auth.models.User`, `finlo.apps.apps` — not `django.contrib.auth.models.User`.
- [ ] Exceptions: `finlo.core.exceptions` — not `django.core.exceptions` for re-exported types.
- [ ] Re-raised exceptions use `raise NewError(...) from exc` when translating caught errors (see [Exception chaining](#exception-chaining-raise--from)).
- [ ] `@cached_property` values are read via accessor methods or explicit resolution — not passed as descriptors into ORM filters (see [`@cached_property` on views](#cached_property-on-views)).
- [ ] Templates omit redundant `{% load static %}`, `{% load i18n %}`, and `{% load finlo_tags %}` (see [Django templates — built-in tag libraries](#django-templates--built-in-tag-libraries)).
- [ ] New direct `django.*` imports are justified (not in Finlo map) or documented.

---

## Exception chaining (`raise ... from`)

When handling a caught exception and raising a different one (validation error, `HttpNotFound`, `ValueError`, serializer error), chain the cause:

```python
except ValueError as exc:
    raise forms.ValidationError(_("Invalid JSON file.")) from exc
```

Do **not** swallow the original exception unless the handler fully recovers. Details and examples: [docs/finlo/core/exceptions.md](docs/finlo/core/exceptions.md#exception-chaining-raise--from).

---

## `@cached_property` on views

`finlo.utils.functional.cached_property` (re-export of Django’s helper) caches a **computed value** on the instance. The attribute name is not the value itself.

```python
@cached_property
def get_company_for_user(self):
    return self.request.active_company or Company.objects.filter(...).first()

def company_for_user(self):
    """Return the resolved company (or None)."""
    return self.get_company_for_user
```

| Pattern | Guidance |
|---------|----------|
| ORM filters / FK assignment | `company = self.company_for_user()` then `if company is not None:` |
| Boolean tests | Prefer `if company is not None:` over `if company:` when pylint W0125 flags constant-test false positives on ternaries |
| Currency / display fallbacks | Initialize default, then assign inside `if company is not None:` |

Example (forecast views): [docs/finlo_crm/forecast/forecast_type_tab.md](docs/finlo_crm/forecast/forecast_type_tab.md#forecasttypetabmixin--cached-context-accessors).

---

## Django templates — built-in tag libraries

Finlo registers common template tag libraries globally via `BUILTINS` in [`finlo/settings/base.py`](../finlo/settings/base.py). They are passed to Django as `OPTIONS["builtins"]` on the template engine.

**Rule:** Do **not** add `{% load static %}`, `{% load i18n %}`, or `{% load finlo_tags %}` at the top of templates. Those libraries are already available in every template.

| Built-in library | Provides (common) |
|------------------|-------------------|
| `django.templatetags.static` | `{% static %}`, `{% get_static_prefix %}`, … |
| `django.templatetags.i18n` | `{% trans %}`, `{% blocktrans %}`, `{% get_current_language %}`, … |
| `finlo.contrib.generics.templatetags.finlo_tags` | `{% has_perm %}`, `{% is_active %}`, `{% display_field_value %}`, … |

Other tag libraries (e.g. `{% load finlo_call_tags %}`, app-specific libraries) are **not** built in — use `{% load … %}` only when you need tags from those modules.

### Examples

```django
{# ✅ OK — no {% load %} needed for static, i18n, or finlo_tags #}
<img src="{% static 'assets/img/activate-company.svg' %}" alt="{% trans 'Activate company' %}">
{% has_perm "core.view_company" as can_view_company %}

{# ❌ Avoid — redundant with BUILTINS #}
{% load static %}
{% load i18n %}
{% load finlo_tags %}
```

```django
{# ✅ OK — library not in BUILTINS #}
{% load finlo_call_tags %}
{% calls_enabled as calls_active %}
```

### Reviewer checklist

- [ ] New or touched templates do not add `{% load static %}`, `{% load i18n %}`, or `{% load finlo_tags %}` unless removing legacy lines during a refactor.
- [ ] `{% load … %}` is present only for tag libraries outside `BUILTINS`.
- [ ] Prerequisite / no-data screens use [empty_state partials](templates/components/empty_state.md) instead of duplicating SVG markup.

---

## Naming

Conventions for **functions**, **classes**, and **variables**. Follow PEP 8 unless a rule below overrides it.

**Related docs**

- Import map and section headers: [Avoid direct Django usage](#avoid-direct-django-usage) (same file)
- Extension system: [docs/finlo/extension/inherit.md](docs/finlo/extension/inherit.md)
- ORM / `finlo.db`: [docs/finlo/contrib/core/models.md](docs/finlo/contrib/core/models.md)
- Commit format: [CLAUDE.md](CLAUDE.md) (`[ADD/FIX/UPDT/REMOVE] SECTION: description`)

### General Python style

| Kind | Style | Example |
|------|--------|---------|
| **Classes** | `PascalCase` | `LeadListView`, `FormExtension` |
| **Functions / methods** | `snake_case` | `resolve_list_view_class`, `bootstrap_extensions` |
| **Variables / attributes** | `snake_case` | `target_path`, `composed_map` |
| **Constants** | `UPPER_SNAKE_CASE` | `LIST_EXTENSION_REGISTRY`, `FORM_COMPOSED_MAP` |
| **Modules / packages** | `snake_case` | `metaclass.py`, `finlo_crm` |
| **Private (module)** | Leading `_` | `_patch_migration_autodetectors` |
| **Django apps** | `snake_case` package name | `my_lead_extensions`, `finlo_crm.leads` |

Avoid abbreviations unless they are domain-standard (`pk`, `fk`, `url`, `htmx`).

### The `Finlo` prefix — when to use it

The package is already named `finlo`. **Do not repeat `Finlo` in every symbol** inside `finlo/` when the import path or base class already makes the context clear.

#### Omit redundant `Finlo` (preferred inside `finlo/`)

Use short, domain-specific names:

| Do | Do not |
|----|--------|
| `ListExtension` | `FinloListExtension` |
| `DetailExtension` | `FinloDetailExtension` |
| `FormExtension` | `FinloFormExtension` |
| `bootstrap_extensions()` | `bootstrap_finlo_extensions()` |
| `_is_list_extension` | `_is_finlo_list_extension` |
| `_is_form_extension` | `_is_finlo_form_extension` |
| `apply_list_extensions()` | `apply_finlo_list_extensions()` |

#### Keep `Finlo` for established framework types

These names are public API across apps and templates. **Do not rename** for consistency with generics, core, and docs:

| Keep as-is | Role |
|------------|------|
| `FinloCoreModel` | Base model (`finlo.contrib.core`) |
| `FinloListView`, `FinloDetailView`, … | Generic CBVs (`finlo.contrib.generics`) |
| `FinloModelForm`, `FinloFormMixin` | Form stack |
| `FinloFilterSet` | Filters |
| `FinloUser` | Auth user model |

**Rule of thumb:** If the symbol lives in `finlo.contrib.*` and is imported by many CRM apps, it likely keeps the `Finlo` prefix. If it lives in `finlo.extension.*` or other internal platform code added for extensions, prefer the short name.

#### Client / third-party extension apps

Extension apps (e.g. `my_lead_extensions`) sit **outside** `finlo/`:

- **Classes:** describe the target + role — `LeadListExtension`, `LeadSingleFormExtension`, `LeadExtension` (model).
- **Do not** prefix every class with `Finlo` — the app is already Finlo-specific.
- **Functions:** `snake_case` helpers — `_clean_industry_code_value`, `_make_industry_optional` (module-private with `_`).

### Classes

#### Views and forms (CRM modules)

```python
# Good — matches finlo_crm patterns
class LeadListView(LoginRequiredMixin, FinloListView):
    ...

class LeadSingleForm(FinloModelForm):
    ...
```

#### Extension registration classes

Subclass the platform base and set the registration attribute on the class body:

```python
from finlo.extension.list import ListExtension

class LeadListExtension(ListExtension):
    _inherit_list = "finlo_crm.leads.views.core.LeadListView"
    columns_insert = [("industry", "industry_code")]
```

```python
# Kanban — see docs/finlo/extension/kanban/inherit.md
from finlo.extension.kanban import KanbanExtension

class LeadKanbanExtension(KanbanExtension):
    _inherit_kanban = "finlo_crm.leads.views.core.LeadKanbanView"
```

```python
# Detail — see docs/finlo/extension/detail/inherit.md
from finlo.extension.detail import DetailExtension

class LeadDetailExtension(DetailExtension):
    _inherit_detail = "finlo_crm.leads.views.core.LeadDetailView"
```

```python
from finlo.extension.forms import FormExtension

class LeadSingleFormExtension(FormExtension):
    _inherit_form = "finlo_crm.leads.forms.LeadSingleForm"
```

```python
from finlo.extension.filter import FilterExtension

class LeadFilterExtension(FilterExtension):
    _inherit_filter = "finlo_crm.leads.filters.LeadFilter"
    search_fields_append = ["industry_code"]
```

```python
from finlo.extension.nav import NavExtension

class LeadNavbarExtension(NavExtension):
    _inherit_nav = "finlo_crm.leads.views.core.LeadNavbar"
    column_selector_exclude_fields_append = ["industry_code"]
```

```python
from finlo.contrib.core.models import FinloCoreModel

class LeadExtension(FinloCoreModel):
    _inherit_model = "leads.Lead"
```

#### Composed runtime classes

Platform-generated classes may carry **marker attributes** (do not use these names on hand-written classes):

| Attribute | Meaning |
|-----------|---------|
| `__finlo_list_composed__` | Composed list view |
| `__finlo_list_path__` | Original list view import path |
| `__wrapped_list_view__` | Core list view behind composed list |
| `__finlo_kanban_composed__` | Composed kanban view |
| `__finlo_kanban_path__` | Original kanban view import path |
| `__wrapped_kanban_view__` | Core kanban view behind composed kanban |
| `__finlo_detail_composed__` | Composed detail view |
| `__finlo_detail_path__` | Original detail view import path |
| `__wrapped_detail_view__` | Core detail view behind composed detail |
| `__finlo_composed__` | Composed form |
| `__finlo_form_path__` | Original form import path |
| `__finlo_filter_path__` | Original filterset import path |
| `__wrapped_filter__` | Core filterset behind composed filter |
| `__finlo_nav_composed__` | Composed nav view |
| `__finlo_nav_path__` | Original nav view import path |
| `__wrapped_nav_view__` | Core nav view behind composed nav |

#### App config

```python
class MyLeadExtensionsConfig(AppLauncher):  # PascalCase + Config suffix
    name = "my_lead_extensions"
```

### Functions

| Rule | Example |
|------|---------|
| **Verbs** for actions | `apply_list_extensions`, `resolve_form_class`, `compose_list_view_class` |
| **get_** for accessors | `get_list_extensions`, `get_form_extensions`, `get_filter_extensions` |
| **get_filterset_class** on list views | Resolves composed filterset (`LeadFilterExtended`) |
| **is_ / has_** for booleans | `is_composed_view`, checks in validators |
| **setup_*_extension** for extension hooks | `setup_list_view_extension`, `setup_nav_view_extension`, `setup_filter_extension` |
| **clean_<field>** on forms | `clean_industry_code` |
| **No** `Finlo` in new platform helpers under `finlo/extension/` | `bootstrap_extensions()` not `bootstrap_finlo_extensions()` |

Module-level “script” helpers in extension apps may use a leading `_` if not part of the public API.

### Variables and attributes

#### Registration and hook attributes (extensions)

Use the **declared hook names** exactly — the metaclass reads these class attributes:

| Mechanism | Registration key | Hook examples |
|-----------|------------------|---------------|
| Model | `_inherit_model` | field names on class body |
| Form | `_inherit_form` | `field_order_insert`, `step_fields_append`, `fields_append` |
| Filter | `_inherit_filter` | `exclude_append` (filter panel dropdown), `search_fields_append`, `fields_append` |
| Nav | `_inherit_nav` | `actions_append`, `custom_view_type_update`, `column_selector_exclude_fields_append` |
| List | `_inherit_list` | `columns_insert`, `bulk_update_fields_append` |

Optional on extension classes:

- `_extension_priority` — `int`, lower runs earlier in merge order.

#### Django model / view conventions

| Use | Name |
|-----|------|
| Model Meta | `class Meta:` with `verbose_name`, `ordering` |
| Managers | `objects` (company-filtered), `all_objects` (unfiltered) |
| Owner filtering | `OWNER_FIELDS = ["lead_owner"]` |
| URL names | `snake_case` — `lead_list`, `lead_detail` |
| `app_name` | package segment — `leads`, `opportunities` |

#### User-facing labels — Title Case

English **`verbose_name`**, **`verbose_name_plural`**, and form **`label`** strings must be **Title Case**. Wrap them with `gettext_lazy` (`_()`). This applies to:

- Field `verbose_name` on models
- `Meta.verbose_name` and `Meta.verbose_name_plural`
- Explicit form field `label=` (and related user-facing captions such as `help_text` only when it is a short label, not a sentence)

Capitalize each significant word. Do not use sentence case, all-lowercase, or all-caps.

```python
# ✅ Title Case
name = models.CharField(max_length=100, verbose_name=_("Forecast Type Name"))

class Meta:
    verbose_name = _("Forecast Type")
    verbose_name_plural = _("Forecast Types")

team = forms.ModelChoiceField(queryset=..., label=_("Select Team"))

# ❌ Sentence case / lowercase
verbose_name = _("forecast type name")
verbose_name = _("Forecast type name")
label = _("select team")
```

Keep small connecting words in Title Case when they are part of the label (`To`, `Of`, `And`) unless an existing product string already uses a fixed phrase — prefer matching nearby labels in the same module.

#### Naming — reviewer checklist (labels)

- [ ] Model field `verbose_name` is Title Case inside `_("…")`.
- [ ] `Meta.verbose_name` and `Meta.verbose_name_plural` are Title Case.
- [ ] Form `label=` values are Title Case.

#### Registries and maps (platform)

`UPPER_SNAKE_CASE` for module-level registries:

- `LIST_EXTENSION_REGISTRY`, `LIST_COMPOSED_MAP`
- `FORM_EXTENSION_REGISTRY`, `FORM_COMPOSED_MAP`
- `INJECTION_MAP` (model field injection)

#### Request / instance state

`snake_case` on `self` — `self.request`, `self.object`, `self.columns`.

### Import paths and string references

Extension `_inherit_*` values are **full dotted paths** to an existing class:

```python
_inherit_list = "finlo_crm.leads.views.core.LeadListView"
_inherit_form = "finlo_crm.leads.forms.LeadSingleForm"
_inherit_model = "leads.Lead"  # app_label.ModelName for models only
```

- Use the real module path from the codebase (MCP `search_codebase` / `get_url_map` before guessing).
- Model `_inherit_model` uses `"app_label.ModelName"`, not the full module path.

### Naming — reviewer checklist

- [ ] New code under `finlo/extension/` avoids redundant `Finlo*` on classes and functions.
- [ ] Public framework types in `finlo.contrib.*` keep existing `Finlo*` names.
- [ ] Extension apps use `*Extension` class names and `_inherit_model` / `_inherit_form` / `_inherit_list`.
- [ ] Functions and variables are `snake_case`; constants are `UPPER_SNAKE_CASE`.
- [ ] `verbose_name`, `verbose_name_plural`, and form `label` strings are Title Case (see [User-facing labels](#user-facing-labels--title-case)).
- [ ] No new `FinloFinlo*` or duplicated prefix typos.
- [ ] Client-only apps are registered via `local_settings.py` (`INSTALLED_APPS += [...]`), not by editing `finlo/settings/base.py` unless you are core maintainers.

### Naming — examples

```python
# Platform (finlo/extension/bootstrap.py)
def bootstrap_extensions() -> None: ...

# Platform (finlo/extension/list/metaclass.py)
class ListExtension: ...

# CRM view (finlo_crm)
class LeadListView(LoginRequiredMixin, FinloListView): ...

# Client extension (my_lead_extensions/lists.py)
class LeadListExtension(ListExtension):
    _inherit_list = "finlo_crm.leads.views.core.LeadListView"
```

When in doubt: **match the nearest existing file in the same package**, then check [docs/finlo/extension/inherit.md](docs/finlo/extension/inherit.md).

---

## Field renames / removals — review stored field-name references

Several Finlo models **persist field names as strings** in the database (visibility prefs, permissions, filters, automations, archived snapshots, etc.). Renaming, removing, or changing a model field’s definition can leave those rows pointing at obsolete names and break UI, filters, permissions, or workflows at runtime.

**Rule:** Whenever **any model field is updated** (renamed, removed, or its behavior/definition is changed), review the models below and their related logic so stored field-name references stay valid. Plan data migrations or cleanup when existing rows would break.

### Models that store field names

| Model | Location | Notes |
|-------|----------|--------|
| `ListColumnVisibility` | [`finlo/contrib/core/models/visibility.py`](../finlo/contrib/core/models/visibility.py) (~L16) | List column visibility |
| `DetailFieldVisibility` | [`finlo/contrib/core/models/visibility.py`](../finlo/contrib/core/models/visibility.py) (~L62) | Detail field visibility |
| `FieldPermission` | [`finlo/contrib/core/models/user.py`](../finlo/contrib/core/models/user.py) (~L342) | Per-field permissions |
| `SavedFilterList`, `KanbanGroupBy`, `TimelineSpanBy`, `QuickFilter` | [`finlo/contrib/core/models/filters.py`](../finlo/contrib/core/models/filters.py) | Saved filters / group-by / span-by |
| `RecycleBin` | [`finlo/contrib/core/models/recyclebin.py`](../finlo/contrib/core/models/recyclebin.py) (~L25) | Archived JSON snapshot of records |
| `ImportHistory`, `ExportSchedule` | [`finlo/contrib/core/models/import_export.py`](../finlo/contrib/core/models/import_export.py) | Import/export field mappings & schedules |
| `FinloAutomation`, `AutomationCondition` | [`finlo/contrib/automations/models.py`](../finlo/contrib/automations/models.py) | Automation triggers & conditions |
| `WorkflowCondition`, `WorkflowTimeTriggerAction` | [`finlo/contrib/workflow/models.py`](../finlo/contrib/workflow/models.py) | Workflow conditions & time-trigger actions |
| `CadenceCondition` | [`finlo/contrib/cadences/models.py`](../finlo/contrib/cadences/models.py) | Cadence conditions |

### What to check

1. **Rename** — update or migrate stored field-name strings in the tables above (and any related views/forms/serializers that hard-code the old name).
2. **Remove** — remove or neutralize rows that reference the deleted field; avoid leaving filters/permissions/automations that would raise on missing fields.
3. **Behavior / definition change** — confirm conditions, permissions, visibility, import/export maps, and recycle-bin snapshots still make sense for the new type or meaning of the field.
4. **Related logic** — search for the old field name in code (views, templates, extensions, `_inherit_*` hooks) in addition to DB-backed models.

### Reviewer checklist

- [ ] Field rename/remove/definition change was checked against the table above.
- [ ] Existing DB rows that store the old field name are migrated or cleaned up when needed.
- [ ] Automations, workflows, cadences, filters, visibility, and permissions that reference the field still resolve correctly.
- [ ] Recycle-bin / import-export paths that embed field names were considered.

---

_Add further rule sections here as `## <Topic>` (e.g. Views, Migrations). See also [Avoid direct Django usage](#avoid-direct-django-usage)._
