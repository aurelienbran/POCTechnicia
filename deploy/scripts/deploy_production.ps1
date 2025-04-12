# Script de déploiement en environnement de production - Technicia OCR
# Version: 1.0
# Date: 2 avril 2025
#
# Ce script permet de déployer le système OCR Technicia dans un environnement de production
# après validation dans l'environnement de staging.

param (
    [string]$StagingDir = "C:\Technicia\Staging",
    [string]$ProductionDir = "C:\Program Files\Technicia\OCRSystem",
    [string]$BackupDir = "C:\Technicia\Backups",
    [switch]$SkipBackup = $false,
    [switch]$SkipVerification = $false
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

# Vérification de l'existence de l'environnement de staging
if (-not (Test-Path -Path $StagingDir -PathType Container)) {
    Write-LogMessage "L'environnement de staging n'existe pas: $StagingDir" "ERROR"
    Write-LogMessage "Veuillez d'abord déployer l'application en staging avec deploy_staging.ps1" "ERROR"
    exit 1
}

# Confirmation par l'utilisateur
if (-not $SkipVerification) {
    Write-LogMessage "ATTENTION: Vous êtes sur le point de déployer en PRODUCTION !" "WARN"
    Write-LogMessage "Cette action remplacera l'application existante et peut entraîner une interruption de service." "WARN"
    
    $confirmation = Read-Host "Êtes-vous sûr de vouloir continuer ? (O/N)"
    if ($confirmation -ne "O") {
        Write-LogMessage "Déploiement annulé par l'utilisateur." "INFO"
        exit 0
    }
}

# Vérification des statuts des services de staging
Write-LogMessage "Vérification des services de staging..."
$stagingServices = @("TechniciaOCR-API-Staging", "TechniciaOCR-Worker-Staging", "TechniciaOCR-Beat-Staging")
foreach ($service in $stagingServices) {
    if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
        $status = (Get-Service -Name $service).Status
        if ($status -ne "Running") {
            Write-LogMessage "Le service $service n'est pas en cours d'exécution (état actuel: $status)." "WARN"
            
            if (-not $SkipVerification) {
                $continue = Read-Host "Continuer quand même ? (O/N)"
                if ($continue -ne "O") {
                    Write-LogMessage "Déploiement annulé par l'utilisateur." "INFO"
                    exit 0
                }
            }
        }
    } else {
        Write-LogMessage "Service $service non trouvé dans l'environnement de staging." "WARN"
    }
}

# Création du répertoire de production s'il n'existe pas
if (-not (Test-Path -Path $ProductionDir -PathType Container)) {
    Write-LogMessage "Création du répertoire de production..."
    New-Item -Path $ProductionDir -ItemType Directory -Force | Out-Null
}

# Création du répertoire de sauvegarde s'il n'existe pas
if (-not (Test-Path -Path $BackupDir -PathType Container)) {
    Write-LogMessage "Création du répertoire de sauvegarde..."
    New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
}

# Création d'un dossier de backup avec horodatage
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupTimestampDir = Join-Path -Path $BackupDir -ChildPath "prod_backup_$timestamp"

# Sauvegarde de l'environnement de production existant
if (-not $SkipBackup -and (Test-Path -Path $ProductionDir)) {
    Write-LogMessage "Sauvegarde de l'environnement de production existant..."
    
    # Création du répertoire de sauvegarde
    New-Item -Path $backupTimestampDir -ItemType Directory -Force | Out-Null
    
    # Copie des fichiers vers la sauvegarde
    Copy-Item -Path "$ProductionDir\*" -Destination $backupTimestampDir -Recurse -Force
    
    Write-LogMessage "Sauvegarde terminée: $backupTimestampDir" "SUCCESS"
}

# Arrêt des services de production
Write-LogMessage "Arrêt des services de production..."
$productionServices = @("TechniciaOCR-API", "TechniciaOCR-Worker", "TechniciaOCR-Beat")
foreach ($service in $productionServices) {
    if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
        Stop-Service -Name $service -Force
        Write-LogMessage "Service $service arrêté."
    } else {
        Write-LogMessage "Service $service non trouvé. Ignoré." "WARN"
    }
}

# Nettoyage du répertoire de production
Write-LogMessage "Nettoyage du répertoire de production..."
Get-ChildItem -Path $ProductionDir -Exclude "data", "logs", "config.ini" | Remove-Item -Recurse -Force

# Déploiement des fichiers depuis staging vers production
Write-LogMessage "Déploiement des fichiers vers l'environnement de production..."
Copy-Item -Path "$StagingDir\*" -Destination $ProductionDir -Recurse -Force -Exclude @("data", "logs", "config.ini", "venv")

# Création ou mise à jour du fichier de configuration
if (-not (Test-Path -Path "$ProductionDir\config.ini" -PathType Leaf)) {
    Write-LogMessage "Création du fichier de configuration pour l'environnement de production..."
    # Copie du fichier de configuration de staging en l'adaptant
    $configContent = Get-Content -Path "$StagingDir\config.ini" -Raw
    $configContent = $configContent -replace "environment = .*", "environment = production"
    $configContent = $configContent -replace "debug = .*", "debug = False"
    $configContent = $configContent -replace "name = .*", "name = Technicia OCR - Production"
    $configContent = $configContent -replace "data_dir = .*", "data_dir = $ProductionDir\data"
    $configContent = $configContent -replace "log_dir = .*", "log_dir = $ProductionDir\logs"
    
    $configContent | Set-Content -Path "$ProductionDir\config.ini" -Force
    Write-LogMessage "Fichier de configuration créé."
} else {
    Write-LogMessage "Mise à jour du fichier de configuration existant..."
    $configContent = Get-Content -Path "$ProductionDir\config.ini" -Raw
    $configContent = $configContent -replace "environment = .*", "environment = production"
    $configContent = $configContent -replace "debug = .*", "debug = False"
    
    $configContent | Set-Content -Path "$ProductionDir\config.ini" -Force
}

# Création des répertoires de données et logs s'ils n'existent pas
Write-LogMessage "Vérification des répertoires de données et logs..."
$dataDirs = @(
    "$ProductionDir\data",
    "$ProductionDir\data\uploads",
    "$ProductionDir\data\processed",
    "$ProductionDir\data\temp",
    "$ProductionDir\data\cache",
    "$ProductionDir\logs"
)

foreach ($dir in $dataDirs) {
    if (-not (Test-Path -Path $dir -PathType Container)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
        Write-LogMessage "Répertoire créé: $dir"
    }
}

# Installation de l'environnement virtuel Python (si nécessaire)
if (-not (Test-Path -Path "$ProductionDir\venv" -PathType Container)) {
    Write-LogMessage "Création de l'environnement virtuel Python..."
    
    # Vérification de la présence de Python
    if (-not (Get-Command -Name "python" -ErrorAction SilentlyContinue)) {
        Write-LogMessage "Python n'est pas installé ou n'est pas dans le PATH." "ERROR"
        exit 1
    }
    
    # Création de l'environnement virtuel
    Set-Location -Path $ProductionDir
    & python -m venv venv
    
    # Activation de l'environnement virtuel et installation des dépendances
    & "$ProductionDir\venv\Scripts\Activate.ps1"
    & python -m pip install -r requirements.txt
    deactivate
} else {
    Write-LogMessage "Mise à jour des dépendances Python..."
    & "$ProductionDir\venv\Scripts\Activate.ps1"
    & python -m pip install --upgrade -r requirements.txt
    deactivate
}

# Installation ou mise à jour des services Windows
Write-LogMessage "Installation ou mise à jour des services Windows..."

# Vérification de NSSM (Non-Sucking Service Manager)
if (-not (Get-Command -Name "nssm" -ErrorAction SilentlyContinue)) {
    Write-LogMessage "NSSM n'est pas installé. L'installation des services est ignorée." "WARN"
} else {
    # Service API
    if (Get-Service -Name "TechniciaOCR-API" -ErrorAction SilentlyContinue) {
        Write-LogMessage "Mise à jour du service API..."
        & nssm set "TechniciaOCR-API" Application "$ProductionDir\venv\Scripts\python.exe"
        & nssm set "TechniciaOCR-API" AppParameters "$ProductionDir\app.py"
        & nssm set "TechniciaOCR-API" AppDirectory "$ProductionDir"
    } else {
        Write-LogMessage "Installation du service API..."
        & nssm install "TechniciaOCR-API" "$ProductionDir\venv\Scripts\python.exe" "$ProductionDir\app.py"
        & nssm set "TechniciaOCR-API" AppDirectory "$ProductionDir"
        & nssm set "TechniciaOCR-API" DisplayName "Technicia OCR API"
        & nssm set "TechniciaOCR-API" Description "Service API pour le système OCR Technicia"
        & nssm set "TechniciaOCR-API" Start SERVICE_AUTO_START
        & nssm set "TechniciaOCR-API" AppStdout "$ProductionDir\logs\api_stdout.log"
        & nssm set "TechniciaOCR-API" AppStderr "$ProductionDir\logs\api_stderr.log"
    }
    
    # Service Worker
    if (Get-Service -Name "TechniciaOCR-Worker" -ErrorAction SilentlyContinue) {
        Write-LogMessage "Mise à jour du service Worker..."
        & nssm set "TechniciaOCR-Worker" Application "$ProductionDir\venv\Scripts\celery.exe"
        & nssm set "TechniciaOCR-Worker" AppParameters "-A app.celery_app worker --loglevel=info --concurrency=4"
        & nssm set "TechniciaOCR-Worker" AppDirectory "$ProductionDir"
    } else {
        Write-LogMessage "Installation du service Worker..."
        & nssm install "TechniciaOCR-Worker" "$ProductionDir\venv\Scripts\celery.exe" "-A app.celery_app worker --loglevel=info --concurrency=4"
        & nssm set "TechniciaOCR-Worker" AppDirectory "$ProductionDir"
        & nssm set "TechniciaOCR-Worker" DisplayName "Technicia OCR Worker"
        & nssm set "TechniciaOCR-Worker" Description "Service Worker pour le système OCR Technicia"
        & nssm set "TechniciaOCR-Worker" Start SERVICE_AUTO_START
        & nssm set "TechniciaOCR-Worker" AppStdout "$ProductionDir\logs\worker_stdout.log"
        & nssm set "TechniciaOCR-Worker" AppStderr "$ProductionDir\logs\worker_stderr.log"
    }
    
    # Service Beat
    if (Get-Service -Name "TechniciaOCR-Beat" -ErrorAction SilentlyContinue) {
        Write-LogMessage "Mise à jour du service Beat..."
        & nssm set "TechniciaOCR-Beat" Application "$ProductionDir\venv\Scripts\celery.exe"
        & nssm set "TechniciaOCR-Beat" AppParameters "-A app.celery_app beat --loglevel=info"
        & nssm set "TechniciaOCR-Beat" AppDirectory "$ProductionDir"
    } else {
        Write-LogMessage "Installation du service Beat..."
        & nssm install "TechniciaOCR-Beat" "$ProductionDir\venv\Scripts\celery.exe" "-A app.celery_app beat --loglevel=info"
        & nssm set "TechniciaOCR-Beat" AppDirectory "$ProductionDir"
        & nssm set "TechniciaOCR-Beat" DisplayName "Technicia OCR Beat"
        & nssm set "TechniciaOCR-Beat" Description "Service Beat pour le système OCR Technicia"
        & nssm set "TechniciaOCR-Beat" Start SERVICE_AUTO_START
        & nssm set "TechniciaOCR-Beat" AppStdout "$ProductionDir\logs\beat_stdout.log"
        & nssm set "TechniciaOCR-Beat" AppStderr "$ProductionDir\logs\beat_stderr.log"
    }
    
    # Démarrage des services
    Write-LogMessage "Démarrage des services..."
    Start-Service -Name "TechniciaOCR-API"
    Start-Service -Name "TechniciaOCR-Worker"
    Start-Service -Name "TechniciaOCR-Beat"
}

# Vérification de l'état des services
Write-LogMessage "Vérification de l'état des services..."
$allServicesRunning = $true
foreach ($service in $productionServices) {
    if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
        $status = (Get-Service -Name $service).Status
        if ($status -ne "Running") {
            $allServicesRunning = $false
            Write-LogMessage "Le service $service n'est pas démarré (état actuel: $status)." "ERROR"
        } else {
            Write-LogMessage "Le service $service est en cours d'exécution." "SUCCESS"
        }
    }
}

if (-not $allServicesRunning) {
    Write-LogMessage "Au moins un service n'a pas démarré correctement. Veuillez vérifier les journaux pour plus de détails." "ERROR"
} else {
    Write-LogMessage "Tous les services ont démarré avec succès." "SUCCESS"
}

Write-LogMessage "Déploiement en environnement de production terminé !" "SUCCESS"
Write-LogMessage "L'application est accessible à l'adresse: http://localhost:5000"
Write-LogMessage ""
Write-LogMessage "Tâches supplémentaires à effectuer:"
Write-LogMessage " - Vérifier les journaux dans $ProductionDir\logs pour détecter les erreurs éventuelles"
Write-LogMessage " - Vérifier que toutes les fonctionnalités sont opérationnelles en production"
Write-LogMessage " - Configurer le monitoring et les alertes avec setup_monitoring.ps1"
Write-LogMessage " - Planifier des sauvegardes régulières avec schedule_backups.ps1"
