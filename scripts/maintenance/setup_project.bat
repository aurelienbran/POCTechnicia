@echo off
setlocal enableextensions enabledelayedexpansion
title Configuration du projet POC TECHNICIA
echo ===== Configuration complete du projet POC TECHNICIA =====
echo.

:: Definir les chemins
set "SCRIPTS_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPTS_DIR%.."
set "FRONTEND_DIR=%PROJECT_DIR%\frontend"
set "PYTHON_ENV=%PROJECT_DIR%\.venv"
set "QDRANT_STORAGE=%PROJECT_DIR%\qdrant_storage"

:: Definir les couleurs
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "RESET=[0m"

echo %YELLOW%[1/5] Verification des prerequis%RESET%
echo ------------------------------

:: Verifier si Python est installe
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo %RED%Erreur: Python n'est pas installe ou n'est pas dans le PATH.%RESET%
    echo Veuillez installer Python depuis https://www.python.org/
    exit /b 1
)

:: Verifier si Node.js est installe
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo %RED%Erreur: Node.js n'est pas installe ou n'est pas dans le PATH.%RESET%
    echo Veuillez installer Node.js depuis https://nodejs.org/
    exit /b 1
)

:: Verifier si npm est installe
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo %RED%Erreur: npm n'est pas installe ou n'est pas dans le PATH.%RESET%
    echo Veuillez installer Node.js depuis https://nodejs.org/
    exit /b 1
)

echo %GREEN%Tous les prerequis sont installes.%RESET%
echo.

echo %YELLOW%[2/5] Configuration du fichier .env%RESET%
echo ------------------------------

:: Verifier si le fichier .env existe, sinon le creer a partir de .env.example
if not exist "%PROJECT_DIR%\.env" (
    if exist "%PROJECT_DIR%\.env.example" (
        echo Creation du fichier .env a partir de .env.example...
        copy "%PROJECT_DIR%\.env.example" "%PROJECT_DIR%\.env"
        echo %GREEN%Fichier .env cree avec succes.%RESET%
        echo %YELLOW%IMPORTANT: Veuillez editer le fichier .env pour configurer vos cles API.%RESET%
    ) else (
        echo %RED%Attention: Le fichier .env.example n'existe pas.%RESET%
        echo Creation d'un fichier .env minimal...
        echo # Configuration POC TECHNICIA > "%PROJECT_DIR%\.env"
        echo VOYAGE_API_KEY=your_voyage_api_key_here >> "%PROJECT_DIR%\.env"
        echo ANTHROPIC_API_KEY=your_anthropic_api_key_here >> "%PROJECT_DIR%\.env"
        echo QDRANT_HOST=localhost >> "%PROJECT_DIR%\.env"
        echo QDRANT_PORT=6333 >> "%PROJECT_DIR%\.env"
        echo %YELLOW%IMPORTANT: Veuillez editer le fichier .env pour configurer vos cles API.%RESET%
    )
)
echo.

echo %YELLOW%[3/5] Configuration de l'environnement virtuel Python%RESET%
echo ------------------------------

:: Creer l'environnement virtuel s'il n'existe pas
if not exist "%PYTHON_ENV%" (
    echo Creation de l'environnement virtuel Python...
    python -m venv "%PYTHON_ENV%"
    echo %GREEN%Environnement virtuel cree avec succes.%RESET%
) else (
    echo L'environnement virtuel existe deja.
)

:: Activer l'environnement virtuel et installer les dependances
echo Installation des dependances Python...
call "%PYTHON_ENV%\Scripts\activate.bat" && (
    python -m pip install --upgrade pip
    pip install -r "%PROJECT_DIR%\requirements.txt"
    echo %GREEN%Dependances Python installees avec succes.%RESET%
) || (
    echo %RED%Erreur lors de l'installation des dependances Python.%RESET%
    exit /b 1
)
echo.

echo %YELLOW%[4/5] Configuration du frontend React%RESET%
echo ------------------------------

:: Verifier si le dossier frontend existe
if not exist "%FRONTEND_DIR%" (
    echo %RED%Erreur: Le dossier frontend n'existe pas: %FRONTEND_DIR%%RESET%
    exit /b 1
)

:: Aller dans le dossier frontend et installer les dependances
echo Installation des dependances du frontend...
cd /d "%FRONTEND_DIR%" && (
    call npm install
    echo %GREEN%Dependances du frontend installees avec succes.%RESET%
) || (
    echo %RED%Erreur lors de l'installation des dependances du frontend.%RESET%
    exit /b 1
)
echo.

echo %YELLOW%[5/5] Configuration de Qdrant%RESET%
echo ------------------------------

:: Verifier si Qdrant est deja configure
if not exist "%QDRANT_STORAGE%" (
    echo Creation du dossier de stockage Qdrant...
    mkdir "%QDRANT_STORAGE%"
    echo %GREEN%Dossier de stockage Qdrant cree avec succes.%RESET%
) else (
    echo Le dossier de stockage Qdrant existe deja.
)

echo %GREEN%Configuration de Qdrant terminee.%RESET%
echo.

echo %YELLOW%[6/6] Verification des dependances OCR (optionnel)%RESET%
echo ------------------------------

echo Verification des dependances externes OCR...
echo Note: Ces dependances sont optionnelles mais necessaires pour la fonctionnalite OCR.

:: Verifier si Tesseract OCR est installe
where tesseract >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo %GREEN%Tesseract OCR trouve dans le PATH.%RESET%
) else (
    echo %YELLOW%Tesseract OCR non trouve dans le PATH.%RESET%
    echo Pour installer l'OCR, consultez: "%PROJECT_DIR%\documentation\INSTALLATION_OCR.md"
)

:: Verifier si Poppler est installe
where pdfinfo >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo %GREEN%Poppler (pdfinfo) trouve dans le PATH.%RESET%
) else (
    echo %YELLOW%Poppler non trouve dans le PATH.%RESET%
    echo Pour installer l'OCR, consultez: "%PROJECT_DIR%\documentation\INSTALLATION_OCR.md"
)

:: Verifier si OCRmyPDF est installe
where ocrmypdf >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo %GREEN%OCRmyPDF trouve dans le PATH.%RESET%
) else (
    echo %YELLOW%OCRmyPDF non trouve dans le PATH.%RESET%
    echo Executez: pip install ocrmypdf
    echo Et consultez: "%PROJECT_DIR%\documentation\INSTALLATION_OCR.md"
)

:: Proposer de lancer le diagnostic OCR
echo.
echo %YELLOW%IMPORTANT: La fonctionnalite OCR permet de traiter les documents numerises (sans texte selectionnable).%RESET%
echo %YELLOW%Sans cette fonctionnalite, l'application ne pourra pas traiter correctement les PDFs scannes.%RESET%
echo.
echo Pour installer les dependances OCR:
echo 1. Consultez "%PROJECT_DIR%\documentation\INSTALLATION_OCR.md"
echo 2. Ou executez le script PowerShell: "%PROJECT_DIR%\scripts\tools\update_ocr_path.ps1" (administrateur)
echo.
echo Pour un diagnostic complet de l'installation OCR, executez:
echo %YELLOW%python "%PROJECT_DIR%\scripts\diagnose_ocr.py"%RESET%
echo.

echo %GREEN%===== Configuration du projet terminee avec succes =====%RESET%
echo.
echo Pour demarrer les serveurs, executez:
echo %YELLOW%start_servers.bat%RESET%
echo.
echo Appuyez sur une touche pour fermer cette fenetre...
pause > nul
