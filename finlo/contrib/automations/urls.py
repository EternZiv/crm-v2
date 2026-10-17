"""
URLs for the automations app
"""

# First party imports (Finlo)
from finlo.urls import path

# Local imports
from . import views
from .load_automation import CreateSelectedAutomationsView, LoadAutomationModalView

app_name = "automations"

urlpatterns = [
    path(
        "automation-view/",
        views.FinloAutomationView.as_view(),
        name="automation_view",
    ),
    path(
        "automation-navbar-view/",
        views.FinloAutomationNavbar.as_view(),
        name="automation_navbar_view",
    ),
    path(
        "automation-list-view/",
        views.FinloAutomationListView.as_view(),
        name="automation_list_view",
    ),
    path(
        "automation-create-view/",
        views.FinloAutomationFormView.as_view(),
        name="automation_create_view",
    ),
    path(
        "automation-update-view/<int:pk>/",
        views.FinloAutomationFormView.as_view(),
        name="automation_update_view",
    ),
    path(
        "get-automation-field-choices/",
        views.AutomationFieldChoicesView.as_view(),
        name="get_automation_field_choices",
    ),
    path(
        "get-mail-to-choices/",
        views.MailToChoicesView.as_view(),
        name="get_mail_to_choices",
    ),
    path(
        "get-template-fields/",
        views.TemplateFieldsView.as_view(),
        name="get_template_fields",
    ),
    path(
        "automation-delete-view/<int:pk>/",
        views.FinloAutomationDeleteView.as_view(),
        name="automation_delete_view",
    ),
    path(
        "load-automation/",
        LoadAutomationModalView.as_view(),
        name="load_automation",
    ),
    path(
        "create-selected-automations/",
        CreateSelectedAutomationsView.as_view(),
        name="create_selected_automations",
    ),
]
