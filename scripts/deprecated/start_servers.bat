@echo off
setlocal enableextensions enabledelayedexpansion
title Demarrage des serveurs POC TECHNICIA
echo ===== Demarrage des serveurs POC TECHNICIA =====
echo.

:: Definir les chemins
set "SCRIPTS_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPTS_DIR%.."
set "FRONTEND_DIR=%PROJECT_DIR%\frontend"
set "PYTHON_ENV=%PROJECT_DIR%\.venv"
set "QDRANT_DIR=%PROJECT_DIR%\qdrant"
set "QDRANT_STORAGE=%PROJECT_DIR%\qdrant_storage"

:: Definir les couleurs
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "RESET=[0m"

echo %YELLOW%[1/3] Demarrage de Qdrant%RESET%
echo ------------------------------

:: Verifier si le dossier de stockage Qdrant existe
if not exist "%QDRANT_STORAGE%" (
    echo Creation du dossier de stockage Qdrant...
    mkdir "%QDRANT_STORAGE%"
)

:: Demarrer Qdrant dans une nouvelle fenetre
if exist "%QDRANT_DIR%\qdrant.exe" (
    echo Demarrage de Qdrant (binaire local)...
    start "Qdrant Server" cmd /c "cd /d "%QDRANT_DIR%" && "%QDRANT_DIR%\qdrant.exe" --storage-path "%QDRANT_STORAGE%""
) else (
    echo %YELLOW%Note: Binaire Qdrant non trouve localement.%RESET%
    echo Qdrant doit etre demarre separement ou installe via Docker.
    echo Veuillez vous assurer que Qdrant est accessible sur localhost:6333.
)

:: Attendre que Qdrant demarre
echo Attente du demarrage de Qdrant...
timeout /t 5 > nul

echo %GREEN%Qdrant demarre (ou suppose demarre).%RESET%
echo.

echo %YELLOW%[2/3] Demarrage du backend FastAPI%RESET%
echo ------------------------------

:: Demarrer le backend FastAPI dans une nouvelle fenetre
echo Demarrage du backend FastAPI...
start "Backend FastAPI" cmd /c "cd /d "%PROJECT_DIR%" && call "%PYTHON_ENV%\Scripts\activate.bat" && python -m uvicorn app.main:app --reload --port 8000"

:: Attendre que le backend demarre
echo Attente du demarrage du backend...
timeout /t 10 > nul

echo %GREEN%Backend FastAPI demarre.%RESET%
echo.

echo %YELLOW%[3/3] Demarrage du frontend React%RESET%
echo ------------------------------

:: Verifier si le repertoire frontend existe
if exist "%FRONTEND_DIR%" (
    :: Demarrer le frontend React dans une nouvelle fenetre
    echo Demarrage du frontend React...
    start "Frontend React" cmd /c "cd /d "%FRONTEND_DIR%" && npm run dev"
    echo %GREEN%Frontend React en cours de demarrage.%RESET%
) else (
    echo %RED%Erreur: Le repertoire frontend n'existe pas.%RESET%
    echo Veuillez vous assurer que le repertoire frontend est present.
)

echo.
echo %GREEN%Tous les serveurs sont demarres.%RESET%
echo %YELLOW%Le frontend sera accessible a l'adresse: http://localhost:3001%RESET%
echo %YELLOW%Le backend sera accessible a l'adresse: http://localhost:8000%RESET%
echo %YELLOW%Qdrant est accessible a l'adresse: http://localhost:6333%RESET%
echo.
echo Appuyez sur Ctrl+C pour fermer cette fenetre (les serveurs continueront a tourner).
echo.

:: Garder la fenetre ouverte
cmd /c pause > nul
