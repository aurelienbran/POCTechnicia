@echo off
echo Starting FastAPI backend...
echo.

set "SCRIPTS_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPTS_DIR%..\.."
set "PYTHON_ENV=%PROJECT_DIR%\.venv"

:: Check if Python environment exists
if not exist "%PYTHON_ENV%" (
    echo ERROR: Python environment does not exist at: %PYTHON_ENV%
    echo Please run setup_project.bat first.
    pause
    exit /b 1
)

:: Start backend with cmd /k to keep the window open
echo Starting FastAPI at http://localhost:8000
start "FastAPI Backend" cmd /k "cd /d "%PROJECT_DIR%" && call "%PYTHON_ENV%\Scripts\activate.bat" && python -m uvicorn app.main:app --reload --port 8000"
echo FastAPI backend started in a new window.
