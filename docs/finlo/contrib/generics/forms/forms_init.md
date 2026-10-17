# Forms package init (`finlo_generics/forms/__init__.py`)

## Purpose

`finlo_generics/forms/__init__.py` is the package export hub for generic forms.

It re-exports form classes from internal submodules so callers can import from a single namespace:

```python
from finlo_generics.forms import FinloModelForm, FinloMultiStepForm, PhoneField
```

instead of importing each submodule directly.

---

## What this file does

The module imports and re-exports from internal submodules:

- `finlo_generics.forms.constants` — `FINLO_FORM_EXCLUDE`
- `finlo_generics.forms.generics` — helper/config forms and widgets
- `finlo_generics.forms.multi_step` — `FinloMultiStepForm`
- `finlo_generics.forms.single_step` — `FinloModelForm` (including `get_fieldsets()`)

This exposes:

- `FinloModelForm` (single-step base form)
- `FinloMultiStepForm` (wizard/multi-step base form)
- `FINLO_FORM_EXCLUDE` (core field exclude list)
- `PhoneWidget` — country-code Select2 + number input widget
- `PhoneField` — `MultiValueField` that compresses to `+XX NNNNNN` in a CharField
- generic helper forms from `generics.py` (e.g., settings/selection/helper forms)

---

## `FINLO_FORM_EXCLUDE`

Defined in `finlo_generics/forms/constants.py` and re-exported here:

```python
FINLO_FORM_EXCLUDE = [
    "company",
    "is_active",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "additional_info",
]
```

These are `FinloCoreModel` audit/tenant fields that should not appear on
create/edit forms.

`FinloModelForm.__init_subclass__` reads this list automatically and merges it
into every subclass `Meta.exclude` at class definition time — child forms do not
need to reference this constant directly.

It lives in `constants.py` (a leaf module with no internal imports) so both
`single_step.py` and any other module can import it without circular dependency.

---

## Why this pattern is used

Benefits:

- simpler import paths for app code
- consistent API surface for generic form consumers
- easier migration/refactor of internal module layout without changing all import sites

Trade-offs:

- wildcard exports can obscure exact symbol origin
- possible naming collisions if multiple submodules export same symbol names

---

## Typical usage patterns

### Aggregated import from package

```python
from finlo_generics.forms import FinloModelForm, FinloMultiStepForm
```

### Direct import when explicit origin is preferred

```python
from finlo_generics.forms.single_step import FinloModelForm
from finlo_generics.forms.multi_step import FinloMultiStepForm
```

Both are valid; package-level import is mainly for convenience.

---

## Relationship to form architecture

This `__init__.py` sits above three form layers:

- `single_step.py`: base form behavior for normal forms (`FinloModelForm`)
- `multi_step.py`: step-wise/wizard behavior (`FinloMultiStepForm`)
- `generics.py`: helper/config forms used by generic views

By exporting all of them, the package becomes a single entry point for form classes used across `finlo_generics.views`.

---

## Maintenance guidance

When adding a new commonly used form in forms submodules:

1. define/export it in its module,
2. ensure module is included here (already true for the three core modules),
3. verify there are no name collisions with existing wildcard exports.

If collision risk exists, consider moving to explicit `__all__` declarations in submodules.

---

## Summary

`finlo_generics/forms/__init__.py` is a convenience aggregation layer that re-exports forms from core submodules, enabling clean package-level imports and a unified public interface for Finlo generic form classes.
