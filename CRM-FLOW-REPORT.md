# Finlo CRM: Application Flow, Pages, Roles, and Permissions

This report describes the CRM implementation in this repository, rather than
only repeating the feature list in the README. It focuses on the main
user-facing screen families, business record lifecycles, and access-control
behavior.

> **Page inventory scope:** This report inventories user-facing page and route
> families by app, including the primary route files and their route ranges.
> Several route declarations are HTMX/modal helpers, callbacks, API endpoints,
> or fragments rather than independent full pages. The route families are
> comprehensive at the module/screen level; they are not a copy of every
> individual URL pattern or API operation.

## 1. What the application is

Finlo CRM is a Django CRM product built on the shared application platform. The
CRM owns sales/marketing records such as accounts, contacts, leads,
opportunities, campaigns, and forecasts. Shared platform apps supply users,
roles, activities, calendar, mail, dashboards, reports, notifications,
automation, and settings.

- Main CRM product: `finlo_crm/`
- Shared platform: `finlo/`, especially `finlo/contrib/`
- Django settings and active application configuration:
  [`finlo/settings/base.py`](./finlo/settings/base.py)
- Project structure and platform explanation:
  [`README.md`](./README.md)

## 2. End-to-end CRM flow

### A. Initial setup and sign-in

1. On a new database, the initial setup/signup flow is enabled only while the
   database is uninitialized and is protected by the setup password.
2. The first account created by that setup flow becomes a staff user and
   superuser, and is logged in.
3. In the existing local setup, an administrator can also create an account
   using `manage.py create_finlo_user`.
4. Normal login authenticates the user, rejects inactive accounts, tracks
   failed logins by IP, locks out repeated failures, and uses a safe redirect
   after authentication.
5. The application then builds its navigation from registered platform and
   product sections; subordinate navigation and settings items can be filtered
   by permissions.

Implementation: `finlo/contrib/core/views/initialiaze_database.py`,
`finlo/contrib/core/views/core.py`, and `finlo/contrib/core/menu.py`.

### B. Configure the organization and access

An administrator establishes the organization and users, assigns roles, and
grants model/action permissions. User records include organization context
such as company, department, and role. Roles have a hierarchy and a set of
Django permissions, but the hierarchy is not itself permission inheritance.
See [Roles and permissions](#5-roles-and-permissions).

### C. Capture and qualify a lead

Leads represent people or potential business before conversion. A lead has an
owner, status, company and conversion state. Leads can be linked to campaign
membership. Booking submissions can also be matched to an existing lead by
email, or create a website lead when there is no matching lead or contact.

Users qualify the lead and can track activity against it. When the lead is
ready, the conversion action coordinates creation/reuse of the downstream
sales records.

Implementation: `finlo_crm/leads/models/base.py`,
`finlo_crm/leads/views/lead_conversion.py`, and
`finlo_crm/leads/signals.py`.

### D. Convert the lead into sales records

Lead conversion is wrapped in a database transaction. It:

1. Creates or reuses an Account.
2. Creates or reuses a Contact and links the Contact to the Account.
3. Creates or reuses an Opportunity.
4. Adds an Opportunity contact role.
5. Uses the first campaign membership as the new Opportunity's primary
   campaign source, when one exists.
6. Marks the Lead converted and sets its final status.

This makes the converted Lead the origin record for the account/contact/deal
relationship, rather than requiring a user to recreate those records manually.

Implementation: `finlo_crm/leads/views/lead_conversion.py` (conversion
transaction and record creation).

### E. Work the account, contacts, and opportunity

- **Account** is the organization/company record. Accounts support ownership
  and parent-account relationships.
- **Contact** is an individual. Account association and the person's role are
  represented through a separate contact/account relationship.
- **Opportunity** is the deal. It tracks amount, expected revenue, close date,
  stage, probability, owner, account, forecast category, and campaign source.
- Opportunity stages carry a probability and an open/won/lost type. Saving an
  Opportunity derives its probability and forecast category from its stage.
- Contact roles, opportunity teams, and splits support multiple participants
  on a deal.

Implementation: `finlo_crm/accounts/models.py`,
`finlo_crm/contacts/models.py`, and
`finlo_crm/opportunities/models.py`.

### F. Track interactions and schedule work

Activities cover events, meetings, tasks, and logged calls. An activity can
refer to a CRM object using a generic content-type/object-ID relationship and
can carry dates, status, assignees, and participants. Calendar event/meeting/
task types are distinct from logged-call activity.

Email records can be associated with CRM objects and can use record-specific
templates. Calls track provider, direction, status, timing, agent, and related
record; creating a call also creates a linked `log_call` activity. Booking
pages collect availability and booking details. A new public booking starts
pending; its signal links it to a matching lead/contact or creates a website
lead and meeting activity. Confirmation is asynchronous.

Implementation: `finlo/contrib/activity/models.py`,
`finlo/contrib/calendar/models.py`, `finlo/contrib/mail/models.py`,
`calls/models.py`, `calls/views/call_log.py`, `booking/models.py`,
`booking/views/public.py`, and `finlo_crm/leads/signals.py`.

### G. Run campaigns and assess results

Campaigns track ownership, status, cost, revenue, and responses, and can be
arranged hierarchically. Campaign members connect a campaign to a Lead or
Contact and track their member type/status. A response updates the campaign's
response count.

Implementation: `finlo_crm/campaigns/models.py`.

### H. Forecast, analyze, and report

Forecasts are organized by forecast type, owner, and fiscal period. The model
tracks pipeline, best case, commit, closed, and actual values and includes
draft/submitted/approved/rejected states. Forecast configuration determines
which opportunity categories contribute; calculation logic considers an
opportunity's forecast category and whether its stage is won.

Reports define a module, columns, groupings, aggregates, filters, and chart
settings. Dashboard components can be driven by a report or module and have
their own metric/grouping/criteria configuration.

Implementation: `finlo_crm/forecast/models.py`,
`finlo_crm/forecast/utils.py`, `finlo/contrib/reports/models.py`, and
`finlo/contrib/dashboard/models.py`.

### I. Automate follow-up and notify users

- **Workflow rules** target a record type, run on create/edit, evaluate
  configured conditions, and can update fields, assign tasks, send email, or
  send notifications. Time-triggered actions can be scheduled relative to a
  record date.
- **Automations** support create/update/delete and scheduled triggers, with
  conditions, email/notification/both actions, and date offsets. Scheduled
  executions use a run log to avoid duplicate runs.
- **Notifications** belong to a user and can link back to the relevant CRM
  record.

Implementation: `finlo/contrib/workflow/models.py`,
`finlo/contrib/workflow/signals.py`,
`finlo/contrib/automations/models.py`,
`finlo/contrib/automations/signals.py`,
`finlo/contrib/automations/tasks.py`, and
`finlo/contrib/notifications/models.py`.

## 3. Page and screen-family inventory

The shared platform provides list, detail, form, and filter components; a particular
module may expose more than one list representation or action route.

| Area | Main screens and user tasks |
|---|---|
| **Dashboard** | Home/dashboard view; see configured metrics and charts, with components sourced from reports or modules. |
| **Accounts** | Browse/search accounts; create or edit an organization; open account details and its related records; maintain ownership and parent-account relationship. |
| **Contacts** | Browse/search people; create or edit a contact; open contact details and manage its account/role relationships. |
| **Leads** | Browse and filter leads; create/edit and progress lead status; view lead details and linked activity/campaign membership; convert a qualified lead. |
| **Opportunities** | Browse the sales pipeline; create/edit and advance a deal's stage; view deal details; manage account, contacts/contact roles, team/splits, dates, value, and forecast attributes. |
| **Campaigns** | Browse and maintain campaigns; configure campaign hierarchy and status/cost/revenue; manage campaign members and response status. |
| **Forecasts** | Configure forecast types and periods; view forecast values/status; submit and approve/reject forecasts. |
| **Activities** | Create and view events, meetings, tasks, and logged calls; associate work with a CRM record; manage dates, status, assignees, and participants. |
| **Calendar** | View and schedule calendar events, meetings, and tasks; manage calendar preferences and supported calendar integrations. |
| **Email/Mail** | Compose/track mail and use templates; associate mail with a CRM record. |
| **Calls** | Configure call-provider/agent data where authorized; create and review call logs; follow call status and linked activity. |
| **Booking** | Configure hosts, participants, availability, policies, and email templates; expose public booking pages; review pending bookings and their CRM links. |
| **Reports** | Configure report module, columns, grouping, aggregates, filters, and charts; view report output. |
| **Settings / organization** | Maintain users, roles, permissions, organization settings, and other registered platform settings. Exact items shown depend on registered settings and permissions. |
| **User and role administration** | Browse users; view/create/edit users within the applicable company scope; inspect and change roles and permission grants. |
| **Notifications** | View user-targeted notifications and follow their linked CRM records. |

The repository's product areas and platform apps are listed in
[`README.md`](./README.md); route families and files are enumerated below.

## 4. Route-family index

The root URL configuration uses `finlo.urls.project`. Apps register their URL
module and prefix dynamically; namespaces are configured per app. The root
also exposes health, admin, localization, JavaScript catalog, Summernote,
`/api/`, and DEBUG-only static/media routes. CRM APIs are nested below
`/api/crm/`; shared API modules include core, activity, dashboard, calendar,
mail, reports, keys, notifications, and calls. Swagger/ReDoc are also exposed
under `/api/`.

### CRM record pages

| App / prefix | Page and action families | URL source |
|---|---|---|
| Accounts `/crm/accounts/` | Overview/list; split, kanban, card, group, chart, and timeline layouts; create/edit/delete and change owner; detail tabs for details, activity, notes/attachments, related lists, and history; hierarchy, child/partner accounts, and account-contact relations. | `finlo_crm/accounts/urls.py` |
| Campaigns `/crm/campaigns/` | List/layout/kanban/card/group/chart/timeline; create/edit/delete and owner change; detail tabs; hierarchy and child campaigns; campaign members and contacts. | `finlo_crm/campaigns/urls.py` |
| Contacts `/crm/contacts/` | List/layout/kanban/card/timeline/chart/group; create/edit/delete and owner change; detail tabs, notes, history, related lists, hierarchy/child contacts, and account relations. | `finlo_crm/contacts/urls.py` |
| Leads `/crm/leads/` | List/card/layout/kanban/group/chart/timeline; create/edit/delete; details, tabs, history, and notes; lead conversion and owner change; stage setup; lead email configuration; public lead capture/form-builder; assignment rules and conditions. | `finlo_crm/leads/urls.py` |
| Opportunities `/crm/opportunities/` | List/kanban/card/group/layout/chart/timeline; create/edit/delete; details/tabs and contact roles; stage management; big-deal alerts; opportunity teams/members; team-selling and splits. | `finlo_crm/opportunities/urls.py` |
| Forecast `/crm/forecast/` | Forecasts, opportunity drill-downs/charts; target lists/forms and role-based controls; forecast type lists/forms. | `finlo_crm/forecast/urls.py` |
| Scoring rules (CRM scoring route prefix configured in app registration) | Scoring-rule list/create/edit/delete/detail; criteria CRUD; activation. | `finlo_crm/scoring_rules/urls.py` |

### Shared platform, settings, and operational pages

| App / prefix | Page and action families | URL source |
|---|---|---|
| Core `/` | Home/login/logout; settings and personal settings; company information, fiscal year, and company switching; holidays; users/profile/login history; roles, branches, departments, and organization settings; recycle bin; imports/import history; role/permission administration. | `finlo/contrib/core/urls.py` |
| Dashboard `/dashboard/` | Home; dashboard list/detail/create/edit/delete; chart/table components; folders, favorites, ordering; add report/chart content. | `finlo/contrib/dashboard/urls.py` |
| Reports `/reports/` | Report/favorite lists; detail, filter, update, preview, export; report/folder CRUD; column/group/aggregate/filter/chart controls. | `finlo/contrib/reports/urls.py` |
| Activity `/activity/` | Global activity and task/meeting/call/event list and kanban; create/update forms; per-record task/meeting/call/email/event lists; activity details/tabs/history/attachments and status updates. | `finlo/contrib/activity/urls.py` |
| Calendar `/calendar/` | Calendar/events/preferences; completion and availability; custom calendars; Google Calendar settings, OAuth, and sync. The webhook is a provider callback, not a user page. | `finlo/contrib/calendar/urls.py` |
| Mail `/mail/` | Incoming/outgoing mail-server management and test email; compose, preview, draft, scheduling; templates; Outlook authorization; mail history and inbox actions. | `finlo/contrib/mail/urls.py` |
| Notifications `/notifications/` | Mark/open/delete notifications; notification-template list/detail/create/edit/delete. | `finlo/contrib/notifications/urls.py` |
| Theme `/theme/` | Theme settings, change theme, set default. | `finlo/contrib/theme/urls.py` |
| Generics `/generics/` | Shared search; kanban/group-by; saved lists and column/detail-field controls; dynamic create/edit; related-list content; user pickers; notes and attachments. Primarily shared UI actions/fragments. | `finlo/contrib/generics/urls.py` |
| Workflow `/workflow/` | Rule list/detail/create/edit/delete/activation; actions, time triggers, trigger history. | `finlo/contrib/workflow/urls.py` |
| Approvals `/approvals/` | Approval-process setup/rules; approval jobs, review/respond, detail tabs; approval history, resubmission, task status. | `finlo/contrib/process/approvals/urls.py` |
| Reviews `/review-process/` | Review-process/rule setup and activation; review jobs and field-level review. | `finlo/contrib/process/reviews/urls.py` |
| Automations `/automations/` | Automation list/create/edit/delete; load-automation flow and supporting field/template choices. | `finlo/contrib/automations/urls.py` |
| Cadences `/cadences/` | Cadence setup, follow-up steps, activation/detail, reports, and task/call/email tabs and lists. | `finlo/contrib/cadences/urls.py` |
| Duplicates `/duplicates/` | Matching/duplicate rule setup and detail; duplicate review, compare, and merge. | `finlo/contrib/duplicates/urls.py` |
| Field requirements `/field-requirements/` | Requirement list/create/edit/delete and field-choice helper. | `finlo/contrib/field_requirements/urls.py` |
| Form layouts `/form-layouts/` | Layout view/editor/save/reset. | `finlo/contrib/form_layouts/urls.py` |
| Shortcuts `/shortkeys/` | Shortcut-key list/create/edit/delete/data. | `finlo/contrib/keys/urls.py` |
| Meetings `/meeting/` | Integration/access settings, user settings, meeting-link generation, Zoom and Teams authorization callbacks. | `finlo/contrib/meeting/urls.py` |
| Custom fields `/custom-fields/` | Custom-field settings/list/create/edit/delete. | `custom_fields/urls.py` |

### Integrations and booking pages

| App / prefix | Page and action families | URL source |
|---|---|---|
| Calls `/calls/` | Integration/user settings; provider and access-control management; call logs; click-to-call/status/cancel. Also includes Twilio TwiML and provider webhooks. | `calls/urls.py` |
| Booking `/booking/` | Booking settings/pages, availability/embed, booking list/status/detail; public booking, slots, confirmation, cancellation, and rescheduling. | `booking/urls.py` |

The booking URL declarations label public booking routes as no-login. Call URL
comments identify a provider webhook as unauthenticated. I have not inferred
the effective authentication/permission behavior of every route from the URL
declaration alone: some views inherit access checks from shared base classes,
and several routes are callbacks, HTMX fragments, or helper endpoints.

## 5. Data relationships at a glance

```text
Lead ──conversion──> Account
  │                    │
  ├──conversion──> Contact ──account relationship──> Account
  │                    │
  ├──conversion──> Opportunity ──> Account
  │                    ├──> Contact roles / team / splits
  │                    └──> Stage / forecast category / campaign source
  └──campaign membership

Campaign ──> Campaign members (Lead or Contact)
CRM record <── generic relation ── Activity / Email / Notification
Booking ──> matched or newly-created Lead/Contact and meeting Activity
CallLog ──> related CRM object reference + linked log_call Activity
```

The diagram summarizes the important links, not every optional field or
foreign key.

## 6. Roles and permissions

### User and role model

- The configured authentication model is `core.FinloUser`, based on
  Django's `AbstractUser`. It retains Django's standard groups,
  `user_permissions`, `is_staff`, and `is_superuser`, and adds Finlo user and
  organization fields.
- A Finlo **Role** is a separate model from a Django **Group**. Roles have
  a parent-role link and a many-to-many set of Django permissions. A parent
  role does **not** automatically inherit its parent's permissions in the
  model.
- On user creation or role change, role permissions are copied/synchronized
  onto the user's Django `user_permissions`. Permission checks consequently
  evaluate the user's Django permission set, rather than dynamically walking
  their role tree for each request.
- New non-superusers and roles receive `view_own_*` permissions by default.
- Field-level access is separate from model/action permissions. The field
  modes are `readonly`, `readwrite`, and `hidden`; explicit user settings take
  precedence over role settings, which take precedence over model defaults.

Implementation: `finlo/contrib/core/models/user.py`,
`finlo/contrib/core/models/organization.py`,
`finlo/contrib/core/signals.py`, and
`finlo/contrib/core/views/groups_and_permissions/`.

### Permission behavior

- Superusers bypass the shared model permission checks.
- The shared `has_any_perms` helper treats an empty permission list as
  unrestricted and otherwise checks whether **any** listed permission passes.
- Permission decorators also default to **any-of**. Callers need to request
  `require_all=True` when every listed permission is required.
- Generic forms check add/change permission and can use `*_own` permission
  variants for models with configured owner fields. Edit/detail checks may
  additionally validate record ownership.
- Reusable DRF permission and queryset helpers implement similar model and
  own-record checks; individual API views must actually use these helpers for
  them to apply.
- Navigation subsection and settings entries can be permission-filtered. A
  hidden navigation item is not, by itself, proof that its route is protected;
  view/API guards are the enforcement point.
- User-management list/grouped views are scoped to active users and the active
  company unless `show_all_companies` is set in the session.

Implementation: `finlo/contrib/core/models/user.py`,
`finlo/utils/decorators/wrapper.py`,
`finlo/contrib/generics/views/toolkit/form_mixin.py`,
`finlo/contrib/generics/views/details.py`,
`finlo/api/permissions.py`, `finlo/api/mixins.py`,
`finlo/menu/sub_section_menu.py`, and
`finlo/contrib/core/views/users.py`.

### Administering permissions

Role administration is linked from Settings. The role list and its create/edit/
delete actions have permission guards. The permission UI presents Django model
permissions, including own variants and custom permissions, and assignments
are written to the user's `user_permissions` or the role's permissions.

Custom permissions include profile, company-switching, and global-settings
capabilities. Role/user permission actions may also synchronize the assigned
permissions to role members.

Implementation: `finlo/contrib/core/menu.py`,
`finlo/contrib/core/views/roles.py`,
`finlo/contrib/core/views/groups_and_permissions/permission_utils.py`,
`finlo/contrib/core/views/groups_and_permissions/base.py`, and
`finlo/contrib/core/views/groups_and_permissions/user_permissions_actions.py`.

## 7. Important implementation caveats

These are code-level behaviors to keep in mind when configuring or extending
the application:

1. **Role tree is not permission inheritance.** Parent roles are organizational
   structure; permission copying to users is a separate synchronization
   behavior.
2. **Keep role grants synchronized.** The reviewed code includes explicit
   synchronization paths, but does not show one universal hook for every
   arbitrary edit to a role's permission set.
3. **Role-list guard differs from other role screens.** The `RoleListView` was
   observed using `core.view_teamrole`, while related role UI uses
   `core.view_role`. This may produce unexpected access differences.
4. **Permission update guards use any-of semantics.** Some permission mutation
   endpoints include view and change permissions under the default any-of
   decorator. Review the guard before relying on it as a strict
   change-permission boundary.
5. **Campaign member references are not mutually exclusive at model level.**
   The member model has nullable Lead and Contact references plus a member
   type; the model does not itself enforce exactly one reference matching
   that type.
6. **Call and booking links are not all foreign keys.** Call records use a
   model-name string and object ID. Booking CRM matching is email-based,
   prioritizes a matching Lead over a Contact, and creates a website Lead
   when neither is found. It does not create an Account or Opportunity as part
   of that path.
7. **Lead conversion's default-stage lookup deserves verification in
   multi-company data.** The reviewed conversion query selects an order-1
   Opportunity stage without an evident company filter.

These notes describe implementation behavior, not a substitute for a complete
security review or an operational policy.

## 8. Key implementation references

- Lead conversion: `finlo_crm/leads/views/lead_conversion.py`
- Lead model and booking linkage: `finlo_crm/leads/models/base.py`,
  `finlo_crm/leads/signals.py`
- Accounts and contacts: `finlo_crm/accounts/models.py`,
  `finlo_crm/contacts/models.py`
- Opportunity pipeline: `finlo_crm/opportunities/models.py`
- Campaign management: `finlo_crm/campaigns/models.py`
- Forecasts: `finlo_crm/forecast/models.py`,
  `finlo_crm/forecast/utils.py`
- User, role, and permission behavior: `finlo/contrib/core/models/user.py`,
  `finlo/contrib/core/models/organization.py`,
  `finlo/contrib/core/signals.py`
- Shared access checks: `finlo/utils/decorators/wrapper.py`,
  `finlo/contrib/generics/views/toolkit/form_mixin.py`,
  `finlo/contrib/generics/views/details.py`
- Activity, mail, calendar, booking, and calls:
  `finlo/contrib/activity/models.py`,
  `finlo/contrib/mail/models.py`,
  `finlo/contrib/calendar/models.py`,
  `booking/`, and `calls/`
- Reports, dashboards, and automation:
  `finlo/contrib/reports/models.py`,
  `finlo/contrib/dashboard/models.py`,
  `finlo/contrib/workflow/`, and `finlo/contrib/automations/`
