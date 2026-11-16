@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\streamlit.exe" (
    echo Project environment is missing. Create it and install requirements first:
    echo   python -m venv .venv
    echo   .venv\Scripts\python -m pip install -r requirements.txt
    pause
    exit /b 1
)

PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_project.ps1" dashboard
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
