@echo off
REM Start Finlo CRM Application

setlocal enabledelayedexpansion

echo Starting Finlo CRM...

cd /d "%~dp0\.."

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run setup-environment.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set environment variables
set DJANGO_SETTINGS_MODULE=finlo.settings
set PYTHONPATH=%CD%

REM Load configuration from file
set CONFIG_FILE=%ProgramData%\Finlo-CRM\config\finlo-crm.conf
if exist "%CONFIG_FILE%" (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        if not "%%a"=="" set "%%a=%%b"
    )
)

if not defined DATABASE_URL (
    echo ERROR: DATABASE_URL is not configured.
    echo Set it in "%ProgramData%\Finlo-CRM\config\finlo-crm.conf" before starting.
    exit /b 1
)

REM Collect static files
echo Collecting static files...
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo ERROR: Static file collection failed
    exit /b 1
)

REM Check if port is available
echo Checking if port 8000 is available...
netstat -an | find "127.0.0.1:8000" >nul
if not errorlevel 1 (
    echo WARNING: Port 8000 is already in use
    echo Another instance might be running
)

REM Start the server
echo Starting Finlo CRM server on http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start Gunicorn server
gunicorn ^
    --bind 127.0.0.1:8000 ^
    --workers 3 ^
    --timeout 120 ^
    --access-logfile "%ProgramData%\Finlo-CRM\logs\access.log" ^
    --error-logfile "%ProgramData%\Finlo-CRM\logs\error.log" ^
    --log-level info ^
    finlo.wsgi:application

echo Server stopped.
pause
