@echo off
REM Setup Environment for Finlo CRM

echo Setting up Finlo CRM environment...

cd /d "%~dp0\.."

REM Select an installed Python 3.12+ interpreter
set "PYTHON_CMD=python"
python -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>&1
if errorlevel 1 (
    py -3 -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python 3.12+ is not installed or not available
        exit /b 1
    )
    set "PYTHON_CMD=py -3"
)

REM Create virtual environment
echo Creating Python virtual environment...
if not exist "venv" (
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip
    exit /b 1
)

REM Install requirements
echo Installing Python dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install requirements
        exit /b 1
    )
)

REM Install additional Windows dependencies
echo Installing Windows-specific dependencies...
pip install gunicorn==22.0.0 whitenoise==6.7.0 psycopg2-binary==2.9.9 pywin32 python-windows-service
if errorlevel 1 (
    echo ERROR: Failed to install Windows-specific dependencies
    exit /b 1
)

REM Create necessary directories
echo Creating application directories...
if not defined ProgramData (
    echo ERROR: ProgramData is not defined
    exit /b 1
)
if not exist "%ProgramData%\Finlo-CRM\logs" mkdir "%ProgramData%\Finlo-CRM\logs"
if not exist "%ProgramData%\Finlo-CRM\media" mkdir "%ProgramData%\Finlo-CRM\media"
if not exist "%ProgramData%\Finlo-CRM\config" mkdir "%ProgramData%\Finlo-CRM\config"

REM Copy configuration and generate a unique secret key when needed
python scripts\prepare_config.py
if errorlevel 1 (
    echo ERROR: Failed to prepare the shared application configuration
    exit /b 1
)

echo Environment setup completed successfully!
echo.
echo Run the following commands to get started:
echo   finlo-crm-start.bat    - Start the application
echo   finlo-crm-admin.bat    - Access admin commands
echo.
