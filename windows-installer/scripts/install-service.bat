@echo off
REM Install Finlo CRM as Windows Service

echo Installing Finlo CRM Windows Service...

cd /d "%~dp0\.."

REM Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install the service
echo Installing service...
python scripts\finlo_service.py install

if errorlevel 1 (
    echo ERROR: Failed to install service
    exit /b 1
)

REM Keep the service stopped until the shared Supabase URL is configured.
sc config FinloCRM start= demand
if errorlevel 1 (
    echo ERROR: Failed to configure service startup mode
    exit /b 1
)

if /i "%~1"=="/install-only" (
    echo Service installed and left stopped until the database is configured.
    exit /b 0
)

echo Configure DATABASE_URL in:
echo   %ProgramData%\Finlo-CRM\config\finlo-crm.conf
echo Then start the service with: net start FinloCRM
