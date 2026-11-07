# Finlo functional utilities (`finlo.utils.functional`)

## Purpose

`finlo/utils/functional.py` is a thin wrapper around Django’s `django.utils.functional` helpers.

It exists so app code can keep one standard import path:

- instead of `from django.utils.functional import cached_property, lazy, …`
- use `from finlo.utils.functional import cached_property, lazy, …`

This matches the pattern used by `finlo.utils.translation`, `finlo.utils.html`, and `finlo.utils.text`.

---

## Module layout

```text
finlo/utils/
└── functional.py   # re-exports django.utils.functional helpers
```

This page is `docs/finlo/utils/functional.md`.

---

## What it re-exports

`finlo.utils.functional` re-exports these names from `django.utils.functional`:

- `LazyObject`
- `Promise`
- `SimpleLazyObject`
- `cached_property`
- `classproperty`
- `empty`
- `keep_lazy`
- `keep_lazy_text`
- `lazy`
- `lazystr`
- `partition`

---

## Common usage

```python
from finlo.utils.functional import cached_property, lazy, Promise

class MyView:
    @cached_property
    def related_list_config(self):
        return {...}
```

`cached_property` is widely used on Finlo list/detail views for computed config. See also [coding_rule.md](../../coding_rule.md) guidance on `@cached_property` on views.

---

## Coding rule

If Finlo re-exports the symbol, import from `finlo.utils.functional` — not `django.utils.functional`.

See [coding_rule.md](../../coding_rule.md) and the package overview in [utils.md](./utils.md).
