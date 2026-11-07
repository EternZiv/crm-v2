"""Filter sets for Custom Field definition list views."""

from finlo.contrib.generics.filters import FinloFilterSet

from .models import CustomFieldDefinition


class CustomFieldDefinitionFilter(FinloFilterSet):
    """Filter set for the Custom Field definitions list."""

    class Meta:
        """Filterable and searchable fields for CustomFieldDefinition."""

        model = CustomFieldDefinition
        fields = ["content_type", "field_type", "is_required"]
        search_fields = ["name"]
