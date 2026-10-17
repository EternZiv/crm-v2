# Views package index (`finlo_generics/views/__init__.py`)

## Purpose

`finlo_generics/views/__init__.py` is a **package aggregator**.
It re-exports view classes/functions from many modules so callers can import from one place:

```python
from finlo_generics import views
```

instead of importing each submodule separately.

---

## What it exports

This file uses wildcard re-exports:

- `core`
- `delete`
- `helpers.condition_widget`
- `details`
- `list`
- `card`
- `split_view`
- `detail_tabs`
- `groupby`
- `chart`
- `kanban`
- `timeline`
- `attachments`
- `global_search`
- `related_list`
- `single_form`
- `multi_form`
- `navbar`

and also exposes:

- `helpers` package object (`from finlo_generics.views import helpers`)

---

## Why import order matters

The source docstring explicitly notes:

> Import order is significant to avoid circular imports.

Because many view modules reference shared classes/mixins from each other (and from helper modules), changing this order can trigger import-time cycles.

So this file should be treated as an ordered dependency chain, not a random list.

---

## Usage pattern in the project

Most URL modules use:

```python
from finlo_generics import views
```

Then reference symbols like:

```python
views.FinloKanbanView
views.FinloRelatedListContentView
views.GlobalSearchView
```

This works because `__init__.py` re-exports those names into the package namespace.

---

## Trade-offs of wildcard exports

### Pros

- very convenient import surface for app `urls.py` and view composition,
- keeps consumer files short and consistent.



## Maintenance guidelines

- Keep imports grouped and ordered intentionally.
- When adding a new generic view module:
  1. add its import here only if it should be part of public package API;
  2. place it where it will not break existing import dependencies.
- If circular import appears after adding a module, test moving that module’s import lower in this file (or reduce cross-module imports in the module itself).

---

## Example: exposing a new generic view

If you add `finlo_generics/views/matrix.py` with `class FinloMatrixView(...)`, expose it here:

```python
from finlo_generics.views.matrix import *
```

Then consumers can use:

```python
from finlo_generics import views

path("matrix/", views.FinloMatrixView.as_view(), name="matrix")
```

---

## Summary

`finlo_generics/views/__init__.py` is the **public entry point** for generic views.
Its main job is export aggregation.
