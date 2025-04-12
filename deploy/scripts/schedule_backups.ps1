# Script de planification des sauvegardes - Technicia OCR
# Version: 1.0
# Date: 2 avril 2025
#
# Ce script configure des sauvegardes automatiques régulières pour le système OCR Technicia.
# Il crée des tâches planifiées Windows pour sauvegarder les données et la base de données.

param (
    [string]$ProductionDir = "C:\Program Files\Technicia\OCRSystem",
    [string]$BackupDir = "C:\Technicia\Backups",
    [string]$BackupScriptDir = "C:\Technicia\Scripts",
    [ValidateSet("Quotidienne", "Hebdomadaire", "Mensuelle")]
    [string]$FrequenceDonnees = "Quotidienne",
    [ValidateSet("Quotidienne", "Hebdomadaire", "Mensuelle")]
    [string]$FrequenceDB = "Quotidienne",
    [string]$HeureBackupDonnees = "23:00",
    [string]$HeureBackupDB = "23:30",
    [string]$NomUtilisateur = "",
    [string]$MotDePasse = "",
    [int]$RetentionJours = 30
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

# Vérification de l'existence du répertoire de production
if (-not (Test-Path -Path $ProductionDir -PathType Container)) {
    Write-LogMessage "Le répertoire de production n'existe pas: $ProductionDir" "ERROR"
    exit 1
}

# Création des répertoires nécessaires
Write-LogMessage "Création des répertoires nécessaires..."
if (-not (Test-Path -Path $BackupDir -PathType Container)) {
    New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
    Write-LogMessage "Répertoire de sauvegarde créé: $BackupDir" "SUCCESS"
}

if (-not (Test-Path -Path $BackupScriptDir -PathType Container)) {
    New-Item -Path $BackupScriptDir -ItemType Directory -Force | Out-Null
    Write-LogMessage "Répertoire de scripts de sauvegarde créé: $BackupScriptDir" "SUCCESS"
}

# Création du script de sauvegarde des données
Write-LogMessage "Création du script de sauvegarde des données..."
$backupDataScript = @"
# Script de sauvegarde des données - Technicia OCR
# Généré automatiquement par schedule_backups.ps1

param (
    [string]`$ProductionDir = "$ProductionDir",
    [string]`$BackupDir = "$BackupDir",
    [int]`$RetentionJours = $RetentionJours
)

`$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
`$backupTimestampDir = Join-Path -Path `$BackupDir -ChildPath "data_backup_`$timestamp"

# Création du répertoire de sauvegarde
New-Item -Path `$backupTimestampDir -ItemType Directory -Force | Out-Null

# Sauvegarde des répertoires de données
Copy-Item -Path "`$ProductionDir\data" -Destination `$backupTimestampDir -Recurse -Force

# Compression de la sauvegarde
Compress-Archive -Path "`$backupTimestampDir\*" -DestinationPath "`$backupTimestampDir.zip" -Force
Remove-Item -Path `$backupTimestampDir -Recurse -Force

# Nettoyage des anciennes sauvegardes
`$dateLimit = (Get-Date).AddDays(-`$RetentionJours)
Get-ChildItem -Path `$BackupDir -Filter "data_backup_*.zip" | Where-Object { `$_.CreationTime -lt `$dateLimit } | ForEach-Object {
    Remove-Item -Path `$_.FullName -Force
    Write-Host "Sauvegarde nettoyée: `$(`$_.Name)"
}

Write-Host "Sauvegarde des données terminée: `$backupTimestampDir.zip"
"@

$backupDataScriptPath = Join-Path -Path $BackupScriptDir -ChildPath "backup_data.ps1"
$backupDataScript | Set-Content -Path $backupDataScriptPath -Force

# Création du script de sauvegarde de la base de données
Write-LogMessage "Création du script de sauvegarde de la base de données..."
$backupDBScript = @"
# Script de sauvegarde de la base de données - Technicia OCR
# Généré automatiquement par schedule_backups.ps1

param (
    [string]`$BackupDir = "$BackupDir",
    [int]`$RetentionJours = $RetentionJours
)

`$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
`$backupFile = Join-Path -Path `$BackupDir -ChildPath "db_backup_`$timestamp.sql"

# Exécution de la sauvegarde PostgreSQL
`$env:PGPASSWORD = "securepassword" # Remplacer par le mot de passe réel
pg_dump -h localhost -U technicia -d ocr_db -f `$backupFile

# Compression de la sauvegarde
Compress-Archive -Path `$backupFile -DestinationPath "`$backupFile.zip" -Force
Remove-Item -Path `$backupFile -Force

# Nettoyage des anciennes sauvegardes
`$dateLimit = (Get-Date).AddDays(-`$RetentionJours)
Get-ChildItem -Path `$BackupDir -Filter "db_backup_*.zip" | Where-Object { `$_.CreationTime -lt `$dateLimit } | ForEach-Object {
    Remove-Item -Path `$_.FullName -Force
    Write-Host "Sauvegarde nettoyée: `$(`$_.Name)"
}

Write-Host "Sauvegarde de la base de données terminée: `$backupFile.zip"
"@

$backupDBScriptPath = Join-Path -Path $BackupScriptDir -ChildPath "backup_db.ps1"
$backupDBScript | Set-Content -Path $backupDBScriptPath -Force

# Préparation des tâches planifiées
Write-LogMessage "Configuration des tâches planifiées..."

# Tâche de sauvegarde des données
$taskNameData = "TechniciaOCR-DataBackup"
$taskDescData = "Sauvegarde automatique des données du système OCR Technicia"
$taskActionData = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$backupDataScriptPath`""

# Configuration du déclencheur en fonction de la fréquence
switch ($FrequenceDonnees) {
    "Quotidienne" {
        $heure = [timespan]::Parse($HeureBackupDonnees)
        $triggerData = New-ScheduledTaskTrigger -Daily -At $HeureBackupDonnees
    }
    "Hebdomadaire" {
        $heure = [timespan]::Parse($HeureBackupDonnees)
        $triggerData = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $HeureBackupDonnees
    }
    "Mensuelle" {
        $heure = [timespan]::Parse($HeureBackupDonnees)
        $triggerData = New-ScheduledTaskTrigger -Monthly -DaysOfMonth 1 -At $HeureBackupDonnees
    }
}

# Tâche de sauvegarde de la base de données
$taskNameDB = "TechniciaOCR-DBBackup"
$taskDescDB = "Sauvegarde automatique de la base de données du système OCR Technicia"
$taskActionDB = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$backupDBScriptPath`""

# Configuration du déclencheur en fonction de la fréquence
switch ($FrequenceDB) {
    "Quotidienne" {
        $heure = [timespan]::Parse($HeureBackupDB)
        $triggerDB = New-ScheduledTaskTrigger -Daily -At $HeureBackupDB
    }
    "Hebdomadaire" {
        $heure = [timespan]::Parse($HeureBackupDB)
        $triggerDB = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $HeureBackupDB
    }
    "Mensuelle" {
        $heure = [timespan]::Parse($HeureBackupDB)
        $triggerDB = New-ScheduledTaskTrigger -Monthly -DaysOfMonth 1 -At $HeureBackupDB
    }
}

# Configuration des options de tâche
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Création des tâches planifiées
Write-LogMessage "Création de la tâche planifiée de sauvegarde des données..."
if (Get-ScheduledTask -TaskName $taskNameData -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskNameData -Confirm:$false
}

if ([string]::IsNullOrEmpty($NomUtilisateur)) {
    # Utilisation du compte SYSTEM si aucun utilisateur n'est spécifié
    Register-ScheduledTask -TaskName $taskNameData -Action $taskActionData -Trigger $triggerData -Settings $taskSettings -Description $taskDescData -RunLevel Highest | Out-Null
} else {
    Register-ScheduledTask -TaskName $taskNameData -Action $taskActionData -Trigger $triggerData -Settings $taskSettings -Description $taskDescData -User $NomUtilisateur -Password $MotDePasse -RunLevel Highest | Out-Null
}

Write-LogMessage "Création de la tâche planifiée de sauvegarde de la base de données..."
if (Get-ScheduledTask -TaskName $taskNameDB -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskNameDB -Confirm:$false
}

if ([string]::IsNullOrEmpty($NomUtilisateur)) {
    # Utilisation du compte SYSTEM si aucun utilisateur n'est spécifié
    Register-ScheduledTask -TaskName $taskNameDB -Action $taskActionDB -Trigger $triggerDB -Settings $taskSettings -Description $taskDescDB -RunLevel Highest | Out-Null
} else {
    Register-ScheduledTask -TaskName $taskNameDB -Action $taskActionDB -Trigger $triggerDB -Settings $taskSettings -Description $taskDescDB -User $NomUtilisateur -Password $MotDePasse -RunLevel Highest | Out-Null
}

# Création du script de restauration
Write-LogMessage "Création du script de restauration..."
$restoreScript = @"
# Script de restauration des sauvegardes - Technicia OCR
# Généré automatiquement par schedule_backups.ps1

param (
    [Parameter(Mandatory=`$true)]
    [string]`$BackupFile,
    [string]`$ProductionDir = "$ProductionDir",
    [switch]`$RestoreData = `$false,
    [switch]`$RestoreDB = `$false
)

function Write-LogMessage {
    param (
        [Parameter(Mandatory=`$true)]
        [string]`$Message,
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS")]
        [string]`$Level = "INFO"
    )
    
    `$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    `$colorMap = @{
        "INFO" = "White";
        "WARN" = "Yellow";
        "ERROR" = "Red";
        "SUCCESS" = "Green"
    }
    
    Write-Host "[`$timestamp] [`$Level] `$Message" -ForegroundColor `$colorMap[`$Level]
}

# Vérification des droits d'administrateur
`$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not `$isAdmin) {
    Write-LogMessage "Ce script doit être exécuté avec des privilèges administrateur." "ERROR"
    exit 1
}

# Vérification de l'existence du fichier de sauvegarde
if (-not (Test-Path -Path `$BackupFile -PathType Leaf)) {
    Write-LogMessage "Le fichier de sauvegarde n'existe pas: `$BackupFile" "ERROR"
    exit 1
}

# Vérification du type de sauvegarde
`$isDataBackup = `$BackupFile -like "*data_backup*"
`$isDBBackup = `$BackupFile -like "*db_backup*"

if (-not (`$isDataBackup -or `$isDBBackup)) {
    Write-LogMessage "Type de sauvegarde non reconnu. Le nom du fichier doit contenir 'data_backup' ou 'db_backup'." "ERROR"
    exit 1
}

if (`$isDataBackup -and -not `$RestoreData) {
    Write-LogMessage "Pour restaurer les données, utilisez le paramètre -RestoreData" "ERROR"
    exit 1
}

if (`$isDBBackup -and -not `$RestoreDB) {
    Write-LogMessage "Pour restaurer la base de données, utilisez le paramètre -RestoreDB" "ERROR"
    exit 1
}

# Arrêt des services
Write-LogMessage "Arrêt des services..."
`$services = @("TechniciaOCR-API", "TechniciaOCR-Worker", "TechniciaOCR-Beat")
foreach (`$service in `$services) {
    if (Get-Service -Name `$service -ErrorAction SilentlyContinue) {
        Stop-Service -Name `$service -Force
        Write-LogMessage "Service `$service arrêté."
    }
}

# Restauration
if (`$isDataBackup -and `$RestoreData) {
    Write-LogMessage "Restauration des données..."
    
    # Extraction de la sauvegarde
    `$tempDir = Join-Path -Path `$env:TEMP -ChildPath ([System.Guid]::NewGuid().ToString())
    New-Item -Path `$tempDir -ItemType Directory -Force | Out-Null
    
    Expand-Archive -Path `$BackupFile -DestinationPath `$tempDir -Force
    
    # Sauvegarde des données actuelles
    `$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    `$currentDataBackup = Join-Path -Path (Split-Path -Path `$ProductionDir -Parent) -ChildPath "data_before_restore_`$timestamp"
    Copy-Item -Path "`$ProductionDir\data" -Destination `$currentDataBackup -Recurse -Force
    
    # Restauration des données
    Copy-Item -Path "`$tempDir\data\*" -Destination "`$ProductionDir\data" -Recurse -Force
    
    # Nettoyage
    Remove-Item -Path `$tempDir -Recurse -Force
    
    Write-LogMessage "Restauration des données terminée. Sauvegarde des données précédentes: `$currentDataBackup" "SUCCESS"
}

if (`$isDBBackup -and `$RestoreDB) {
    Write-LogMessage "Restauration de la base de données..."
    
    # Extraction de la sauvegarde
    `$tempDir = Join-Path -Path `$env:TEMP -ChildPath ([System.Guid]::NewGuid().ToString())
    New-Item -Path `$tempDir -ItemType Directory -Force | Out-Null
    
    Expand-Archive -Path `$BackupFile -DestinationPath `$tempDir -Force
    `$sqlFile = Get-ChildItem -Path `$tempDir -Filter "*.sql" | Select-Object -First 1
    
    if (`$null -eq `$sqlFile) {
        Write-LogMessage "Fichier SQL non trouvé dans la sauvegarde." "ERROR"
        Remove-Item -Path `$tempDir -Recurse -Force
        exit 1
    }
    
    # Restauration de la base de données
    `$env:PGPASSWORD = "securepassword" # Remplacer par le mot de passe réel
    
    # Sauvegarde de la base de données actuelle
    `$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    `$currentDBBackup = Join-Path -Path (Split-Path -Path `$BackupFile -Parent) -ChildPath "db_before_restore_`$timestamp.sql"
    pg_dump -h localhost -U technicia -d ocr_db -f `$currentDBBackup
    
    # Restauration
    psql -h localhost -U technicia -d ocr_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    psql -h localhost -U technicia -d ocr_db -f `$sqlFile.FullName
    
    # Nettoyage
    Remove-Item -Path `$tempDir -Recurse -Force
    
    Write-LogMessage "Restauration de la base de données terminée. Sauvegarde de la base de données précédente: `$currentDBBackup" "SUCCESS"
}

# Redémarrage des services
Write-LogMessage "Redémarrage des services..."
foreach (`$service in `$services) {
    if (Get-Service -Name `$service -ErrorAction SilentlyContinue) {
        Start-Service -Name `$service
        Write-LogMessage "Service `$service démarré."
    }
}

Write-LogMessage "Restauration terminée avec succès !" "SUCCESS"
"@

$restoreScriptPath = Join-Path -Path $BackupScriptDir -ChildPath "restore_backup.ps1"
$restoreScript | Set-Content -Path $restoreScriptPath -Force

Write-LogMessage "Configuration des sauvegardes terminée avec succès !" "SUCCESS"
Write-LogMessage ""
Write-LogMessage "Informations importantes:"
Write-LogMessage " - Sauvegarde des données: $FrequenceDonnees à $HeureBackupDonnees"
Write-LogMessage " - Sauvegarde de la base de données: $FrequenceDB à $HeureBackupDB"
Write-LogMessage " - Durée de rétention: $RetentionJours jours"
Write-LogMessage " - Répertoire des sauvegardes: $BackupDir"
Write-LogMessage " - Script de restauration: $restoreScriptPath"
Write-LogMessage ""
Write-LogMessage "Pour restaurer une sauvegarde de données:"
Write-LogMessage "  powershell -ExecutionPolicy Bypass -File $restoreScriptPath -BackupFile <chemin_sauvegarde> -RestoreData"
Write-LogMessage ""
Write-LogMessage "Pour restaurer une sauvegarde de base de données:"
Write-LogMessage "  powershell -ExecutionPolicy Bypass -File $restoreScriptPath -BackupFile <chemin_sauvegarde> -RestoreDB"
