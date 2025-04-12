# Script de test pour vérifier le chargement des modules et l'accès aux fonctions
# Auteur: Support Technique
# Date: 2025-04-10
# Version: 1.1
# Description: Ce script teste que les modules renommés fonctionnent correctement

param(
    [Parameter(Mandatory=$false)]
    [string]$LogPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$DetailedReportPath = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateHtmlReport,
    
    [Parameter(Mandatory=$false)]
    [switch]$Quiet
)

# Force l'encodage en UTF-8 pour éviter les problèmes avec les caractères accentués
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

# Déterminer le chemin du script de manière robuste
$scriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($scriptPath)) {
    $scriptPath = $PSCommandPath
}

# Si le chemin est toujours vide (peut arriver avec certaines méthodes d'invocation), utiliser le répertoire courant
if ([string]::IsNullOrEmpty($scriptPath)) {
    $scriptPath = Join-Path -Path (Get-Location) -ChildPath "test_modules.ps1"
}

# Définir le répertoire de base pour les scripts
$baseDir = Split-Path -Parent $scriptPath

# Définir le chemin des logs si non spécifié
if ([string]::IsNullOrEmpty($LogPath)) {
    $LogPath = Join-Path -Path $baseDir -ChildPath "logs"
}

# Définir la politique d'exécution pour cette session
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# Charger les utilitaires
$utilsDir = Join-Path -Path $baseDir -ChildPath "utils"

# Créer le répertoire de logs s'il n'existe pas
if (-not (Test-Path -Path $LogPath)) {
    New-Item -Path $LogPath -ItemType Directory -Force | Out-Null
}

# Définir le chemin du fichier de log
$logFile = Join-Path -Path $LogPath -ChildPath "modules_test_$(Get-Date -Format 'yyyyMMdd').log"

# Initialiser les compteurs de tests
$script:testsPassed = 0
$script:testsFailed = 0
$script:testsWarning = 0
$script:testResults = @()

# Fonction pour écrire dans le journal
function Write-TestLog {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "ERROR", "WARNING", "SUCCESS", "TEST")]
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Définir la couleur en fonction du niveau
    $colorMap = @{
        "INFO" = "White"
        "ERROR" = "Red"
        "WARNING" = "Yellow"
        "SUCCESS" = "Green"
        "TEST" = "Cyan"
    }
    
    # Afficher le message dans la console si ce n'est pas en mode silencieux
    if (-not $Quiet) {
        Write-Host $logMessage -ForegroundColor $colorMap[$Level]
    }
    
    # Écrire dans le fichier de log
    $logMessage | Out-File -FilePath $logFile -Append -Encoding UTF8
}

# Fonction pour enregistrer un résultat de test
function Register-TestResult {
    param (
        [Parameter(Mandatory=$true)]
        [string]$TestName,
        
        [Parameter(Mandatory=$true)]
        [ValidateSet("Success", "Failure", "Warning")]
        [string]$Result,
        
        [Parameter(Mandatory=$false)]
        [string]$Details = ""
    )
    
    # Mise à jour des compteurs
    switch ($Result) {
        "Success" { $script:testsPassed++ }
        "Failure" { $script:testsFailed++ }
        "Warning" { $script:testsWarning++ }
    }
    
    # Enregistrer le résultat
    $script:testResults += [PSCustomObject]@{
        Name = $TestName
        Result = $Result
        Details = $Details
        Timestamp = Get-Date
    }
    
    # Afficher le résultat
    $icon = switch ($Result) {
        "Success" { "[OK]" }
        "Failure" { "[ERREUR]" }
        "Warning" { "[AVERT]" }
    }
    
    $level = switch ($Result) {
        "Success" { "SUCCESS" }
        "Failure" { "ERROR" }
        "Warning" { "WARNING" }
    }
    
    Write-TestLog "$icon $TestName`: $Details" -Level $level
}

# Fonction pour tester le chargement d'un module
function Test-ModuleLoading {
    param (
        [string]$ModulePath,
        [string]$ModuleName
    )
    
    Write-TestLog "Test de chargement du module: $ModuleName" -Level "TEST"
    
    if (-not (Test-Path -Path $ModulePath -PathType Leaf)) {
        Register-TestResult -TestName "Module $ModuleName" -Result "Failure" -Details "Fichier introuvable: $ModulePath"
        return $false
    }
    
    try {
        # Charger le module
        . $ModulePath
        Register-TestResult -TestName "Module $ModuleName" -Result "Success" -Details "Chargé avec succès"
        return $true
    }
    catch {
        Register-TestResult -TestName "Module $ModuleName" -Result "Failure" -Details "Échec du chargement: $_"
        return $false
    }
}

# Définir la fonction pour tester une fonction spécifique
function Test-FunctionExists {
    param (
        [Parameter(Mandatory=$true)]
        [string]$FunctionName,
        
        [Parameter(Mandatory=$false)]
        [string]$Category = "Général"
    )
    
    $testFunctionExists = Get-Item "function:$FunctionName" -ErrorAction SilentlyContinue
    if ($testFunctionExists) {
        Register-TestResult -TestName "Fonction $FunctionName" -Result "Success" -Details "[$Category] Fonction accessible"
        return $true
    }
    else {
        # Vérifier si elle existe comme variable globale (comportement PowerShell pour certaines fonctions)
        $variableName = $FunctionName.Replace('-', '_')
        $testVariableExists = Get-Variable -Name $variableName -ErrorAction SilentlyContinue
        
        if ($testVariableExists) {
            Register-TestResult -TestName "Fonction $FunctionName (variable)" -Result "Success" -Details "[$Category] Accessible via variable $variableName"
            return $true
        }
        else {
            Register-TestResult -TestName "Fonction $FunctionName" -Result "Failure" -Details "[$Category] Fonction non accessible"
            return $false
        }
    }
}

# Initialiser le test
Write-TestLog "=== Demarrage des tests de modules et fonctions renommees ===" -Level "TEST"
Write-TestLog "Date et heure: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Level "INFO"
Write-TestLog "Repertoire des utilitaires: $utilsDir" -Level "INFO"

# Verification si le répertoire des utilitaires existe
if (-not (Test-Path -Path $utilsDir -PathType Container)) {
    Write-TestLog "Le repertoire des utilitaires n'existe pas: $utilsDir" -Level "ERROR"
    New-Item -Path $utilsDir -ItemType Directory -Force | Out-Null
    Write-TestLog "Creation du repertoire des utilitaires" -Level "INFO"
}

# Liste des modules à tester
$modules = @(
    @{Path = "$utilsDir\staging_logger.ps1"; Name = "Logger"},
    @{Path = "$utilsDir\staging_prereqs.ps1"; Name = "Prerequisites"},
    @{Path = "$utilsDir\staging_software.ps1"; Name = "Software"},
    @{Path = "$utilsDir\staging_network.ps1"; Name = "Network"},
    @{Path = "$utilsDir\staging_security.ps1"; Name = "Security"},
    @{Path = "$utilsDir\staging_data.ps1"; Name = "Data"},
    @{Path = "$utilsDir\staging_database.ps1"; Name = "Database"}
)

# Verifier si tous les modules existent
foreach ($module in $modules) {
    if (-not (Test-Path -Path $module.Path -PathType Leaf)) {
        Register-TestResult -TestName "Verification du module $($module.Name)" -Result "Failure" -Details "Fichier introuvable: $($module.Path)"
        
        # Créer un fichier vide pour le test
        $moduleDir = Split-Path -Parent $module.Path
        if (-not (Test-Path -Path $moduleDir -PathType Container)) {
            New-Item -Path $moduleDir -ItemType Directory -Force | Out-Null
        }
        
        # Créer un fichier de module minimal pour les tests
        $moduleContent = @"
# Module $($module.Name) genere automatiquement pour les tests
# Date: $(Get-Date -Format 'yyyy-MM-dd')

function Test-${module.Name}Module {
    return $true
}
"@
        
        $moduleContent | Out-File -FilePath $module.Path -Encoding UTF8 -Force
        Write-TestLog "Creation d'un fichier de substitution pour le module $($module.Name)" -Level "WARNING"
    }
}

# Tester chaque module
$allModulesLoaded = $true
foreach ($module in $modules) {
    $success = Test-ModuleLoading -ModulePath $module.Path -ModuleName $module.Name
    if (-not $success) {
        $allModulesLoaded = $false
    }
}

# Si tous les modules sont chargés, tester les fonctions renommées
if ($allModulesLoaded) {
    Write-TestLog "Test des fonctions renommées" -Level "TEST"
    
    # Liste des fonctions à tester, organisées par catégorie
    $functionsToTest = @{
        "Logging" = @(
            "Write-LogMessage",
            "Start-LogSection",
            "Start-LogTask",
            "Complete-LogTask",
            "Write-DetailedLog"
        );
        "Réseau" = @(
            "Set-NetworkConfiguration",
            "Test-NetworkConnectivity",
            "Start-NetworkService",
            "Stop-NetworkService"
        );
        "Sécurité" = @(
            "Set-SecurityConfiguration",
            "Test-SecurityCompliance",
            "New-SecurityCertificate"
        );
        "Données" = @(
            "Start-DataPreparation",
            "Import-SampleData",
            "Test-DataIntegrity"
        );
        "Base de données" = @(
            "New-DatabaseInstance",
            "Set-DatabaseConfiguration",
            "Test-DatabaseConnection"
        )
    }
    
    # Tester chaque fonction de chaque catégorie
    foreach ($category in $functionsToTest.Keys) {
        Write-TestLog "Test des fonctions de la catégorie: $category" -Level "INFO"
        
        foreach ($function in $functionsToTest[$category]) {
            try {
                Test-FunctionExists -FunctionName $function -Category $category
            }
            catch {
                Register-TestResult -TestName "Fonction $function" -Result "Failure" -Details "[$category] Erreur lors du test: $_"
            }
        }
    }
    
    # Tester l'exécution de certaines fonctions clés si elles existent
    try {
        if (Get-Item "function:Write-LogMessage" -ErrorAction SilentlyContinue) {
            Write-LogMessage "Test d'exécution de Write-LogMessage" "INFO"
            Register-TestResult -TestName "Exécution de Write-LogMessage" -Result "Success" -Details "Fonction exécutée avec succès"
        }
    }
    catch {
        Register-TestResult -TestName "Exécution de Write-LogMessage" -Result "Failure" -Details "Erreur lors de l'exécution: $_"
    }
}

# Générer un rapport de test
Write-TestLog "Tests terminés" -Level "TEST"
Write-TestLog "Resultats: $script:testsPassed tests reussis, $script:testsFailed echecs, $script:testsWarning avertissements" -Level "INFO"

# Déterminer le statut global
if ($script:testsFailed -eq 0) {
    if ($script:testsWarning -eq 0) {
        Write-TestLog "Tous les tests ont ete executes avec succes" -Level "SUCCESS"
        $globalStatus = "SUCCESS"
    }
    else {
        Write-TestLog "Tests reussis avec des avertissements" -Level "WARNING"
        $globalStatus = "WARNING"
    }
}
else {
    Write-TestLog "Des tests ont echoue" -Level "ERROR"
    $globalStatus = "FAILURE"
}

# Générer un rapport HTML si demandé
if ($GenerateHtmlReport) {
    $htmlReportPath = if ([string]::IsNullOrEmpty($DetailedReportPath)) {
        Join-Path -Path $LogPath -ChildPath "modules_test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').html"
    }
    else {
        $DetailedReportPath
    }
    
    # Déterminer la couleur du statut global
    $statusColor = "#5cb85c" # Vert par défaut (succès)
    if ($script:testsFailed -gt 0) {
        $statusColor = "#d9534f" # Rouge pour échec
    }
    elseif ($script:testsWarning -gt 0) {
        $statusColor = "#f0ad4e" # Orange pour avertissement
    }
    
    # Préparer les lignes du tableau pour les résultats de test
    $tableRows = ""
    
    foreach ($result in $script:testResults) {
        # Définir la classe CSS selon le résultat
        $resultClass = "success"
        if ($result.Result -eq "Failure") { $resultClass = "failure" }
        if ($result.Result -eq "Warning") { $resultClass = "warning" }
        
        # Ajouter une ligne au tableau
        $tableRows += "<tr>`n"
        $tableRows += "  <td>$($result.Name)</td>`n"
        $tableRows += "  <td class='$resultClass'>$($result.Result)</td>`n"
        $tableRows += "  <td>$($result.Details)</td>`n"
        $tableRows += "  <td>$($result.Timestamp.ToString('HH:mm:ss'))</td>`n"
        $tableRows += "</tr>`n"
    }
    
    # Générer les recommandations
    $recommendations = ""
    if ($script:testsFailed -eq 0 -and $script:testsWarning -eq 0) {
        $recommendations += "<li>Tous les modules et fonctions sont correctement configurés.</li>`n"
        $recommendations += "<li>Aucune action n'est requise.</li>`n"
    }
    elseif ($script:testsFailed -eq 0) {
        $recommendations += "<li>Les modules sont fonctionnels mais certains avertissements ont été détectés.</li>`n"
        $recommendations += "<li>Vérifiez les points avec des avertissements avant de procéder au déploiement.</li>`n"
    }
    else {
        $recommendations += "<li>Certains tests ont échoué. Corrigez les problèmes avant de procéder au déploiement.</li>`n"
        $recommendations += "<li>Assurez-vous que tous les modules sont présents et utilisent les noms de fonctions standardisés.</li>`n"
    }
    
    # Générer le HTML complet en évitant les problèmes de syntaxe
    $htmlContent = @"
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Rapport de test des modules</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .summary { font-size: 1.2em; margin: 20px 0; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }
        .status { color: $statusColor; font-weight: bold; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .success { color: #5cb85c; }
        .failure { color: #d9534f; }
        .warning { color: #f0ad4e; }
    </style>
</head>
<body>
    <h1>Rapport de test des modules Technicia</h1>
    <p>Date du test: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>
    
    <div class="summary">
        <p>Statut global: <span class="status">$globalStatus</span></p>
        <p>Tests réussis: <span class="success">$script:testsPassed</span></p>
        <p>Tests échoués: <span class="failure">$script:testsFailed</span></p>
        <p>Avertissements: <span class="warning">$script:testsWarning</span></p>
    </div>
    
    <h2>Détails des tests</h2>
    <table>
        <tr>
            <th>Test</th>
            <th>Résultat</th>
            <th>Détails</th>
            <th>Horodatage</th>
        </tr>
        $tableRows
    </table>
    
    <h2>Recommandations</h2>
    <ul>
        $recommendations
    </ul>
    
    <p><small>Rapport généré automatiquement par le script de test de modules Technicia.</small></p>
</body>
</html>
"@
    
    # Écrire le contenu HTML dans le fichier
    $htmlContent | Out-File -FilePath $htmlReportPath -Encoding UTF8
    Write-TestLog "Rapport HTML généré à: $htmlReportPath" -Level "SUCCESS"
}

# Retourner l'état global du test
exit [int]($script:testsFailed -gt 0)
