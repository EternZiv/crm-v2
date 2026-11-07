"""Finlo generic views package. Re-exports FormView for callers."""

from finlo.views.generic.edit import FormView
from finlo.views.generic.base import View, TemplateView
from finlo.views.generic.list import ListView
from finlo.views.generic.detail import DetailView

__all__ = ["FormView", "View", "TemplateView", "ListView", "DetailView"]
