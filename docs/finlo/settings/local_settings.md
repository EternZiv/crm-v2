# `local_settings.py`

## 🎯 Purpose

`finlo/settings/local_settings.py` is intended for **local overrides**.

In your current repo snapshot, this file may be empty/placeholder, but the expected pattern is:
- developers customize settings per machine/environment here
- base settings remain in `base.py`
- CRM / extra apps are appended in `finlo_apps.py`

## How it is loaded

`finlo/settings/__init__.py` imports in this order:

```python
from finlo.settings.base import *
from finlo.settings import finlo_apps
from finlo.settings.local_settings import *
```

1. **`base.py`** — platform defaults (`INSTALLED_APPS`, middleware, databases, …).
2. **`finlo_apps`** — mutates `INSTALLED_APPS` (and related) for CRM and optional packages; see [finlo_apps.md](finlo_apps.md).
3. **`local_settings.py`** — **last**, so machine/env overrides win over both base and app-extension lists.

Anything you define in `local_settings.py` can override variables imported from `base.py` **and** adjustments made while importing `finlo_apps` (for example reordering or removing apps from `INSTALLED_APPS`, `DEBUG`, `ALLOWED_HOSTS`, database credentials).

> **Why after `finlo_apps`?** App packages may append to `INSTALLED_APPS` at import time. Loading local settings first would let those appends overwrite your local `INSTALLED_APPS` assignment. Importing local settings **last** keeps developer overrides authoritative.

## Example override

```python
# finlo/settings/local_settings.py

DEBUG = False
ALLOWED_HOSTS = ["crm.example.com"]
```

---

If you add variables here, ensure they are compatible with what `base.py` expects.
