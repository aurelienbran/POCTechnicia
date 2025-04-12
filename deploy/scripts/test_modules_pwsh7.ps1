# Script de test optimise pour PowerShell 7
# Prend en charge l'encodage UTF-8 nativement et gere les caracteres speciaux
# Version 1.0 - 2025-04-10

param(
    [string]$LogPath = "",
    [string]$ReportPath = "",
    [switch]$GenerateReport
)

# Forcer l'encodage UTF-8 sans BOM
if ($PSVersionTable.PSVersion.Major -ge 7) {
    # Ceci est uniquement disponible dans PowerShell 7+
    $PSDefaultParameterValues['Out-File:Encoding'] = 'utf8NoBOM'
    $PSDefaultParameterValues['*:Encoding'] = 'utf8NoBOM'
} else {
    Write-Warning "Ce script est optimise pour PowerShell 7+. L'affichage des caracteres accentues peut être altere."
}

# Chemins
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

# Logs
if (-not $LogPath) { $LogPath = Join-Path -Path $scriptDir -ChildPath "logs" }
$logFileName = "module_test_$(Get-Date -Format 'yyyyMMdd').log"
$logFile = Join-Path -Path $LogPath -ChildPath $logFileName

# Creer le dossier de logs
if (-not (Test-Path -Path $LogPath -PathType Container)) {
    New-Item -Path $LogPath -ItemType Directory -Force | Out-Null
}

# Fonction de journalisation
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Console
    $color = switch ($Level) {
        "ERROR"   { "Red" }
        "WARNING" { "Yellow" }
        "SUCCESS" { "Green" }
        default   { "White" }
    }
    Write-Host $logMessage -ForegroundColor $color
    
    # Fichier
    Add-Content -Path $logFile -Value $logMessage
}

# Compteurs
$script:testsPassed = 0
$script:testsFailed = 0
$script:testsWarning = 0
$script:testResults = @()

# Enregistrement des resultats
function Register-TestResult {
    param(
        [string]$TestName,
        [string]$Result,
        [string]$Details = ""
    )
    
    switch ($Result) {
        "Success" { $script:testsPassed++ }
        "Failure" { $script:testsFailed++ }
        "Warning" { $script:testsWarning++ }
    }
    
    $resultObj = [PSCustomObject]@{
        Name = $TestName
        Result = $Result
        Details = $Details
        Time = Get-Date
    }
    
    $script:testResults += $resultObj
    
    $prefix = switch ($Result) {
        "Success" { "[OK]" }
        "Failure" { "[ECHEC]" }
        "Warning" { "[AVERT]" }
    }
    
    $level = switch ($Result) {
        "Success" { "SUCCESS" }
        "Failure" { "ERROR" }
        "Warning" { "WARNING" }
    }
    
    Write-Log -Message "$prefix $TestName : $Details" -Level $level
}

# Test des modules
function Test-Module {
    param(
        [string]$ModulePath,
        [string]$ModuleName
    )
    
    Write-Log -Message "Test du module: $ModuleName" -Level "INFO"
    
    if (-not (Test-Path -Path $ModulePath -PathType Leaf)) {
        Register-TestResult -TestName "Module $ModuleName" -Result "Failure" -Details "Fichier introuvable: $ModulePath"
        
        try {
            # Créer un module de substitution
            $moduleDir = Split-Path -Parent $ModulePath
            if (-not (Test-Path -Path $moduleDir -PathType Container)) {
                New-Item -Path $moduleDir -ItemType Directory -Force | Out-Null
            }
            
            $moduleContent = @"
# Module $ModuleName (automatique)
# Date: $(Get-Date -Format 'yyyy-MM-dd')

function Test-${ModuleName}Module {
    return `$true
}
"@
            
            Set-Content -Path $ModulePath -Value $moduleContent
            Register-TestResult -TestName "Creation auto du module $ModuleName" -Result "Warning" -Details "Module de substitution cree"
        }
        catch {
            Register-TestResult -TestName "Creation du module $ModuleName" -Result "Failure" -Details "Erreur: $_"
            return $false
        }
    }
    
    try {
        # Dot sourcing
        . $ModulePath
        Register-TestResult -TestName "Chargement du module $ModuleName" -Result "Success" -Details "Module charge"
        return $true
    }
    catch {
        Register-TestResult -TestName "Chargement du module $ModuleName" -Result "Failure" -Details "Erreur: $_"
        return $false
    }
}

# Test des fonctions
function Test-Function {
    param(
        [string]$FunctionName,
        [string]$Category = "General"
    )
    
    try {
        $exists = Get-Command -Name $FunctionName -ErrorAction SilentlyContinue
        if ($exists) {
            Register-TestResult -TestName "Fonction $FunctionName" -Result "Success" -Details "[$Category] Disponible"
            return $true
        }
        else {
            Register-TestResult -TestName "Fonction $FunctionName" -Result "Failure" -Details "[$Category] Non disponible"
            return $false
        }
    }
    catch {
        Register-TestResult -TestName "Fonction $FunctionName" -Result "Failure" -Details "[$Category] Erreur: $_"
        return $false
    }
}

# Création du rapport HTML basique
function Create-BasicReport {
    param(
        [string]$ReportFilePath,
        [string]$Status,
        [int]$Passed,
        [int]$Failed,
        [int]$Warnings
    )
    
    # Construction du rapport HTML item par item
    $reportLines = [System.Collections.ArrayList]::new()
    [void]$reportLines.Add("<!DOCTYPE html>")
    [void]$reportLines.Add("<html>")
    [void]$reportLines.Add("<head>")
    [void]$reportLines.Add("  <meta charset='UTF-8'>")
    [void]$reportLines.Add("  <title>Rapport de test des modules</title>")
    [void]$reportLines.Add("  <style>")
    [void]$reportLines.Add("    body { font-family: Arial, sans-serif; margin: 20px; }")
    [void]$reportLines.Add("    .success { color: green; }")
    [void]$reportLines.Add("    .failure { color: red; }")
    [void]$reportLines.Add("    .warning { color: orange; }")
    [void]$reportLines.Add("    table { border-collapse: collapse; width: 100%; }")
    [void]$reportLines.Add("    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
    [void]$reportLines.Add("    th { background-color: #f2f2f2; }")
    [void]$reportLines.Add("  </style>")
    [void]$reportLines.Add("</head>")
    [void]$reportLines.Add("<body>")
    [void]$reportLines.Add("  <h1>Rapport de test des modules</h1>")
    [void]$reportLines.Add("  <p>Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>")
    [void]$reportLines.Add("  <h2>Résumé</h2>")
    
    # Résumé
    [void]$reportLines.Add("  <p>Tests réussis: <span class='success'>$Passed</span></p>")
    [void]$reportLines.Add("  <p>Tests échoués: <span class='failure'>$Failed</span></p>")
    [void]$reportLines.Add("  <p>Avertissements: <span class='warning'>$Warnings</span></p>")
    
    # Statut
    $statusClass = switch ($Status) {
        "SUCCESS" { "success" }
        "WARNING" { "warning" }
        "FAILURE" { "failure" }
    }
    [void]$reportLines.Add("  <p>Statut global: <span class='$statusClass'>$Status</span></p>")
    
    # Tableau des résultats
    [void]$reportLines.Add("  <h2>Détails des tests</h2>")
    [void]$reportLines.Add("  <table>")
    [void]$reportLines.Add("    <tr>")
    [void]$reportLines.Add("      <th>Test</th>")
    [void]$reportLines.Add("      <th>Résultat</th>")
    [void]$reportLines.Add("      <th>Détails</th>")
    [void]$reportLines.Add("      <th>Heure</th>")
    [void]$reportLines.Add("    </tr>")
    
    # Lignes de résultats
    foreach ($result in $script:testResults) {
        $resultClass = switch ($result.Result) {
            "Success" { "success" }
            "Failure" { "failure" }
            "Warning" { "warning" }
        }
        
        # Échapper les caractères HTML
        $escapedName = $result.Name -replace '<', '&lt;' -replace '>', '&gt;'
        $escapedDetails = $result.Details -replace '<', '&lt;' -replace '>', '&gt;'
        
        [void]$reportLines.Add("    <tr>")
        [void]$reportLines.Add("      <td>$escapedName</td>")
        [void]$reportLines.Add("      <td class='$resultClass'>$($result.Result)</td>")
        [void]$reportLines.Add("      <td>$escapedDetails</td>")
        [void]$reportLines.Add("      <td>$($result.Time.ToString('HH:mm:ss'))</td>")
        [void]$reportLines.Add("    </tr>")
    }
    
    [void]$reportLines.Add("  </table>")
    
    # Recommandations
    [void]$reportLines.Add("  <h2>Recommandations</h2>")
    [void]$reportLines.Add("  <ul>")
    
    if ($Failed -eq 0 -and $Warnings -eq 0) {
        [void]$reportLines.Add("    <li>Tous les modules sont correctement configurés.</li>")
        [void]$reportLines.Add("    <li>Aucune action n'est requise.</li>")
    }
    elseif ($Failed -eq 0) {
        [void]$reportLines.Add("    <li>Les modules sont fonctionnels mais il y a des avertissements.</li>")
        [void]$reportLines.Add("    <li>Vérifiez les avertissements avant de continuer.</li>")
    }
    else {
        [void]$reportLines.Add("    <li>Des problèmes ont été détectés. Correction nécessaire.</li>")
        [void]$reportLines.Add("    <li>Vérifiez que tous les modules requis sont présents.</li>")
    }
    
    [void]$reportLines.Add("  </ul>")
    [void]$reportLines.Add("  <p><small>Rapport généré automatiquement</small></p>")
    [void]$reportLines.Add("</body>")
    [void]$reportLines.Add("</html>")
    
    # Écrire le rapport ligne par ligne
    try {
        $reportDir = Split-Path -Parent $ReportFilePath
        if (-not (Test-Path -Path $reportDir -PathType Container)) {
            New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
        }
        
        $reportLines | Set-Content -Path $ReportFilePath
        Write-Log -Message "Rapport généré: $ReportFilePath" -Level "SUCCESS"
        return $true
    }
    catch {
        Write-Log -Message "Erreur lors de la génération du rapport: $_" -Level "ERROR"
        return $false
    }
}

# Programme principal
Write-Log -Message "=== Démarrage des tests de modules ===" -Level "INFO"

# Répertoire des modules
$utilsDir = Join-Path -Path $scriptDir -ChildPath "utils"
Write-Log -Message "Répertoire des modules: $utilsDir" -Level "INFO"

# Liste des modules
$modulesToTest = @(
    @{Path = "$utilsDir\staging_logger.ps1"; Name = "Logger"},
    @{Path = "$utilsDir\staging_prereqs.ps1"; Name = "Prerequisites"},
    @{Path = "$utilsDir\staging_software.ps1"; Name = "Software"},
    @{Path = "$utilsDir\staging_network.ps1"; Name = "Network"},
    @{Path = "$utilsDir\staging_security.ps1"; Name = "Security"},
    @{Path = "$utilsDir\staging_data.ps1"; Name = "Data"},
    @{Path = "$utilsDir\staging_database.ps1"; Name = "Database"}
)

# Test des modules
$allModulesLoaded = $true
foreach ($module in $modulesToTest) {
    $success = Test-Module -ModulePath $module.Path -ModuleName $module.Name
    if (-not $success) {
        $allModulesLoaded = $false
    }
}

# Test des fonctions
if ($allModulesLoaded) {
    Write-Log -Message "Test des fonctions..." -Level "INFO"
    
    $functionsToTest = @{
        "Journalisation" = @(
            "Write-LogMessage",
            "Start-LogSection"
        );
        "Réseau" = @(
            "Test-NetworkConnectivity",
            "Set-NetworkConfiguration"
        );
        "Sécurité" = @(
            "Test-SecurityCompliance",
            "Set-SecurityConfiguration"
        );
        "Données" = @(
            "Import-SampleData",
            "Test-DataIntegrity"
        )
    }
    
    foreach ($category in $functionsToTest.Keys) {
        foreach ($function in $functionsToTest[$category]) {
            Test-Function -FunctionName $function -Category $category
        }
    }
}

# Déterminer le statut global
$globalStatus = if ($script:testsFailed -eq 0) {
    if ($script:testsWarning -eq 0) { "SUCCESS" } else { "WARNING" }
} else {
    "FAILURE"
}

# Résumé
Write-Log -Message "=== Tests terminés ===" -Level "INFO"
Write-Log -Message "Résultats: $script:testsPassed réussis, $script:testsFailed échoués, $script:testsWarning avertissements" -Level "INFO"
Write-Log -Message "Statut global: $globalStatus" -Level "INFO"

# Générer le rapport
if ($GenerateReport) {
    if (-not $ReportPath) {
        $ReportPath = Join-Path -Path $LogPath -ChildPath "module_test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').html"
    }
    
    Create-BasicReport -ReportFilePath $ReportPath -Status $globalStatus -Passed $script:testsPassed -Failed $script:testsFailed -Warnings $script:testsWarning
}

# Retourner le résultat
exit ([int]($globalStatus -eq "FAILURE"))
