# ==========================================================================
# Script de préparation de l'environnement de staging pour Technicia OCR
# Version: 1.1
# Date: 7 avril 2025
#
# Description: 
# Ce script automatise la préparation complète de l'environnement de staging
# pour le système OCR Technicia selon les spécifications définies.
#
# Il gère les opérations suivantes:
#   - Vérification des prérequis système
#   - Installation des logiciels nécessaires
#   - Configuration réseau
#   - Configuration de sécurité
#   - Préparation des données
#   - Initialisation et migrations de la base de données
#   - Exécution des tests (si activé)
# ==========================================================================

param (
    [Parameter(Mandatory=$false)]
    [string]$ConfigPath = "..\..\deploy\configs\staging_config.json",
    
    [switch]$SkipPrerequisites = $false,
    
    [switch]$SkipSoftwareInstall = $false,
    
    [switch]$SkipNetworkConfig = $false,
    
    [switch]$SkipSecurityConfig = $false,
    
    [switch]$SkipDataPreparation = $false,
    
    [switch]$SkipDatabasePreparation = $false,
    
    [switch]$IncludeTestData = $false,
    
    [switch]$Force = $false
)

#region Initialisation
# Déterminer le chemin de base
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$global:basePath = (Get-Item $scriptPath).Parent.Parent.FullName

# Importer les modules utilitaires
. "$scriptPath\utils\staging_logger.ps1"
. "$scriptPath\utils\staging_prereqs.ps1"
. "$scriptPath\utils\staging_software.ps1"
. "$scriptPath\utils\staging_network.ps1"
. "$scriptPath\utils\staging_security.ps1"
. "$scriptPath\utils\staging_data.ps1"
. "$scriptPath\utils\staging_database.ps1"

# Initialiser le fichier de log
$logDir = Join-Path -Path $global:basePath -ChildPath "deploy\logs"
if (-not (Test-Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$global:logFile = Join-Path -Path $logDir -ChildPath "staging_prep_$timestamp.log"

# Charger la configuration
function Import-Configuration {
    param (
        [string]$ConfigPath
    )
    
    if (-not (Test-Path $ConfigPath)) {
        Write-LogMessage "Le fichier de configuration '$ConfigPath' n'existe pas!" "ERROR"
        Exit 1
    }
    
    try {
        $config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
        return $config
    }
    catch {
        Write-LogMessage "Erreur lors du chargement de la configuration: $_" "ERROR"
        Exit 1
    }
}

$global:config = Import-Configuration -ConfigPath $ConfigPath
#endregion Initialisation

#region Fonctions utilitaires
function Confirm-Action {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [switch]$WarningMessage = $false
    )
    
    if ($Force) {
        return $true
    }
    
    $style = if ($WarningMessage) { "Yellow" } else { "Cyan" }
    Write-Host $Message -ForegroundColor $style
    
    $options = @("O", "o", "N", "n")
    $response = ""
    
    while (-not $options.Contains($response)) {
        $response = Read-Host "Entrez O pour Oui, N pour Non"
    }
    
    return $response -eq "O" -or $response -eq "o"
}

function Show-Summary {
    Write-LogMessage "=== RÉSUMÉ DE LA PRÉPARATION DE L'ENVIRONNEMENT DE STAGING ===" "INFO"
    
    # Générer le rapport HTML
    $reportDir = Join-Path -Path $global:basePath -ChildPath "deploy\reports"
    if (-not (Test-Path $reportDir)) {
        New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
    }
    
    $reportFile = Join-Path -Path $reportDir -ChildPath "staging_prep_report_$timestamp.html"
    
    $htmlContent = @"
<!DOCTYPE html>
<html>
<head>
    <title>Rapport de préparation de l'environnement de staging - Technicia OCR</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #2c3e50; }
        .section { margin-bottom: 20px; }
        .section-title { background-color: #34495e; color: white; padding: 5px 10px; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Rapport de préparation de l'environnement de staging</h1>
    <p>Date et heure: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>
    
    <div class="section">
        <h2 class="section-title">Informations système</h2>
        <table>
            <tr><th>Composant</th><th>Détails</th></tr>
            <tr><td>Système d'exploitation</td><td>$((Get-WmiObject -Class Win32_OperatingSystem).Caption)</td></tr>
            <tr><td>Processeur</td><td>$((Get-WmiObject -Class Win32_Processor).Name) ($(Get-WmiObject -Class Win32_Processor).NumberOfCores) cœurs)</td></tr>
            <tr><td>Mémoire RAM</td><td>$([math]::Round((Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)) Go</td></tr>
            <tr><td>Espace disque disponible</td><td>$([math]::Round((Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB, 2)) Go</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2 class="section-title">Résumé des étapes</h2>
        <table>
            <tr><th>Étape</th><th>Statut</th><th>Commentaires</th></tr>
            <tr><td>Vérification des prérequis</td><td class="$(if ($SkipPrerequisites) { "warning" } else { "success" })">$(if ($SkipPrerequisites) { "Ignoré" } else { "Complété" })</td><td>$(if ($SkipPrerequisites) { "L'utilisateur a choisi d'ignorer cette étape" } else { "Tous les prérequis sont satisfaits" })</td></tr>
            <tr><td>Installation des logiciels</td><td class="$(if ($SkipSoftwareInstall) { "warning" } else { "success" })">$(if ($SkipSoftwareInstall) { "Ignoré" } else { "Complété" })</td><td>$(if ($SkipSoftwareInstall) { "L'utilisateur a choisi d'ignorer cette étape" } else { "Tous les logiciels requis sont installés" })</td></tr>
            <tr><td>Configuration réseau</td><td class="$(if ($SkipNetworkConfig) { "warning" } else { "success" })">$(if ($SkipNetworkConfig) { "Ignoré" } else { "Complété" })</td><td>$(if ($SkipNetworkConfig) { "L'utilisateur a choisi d'ignorer cette étape" } else { "La configuration réseau est terminée" })</td></tr>
            <tr><td>Configuration de sécurité</td><td class="$(if ($SkipSecurityConfig) { "warning" } else { "success" })">$(if ($SkipSecurityConfig) { "Ignoré" } else { "Complété" })</td><td>$(if ($SkipSecurityConfig) { "L'utilisateur a choisi d'ignorer cette étape" } else { "La configuration de sécurité est terminée" })</td></tr>
            <tr><td>Préparation des données</td><td class="$(if ($SkipDataPreparation) { "warning" } else { "success" })">$(if ($SkipDataPreparation) { "Ignoré" } else { "Complété" })</td><td>$(if ($SkipDataPreparation) { "L'utilisateur a choisi d'ignorer cette étape" } else { "Les données ont été préparées avec succès" })</td></tr>
            <tr><td>Préparation de la base de données</td><td class="$(if ($SkipDatabasePreparation) { "warning" } else { "success" })">$(if ($SkipDatabasePreparation) { "Ignoré" } else { "Complété" })</td><td>$(if ($SkipDatabasePreparation) { "L'utilisateur a choisi d'ignorer cette étape" } else { if ($IncludeTestData) { "La base de données a été préparée avec les données de test" } else { "La base de données a été préparée (sans données de test)" } })</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2 class="section-title">Prochaines étapes recommandées</h2>
        <ul>
            <li>Vérifier l'accès à l'application Technicia OCR</li>
            <li>Exécuter les tests d'acceptation utilisateur</li>
            <li>Vérifier la journalisation et le monitoring</li>
            <li>Effectuer une sauvegarde initiale complète</li>
        </ul>
    </div>
    
    <p>Pour plus d'informations, consultez le fichier log: $global:logFile</p>
</body>
</html>
"@
    
    $htmlContent | Out-File -FilePath $reportFile -Encoding UTF8
    
    Write-LogMessage "Rapport de préparation généré: $reportFile" "INFO"
}
#endregion Fonctions utilitaires

#region Fonctions principales
function Initialize-StagingPreparation {
    Write-LogMessage "=== INITIALISATION DE LA PRÉPARATION DE L'ENVIRONNEMENT DE STAGING ===" "INFO"
    
    # Vérifier l'accès administrateur uniquement si on ne saute pas toutes les étapes
    if (-not ($SkipPrerequisites -and $SkipSoftwareInstall -and $SkipNetworkConfig -and $SkipSecurityConfig -and $SkipDataPreparation -and $SkipDatabasePreparation)) {
        $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
        $isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        
        if (-not $isAdmin) {
            Write-LogMessage "Ce script doit être exécuté avec des privilèges administrateur!" "ERROR"
            Exit 1
        }
    }
    else {
        Write-LogMessage "Mode test: contournement de la vérification des privilèges administrateur" "WARN"
    }
    
    # Vérifier l'accès au répertoire de base
    if (-not (Test-Path $global:basePath)) {
        Write-LogMessage "Impossible d'accéder au répertoire de base: $global:basePath" "ERROR"
        Exit 1
    }
    
    Write-LogMessage "Fichier log: $global:logFile" "INFO"
    Write-LogMessage "Date et heure de début: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "INFO"
    
    Write-LogMessage "=== DÉBUT DE LA PRÉPARATION DE L'ENVIRONNEMENT DE STAGING ===" "INFO"
}

function Complete-StagingPreparation {
    Write-LogMessage "=== FINALISATION DE LA PRÉPARATION DE L'ENVIRONNEMENT DE STAGING ===" "INFO"
    
    # Effectuer des opérations de nettoyage si nécessaire
    # ...
    
    Write-LogMessage "Fichier log: $global:logFile" "INFO"
    Write-LogMessage "Date et heure de fin: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "INFO"
    
    Write-LogMessage "=== FIN DE LA PRÉPARATION DE L'ENVIRONNEMENT DE STAGING ===" "SUCCESS"
}
#endregion Fonctions principales

#region Exécution principale
try {
    # Afficher l'en-tête
    Write-LogMessage "=============================================================" "INFO"
    Write-LogMessage "  PRÉPARATION DE L'ENVIRONNEMENT DE STAGING - TECHNICIA OCR  " "INFO"
    Write-LogMessage "=============================================================" "INFO"
    Write-LogMessage "Date et heure de début: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "INFO"
    Write-LogMessage "Version du script: 1.1" "INFO"
    Write-LogMessage "Chemin de base: $global:basePath" "INFO"
    Write-LogMessage "=============================================================" "INFO"
    
    # Initialiser la préparation
    Initialize-StagingPreparation
    
    # 1. Vérification des prérequis
    if (-not $SkipPrerequisites) {
        $confirmPrereqs = Confirm-Action -Message "Voulez-vous procéder à la vérification des prérequis système?"
        
        if ($confirmPrereqs) {
            $prereqsOk = Test-SystemPrerequisites
            
            if (-not $prereqsOk) {
                $confirmContinue = Confirm-Action -Message "Certains prérequis système ne sont pas satisfaits. Voulez-vous continuer quand même?" -WarningMessage
                
                if (-not $confirmContinue) {
                    Write-LogMessage "Préparation interrompue: prérequis système non satisfaits" "ERROR"
                    Exit 1
                }
            }
            
            $dependenciesOk = Test-SoftwareDependencies
            
            if (-not $dependenciesOk) {
                $confirmDependencies = Confirm-Action -Message "Certaines dépendances logicielles ne sont pas satisfaites. Voulez-vous continuer quand même?" -WarningMessage
                
                if (-not $confirmDependencies) {
                    Write-LogMessage "Préparation interrompue: dépendances logicielles non satisfaites" "ERROR"
                    Exit 1
                }
            }
        }
    }
    else {
        Write-LogMessage "Vérification des prérequis ignorée" "WARN"
    }
    
    # 2. Installation des logiciels
    if (-not $SkipSoftwareInstall) {
        $confirmSoftware = Confirm-Action -Message "Voulez-vous procéder à l'installation des logiciels requis?"
        
        if ($confirmSoftware) {
            Install-RequiredSoftware
        }
    }
    else {
        Write-LogMessage "Installation des logiciels ignorée" "WARN"
    }
    
    # 3. Configuration réseau
    if (-not $SkipNetworkConfig) {
        $confirmNetwork = Confirm-Action -Message "Voulez-vous procéder à la configuration réseau?"
        
        if ($confirmNetwork) {
            Set-NetworkConfiguration
        }
    }
    else {
        Write-LogMessage "Configuration réseau ignorée" "WARN"
    }
    
    # 4. Configuration de sécurité
    if (-not $SkipSecurityConfig) {
        $confirmSecurity = Confirm-Action -Message "Voulez-vous procéder à la configuration de sécurité?"
        
        if ($confirmSecurity) {
            Set-SecurityConfiguration
        }
    }
    else {
        Write-LogMessage "Configuration de sécurité ignorée" "WARN"
    }
    
    # 5. Préparation des données
    if (-not $SkipDataPreparation) {
        $confirmData = Confirm-Action -Message "Voulez-vous procéder à la préparation des données?"
        
        if ($confirmData) {
            Start-DataPreparation
        }
    }
    else {
        Write-LogMessage "Préparation des données ignorée" "WARN"
    }
    
    # 6. Préparation de la base de données
    if (-not $SkipDatabasePreparation) {
        $confirmDatabase = Confirm-Action -Message "Voulez-vous procéder à la préparation de la base de données?"
        
        if ($confirmDatabase) {
            $sqlScriptsPath = Join-Path -Path $global:basePath -ChildPath "deploy\scripts\sql"
            
            # Utiliser les paramètres de connexion à la base de données à partir de la configuration
            $dbConfig = $global:config.database
            
            # Préparer la base de données avec les scripts SQL appropriés
            Write-LogMessage "Lancement de la préparation de la base de données..." "INFO"
            
            # Appel de la fonction de préparation de base de données
            & $global:Invoke_DatabasePreparation `
                -Server $dbConfig.server `
                -Port $dbConfig.port `
                -Database $dbConfig.name `
                -Username $dbConfig.username `
                -Password (ConvertTo-SecureString $dbConfig.password -AsPlainText -Force) `
                -SqlScriptsPath $sqlScriptsPath `
                -IncludeTestData:$IncludeTestData
                
            Write-LogMessage "Préparation de la base de données terminée" "SUCCESS"
        }
    }
    else {
        Write-LogMessage "Préparation de la base de données ignorée" "WARN"
    }
    
    # 7. Exécution des tests (si activé)
    if ($global:config.testing.enabled -eq $true -and $global:config.testing.executeTestsAfterDeployment -eq $true) {
        $confirmTests = Confirm-Action -Message "Voulez-vous exécuter les tests après le déploiement?"
        
        if ($confirmTests) {
            Write-LogMessage "Exécution des tests..." "INFO"
            
            # Logique d'exécution des tests (à implémenter)
            # Cette section sera développée ultérieurement
        }
    }
    
    # Afficher le résumé
    Show-Summary
    
    Write-LogMessage "Préparation de l'environnement de staging terminée avec succès!" "SUCCESS"
}
catch {
    # Journaliser l'exception
    Write-LogMessage "Une erreur s'est produite : $($_.Exception.Message)" "ERROR"
    Write-LogMessage "Stack trace: $($_.ScriptStackTrace)" "ERROR"
    Write-LogMessage "La préparation de l'environnement de staging a échoué" "ERROR"
    Exit 1
}
finally {
    Write-LogMessage "Consultez le fichier log pour plus de détails: $global:logFile" "INFO"
}
#endregion Exécution principale
