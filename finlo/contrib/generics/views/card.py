"""
Card (tile) view for displaying list data in a grid of cards.
Uses the same data and context as FinloListView with a card layout.
"""

# Standard library imports
import logging

# Django
# Third-party imports (Django)
from django.template.loader import render_to_string

from finlo.shortcuts import render

# First party imports (Finlo)
from finlo.web import HttpResponse

# Local imports
from .list import FinloListView

logger = logging.getLogger(__name__)


class FinloCardView(FinloListView):
    """
    View for displaying data in a card (tile) grid layout.
    Reuses FinloListView queryset, filters, and context with a card template.
    """

    template_name = "card_view.html"
    supports_quick_filters = False
    bulk_select_option = False
    table_class = False
    table_width = False
    paginate_by = 24

    def render_to_response(self, context, **response_kwargs):
        """Override to use card template for HTMX and normal requests."""
        is_htmx = self.request.headers.get("HX-Request") == "true"
        context["request_params"] = self.request.GET.copy()

        if is_htmx:
            page_kwarg = getattr(self, "page_kwarg", "page")
            if self.request.GET.get(page_kwarg):
                html = render_to_string(
                    "partials/card_view_load_more.html",
                    context,
                    request=self.request,
                )
                return HttpResponse(html)
            return render(self.request, "card_view.html", context)

        return super(FinloListView, self).render_to_response(
            context, **response_kwargs
        )
