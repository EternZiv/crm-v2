# Finlo CRM Debian Package

This directory contains the Debian packaging configuration for Finlo CRM.

## Package Information

- **Package Name**: finlo-crm
- **Version**: 1.0.0-1
- **Architecture**: all
- **License**: LGPL-2.1+
- **Maintainer**: Finlo CRM Team

## Installation Locations

- **Application**: `/opt/finlo-crm/`
- **Configuration**: `/etc/finlo-crm/`
- **Data**: `/var/lib/finlo-crm/`
- **Logs**: `/var/log/finlo-crm/`
- **Service**: `systemd` (finlo-crm.service)
- **User**: `finlo-crm` (system user)

## Building the Package

### Prerequisites (Ubuntu/Debian)

```bash
sudo apt-get install dpkg-dev debhelper python3-dev python3-venv \
                     build-essential libjpeg-dev zlib1g-dev \
                     libfreetype6-dev liblcms2-dev libopenjp2-7-dev \
                     libwebp-dev libpq-dev
```

### Build Process

```bash
# Method 1: Use the build script
./debian/build-package.sh

# Method 2: Manual build
dpkg-buildpackage -us -uc -b
```

## Installation

```bash
# Install the package
sudo dpkg -i ../finlo-crm_*.deb

# Fix any dependency issues
sudo apt-get install -f
```

## Configuration

1. **Edit configuration file**:
   ```bash
   sudo nano /etc/finlo-crm/finlo-crm.conf
   ```

2. **Key settings to update**:
   - `SECRET_KEY`: Auto-generated, but can be changed
   - `DEBUG`: Set to 0 for production
   - `ALLOWED_HOSTS`: Add your domain/IP
   - `DATABASE_URL`: Configure your database connection

3. **Database setup**:
   Configure `DATABASE_URL` in `/etc/finlo-crm/finlo-crm.conf` with the
   Supabase PostgreSQL connection URL from Project Settings > Database. Require
   TLS with `sslmode=require`; do not configure a local database.

4. **Create superuser**:
   ```bash
   sudo -u finlo-crm finlo-crm-manage createsuperuser
   ```

## Service Management

```bash
# Start the service
sudo systemctl start finlo-crm

# Enable automatic startup
sudo systemctl enable finlo-crm

# Check status
sudo systemctl status finlo-crm

# View logs
sudo journalctl -u finlo-crm -f

# Restart service
sudo systemctl restart finlo-crm
```

## Management Commands

The package provides a wrapper script for Django management commands:

```bash
# General syntax
sudo -u finlo-crm finlo-crm-manage <command>

# Examples
sudo -u finlo-crm finlo-crm-manage migrate
sudo -u finlo-crm finlo-crm-manage collectstatic
sudo -u finlo-crm finlo-crm-manage createsuperuser
sudo -u finlo-crm finlo-crm-manage shell
```

## Web Server Configuration

### Nginx Example

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/finlo-crm/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location /media/ {
        alias /opt/finlo-crm/media/;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }
}
```

## Package Files

- `control`: Package metadata and dependencies
- `rules`: Build instructions
- `compat`: Debhelper compatibility level
- `install`: File installation mapping
- `changelog`: Version history
- `copyright`: License information
- `postinst`: Post-installation script
- `prerm`: Pre-removal script
- `postrm`: Post-removal script
- `finlo-crm.service`: Systemd service file
- `finlo-crm.logrotate`: Log rotation configuration
- `build-package.sh`: Build automation script

## Troubleshooting

### Service won't start
```bash
# Check service status
sudo systemctl status finlo-crm

# Check logs
sudo journalctl -u finlo-crm -n 50

# Check configuration
sudo -u finlo-crm finlo-crm-manage check
```

### Database issues
```bash
# Run migrations
sudo -u finlo-crm finlo-crm-manage migrate

# Check database connection
sudo -u finlo-crm finlo-crm-manage dbshell
```

### Permission issues
```bash
# Fix ownership
sudo chown -R finlo-crm:finlo-crm /opt/finlo-crm
sudo chown -R finlo-crm:finlo-crm /var/lib/finlo-crm
sudo chown -R finlo-crm:finlo-crm /var/log/finlo-crm
```

## Uninstallation

```bash
# Remove package (keep data)
sudo apt-get remove finlo-crm

# Complete removal (including data)
sudo apt-get purge finlo-crm
sudo rm -rf /var/lib/finlo-crm /var/log/finlo-crm
```

## Development

To modify the package:

1. Update version in `debian/changelog`
2. Modify configuration in relevant files
3. Test build: `./debian/build-package.sh`
4. Test installation in a clean environment

## Support

- GitHub: https://github.com/EternZiv/crm-v2
- Documentation: Available in the application
- Issues: Use GitHub issue tracker
