# Script de test des procédures de sauvegarde et restauration - Technicia OCR
# Version: 1.1
# Date: 10 avril 2025
#
# Ce script teste de manière automatisée les procédures de sauvegarde et restauration
# du système OCR Technicia en simulant un environnement de production, puis une défaillance
# et enfin la restauration complète du système.

# Vérification de la version PowerShell
#Requires -Version 5.1

# Force l'encodage en UTF-8 pour éviter les problèmes avec les caractères accentués
$OutputEncoding = [System.Text.UTF8Encoding]::new()

param (
    [string]$TestDir = "C:\Technicia\BackupRestoreTest",
    [string]$ProductionDir = "C:\Program Files\Technicia\OCRSystem",
    [string]$BackupDir = "C:\Technicia\Backups",
    [System.Security.SecureString]$DbPassword = (ConvertTo-SecureString "securePwd123!" -AsPlainText -Force),
    [System.Security.SecureString]$RedisPassword = (ConvertTo-SecureString "secureRedisPwd!" -AsPlainText -Force),
    [switch]$CleanupAfterTest,
    [switch]$VerboseOutput,
    [switch]$SkipAdminCheck,
    [switch]$TestMode,
    [string]$LogPrefix = ""
)

#region Fonctions utilitaires

function Write-LogMessage {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS", "TEST")]
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colorMap = @{
        "INFO" = "White";
        "WARN" = "Yellow";
        "ERROR" = "Red";
        "SUCCESS" = "Green";
        "TEST" = "Cyan"
    }
    
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $colorMap[$Level]
    
    # Écriture du log dans un fichier avec encodage UTF-8 explicite
    $logFilePath = Join-Path -Path $TestDir -ChildPath "logs\backup_restore_test.log"
    
    # Création du répertoire de logs s'il n'existe pas
    $logDir = Split-Path -Parent $logFilePath
    if (-not (Test-Path -Path $logDir -PathType Container)) {
        New-Item -Path $logDir -ItemType Directory -Force | Out-Null
    }
    
    "[{0}] [{1}] {2}" -f $timestamp, $Level, $Message | Out-File -FilePath $logFilePath -Append -Encoding UTF8
}

function Test-AdminPrivileges {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$false)]
        [switch]$SkipCheck
    )
    
    if ($SkipCheck) {
        Write-LogMessage "Vérification des privilèges administrateur ignorée (mode test)." "WARN"
        return $true
    }
    
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-LogMessage "Ce script doit être exécuté avec des privilèges administrateur." "ERROR"
        return $false
    }
    Write-LogMessage "Vérification des privilèges administrateur réussie." "SUCCESS"
    return $true
}

function Initialize-TestEnvironment {
    Write-LogMessage "Initialisation de l'environnement de test..." "TEST"
    
    # Création des répertoires de test
    $directories = @(
        $TestDir,
        "$TestDir\db",
        "$TestDir\redis",
        "$TestDir\data",
        "$TestDir\logs",
        "$TestDir\config",
        "$TestDir\restore",
        "$BackupDir",
        "$BackupDir\db",
        "$BackupDir\config",
        "$BackupDir\data"
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path -Path $dir -PathType Container)) {
            New-Item -Path $dir -ItemType Directory -Force | Out-Null
            Write-LogMessage "Répertoire créé: $dir"
        }
    }
    
    # Création de fichiers de test pour simuler des données de production
    Write-LogMessage "Création des fichiers de test..."
    
    # Fichiers de configuration de test
    $configContent = @"
# Configuration du système OCR Technicia
# Généré pour les tests de sauvegarde et restauration

[General]
AppName = Technicia OCR System
Version = 2.1.0
Mode = Production
LogLevel = Info
MaxThreads = 8

[Database]
Host = localhost
Port = 5432
Name = ocr_db
User = technicia
Password = $($DbPassword | ConvertFrom-SecureString -AsPlainText)
MaxConnections = 20
ConnectionTimeout = 30

[Redis]
Host = localhost
Port = 6379
Password = $($RedisPassword | ConvertFrom-SecureString -AsPlainText)
DBIndex = 0

[OCR]
Engine = Tesseract
Languages = fra,eng,deu
ModelPath = C:\Program Files\Technicia\OCRSystem\models
Accuracy = High
EnableGPU = True

[API]
Port = 5000
Host = 0.0.0.0
RateLimitPerMinute = 100
EnableSwagger = True
"@
    $configContent | Out-File -FilePath "$TestDir\config\app_config.ini" -Encoding utf8
    
    # Création d'une base de données de test (simulation)
    Write-LogMessage "Création d'une base de données de test (simulation)..."
    
    # Création d'un dump SQL de test
    $sqlDumpContent = @"
-- Dump de la base de données OCR Technicia pour test de sauvegarde/restauration
-- Version: 1.0
-- Date: 7 avril 2025

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50),
    md5_hash VARCHAR(32),
    uploaded_by INTEGER REFERENCES users(id),
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(20) DEFAULT 'pending'
);

CREATE TABLE processing_results (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    result_type VARCHAR(50) NOT NULL,
    content TEXT,
    confidence FLOAT,
    processing_time FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insertion de données de test
INSERT INTO users (username, email, full_name, password_hash, is_admin) VALUES
('admin', 'admin@technicia.com', 'Admin Technicia', 'hashed_password_here', TRUE),
('user1', 'user1@example.com', 'User One', 'hashed_password_here', FALSE),
('user2', 'user2@example.com', 'User Two', 'hashed_password_here', FALSE);

INSERT INTO documents (title, file_path, file_size, file_type, md5_hash, uploaded_by, processing_status) VALUES
('Document Test 1', '/data/documents/doc1.pdf', 1024000, 'pdf', '5f4dcc3b5aa765d61d8327deb882cf99', 1, 'completed'),
('Document Test 2', '/data/documents/doc2.docx', 524288, 'docx', '7c6a180b36896a0a8c02787eeafb0e4c', 2, 'completed'),
('Document Test 3', '/data/documents/doc3.pdf', 2048576, 'pdf', '6cb75f652a9b52798eb6cf2201057c73', 3, 'processing');

INSERT INTO processing_results (document_id, result_type, content, confidence, processing_time) VALUES
(1, 'text', 'Contenu textuel extrait du document 1', 0.95, 2.3),
(1, 'tables', '[{"table": "Table 1", "rows": 5, "columns": 3}]', 0.87, 1.1),
(2, 'text', 'Contenu textuel extrait du document 2', 0.92, 1.8),
(2, 'formulas', '[{"formula": "E=mc^2", "confidence": 0.88}]', 0.88, 0.9);
"@
    $sqlDumpContent | Out-File -FilePath "$TestDir\db\ocr_db_dump.sql" -Encoding utf8
    
    # Création de fichiers documents de test
    1..10 | ForEach-Object {
        $randomSize = Get-Random -Minimum 512 -Maximum 4096
        $randomContent = -join ((65..90) + (97..122) | Get-Random -Count $randomSize | ForEach-Object {[char]$_})
        $randomContent | Out-File -FilePath "$TestDir\data\test_document_$_.txt" -Encoding utf8
    }
    
    # Création d'un fichier Redis de test (simulation)
    $redisContent = @"
# Redis DB dump pour test
# Technicia OCR System

SET ocr:settings:engine "Tesseract"
SET ocr:settings:lang "fra,eng,deu"
SET ocr:stats:documents_processed 1342
SET ocr:stats:success_rate 0.94
SET ocr:stats:avg_processing_time 2.45
SADD ocr:active_users "user1" "user2" "admin"
LPUSH ocr:processing_queue "doc123" "doc456" "doc789"
HSET ocr:document:doc123 "status" "processing" "start_time" "1617791452" "priority" "high"
HSET ocr:document:doc456 "status" "queued" "start_time" "1617791453" "priority" "normal"
HSET ocr:document:doc789 "status" "queued" "start_time" "1617791454" "priority" "low"
"@
    $redisContent | Out-File -FilePath "$TestDir\redis\redis_dump.txt" -Encoding utf8
    
    Write-LogMessage "Environnement de test initialisé avec succès." "SUCCESS"
    return $true
}

function Invoke-SystemBackup {
    param (
        [Parameter(Mandatory=$true)]
        [string]$BackupName
    )
    
    Write-LogMessage "Démarrage de la procédure de sauvegarde: $BackupName..." "TEST"
    
    # Création du dossier de sauvegarde spécifique
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = Join-Path -Path $BackupDir -ChildPath "$BackupName`_$timestamp"
    
    if (-not (Test-Path -Path $backupPath -PathType Container)) {
        New-Item -Path $backupPath -ItemType Directory -Force | Out-Null
        Write-LogMessage "Dossier de sauvegarde créé: $backupPath"
    }
    
    # Sous-dossiers pour les différents types de sauvegarde
    $dbBackupPath = Join-Path -Path $backupPath -ChildPath "db"
    $configBackupPath = Join-Path -Path $backupPath -ChildPath "config"
    $dataBackupPath = Join-Path -Path $backupPath -ChildPath "data"
    
    New-Item -Path $dbBackupPath -ItemType Directory -Force | Out-Null
    New-Item -Path $configBackupPath -ItemType Directory -Force | Out-Null
    New-Item -Path $dataBackupPath -ItemType Directory -Force | Out-Null
    
    # Sauvegarde de la base de données
    Write-LogMessage "Sauvegarde de la base de données..."
    try {
        Copy-Item -Path "$TestDir\db\ocr_db_dump.sql" -Destination "$dbBackupPath\ocr_db_dump.sql" -Force
        Write-LogMessage "Sauvegarde de la base de données réussie." "SUCCESS"
    }
    catch {
        Write-LogMessage "Erreur lors de la sauvegarde de la base de données: $_" "ERROR"
        return $false
    }
    
    # Sauvegarde des fichiers de configuration
    Write-LogMessage "Sauvegarde des fichiers de configuration..."
    try {
        Copy-Item -Path "$TestDir\config\*" -Destination $configBackupPath -Recurse -Force
        Write-LogMessage "Sauvegarde des fichiers de configuration réussie." "SUCCESS"
    }
    catch {
        Write-LogMessage "Erreur lors de la sauvegarde des fichiers de configuration: $_" "ERROR"
        return $false
    }
    
    # Sauvegarde des données utilisateurs
    Write-LogMessage "Sauvegarde des données utilisateurs..."
    try {
        Copy-Item -Path "$TestDir\data\*" -Destination $dataBackupPath -Recurse -Force
        Write-LogMessage "Sauvegarde des données utilisateurs réussie." "SUCCESS"
    }
    catch {
        Write-LogMessage "Erreur lors de la sauvegarde des données utilisateurs: $_" "ERROR"
        return $false
    }
    
    # Sauvegarde des données Redis
    Write-LogMessage "Sauvegarde des données Redis..."
    try {
        Copy-Item -Path "$TestDir\redis\redis_dump.txt" -Destination "$dbBackupPath\redis_dump.txt" -Force
        Write-LogMessage "Sauvegarde des données Redis réussie." "SUCCESS"
    }
    catch {
        Write-LogMessage "Erreur lors de la sauvegarde des données Redis: $_" "ERROR"
        return $false
    }
    
    # Création d'un fichier de métadonnées pour la sauvegarde
    $backupMetadata = @"
# Métadonnées de sauvegarde du système OCR Technicia
# Généré automatiquement

[Backup]
BackupName = $BackupName
Timestamp = $timestamp
CreatedBy = $env:USERNAME
BackupVersion = 1.0

[System]
AppVersion = 2.1.0
DBVersion = 1.0
RedisVersion = 6.2.6
"@
    $backupMetadata | Out-File -FilePath "$backupPath\backup_metadata.ini" -Encoding utf8
    
    Write-LogMessage "Sauvegarde complète terminée avec succès." "SUCCESS"
    return $backupPath
}

function Invoke-SystemCorruption {
    Write-LogMessage "Simulation d'une corruption du système..." "TEST"
    
    # Simulation de corruption de fichiers de configuration
    Write-LogMessage "Corruption des fichiers de configuration..."
    try {
        $configFile = "$TestDir\config\app_config.ini"
        if (Test-Path -Path $configFile -PathType Leaf) {
            $corruptedContent = "FICHIER CORROMPU - NE PAS UTILISER`r`n"
            $corruptedContent | Out-File -FilePath $configFile -Encoding utf8 -Force
            Write-LogMessage "Fichier de configuration corrompu: $configFile" "SUCCESS"
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la corruption des fichiers de configuration: $_" "ERROR"
    }
    
    # Simulation de suppression de certains fichiers de données
    Write-LogMessage "Suppression de fichiers de données..."
    try {
        $dataFiles = Get-ChildItem -Path "$TestDir\data" -Filter "test_document_*.txt" | Select-Object -First 3
        foreach ($file in $dataFiles) {
            Remove-Item -Path $file.FullName -Force
            Write-LogMessage "Fichier de données supprimé: $($file.FullName)" "SUCCESS"
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la suppression des fichiers de données: $_" "ERROR"
    }
    
    # Simulation de corruption de la base de données
    Write-LogMessage "Corruption de la base de données..."
    try {
        $dbFile = "$TestDir\db\ocr_db_dump.sql"
        if (Test-Path -Path $dbFile -PathType Leaf) {
            $corruptedContent = "-- BASE DE DONNÉES CORROMPUE`r`n-- NE PAS RESTAURER`r`n"
            $corruptedContent | Out-File -FilePath $dbFile -Encoding utf8 -Force
            Write-LogMessage "Base de données corrompue: $dbFile" "SUCCESS"
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la corruption de la base de données: $_" "ERROR"
    }
    
    # Simulation de corruption du cache Redis
    Write-LogMessage "Corruption du cache Redis..."
    try {
        $redisFile = "$TestDir\redis\redis_dump.txt"
        if (Test-Path -Path $redisFile -PathType Leaf) {
            $corruptedContent = "# REDIS DUMP CORROMPU - NE PAS UTILISER`r`n"
            $corruptedContent | Out-File -FilePath $redisFile -Encoding utf8 -Force
            Write-LogMessage "Cache Redis corrompu: $redisFile" "SUCCESS"
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la corruption du cache Redis: $_" "ERROR"
    }
    
    Write-LogMessage "Simulation de corruption du système terminée." "SUCCESS"
    return $true
}

function Invoke-SystemRestore {
    param (
        [Parameter(Mandatory=$true)]
        [string]$BackupPath
    )
    
    Write-LogMessage "Démarrage de la procédure de restauration depuis: $BackupPath..." "TEST"
    
    # Vérification que le dossier de sauvegarde existe
    if (-not (Test-Path -Path $BackupPath -PathType Container)) {
        Write-LogMessage "Le dossier de sauvegarde n'existe pas: $BackupPath" "ERROR"
        return $false
    }
    
    # Vérification des métadonnées de sauvegarde
    $metadataFile = Join-Path -Path $BackupPath -ChildPath "backup_metadata.ini"
    if (-not (Test-Path -Path $metadataFile -PathType Leaf)) {
        Write-LogMessage "Fichier de métadonnées de sauvegarde introuvable: $metadataFile" "ERROR"
        return $false
    }
    
    # Création du dossier de restauration
    $restorePath = Join-Path -Path $TestDir -ChildPath "restore"
    if (-not (Test-Path -Path $restorePath -PathType Container)) {
        New-Item -Path $restorePath -ItemType Directory -Force | Out-Null
    }
    
    # Restauration de la base de données
    Write-LogMessage "Restauration de la base de données..."
    try {
        $dbBackupFile = Join-Path -Path $BackupPath -ChildPath "db\ocr_db_dump.sql"
        if (Test-Path -Path $dbBackupFile -PathType Leaf) {
            Copy-Item -Path $dbBackupFile -Destination "$TestDir\db\ocr_db_dump.sql" -Force
            Write-LogMessage "Restauration de la base de données réussie." "SUCCESS"
        }
        else {
            Write-LogMessage "Fichier de sauvegarde de la base de données introuvable: $dbBackupFile" "ERROR"
            return $false
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la restauration de la base de données: $_" "ERROR"
        return $false
    }
    
    # Restauration des fichiers de configuration
    Write-LogMessage "Restauration des fichiers de configuration..."
    try {
        $configBackupPath = Join-Path -Path $BackupPath -ChildPath "config"
        if (Test-Path -Path $configBackupPath -PathType Container) {
            Copy-Item -Path "$configBackupPath\*" -Destination "$TestDir\config" -Recurse -Force
            Write-LogMessage "Restauration des fichiers de configuration réussie." "SUCCESS"
        }
        else {
            Write-LogMessage "Dossier de sauvegarde des configurations introuvable: $configBackupPath" "ERROR"
            return $false
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la restauration des fichiers de configuration: $_" "ERROR"
        return $false
    }
    
    # Restauration des données utilisateurs
    Write-LogMessage "Restauration des données utilisateurs..."
    try {
        $dataBackupPath = Join-Path -Path $BackupPath -ChildPath "data"
        if (Test-Path -Path $dataBackupPath -PathType Container) {
            Copy-Item -Path "$dataBackupPath\*" -Destination "$TestDir\data" -Recurse -Force
            Write-LogMessage "Restauration des données utilisateurs réussie." "SUCCESS"
        }
        else {
            Write-LogMessage "Dossier de sauvegarde des données introuvable: $dataBackupPath" "ERROR"
            return $false
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la restauration des données utilisateurs: $_" "ERROR"
        return $false
    }
    
    # Restauration des données Redis
    Write-LogMessage "Restauration des données Redis..."
    try {
        $redisBackupFile = Join-Path -Path $BackupPath -ChildPath "db\redis_dump.txt"
        if (Test-Path -Path $redisBackupFile -PathType Leaf) {
            Copy-Item -Path $redisBackupFile -Destination "$TestDir\redis\redis_dump.txt" -Force
            Write-LogMessage "Restauration des données Redis réussie." "SUCCESS"
        }
        else {
            Write-LogMessage "Fichier de sauvegarde Redis introuvable: $redisBackupFile" "ERROR"
            return $false
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la restauration des données Redis: $_" "ERROR"
        return $false
    }
    
    Write-LogMessage "Restauration du système terminée avec succès." "SUCCESS"
    return $true
}

function Test-SystemIntegrity {
    Write-LogMessage "Vérification de l'intégrité du système restauré..." "TEST"
    
    $integrityStatus = $true
    $errorCount = 0
    
    # Vérification des fichiers de configuration
    Write-LogMessage "Vérification des fichiers de configuration..."
    $configFile = "$TestDir\config\app_config.ini"
    if (Test-Path -Path $configFile -PathType Leaf) {
        $configContent = Get-Content -Path $configFile -Raw
        if ($configContent -like "*CORROMPU*") {
            Write-LogMessage "Fichier de configuration toujours corrompu: $configFile" "ERROR"
            $integrityStatus = $false
            $errorCount++
        }
        else {
            Write-LogMessage "Fichier de configuration intègre: $configFile" "SUCCESS"
        }
    }
    else {
        Write-LogMessage "Fichier de configuration manquant: $configFile" "ERROR"
        $integrityStatus = $false
        $errorCount++
    }
    
    # Vérification des fichiers de données
    Write-LogMessage "Vérification des fichiers de données..."
    $dataFilesCount = (Get-ChildItem -Path "$TestDir\data" -Filter "test_document_*.txt").Count
    if ($dataFilesCount -eq 10) {
        Write-LogMessage "Nombre correct de fichiers de données: $dataFilesCount" "SUCCESS"
    }
    else {
        Write-LogMessage "Nombre incorrect de fichiers de données: $dataFilesCount (attendu: 10)" "ERROR"
        $integrityStatus = $false
        $errorCount++
    }
    
    # Vérification de la base de données
    Write-LogMessage "Vérification de la base de données..."
    $dbFile = "$TestDir\db\ocr_db_dump.sql"
    if (Test-Path -Path $dbFile -PathType Leaf) {
        $dbContent = Get-Content -Path $dbFile -Raw
        if ($dbContent -like "*CORROMPU*") {
            Write-LogMessage "Base de données toujours corrompue: $dbFile" "ERROR"
            $integrityStatus = $false
            $errorCount++
        }
        else {
            Write-LogMessage "Base de données intègre: $dbFile" "SUCCESS"
        }
    }
    else {
        Write-LogMessage "Fichier de base de données manquant: $dbFile" "ERROR"
        $integrityStatus = $false
        $errorCount++
    }
    
    # Vérification du cache Redis
    Write-LogMessage "Vérification du cache Redis..."
    $redisFile = "$TestDir\redis\redis_dump.txt"
    if (Test-Path -Path $redisFile -PathType Leaf) {
        $redisContent = Get-Content -Path $redisFile -Raw
        if ($redisContent -like "*CORROMPU*") {
            Write-LogMessage "Cache Redis toujours corrompu: $redisFile" "ERROR"
            $integrityStatus = $false
            $errorCount++
        }
        else {
            Write-LogMessage "Cache Redis intègre: $redisFile" "SUCCESS"
        }
    }
    else {
        Write-LogMessage "Fichier de cache Redis manquant: $redisFile" "ERROR"
        $integrityStatus = $false
        $errorCount++
    }
    
    if ($integrityStatus) {
        Write-LogMessage "Vérification de l'intégrité du système réussie. Tous les composants sont intègres." "SUCCESS"
    }
    else {
        Write-LogMessage "Vérification de l'intégrité du système échouée. $errorCount erreur(s) détectée(s)." "ERROR"
    }
    
    return $integrityStatus
}

function Invoke-BackupRestoreTest {
    param (
        [Parameter(Mandatory=$true)]
        [string]$TestName,
        [switch]$IncludePerformanceTest
    )
    
    Write-LogMessage "==================================================" "TEST"
    Write-LogMessage "DÉBUT DU TEST: $TestName" "TEST"
    Write-LogMessage "==================================================" "TEST"
    
    # Étape 1: Initialisation de l'environnement de test
    Write-LogMessage "ÉTAPE 1: Initialisation de l'environnement de test..." "TEST"
    if (-not (Initialize-TestEnvironment)) {
        Write-LogMessage "Échec de l'initialisation de l'environnement de test. Abandon du test." "ERROR"
        return $false
    }
    
    # Étape 2: Création d'une sauvegarde initiale
    Write-LogMessage "ÉTAPE 2: Création d'une sauvegarde initiale..." "TEST"
    $backupPath = Invoke-SystemBackup -BackupName "InitialBackup"
    if (-not $backupPath -or -not (Test-Path -Path $backupPath -PathType Container)) {
        Write-LogMessage "Échec de la création de la sauvegarde initiale. Abandon du test." "ERROR"
        return $false
    }
    
    # Si demandé, exécuter un test de performance pour la sauvegarde
    if ($IncludePerformanceTest) {
        Write-LogMessage "Exécution d'un test de performance pour la sauvegarde..." "TEST"
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        
        # Création d'une sauvegarde avec plus de données pour le test de performance
        1..100 | ForEach-Object {
            $randomSize = Get-Random -Minimum 5120 -Maximum 10240
            $randomContent = -join ((65..90) + (97..122) | Get-Random -Count $randomSize | ForEach-Object {[char]$_})
            $randomContent | Out-File -FilePath "$TestDir\data\perf_test_$_.txt" -Encoding utf8
        }
        
        Invoke-SystemBackup -BackupName "PerformanceBackup"
        $sw.Stop()
        
        Write-LogMessage "Test de performance de sauvegarde terminé en $($sw.Elapsed.TotalSeconds) secondes." "SUCCESS"
    }
    
    # Étape 3: Simulation d'une corruption du système
    Write-LogMessage "ÉTAPE 3: Simulation d'une corruption du système..." "TEST"
    if (-not (Invoke-SystemCorruption)) {
        Write-LogMessage "Échec de la simulation de corruption. Abandon du test." "ERROR"
        return $false
    }
    
    # Étape 4: Restauration du système depuis la sauvegarde
    Write-LogMessage "ÉTAPE 4: Restauration du système depuis la sauvegarde..." "TEST"
    if (-not (Invoke-SystemRestore -BackupPath $backupPath)) {
        Write-LogMessage "Échec de la restauration du système. Abandon du test." "ERROR"
        return $false
    }
    
    # Si demandé, exécuter un test de performance pour la restauration
    if ($IncludePerformanceTest) {
        Write-LogMessage "Exécution d'un test de performance pour la restauration..." "TEST"
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        
        # Simulation d'une corruption
        Invoke-SystemCorruption
        
        # Restauration à partir de la sauvegarde de performance
        $perfBackupPath = Get-ChildItem -Path $BackupDir -Directory -Filter "PerformanceBackup*" | Sort-Object -Property LastWriteTime -Descending | Select-Object -First 1
        if ($perfBackupPath) {
            Invoke-SystemRestore -BackupPath $perfBackupPath.FullName
            $sw.Stop()
            Write-LogMessage "Test de performance de restauration terminé en $($sw.Elapsed.TotalSeconds) secondes." "SUCCESS"
        }
        else {
            Write-LogMessage "Sauvegarde de performance introuvable. Test ignoré." "WARN"
        }
    }
    
    # Étape 5: Vérification de l'intégrité du système restauré
    Write-LogMessage "ÉTAPE 5: Vérification de l'intégrité du système restauré..." "TEST"
    $integrityResult = Test-SystemIntegrity
    
    # Étape 6: Nettoyage (si demandé)
    if ($CleanupAfterTest) {
        Write-LogMessage "ÉTAPE 6: Nettoyage de l'environnement de test..." "TEST"
        try {
            Write-LogMessage "Suppression du répertoire de test: $TestDir"
            if (Test-Path -Path $TestDir -PathType Container) {
                Remove-Item -Path $TestDir -Recurse -Force
            }
            
            # Ne pas supprimer les sauvegardes par défaut
            # Write-LogMessage "Suppression du répertoire de sauvegarde: $BackupDir"
            # if (Test-Path -Path $BackupDir -PathType Container) {
            #     Remove-Item -Path $BackupDir -Recurse -Force
            # }
            
            Write-LogMessage "Nettoyage terminé avec succès." "SUCCESS"
        }
        catch {
            Write-LogMessage "Erreur lors du nettoyage: $_" "ERROR"
        }
    }
    else {
        Write-LogMessage "ÉTAPE 6: Nettoyage ignoré (option désactivée)." "INFO"
    }
    
    # Résumé du test
    Write-LogMessage "==================================================" "TEST"
    Write-LogMessage "RÉSUMÉ DU TEST: $TestName" "TEST"
    Write-LogMessage "==================================================" "TEST"
    
    if ($integrityResult) {
        Write-LogMessage "RÉSULTAT: SUCCÈS" "SUCCESS"
        Write-LogMessage "Le test de sauvegarde et restauration s'est terminé avec succès." "SUCCESS"
        Write-LogMessage "Le système a été correctement restauré et toutes les vérifications d'intégrité ont réussi." "SUCCESS"
    }
    else {
        Write-LogMessage "RÉSULTAT: ÉCHEC" "ERROR"
        Write-LogMessage "Le test de sauvegarde et restauration a échoué." "ERROR"
        Write-LogMessage "Le système n'a pas été correctement restauré ou certaines vérifications d'intégrité ont échoué." "ERROR"
    }
    
    # Génération d'un rapport de test
    $reportPath = "$env:USERPROFILE\Desktop\backup_restore_test_report_$($TestName)_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
    $logFilePath = Join-Path -Path $TestDir -ChildPath "logs\backup_restore_test.log"
    
    if (Test-Path -Path $logFilePath -PathType Leaf) {
        try {
            Copy-Item -Path $logFilePath -Destination $reportPath -Force
            Write-LogMessage "Rapport de test généré: $reportPath" "SUCCESS"
        }
        catch {
            Write-LogMessage "Erreur lors de la génération du rapport de test: $_" "ERROR"
        }
    }
    
    return $integrityResult
}

# Vérification des privilèges administrateur
$adminCheckResult = Test-AdminPrivileges -SkipCheck:$SkipAdminCheck
if (-not $adminCheckResult -and -not $TestMode) {
    Write-LogMessage "Exécution arrêtée en raison de l'absence de privilèges administrateur. Utilisez -SkipAdminCheck pour ignorer cette vérification en mode test." "ERROR"
    exit 1
}

# Définition des paramètres de test
$testConfig = @{
    TestName = "BackupRestoreTest_$(Get-Date -Format 'yyyyMMdd')"
    IncludePerformanceTest = $true
}

# Exécution du test
Write-Host "Démarrage du test complet de sauvegarde et restauration..." -ForegroundColor Cyan
Invoke-BackupRestoreTest @testConfig

# Affichage du résultat du test
if ($?) {
    Write-Host "Le test de sauvegarde et restauration a été exécuté avec succès." -ForegroundColor Green
    Write-Host "Un rapport détaillé a été généré sur le bureau." -ForegroundColor Green
    
    # Mise à jour du journal d'exécution global si demandé
    $testLogPath = "$TestDir\logs\test_execution_history.csv"
    $testResult = [PSCustomObject]@{
        Date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        TestName = "BackupRestore_$LogPrefix"
        Result = "Success"
        Details = "Tous les tests ont passé avec succès"
    }
    
    # Création du fichier s'il n'existe pas
    if (-not (Test-Path -Path $testLogPath)) {
        "Date,TestName,Result,Details" | Out-File -FilePath $testLogPath -Encoding UTF8
    }
    
    # Ajout de l'entrée dans le journal
    "$($testResult.Date),$($testResult.TestName),$($testResult.Result),$($testResult.Details)" | 
        Out-File -FilePath $testLogPath -Encoding UTF8 -Append
}
else {
    Write-Host "Le test de sauvegarde et restauration a échoué. Consultez le journal pour plus de détails." -ForegroundColor Red
    
    # Mise à jour du journal d'exécution global en cas d'échec
    $testLogPath = "$TestDir\logs\test_execution_history.csv"
    $testResult = [PSCustomObject]@{
        Date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        TestName = "BackupRestore_$LogPrefix"
        Result = "Failure"
        Details = "Consultez les logs détaillés pour plus d'informations"
    }
    
    # Création du fichier s'il n'existe pas
    if (-not (Test-Path -Path $testLogPath)) {
        "Date,TestName,Result,Details" | Out-File -FilePath $testLogPath -Encoding UTF8
    }
    
    # Ajout de l'entrée dans le journal
    "$($testResult.Date),$($testResult.TestName),$($testResult.Result),$($testResult.Details)" | 
        Out-File -FilePath $testLogPath -Encoding UTF8 -Append
}
