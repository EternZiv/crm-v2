"""Details view classes for all Finlo views."""

from django.views.generic import DetailView as DjangoDetailView


class DetailView(DjangoDetailView):
    """Django DetailView base for Finlo records detail screens."""
