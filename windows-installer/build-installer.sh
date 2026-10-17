#!/bin/bash
# Cross-platform build script for Finlo CRM Windows Installer
# Can be run on macOS/Linux with NSIS tools

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building Finlo CRM Windows Installer..."
echo "========================================="

cd "$SCRIPT_DIR"

# Check if NSIS is available (for cross-platform builds)
if command -v makensis &> /dev/null; then
    NSIS_CMD="makensis"
elif command -v nsis &> /dev/null; then
    NSIS_CMD="nsis"
elif [ -f "/usr/bin/makensis" ]; then
    NSIS_CMD="/usr/bin/makensis"
else
    echo "ERROR: NSIS not found"
    echo ""
    echo "On Ubuntu/Debian:"
    echo "  sudo apt-get install nsis"
    echo ""
    echo "On macOS:"
    echo "  brew install makensis"
    echo ""
    echo "On Windows:"
    echo "  Download from https://nsis.sourceforge.io/"
    echo ""
    exit 1
fi

# Check required files
echo "Checking required files..."
required_files=(
    "finlo-crm-installer.nsi"
    "scripts/finlo_service.py"
    "scripts/setup-environment.bat"
    "scripts/finlo-crm-start.bat"
    "scripts/finlo-crm-admin.bat"
    "scripts/finlo-crm-stop.bat"
    "scripts/install-service.bat"
    "scripts/uninstall-service.bat"
    "config/finlo-crm.conf"
    "config/logging.conf"
    "config/requirements-windows.txt"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file not found: $file"
        exit 1
    fi
done

# Create directories and resources
echo "Preparing resources..."
mkdir -p icons resources

# Copy LICENSE file
if [[ -f "../LICENSE" ]]; then
    cp "../LICENSE" "resources/LICENSE.txt"
else
    echo "License file not found - creating placeholder"
    echo "Finlo CRM License" > "resources/LICENSE.txt"
fi

# Create installation README
cat > "resources/README.txt" << 'EOF'
Finlo CRM Windows Installation
================================

This installer will set up Finlo CRM on your Windows system.

System Requirements:
- Windows 10 or later (64-bit)
- Python 3.12 or later
- At least 2GB free disk space
- Administrator privileges for service installation

Installation Process:
1. Core application files are installed to Program Files
2. Configuration files are placed in your user AppData folder
3. A Python virtual environment is created with dependencies
4. Optional Windows service installation for background operation

After Installation:
- Access via Start Menu shortcuts
- Default URL: http://localhost:8000
- Admin interface: Use finlo-crm-admin.bat

For support, visit: https://github.com/EternZiv/crm-v2
EOF

# Build the installer
echo "Building installer with NSIS..."
"$NSIS_CMD" finlo-crm-installer.nsi

# Check if installer was created
if [[ -f "Finlo-CRM-1.0.0-Setup.exe" ]]; then
    echo ""
    echo "SUCCESS: Installer built successfully!"
    echo "File: Finlo-CRM-1.0.0-Setup.exe"
    echo "Size: $(du -h "Finlo-CRM-1.0.0-Setup.exe" | cut -f1)"
    echo ""
    echo "You can now distribute this installer to install Finlo CRM on Windows systems."
    echo ""
    echo "Next steps:"
    echo "1. Test the installer on a Windows machine"
    echo "2. Sign the installer for production distribution"
    echo "3. Create documentation for end users"
else
    echo "ERROR: Installer file not found after build"
    exit 1
fi

echo ""
echo "Build completed successfully!"
