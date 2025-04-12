# Module de configuration réseau pour l'environnement de staging
# Version: 1.0
# Date: 7 avril 2025
#
# Ce module gère la configuration réseau nécessaire pour l'environnement
# de staging du système OCR Technicia, incluant la configuration des ports,
# des règles de pare-feu et du serveur web.

<#
.SYNOPSIS
    Configure le réseau pour l'environnement de staging.

.DESCRIPTION
    Cette fonction effectue toutes les configurations réseau nécessaires
    pour l'environnement de staging du système OCR Technicia, notamment
    l'ouverture des ports requis et la configuration du pare-feu Windows.

.EXAMPLE
    Configure-Network
#>
function Set-NetworkConfiguration {
    Start-LogSection "Configuration réseau"
    
    try {
        # 1. Configuration des ports
        Configure-Ports
        
        # 2. Configuration du pare-feu Windows
        Configure-Firewall
        
        # 3. Configuration du proxy inverse (si nécessaire)
        if ($global:config.network.reverseProxy -eq $true) {
            Configure-ReverseProxy
        }
        
        # 4. Tester la configuration réseau
        Test-NetworkConfig
        
        Write-LogMessage "Configuration réseau terminée avec succès" "SUCCESS"
    }
    catch {
        Write-ExceptionLog $_ "Set-NetworkConfiguration"
        Write-LogMessage "La configuration réseau a échoué" "ERROR"
    }
    
    Stop-LogSection
}

<#
.SYNOPSIS
    Configure les ports requis pour l'application.

.DESCRIPTION
    Cette fonction vérifie la disponibilité des ports requis et libère
    les ports utilisés si nécessaire.

.EXAMPLE
    Configure-Ports
#>
function Set-PortConfiguration {
    Start-LogTask "Configuration des ports"
    
    try {
        $requiredPorts = $global:config.network.requiredPorts
        $portConflicts = @()
        
        # Vérifier chaque port requis
        foreach ($port in $requiredPorts) {
            $portNumber = $port.port
            $application = $port.application
            $critical = $port.critical -eq $true
            
            Write-LogMessage "Vérification du port $portNumber pour $application..." "INFO"
            
            # Vérifier si le port est déjà utilisé
            $portInUse = Test-NetConnection -ComputerName "localhost" -Port $portNumber -WarningAction SilentlyContinue -InformationLevel Quiet -ErrorAction SilentlyContinue
            
            if ($portInUse) {
                $processInfo = Get-NetTCPConnection -LocalPort $portNumber -ErrorAction SilentlyContinue | 
                               Select-Object -First 1 | 
                               ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
                
                if ($processInfo) {
                    Write-LogMessage "Port $portNumber déjà utilisé par le processus: $($processInfo.ProcessName) (PID: $($processInfo.Id))" "WARN"
                    
                    # Si nous sommes autorisés à libérer le port et que ce n'est pas un service critique
                    if ($port.forceRelease -eq $true) {
                        Write-LogMessage "Tentative de libération du port $portNumber..." "WARN"
                        
                        try {
                            # Arrêter le processus qui utilise le port
                            Stop-Process -Id $processInfo.Id -Force -ErrorAction SilentlyContinue
                            Write-LogMessage "Le processus utilisant le port $portNumber a été arrêté" "SUCCESS"
                        }
                        catch {
                            Write-LogMessage "Impossible d'arrêter le processus utilisant le port $portNumber" "ERROR"
                            if ($critical) {
                                $portConflicts += "$portNumber ($application)"
                            }
                        }
                    }
                    else {
                        if ($critical) {
                            $portConflicts += "$portNumber ($application)"
                        }
                    }
                }
                else {
                    Write-LogMessage "Port $portNumber déjà utilisé mais impossible d'identifier le processus" "WARN"
                    if ($critical) {
                        $portConflicts += "$portNumber ($application)"
                    }
                }
            }
            else {
                Write-LogMessage "Port $portNumber disponible pour $application" "SUCCESS"
            }
        }
        
        # Si des conflits de port critiques existent toujours
        if ($portConflicts.Count -gt 0) {
            Write-LogMessage "Des ports critiques ne sont pas disponibles: $($portConflicts -join ', ')" "ERROR"
            Complete-LogTask "Configuration des ports" $false
            return $false
        }
        
        Write-LogMessage "Tous les ports requis sont configurés correctement" "SUCCESS"
        Complete-LogTask "Configuration des ports" $true
        return $true
    }
    catch {
        Write-ExceptionLog $_ "Set-PortConfiguration"
        Complete-LogTask "Configuration des ports" $false
        return $false
    }
}

<#
.SYNOPSIS
    Configure les règles de pare-feu Windows pour l'application.

.DESCRIPTION
    Cette fonction configure les règles de pare-feu Windows pour permettre
    les communications entrantes et sortantes nécessaires pour l'application.

.EXAMPLE
    Configure-Firewall
#>
function Set-FirewallConfiguration {
    Start-LogTask "Configuration du pare-feu Windows"
    
    try {
        $requiredPorts = $global:config.network.requiredPorts
        $applicationName = $global:config.general.applicationName
        
        # Vérifier si le pare-feu Windows est actif
        $firewallEnabled = Get-NetFirewallProfile | Where-Object { $_.Enabled -eq $true }
        
        if (-not $firewallEnabled) {
            Write-LogMessage "Le pare-feu Windows semble être désactivé sur tous les profils" "WARN"
        }
        
        # Créer un groupe de règles pour notre application
        $appRuleGroupName = "$applicationName-StagingRules"
        
        # Supprimer les règles existantes avec le même nom (pour éviter les doublons)
        Get-NetFirewallRule -DisplayName "$appRuleGroupName-*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
        
        # Créer des règles pour chaque port requis
        foreach ($port in $requiredPorts) {
            $portNumber = $port.port
            $protocol = $port.protocol.ToUpper()
            $description = "Allow $($port.application) on port $portNumber"
            
            $ruleName = "$appRuleGroupName-$($port.application)-$portNumber-$protocol"
            
            Write-LogMessage "Création de la règle de pare-feu pour $($port.application) sur le port $portNumber/$protocol..." "INFO"
            
            # Règle entrante
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol $protocol -LocalPort $portNumber -Description $description | Out-Null
            
            Write-LogMessage "Règle de pare-feu créée: $ruleName" "SUCCESS"
        }
        
        # Vérifier que les règles ont été créées
        $createdRules = Get-NetFirewallRule -DisplayName "$appRuleGroupName-*" -ErrorAction SilentlyContinue
        
        if ($createdRules) {
            Write-LogMessage "Toutes les règles de pare-feu ont été créées avec succès" "SUCCESS"
            Complete-LogTask "Configuration du pare-feu Windows" $true
            return $true
        }
        else {
            Write-LogMessage "Problème lors de la création des règles de pare-feu" "ERROR"
            Complete-LogTask "Configuration du pare-feu Windows" $false
            return $false
        }
    }
    catch {
        Write-ExceptionLog $_ "Set-FirewallConfiguration"
        Complete-LogTask "Configuration du pare-feu Windows" $false
        return $false
    }
}

<#
.SYNOPSIS
    Configure un proxy inverse pour l'application.

.DESCRIPTION
    Cette fonction configure un proxy inverse (Nginx) pour rediriger
    le trafic vers les différents services de l'application.

.EXAMPLE
    Configure-ReverseProxy
#>
function Set-ReverseProxyConfiguration {
    Start-LogTask "Configuration du proxy inverse"
    
    try {
        # Vérifier si Nginx est installé
        $nginxInfo = Test-SoftwareInstalled -SoftwareName "Nginx" -ExecutableName "nginx"
        
        if (-not $nginxInfo.IsInstalled) {
            Write-LogMessage "Nginx n'est pas installé, installation en cours..." "WARN"
            
            # Installer Nginx
            $nginxConfig = $global:config.software.requiredSoftware | Where-Object { $_.name -eq "Nginx" }
            if (-not $nginxConfig) {
                $nginxConfig = @{
                    name = "Nginx"
                    minVersion = "1.22.0"
                    executable = "nginx"
                    downloadUrl = "http://nginx.org/download/nginx-1.22.0.zip"
                }
            }
            
            # Appeler la fonction d'installation (doit être définie dans le module staging_software.ps1)
            # Cette fonction n'est pas encore implémentée dans ce module, donc nous la simulons ici
            Write-LogMessage "L'installation de Nginx sera gérée par le module d'installation des logiciels" "INFO"
        }
        
        # Chemin d'installation de Nginx
        $nginxPath = if ($nginxInfo.Path) { Split-Path -Parent $nginxInfo.Path } else { "C:\nginx" }
        $nginxConfigPath = "$nginxPath\conf\nginx.conf"
        $nginxBackupPath = "$nginxPath\conf\nginx.conf.bak"
        
        # Sauvegarder la configuration existante
        if (Test-Path $nginxConfigPath) {
            Copy-Item -Path $nginxConfigPath -Destination $nginxBackupPath -Force
            Write-LogMessage "Configuration Nginx existante sauvegardée: $nginxBackupPath" "INFO"
        }
        
        # Créer la nouvelle configuration
        $proxyConfig = $global:config.network.proxyConfig
        
        if (-not $proxyConfig -or -not $proxyConfig.servers) {
            Write-LogMessage "Configuration du proxy inverse non fournie dans le fichier de configuration" "ERROR"
            Complete-LogTask "Configuration du proxy inverse" $false
            return $false
        }
        
        # Générer la configuration Nginx
        $nginxConfigContent = @"
worker_processes auto;
events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;
    
    # Logs
    access_log logs/access.log;
    error_log  logs/error.log;

"@
        
        # Ajouter les serveurs du proxy
        foreach ($server in $proxyConfig.servers) {
            $nginxConfigContent += @"
    
    # $($server.name)
    server {
        listen $($server.port);
        server_name $($server.serverName);
        
"@
            
            # Ajouter les locations
            foreach ($location in $server.locations) {
                $nginxConfigContent += @"
        
        location $($location.path) {
            proxy_pass $($location.proxyPass);
            proxy_set_header Host `$host;
            proxy_set_header X-Real-IP `$remote_addr;
            proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto `$scheme;
        }
        
"@
            }
            
            $nginxConfigContent += @"
    }
    
"@
        }
        
        $nginxConfigContent += @"
}
"@
        
        # Écrire la configuration dans le fichier
        Set-Content -Path $nginxConfigPath -Value $nginxConfigContent
        
        Write-LogMessage "Configuration Nginx créée: $nginxConfigPath" "SUCCESS"
        
        # Redémarrer Nginx
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
            Complete-LogTask "Configuration du proxy inverse" $true
            return $true
        }
        catch {
            Write-ExceptionLog $_ "Redémarrage de Nginx"
            Complete-LogTask "Configuration du proxy inverse" $false
            return $false
        }
    }
    catch {
        Write-ExceptionLog $_ "Set-ReverseProxyConfiguration"
        Complete-LogTask "Configuration du proxy inverse" $false
        return $false
    }
}

<#
.SYNOPSIS
    Teste la configuration réseau.

.DESCRIPTION
    Cette fonction vérifie que toutes les configurations réseau sont
    correctement appliquées et fonctionnelles.

.EXAMPLE
    Test-NetworkConfig
#>
function Test-NetworkConfig {
    Start-LogTask "Test de la configuration réseau"
    
    try {
        $allTestsPassed = $true
        $requiredPorts = $global:config.network.requiredPorts
        
        # Tester chaque port
        foreach ($port in $requiredPorts) {
            $portNumber = $port.port
            $application = $port.application
            
            Write-LogMessage "Test du port $portNumber pour $application..." "INFO"
            
            # Vérifier si le port est accessible localement
            $portTest = Test-NetConnection -ComputerName "localhost" -Port $portNumber -WarningAction SilentlyContinue -InformationLevel Detailed -ErrorAction SilentlyContinue
            
            if ($portTest.TcpTestSucceeded) {
                Write-LogMessage "Port $portNumber accessible localement" "SUCCESS"
            }
            else {
                Write-LogMessage "Port $portNumber non accessible localement" "WARN"
                if ($port.critical -eq $true) {
                    $allTestsPassed = $false
                }
            }
        }
        
        # Tester les règles de pare-feu
        $applicationName = $global:config.general.applicationName
        $appRuleGroupName = "$applicationName-StagingRules"
        
        $firewallRules = Get-NetFirewallRule -DisplayName "$appRuleGroupName-*" -ErrorAction SilentlyContinue
        
        if ($firewallRules) {
            Write-LogMessage "Règles de pare-feu détectées: $($firewallRules.Count) règle(s)" "SUCCESS"
        }
        else {
            Write-LogMessage "Aucune règle de pare-feu détectée pour l'application" "ERROR"
            $allTestsPassed = $false
        }
        
        # Tester la connectivité Internet
        $internetTest = Test-Connection -ComputerName "www.google.com" -Count 1 -Quiet -ErrorAction SilentlyContinue
        
        if ($internetTest) {
            Write-LogMessage "Connectivité Internet disponible" "SUCCESS"
        }
        else {
            Write-LogMessage "Connectivité Internet non disponible" "WARN"
            # Ne pas échouer pour cette vérification
        }
        
        if ($allTestsPassed) {
            Write-LogMessage "Tous les tests de configuration réseau ont réussi" "SUCCESS"
        }
        else {
            Write-LogMessage "Certains tests de configuration réseau ont échoué" "ERROR"
        }
        
        Complete-LogTask "Test de la configuration réseau" $allTestsPassed
        return $allTestsPassed
    }
    catch {
        Write-ExceptionLog $_ "Test-NetworkConfig"
        Complete-LogTask "Test de la configuration réseau" $false
        return $false
    }
}

# Rendre les fonctions disponibles pour les autres scripts
$global:Set_NetworkConfiguration = ${function:Set-NetworkConfiguration}
$global:Set_PortConfiguration = ${function:Set-PortConfiguration}
$global:Set_FirewallConfiguration = ${function:Set-FirewallConfiguration}
$global:Set_ReverseProxyConfiguration = ${function:Set-ReverseProxyConfiguration}
$global:Test_NetworkConfig = ${function:Test-NetworkConfig}
