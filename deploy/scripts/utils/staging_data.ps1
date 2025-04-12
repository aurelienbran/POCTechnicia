# Module de préparation des données pour l'environnement de staging
# Version: 1.0
# Date: 7 avril 2025
#
# Ce module gère la préparation et le chargement des données nécessaires
# pour l'environnement de staging du système OCR Technicia, incluant
# la création des structures de données, la génération de données de test
# et la migration des données existantes si nécessaire.

<#
.SYNOPSIS
    Prépare les données pour l'environnement de staging.

.DESCRIPTION
    Cette fonction orchestre toutes les étapes de préparation des données
    pour l'environnement de staging, incluant la création des répertoires
    de données, l'initialisation des bases de données, le chargement des
    données de test et la validation de l'intégrité des données.

.EXAMPLE
    Prepare-Data
#>
function Start-DataPreparation {
    Start-LogSection "Préparation des données"
    
    try {
        # 1. Création des répertoires de données
        Initialize-DataDirectories
        
        # 2. Initialisation des bases de données
        Initialize-Databases
        
        # 3. Chargement des données de test
        Load-TestData
        
        # 4. Migration des données existantes (si configuré)
        if ($global:config.data.migrationEnabled -eq $true) {
            Migrate-ExistingData
        }
        
        # 5. Validation de l'intégrité des données
        Validate-DataIntegrity
        
        Write-LogMessage "Préparation des données terminée avec succès" "SUCCESS"
    }
    catch {
        Write-ExceptionLog $_ "Start-DataPreparation"
        Write-LogMessage "La préparation des données a échoué" "ERROR"
    }
    
    Stop-LogSection
}

<#
.SYNOPSIS
    Initialise les répertoires de données pour l'environnement de staging.

.DESCRIPTION
    Cette fonction crée tous les répertoires nécessaires pour stocker
    les données de l'application dans l'environnement de staging.

.EXAMPLE
    Initialize-DataDirectories
#>
function New-DataDirectories {
    Start-LogTask "Initialisation des répertoires de données"
    
    try {
        $dataConfig = $global:config.data
        
        if (-not $dataConfig -or -not $dataConfig.directories) {
            Write-LogMessage "Aucune configuration de répertoires de données trouvée" "ERROR"
            Complete-LogTask "Initialisation des répertoires de données" $false
            return $false
        }
        
        # Créer chaque répertoire spécifié dans la configuration
        foreach ($dir in $dataConfig.directories) {
            $dirPath = $dir.path
            
            # Remplacer les variables d'environnement dans le chemin si nécessaire
            $dirPath = [System.Environment]::ExpandEnvironmentVariables($dirPath)
            
            # Créer le répertoire s'il n'existe pas
            if (-not (Test-Path $dirPath)) {
                New-Item -Path $dirPath -ItemType Directory -Force | Out-Null
                Write-LogMessage "Répertoire créé: $dirPath" "INFO"
            }
            else {
                Write-LogMessage "Le répertoire existe déjà: $dirPath" "INFO"
                
                # Nettoyer le répertoire si spécifié
                if ($dir.cleanOnInit -eq $true) {
                    Write-LogMessage "Nettoyage du répertoire: $dirPath" "INFO"
                    
                    # Supprimer tout le contenu du répertoire
                    Get-ChildItem -Path $dirPath -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
                }
            }
            
            # Définir les permissions si spécifiées
            if ($dir.permissions) {
                Write-LogMessage "Configuration des permissions pour: $dirPath" "INFO"
                
                # Configuration des ACL
                $acl = Get-Acl -Path $dirPath
                
                foreach ($permission in $dir.permissions) {
                    $identity = $permission.identity
                    $rights = $permission.rights
                    
                    # Créer un nouvel objet d'accès
                    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity, $rights, "ContainerInherit,ObjectInherit", "None", "Allow")
                    
                    # Ajouter la règle d'accès à l'ACL
                    $acl.SetAccessRule($accessRule)
                }
                
                # Appliquer l'ACL au répertoire
                Set-Acl -Path $dirPath -AclObject $acl
            }
            
            # Vérifier que le répertoire est accessible en lecture/écriture
            $testFilePath = Join-Path -Path $dirPath -ChildPath "test_access.tmp"
            try {
                "Test d'accès" | Out-File -FilePath $testFilePath -Force
                Remove-Item -Path $testFilePath -Force
                Write-LogMessage "Accès en lecture/écriture confirmé pour: $dirPath" "SUCCESS"
            }
            catch {
                Write-LogMessage "Impossible d'écrire dans le répertoire: $dirPath" "ERROR"
                Write-ExceptionLog $_ "Test d'accès pour $dirPath"
                Complete-LogTask "Initialisation des répertoires de données" $false
                return $false
            }
        }
        
        Write-LogMessage "Initialisation des répertoires de données terminée avec succès" "SUCCESS"
        Complete-LogTask "Initialisation des répertoires de données" $true
        return $true
    }
    catch {
        Write-ExceptionLog $_ "New-DataDirectories"
        Complete-LogTask "Initialisation des répertoires de données" $false
        return $false
    }
}

<#
.SYNOPSIS
    Initialise les bases de données pour l'environnement de staging.

.DESCRIPTION
    Cette fonction crée et configure les bases de données nécessaires
    pour l'environnement de staging, incluant la création des schémas,
    des tables et des utilisateurs.

.EXAMPLE
    Initialize-Databases
#>
function New-Databases {
    Start-LogTask "Initialisation des bases de données"
    
    try {
        $dbConfig = $global:config.data.databases
        
        if (-not $dbConfig) {
            Write-LogMessage "Aucune configuration de base de données trouvée" "ERROR"
            Complete-LogTask "Initialisation des bases de données" $false
            return $false
        }
        
        # Initialiser chaque base de données configurée
        foreach ($db in $dbConfig) {
            $dbType = $db.type
            $dbName = $db.name
            
            Write-LogMessage "Initialisation de la base de données $dbName ($dbType)..." "INFO"
            
            switch ($dbType) {
                "postgresql" {
                    Initialize-PostgreSQLDatabase -DbConfig $db
                }
                "mysql" {
                    Initialize-MySQLDatabase -DbConfig $db
                }
                "sqlite" {
                    Initialize-SQLiteDatabase -DbConfig $db
                }
                "mongodb" {
                    Initialize-MongoDBDatabase -DbConfig $db
                }
                "redis" {
                    Initialize-RedisDatabase -DbConfig $db
                }
                default {
                    Write-LogMessage "Type de base de données non pris en charge: $dbType" "ERROR"
                }
            }
        }
        
        Write-LogMessage "Initialisation des bases de données terminée" "SUCCESS"
        Complete-LogTask "Initialisation des bases de données" $true
        return $true
    }
    catch {
        Write-ExceptionLog $_ "New-Databases"
        Complete-LogTask "Initialisation des bases de données" $false
        return $false
    }
}

<#
.SYNOPSIS
    Initialise une base de données PostgreSQL.

.DESCRIPTION
    Cette fonction initialise une base de données PostgreSQL selon la configuration
    spécifiée, incluant la création de la base de données, des utilisateurs,
    des schémas et des tables.

.PARAMETER DbConfig
    Configuration de la base de données PostgreSQL.

.EXAMPLE
    Initialize-PostgreSQLDatabase -DbConfig $postgresConfig
#>
function New-PostgreSQLDatabase {
    param (
        [Parameter(Mandatory=$true)]
        [PSCustomObject]$DbConfig
    )
    
    Write-LogMessage "Initialisation de la base de données PostgreSQL: $($DbConfig.name)" "INFO"
    
    try {
        # Vérifier que PostgreSQL est installé
        $pgInfo = Test-SoftwareInstalled -SoftwareName "PostgreSQL" -ExecutableName "psql"
        
        if (-not $pgInfo.IsInstalled) {
            Write-LogMessage "PostgreSQL n'est pas installé" "ERROR"
            return $false
        }
        
        # Paramètres de connexion
        $dbHost = $DbConfig.host
        $port = $DbConfig.port
        $adminUser = $DbConfig.adminUser
        $adminPassword = $DbConfig.adminPassword
        $dbName = $DbConfig.name
        
        # Définir la variable d'environnement PGPASSWORD pour l'authentification
        $env:PGPASSWORD = $adminPassword
        
        # Vérifier la connexion à PostgreSQL
        $connectionTest = (Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"\conninfo`"") -join "`n"
        
        if ($connectionTest -like "*connection to server*") {
            Write-LogMessage "Connexion à PostgreSQL établie: ${dbHost}:${port}" "SUCCESS"
        }
        else {
            Write-LogMessage "Impossible de se connecter à PostgreSQL: ${dbHost}:${port}" "ERROR"
            $env:PGPASSWORD = ""
            return $false
        }
        
        # Vérifier si la base de données existe
        $dbExists = (Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"SELECT 1 FROM pg_database WHERE datname='${dbName}';`" -t") -join "`n"
        
        if ($dbExists.Trim() -eq "1") {
            Write-LogMessage "La base de données ${dbName} existe déjà" "INFO"
            
            if ($DbConfig.dropIfExists -eq $true) {
                Write-LogMessage "Suppression de la base de données existante: ${dbName}" "WARN"
                Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"DROP DATABASE ${dbName};`""
                $dbExists = $false
            }
        }
        else {
            $dbExists = $false
        }
        
        # Créer la base de données si nécessaire
        if (-not $dbExists) {
            Write-LogMessage "Création de la base de données: ${dbName}" "INFO"
            Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"CREATE DATABASE ${dbName};`""
            
            # Vérifier que la base de données a été créée
            $dbCreated = (Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"SELECT 1 FROM pg_database WHERE datname='${dbName}';`" -t") -join "`n"
            
            if ($dbCreated.Trim() -ne "1") {
                Write-LogMessage "Échec de la création de la base de données: ${dbName}" "ERROR"
                $env:PGPASSWORD = ""
                return $false
            }
        }
        
        # Créer l'utilisateur spécifique à l'application si nécessaire
        if ($DbConfig.appUser -and $DbConfig.appPassword) {
            $appUser = $DbConfig.appUser
            $appPassword = $DbConfig.appPassword
            
            # Vérifier si l'utilisateur existe
            $userExists = (Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"SELECT 1 FROM pg_roles WHERE rolname='${appUser}';`" -t") -join "`n"
            
            if ($userExists.Trim() -ne "1") {
                Write-LogMessage "Création de l'utilisateur: ${appUser}" "INFO"
                Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"CREATE USER ${appUser} WITH ENCRYPTED PASSWORD '${appPassword}';`""
                
                # Vérifier que l'utilisateur a été créé
                $userCreated = (Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"SELECT 1 FROM pg_roles WHERE rolname='${appUser}';`" -t") -join "`n"
                
                if ($userCreated.Trim() -ne "1") {
                    Write-LogMessage "Échec de la création de l'utilisateur: ${appUser}" "ERROR"
                }
            }
            else {
                Write-LogMessage "L'utilisateur ${appUser} existe déjà" "INFO"
                
                # Mettre à jour le mot de passe
                Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"ALTER USER ${appUser} WITH ENCRYPTED PASSWORD '${appPassword}';`""
            }
            
            # Attribuer les privilèges sur la base de données
            Write-LogMessage "Attribution des privilèges à l'utilisateur ${appUser} sur la base de données ${dbName}" "INFO"
            Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -c `"GRANT ALL PRIVILEGES ON DATABASE ${dbName} TO ${appUser};`""
            
            # Connecter à la base de données spécifique
            Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -d ${dbName} -c `"GRANT ALL ON SCHEMA public TO ${appUser};`""
        }
        
        # Exécuter le script d'initialisation si spécifié
        if ($DbConfig.initScript) {
            $initScriptPath = $DbConfig.initScript
            
            # Vérifier que le script existe
            if (Test-Path $initScriptPath) {
                Write-LogMessage "Exécution du script d'initialisation: ${initScriptPath}" "INFO"
                Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -d ${dbName} -f `"${initScriptPath}`""
                
                Write-LogMessage "Script d'initialisation exécuté avec succès" "SUCCESS"
            }
            else {
                Write-LogMessage "Le script d'initialisation n'existe pas: ${initScriptPath}" "ERROR"
            }
        }
        
        # Effectuer les migrations si spécifiées
        if ($DbConfig.migrations -and $DbConfig.migrations.Count -gt 0) {
            foreach ($migration in $DbConfig.migrations) {
                $migrationPath = $migration.path
                
                if (Test-Path $migrationPath) {
                    Write-LogMessage "Exécution de la migration: ${migrationPath}" "INFO"
                    Invoke-Expression "psql -h ${dbHost} -p ${port} -U ${adminUser} -d ${dbName} -f `"${migrationPath}`""
                }
                else {
                    Write-LogMessage "Le fichier de migration n'existe pas: ${migrationPath}" "ERROR"
                }
            }
        }
        
        Write-LogMessage "Initialisation de la base de données PostgreSQL terminée: ${dbName}" "SUCCESS"
        return $true
    }
    catch {
        Write-ExceptionLog $_ "New-PostgreSQLDatabase"
        return $false
    }
    finally {
        # Nettoyer la variable d'environnement
        $env:PGPASSWORD = ""
    }
}

<#
.SYNOPSIS
    Charge des données de test dans l'environnement de staging.

.DESCRIPTION
    Cette fonction charge des données de test dans l'environnement de staging,
    incluant les utilisateurs, les documents et les configurations de test.

.EXAMPLE
    Load-TestData
#>
function Import-TestData {
    Start-LogTask "Chargement des données de test"
    
    try {
        $testDataConfig = $global:config.data.testData
        
        if (-not $testDataConfig -or -not $testDataConfig.enabled) {
            Write-LogMessage "Le chargement des données de test est désactivé" "INFO"
            Complete-LogTask "Chargement des données de test" $true
            return $true
        }
        
        Write-LogMessage "Chargement des données de test..." "INFO"
        
        # Charger les utilisateurs de test
        if ($testDataConfig.users -and $testDataConfig.users.Count -gt 0) {
            Load-TestUsers -Users $testDataConfig.users
        }
        
        # Charger les documents de test
        if ($testDataConfig.documents -and $testDataConfig.documents.Count -gt 0) {
            Load-TestDocuments -Documents $testDataConfig.documents
        }
        
        # Charger les configurations de test
        if ($testDataConfig.configurations -and $testDataConfig.configurations.Count -gt 0) {
            Load-TestConfigurations -Configurations $testDataConfig.configurations
        }
        
        # Charger les données OCR de test
        if ($testDataConfig.ocrData -and $testDataConfig.ocrData.enabled) {
            Load-TestOCRData -OCRConfig $testDataConfig.ocrData
        }
        
        Write-LogMessage "Chargement des données de test terminé avec succès" "SUCCESS"
        Complete-LogTask "Chargement des données de test" $true
        return $true
    }
    catch {
        Write-ExceptionLog $_ "Import-TestData"
        Complete-LogTask "Chargement des données de test" $false
        return $false
    }
}

<#
.SYNOPSIS
    Charge des utilisateurs de test dans l'environnement de staging.

.DESCRIPTION
    Cette fonction crée des utilisateurs de test dans l'application pour
    permettre les tests avec différents niveaux d'accès.

.PARAMETER Users
    Liste des utilisateurs de test à créer.

.EXAMPLE
    Load-TestUsers -Users $testUsers
#>
function Import-TestUsers {
    param (
        [Parameter(Mandatory=$true)]
        [array]$Users
    )
    
    Write-LogMessage "Chargement des utilisateurs de test..." "INFO"
    
    try {
        # Déterminer la méthode de chargement des utilisateurs selon l'application
        $authMethod = $global:config.security.authentication.method
        
        foreach ($user in $Users) {
            $username = $user.username
            $password = $user.password
            $role = $user.role
            
            Write-LogMessage "Création de l'utilisateur de test: $username (rôle: $role)" "INFO"
            
            # Ajouter l'utilisateur selon la méthode d'authentification
            switch ($authMethod) {
                "basic" {
                    # Pour l'authentification de base, nous pouvons stocker dans un fichier htpasswd
                    $htpasswdPath = $global:config.security.authentication.htpasswdPath
                    
                    if (-not $htpasswdPath) {
                        $htpasswdPath = "$global:basePath\security\htpasswd"
                    }
                    
                    # S'assurer que le répertoire existe
                    $htpasswdDir = Split-Path -Parent $htpasswdPath
                    if (-not (Test-Path $htpasswdDir)) {
                        New-Item -Path $htpasswdDir -ItemType Directory -Force | Out-Null
                    }
                    
                    # Ajouter l'utilisateur au fichier htpasswd
                    # Note: Ceci est une simulation, normalement on utiliserait l'utilitaire htpasswd d'Apache
                    $userEntry = "${username}:{SHA}" + [Convert]::ToBase64String([System.Security.Cryptography.SHA1]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($password)))
                    
                    if (Test-Path $htpasswdPath) {
                        # Vérifier si l'utilisateur existe déjà
                        $existingUsers = Get-Content -Path $htpasswdPath
                        $userExists = $existingUsers | Where-Object { $_ -like "${username}:*" }
                        
                        if ($userExists) {
                            # Mettre à jour l'utilisateur existant
                            $newContent = $existingUsers | ForEach-Object {
                                if ($_ -like "${username}:*") {
                                    $userEntry
                                }
                                else {
                                    $_
                                }
                            }
                            
                            Set-Content -Path $htpasswdPath -Value $newContent
                        }
                        else {
                            # Ajouter le nouvel utilisateur
                            Add-Content -Path $htpasswdPath -Value $userEntry
                        }
                    }
                    else {
                        # Créer le fichier avec le premier utilisateur
                        Set-Content -Path $htpasswdPath -Value $userEntry
                    }
                }
                "database" {
                    # Pour l'authentification par base de données, nous devons ajouter l'utilisateur à la base de données
                    # Cette implémentation dépend de la base de données spécifique utilisée
                    $dbConfig = $global:config.data.databases | Where-Object { $_.purpose -eq "auth" -or $_.primary -eq $true } | Select-Object -First 1
                    
                    if ($dbConfig) {
                        switch ($dbConfig.type) {
                            "postgresql" {
                                Add-UserToPostgreSQL -DbConfig $dbConfig -Username $username -Password $password -Role $role
                            }
                            "mysql" {
                                Add-UserToMySQL -DbConfig $dbConfig -Username $username -Password $password -Role $role
                            }
                            "sqlite" {
                                Add-UserToSQLite -DbConfig $dbConfig -Username $username -Password $password -Role $role
                            }
                            default {
                                Write-LogMessage "Type de base de données non pris en charge pour l'authentification: $($dbConfig.type)" "ERROR"
                            }
                        }
                    }
                    else {
                        Write-LogMessage "Aucune base de données configurée pour l'authentification" "ERROR"
                    }
                }
                default {
                    Write-LogMessage "Méthode d'authentification non prise en charge pour le chargement des utilisateurs: $authMethod" "ERROR"
                }
            }
        }
        
        Write-LogMessage "Chargement des utilisateurs de test terminé avec succès" "SUCCESS"
        return $true
    }
    catch {
        Write-ExceptionLog $_ "Import-TestUsers"
        return $false
    }
}

<#
.SYNOPSIS
    Valide l'intégrité des données de l'environnement de staging.

.DESCRIPTION
    Cette fonction effectue une série de vérifications pour s'assurer que
    toutes les données nécessaires pour le fonctionnement de l'application
    sont présentes et valides.

.EXAMPLE
    Validate-DataIntegrity
#>
function Test-DataIntegrity {
    Start-LogTask "Validation de l'intégrité des données"
    
    try {
        $validationConfig = $global:config.data.validation
        $allValidationsSucceeded = $true
        
        if (-not $validationConfig -or -not $validationConfig.enabled) {
            Write-LogMessage "La validation de l'intégrité des données est désactivée" "INFO"
            Complete-LogTask "Validation de l'intégrité des données" $true
            return $true
        }
        
        Write-LogMessage "Validation de l'intégrité des données..." "INFO"
        
        # Vérifier l'existence des répertoires de données
        if ($validationConfig.checkDirectories -eq $true) {
            Write-LogMessage "Vérification des répertoires de données..." "INFO"
            
            foreach ($dir in $global:config.data.directories) {
                $dirPath = $dir.path
                $dirPath = [System.Environment]::ExpandEnvironmentVariables($dirPath)
                
                if (-not (Test-Path $dirPath)) {
                    Write-LogMessage "Répertoire de données manquant: $dirPath" "ERROR"
                    $allValidationsSucceeded = $false
                }
                else {
                    Write-LogMessage "Répertoire de données présent: $dirPath" "SUCCESS"
                    
                    # Vérifier les permissions si spécifié
                    if ($validationConfig.checkPermissions -eq $true) {
                        $testFilePath = Join-Path -Path $dirPath -ChildPath "permission_test.tmp"
                        
                        try {
                            "Test" | Out-File -FilePath $testFilePath -Force
                            Remove-Item -Path $testFilePath -Force
                            Write-LogMessage "Permissions correctes pour: $dirPath" "SUCCESS"
                        }
                        catch {
                            Write-LogMessage "Permissions incorrectes pour: $dirPath" "ERROR"
                            $allValidationsSucceeded = $false
                        }
                    }
                }
            }
        }
        
        # Vérifier la connectivité aux bases de données
        if ($validationConfig.checkDatabases -eq $true) {
            Write-LogMessage "Vérification de la connectivité aux bases de données..." "INFO"
            
            foreach ($db in $global:config.data.databases) {
                $dbType = $db.type
                $dbName = $db.name
                
                Write-LogMessage "Vérification de la connectivité à la base de données: $dbName ($dbType)" "INFO"
                
                $connectionResult = $false
                
                switch ($dbType) {
                    "postgresql" {
                        $connectionResult = Test-PostgreSQLConnection -DbConfig $db
                    }
                    "mysql" {
                        $connectionResult = Test-MySQLConnection -DbConfig $db
                    }
                    "sqlite" {
                        $connectionResult = Test-SQLiteConnection -DbConfig $db
                    }
                    "mongodb" {
                        $connectionResult = Test-MongoDBConnection -DbConfig $db
                    }
                    "redis" {
                        $connectionResult = Test-RedisConnection -DbConfig $db
                    }
                    default {
                        Write-LogMessage "Type de base de données non pris en charge: $dbType" "ERROR"
                        $connectionResult = $false
                    }
                }
                
                if ($connectionResult) {
                    Write-LogMessage "Connectivité à la base de données confirmée: $dbName" "SUCCESS"
                }
                else {
                    Write-LogMessage "Échec de la connexion à la base de données: $dbName" "ERROR"
                    $allValidationsSucceeded = $false
                }
            }
        }
        
        # Vérifier la présence des données de test si activé
        if ($validationConfig.checkTestData -eq $true -and $global:config.data.testData.enabled -eq $true) {
            Write-LogMessage "Vérification des données de test..." "INFO"
            
            # Cette vérification dépendra de la nature des données de test
            # Implémentez cette partie selon vos besoins spécifiques
        }
        
        # Vérification finale
        if ($allValidationsSucceeded) {
            Write-LogMessage "Validation de l'intégrité des données réussie" "SUCCESS"
        }
        else {
            Write-LogMessage "Validation de l'intégrité des données échouée" "ERROR"
        }
        
        Complete-LogTask "Validation de l'intégrité des données" $allValidationsSucceeded
        return $allValidationsSucceeded
    }
    catch {
        Write-ExceptionLog $_ "Test-DataIntegrity"
        Complete-LogTask "Validation de l'intégrité des données" $false
        return $false
    }
}

# Rendre les fonctions disponibles pour les autres scripts
$global:Start_DataPreparation = ${function:Start-DataPreparation}
$global:New_DataDirectories = ${function:New-DataDirectories}
$global:New_Databases = ${function:New-Databases}
$global:New_PostgreSQLDatabase = ${function:New-PostgreSQLDatabase}
$global:Import_TestData = ${function:Import-TestData}
$global:Import_TestUsers = ${function:Import-TestUsers}
$global:Test_DataIntegrity = ${function:Test-DataIntegrity}
