@echo off
REM Stop Finlo CRM Application

echo Stopping Finlo CRM...

REM Stop Windows service if running
sc query "FinloCRM" >nul 2>&1
if not errorlevel 1 (
    echo Stopping Finlo CRM service...
    net stop FinloCRM
)

REM Stop only processes launched from Finlo CRM's virtual environment
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-finlo-processes.ps1"
if errorlevel 1 (
    echo ERROR: Failed to stop all Finlo CRM processes
    exit /b 1
)

echo Finlo CRM stopped.
pause
