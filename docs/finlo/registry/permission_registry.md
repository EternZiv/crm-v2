# Permission Registry (`permission_registry.py`)

## Purpose

`finlo/registry/permission_registry.py` maintains a set of model names that are exempt from permission checks.

The set is:

```python
PERMISSION_EXEMPT_MODELS
```

It includes built-in defaults like `Session`, `Group`, `Permission`, etc.

## API

### `@permission_exempt_model`

Decorator that adds `cls.__name__` into `PERMISSION_EXEMPT_MODELS`.

## Usage example

```python
from finlo.registry.permission_registry import permission_exempt_model


@permission_exempt_model
class ReviewCondition(FinloCoreModel):
    ...
```

After class definition, `"ReviewCondition"` is in `PERMISSION_EXEMPT_MODELS`.
