# FINLONEXA

<div align="center">
  <img src="static/assets/img/finlo-crm-logo.png" alt="FINLONEXA Logo" width="232" height="57">
  <h3>Customer Relationship Management System</h3>
  <p>A comprehensive CRM solution designed for enterprise-level customer engagement, sales tracking, and business process automation.</p>
  <p><em>Finlo CRM is built on the <strong>Horilla platform</strong>; shared support apps live under <code>horilla.contrib</code>.</em></p>
</div>

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/django-5.2+-green.svg)](https://djangoproject.com)

## ✨ Features

### 🏢 **Core CRM Modules**
- **👥 People Management**
  - **Accounts**: Manage companies and organizations with detailed profiles
  - **Contacts**: Individual contact management with relationship tracking
  - **Roles & Permissions**: Granular access control and user management

- **💼 Sales Pipeline**
  - **Leads**: Lead capture, qualification, and nurturing
  - **Opportunities**: Deal tracking with customizable sales stages
  - **Forecasting**: Revenue predictions and sales analytics
  - **Big Deal Alerts**: Automated notifications for high-value opportunities

- **📊 Marketing & Campaigns**
  - **Campaign Management**: Multi-channel campaign creation and tracking
  - **Campaign Analytics**: Performance metrics and ROI analysis
  - **Lead Source Tracking**: Attribution and conversion analysis

- **📅 Activity & Communication**
  - **Activity Tracking**: Meetings, calls, emails, and task management
  - **Calendar Integration**: Unified scheduling and event management
  - **Timeline View**: Chronological activity history
  - **Email Integration**: Built-in email composer with templates

- **📈 Analytics & Reporting**
  - **Interactive Dashboards**: Customizable widgets and charts
  - **Advanced Reports**: Detailed analytics across all modules
  - **Data Export**: CSV, Excel export capabilities
  - **Real-time Notifications**: WebSocket-based live updates

### 🌐 **Technical Features**
- **Multi-language Support**: 25+ languages including English, Arabic, German, French, Korean
- **Multi-currency**: Global currency support with conversion
- **Real-time Updates**: WebSocket integration for live notifications
- **Advanced Search**: Global search across all modules
- **Import/Export**: Bulk data operations with CSV/Excel support
- **Audit Trail**: Complete activity logging and history tracking
- **Responsive Design**: Mobile-friendly interface
- **Dark/Light Themes**: Customizable UI preferences

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Redis (for background jobs; optional for single-process local WebSockets)

### Local Development

1. **Create and activate a virtual environment** (Windows PowerShell)
   ```bash
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment and database**

   Local settings use `db.sqlite3` when `DATABASE_URL` is unset. In-memory WebSockets
   are used in local development by default; configure `CHANNEL_REDIS_URL` to
   use a Redis 5+ server when running multiple application processes.
   ```bash
   DATABASE_URL=sqlite:///db.sqlite3
   REDIS_URL=redis://127.0.0.1:6379/0
   CHANNEL_REDIS_URL=
   CELERY_BROKER_URL=redis://127.0.0.1:6379/0
   CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
   ```

4. **Initialize the database and create an admin**
   ```bash
   python manage.py migrate
   python manage.py create_horilla_user
   ```

5. **Run the app**
   ```bash
   python manage.py runserver
   ```

   Open http://localhost:8000. For an existing SQLite database migration to
   Supabase, see [SUPABASE-MIGRATION.md](SUPABASE-MIGRATION.md).

   On start you will see a one-line Horilla loading progress bar, then a banner with
   **Horilla version** (from `horilla.__version__`) instead of Django’s version line.
   See [docs/horilla/utils/startup.md](docs/horilla/utils/startup.md).

### Deploying on Vercel

Vercel detects this Django project from `manage.py`, uses the configured ASGI
application, and collects static assets during its build. See
[VERCEL-DEPLOYMENT.md](VERCEL-DEPLOYMENT.md) for required environment variables,
database and Redis setup, and serverless storage and worker limitations.

## ⬆️ Upgrading from v1.9 to v1.10.0

> Existing users on **Horilla CRM v1.9** must follow these steps once before starting the v1.10.0 server. Migrations alone are **not** enough — the v1.10.0 release renames several app labels (e.g. `horilla_activity` → `activity`, `horilla_core` → `core`), and the `sync_db` management command rewrites the migration history and content-type references to match.

### Step 1 — Pull the latest code

```bash
git pull origin main
pip install -r requirements.txt
```

### Step 2 — Enable the `sync_db` helper app

Open **`horilla/settings/local_settings.py`** and add these two lines:

```python
from horilla.settings.base import INSTALLED_APPS

INSTALLED_APPS.append("sync_db")
```

This registers the one-shot helper app that ships only the `sync_db` management command. It is intentionally kept out of `base.py` so fresh installs never run it.

### Step 3 — Run the sync command

```bash
python3 manage.py sync_db
```

This will:

- Remap legacy app labels in the `django_migrations` table
- Fake-apply the renamed migrations so Django sees the new app names as already-applied
- Update `ContentType` and permission references to point at the new app labels

When the command finishes, your v1.9 database is fully migrated to the v1.10.0 schema. You can optionally remove the two `sync_db` lines from `local_settings.py` afterwards.

### Fresh installation (no v1.9 data)

New installs **do not** need `sync_db`. Just pull the code and run:

```bash
python3 manage.py migrate
```

## 📦 Installation Options

### Debian/Ubuntu Package
```bash
# Install the .deb package
sudo dpkg -i horilla-crm_1.0.0-1_all.deb
sudo apt-get install -f

# Start the service
sudo systemctl start horilla-crm
sudo systemctl enable horilla-crm
```

### Windows Installer
- Download and run the Windows installer from releases
- Supports both manual and service installation
- Includes automatic Python environment setup
- Service integration with Windows Service Manager

## 🏗️ Architecture

### Technology Stack
- **Backend**: Django 5.2+ with Python 3.12+
- **Database**: PostgreSQL (recommended), SQLite (development)
- **Web Server**: Uvicorn ASGI server with WebSocket support
- **Frontend**: HTML5, TailwindCSS, HTMX for dynamic interactions
- **Real-time**: Django Channels for WebSocket communication
- **Task Queue**: APScheduler for background tasks
- **File Storage**: WhiteNoise for static files

### Platform layout — Horilla as a multi-product ERP base

The repository follows a **two-tier package layout**:

- **`horilla/`** — the **platform**. Houses framework-level helpers (`apps`, `db`, `web`, `menu`, `registry`, `shortcuts`, `utils`) plus all shared **support apps** under **`horilla.contrib.<app>`** (`core`, `mail`, `activity`, `notifications`, `dashboard`, `reports`, `automations`, `calendar`, `cadences`, `process`, `keys`, `theme`, `duplicates`, `generics`, `utils`).
- **`horilla_<product>/`** — an **ERP product package**. This repository contains **`horilla_crm/`**; the platform is also the foundation for the existing HRMS product, and future products such as **`horilla_sales`** and **`horilla_purchase`** ship as their own top-level packages on the same platform.

ERP product packages **import from `horilla.contrib`**, never the other way around. Each product keeps its **own app label and table prefix** (`horilla_crm_lead`, future `horilla_sales_order`, …), so products are independently installable and versioned while still sharing one consistent foundation for auth, mail, activity, dashboards, automations, and the rest of the platform features.

### Project Structure
```
horilla-crm/
├── horilla/                    # Django project package
│   ├── settings/               # Environment settings (base/dev/prod)
│   ├── urls/                   # Project URL configuration
│   ├── contrib/                # Shared platform modules
│   │   ├── core/               # Users, roles, settings, org data
│   │   ├── generics/           # Reusable CBVs/forms/filter helpers
│   │   ├── dashboard/          # Dashboard builder and chart components
│   │   ├── activity/           # Activity tracking
│   │   ├── calendar/           # Calendar + Google sync
│   │   ├── mail/               # Outbound/inbound mail integration
│   │   ├── notifications/      # Real-time/user notifications
│   │   ├── automations/        # Event/scheduled automations
│   │   ├── duplicates/         # Duplicate detection and merge
│   │   ├── reports/            # Report definitions and execution
│   │   ├── cadences/           # Sales cadence workflows
│   │   ├── process/            # Approvals and review processes
│   │   ├── keys/               # Keyboard shortcut management
│   │   ├── theme/              # Theme and UI customization
│   │   └── utils/              # Shared utility services
│   ├── auth/                   # Auth layer extensions
│   ├── apps/                   # AppLauncher and app bootstrap helpers
│   ├── db/                     # ORM wrappers/utilities
│   ├── web/                    # HTTP response helpers (horilla.web)
│   ├── menu/                   # Menu registry and builders
│   ├── registry/               # Feature/permission registries
│   ├── shortcuts/              # Shared shortcut helpers
│   └── utils/                  # Core utility modules
├── horilla_crm/                # CRM ERP product (this repository)
│   ├── accounts/               # Company/Account management
│   ├── contacts/               # Contact management
│   ├── leads/                  # Lead management
│   ├── opportunities/          # Deal/Opportunity tracking
│   ├── campaigns/              # Marketing campaigns
│   └── forecast/               # Sales forecasting
# Future ERP product packages plug in alongside horilla_crm at the same level:
#   horilla_sales/              # Quotes, orders, invoicing (planned)
#   horilla_purchase/           # Vendors, POs, GRNs (planned)
├── templates/                  # Global HTML templates
├── static/                     # Static assets
├── media/                      # Uploaded files
├── debian/                     # Debian packaging files
└── windows-installer/          # Windows installer assets
```

## 🔧 Configuration

### Database Configuration

**SQLite (Development)**
```python
DATABASE_URL=sqlite:///db.sqlite3
```

**PostgreSQL (Production)**
```python
DATABASE_URL=postgres://username:password@localhost:5432/horilla_crm
```

**MySQL/MariaDB**
```python
DATABASE_URL=mysql://username:password@localhost:3306/horilla_crm
```

To migrate the existing SQLite database to Supabase PostgreSQL, see
[SUPABASE-MIGRATION.md](SUPABASE-MIGRATION.md).

### Email Configuration
```python
# SMTP Settings
EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST='smtp.gmail.com'
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER='your-email@gmail.com'
EMAIL_HOST_PASSWORD='your-app-password'
```

### Redis Configuration (Optional)
```python
# For production WebSocket scaling
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

## 🔐 Security Features

- **Role-based Access Control**: Granular permissions system
- **CSRF Protection**: Built-in Django CSRF protection
- **SQL Injection Protection**: Django ORM with parameterized queries
- **XSS Protection**: Template auto-escaping and CSP headers
- **Secure Headers**: Security middleware with HSTS, X-Frame-Options
- **Password Validation**: Strong password requirements
- **Session Security**: Secure session configuration
- **API Rate Limiting**: Built-in rate limiting for API endpoints

### Reporting Security Issues

Do **not** create public GitHub issues for security vulnerabilities. Report privately via [GitHub Private Vulnerability Reporting](https://github.com/cybroodoodev/horillacrm/security/advisories/new) only — see [SECURITY.md](SECURITY.md). We do not triage security reports by email.

## 📊 API & Integrations

### REST API
- RESTful API endpoints for all modules
- Token-based authentication
- Pagination and filtering support
- Swagger/OpenAPI documentation

### Webhook Support
- Outbound webhooks for key events
- Configurable event triggers
- Retry mechanism with exponential backoff

### Import/Export
- CSV import/export for all data
- Excel file support
- Bulk operations API
- Data validation and error reporting

## 🌍 Internationalization

### Supported Languages
- English (en)
- Arabic (ar)
- German (de)
- French (fr)
- Korean (ko)
- Malayalam (ml)
- And 20+ more languages

### Adding New Languages
1. Create translation files from the project root: `python manage.py makemessages -l <language_code>`
   - To update **platform strings only** (under `horilla/`), run from that directory: `cd horilla && python ../manage.py makemessages -l <language_code>`
   - Locale files are written to `horilla/locale/` (see `LOCALE_PATHS` in settings)
2. Translate strings in `.po` files
3. Compile messages: `python manage.py compilemessages`
4. Add language to `ALLOWED_LANGUAGES` in settings

## 📈 Performance Optimization

### Database Optimization
- Database indexing on frequently queried fields
- Query optimization with select_related and prefetch_related
- Connection pooling configuration
- Read replica support

### Caching Strategy
- Template fragment caching
- Database query caching
- Static file caching with long expiry
- Redis caching layer (optional)

### Frontend Optimization
- Minified CSS and JavaScript
- Image optimization and lazy loading
- HTMX for dynamic content without full page reloads
- CDN support for static assets

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test horilla_crm.leads

# Run with coverage
coverage run manage.py test
coverage html
```

### Test Types
- **Unit Tests**: Individual component testing
- **Integration Tests**: Module interaction testing
- **API Tests**: REST API endpoint testing
- **UI Tests**: Frontend functionality testing

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure strong `SECRET_KEY`
- [ ] Set up production database (PostgreSQL)
- [ ] Configure email settings
- [ ] Set up SSL/HTTPS
- [ ] Configure static file serving
- [ ] Set up backup strategy
- [ ] Configure monitoring and logging
- [ ] Set up Redis for caching (optional)
- [ ] Configure firewall and security groups

### Deployment Options

1. **Traditional Server**
   - Systemd service files included
   - Nginx configuration templates
   - Debian/Ubuntu package installation

2. **Cloud Platforms**
   - Standard WSGI/ASGI application deployment
   - Cloud VM and Managed PostgreSQL support

## 🔍 Monitoring & Logging

### Application Logs
```bash
# View systemd service logs (Debian/Ubuntu)
journalctl -u horilla-crm -f
```

### Health Checks
- **Application**: `GET /healthz`
- **Database**: Built-in connection monitoring
- **WebSocket**: Real-time connection status

### Metrics Collection
- User activity tracking
- Performance metrics
- Error rate monitoring
- Resource usage statistics

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `python manage.py test`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Create a Pull Request

### Code Style
- Follow PEP 8 for Python code
- Use Black for code formatting
- Run pylint for code analysis
- Write docstrings for all functions and classes

### Reporting Issues
- Use GitHub Issues for bug reports and feature requests
- Include detailed reproduction steps, environment information, and relevant logs
- **Security vulnerabilities:** do **not** use public issues — see [SECURITY.md](SECURITY.md)

## 📚 Documentation

### User Documentation
- **Admin Guide**: Complete administration documentation
- **User Manual**: End-user feature documentation
- **API Reference**: Complete API documentation
- **Integration Guide**: Third-party integration examples

### Developer Documentation
- **Architecture Guide**: System design and components
- **Contributing Guide**: Development setup and guidelines
- **API Documentation**: REST API reference
- **Deployment Guide**: Production deployment instructions

## 🆘 Support

### Community Support
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community Q&A and discussions
- **Documentation**: Comprehensive guides and tutorials

### Enterprise Support
- Professional support available
- Custom development services
- Training and onboarding
- SLA-backed support options

## 📋 System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB
- **OS**: Linux, Windows, macOS
- **Python**: 3.12+
- **Database**: PostgreSQL 12+, MySQL 8.0+, or SQLite 3.x

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **Database**: PostgreSQL 16+
- **Redis**: 6.0+ (for caching)
