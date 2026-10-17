# Finlo CRM Windows Installer

This directory contains the complete Windows installer infrastructure for Finlo CRM, including NSIS installer script, Windows service integration, and management tools.

## Overview

The Windows installer provides:
- **Automated Installation**: One-click setup with dependency management
- **Windows Service**: Background operation, started explicitly by an administrator
- **Management Tools**: Batch scripts for administration and control
- **System Integration**: Start Menu shortcuts and desktop integration
- **Security**: Runs as dedicated service with proper permissions

## Prerequisites

### For Building the Installer:
- **NSIS (Nullsoft Scriptable Install System)**: Download from https://nsis.sourceforge.io/
- **Windows 10 or later** (64-bit)
- **Administrator privileges** for building and testing

### For Target Systems:
- **Windows 10 or later** (64-bit)
- **Python 3.12+** (installer can download if missing)
- **Administrator privileges** for service installation
- **2GB+ free disk space**

## Building the Installer

### Method 1: Automated Build
```batch
cd windows-installer
build-installer.bat
```

### Method 2: Manual Build
```batch
cd windows-installer
makensis finlo-crm-installer.nsi
```

## Installation Structure

### Installation Directories:
- **Application**: `C:\Program Files\Finlo-CRM\`
- **Configuration**: `%ProgramData%\Finlo-CRM\config\`
- **Logs**: `%ProgramData%\Finlo-CRM\logs\`
- **Media Files**: `%ProgramData%\Finlo-CRM\media\`

### Installed Components:
- Core Finlo CRM application
- Python virtual environment with dependencies
- Windows service wrapper
- Management batch scripts
- Configuration files
- Start Menu shortcuts

## Management Scripts

### Core Scripts:
- **`finlo-crm-start.bat`**: Start the application server
- **`finlo-crm-stop.bat`**: Stop the application server
- **`finlo-crm-admin.bat`**: Administration interface
- **`setup-environment.bat`**: Environment setup (auto-run during install)

### Service Management:
- **`install-service.bat`**: Install as Windows service
- **`uninstall-service.bat`**: Remove Windows service

### Service Features:
- **Manual Startup**: Installed stopped and set to demand-start
- **Background Operation**: Runs without user login
- **Crash Recovery**: Automatic restart on failure
- **Logging**: Comprehensive error and access logs
- **Security**: Runs with minimal privileges

## Configuration

### Main Configuration File:
`%ProgramData%\Finlo-CRM\config\finlo-crm.conf`

Key settings:
```ini
# Security
# SECRET_KEY is generated uniquely during setup; keep it private
DEBUG=0

# Network
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000

# Required Supabase PostgreSQL connection URL (sslmode=require)
DATABASE_URL=<Supabase connection URL>

## Usage Instructions

### After Installation:

1. **First-time Setup**:
   Configure the Supabase `DATABASE_URL` before starting the application.
   This installer does not create a local database. Existing Supabase users
   should sign in with their existing account; create an administrator only
   when authorized.
   ```batch
   # Create administrative user
   "C:\Program Files\Finlo-CRM\scripts\finlo-crm-admin.bat"
   # Choose option 1 only if you are authorized to create an administrator
   ```

2. **Start Application**:
   - Configure `DATABASE_URL` in the machine-wide configuration first.
   - **Manual**: Use Start Menu → Finlo CRM
   - **Service**: Start explicitly with `net start FinloCRM` after configuration.
     The installer does not start the service or configure automatic startup.
   - **URL**: http://localhost:8000

3. **Administration**:
   ```batch
   # Open admin interface
   "C:\Program Files\Finlo-CRM\scripts\finlo-crm-admin.bat"
   ```

4. **Service Management**:
   ```batch
   # Install service (requires admin); installed in demand-start mode
   "C:\Program Files\Finlo-CRM\scripts\install-service.bat"

   # Start and stop explicitly:
   net start FinloCRM
   net stop FinloCRM
   ```

## Database Setup

Finlo CRM requires Supabase PostgreSQL. Configure `DATABASE_URL` in
`%ProgramData%\Finlo-CRM\config\finlo-crm.conf` using the Supabase Project
Settings > Database connection URL, with `sslmode=require`. Local SQLite and
MySQL are not supported application databases. Never commit or share the
connection string.

The installer and application startup do not apply database migrations. Before
starting a newly installed or upgraded version, review the release's migrations
and back up the shared database. Then run the admin script and select option 2
to apply migrations intentionally. This changes the Supabase schema.

## Web Server Integration

### IIS Integration:
1. Install IIS with CGI support
2. Install Python CGI handler
3. Configure the virtual directory to point to the Finlo CRM installation

### Nginx for Windows:
1. Download Nginx for Windows
2. Configure reverse proxy:
   ```nginx
   server {
       listen 80;
       server_name localhost;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Security Considerations

### Firewall:
- **Default**: Only localhost access (127.0.0.1:8000)
- **Production**: Configure Windows Firewall for external access
- **HTTPS**: Use reverse proxy (IIS/Nginx) for SSL termination

### User Permissions:
- **Service**: Runs as LocalService account
- **Files**: Application files read-only, data files writable
- **Network**: Bound to localhost by default

### Hardening:
- Keep the generated `SECRET_KEY` private and back it up securely
- Use strong database passwords
- Enable HTTPS in production
- Regular security updates

## Troubleshooting

### Installation Issues:
1. **Permission Denied**: Run installer as Administrator
2. **Python Not Found**: Install Python 3.12+ manually
3. **Port 8000 in Use**: Change port in configuration or stop conflicting service

### Service Issues:
1. **Service Won't Start**: Check Windows Event Viewer
2. **Database Errors**: Verify database configuration and connectivity
3. **Permission Errors**: Ensure service has proper file permissions

### Application Issues:
1. **Can't Access Web Interface**: Check if server is running on correct port
2. **Static Files Missing**: Run `collectstatic` command via admin interface
3. **Database Migration Errors**: Review the migration output. Apply migrations explicitly from the admin interface only after reviewing and backing up the shared database; startup does not migrate automatically.

### Log Files:
- **Application Logs**: `%ProgramData%\Finlo-CRM\logs\`
- **Service Logs**: Windows Event Viewer → Applications and Services
- **Web Server Logs**: Access and error logs in logs directory

## File Structure

```
windows-installer/
├── finlo-crm-installer.nsi     # Main NSIS installer script
├── build-installer.bat           # Automated build script
├── scripts/                      # Management scripts
│   ├── finlo_service.py        # Windows service wrapper
│   ├── setup-environment.bat     # Environment setup
│   ├── finlo-crm-start.bat     # Start application
│   ├── finlo-crm-stop.bat      # Stop application
│   ├── finlo-crm-admin.bat     # Admin interface
│   ├── install-service.bat       # Install service
│   └── uninstall-service.bat     # Remove service
├── config/                       # Configuration files
│   ├── finlo-crm.conf          # Main configuration
│   ├── logging.conf              # Logging configuration
│   └── requirements-windows.txt  # Windows-specific dependencies
├── icons/                        # Application icons (add custom)
├── resources/                    # Installer resources
└── README.md                     # This file
```

## Distribution

### Signing the Installer:
For production distribution, sign the installer with a code signing certificate:
```batch
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com Finlo-CRM-1.0.0-Setup.exe
```

### Deployment Options:
1. **Direct Distribution**: Share the .exe file
2. **Group Policy**: Deploy via Windows Group Policy
3. **SCCM**: Deploy via System Center Configuration Manager
4. **Chocolatey**: Create Chocolatey package for easy updates

## Support

- **Documentation**: Available in installed application
- **GitHub**: https://github.com/EternZiv/crm-v2
- **Issues**: Use GitHub issue tracker
- **Community**: Check project documentation for community resources

---

**Note**: This installer is designed for Windows environments. For Linux deployment, use the Debian package in the `debian/` directory.
