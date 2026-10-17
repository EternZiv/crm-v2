"""List view classes for all Finlo views."""

from django.views.generic import ListView as DjangoListView


class ListView(DjangoListView):
    """Django ListView base for Finlo list screens."""
