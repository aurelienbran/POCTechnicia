# ==========================================================================
# staging_database.ps1
# Version: 1.1
# Date: 7 avril 2025
# 
# Description: 
#   Module pour la gestion de la base de données PostgreSQL de l'environnement
#   de staging Technicia OCR, incluant l'initialisation et les migrations.
#
# Fonctions:
#   - Test-DatabaseConnection: Vérifie la connectivité à la base de données
#   - New-Database: Crée une nouvelle base de données
#   - Initialize-Database: Initialise la base de données PostgreSQL
#   - Invoke-DatabaseMigrations: Applique les scripts de migration SQL dans l'ordre
#   - Import-TestData: Importe des données de test si nécessaire
#   - Invoke-DatabasePreparation: Prépare la base de données pour l'utilisation
#   - Backup-Database: Sauvegarde la base de données
# ==========================================================================

# Importer le module de journalisation
. "$PSScriptRoot\staging_logger.ps1"

# Fonction pour tester la connexion à la base de données
function Test-DatabaseConnection {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Server,
        
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [Parameter(Mandatory=$true)]
        [string]$Database,
        
        [Parameter(Mandatory=$true)]
        [string]$Username,
        
        [Parameter(Mandatory=$true)]
        [System.Security.SecureString]$Password
    )
    
    try {
        Write-LogMessage "Test de connexion à la base de données $Database sur $Server port $Port..." "INFO"
        
        # Convertir le SecureString en plaintext pour psql
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
        $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        
        # Stocker temporairement le mot de passe dans la variable d'environnement PGPASSWORD
        $env:PGPASSWORD = $PlainPassword
        
        # Exécuter une commande simple pour vérifier la connexion
        $testCmd = "psql -h $Server -p $Port -U $Username -d $Database -t -c `"SELECT 1 AS connection_test`""
        $testResult = Invoke-Expression $testCmd
        
        if ($testResult -match "1") {
            Write-LogMessage "Connexion réussie à la base de données $Database." "SUCCESS"
            $env:PGPASSWORD = $null
            return $true
        } else {
            Write-LogMessage "Échec de la connexion à la base de données $Database." "ERROR"
            $env:PGPASSWORD = $null
            return $false
        }
    }
    catch {
        Write-LogMessage "Erreur lors du test de connexion à la base de données: $_" "ERROR"
        $env:PGPASSWORD = $null
        return $false
    }
}

# Fonction pour créer une nouvelle base de données
function New-Database {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Server,
        
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [Parameter(Mandatory=$true)]
        [string]$Database,
        
        [Parameter(Mandatory=$true)]
        [string]$Username,
        
        [Parameter(Mandatory=$true)]
        [System.Security.SecureString]$Password
    )
    
    try {
        Write-LogMessage "Création de la base de données $Database sur $Server port $Port..." "INFO"
        
        # Convertir le SecureString en plaintext pour psql
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
        $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        
        # Stocker temporairement le mot de passe dans la variable d'environnement PGPASSWORD
        $env:PGPASSWORD = $PlainPassword
        
        # Exécuter la commande pour créer la base de données
        $createCmd = "psql -h $Server -p $Port -U $Username -d postgres -c `"CREATE DATABASE $Database`""
        Invoke-Expression $createCmd | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-LogMessage "Base de données $Database créée avec succès." "SUCCESS"
            $env:PGPASSWORD = $null
            return $true
        } else {
            Write-LogMessage "Échec de la création de la base de données $Database." "ERROR"
            $env:PGPASSWORD = $null
            return $false
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la création de la base de données: $_" "ERROR"
        $env:PGPASSWORD = $null
        return $false
    }
}

# Fonction pour initialiser la base de données
function Initialize-Database {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Server,
        
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [Parameter(Mandatory=$true)]
        [string]$Database,
        
        [Parameter(Mandatory=$true)]
        [string]$Username,
        
        [Parameter(Mandatory=$true)]
        [System.Security.SecureString]$Password,
        
        [Parameter(Mandatory=$true)]
        [string]$InitScriptPath
    )
    
    try {
        Write-LogMessage "Initialisation de la base de données $Database..." "INFO"
        
        # Vérifier l'existence du script d'initialisation
        if (-not (Test-Path $InitScriptPath)) {
            Write-LogMessage "Le script d'initialisation $InitScriptPath n'existe pas." "ERROR"
            return $false
        }
        
        # Convertir le SecureString en plaintext pour psql
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
        $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        
        # Stocker temporairement le mot de passe dans la variable d'environnement PGPASSWORD
        $env:PGPASSWORD = $PlainPassword
        
        # Exécuter le script d'initialisation
        $initCmd = "psql -h $Server -p $Port -U $Username -d $Database -f `"$InitScriptPath`""
        Invoke-Expression $initCmd | Out-Null
        
        Write-LogMessage "Base de données initialisée avec succès." "SUCCESS"
        $env:PGPASSWORD = $null
        return $true
    }
    catch {
        Write-LogMessage "Erreur lors de l'initialisation de la base de données: $_" "ERROR"
        $env:PGPASSWORD = $null
        return $false
    }
}

# Fonction pour appliquer les migrations
function Invoke-DatabaseMigrations {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Server,
        
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [Parameter(Mandatory=$true)]
        [string]$Database,
        
        [Parameter(Mandatory=$true)]
        [string]$Username,
        
        [Parameter(Mandatory=$true)]
        [System.Security.SecureString]$Password,
        
        [Parameter(Mandatory=$true)]
        [string]$MigrationsPath
    )
    
    try {
        Write-LogMessage "Application des migrations à la base de données $Database..." "INFO"
        
        # Vérifier l'existence du dossier de migrations
        if (-not (Test-Path $MigrationsPath)) {
            Write-LogMessage "Le dossier de migrations $MigrationsPath n'existe pas." "ERROR"
            return $false
        }
        
        # Convertir le SecureString en plaintext pour psql
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
        $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        
        # Stocker temporairement le mot de passe dans la variable d'environnement PGPASSWORD
        $env:PGPASSWORD = $PlainPassword
        
        # Créer la table de suivi des migrations si elle n'existe pas déjà
        $createMigrationsTableCmd = "psql -h $Server -p $Port -U $Username -d $Database -c `"
            CREATE TABLE IF NOT EXISTS public.applied_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL,
                script_hash VARCHAR(64) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        `""
        Invoke-Expression $createMigrationsTableCmd | Out-Null
        
        # Récupérer la liste des fichiers de migration triés par nom
        $migrationFiles = Get-ChildItem -Path $MigrationsPath -Filter "*.sql" | Sort-Object Name
        
        $migrationsApplied = 0
        
        foreach ($migrationFile in $migrationFiles) {
            $scriptName = $migrationFile.Name
            $scriptPath = $migrationFile.FullName
            $scriptContent = Get-Content -Path $scriptPath -Raw
            $scriptHash = (Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($scriptContent)))).Hash
            
            # Vérifier si cette migration a déjà été appliquée
            $checkMigrationCmd = "psql -h $Server -p $Port -U $Username -d $Database -t -c `"SELECT script_hash FROM public.applied_migrations WHERE migration_name = '$scriptName'`""
            $existingHash = (Invoke-Expression $checkMigrationCmd).Trim()
            
            if ($existingHash -ne "") {
                # Migration déjà appliquée, vérifier le hash
                if ($existingHash -eq $scriptHash) {
                    Write-LogMessage "Migration $scriptName déjà appliquée (inchangée)." "INFO"
                } else {
                    Write-LogMessage "Le fichier de migration $scriptName a été modifié depuis son application. Le script ne sera pas réappliqué." "WARN"
                }
                continue
            }
            
            # Appliquer la migration
            Write-LogMessage "Application de la migration: $scriptName" "INFO"
            $applyMigrationCmd = "psql -h $Server -p $Port -U $Username -d $Database -f `"$scriptPath`""
            Invoke-Expression $applyMigrationCmd | Out-Null
            
            # Enregistrer la migration comme appliquée
            $recordMigrationCmd = "psql -h $Server -p $Port -U $Username -d $Database -c `"
                INSERT INTO public.applied_migrations (migration_name, script_hash) 
                VALUES ('$scriptName', '$scriptHash')
            `""
            Invoke-Expression $recordMigrationCmd | Out-Null
            
            Write-LogMessage "Migration $scriptName appliquée avec succès." "SUCCESS"
            $migrationsApplied++
        }
        
        Write-LogMessage "$migrationsApplied migrations appliquées." "SUCCESS"
        $env:PGPASSWORD = $null
        return $true
    }
    catch {
        Write-LogMessage "Erreur lors de l'application des migrations: $_" "ERROR"
        $env:PGPASSWORD = $null
        return $false
    }
}

# Fonction pour importer des données de test
function Import-TestData {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Server,
        
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [Parameter(Mandatory=$true)]
        [string]$Database,
        
        [Parameter(Mandatory=$true)]
        [string]$Username,
        
        [Parameter(Mandatory=$true)]
        [System.Security.SecureString]$Password,
        
        [Parameter(Mandatory=$true)]
        [string]$TestDataPath
    )
    
    try {
        Write-LogMessage "Importation des données de test dans la base de données $Database..." "INFO"
        
        # Vérifier l'existence du fichier de données de test
        if (-not (Test-Path $TestDataPath)) {
            Write-LogMessage "Le fichier de données de test $TestDataPath n'existe pas." "ERROR"
            return $false
        }
        
        # Convertir le SecureString en plaintext pour psql
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
        $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        
        # Stocker temporairement le mot de passe dans la variable d'environnement PGPASSWORD
        $env:PGPASSWORD = $PlainPassword
        
        # Exécuter le script de données de test
        $importCmd = "psql -h $Server -p $Port -U $Username -d $Database -f `"$TestDataPath`""
        Invoke-Expression $importCmd | Out-Null
        
        Write-LogMessage "Données de test importées avec succès." "SUCCESS"
        $env:PGPASSWORD = $null
        return $true
    }
    catch {
        Write-LogMessage "Erreur lors de l'importation des données de test: $_" "ERROR"
        $env:PGPASSWORD = $null
        return $false
    }
}

# Fonction principale pour la préparation complète de la base de données
function Invoke-DatabasePreparation {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [PSCustomObject]$DatabaseConfig,
        
        [Parameter(Mandatory=$true)]
        [string]$SqlScriptsPath,
        
        [Parameter(Mandatory=$false)]
        [switch]$IncludeTestData = $false
    )
    
    try {
        Write-LogMessage "=== PRÉPARATION DE LA BASE DE DONNÉES ===" "INFO"
        
        $server = $DatabaseConfig.server
        $port = $DatabaseConfig.port
        $database = $DatabaseConfig.database
        $username = $DatabaseConfig.username
        
        # Convertir le mot de passe en SecureString
        $securePassword = ConvertTo-SecureString $DatabaseConfig.password -AsPlainText -Force
        
        Write-LogMessage "Préparation de la base de données $database sur $server port $port..." "INFO"
        
        # Vérifier la connexion au serveur PostgreSQL
        if (-not (Test-DatabaseConnection -Server $server -Port $port -Database "postgres" -Username $username -Password $securePassword)) {
            Write-LogMessage "Impossible de se connecter au serveur PostgreSQL. Vérifiez les paramètres de connexion." "ERROR"
            return $false
        }
        
        # Créer la base de données si elle n'existe pas
        if (-not (New-Database -Server $server -Port $port -Database $database -Username $username -Password $securePassword)) {
            Write-LogMessage "Échec de la création de la base de données." "ERROR"
            return $false
        }
        
        # Initialiser la base de données
        $initScriptPath = Join-Path -Path $SqlScriptsPath -ChildPath "init_db.sql"
        if (-not (Initialize-Database -Server $server -Port $port -Database $database -Username $username -Password $securePassword -InitScriptPath $initScriptPath)) {
            Write-LogMessage "Échec de l'initialisation de la base de données." "ERROR"
            return $false
        }
        
        # Appliquer les migrations
        $migrationsPath = Join-Path -Path $SqlScriptsPath -ChildPath "migrations"
        if (-not (Invoke-DatabaseMigrations -Server $server -Port $port -Database $database -Username $username -Password $securePassword -MigrationsPath $migrationsPath)) {
            Write-LogMessage "Échec de l'application des migrations." "ERROR"
            return $false
        }
        
        # Importer les données de test si demandé
        if ($IncludeTestData) {
            $testDataPath = Join-Path -Path $SqlScriptsPath -ChildPath "test_data.sql"
            if (-not (Import-TestData -Server $server -Port $port -Database $database -Username $username -Password $securePassword -TestDataPath $testDataPath)) {
                Write-LogMessage "Échec de l'importation des données de test." "ERROR"
                return $false
            }
        }
        
        Write-LogMessage "Préparation de la base de données terminée avec succès." "SUCCESS"
        return $true
    }
    catch {
        Write-LogMessage "Erreur lors de la préparation de la base de données: $_" "ERROR"
        return $false
    }
}

# Fonction pour sauvegarder la base de données
function Backup-Database {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Server,
        
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [Parameter(Mandatory=$true)]
        [string]$Database,
        
        [Parameter(Mandatory=$true)]
        [string]$Username,
        
        [Parameter(Mandatory=$true)]
        [System.Security.SecureString]$Password,
        
        [Parameter(Mandatory=$false)]
        [string]$BackupDir = "$PSScriptRoot\..\..\backups",
        
        [Parameter(Mandatory=$false)]
        [string]$BackupPrefix = "technicia_db_backup"
    )
    
    try {
        # Créer le répertoire de sauvegarde s'il n'existe pas
        if (-not (Test-Path $BackupDir)) {
            New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
            Write-LogMessage "Répertoire de sauvegarde créé: $BackupDir" "INFO"
        }
        
        # Générer un nom de fichier basé sur la date et l'heure
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupFile = Join-Path $BackupDir "$BackupPrefix`_$timestamp.sql"
        
        Write-LogMessage "Sauvegarde de la base de données $Database vers $backupFile..." "INFO"
        
        # Convertir le SecureString en plaintext pour psql
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
        $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        
        # Stocker temporairement le mot de passe dans la variable d'environnement PGPASSWORD
        $env:PGPASSWORD = $PlainPassword
        
        # Exécuter pg_dump pour la sauvegarde
        $backupCmd = "pg_dump -h $Server -p $Port -U $Username -F p -f `"$backupFile`" $Database"
        Invoke-Expression $backupCmd | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            # Compresser le fichier de sauvegarde
            Write-LogMessage "Compression du fichier de sauvegarde..." "INFO"
            
            $compressedFile = "$backupFile.zip"
            Compress-Archive -Path $backupFile -DestinationPath $compressedFile -Force
            
            # Supprimer le fichier SQL original
            Remove-Item -Path $backupFile -Force
            
            Write-LogMessage "Sauvegarde terminée avec succès: $compressedFile" "SUCCESS"
            $env:PGPASSWORD = $null
            return $compressedFile
        } else {
            Write-LogMessage "Erreur lors de la sauvegarde de la base de données. Code: $LASTEXITCODE" "ERROR"
            $env:PGPASSWORD = $null
            return $false
        }
    }
    catch {
        Write-LogMessage "Erreur lors de la sauvegarde de la base de données: $_" "ERROR"
        $env:PGPASSWORD = $null
        return $false
    }
}

# Rendre les fonctions disponibles pour les autres scripts
# Cette approche est plus compatible avec le dot-sourcing
$global:Test_DatabaseConnection = ${function:Test-DatabaseConnection}
$global:New_Database = ${function:New-Database}
$global:Initialize_Database = ${function:Initialize-Database}
$global:Invoke_DatabaseMigrations = ${function:Invoke-DatabaseMigrations}
$global:Import_TestData = ${function:Import-TestData}
$global:Invoke_DatabasePreparation = ${function:Invoke-DatabasePreparation}
$global:Backup_Database = ${function:Backup-Database}
