# Finlo generic views (`finlo.views.generic`)

Thin Django CBV wrappers that apply Finlo extension composition. Import from this package when you need platform hooks without the full generics list/detail stack.

```python
from finlo.views.generic import View, FormView, ListView
```

Supported re-exports in this package:

- `FormView`
- `View`
- `TemplateView`
- `ListView`
- `DetailView`

In `finlo.contrib` modules, place `from finlo.views.generic import ...` under `# First party imports (Finlo)` (not under Django imports).

If you need a CBV that is not exported here (for example `DeleteView`), import it directly from Django.

---

## `View`

```python
from finlo.views.generic import View
```

Subclass of Django’s `View`. `as_view()` resolves [`_inherit_view`](../extension/view/inherit.md) extensions for the **concrete** subclass on each request (same late-binding idea as list/card/kanban).

```python
from finlo.extension.view import ViewExtension

class JalaliFieldInfoResolverExtension(ViewExtension):
    _inherit_view = (
        "finlo.contrib.generics.views.helpers.edit_field.FieldInfoResolver"
    )

    def parse_date_field_value(self, value, user=None):
        ...
```

Examples that inherit this base: `FieldInfoResolver`, `ExtraFieldsProvider`, `EditAllFieldsView`, `UpdateAllFieldsView`.

Direct instantiation must go through `resolve_view_class` (or helpers such as `get_field_info_resolver()`) so extensions apply.

---

## `FormView`

```python
from finlo.views.generic import FormView
```

Subclass of Django’s `FormView`. `get_form_class()` returns `resolve_form_class(base)` so registered `FormExtension` classes apply.

```python
class ReginalFormatingView(LoginRequiredMixin, FormView):
    form_class = RegionalFormattingForm

    def get(self, request, *args, **kwargs):
        form = self.get_form_class()(instance=request.user)
        ...
```

Do **not** instantiate `RegionalFormattingForm(...)` directly in the view if extensions should run — always go through `get_form_class()`.

`FinloSingleFormView` / `FinloMultiStepFormView` already call `resolve_form_class()`; they do not need this wrapper.

Lazy import of `resolve_form_class` avoids a cycle: `finlo.extension.forms.compose` imports `FinloModelForm` from generics.

---

## `ListView`

```python
from finlo.views.generic import ListView
```

Thin wrapper around Django’s `ListView` (no extension resolve of its own). Prefer `FinloListView` when you need `_inherit_list`, filters, bulk actions, etc.

---

## Related

- [View `_inherit_view`](../extension/view/inherit.md)
- [Form `_inherit_form`](../extension/forms/inherit.md)
- [Regional formatting](../contrib/core/core_app.md#regional-formatting)
- [Edit field helpers](../contrib/generics/views/helpers/edit_field.md)
- [Coding rules — import `finlo.views.generic`](../coding_rule.md#avoid-direct-django-usage)
