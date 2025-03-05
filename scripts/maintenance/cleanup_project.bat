@echo off
setlocal enableextensions enabledelayedexpansion
title Nettoyage du Projet POC TECHNICIA
echo ===== Nettoyage du Projet POC TECHNICIA =====
echo.

:: Définir les couleurs
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "RESET=[0m"

echo %YELLOW%Début du nettoyage du projet...%RESET%
echo.

:: Chemin racine du projet
set "PROJECT_ROOT=D:\Projets\POC TECHNICIA"

echo %YELLOW%1. Suppression des fichiers de test temporaires...%RESET%
if exist "%PROJECT_ROOT%\test_env.py" (
    echo    - Suppression de test_env.py
    del /q "%PROJECT_ROOT%\test_env.py"
)
if exist "%PROJECT_ROOT%\test_payload_size.py" (
    echo    - Suppression de test_payload_size.py
    del /q "%PROJECT_ROOT%\test_payload_size.py"
)
if exist "%PROJECT_ROOT%\test_qdrant.py" (
    echo    - Suppression de test_qdrant.py
    del /q "%PROJECT_ROOT%\test_qdrant.py"
)
if exist "%PROJECT_ROOT%\test_upload.py" (
    echo    - Suppression de test_upload.py
    del /q "%PROJECT_ROOT%\test_upload.py"
)
if exist "%PROJECT_ROOT%\test_output.txt" (
    echo    - Suppression de test_output.txt
    del /q "%PROJECT_ROOT%\test_output.txt"
)
if exist "%PROJECT_ROOT%\qdrant_status.txt" (
    echo    - Suppression de qdrant_status.txt
    del /q "%PROJECT_ROOT%\qdrant_status.txt"
)
echo.

echo %YELLOW%2. Suppression de docker-compose.yml...%RESET%
if exist "%PROJECT_ROOT%\docker-compose.yml" (
    echo    - Suppression de docker-compose.yml
    del /q "%PROJECT_ROOT%\docker-compose.yml"
)
echo.

echo %YELLOW%3. Suppression des caches et environnements générés...%RESET%
if exist "%PROJECT_ROOT%\.pytest_cache" (
    echo    - Suppression de .pytest_cache
    rmdir /s /q "%PROJECT_ROOT%\.pytest_cache"
)
if exist "%PROJECT_ROOT%\.coverage" (
    echo    - Suppression de .coverage
    del /q "%PROJECT_ROOT%\.coverage"
)
if exist "%PROJECT_ROOT%\poc_technicia.egg-info" (
    echo    - Suppression de poc_technicia.egg-info
    rmdir /s /q "%PROJECT_ROOT%\poc_technicia.egg-info"
)
echo.

echo %YELLOW%4. Suppression des dossiers de rapports...%RESET%
if exist "%PROJECT_ROOT%\performance_reports" (
    echo    - Suppression de performance_reports
    rmdir /s /q "%PROJECT_ROOT%\performance_reports"
)
if exist "%PROJECT_ROOT%\reports" (
    echo    - Suppression de reports
    rmdir /s /q "%PROJECT_ROOT%\reports"
)
echo.

echo %YELLOW%5. Suppression des artefacts et dossiers vides...%RESET%
if exist "%PROJECT_ROOT%\temp" (
    echo    - Suppression de temp
    rmdir /s /q "%PROJECT_ROOT%\temp"
)
if exist "%PROJECT_ROOT%\.qdrant-initialized" (
    echo    - Suppression de .qdrant-initialized
    del /q "%PROJECT_ROOT%\.qdrant-initialized"
)
if exist "%PROJECT_ROOT%\qdrant\.qdrant-initialized" (
    echo    - Suppression de qdrant\.qdrant-initialized
    del /q "%PROJECT_ROOT%\qdrant\.qdrant-initialized"
)
if exist "%PROJECT_ROOT%\frontend\.bolt" (
    echo    - Suppression de frontend\.bolt
    rmdir /s /q "%PROJECT_ROOT%\frontend\.bolt"
)
echo.

echo %GREEN%Nettoyage terminé avec succès!%RESET%
echo.
echo Liste des suppression effectuées:
echo - Fichiers de test temporaires (test_*.py)
echo - docker-compose.yml
echo - Caches et fichiers de build (.pytest_cache, .coverage, etc.)
echo - Dossiers de rapports (performance_reports, reports)
echo - Artefacts et dossiers vides (temp, .qdrant-initialized)
echo.
echo %YELLOW%Note: Les dossiers suivants n'ont pas été supprimés:%RESET%
echo - .venv (environnement virtuel)
echo - frontend/node_modules
echo.
echo Si vous souhaitez également supprimer ces dossiers, exécutez:
echo rmdir /s /q "%PROJECT_ROOT%\.venv"
echo rmdir /s /q "%PROJECT_ROOT%\frontend\node_modules"
echo.
echo Appuyez sur une touche pour fermer cette fenêtre...
pause > nul
