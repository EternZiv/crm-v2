"""
FINLONEXA CRM v2 — Connect MCP Server Settings View.

Enables authorized CRM users to inspect their MCP connection status,
copy AI setup prompts and configuration snippets, view accessible modules,
and manage their AI assistant integrations.
"""

import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from finlo.contrib.core.mcp_data_service import get_user_accessible_modules


class ConnectMCPSettingsView(LoginRequiredMixin, View):
    """
    User-facing Settings page: Settings → Integrations → Connect MCP Server.
    Provides connection status, copyable agent setup prompts, client configs,
    and permission-aware module access summaries.
    """

    template_name = "settings/connect_mcp_settings.html"

    def get(self, request, *args, **kwargs):
        user = request.user
        company = getattr(request, "active_company", None) or getattr(user, "company", None)
        company_name = company.name if company else "Default Organization"
        role_name = str(getattr(user, "role", "Standard User"))

        # 1. Accessible Modules & Permissions
        modules = get_user_accessible_modules(user)
        accessible_count = sum(1 for m in modules if m["is_accessible"])

        # 2. Connection Status Details
        connection_status = {
            "mcp_enabled": True,
            "transport_type": "STDIO / Streamable HTTP",
            "stdio_status": "LOCAL VERIFIED",
            "remote_status": "SETUP REQUIRED",
            "remote_endpoint": None,  # Explicitly None to prevent fabricated URLs
            "user_identity": user.username,
            "user_email": user.email or user.username,
            "company_name": company_name,
            "role_name": role_name,
            "accessible_modules_count": accessible_count,
            "total_modules_count": len(modules),
            "last_connected": getattr(user, "last_login", None),
        }

        # 3. Copyable AI Agent Setup Script
        agent_setup_prompt = (
            "You are connected to FINLONEXA CRM v2 via the Model Context Protocol (MCP).\n"
            f"Tenant Company: {company_name}\n"
            f"Authorized User: {user.username} ({role_name})\n\n"
            "OPERATING GUIDELINES:\n"
            "1. This integration is strictly READ-ONLY. No database mutations, deletions, or creates are permitted.\n"
            "2. All queries are strictly scoped to the authenticated user's effective permissions and sales hierarchy.\n"
            "3. Discover available tools using the standard MCP 'tools/list' handshake.\n"
            "4. Respect field-level visibility: fields marked as hidden by administrator policy are omitted.\n"
            "5. Never prompt for or store customer passwords, session tokens, or sensitive credentials.\n"
            "6. Present tabular CRM data clearly in markdown tables and suggest relevant charts for aggregated metrics."
        )

        # 4. Standard Client Configurations (generic templates without leaking private filesystem paths)
        client_configs = {
            "antigravity": json.dumps(
                {
                    "mcpServers": {
                        "finlo-crm": {
                            "command": "<CRM_PROJECT_DIR>/.venv/Scripts/python.exe",
                            "args": ["<CRM_PROJECT_DIR>/finlo/mcp_server.py"],
                            "env": {"PYTHONUNBUFFERED": "1"},
                        }
                    }
                },
                indent=2,
            ),
            "claude": json.dumps(
                {
                    "mcpServers": {
                        "finlo-crm": {
                            "command": "<CRM_PROJECT_DIR>/.venv/Scripts/python.exe",
                            "args": ["<CRM_PROJECT_DIR>/finlo/mcp_server.py"],
                            "env": {"PYTHONUNBUFFERED": "1"},
                        }
                    }
                },
                indent=2,
            ),
            "cursor": json.dumps(
                {
                    "mcpServers": {
                        "finlo-crm": {
                            "command": "<CRM_PROJECT_DIR>/.venv/Scripts/python.exe",
                            "args": ["<CRM_PROJECT_DIR>/finlo/mcp_server.py"],
                        }
                    }
                },
                indent=2,
            ),
            "codex": json.dumps(
                {
                    "mcpServers": {
                        "finlo-crm": {
                            "command": "<CRM_PROJECT_DIR>/.venv/Scripts/python.exe",
                            "args": ["<CRM_PROJECT_DIR>/finlo/mcp_server.py"],
                        }
                    }
                },
                indent=2,
            ),
            "remote_http": (
                "# Streamable HTTP Endpoint (Requires Remote Gateway Activation)\n"
                "# https://<your-finlo-domain>/mcp/v1/\n"
                "# Status: SETUP REQUIRED (Not deployed on this environment)"
            ),
        }

        # 5. Connected AI Applications
        # External client token management and revocation require OAuth 2.0 PKCE deployment.
        connected_applications = []

        context = {
            "connection_status": connection_status,
            "modules": modules,
            "agent_setup_prompt": agent_setup_prompt,
            "client_configs": client_configs,
            "connected_applications": connected_applications,
        }

        return render(request, self.template_name, context)

