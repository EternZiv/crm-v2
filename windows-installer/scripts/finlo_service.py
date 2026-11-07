"""Windows Service Wrapper for Finlo CRM."""

# Standard library imports
import os
import subprocess
import sys
from pathlib import Path

import servicemanager
import win32event

# Third-party imports (Others)
import win32service
import win32serviceutil


class FinloCRMService(win32serviceutil.ServiceFramework):
    """Windows Service wrapper for the Finlo CRM application.

    This service manages the Django application server lifecycle on Windows,
    including starting/stopping the Gunicorn server and collecting static
    files. It extends win32serviceutil.ServiceFramework
    to provide Windows service functionality.
    """

    _svc_name_ = "FinloCRM"
    _svc_display_name_ = "Finlo CRM Application Server"
    _svc_description_ = "Enterprise Customer Relationship Management System"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True
        self.process = None

        # Set up paths
        self.service_dir = Path(__file__).parent.parent
        self.app_dir = self.service_dir
        self.venv_dir = self.service_dir / "venv"
        self.python_exe = self.venv_dir / "Scripts" / "python.exe"
        self.manage_py = self.app_dir / "manage.py"

        # Configuration
        self.host = "127.0.0.1"
        self.port = 8000
        self.workers = 3
        self.timeout = 120

    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_running = False

        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

        win32event.SetEvent(self.hWaitStop)
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, ""),
        )

    def SvcDoRun(self):
        """Start the service"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        try:
            self.run_django_server()
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {str(e)}")
            self.SvcStop()

    def run_django_server(self):
        """Run the Django application using Gunicorn"""
        # Set environment variables
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_SETTINGS_MODULE": "finlo.settings",
                "PYTHONPATH": str(self.app_dir),
            }
        )

        # Load configuration from file
        program_data = os.environ.get("ProgramData")
        if not program_data:
            raise RuntimeError("The Windows ProgramData directory is unavailable.")
        shared_data_dir = Path(program_data) / "Finlo-CRM"
        config_file = shared_data_dir / "config" / "finlo-crm.conf"
        if config_file.exists():
            with open(config_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(("#", ";")) and "=" in line:
                        key, _, value = line.partition("=")
                        env[key.strip()] = value.strip()

        if not env.get("DATABASE_URL"):
            raise RuntimeError(
                f"DATABASE_URL is not configured in {config_file}."
            )

        # Change to application directory
        os.chdir(str(self.app_dir))

        # Database migrations require an explicit operator action.
        try:
            subprocess.run(
                [str(self.python_exe), "manage.py", "collectstatic", "--noinput"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            servicemanager.LogErrorMsg(
                f"Static file collection failed with exit code {e.returncode}; "
                "the server will not start."
            )
            raise RuntimeError("Static file collection failed.") from e

        # Start Gunicorn server
        cmd = [
            str(self.venv_dir / "Scripts" / "gunicorn.exe"),
            "--bind",
            f"{self.host}:{self.port}",
            "--workers",
            str(self.workers),
            "--timeout",
            str(self.timeout),
            "--access-logfile",
            str(shared_data_dir / "logs" / "access.log"),
            "--error-logfile",
            str(shared_data_dir / "logs" / "error.log"),
            "--log-level",
            "info",
            "finlo.wsgi:application",
        ]

        servicemanager.LogInfoMsg(f"Starting server: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            env=env,
            cwd=str(self.app_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for service to stop
        while self.is_running:
            # Check if process is still running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                servicemanager.LogErrorMsg(
                    f"Server process exited. STDOUT: {stdout}, STDERR: {stderr}"
                )
                break

            # Wait for stop signal
            rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
            if rc == win32event.WAIT_OBJECT_0:
                break


def install_service():
    """Install the Windows service"""
    try:
        win32serviceutil.InstallService(
            FinloCRMService,
            FinloCRMService._svc_name_,
            FinloCRMService._svc_display_name_,
            description=FinloCRMService._svc_description_,
        )
        print("Service installed successfully")
        return True
    except Exception as e:
        print(f"Failed to install service: {e}")
        return False


def remove_service():
    """Remove the Windows service"""
    try:
        win32serviceutil.RemoveService(FinloCRMService._svc_name_)
        print("Service removed successfully")
        return True
    except Exception as e:
        print(f"Failed to remove service: {e}")
        return False


def start_service():
    """Start the Windows service"""
    try:
        win32serviceutil.StartService(FinloCRMService._svc_name_)
        print("Service started successfully")
        return True
    except Exception as e:
        print(f"Failed to start service: {e}")
        return False


def stop_service():
    """Stop the Windows service"""
    try:
        win32serviceutil.StopService(FinloCRMService._svc_name_)
        print("Service stopped successfully")
        return True
    except Exception as e:
        print(f"Failed to stop service: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FinloCRMService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FinloCRMService)
