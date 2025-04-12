# Script d'installation Technicia OCR pour Windows
# Version: 1.0
# Date: 2 avril 2025
#
# Ce script permet l'installation et la configuration du système OCR Technicia
# sur un serveur Windows.

# Paramètres configurables
param (
    [string]$InstallDir = "C:\Program Files\Technicia\OCRSystem",
    [string]$DataDir = "C:\Technicia\Data",
    [string]$LogDir = "C:\Technicia\Logs",
    [string]$PostgresPassword = "SecureP@ssw0rd",
    [string]$PostgresPort = "5432",
    [string]$AppPort = "5000",
    [switch]$SkipPython = $false,
    [switch]$SkipPostgres = $false,
    [switch]$SkipRedis = $false,
    [switch]$InstallAsService = $true
)

# Fonction pour afficher les messages avec horodatage
function Write-LogMessage {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR")]
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colorMap = @{
        "INFO" = "White";
        "WARN" = "Yellow";
        "ERROR" = "Red"
    }
    
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $colorMap[$Level]
}

# Fonction pour vérifier l'existence d'une commande
function Test-CommandExists {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Command
    )
    
    return [bool](Get-Command -Name $Command -ErrorAction SilentlyContinue)
}

# Vérification des droits d'administrateur
Write-LogMessage "Vérification des privilèges administrateur..."
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-LogMessage "Ce script doit être exécuté avec des privilèges administrateur." "ERROR"
    exit 1
}

# Création des répertoires nécessaires
Write-LogMessage "Création des répertoires d'installation..."
$directories = @(
    $InstallDir,
    $DataDir,
    "$DataDir\uploads",
    "$DataDir\processed",
    "$DataDir\temp",
    "$DataDir\cache",
    $LogDir
)

foreach ($dir in $directories) {
    if (-not (Test-Path -Path $dir -PathType Container)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
        Write-LogMessage "Répertoire créé: $dir"
    }
    else {
        Write-LogMessage "Le répertoire existe déjà: $dir" "WARN"
    }
}

# Installation de Python et pip si nécessaire
if (-not $SkipPython) {
    Write-LogMessage "Vérification de l'installation Python..."
    
    if (-not (Test-CommandExists "python")) {
        Write-LogMessage "Python n'est pas installé. Installation en cours..."
        
        # Téléchargement de Python
        $pythonUrl = "https://www.python.org/ftp/python/3.10.0/python-3.10.0-amd64.exe"
        $pythonInstaller = "$env:TEMP\python-3.10.0-amd64.exe"
        
        Write-LogMessage "Téléchargement de Python 3.10..."
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
        
        # Installation de Python
        Write-LogMessage "Installation de Python 3.10..."
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
        
        # Suppression du fichier d'installation
        Remove-Item -Path $pythonInstaller -Force
        
        # Vérification de l'installation
        if (-not (Test-CommandExists "python")) {
            Write-LogMessage "L'installation de Python a échoué." "ERROR"
            exit 1
        }
    }
    else {
        Write-LogMessage "Python est déjà installé: $(python --version)"
    }
    
    # Mise à jour de pip
    Write-LogMessage "Mise à jour de pip..."
    python -m pip install --upgrade pip
}

# Installation de PostgreSQL si nécessaire
if (-not $SkipPostgres) {
    Write-LogMessage "Vérification de l'installation PostgreSQL..."
    
    if (-not (Test-CommandExists "psql")) {
        Write-LogMessage "PostgreSQL n'est pas installé. Installation en cours..."
        
        # Téléchargement de PostgreSQL
        $postgresUrl = "https://get.enterprisedb.com/postgresql/postgresql-14.1-1-windows-x64.exe"
        $postgresInstaller = "$env:TEMP\postgresql-14.1-1-windows-x64.exe"
        
        Write-LogMessage "Téléchargement de PostgreSQL 14..."
        Invoke-WebRequest -Uri $postgresUrl -OutFile $postgresInstaller
        
        # Installation de PostgreSQL
        Write-LogMessage "Installation de PostgreSQL 14..."
        $installArgs = "--mode unattended --superpassword $PostgresPassword --serverport $PostgresPort --prefix `"C:\Program Files\PostgreSQL\14`" --datadir `"C:\Program Files\PostgreSQL\14\data`""
        Start-Process -FilePath $postgresInstaller -ArgumentList $installArgs -Wait
        
        # Suppression du fichier d'installation
        Remove-Item -Path $postgresInstaller -Force
        
        # Ajout de PostgreSQL au PATH
        $env:Path += ";C:\Program Files\PostgreSQL\14\bin"
        [Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::Machine)
        
        # Vérification de l'installation
        if (-not (Test-CommandExists "psql")) {
            Write-LogMessage "L'installation de PostgreSQL a échoué." "ERROR"
            exit 1
        }
    }
    else {
        Write-LogMessage "PostgreSQL est déjà installé: $(psql --version)"
    }
    
    # Création de la base de données et de l'utilisateur
    Write-LogMessage "Configuration de la base de données PostgreSQL..."
    
    # Commandes SQL pour la configuration
    $sqlCommands = @"
CREATE DATABASE ocr_db;
CREATE USER technicia WITH ENCRYPTED PASSWORD '$PostgresPassword';
GRANT ALL PRIVILEGES ON DATABASE ocr_db TO technicia;
"@
    
    # Enregistrement des commandes dans un fichier temporaire
    $sqlFile = "$env:TEMP\postgres_setup.sql"
    $sqlCommands | Set-Content -Path $sqlFile
    
    # Exécution des commandes SQL
    psql -U postgres -f $sqlFile
    
    # Suppression du fichier temporaire
    Remove-Item -Path $sqlFile -Force
}

# Installation de Redis si nécessaire
if (-not $SkipRedis) {
    Write-LogMessage "Vérification de l'installation Redis..."
    
    if (-not (Test-CommandExists "redis-cli")) {
        Write-LogMessage "Redis n'est pas installé. Installation en cours..."
        
        # Téléchargement de Redis
        $redisUrl = "https://github.com/microsoftarchive/redis/releases/download/win-3.2.100/Redis-x64-3.2.100.msi"
        $redisInstaller = "$env:TEMP\Redis-x64-3.2.100.msi"
        
        Write-LogMessage "Téléchargement de Redis..."
        Invoke-WebRequest -Uri $redisUrl -OutFile $redisInstaller
        
        # Installation de Redis
        Write-LogMessage "Installation de Redis..."
        Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", $redisInstaller, "/qn" -Wait
        
        # Suppression du fichier d'installation
        Remove-Item -Path $redisInstaller -Force
        
        # Vérification de l'installation
        if (-not (Test-CommandExists "redis-cli")) {
            Write-LogMessage "L'installation de Redis a échoué." "ERROR"
            exit 1
        }
    }
    else {
        Write-LogMessage "Redis est déjà installé: $(redis-cli --version)"
    }
}

# Installation de Tesseract OCR
Write-LogMessage "Installation de Tesseract OCR..."
$tesseractUrl = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v5.0.0-alpha.20200328.exe"
$tesseractInstaller = "$env:TEMP\tesseract-ocr-setup.exe"

if (-not (Test-Path -Path "C:\Program Files\Tesseract-OCR\tesseract.exe" -PathType Leaf)) {
    Write-LogMessage "Téléchargement de Tesseract OCR..."
    Invoke-WebRequest -Uri $tesseractUrl -OutFile $tesseractInstaller
    
    # Installation de Tesseract OCR
    Write-LogMessage "Installation de Tesseract OCR..."
    Start-Process -FilePath $tesseractInstaller -ArgumentList "/S" -Wait
    
    # Suppression du fichier d'installation
    Remove-Item -Path $tesseractInstaller -Force
    
    # Ajout de Tesseract au PATH
    $env:Path += ";C:\Program Files\Tesseract-OCR"
    [Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::Machine)
}
else {
    Write-LogMessage "Tesseract OCR est déjà installé"
}

# Téléchargement et extraction du code source de l'application
Write-LogMessage "Copie des fichiers de l'application vers le répertoire d'installation..."
# Supposons que nous avons le code source dans le répertoire courant
$sourceDir = (Get-Location).Path
Copy-Item -Path "$sourceDir\*" -Destination $InstallDir -Recurse -Force -Exclude @("deploy", "logs", "data", "*.git*")

# Création du fichier de configuration
Write-LogMessage "Création du fichier de configuration..."
$configContent = @"
# Configuration du système OCR Technicia
# Généré automatiquement par le script d'installation

[app]
name = Technicia OCR
environment = production
debug = False
secret_key = $([Guid]::NewGuid().ToString())
max_parallel_tasks = 4
ocr_quality_threshold = 0.75

[paths]
data_dir = $DataDir
log_dir = $LogDir

[database]
host = localhost
port = $PostgresPort
name = ocr_db
user = technicia
password = $PostgresPassword

[redis]
host = localhost
port = 6379
db = 0
"@

$configContent | Set-Content -Path "$InstallDir\config.ini" -Force

# Installation des dépendances Python
Write-LogMessage "Installation des dépendances Python..."
Set-Location -Path $InstallDir
python -m pip install -r requirements.txt

# Création du service Windows si demandé
if ($InstallAsService) {
    Write-LogMessage "Installation en tant que service Windows..."
    
    # Vérification de NSSM (Non-Sucking Service Manager)
    if (-not (Test-CommandExists "nssm")) {
        Write-LogMessage "NSSM n'est pas installé. Téléchargement et installation..."
        
        # Téléchargement de NSSM
        $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
        $nssmZip = "$env:TEMP\nssm-2.24.zip"
        $nssmExtractDir = "$env:TEMP\nssm-2.24"
        
        Write-LogMessage "Téléchargement de NSSM..."
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
        
        # Extraction de NSSM
        Write-LogMessage "Extraction de NSSM..."
        Expand-Archive -Path $nssmZip -DestinationPath $nssmExtractDir -Force
        
        # Copie de NSSM dans le répertoire système
        $nssmExe = Get-ChildItem -Path $nssmExtractDir -Recurse -Filter "nssm.exe" | Where-Object { $_.DirectoryName -like "*win64*" } | Select-Object -First 1
        Copy-Item -Path $nssmExe.FullName -Destination "C:\Windows\System32\" -Force
        
        # Suppression des fichiers temporaires
        Remove-Item -Path $nssmZip -Force
        Remove-Item -Path $nssmExtractDir -Recurse -Force
    }
    
    # Installation du service API
    Write-LogMessage "Installation du service API..."
    nssm install "TechniciaOCR-API" "python" "$InstallDir\app.py"
    nssm set "TechniciaOCR-API" AppDirectory "$InstallDir"
    nssm set "TechniciaOCR-API" DisplayName "Technicia OCR API"
    nssm set "TechniciaOCR-API" Description "Service API pour le système OCR Technicia"
    nssm set "TechniciaOCR-API" Start SERVICE_AUTO_START
    nssm set "TechniciaOCR-API" AppStdout "$LogDir\api_stdout.log"
    nssm set "TechniciaOCR-API" AppStderr "$LogDir\api_stderr.log"
    
    # Installation du service Worker
    Write-LogMessage "Installation du service Worker..."
    nssm install "TechniciaOCR-Worker" "celery" "-A app.celery_app worker --loglevel=info --concurrency=4"
    nssm set "TechniciaOCR-Worker" AppDirectory "$InstallDir"
    nssm set "TechniciaOCR-Worker" DisplayName "Technicia OCR Worker"
    nssm set "TechniciaOCR-Worker" Description "Service Worker pour le système OCR Technicia"
    nssm set "TechniciaOCR-Worker" Start SERVICE_AUTO_START
    nssm set "TechniciaOCR-Worker" AppStdout "$LogDir\worker_stdout.log"
    nssm set "TechniciaOCR-Worker" AppStderr "$LogDir\worker_stderr.log"
    
    # Installation du service Beat
    Write-LogMessage "Installation du service Beat..."
    nssm install "TechniciaOCR-Beat" "celery" "-A app.celery_app beat --loglevel=info"
    nssm set "TechniciaOCR-Beat" AppDirectory "$InstallDir"
    nssm set "TechniciaOCR-Beat" DisplayName "Technicia OCR Beat"
    nssm set "TechniciaOCR-Beat" Description "Service Beat pour le système OCR Technicia"
    nssm set "TechniciaOCR-Beat" Start SERVICE_AUTO_START
    nssm set "TechniciaOCR-Beat" AppStdout "$LogDir\beat_stdout.log"
    nssm set "TechniciaOCR-Beat" AppStderr "$LogDir\beat_stderr.log"
    
    # Démarrage des services
    Write-LogMessage "Démarrage des services..."
    Start-Service -Name "TechniciaOCR-API"
    Start-Service -Name "TechniciaOCR-Worker"
    Start-Service -Name "TechniciaOCR-Beat"
}

Write-LogMessage "Installation terminée avec succès !"
Write-LogMessage "L'API est accessible à l'adresse: http://localhost:$AppPort"
Write-LogMessage "Pour plus d'informations, consultez le guide administrateur dans la documentation."
