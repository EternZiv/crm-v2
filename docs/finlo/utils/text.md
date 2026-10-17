# Finlo text utilities (`finlo.utils.text`)

## Purpose

`finlo/utils/text.py` is a thin wrapper around Django’s `django.utils.text` helpers.

It exists so app code can keep one standard import path:

- instead of `from django.utils.text import slugify, …`
- use `from finlo.utils.text import slugify, …`

This matches the pattern used by `finlo.utils.translation`, `finlo.utils.timezone`, and `finlo.utils.html`.

---

## Module layout

```text
finlo/utils/
└── text.py   # re-exports django.utils.text functions
```

This page is `docs/finlo/utils/text.md`.

---

## What it re-exports

`finlo.utils.text` re-exports these names from `django.utils.text`:

- `Truncator`
- `camel_case_to_spaces`
- `capfirst`
- `compress_sequence`
- `compress_string`
- `get_text_list`
- `get_valid_filename`
- `normalize_newlines`
- `phone2numeric`
- `slugify`
- `smart_split`
- `unescape_string_literal`
- `wrap`

---

## Common usage

```python
from finlo.utils.text import slugify, Truncator, capfirst

name = slugify("My Report Title")  # "my-report-title"
```

Used across import/export, upload path generation, charts, and group-by views.

---

## Coding rule

If Finlo re-exports the symbol, import from `finlo.utils.text` — not `django.utils.text`.

See [coding_rule.md](../../coding_rule.md) and the package overview in [utils.md](./utils.md).
