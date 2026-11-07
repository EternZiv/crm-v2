; Finlo CRM Windows Installer Script
; Uses NSIS (Nullsoft Scriptable Install System)

!define PRODUCT_NAME "Finlo CRM"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "Finlo CRM Team"
!define PRODUCT_WEB_SITE "https://github.com/EternZiv/crm-v2"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\finlo-crm.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Finlo-CRM"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"
!define PRODUCT_STARTMENU_REGVAL "NSIS:StartMenuDir"

; Modern UI
!include "MUI2.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

; Installer properties
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "Finlo-CRM-${PRODUCT_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES64\Finlo-CRM"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show
RequestExecutionLevel admin
Unicode True

; Version Information
VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "Comments" "Enterprise Customer Relationship Management System"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "LegalCopyright" "© 2024 ${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileDescription" "${PRODUCT_NAME} Installer"
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "ProductVersion" "${PRODUCT_VERSION}"

; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "..\static\assets\img\finlo-favicon.ico"
!define MUI_UNICON "..\static\assets\img\finlo-favicon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "icons\header.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP "icons\welcome.bmp"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "resources\LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY

; Start Menu Folder Page Configuration
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "${PRODUCT_UNINST_ROOT_KEY}"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "${PRODUCT_UNINST_KEY}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "${PRODUCT_STARTMENU_REGVAL}"
Var StartMenuFolder
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

!insertmacro MUI_PAGE_INSTFILES

; Finish Page Configuration
!define MUI_FINISHPAGE_RUN "$INSTDIR\scripts\finlo-crm-start.bat"
!define MUI_FINISHPAGE_RUN_TEXT "Start Finlo CRM Server"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.txt"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Show README"
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Reserve Files
!insertmacro MUI_RESERVEFILE_LANGDLL

; Sections
Section "Core Application" SecCore
  SectionIn RO
  SetOutPath "$INSTDIR"

  ; Copy application files
  File /r /x ".git*" /x ".env" /x ".env.*" /x ".venv" /x "venv" /x "db.sqlite3" /x "staticfiles" /x "debian" /x "windows-installer" /x "test*.json" /x "__pycache__" "..\"

  ; Copy Windows-specific files
  SetOutPath "$INSTDIR\scripts"
  File "scripts\*.bat"
  File "scripts\*.py"
  File "scripts\*.ps1"

  SetOutPath "$INSTDIR\config"
  File "config\*.conf"
  File "config\*.ini"

  ; Create data directories
  CreateDirectory "$COMMONAPPDATA\Finlo-CRM\logs"
  CreateDirectory "$COMMONAPPDATA\Finlo-CRM\media"
  CreateDirectory "$COMMONAPPDATA\Finlo-CRM\config"

  ; Install Python if not present
  Call InstallPython

  ; Create virtual environment and install dependencies
  DetailPrint "Creating Python virtual environment..."
  nsExec::ExecToLog '"$COMSPEC" /c ""$INSTDIR\scripts\setup-environment.bat""'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Finlo CRM environment setup failed (exit code $0)."
    Abort
  ${EndIf}

  ; Install Windows service
  DetailPrint "Installing Windows service..."
  nsExec::ExecToLog '"$COMSPEC" /c ""$INSTDIR\scripts\install-service.bat" /install-only"'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Finlo CRM service installation failed (exit code $0)."
    Abort
  ${EndIf}
SectionEnd

Section "Desktop Shortcut" SecDesktop
  CreateShortCut "$DESKTOP\Finlo CRM.lnk" "$INSTDIR\scripts\finlo-crm-start.bat" "" "$INSTDIR\static\assets\img\finlo-favicon.ico"
SectionEnd

Section "Quick Launch" SecQuickLaunch
  CreateShortCut "$QUICKLAUNCH\Finlo CRM.lnk" "$INSTDIR\scripts\finlo-crm-start.bat" "" "$INSTDIR\static\assets\img\finlo-favicon.ico"
SectionEnd

; Installation Functions
Function .onInit
  ; Check Windows version (Windows 10 or later)
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK "This application requires Windows 10 or later."
    Abort
  ${EndIf}

  ; Check for 64-bit system
  ${IfNot} ${RunningX64}
    MessageBox MB_OK "This application requires a 64-bit Windows system."
    Abort
  ${EndIf}

  ; Check if already installed
  ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString"
  StrCmp $R0 "" done

  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
  "${PRODUCT_NAME} is already installed. $\n$\nClick 'OK' to remove the previous version or 'Cancel' to cancel this upgrade." \
  IDOK uninst
  Abort

  uninst:
    ClearErrors
    ExecWait '$R0 _?=$INSTDIR'

    IfErrors no_remove_uninstaller done
    no_remove_uninstaller:

  done:
FunctionEnd

Function InstallPython
  ; Check if Python 3.12+ is installed
  nsExec::ExecToStack 'python -c "import sys; sys.exit(sys.version_info < (3, 12))"'
  Pop $0
  Pop $1

  ${If} $0 != 0
    MessageBox MB_YESNO "Python 3.12+ is required but not found. Would you like to download and install Python?" IDYES download_python IDNO skip_python

    download_python:
      DetailPrint "Downloading Python 3.12..."
      inetc::get "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" "$TEMP\python-installer.exe"
      Pop $0
      ${If} $0 == "OK"
        DetailPrint "Installing Python..."
        ExecWait '"$TEMP\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0' $0
        Delete "$TEMP\python-installer.exe"
        ${If} $0 != 0
          MessageBox MB_OK "Python installation failed. Please install Python 3.12+ manually."
          Abort
        ${EndIf}
      ${Else}
        MessageBox MB_OK "Failed to download Python. Please install Python 3.12+ manually."
        Abort
      ${EndIf}

      Goto python_installed
    skip_python:
      Abort
  ${EndIf}
  python_installed:
FunctionEnd

; Post-installation
Section -AdditionalIcons
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
  CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
  CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Finlo CRM.lnk" "$INSTDIR\scripts\finlo-crm-start.bat" "" "$INSTDIR\static\assets\img\finlo-favicon.ico"
  CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Finlo CRM Admin.lnk" "$INSTDIR\scripts\finlo-crm-admin.bat" "" "$INSTDIR\static\assets\img\finlo-favicon.ico"
  CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Stop Finlo CRM.lnk" "$INSTDIR\scripts\finlo-crm-stop.bat" "" "$INSTDIR\static\assets\img\finlo-favicon.ico"
  CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Uninstall Finlo CRM.lnk" "$INSTDIR\uninst.exe"
  !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\static\assets\img\finlo-favicon.ico"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "NoRepair" 1
SectionEnd

; Component Descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Core Finlo CRM application files and dependencies"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a desktop shortcut for Finlo CRM"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecQuickLaunch} "Create a quick launch shortcut for Finlo CRM"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Uninstaller Section
Section Uninstall
  ; Stop service
  nsExec::ExecToLog '"$INSTDIR\scripts\uninstall-service.bat"'

  ; Remove registry keys
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"

  ; Remove shortcuts
  !insertmacro MUI_STARTMENU_GETFOLDER "Application" $StartMenuFolder
  Delete "$SMPROGRAMS\$StartMenuFolder\*.*"
  RMDir "$SMPROGRAMS\$StartMenuFolder"
  Delete "$DESKTOP\Finlo-CRM.lnk"
  Delete "$QUICKLAUNCH\Finlo-CRM.lnk"
  Delete "$DESKTOP\Finlo CRM.lnk"
  Delete "$QUICKLAUNCH\Finlo CRM.lnk"

  ; Remove application files
  RMDir /r "$INSTDIR"

  ; Ask about user data
  MessageBox MB_YESNO "Do you want to remove user data and configuration files?" IDNO skip_data
  RMDir /r "$COMMONAPPDATA\Finlo-CRM"

  skip_data:
  SetAutoClose true
SectionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort
FunctionEnd
