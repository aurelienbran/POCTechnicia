# Script de déploiement en environnement de staging - Technicia OCR
# Version: 1.0
# Date: 2 avril 2025
#
# Ce script permet de déployer le système OCR Technicia dans un environnement de staging
# et d'effectuer les tests nécessaires avant la mise en production.

param (
    [string]$SourceDir = ".",
    [string]$StagingDir = "C:\Technicia\Staging",
    [string]$BackupDir = "C:\Technicia\Backups",
    [switch]$SkipBackup = $false,
    [switch]$RunTests = $true
)

function Write-LogMessage {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS")]
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colorMap = @{
        "INFO" = "White";
        "WARN" = "Yellow";
        "ERROR" = "Red";
        "SUCCESS" = "Green"
    }
    
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $colorMap[$Level]
}

# Vérification des droits d'administrateur
Write-LogMessage "Vérification des privilèges administrateur..."
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-LogMessage "Ce script doit être exécuté avec des privilèges administrateur." "ERROR"
    exit 1
}

# Création des répertoires nécessaires
Write-LogMessage "Création des répertoires nécessaires..."
if (-not (Test-Path -Path $StagingDir -PathType Container)) {
    New-Item -Path $StagingDir -ItemType Directory -Force | Out-Null
}

if (-not (Test-Path -Path $BackupDir -PathType Container)) {
    New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
}

# Création d'un dossier de backup avec horodatage
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupTimestampDir = Join-Path -Path $BackupDir -ChildPath "backup_$timestamp"

# Sauvegarde de l'environnement existant si présent
if (-not $SkipBackup -and (Test-Path -Path $StagingDir)) {
    Write-LogMessage "Sauvegarde de l'environnement de staging existant..."
    
    # Création du répertoire de sauvegarde
    New-Item -Path $backupTimestampDir -ItemType Directory -Force | Out-Null
    
    # Copie des fichiers vers la sauvegarde
    Copy-Item -Path "$StagingDir\*" -Destination $backupTimestampDir -Recurse -Force
    
    Write-LogMessage "Sauvegarde terminée: $backupTimestampDir" "SUCCESS"
}

# Arrêt des services existants
Write-LogMessage "Arrêt des services existants dans l'environnement de staging..."
$services = @("TechniciaOCR-API-Staging", "TechniciaOCR-Worker-Staging", "TechniciaOCR-Beat-Staging")
foreach ($service in $services) {
    if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
        Stop-Service -Name $service -Force
        Write-LogMessage "Service $service arrêté."
    } else {
        Write-LogMessage "Service $service non trouvé. Ignoré." "WARN"
    }
}

# Nettoyage du répertoire de staging
Write-LogMessage "Nettoyage du répertoire de staging..."
Get-ChildItem -Path $StagingDir -Exclude "data", "logs", "config.ini" | Remove-Item -Recurse -Force

# Déploiement des nouveaux fichiers
Write-LogMessage "Déploiement des fichiers vers l'environnement de staging..."
Copy-Item -Path "$SourceDir\*" -Destination $StagingDir -Recurse -Force -Exclude @("deploy", "logs", "data", ".git*", "tests")

# Création ou mise à jour du fichier de configuration
if (-not (Test-Path -Path "$StagingDir\config.ini" -PathType Leaf)) {
    Write-LogMessage "Création du fichier de configuration pour l'environnement de staging..."
    $configContent = @"
# Configuration du système OCR Technicia - Environnement de Staging
# Généré automatiquement par le script de déploiement

[app]
name = Technicia OCR - Staging
environment = staging
debug = True
secret_key = $([Guid]::NewGuid().ToString())
max_parallel_tasks = 2
ocr_quality_threshold = 0.75

[paths]
data_dir = $StagingDir\data
log_dir = $StagingDir\logs

[database]
host = localhost
port = 5432
name = ocr_db_staging
user = technicia
password = stagingPassword123

[redis]
host = localhost
port = 6379
db = 1
"@

    $configContent | Set-Content -Path "$StagingDir\config.ini" -Force
    Write-LogMessage "Fichier de configuration créé."
} else {
    Write-LogMessage "Le fichier de configuration existe déjà, mise à jour du paramètre 'environment'..."
    $configContent = Get-Content -Path "$StagingDir\config.ini" -Raw
    $configContent = $configContent -replace "environment = .*", "environment = staging"
    $configContent | Set-Content -Path "$StagingDir\config.ini" -Force
}

# Création des répertoires de données et logs s'ils n'existent pas
Write-LogMessage "Création des répertoires de données et logs..."
$dataDirs = @(
    "$StagingDir\data",
    "$StagingDir\data\uploads",
    "$StagingDir\data\processed",
    "$StagingDir\data\temp",
    "$StagingDir\data\cache",
    "$StagingDir\logs"
)

foreach ($dir in $dataDirs) {
    if (-not (Test-Path -Path $dir -PathType Container)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
        Write-LogMessage "Répertoire créé: $dir"
    }
}

# Installation de l'environnement virtuel Python (si nécessaire)
if (-not (Test-Path -Path "$StagingDir\venv" -PathType Container)) {
    Write-LogMessage "Création de l'environnement virtuel Python..."
    
    # Vérification de la présence de Python
    if (-not (Get-Command -Name "python" -ErrorAction SilentlyContinue)) {
        Write-LogMessage "Python n'est pas installé ou n'est pas dans le PATH." "ERROR"
        exit 1
    }
    
    # Création de l'environnement virtuel
    Set-Location -Path $StagingDir
    & python -m venv venv
    
    # Activation de l'environnement virtuel et installation des dépendances
    & "$StagingDir\venv\Scripts\Activate.ps1"
    & python -m pip install -r requirements.txt
    deactivate
} else {
    Write-LogMessage "Mise à jour des dépendances Python..."
    & "$StagingDir\venv\Scripts\Activate.ps1"
    & python -m pip install --upgrade -r requirements.txt
    deactivate
}

# Exécution des tests si demandé
if ($RunTests) {
    Write-LogMessage "Exécution des tests dans l'environnement de staging..."
    Set-Location -Path $StagingDir
    & "$StagingDir\venv\Scripts\Activate.ps1"
    
    # Exécution des tests unitaires
    Write-LogMessage "Exécution des tests unitaires..."
    & python -m pytest tests/unit -v
    
    # Exécution des tests d'intégration
    Write-LogMessage "Exécution des tests d'intégration..."
    & python -m pytest tests/integration -v
    
    # Exécution des tests de performance
    Write-LogMessage "Exécution des tests de performance..."
    & python -m pytest tests/performance -v
    
    deactivate
}

# Installation ou mise à jour des services Windows
Write-LogMessage "Installation ou mise à jour des services Windows..."

# Vérification de NSSM (Non-Sucking Service Manager)
if (-not (Get-Command -Name "nssm" -ErrorAction SilentlyContinue)) {
    Write-LogMessage "NSSM n'est pas installé. L'installation des services est ignorée." "WARN"
} else {
    # Service API
    if (Get-Service -Name "TechniciaOCR-API-Staging" -ErrorAction SilentlyContinue) {
        Write-LogMessage "Mise à jour du service API..."
        & nssm set "TechniciaOCR-API-Staging" Application "$StagingDir\venv\Scripts\python.exe"
        & nssm set "TechniciaOCR-API-Staging" AppParameters "$StagingDir\app.py"
        & nssm set "TechniciaOCR-API-Staging" AppDirectory "$StagingDir"
    } else {
        Write-LogMessage "Installation du service API..."
        & nssm install "TechniciaOCR-API-Staging" "$StagingDir\venv\Scripts\python.exe" "$StagingDir\app.py"
        & nssm set "TechniciaOCR-API-Staging" AppDirectory "$StagingDir"
        & nssm set "TechniciaOCR-API-Staging" DisplayName "Technicia OCR API - Staging"
        & nssm set "TechniciaOCR-API-Staging" Description "Service API pour le système OCR Technicia (Staging)"
        & nssm set "TechniciaOCR-API-Staging" Start SERVICE_AUTO_START
        & nssm set "TechniciaOCR-API-Staging" AppStdout "$StagingDir\logs\api_stdout.log"
        & nssm set "TechniciaOCR-API-Staging" AppStderr "$StagingDir\logs\api_stderr.log"
    }
    
    # Service Worker
    if (Get-Service -Name "TechniciaOCR-Worker-Staging" -ErrorAction SilentlyContinue) {
        Write-LogMessage "Mise à jour du service Worker..."
        & nssm set "TechniciaOCR-Worker-Staging" Application "$StagingDir\venv\Scripts\celery.exe"
        & nssm set "TechniciaOCR-Worker-Staging" AppParameters "-A app.celery_app worker --loglevel=info --concurrency=2"
        & nssm set "TechniciaOCR-Worker-Staging" AppDirectory "$StagingDir"
    } else {
        Write-LogMessage "Installation du service Worker..."
        & nssm install "TechniciaOCR-Worker-Staging" "$StagingDir\venv\Scripts\celery.exe" "-A app.celery_app worker --loglevel=info --concurrency=2"
        & nssm set "TechniciaOCR-Worker-Staging" AppDirectory "$StagingDir"
        & nssm set "TechniciaOCR-Worker-Staging" DisplayName "Technicia OCR Worker - Staging"
        & nssm set "TechniciaOCR-Worker-Staging" Description "Service Worker pour le système OCR Technicia (Staging)"
        & nssm set "TechniciaOCR-Worker-Staging" Start SERVICE_AUTO_START
        & nssm set "TechniciaOCR-Worker-Staging" AppStdout "$StagingDir\logs\worker_stdout.log"
        & nssm set "TechniciaOCR-Worker-Staging" AppStderr "$StagingDir\logs\worker_stderr.log"
    }
    
    # Service Beat
    if (Get-Service -Name "TechniciaOCR-Beat-Staging" -ErrorAction SilentlyContinue) {
        Write-LogMessage "Mise à jour du service Beat..."
        & nssm set "TechniciaOCR-Beat-Staging" Application "$StagingDir\venv\Scripts\celery.exe"
        & nssm set "TechniciaOCR-Beat-Staging" AppParameters "-A app.celery_app beat --loglevel=info"
        & nssm set "TechniciaOCR-Beat-Staging" AppDirectory "$StagingDir"
    } else {
        Write-LogMessage "Installation du service Beat..."
        & nssm install "TechniciaOCR-Beat-Staging" "$StagingDir\venv\Scripts\celery.exe" "-A app.celery_app beat --loglevel=info"
        & nssm set "TechniciaOCR-Beat-Staging" AppDirectory "$StagingDir"
        & nssm set "TechniciaOCR-Beat-Staging" DisplayName "Technicia OCR Beat - Staging"
        & nssm set "TechniciaOCR-Beat-Staging" Description "Service Beat pour le système OCR Technicia (Staging)"
        & nssm set "TechniciaOCR-Beat-Staging" Start SERVICE_AUTO_START
        & nssm set "TechniciaOCR-Beat-Staging" AppStdout "$StagingDir\logs\beat_stdout.log"
        & nssm set "TechniciaOCR-Beat-Staging" AppStderr "$StagingDir\logs\beat_stderr.log"
    }
    
    # Démarrage des services
    Write-LogMessage "Démarrage des services..."
    Start-Service -Name "TechniciaOCR-API-Staging"
    Start-Service -Name "TechniciaOCR-Worker-Staging"
    Start-Service -Name "TechniciaOCR-Beat-Staging"
}

Write-LogMessage "Déploiement en environnement de staging terminé avec succès !" "SUCCESS"
Write-LogMessage "L'application de staging est accessible à l'adresse: http://localhost:5000"
Write-LogMessage "Tâches supplémentaires à effectuer:"
Write-LogMessage " - Vérifier les journaux dans $StagingDir\logs pour détecter les erreurs éventuelles"
Write-LogMessage " - Exécuter les tests manuels selon le plan de test"
Write-LogMessage " - Vérifier que toutes les fonctionnalités sont opérationnelles"
Write-LogMessage " - Une fois validé, utiliser deploy_production.ps1 pour déployer en production"
