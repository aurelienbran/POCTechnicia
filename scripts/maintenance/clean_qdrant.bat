@echo off
setlocal enableextensions enabledelayedexpansion
title Nettoyage de la base de donnees Qdrant
echo ===== Nettoyage de la base de donnees Qdrant =====
echo.

:: Definir les chemins
set "SCRIPTS_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPTS_DIR%..\\.."
set "PYTHON_DIR=%PROJECT_DIR%\scripts\python"
set "PYTHON_ENV=%PROJECT_DIR%\.venv"
set "QDRANT_STORAGE=%PROJECT_DIR%\qdrant_storage"
set "SNAPSHOTS_DIR=%PROJECT_DIR%\snapshots"

:: Verifier si l'environnement Python existe
if not exist "%PYTHON_ENV%" (
    echo Erreur: L'environnement Python n'existe pas.
    echo Veuillez executer setup_project.bat pour configurer le projet.
    exit /b 1
)

:: Creer le dossier de snapshots s'il n'existe pas
if not exist "%SNAPSHOTS_DIR%" (
    echo Creation du dossier de snapshots...
    mkdir "%SNAPSHOTS_DIR%"
)

:: Afficher le menu
:MENU
cls
echo ===== Nettoyage de la base de donnees Qdrant =====
echo.
echo ATTENTION: Cette operation peut entrainer une perte de donnees.
echo Assurez-vous que Qdrant est en cours d'execution avant de continuer.
echo.
echo Options de nettoyage:
echo [1] Supprimer uniquement la collection 'documents'
echo [2] Supprimer toutes les collections
echo [3] Creer un snapshot avant la suppression
echo [4] Restaurer un snapshot
echo [5] Quitter
echo.

set /p CHOICE=Choisissez une option (1-5): 

if "%CHOICE%"=="1" goto :CLEAN_DOCUMENTS
if "%CHOICE%"=="2" goto :CLEAN_ALL
if "%CHOICE%"=="3" goto :CREATE_SNAPSHOT
if "%CHOICE%"=="4" goto :RESTORE_SNAPSHOT
if "%CHOICE%"=="5" goto :EOF

echo Option invalide. Veuillez reessayer.
timeout /t 2 > nul
goto :MENU

:CLEAN_DOCUMENTS
echo.
echo Suppression de la collection 'documents'...
echo.

:: Activer l'environnement virtuel et exécuter le script Python
call "%PYTHON_ENV%\Scripts\activate.bat" && (
    python "%PYTHON_DIR%\clean_documents.py"
    
    if !ERRORLEVEL! equ 0 (
        echo Operation terminee avec succes.
    ) else (
        echo Erreur lors de l'operation.
        echo Assurez-vous que Qdrant est en cours d'execution.
    )
)

pause
goto :MENU

:CLEAN_ALL
echo.
echo Suppression de toutes les collections...
echo.

:: Activer l'environnement virtuel et exécuter le script Python
call "%PYTHON_ENV%\Scripts\activate.bat" && (
    python "%PYTHON_DIR%\clean_all_collections.py"
    
    if !ERRORLEVEL! equ 0 (
        echo Operation terminee avec succes.
    ) else (
        echo Erreur lors de l'operation.
        echo Assurez-vous que Qdrant est en cours d'execution.
    )
)

pause
goto :MENU

:CREATE_SNAPSHOT
echo.
echo Creation d'un snapshot...
echo.

:: Activer l'environnement virtuel et exécuter le script Python
call "%PYTHON_ENV%\Scripts\activate.bat" && (
    python "%PYTHON_DIR%\create_snapshot.py" "%SNAPSHOTS_DIR%"
    
    if !ERRORLEVEL! equ 0 (
        echo Snapshot cree avec succes.
    ) else (
        echo Erreur lors de la creation du snapshot.
        echo Assurez-vous que Qdrant est en cours d'execution.
    )
)

pause
goto :MENU

:RESTORE_SNAPSHOT
echo.
echo Restauration d'un snapshot...
echo.

:: Lister les snapshots disponibles
echo Snapshots disponibles:
echo.

set COUNT=0
for %%F in ("%SNAPSHOTS_DIR%\*_snapshot_*") do (
    set /a COUNT+=1
    set "FILE_%%COUNT%%=%%~nxF"
    echo [!COUNT!] %%~nxF
)

if %COUNT% EQU 0 (
    echo Aucun snapshot disponible.
    pause
    goto :MENU
)

echo.
set /p SNAPSHOT_CHOICE=Choisissez un snapshot (1-%COUNT%) ou 0 pour annuler: 

if "%SNAPSHOT_CHOICE%"=="0" goto :MENU

:: Vérifier que le choix est valide
if %SNAPSHOT_CHOICE% LSS 1 (
    echo Choix invalide.
    pause
    goto :RESTORE_SNAPSHOT
)
if %SNAPSHOT_CHOICE% GTR %COUNT% (
    echo Choix invalide.
    pause
    goto :RESTORE_SNAPSHOT
)

:: Obtenir le nom du snapshot sélectionné
call set "SELECTED_SNAPSHOT=%%FILE_%SNAPSHOT_CHOICE%%%"

echo.
echo Restauration du snapshot: %SELECTED_SNAPSHOT%
echo.

:: Activer l'environnement virtuel et exécuter le script Python
call "%PYTHON_ENV%\Scripts\activate.bat" && (
    python "%PYTHON_DIR%\restore_snapshot.py" "%SNAPSHOTS_DIR%" "%SELECTED_SNAPSHOT%"
    
    if !ERRORLEVEL! equ 0 (
        echo Snapshot restaure avec succes.
    ) else (
        echo Erreur lors de la restauration du snapshot.
        echo Le snapshot n'existe peut-etre pas ou Qdrant n'est pas en cours d'execution.
    )
)

pause
goto :MENU
