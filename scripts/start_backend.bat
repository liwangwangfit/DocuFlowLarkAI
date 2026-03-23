@echo off
setlocal
chcp 65001 >nul
cls
echo ==========================================
echo    DocuFlow - API Mode
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%..\backend"

if not exist "%BACKEND_DIR%\main.py" (
    echo [ERROR] main.py not found:
    echo         %BACKEND_DIR%\main.py
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
)

echo [INFO] Starting backend service...
echo [INFO] URL: http://127.0.0.1:8000
echo.

python main.py
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo [ERROR] Backend exited with code %EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
