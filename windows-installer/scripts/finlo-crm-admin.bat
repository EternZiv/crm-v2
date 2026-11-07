@echo off
REM Finlo CRM Administration Interface

setlocal enabledelayedexpansion

echo Finlo CRM Administration Interface
echo ===================================

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

:menu
echo.
echo Available commands:
echo 1. Create superuser
echo 2. Apply Supabase migrations (changes the shared database schema)
echo 3. Collect static files
echo 4. Open Django shell
echo 5. Run isolated security tests
echo 6. Show application status
echo 7. View logs
echo 8. Custom Django command
echo 0. Exit
echo.

set /p choice="Enter your choice (0-8): "

if "%choice%"=="1" goto create_superuser
if "%choice%"=="2" goto migrate
if "%choice%"=="3" goto collectstatic
if "%choice%"=="4" goto shell
if "%choice%"=="5" goto test
if "%choice%"=="6" goto status
if "%choice%"=="7" goto logs
if "%choice%"=="8" goto custom_command
if "%choice%"=="0" goto exit
goto menu

:create_superuser
echo Creating superuser...
python manage.py createsuperuser
goto menu

:migrate
echo Running database migrations...
python manage.py migrate
goto menu

:collectstatic
echo Collecting static files...
python manage.py collectstatic --noinput
goto menu

:shell
echo Opening Django shell...
python manage.py shell
goto menu

:test
echo Running isolated security tests with an in-memory database...
python manage.py test --settings=finlo.settings.security_test
goto menu

:status
echo Application Status:
echo ===================
sc query "FinloCRM" 2>nul
if errorlevel 1 (
    echo Service: Not installed
) else (
    echo Service: Installed
)

netstat -an | find "127.0.0.1:8000" >nul
if errorlevel 1 (
    echo Server: Not running on port 8000
) else (
    echo Server: Running on http://127.0.0.1:8000
)

echo.
echo Database status:
python manage.py check --database default
goto menu

:logs
echo Recent logs:
echo ===========
if exist "%ProgramData%\Finlo-CRM\logs\error.log" (
    echo Error log (last 20 lines):
    powershell "Get-Content '%ProgramData%\Finlo-CRM\logs\error.log' -Tail 20"
) else (
    echo No error log found
)
echo.
if exist "%ProgramData%\Finlo-CRM\logs\access.log" (
    echo Access log (last 10 lines):
    powershell "Get-Content '%ProgramData%\Finlo-CRM\logs\access.log' -Tail 10"
) else (
    echo No access log found
)
goto menu

:custom_command
set /p command="Enter Django management command: "
echo Running: python manage.py %command%
python manage.py %command%
goto menu

:exit
echo Goodbye!
pause
