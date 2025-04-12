# Module de configuration de sécurité pour l'environnement de staging
# Version: 1.0
# Date: 7 avril 2025
#
# Ce module gère la configuration de sécurité pour l'environnement de staging
# du système OCR Technicia, incluant la génération de certificats SSL/TLS,
# la configuration HTTPS, les paramètres d'authentification et les contrôles d'accès.

<#
.SYNOPSIS
    Configure la sécurité pour l'environnement de staging.

.DESCRIPTION
    Cette fonction met en place toutes les configurations de sécurité
    nécessaires pour l'environnement de staging du système OCR Technicia,
    notamment les certificats SSL/TLS, l'authentification, et les contrôles d'accès.

.EXAMPLE
    Configure-Security
#>
function Set-SecurityConfiguration {
    Start-LogSection "Configuration de sécurité"
    
    try {
        # 1. Configuration des certificats SSL/TLS
        Configure-SSL
        
        # 2. Configuration de l'authentification
        Configure-Authentication
        
        # 3. Configuration des contrôles d'accès
        Configure-AccessControl
        
        # 4. Configuration des politiques de sécurité
        Configure-SecurityPolicies
        
        # 5. Tester la configuration de sécurité
        Test-SecurityConfig
        
        Write-LogMessage "Configuration de sécurité terminée avec succès" "SUCCESS"
    }
    catch {
        Write-ExceptionLog $_ "Set-SecurityConfiguration"
        Write-LogMessage "La configuration de sécurité a échoué" "ERROR"
    }
    
    Stop-LogSection
}

<#
.SYNOPSIS
    Configure les certificats SSL/TLS pour l'environnement de staging.

.DESCRIPTION
    Cette fonction génère ou importe des certificats SSL/TLS pour
    sécuriser les communications de l'environnement de staging.

.EXAMPLE
    Configure-SSL
#>
function Set-SSLConfiguration {
    Start-LogTask "Configuration SSL/TLS"
    
    try {
        $sslConfig = $global:config.security.ssl
        
        if (-not $sslConfig) {
            Write-LogMessage "Aucune configuration SSL/TLS trouvée, utilisation des valeurs par défaut" "WARN"
            $sslConfig = @{
                generateSelfSigned = $true
                domainName = "technicia-staging.local"
                certificatePath = "$global:basePath\certificates"
                certificateName = "technicia-staging"
            }
        }
        
        # Créer le répertoire des certificats s'il n'existe pas
        $certPath = $sslConfig.certificatePath
        if (-not (Test-Path $certPath)) {
            New-Item -Path $certPath -ItemType Directory -Force | Out-Null
            Write-LogMessage "Répertoire des certificats créé: $certPath" "INFO"
        }
        
        # Déterminer si nous devons générer un certificat auto-signé ou utiliser un certificat existant
        if ($sslConfig.generateSelfSigned -eq $true) {
            # Générer un certificat auto-signé
            $domainName = $sslConfig.domainName
            $certName = $sslConfig.certificateName
            $certFile = "$certPath\$certName.pfx"
            $certPassword = $sslConfig.certificatePassword
            
            if (-not $certPassword) {
                $certPassword = "Technicia2024!"
            }
            
            Write-LogMessage "Génération d'un certificat SSL/TLS auto-signé pour $domainName..." "INFO"
            
            # Vérifier si un certificat existe déjà
            $existingCert = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object { $_.Subject -like "*$domainName*" }
            
            if ($existingCert) {
                Write-LogMessage "Un certificat pour $domainName existe déjà. Utilisation du certificat existant." "INFO"
                $cert = $existingCert
            }
            else {
                # Créer un certificat avec PowerShell
                Write-LogMessage "Création d'un nouveau certificat auto-signé..." "INFO"
                
                $cert = New-SelfSignedCertificate `
                    -DnsName $domainName `
                    -CertStoreLocation Cert:\LocalMachine\My `
                    -NotAfter (Get-Date).AddYears(1) `
                    -KeyAlgorithm RSA `
                    -KeyLength 2048 `
                    -HashAlgorithm SHA256 `
                    -KeyUsage DigitalSignature, KeyEncipherment, DataEncipherment `
                    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.1") `
                    -FriendlyName "Certificat Technicia Staging"
                
                Write-LogMessage "Certificat auto-signé créé avec succès" "SUCCESS"
            }
            
            # Exporter le certificat au format PFX
            $securePassword = ConvertTo-SecureString -String $certPassword -Force -AsPlainText
            
            Export-PfxCertificate -Cert $cert -FilePath $certFile -Password $securePassword -Force | Out-Null
            
            # Certificat exporté avec succès
            
            Write-LogMessage "Certificat exporté: $certFile" "SUCCESS"
            
            # Mettre à jour la configuration avec le chemin du certificat
            $global:config.security.ssl.certificateFile = $certFile
            $global:config.security.ssl.certificatePassword = $certPassword
        }
        else {
            # Utiliser un certificat existant
            $certFile = $sslConfig.certificateFile
            
            if (-not $certFile -or -not (Test-Path $certFile)) {
                Write-LogMessage "Le certificat spécifié n'existe pas: $certFile" "ERROR"
                Complete-LogTask "Configuration SSL/TLS" $false
                return $false
            }
            
            Write-LogMessage "Utilisation du certificat existant: $certFile" "INFO"
        }
        
        # Configurer les applications pour utiliser le certificat
        if ($global:config.security.ssl.configureApplications -eq $true) {
            # Pour chaque application à configurer
            foreach ($app in $global:config.security.ssl.applications) {
                Write-LogMessage "Configuration de $($app.name) pour utiliser SSL/TLS..." "INFO"
                
                # La logique de configuration dépendra de l'application spécifique
                switch ($app.type) {
                    "nginx" {
                        Configure-NginxSSL -App $app
                    }
                    "iis" {
                        Configure-IISSSL -App $app
                    }
                    "flask" {
                        Configure-FlaskSSL -App $app
                    }
                    "django" {
                        Configure-DjangoSSL -App $app
                    }
                    "fastapi" {
                        Configure-FastAPISSL -App $app
                    }
                    default {
                        Write-LogMessage "Type d'application non pris en charge pour la configuration SSL: $($app.type)" "WARN"
                    }
                }
            }
        }
        
        Write-LogMessage "Configuration SSL/TLS terminée avec succès" "SUCCESS"
        Complete-LogTask "Configuration SSL/TLS" $true
        return $true
    }
    catch {
        Write-ExceptionLog $_ "Set-SSLConfiguration"
        Complete-LogTask "Configuration SSL/TLS" $false
        return $false
    }
}

<#
.SYNOPSIS
    Configure SSL/TLS pour Nginx.

.DESCRIPTION
    Cette fonction configure Nginx pour utiliser des certificats SSL/TLS.

.PARAMETER App
    Configuration de l'application Nginx.

.EXAMPLE
    Configure-NginxSSL -App $nginxApp
#>
function Set-NginxSSLConfiguration {
    param (
        [Parameter(Mandatory=$true)]
        [PSCustomObject]$App
    )
    
    try {
        $nginxPath = $App.path
        if (-not $nginxPath) {
            # Essayer de trouver le chemin d'installation de Nginx
            $nginxInfo = Test-SoftwareInstalled -SoftwareName "Nginx" -ExecutableName "nginx"
            $nginxPath = if ($nginxInfo.Path) { Split-Path -Parent $nginxInfo.Path } else { "C:\nginx" }
        }
        
        $nginxConfigPath = "$nginxPath\conf\nginx.conf"
        $nginxBackupPath = "$nginxPath\conf\nginx.conf.bak"
        
        # Sauvegarder la configuration existante
        if (Test-Path $nginxConfigPath) {
            Copy-Item -Path $nginxConfigPath -Destination $nginxBackupPath -Force
            Write-LogMessage "Configuration Nginx existante sauvegardée: $nginxBackupPath" "INFO"
        }
        else {
            Write-LogMessage "Impossible de trouver la configuration Nginx: $nginxConfigPath" "ERROR"
            return $false
        }
        
        # Lire la configuration
        $nginxConfig = Get-Content -Path $nginxConfigPath -Raw
        
        # Récupérer les informations du certificat
        $certFile = $global:config.security.ssl.certificateFile
        $keyFile = $certFile -replace '\.pfx$', '.key'
        
        # Convertir le certificat PFX en CRT et KEY si nécessaire
        if ($certFile -like "*.pfx" -and -not (Test-Path $keyFile)) {
            $certPassword = $global:config.security.ssl.certificatePassword
            
            # Cette conversion nécessite OpenSSL, donc on vérifie si c'est disponible
            $openssl = Get-Command -Name "openssl" -ErrorAction SilentlyContinue
            
            if (-not $openssl) {
                Write-LogMessage "OpenSSL n'est pas installé. Impossible de convertir le certificat PFX." "ERROR"
                return $false
            }
            
            $crtFile = $certFile -replace '\.pfx$', '.crt'
            
            # Convertir PFX en CRT et KEY
            $opensslCmd = "openssl pkcs12 -in `"$certFile`" -out `"$crtFile`" -nokeys -password pass:$certPassword"
            Invoke-Expression $opensslCmd
            
            $opensslCmd = "openssl pkcs12 -in `"$certFile`" -out `"$keyFile`" -nocerts -nodes -password pass:$certPassword"
            Invoke-Expression $opensslCmd
            
            Write-LogMessage "Certificat converti en format CRT et KEY" "SUCCESS"
        }
        
        # Mettre à jour la configuration pour utiliser SSL/TLS
        $serverBlock = @"
    server {
        listen 443 ssl;
        server_name $($App.serverName);
        
        ssl_certificate "$crtFile";
        ssl_certificate_key "$keyFile";
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;
        ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
        
        # Configuration SSL supplémentaire
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # Autres paramètres de sécurité
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options SAMEORIGIN;
        add_header X-XSS-Protection "1; mode=block";
        
        # Redirection de tout le trafic vers HTTPS
        location / {
            proxy_pass $($App.proxyPass);
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
    
    # Redirection HTTP vers HTTPS
    server {
        listen 80;
        server_name $($App.serverName);
        return 301 https://\$host\$request_uri;
    }
"@
        
        # Ajouter ou remplacer la configuration du serveur
        if ($nginxConfig -match "server\s*\{[^}]*listen\s+443") {
            # Remplacer la configuration existante du serveur HTTPS
            $nginxConfig = $nginxConfig -replace "server\s*\{[^}]*listen\s+443.*?\}\s*(?=server|\}|$)", $serverBlock
        }
        else {
            # Ajouter la nouvelle configuration du serveur
            $nginxConfig = $nginxConfig -replace "http\s*\{(.*?)\s*\}", "http {`$1`n$serverBlock`n}"
        }
        
        # Écrire la configuration mise à jour
        Set-Content -Path $nginxConfigPath -Value $nginxConfig
        
        Write-LogMessage "Configuration SSL/TLS pour Nginx mise à jour: $nginxConfigPath" "SUCCESS"
        
        # Redémarrer Nginx pour appliquer les changements
        Write-LogMessage "Redémarrage de Nginx..." "INFO"
        
        try {
            # Arrêter Nginx s'il est en cours d'exécution
            $nginxProcess = Get-Process -Name "nginx" -ErrorAction SilentlyContinue
            if ($nginxProcess) {
                Start-Process -FilePath "$nginxPath\nginx.exe" -ArgumentList "-s stop" -Wait -NoNewWindow
                Start-Sleep -Seconds 2
            }
            
            # Démarrer Nginx
            Start-Process -FilePath "$nginxPath\nginx.exe" -NoNewWindow
            
            Write-LogMessage "Nginx redémarré avec succès" "SUCCESS"
            return $true
        }
        catch {
            Write-ExceptionLog $_ "Redémarrage de Nginx"
            return $false
        }
    }
    catch {
        Write-ExceptionLog $_ "Set-NginxSSLConfiguration"
        return $false
    }
}

<#
.SYNOPSIS
    Configure l'authentification pour l'environnement de staging.

.DESCRIPTION
    Cette fonction configure les mécanismes d'authentification pour
    l'environnement de staging, notamment les comptes utilisateurs,
    les rôles et les stratégies d'authentification.

.EXAMPLE
    Configure-Authentication
#>
function Set-AuthenticationConfiguration {
    Start-LogTask "Configuration de l'authentification"
    
    try {
        $authConfig = $global:config.security.authentication
        
        if (-not $authConfig) {
            Write-LogMessage "Aucune configuration d'authentification trouvée, utilisation des valeurs par défaut" "WARN"
            $authConfig = @{
                enabled = $true
                method = "basic"
                users = @(
                    @{
                        username = "admin"
                        password = "Admin2024!"
                        role = "admin"
                    },
                    @{
                        username = "user"
                        password = "User2024!"
                        role = "user"
                    }
                )
            }
        }
        
        if ($authConfig.enabled -ne $true) {
            Write-LogMessage "L'authentification est désactivée dans la configuration" "WARN"
            Complete-LogTask "Configuration de l'authentification" $true
            return $true
        }
        
        # Configurer selon la méthode d'authentification
        switch ($authConfig.method) {
            "basic" {
                Configure-BasicAuth -AuthConfig $authConfig
            }
            "jwt" {
                Configure-JWTAuth -AuthConfig $authConfig
            }
            "oauth" {
                Configure-OAuthAuth -AuthConfig $authConfig
            }
            "ldap" {
                Configure-LDAPAuth -AuthConfig $authConfig
            }
            default {
                Write-LogMessage "Méthode d'authentification non prise en charge: $($authConfig.method)" "ERROR"
                Complete-LogTask "Configuration de l'authentification" $false
                return $false
            }
        }
        
        Write-LogMessage "Configuration de l'authentification terminée avec succès" "SUCCESS"
        Complete-LogTask "Configuration de l'authentification" $true
        return $true
    }
    catch {
        Write-LogMessage "Erreur lors de la configuration de l'authentification: $($_.Exception.Message)" "ERROR"
        Write-LogMessage "Stack trace: $($_.ScriptStackTrace)" "ERROR"
        Complete-LogTask "Configuration de l'authentification" $false
        return $false
    }
}

# Rendre les fonctions disponibles pour les autres scripts
$global:Set_SecurityConfiguration = ${function:Set-SecurityConfiguration}
$global:Set_SSLConfiguration = ${function:Set-SSLConfiguration}
$global:Set_NginxSSLConfiguration = ${function:Set-NginxSSLConfiguration}
$global:Set_AuthenticationConfiguration = ${function:Set-AuthenticationConfiguration}
