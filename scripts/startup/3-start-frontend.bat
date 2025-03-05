@echo off
echo Starting React frontend...
echo.

set "SCRIPTS_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPTS_DIR%..\.."
set "FRONTEND_DIR=%PROJECT_DIR%\frontend"

:: Check if frontend directory exists
if not exist "%FRONTEND_DIR%" (
    echo ERROR: Frontend directory does not exist at: %FRONTEND_DIR%
    pause
    exit /b 1
)

:: Start frontend with cmd /k to keep the window open
echo Starting React frontend at http://localhost:3001
start "React Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"
echo React frontend started in a new window.
