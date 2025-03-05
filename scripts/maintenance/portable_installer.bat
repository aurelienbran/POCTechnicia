@echo off
setlocal enableextensions enabledelayedexpansion
title Installateur Portable POC TECHNICIA
echo ===== Installateur Portable POC TECHNICIA =====
echo.

:: Définir les couleurs
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "RESET=[0m"

:: Obtenir le répertoire courant (où le script est exécuté)
set "INSTALLER_DIR=%~dp0"

:: Afficher l'introduction
echo Ce script va créer un installateur auto-extractible pour le projet POC TECHNICIA.
echo L'installateur contiendra:
echo  - Le code source complet du projet
echo  - Des versions portables de Python, Node.js et Qdrant
echo  - Des scripts d'installation et de démarrage
echo.
echo %YELLOW%IMPORTANT: Ce script ne crée que le squelette de l'installateur.%RESET%
echo Vous devrez y ajouter manuellement les dépendances portables.
echo.
pause

:: Demander le répertoire de sortie pour l'installateur
set "OUTPUT_DIR="
set /p OUTPUT_DIR=Entrez le répertoire où créer l'installateur (ex: D:\Temp): 

if "%OUTPUT_DIR%"=="" (
    set "OUTPUT_DIR=%USERPROFILE%\Desktop"
    echo %YELLOW%Utilisation du répertoire par défaut: %OUTPUT_DIR%%RESET%
)

:: Créer la structure de l'installateur
echo %YELLOW%Création de la structure de l'installateur...%RESET%
if not exist "%OUTPUT_DIR%\POCTechnicia_Installer" mkdir "%OUTPUT_DIR%\POCTechnicia_Installer"
if not exist "%OUTPUT_DIR%\POCTechnicia_Installer\project_source" mkdir "%OUTPUT_DIR%\POCTechnicia_Installer\project_source"
if not exist "%OUTPUT_DIR%\POCTechnicia_Installer\portable_deps" mkdir "%OUTPUT_DIR%\POCTechnicia_Installer\portable_deps"
if not exist "%OUTPUT_DIR%\POCTechnicia_Installer\portable_deps\python_portable" mkdir "%OUTPUT_DIR%\POCTechnicia_Installer\portable_deps\python_portable"
if not exist "%OUTPUT_DIR%\POCTechnicia_Installer\portable_deps\nodejs_portable" mkdir "%OUTPUT_DIR%\POCTechnicia_Installer\portable_deps\nodejs_portable"
if not exist "%OUTPUT_DIR%\POCTechnicia_Installer\portable_deps\qdrant_portable" mkdir "%OUTPUT_DIR%\POCTechnicia_Installer\portable_deps\qdrant_portable"

:: Créer le README.txt
echo %YELLOW%Création du fichier README.txt...%RESET%
(
echo ======== POC TECHNICIA - Installateur Portable ========
echo.
echo Ce paquet contient un installateur portable pour le projet POC TECHNICIA.
echo.
echo CONTENU:
echo ---------
echo 1. Code source du projet
echo 2. Dépendances portables (Python, Node.js, Qdrant)
echo 3. Scripts d'installation et de démarrage
echo.
echo INSTRUCTIONS:
echo -------------
echo 1. Exécutez "install.bat" pour installer le projet
echo 2. Suivez les instructions à l'écran
echo 3. Une fois l'installation terminée, utilisez les scripts dans le dossier "scripts"
echo    - "setup_portable.bat" pour configurer le projet
echo    - "start_portable.bat" pour démarrer l'application
echo.
echo PRÉREQUIS:
echo ----------
echo - Windows 10 ou supérieur
echo - Au moins 2 Go d'espace disque libre
echo - Droits d'administrateur (pour certaines fonctionnalités)
echo.
echo SUPPORT:
echo --------
echo Pour toute question ou assistance, contactez l'équipe de développement.
) > "%OUTPUT_DIR%\POCTechnicia_Installer\README.txt"

:: Créer le script d'installation principal
echo %YELLOW%Création du script d'installation principal...%RESET%
(
echo @echo off
echo setlocal enableextensions enabledelayedexpansion
echo title Installateur POC TECHNICIA
echo echo ===== Installation de POC TECHNICIA =====
echo echo.
echo.
echo :: Définir les couleurs
echo set "GREEN=[92m"
echo set "YELLOW=[93m"
echo set "RED=[91m"
echo set "RESET=[0m"
echo.
echo :: Déterminer le répertoire d'extraction (où ce script est exécuté)
echo set "EXTRACT_DIR=%%~dp0"
echo.
echo :: Demander le répertoire d'installation
echo set "INSTALL_DIR="
echo set /p INSTALL_DIR=Entrez le chemin d'installation (ex: D:\Projets\POC TECHNICIA^): 
echo.
echo if "%%INSTALL_DIR%%"=="" (
echo     set "INSTALL_DIR=%%USERPROFILE%%\POC TECHNICIA"
echo     echo %%YELLOW%%Utilisation du répertoire par défaut: %%INSTALL_DIR%%%%RESET%%
echo ^)
echo.
echo :: Création du répertoire s'il n'existe pas
echo if not exist "%%INSTALL_DIR%%" (
echo     mkdir "%%INSTALL_DIR%%"
echo ^)
echo.
echo :: Créer la structure des dossiers pour l'installation
echo echo Création de la structure des dossiers...
echo mkdir "%%INSTALL_DIR%%\scripts"
echo mkdir "%%INSTALL_DIR%%\scripts\startup"
echo mkdir "%%INSTALL_DIR%%\scripts\maintenance"
echo mkdir "%%INSTALL_DIR%%\scripts\python"
echo mkdir "%%INSTALL_DIR%%\scripts\tools"
echo.
echo :: Copier les fichiers du projet
echo echo %%YELLOW%%Copie des fichiers du projet...%%RESET%%
echo xcopy /E /I /Y "%%EXTRACT_DIR%%\project_source\*" "%%INSTALL_DIR%%"
echo.
echo :: Configurer les dépendances portables
echo echo %%YELLOW%%Configuration des dépendances portables...%%RESET%%
echo.
echo :: Créer le dossier portable_deps s'il n'existe pas
echo if not exist "%%INSTALL_DIR%%\portable_deps" (
echo     mkdir "%%INSTALL_DIR%%\portable_deps"
echo ^)
echo.
echo :: Configurer Python portable
echo echo %%YELLOW%%Configuration de Python portable...%%RESET%%
echo xcopy /E /I /Y "%%EXTRACT_DIR%%\portable_deps\python_portable" "%%INSTALL_DIR%%\portable_deps\python"
echo.
echo :: Configurer Node.js portable
echo echo %%YELLOW%%Configuration de Node.js portable...%%RESET%%
echo xcopy /E /I /Y "%%EXTRACT_DIR%%\portable_deps\nodejs_portable" "%%INSTALL_DIR%%\portable_deps\nodejs"
echo.
echo :: Configurer Qdrant portable
echo echo %%YELLOW%%Configuration de Qdrant portable...%%RESET%%
echo xcopy /E /I /Y "%%EXTRACT_DIR%%\portable_deps\qdrant_portable" "%%INSTALL_DIR%%\portable_deps\qdrant"
echo.
echo :: Créer le script de configuration avec les chemins portables
echo echo %%YELLOW%%Création des scripts de démarrage portables...%%RESET%%
echo.
echo :: Créer setup_portable.bat
echo (
echo echo @echo off
echo echo setlocal enableextensions enabledelayedexpansion
echo echo title Configuration Portable POC TECHNICIA
echo echo.
echo echo :: Définir les chemins portables
echo echo set "PROJECT_DIR=%%%%~dp0..\.."
echo echo set "PYTHON_PORTABLE=%%%%PROJECT_DIR%%%%\portable_deps\python\python.exe"
echo echo set "NODE_PORTABLE=%%%%PROJECT_DIR%%%%\portable_deps\nodejs\node.exe"
echo echo set "NPM_PORTABLE=%%%%PROJECT_DIR%%%%\portable_deps\nodejs\npm.cmd"
echo echo set "QDRANT_PORTABLE=%%%%PROJECT_DIR%%%%\portable_deps\qdrant\qdrant.exe"
echo echo.
echo echo :: Configurer le frontend
echo echo cd /d "%%%%PROJECT_DIR%%%%\frontend"
echo echo call "%%%%NPM_PORTABLE%%%%" install
echo echo.
echo echo :: Configurer l'environnement Python
echo echo cd /d "%%%%PROJECT_DIR%%%%"
echo echo "%%%%PYTHON_PORTABLE%%%%" -m pip install -r requirements.txt
echo echo.
echo echo echo Installation terminée! Utilisez scripts\startup\start_portable.bat pour démarrer l'application.
echo echo pause
echo ^) ^> "%%INSTALL_DIR%%\scripts\maintenance\setup_portable.bat"
echo.
echo :: Créer start_portable.bat
echo (
echo echo @echo off
echo echo setlocal enableextensions enabledelayedexpansion
echo echo title Démarrage Portable POC TECHNICIA
echo echo.
echo echo :: Définir les chemins portables
echo echo set "PROJECT_DIR=%%%%~dp0..\.."
echo echo set "PYTHON_PORTABLE=%%%%PROJECT_DIR%%%%\portable_deps\python\python.exe"
echo echo set "NODE_PORTABLE=%%%%PROJECT_DIR%%%%\portable_deps\nodejs\node.exe"
echo echo set "NPM_PORTABLE=%%%%PROJECT_DIR%%%%\portable_deps\nodejs\npm.cmd"
echo echo set "QDRANT_PORTABLE=%%%%PROJECT_DIR%%%%\portable_deps\qdrant\qdrant.exe"
echo echo.
echo echo :: Démarrer Qdrant
echo echo start "Qdrant" cmd /c "%%%%QDRANT_PORTABLE%%%% --storage-path %%%%PROJECT_DIR%%%%\qdrant_storage"
echo echo timeout /t 5 ^> nul
echo echo.
echo echo :: Démarrer le backend
echo echo start "Backend" cmd /c "cd /d %%%%PROJECT_DIR%%%% ^&^& %%%%PYTHON_PORTABLE%%%% -m uvicorn app.main:app --reload --port 8000"
echo echo timeout /t 10 ^> nul
echo echo.
echo echo :: Démarrer le frontend
echo echo start "Frontend" cmd /c "cd /d %%%%PROJECT_DIR%%%%\frontend ^&^& %%%%NPM_PORTABLE%%%% run dev"
echo echo.
echo echo echo Tous les services sont démarrés!
echo ^) ^> "%%INSTALL_DIR%%\scripts\startup\start_portable.bat"
echo.
echo :: Créer clean_qdrant_portable.bat
echo (
echo echo @echo off
echo echo setlocal enableextensions enabledelayedexpansion
echo echo title Nettoyage de Qdrant (Portable)
echo echo.
echo echo :: Définir les chemins portables
echo echo set "PROJECT_DIR=%%%%~dp0..\.."
echo echo set "PYTHON_PORTABLE=%%%%PROJECT_DIR%%%%\portable_deps\python\python.exe"
echo echo.
echo echo echo ===== Nettoyage de la base de données Qdrant =====
echo echo echo.
echo echo echo ATTENTION: Cette opération supprimera toutes les collections de la base Qdrant.
echo echo echo Assurez-vous que Qdrant est en cours d'exécution.
echo echo echo.
echo echo set /p CONFIRM=Êtes-vous sûr de vouloir continuer? (O/N): 
echo echo.
echo echo if /i "%%%%CONFIRM%%%%"=="O" (
echo echo     "%%%%PYTHON_PORTABLE%%%%" -c "from qdrant_client import QdrantClient; client = QdrantClient(host='localhost', port=6333); [client.delete_collection(collection.name) for collection in client.get_collections().collections];"
echo echo     echo Base de données Qdrant nettoyée avec succès!
echo echo ) else (
echo echo     echo Opération annulée.
echo echo )
echo echo.
echo echo pause
echo ^) ^> "%%INSTALL_DIR%%\scripts\maintenance\clean_qdrant_portable.bat"
echo.
echo echo %%GREEN%%Installation terminée!%%RESET%%
echo echo.
echo echo Pour configurer le projet, exécutez:
echo echo %%YELLOW%%%%INSTALL_DIR%%\scripts\maintenance\setup_portable.bat%%RESET%%
echo echo.
echo echo Pour démarrer l'application, exécutez:
echo echo %%YELLOW%%%%INSTALL_DIR%%\scripts\startup\start_portable.bat%%RESET%%
echo echo.
echo echo Appuyez sur une touche pour fermer cette fenêtre...
echo pause ^> nul
) > "%OUTPUT_DIR%\POCTechnicia_Installer\install.bat"

:: Créer le fichier config.txt pour 7-Zip SFX
echo %YELLOW%Création du fichier de configuration 7-Zip SFX...%RESET%
(
echo ;!@Install@!UTF-8!
echo Title="Installateur POC TECHNICIA"
echo BeginPrompt="Voulez-vous installer POC TECHNICIA?"
echo ExecuteFile="install.bat"
echo ;!@InstallEnd@!
) > "%OUTPUT_DIR%\POCTechnicia_Installer\config.txt"

:: Créer un script README pour les étapes finales
echo %YELLOW%Création du guide d'utilisation...%RESET%
(
echo ======== ÉTAPES POUR FINALISER L'INSTALLATEUR ========
echo.
echo Pour finaliser la création de l'installateur auto-extractible:
echo.
echo 1. COPIEZ LES DÉPENDANCES PORTABLES:
echo    - Téléchargez Python Portable (https://www.python.org/)
echo      et placez-le dans: portable_deps\python_portable\
echo.
echo    - Téléchargez Node.js Portable (https://nodejs.org/)
echo      et placez-le dans: portable_deps\nodejs_portable\
echo.
echo    - Téléchargez Qdrant (https://qdrant.tech/)
echo      et placez-le dans: portable_deps\qdrant_portable\
echo.
echo 2. COPIEZ LE CODE SOURCE:
echo    - Copiez tout le contenu de votre projet
echo      dans: project_source\
echo.
echo 3. CRÉEZ L'EXÉCUTABLE AUTO-EXTRACTIBLE:
echo    - Téléchargez et installez 7-Zip (https://www.7-zip.org/)
echo    - Téléchargez 7-Zip Extra (contient les modules SFX)
echo    - Exécutez les commandes suivantes:
echo.
echo      cd /d "%OUTPUT_DIR%\POCTechnicia_Installer"
echo      7z a -r installer.7z project_source portable_deps install.bat README.txt
echo      copy /b 7zSD.sfx + config.txt + installer.7z POCTechnicia_Installer.exe
echo.
echo 4. TESTEZ L'INSTALLATEUR:
echo    - Exécutez POCTechnicia_Installer.exe
echo    - Vérifiez que tout s'installe correctement
echo    - Vérifiez que les scripts portable fonctionnent
echo.
echo ====================================================
) > "%OUTPUT_DIR%\POCTechnicia_Installer\GUIDE_INSTALLATION.txt"

echo %GREEN%Structure de l'installateur créée avec succès!%RESET%
echo.
echo Accédez au dossier: %OUTPUT_DIR%\POCTechnicia_Installer
echo Et suivez les instructions dans GUIDE_INSTALLATION.txt
echo pour finaliser l'installateur.
echo.
echo Appuyez sur une touche pour fermer cette fenêtre...
pause > nul
