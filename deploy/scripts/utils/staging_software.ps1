# Module d'installation des logiciels pour l'environnement de staging
# Version: 1.0
# Date: 7 avril 2025
#
# Ce module gère l'installation et la configuration des logiciels nécessaires
# pour l'environnement de staging du système OCR Technicia.

<#
.SYNOPSIS
    Installe tous les logiciels requis pour l'environnement de staging.

.DESCRIPTION
    Cette fonction orchestre l'installation de tous les logiciels nécessaires
    au fonctionnement de l'environnement de staging du système OCR Technicia.
    Elle vérifie d'abord si le logiciel est déjà installé, puis procède à 
    l'installation si nécessaire.

.EXAMPLE
    Install-RequiredSoftware
#>
function Install-RequiredSoftware {
    Start-LogSection "Installation des logiciels requis"
    
    try {
        # Vérifier les dépendances déjà installées
        $softwareDependencies = Test-SoftwareDependencies
        
        if ($softwareDependencies) {
            Write-LogMessage "Certains logiciels requis sont déjà installés" "INFO"
        }
        
        # Installer les logiciels manquants selon la configuration
        $requiredSoftware = $global:config.software.requiredSoftware
        
        foreach ($software in $requiredSoftware) {
            $softwareInfo = Test-SoftwareInstalled -SoftwareName $software.name -MinVersion $software.minVersion -ExecutableName $software.executable
            
            if (-not $softwareInfo.IsInstalled -or 
                ($software.minVersion -and $softwareInfo.Version -and 
                 [version]$softwareInfo.Version -lt [version]$software.minVersion)) {
                
                Start-LogTask "Installation de $($software.name)"
                
                switch ($software.name) {
                    "Docker Desktop" {
                        Install-Docker -Config $software
                    }
                    "PostgreSQL" {
                        Install-PostgreSQL -Config $software
                    }
                    "Python" {
                        Install-Python -Config $software
                    }
                    "Redis" {
                        Install-Redis -Config $software
                    }
                    "Nginx" {
                        Install-Nginx -Config $software
                    }
                    "Tesseract OCR" {
                        Install-TesseractOCR -Config $software
                    }
                    "Git" {
                        Install-Git -Config $software
                    }
                    "NodeJS" {
                        Install-NodeJS -Config $software
                    }
                    "Prometheus" {
                        Install-Prometheus -Config $software
                    }
                    "Grafana" {
                        Install-Grafana -Config $software
                    }
                    default {
                        Write-LogMessage "Aucune méthode d'installation définie pour $($software.name)" "WARN"
                        Complete-LogTask "Installation de $($software.name)" $false "Méthode d'installation non définie"
                        continue
                    }
                }
                
                # Vérifier si l'installation a réussi
                $softwareInfoAfter = Test-SoftwareInstalled -SoftwareName $software.name -ExecutableName $software.executable
                
                if ($softwareInfoAfter.IsInstalled) {
                    Write-LogMessage "$($software.name) a été installé avec succès, version: $($softwareInfoAfter.Version)" "SUCCESS"
                    Complete-LogTask "Installation de $($software.name)" $true
                }
                else {
                    Write-LogMessage "L'installation de $($software.name) a échoué" "ERROR"
                    Complete-LogTask "Installation de $($software.name)" $false
                    
                    if ($software.critical -eq $true) {
                        Write-LogMessage "L'installation d'un logiciel critique a échoué. Interruption de la préparation." "ERROR"
                        Exit 1
                    }
                }
            }
            else {
                Write-LogMessage "$($software.name) est déjà installé (version: $($softwareInfo.Version))" "INFO"
            }
        }
        
        # Installation des packages Python requis
        if ($global:config.software.pythonPackages -and $global:config.software.pythonPackages.Count -gt 0) {
            Install-PythonPackages -Packages $global:config.software.pythonPackages
        }
        
        # Installation des packages Node.js requis
        if ($global:config.software.nodePackages -and $global:config.software.nodePackages.Count -gt 0) {
            Install-NodePackages -Packages $global:config.software.nodePackages
        }
        
        Write-LogMessage "Installation des logiciels terminée" "SUCCESS"
    }
    catch {
        Write-ExceptionLog $_ "Install-RequiredSoftware"
        Write-LogMessage "L'installation des logiciels a échoué" "ERROR"
        Exit 1
    }
    
    Stop-LogSection
}

<#
.SYNOPSIS
    Installe Docker Desktop.

.DESCRIPTION
    Cette fonction télécharge et installe Docker Desktop selon la configuration spécifiée.

.PARAMETER Config
    Configuration spécifique pour Docker.

.EXAMPLE
    Install-Docker -Config $dockerConfig
#>
function Install-Docker {
    param (
        [Parameter(Mandatory=$true)]
        [PSCustomObject]$Config
    )
    
    Write-LogMessage "Installation de Docker Desktop..." "INFO"
    
    try {
        $installerPath = "$env:TEMP\DockerDesktopInstaller.exe"
        $downloadUrl = $Config.downloadUrl
        
        if (-not $downloadUrl) {
            $downloadUrl = "https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe"
        }
        
        # Télécharger l'installateur
        Write-LogMessage "Téléchargement de Docker Desktop depuis $downloadUrl" "INFO"
        Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath
        
        # Exécuter l'installateur en mode silencieux
        Write-LogMessage "Exécution de l'installateur Docker Desktop" "INFO"
        $installArgs = "--quiet"
        if ($Config.installArgs) {
            $installArgs = $Config.installArgs
        }
        
        Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait
        
        # Vérifier l'installation
        $dockerPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
        if (Test-Path $dockerPath) {
            Write-LogMessage "Docker Desktop a été installé" "SUCCESS"
            
            # Démarrer Docker si spécifié
            if ($Config.startAfterInstall -eq $true) {
                Write-LogMessage "Démarrage de Docker Desktop..." "INFO"
                Start-Process -FilePath $dockerPath
                # Attendre que Docker soit prêt
                Start-Sleep -Seconds 30
            }
            
            return $true
        }
        else {
            Write-LogMessage "L'installation de Docker Desktop a échoué" "ERROR"
            return $false
        }
    }
    catch {
        Write-ExceptionLog $_ "Install-Docker"
        return $false
    }
    finally {
        # Nettoyer l'installateur
        if (Test-Path $installerPath) {
            Remove-Item -Path $installerPath -Force
        }
    }
}

<#
.SYNOPSIS
    Installe PostgreSQL.

.DESCRIPTION
    Cette fonction télécharge et installe PostgreSQL selon la configuration spécifiée.

.PARAMETER Config
    Configuration spécifique pour PostgreSQL.

.EXAMPLE
    Install-PostgreSQL -Config $postgresConfig
#>
function Install-PostgreSQL {
    param (
        [Parameter(Mandatory=$true)]
        [PSCustomObject]$Config
    )
    
    Write-LogMessage "Installation de PostgreSQL..." "INFO"
    
    try {
        $installerPath = "$env:TEMP\postgresql_installer.exe"
        $downloadUrl = $Config.downloadUrl
        
        if (-not $downloadUrl) {
            $version = $Config.minVersion
            if (-not $version) {
                $version = "15.3-1"
            }
            $downloadUrl = "https://get.enterprisedb.com/postgresql/postgresql-$version-windows-x64.exe"
        }
        
        # Télécharger l'installateur
        Write-LogMessage "Téléchargement de PostgreSQL depuis $downloadUrl" "INFO"
        Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath
        
        # Préparer les arguments d'installation
        $installDir = $Config.installDir
        if (-not $installDir) {
            $installDir = "C:\Program Files\PostgreSQL\$version"
        }
        
        $password = $Config.password
        if (-not $password) {
            $password = "postgres"
        }
        
        $port = $Config.port
        if (-not $port) {
            $port = "5432"
        }
        
        # Exécuter l'installateur en mode silencieux
        Write-LogMessage "Exécution de l'installateur PostgreSQL" "INFO"
        $installArgs = "--mode unattended --unattendedmodeui none --superpassword $password --serverport $port --prefix `"$installDir`""
        
        Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait
        
        # Vérifier l'installation
        $pgPath = "$installDir\bin\psql.exe"
        if (Test-Path $pgPath) {
            Write-LogMessage "PostgreSQL a été installé" "SUCCESS"
            
            # Configuration post-installation
            Write-LogMessage "Configuration de PostgreSQL..." "INFO"
            
            # Ajouter le répertoire bin au PATH
            $env:Path += ";$installDir\bin"
            [Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)
            
            # Créer la base de données pour l'application si spécifié
            if ($Config.createDatabase -eq $true) {
                $dbName = $Config.dbName
                if (-not $dbName) {
                    $dbName = "ocr_db_staging"
                }
                
                $dbUser = $Config.dbUser
                if (-not $dbUser) {
                    $dbUser = "technicia"
                }
                
                $dbPassword = $Config.dbPassword
                if (-not $dbPassword) {
                    $dbPassword = "technicia_password"
                }
                
                # Créer l'utilisateur et la base de données
                $env:PGPASSWORD = $password
                
                Write-LogMessage "Création de l'utilisateur $dbUser..." "INFO"
                & "$installDir\bin\psql.exe" -h localhost -U postgres -c "CREATE USER $dbUser WITH PASSWORD '$dbPassword';"
                
                Write-LogMessage "Création de la base de données $dbName..." "INFO"
                & "$installDir\bin\psql.exe" -h localhost -U postgres -c "CREATE DATABASE $dbName OWNER $dbUser;"
                
                $env:PGPASSWORD = ""
            }
            
            return $true
        }
        else {
            Write-LogMessage "L'installation de PostgreSQL a échoué" "ERROR"
            return $false
        }
    }
    catch {
        Write-ExceptionLog $_ "Install-PostgreSQL"
        return $false
    }
    finally {
        # Nettoyer l'installateur
        if (Test-Path $installerPath) {
            Remove-Item -Path $installerPath -Force
        }
    }
}

<#
.SYNOPSIS
    Installe Python.

.DESCRIPTION
    Cette fonction télécharge et installe Python selon la configuration spécifiée.

.PARAMETER Config
    Configuration spécifique pour Python.

.EXAMPLE
    Install-Python -Config $pythonConfig
#>
function Install-Python {
    param (
        [Parameter(Mandatory=$true)]
        [PSCustomObject]$Config
    )
    
    Write-LogMessage "Installation de Python..." "INFO"
    
    try {
        $installerPath = "$env:TEMP\python_installer.exe"
        $downloadUrl = $Config.downloadUrl
        
        if (-not $downloadUrl) {
            $version = $Config.minVersion
            if (-not $version) {
                $version = "3.10.11"
            }
            $downloadUrl = "https://www.python.org/ftp/python/$version/python-$version-amd64.exe"
        }
        
        # Télécharger l'installateur
        Write-LogMessage "Téléchargement de Python depuis $downloadUrl" "INFO"
        Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath
        
        # Préparer les arguments d'installation
        $installDir = $Config.installDir
        if (-not $installDir) {
            $installDir = "C:\Python310"
        }
        
        # Exécuter l'installateur en mode silencieux
        Write-LogMessage "Exécution de l'installateur Python" "INFO"
        $installArgs = "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 TargetDir=`"$installDir`""
        
        Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait
        
        # Vérifier l'installation
        $pythonPath = "$installDir\python.exe"
        if (Test-Path $pythonPath) {
            Write-LogMessage "Python a été installé" "SUCCESS"
            
            # Mettre à jour pip
            Write-LogMessage "Mise à jour de pip..." "INFO"
            Start-Process -FilePath $pythonPath -ArgumentList "-m pip install --upgrade pip" -Wait
            
            # Installer les packages essentiels
            Write-LogMessage "Installation des packages Python essentiels..." "INFO"
            Start-Process -FilePath $pythonPath -ArgumentList "-m pip install virtualenv wheel setuptools" -Wait
            
            return $true
        }
        else {
            Write-LogMessage "L'installation de Python a échoué" "ERROR"
            return $false
        }
    }
    catch {
        Write-ExceptionLog $_ "Install-Python"
        return $false
    }
    finally {
        # Nettoyer l'installateur
        if (Test-Path $installerPath) {
            Remove-Item -Path $installerPath -Force
        }
    }
}

<#
.SYNOPSIS
    Installe les packages Python requis.

.DESCRIPTION
    Cette fonction installe les packages Python spécifiés via pip.

.PARAMETER Packages
    Liste des packages Python à installer.

.EXAMPLE
    Install-PythonPackages -Packages @("fastapi", "sqlalchemy", "celery")
#>
function Install-PythonPackages {
    param (
        [Parameter(Mandatory=$true)]
        [array]$Packages
    )
    
    Write-LogMessage "Installation des packages Python..." "INFO"
    
    try {
        # Trouver le chemin vers Python
        $pythonInfo = Test-SoftwareInstalled -SoftwareName "Python" -ExecutableName "python"
        
        if (-not $pythonInfo.IsInstalled) {
            Write-LogMessage "Python n'est pas installé, impossible d'installer les packages" "ERROR"
            return $false
        }
        
        $pythonPath = "python"
        if ($pythonInfo.Path) {
            $pythonPath = $pythonInfo.Path
        }
        
        # Installer chaque package
        foreach ($package in $Packages) {
            $packageName = $package.name
            $packageVersion = $package.version
            
            Write-LogMessage "Installation du package Python: $packageName..." "INFO"
            
            $installCmd = "-m pip install"
            if ($packageVersion) {
                $installCmd += " $packageName==$packageVersion"
            }
            else {
                $installCmd += " $packageName"
            }
            
            Start-Process -FilePath $pythonPath -ArgumentList $installCmd -Wait -NoNewWindow
            
            # Vérifier l'installation
            $checkCmd = "-c `"import $($packageName.Split('=')[0].Split('[')[0].Split('<')[0].Split('>')[0]); print('Package installé')`""
            $checkResult = Start-Process -FilePath $pythonPath -ArgumentList $checkCmd -Wait -NoNewWindow -RedirectStandardOutput "NUL" -PassThru
            
            if ($checkResult.ExitCode -eq 0) {
                Write-LogMessage "Package Python $packageName installé avec succès" "SUCCESS"
            }
            else {
                Write-LogMessage "L'installation du package Python $packageName a échoué" "ERROR"
            }
        }
        
        Write-LogMessage "Installation des packages Python terminée" "SUCCESS"
        return $true
    }
    catch {
        Write-LogMessage "Erreur lors de l'installation des packages Python: $($_.Exception.Message)" "ERROR"
        Write-LogMessage "Stack trace: $($_.ScriptStackTrace)" "ERROR"
        return $false
    }
}

# Rendre les fonctions disponibles pour les autres scripts
$global:Install_RequiredSoftware = ${function:Install-RequiredSoftware}
$global:Install_Docker = ${function:Install-Docker}
$global:Install_PostgreSQL = ${function:Install-PostgreSQL}
$global:Install_Python = ${function:Install-Python}
