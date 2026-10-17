"""
Finlo generics forms package.

Re-exports form classes and widgets from submodules so callers can use:
from finlo.contrib.generics.forms import FinloModelForm, KanbanGroupByForm
"""

from finlo.contrib.generics.forms.constants import FINLO_FORM_EXCLUDE

from finlo.contrib.generics.forms.generics import (
    KanbanGroupByForm,
    TimelineSpanByForm,
    ColumnSelectionForm,
    SaveFilterListForm,
    PasswordInputWithEye,
    FinloHistoryForm,
    RowFieldWidget,
    RowField,
    CustomFileInput,
    FinloAttachmentForm,
    PhoneWidget,
    PhoneField,
    CheckboxGridSelectMultiple,
)
from finlo.contrib.generics.forms.multi_step import FinloMultiStepForm
from finlo.contrib.generics.forms.single_step import FinloModelForm

__all__ = [
    # Base Forms
    "KanbanGroupByForm",
    "TimelineSpanByForm",
    "ColumnSelectionForm",
    "SaveFilterListForm",
    "PasswordInputWithEye",
    "FinloHistoryForm",
    "RowFieldWidget",
    "RowField",
    "CustomFileInput",
    "FinloAttachmentForm",
    "CheckboxGridSelectMultiple",
    # Phone widgets
    "PhoneWidget",
    "PhoneField",
    # Multi-step Forms
    "FinloMultiStepForm",
    # Single-step Forms
    "FinloModelForm",
    # Shared exclude list
    "FINLO_FORM_EXCLUDE",
]
