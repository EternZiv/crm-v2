```markdown id="u4k9xp"
# Finlo Model Layer & Core Architecture

## 🎯 Purpose

Finlo extends Django’s ORM with:

- Centralized model imports
- Custom field extensions
- Core reusable base models
- Scalable architecture across apps

---

## 🧠 Project Structure

```

project_root/
│
├── finlo/          # Django PROJECT (settings, urls, db abstraction)
│   └── db/           # ORM abstraction layer
│
├── finlo_core/     # Django APP (core business models)
│
├── manage.py

````

---

## 🧩 1. ORM Abstraction Layer (`finlo.db`)

Finlo centralizes Django database imports under **`finlo.db`** so app code does not scatter `django.db` imports. Use it for models, transactions, and the default DB connection handle.

### ❌ Avoid direct Django usage in app code

```python
from django.db import models
from django.db import transaction
from django.db import connection
```

---

### ✅ Always use

```python id="a1k2xp"
from finlo.db import models
from finlo.db import transaction
from finlo.db import connection
```

`transaction` and `connection` are re-exports of Django’s modules (same API: `transaction.atomic()`, `transaction.on_commit()`, `connection.cursor()`, etc.).

---

## 📍 Entry Point

```python id="b3m8qz"
# finlo/db/__init__.py

from django.db import connection, transaction

from finlo.db import models

__all__ = ["connection", "models", "transaction"]
```

Only **`finlo/db/__init__.py`** should import `connection` and `transaction` from `django.db` directly; all other Finlo apps import from `finlo.db`.

---

## 🔁 Transactions and connections

| Import | Use when |
|--------|----------|
| `from finlo.db import transaction` | Wrap writes in `transaction.atomic()`, schedule `transaction.on_commit()` callbacks |
| `from finlo.db import connection` | Raw SQL, schema introspection, or vendor-specific checks via `connection` |

Example:

```python
from finlo.db import transaction

with transaction.atomic():
    obj.save()
    transaction.on_commit(lambda: notify_async(obj.pk))
```

When a module also needs other `django.db` symbols (e.g. `IntegrityError`, `close_old_connections`), import those from `django.db` only — not `transaction` or `connection`.

### Import placement (file layout)

Place **all** `finlo.*` imports (including `finlo.db`) under `# First party imports (Finlo)`, not under `# Third-party imports (Django)`. See [docs/coding_rule.md](../../../coding_rule.md#import-order-and-section-comments).

```python
# Third-party imports (Django)
from django.dispatch import receiver

# First party imports (Finlo)
from finlo.db import models, transaction
from finlo.db.models.signals import post_save
from finlo.contrib.core.models import FinloCoreModel  # finlo.contrib.* last
```

Signals, views (`load_data.py`, `import_data/step4.py`), CRM modules (`finlo_crm/leads/signals.py`), and inventory helpers (`finlo_inventory/stock/methods.py`) follow this layout.

---

## 📍 Extended Models Module

```python id="c7n1tr"
# finlo/db/models/__init__.py

from django.db.models import *
from django.db import models as _django_models

from finlo.db.models.fields import GenericForeignKey

__all__ = list(_django_models.__all__) + ["GenericForeignKey"]
```

✔ Includes:

* All Django model fields
* Custom `GenericForeignKey`
* Model signals via **`finlo.db.models.signals`** (re-export of `django.db.models.signals`)

---

## 📡 Model signals (`finlo.db.models.signals`)

Prefer Finlo imports for ORM signal receivers (same pattern as `finlo.web`, `finlo.shortcuts`):

```python
from finlo.db.models.signals import post_save, pre_save, post_delete
```

For namespace-style `.connect()` registration:

```python
from finlo.db.models import signals

signals.post_save.connect(my_handler, sender=MyModel)
```

Do **not** import from `django.db.models.signals` in new Finlo app code.

## 🔧 Custom GenericForeignKey

### 🚨 Django Limitation

* Only supports `ContentType`
* Does NOT support proxy models

---

### ✅ Finlo Solution

```python id="d4v8nx"
class GenericForeignKey(DjangoGenericForeignKey):
```

### ✔ Enhancements

* Supports proxy models
* Custom `verbose_name`
* Relaxed validation:

```python id="e2m7ka"
issubclass(model, ContentType)
```

---

## 🧩 2. Proxy ContentType Support

```python id="f7n2yk"
class FinloContentType(ContentType):
    class Meta:
        proxy = True
```

✔ Works seamlessly with custom `GenericForeignKey`

---

## 🧪 Example Usage

```python id="g8x4pq"
content_type = models.ForeignKey(FinloContentType, ...)
object_id = models.PositiveIntegerField(...)
related_object = models.GenericForeignKey("content_type", "object_id")
```

---

# 🧩 3. Core Models Layer (`finlo_core` app)

## 📍 Central Model Export

```python id="h1z8rw"
# finlo_core/models/__init__.py
```

### 🎯 Purpose

Provides a **single import point** for all core models.

---

### ❌ Avoid scattered imports

```python
from finlo_core.models.company import Company
```

---

### ✅ Use centralized import

```python id="i5k2zs"
from finlo_core.models import Company
```

---

### 📦 Includes Models Like:

* Company
* FinloUser
* Department, Role
* Activity, RecentlyViewed
* Attachments
* Filters & UI configs
* Business hours & holidays
* Finance models
* Import/Export
* Recycle bin
* System settings
* Visibility controls

---

# 🧩 4. Core Base Models

## 🏢 Company Model

### Features:

* Company details (name, email, website)
* Address & location
* Financial data
* Localization settings
* HQ management (only one HQ)

---

### ⚙️ Smart HQ Logic

```python id="j3n8qp"
if not Company.objects.exclude(pk=self.pk).filter(hq=True).exists():
    self.hq = True
elif self.hq:
    Company.objects.exclude(pk=self.pk).filter(hq=True).update(hq=False)
```

---

## 🔍 CompanyFilteredManager

### Purpose:

Filters queryset automatically based on:

* Active company in request
* Session flag (`show_all_companies`)

---

```python id="k9m2wr"
objects = CompanyFilteredManager()
```

✔ Enables multi-company behavior globally

---

## 🧱 FinloCoreModel (Base Model)

```python id="l4x7ns"
class FinloCoreModel(models.Model):
```

### Features:

* Common fields:

  * company
  * created_at / updated_at
  * created_by / updated_by
* Audit logging
* Active flag
* JSON additional info

---

### ⚙️ Auto Field Handling

```python id="m8q2pt"
def save(self, *args, **kwargs):
```

✔ Automatically sets:

* User tracking
* Timestamps
* Company context

---

### 🕓 Audit History

```python id="n2k9yb"
@property
def histories(self)
```

✔ Returns object history

---

### 🔗 Full History Tracking

```python
@property
def full_histories(self)
```

✔ Tracks:

* Own changes
* Related FK / OneToOne reverse objects (`_meta.related_objects`)
* Related GenericForeignKey objects (and string GFK: `related_model_name` + `related_object_id`)

✔ Performance:

* Does **not** call `get_for_model()` for every installed model (that caused ~N ContentType SELECTs on history tabs)
* Resolves ContentTypes only for models that actually have related rows, via `FinloContentType.objects.get_for_models(...)`
* Caches the GFK-candidate model list in-process (`get_history_gfk_models`)

---

# ⚠️ Important Guidelines

## ❌ Avoid

```python id="a0h4dg"
from django.db import models
from django.db import transaction
from django.db import connection
from django.contrib.contenttypes.fields import GenericForeignKey
```

---

## ✅ Always use

```python id="p6t8zx"
from finlo.db import models
from finlo.db import transaction
from finlo.db import connection
```

```python id="q1w4er"
from finlo_core.models import Company
```

---

# 🧩 Benefits

* 🔄 Centralized ORM control
* 🧼 Clean import structure
* 🔧 Extendable fields
* 🧠 AI-friendly architecture
* 🏢 Built-in multi-company support
* 📊 Integrated audit logging
* 🚀 Supports advanced relationships

---

# 📌 Summary

| Feature           | Django   | Finlo     |
| ----------------- | -------- | ----------- |
| Model import      | Direct   | Centralized (`finlo.db.models`) |
| Transactions      | `django.db.transaction` | `finlo.db.transaction` (re-export) |
| DB connection     | `django.db.connection` | `finlo.db.connection` (re-export) |
| GenericForeignKey | Limited  | Extended    |
| Proxy ContentType | ❌        | ✅           |
| Base model        | Manual   | Built-in    |
| Multi-company     | Custom   | Built-in    |
| Audit history     | External | Integrated  |

---

# 🏁 Conclusion

Finlo’s architecture separates:

* **Project layer (`finlo`)** → infrastructure & abstraction
* **App layer (`finlo_core`)** → business logic & models

This ensures:

* Clean separation of concerns
* High scalability
* Easy customization

---
