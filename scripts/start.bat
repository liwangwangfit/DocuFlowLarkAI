@echo off
setlocal
chcp 65001 >nul
cls
echo ==========================================
echo    DocuFlow - Desktop Mode
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%..\backend"

if not exist "%BACKEND_DIR%\desktop_app.py" (
    echo [ERROR] desktop_app.py not found:
    echo         %BACKEND_DIR%\desktop_app.py
    pause
    exit /b 1
)

cd /d "%BACKEND_DIR%" || (
    echo [ERROR] Failed to enter backend directory:
    echo         %BACKEND_DIR%
    pause
    exit /b 1
)

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [WARN] Virtual environment not found. Using system Python.
)

echo [INFO] Starting desktop app...
echo [INFO] For API-only mode, run scripts\start_backend.bat
echo.

python desktop_app.py
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo [ERROR] Desktop app exited with code %EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
