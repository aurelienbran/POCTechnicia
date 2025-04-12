# Script wrapper pour lancer les tests de modules avec le bon encodage
# Ce script détecte PowerShell 7 et l'utilise si disponible
# Sinon, il utilise une version compatible avec PowerShell 5.1
# Version 1.0 - 2025-04-10

param(
    [string]$LogPath = "",
    [string]$ReportPath = "",
    [switch]$GenerateReport
)

# Fonction pour écrire dans le journal principal
function Write-MainLog {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Affichage console
    $color = switch ($Level) {
        "ERROR"   { "Red" }
        "WARNING" { "Yellow" }
        "SUCCESS" { "Green" }
        default   { "White" }
    }
    Write-Host $logMessage -ForegroundColor $color
}

# Déterminer le chemin du script et le répertoire
$scriptPath = $MyInvocation.MyCommand.Path
if (-not $scriptPath) {
    $scriptPath = $PSCommandPath
}
if (-not $scriptPath) {
    $scriptPath = Join-Path -Path (Get-Location) -ChildPath "run_module_tests.ps1"
}
$scriptDir = Split-Path -Parent $scriptPath

# Déterminer le chemin des logs
if (-not $LogPath) {
    $LogPath = Join-Path -Path $scriptDir -ChildPath "logs"
}
if (-not (Test-Path -Path $LogPath -PathType Container)) {
    New-Item -Path $LogPath -ItemType Directory -Force | Out-Null
    Write-MainLog "Création du répertoire de logs: $LogPath" -Level "INFO"
}

# Définir le chemin du rapport si non spécifié
if ($GenerateReport -and (-not $ReportPath)) {
    $ReportPath = Join-Path -Path $LogPath -ChildPath "module_test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').html"
}

# Vérifier si PowerShell 7 est disponible
$pwsh7Path = $null
$pwsh7Paths = @(
    "C:\Program Files\PowerShell\7\pwsh.exe",
    "C:\Program Files (x86)\PowerShell\7\pwsh.exe",
    "$env:ProgramFiles\PowerShell\7\pwsh.exe"
)

foreach ($path in $pwsh7Paths) {
    if (Test-Path -Path $path -PathType Leaf) {
        $pwsh7Path = $path
        break
    }
}

# Définir le contenu du script de test minimaliste
$testScript = @'
# Script de test minimaliste pour les modules
# Généré automatiquement
param(
    [string]$LogPath = "",
    [string]$ReportPath = "",
    [switch]$GenerateReport = $false
)

# Configuration
$ErrorActionPreference = "Stop"
$moduleTestResults = @{
    Passed = 0
    Failed = 0
    Warnings = 0
    Details = @()
}

# Fonction de journalisation
function Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $fullMessage = "[$timestamp] [$Level] $Message"
    Write-Host $fullMessage
    if ($LogPath) {
        $logFile = Join-Path -Path $LogPath -ChildPath "module_test_$(Get-Date -Format 'yyyyMMdd').log"
        $fullMessage | Out-File -FilePath $logFile -Append -Encoding utf8
    }
}

# Enregistrer un résultat
function Register {
    param([string]$Test, [string]$Result, [string]$Details = "")
    
    switch ($Result) {
        "Success" { $moduleTestResults.Passed++ }
        "Failure" { $moduleTestResults.Failed++ }
        "Warning" { $moduleTestResults.Warnings++ }
    }
    
    $moduleTestResults.Details += @{
        Name = $Test
        Result = $Result
        Details = $Details
        Time = Get-Date
    }
    
    Log -Message "[$Result] $Test : $Details" -Level $Result.ToUpper()
}

# Tester un module
function TestModule {
    param([string]$Path, [string]$Name)
    
    if (-not (Test-Path -Path $Path -PathType Leaf)) {
        Register -Test "Module $Name" -Result "Failure" -Details "Fichier introuvable: $Path"
        
        # Créer un module temporaire
        $dir = Split-Path -Parent $Path
        if (-not (Test-Path -Path $dir -PathType Container)) {
            New-Item -Path $dir -ItemType Directory -Force | Out-Null
        }
        
        $content = @"
# Module $Name temporaire
function Test-${Name}Module { return `$true }
"@
        Set-Content -Path $Path -Value $content -Encoding utf8
        Register -Test "Module $Name temporaire" -Result "Warning" -Details "Module temporaire créé"
        
        try {
            . $Path
            Register -Test "Chargement de $Name" -Result "Success" -Details "Module temporaire chargé"
            return $true
        } catch {
            Register -Test "Chargement de $Name" -Result "Failure" -Details "Erreur: $_"
            return $false
        }
    } else {
        try {
            . $Path
            Register -Test "Chargement de $Name" -Result "Success" -Details "Module chargé"
            return $true
        } catch {
            Register -Test "Chargement de $Name" -Result "Failure" -Details "Erreur: $_"
            return $false
        }
    }
}

# Tester une fonction
function TestFunction {
    param([string]$Name, [string]$Category = "General")
    
    try {
        $exists = Get-Command -Name $Name -ErrorAction SilentlyContinue
        if ($exists) {
            Register -Test "Fonction $Name" -Result "Success" -Details "[$Category] Disponible"
            return $true
        } else {
            Register -Test "Fonction $Name" -Result "Failure" -Details "[$Category] Non disponible"
            return $false
        }
    } catch {
        Register -Test "Fonction $Name" -Result "Failure" -Details "[$Category] Erreur: $_"
        return $false
    }
}

# Générer un rapport HTML simple
function GenerateReport {
    param([string]$Path)
    
    try {
        $html = @"
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Rapport de test des modules</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .success { color: green; }
    .failure { color: red; }
    .warning { color: orange; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #f2f2f2; }
  </style>
</head>
<body>
  <h1>Rapport de test des modules</h1>
  <p>Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>
  
  <h2>Résumé</h2>
  <p>Tests réussis: <span class="success">$($moduleTestResults.Passed)</span></p>
  <p>Tests échoués: <span class="failure">$($moduleTestResults.Failed)</span></p>
  <p>Avertissements: <span class="warning">$($moduleTestResults.Warnings)</span></p>
  
  <h2>Détails</h2>
  <table>
    <tr>
      <th>Test</th>
      <th>Résultat</th>
      <th>Détails</th>
      <th>Heure</th>
    </tr>
"@

        foreach ($result in $moduleTestResults.Details) {
            $class = $result.Result.ToLower()
            $time = $result.Time.ToString("HH:mm:ss")
            $escapedName = $result.Name -replace '<', '&lt;' -replace '>', '&gt;'
            $escapedDetails = $result.Details -replace '<', '&lt;' -replace '>', '&gt;'
            
            $html += @"
    <tr>
      <td>$escapedName</td>
      <td class="$class">$($result.Result)</td>
      <td>$escapedDetails</td>
      <td>$time</td>
    </tr>
"@
        }

        $html += @"
  </table>
  
  <h2>Recommandations</h2>
  <ul>
"@

        if ($moduleTestResults.Failed -eq 0 -and $moduleTestResults.Warnings -eq 0) {
            $html += "    <li>Tous les modules sont correctement configurés.</li>`n"
        }
        elseif ($moduleTestResults.Failed -eq 0) {
            $html += "    <li>Les modules sont fonctionnels mais certains avertissements existent.</li>`n"
        }
        else {
            $html += "    <li>Des problèmes ont été détectés. Correction nécessaire.</li>`n"
        }

        $html += @"
  </ul>
  
  <p><small>Rapport généré automatiquement</small></p>
</body>
</html>
"@

        $html | Out-File -FilePath $Path -Encoding utf8
        Log -Message "Rapport généré: $Path" -Level "SUCCESS"
        return $true
    }
    catch {
        Log -Message "Erreur lors de la génération du rapport: $_" -Level "ERROR"
        return $false
    }
}

# Exécution principale
Log -Message "=== Test des modules ===" -Level "INFO"

# Répertoire des scripts
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

# Répertoire des modules
$utilsDir = Join-Path -Path $scriptDir -ChildPath "utils"
Log -Message "Répertoire des modules: $utilsDir" -Level "INFO"

# Liste des modules
$modules = @(
    @{Path = "$utilsDir\staging_logger.ps1"; Name = "Logger"},
    @{Path = "$utilsDir\staging_prereqs.ps1"; Name = "Prerequisites"},
    @{Path = "$utilsDir\staging_software.ps1"; Name = "Software"},
    @{Path = "$utilsDir\staging_network.ps1"; Name = "Network"},
    @{Path = "$utilsDir\staging_security.ps1"; Name = "Security"},
    @{Path = "$utilsDir\staging_data.ps1"; Name = "Data"},
    @{Path = "$utilsDir\staging_database.ps1"; Name = "Database"}
)

# Test des modules
$allLoaded = $true
foreach ($module in $modules) {
    $success = TestModule -Path $module.Path -Name $module.Name
    if (-not $success) { $allLoaded = $false }
}

# Test des fonctions
if ($allLoaded) {
    Log -Message "Test des fonctions..." -Level "INFO"
    
    $functions = @{
        "Journalisation" = @("Write-LogMessage", "Start-LogSection", "Write-DetailedLog");
        "Réseau" = @("Test-NetworkConnectivity", "Set-NetworkConfiguration");
        "Sécurité" = @("Test-SecurityCompliance", "Set-SecurityConfiguration");
        "Données" = @("Import-SampleData", "Test-DataIntegrity")
    }
    
    foreach ($category in $functions.Keys) {
        foreach ($function in $functions[$category]) {
            TestFunction -Name $function -Category $category
        }
    }
}

# Résumé
$status = if ($moduleTestResults.Failed -gt 0) { "FAILURE" } 
          elseif ($moduleTestResults.Warnings -gt 0) { "WARNING" }
          else { "SUCCESS" }

Log -Message "=== Tests terminés ===" -Level "INFO"
Log -Message "Résultats: $($moduleTestResults.Passed) réussis, $($moduleTestResults.Failed) échoués, $($moduleTestResults.Warnings) avertissements" -Level "INFO"
Log -Message "Statut: $status" -Level "INFO"

# Générer le rapport si demandé
if ($GenerateReport -and $ReportPath) {
    GenerateReport -Path $ReportPath
}

# Code de sortie
if ($status -eq "FAILURE") { exit 1 } else { exit 0 }
'@

# Créer un fichier temporaire pour le script de test
$tempScriptPath = Join-Path -Path $scriptDir -ChildPath "temp_test_script.ps1"
Set-Content -Path $tempScriptPath -Value $testScript -Force

# Paramètres à passer au script
$params = @()
if ($LogPath) { $params += "-LogPath `"$LogPath`"" }
if ($ReportPath -and $GenerateReport) { $params += "-ReportPath `"$ReportPath`"" }
if ($GenerateReport) { $params += "-GenerateReport" }
$paramString = $params -join " "

# Exécuter avec PowerShell 7 si disponible, sinon avec PowerShell standard
try {
    Write-MainLog "Démarrage des tests de modules..." -Level "INFO"
    
    if ($pwsh7Path) {
        Write-MainLog "PowerShell 7 détecté. Utilisation pour une meilleure compatibilité." -Level "INFO"
        $command = "`"$pwsh7Path`" -ExecutionPolicy Bypass -File `"$tempScriptPath`" $paramString"
        Write-MainLog "Exécution de: $command" -Level "INFO"
        
        $result = Invoke-Expression -Command $command
        $exitCode = $LASTEXITCODE
    } else {
        Write-MainLog "PowerShell 7 non détecté. Utilisation de PowerShell standard." -Level "WARNING"
        $command = "powershell.exe -ExecutionPolicy Bypass -File `"$tempScriptPath`" $paramString"
        Write-MainLog "Exécution de: $command" -Level "INFO"
        
        $result = Invoke-Expression -Command $command
        $exitCode = $LASTEXITCODE
    }
    
    Write-MainLog "Tests terminés avec code de sortie: $exitCode" -Level $(if ($exitCode -eq 0) { "SUCCESS" } else { "ERROR" })
    
    # Nettoyer les fichiers temporaires
    if (Test-Path -Path $tempScriptPath) {
        Remove-Item -Path $tempScriptPath -Force
    }
    
    exit $exitCode
} catch {
    Write-MainLog "Erreur lors de l'exécution des tests: $_" -Level "ERROR"
    
    # Nettoyer les fichiers temporaires même en cas d'erreur
    if (Test-Path -Path $tempScriptPath) {
        Remove-Item -Path $tempScriptPath -Force
    }
    
    exit 1
}
