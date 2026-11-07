# Finlo utilities (`finlo.utils`)

## Purpose

Top-level **`finlo.utils`** holds small, cross-cutting helpers: branding defaults, form/field choice tuples, upload path generation, version aggregation for installed apps, plus subpackages/modules for **decorators**, **translation**, **HTML**, **text**, and **functional** re-exports.

This is **not** the Django app `finlo.contrib.utils` (that package lives under `finlo/contrib/utils/`). Import paths here are `finlo.utils.*`.

---

## Module layout (on disk)

Layout under `finlo/utils/` matches the repository (after the package is used locally, Python may also create `__pycache__/` directories; those are generated and are not source).

```text
finlo/utils/
├── decorators/       # View decorators (permissions, HTMX, DB init). See docs below.
├── translation/      # Re-exports Django translation API under one import path.
├── startup/          # runserver progress bar + Finlo CRM version banner. See docs below.
├── html.py           # Re-exports django.utils.html (format_html, escape, …)
├── text.py           # Re-exports django.utils.text (slugify, Truncator, …)
├── functional.py     # Re-exports django.utils.functional (cached_property, lazy, …)
├── timezone.py       # Re-exports django.utils.timezone (now, localtime, make_aware, …)
├── branding.py       # DEFAULTS + load_branding() from optional settings.BRANDING_MODULE
├── choices.py        # TIMEZONE_CHOICES, LANGUAGE_CHOICES, format/operator tuples, FIELD_TYPE_MAP, …
├── upload.py         # upload_path(instance, filename) for namespaced FileField paths
├── version.py        # get_module_version_info, collect_all_versions (reads `__version__` modules)
└── __init__.py       # Empty placeholder (no re-exports at package root)
```

| Path | Role |
|------|------|
| `decorators/` | `permission_required`, `htmx_required`, `db_initialization`, etc. Documented in [decorators.md](./decorators.md). |
| `translation/` | `gettext_lazy`, `gettext`, `activate`, … from Django. Documented in [translation.md](./translation.md). |
| `startup/` | `runserver` progress bar and Finlo CRM version banner. Documented in [startup.md](./startup.md). |
| `html.py` | `format_html`, `format_html_join`, `escape`, `strip_tags`, … from Django. Documented in [html.md](./html.md). |
| `text.py` | `slugify`, `Truncator`, `capfirst`, … from Django. Documented in [text.md](./text.md). |
| `functional.py` | `cached_property`, `lazy`, `Promise`, … from Django. Documented in [functional.md](./functional.md). |
| `timezone.py` | `now`, `localtime`, `make_aware`, `UTC`, … from Django. Use `from finlo.utils import timezone`. |
| `branding.py` | `DEFAULTS` (title, login copy, logo paths) and `load_branding()` merging overrides from `BRANDING_MODULE`. Also used as the fallback **company name** in activity meeting and booking transactional emails when no company is set. |
| `choices.py` | Shared `(value, label)` tuples and maps (languages, date/time formats, operators, field types, `BLOCKED_EXTENSIONS`). |
| `upload.py` | Builds `app_label/model_name/[field_name/]slug-uuid.ext` paths to avoid collisions. |
| `version.py` | Discovers `module.__version__` metadata and changelog attributes like `__1_2_0__` for about/settings UIs. Platform vs module rules: [versioning.md](../../versioning.md). |
| `__init__.py` | Intentionally empty; import from submodules or specific modules (e.g. `from finlo.utils.choices import LANGUAGE_CHOICES`). |

---

## Deeper docs

- [Decorators](./decorators.md) — `finlo.utils.decorators`
- [Translation](./translation.md) — `finlo.utils.translation`
- [Startup / runserver](./startup.md) — `finlo.utils.startup` (progress bar + Finlo CRM banner)
- [HTML](./html.md) — `finlo.utils.html`
- [Text](./text.md) — `finlo.utils.text`
- [Functional](./functional.md) — `finlo.utils.functional`

### Timezone (`finlo.utils.timezone`)

Prefer Finlo imports over `django.utils.timezone`:

```python
from finlo.utils import timezone

now = timezone.now()
aware = timezone.make_aware(naive_dt)
```

Also available as named imports: `from finlo.utils.timezone import now, localtime, UTC`.

---

## Quick import examples

```python
from finlo.utils.branding import load_branding, DEFAULTS
from finlo.utils.choices import LANGUAGE_CHOICES, OPERATOR_CHOICES
from finlo.utils.upload import upload_path
from finlo.utils.version import collect_all_versions, get_module_version_info
from finlo.utils.decorators import permission_required, htmx_required
from finlo.utils.translation import gettext_lazy as _
from finlo.utils.html import format_html, escape, strip_tags
from finlo.utils.text import slugify
from finlo.utils.functional import cached_property
from finlo.utils import timezone
from finlo.utils.startup import install_banner, install_progress  # manage.py only
```
