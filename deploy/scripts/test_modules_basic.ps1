#=========================================================================
# TEST_MODULES_BASIC.PS1
# 
# Description:
#   Script de test simplifie pour verifier les modules de Technicia
#   Ce script utilise uniquement des caracteres ASCII pour eviter 
#   les problemes d'encodage.
#
# Auteur: Support Technique
# Date: 2025-04-10
# Version: 1.0
#
# Parametres:
#   -LogDir : Repertoire pour les fichiers log (optionnel)
#   -ReportDir : Repertoire pour les rapports HTML (optionnel)
#   -NoReport : Ne pas generer de rapport HTML (switch)
#=========================================================================

param(
    [string]$LogDir = "",
    [string]$ReportDir = "",
    [switch]$NoReport
)

#=========================================================================
# CONFIGURATION INITIALE
#=========================================================================

# Fixer l'action en cas d'erreur
$ErrorActionPreference = "Continue"

# Repertoire du script
$scriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($scriptPath)) {
    $scriptPath = Join-Path (Get-Location) "test_modules_basic.ps1"
}
$scriptDir = Split-Path -Parent $scriptPath

# Repertoire des logs
if ([string]::IsNullOrEmpty($LogDir)) {
    $LogDir = Join-Path $scriptDir "logs"
}
if (-not (Test-Path $LogDir -PathType Container)) {
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
}

# Fichier log
$logFile = Join-Path $LogDir "modules_test_$(Get-Date -Format 'yyyyMMdd').log"

# Compteurs pour les statistiques
$global:testsPassed = 0
$global:testsFailed = 0
$global:testsWarning = 0
$global:testResults = @()

#=========================================================================
# FONCTIONS UTILITAIRES
#=========================================================================

<#
.SYNOPSIS
    Ecrit un message dans le journal et la console.

.DESCRIPTION
    Cette fonction ajoute un message horodate dans le fichier journal
    et l'affiche egalement dans la console avec un code couleur
    correspondant au niveau de severite.

.PARAMETER Message
    Le message a journaliser.

.PARAMETER Level
    Le niveau de severite du message (INFO, ERROR, WARNING, SUCCESS).
#>
function Write-Log {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "ERROR", "WARNING", "SUCCESS")]
        [string]$Level = "INFO"
    )
    
    # Format horodate
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $formattedMessage = "[$timestamp] [$Level] $Message"
    
    # Couleur console
    $color = switch ($Level) {
        "ERROR"   { "Red" }
        "WARNING" { "Yellow" }
        "SUCCESS" { "Green" }
        default   { "White" }
    }
    
    # Affichage console
    Write-Host $formattedMessage -ForegroundColor $color
    
    # Ecriture fichier
    try {
        Add-Content -Path $logFile -Value $formattedMessage
    }
    catch {
        Write-Host "Erreur d'ecriture dans le fichier journal: $_" -ForegroundColor Red
    }
}

<#
.SYNOPSIS
    Enregistre le resultat d'un test.

.DESCRIPTION
    Cette fonction enregistre le resultat d'un test, met a jour les
    compteurs et journalise le resultat.

.PARAMETER TestName
    Le nom du test.

.PARAMETER Result
    Le resultat du test (Success, Failure, Warning).

.PARAMETER Details
    Les details complementaires du test.
#>
function Register-TestResult {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$TestName,
        
        [Parameter(Mandatory=$true)]
        [ValidateSet("Success", "Failure", "Warning")]
        [string]$Result,
        
        [Parameter(Mandatory=$false)]
        [string]$Details = ""
    )
    
    # Mettre a jour les compteurs
    switch ($Result) {
        "Success" { $global:testsPassed++ }
        "Failure" { $global:testsFailed++ }
        "Warning" { $global:testsWarning++ }
    }
    
    # Creer l'objet de resultat
    $resultObject = [PSCustomObject]@{
        Name = $TestName
        Result = $Result
        Details = $Details
        Time = Get-Date
    }
    
    # Ajouter au tableau global
    $global:testResults += $resultObject
    
    # Symbole pour le log
    $symbol = switch ($Result) {
        "Success" { "[OK]" }
        "Failure" { "[ECHEC]" }
        "Warning" { "[AVERT]" }
    }
    
    # Niveau de log
    $logLevel = switch ($Result) {
        "Success" { "SUCCESS" }
        "Failure" { "ERROR" }
        "Warning" { "WARNING" }
    }
    
    # Journaliser le resultat
    Write-Log -Message "$symbol $TestName : $Details" -Level $logLevel
}

#=========================================================================
# FONCTIONS DE TEST
#=========================================================================

<#
.SYNOPSIS
    Teste le chargement d'un module.

.DESCRIPTION
    Cette fonction verifie si un module existe, le cree si necessaire,
    puis tente de le charger.

.PARAMETER ModulePath
    Le chemin complet vers le fichier du module.

.PARAMETER ModuleName
    Le nom du module.

.RETURNS
    True si le module est charge avec succes, False sinon.
#>
function Test-ModuleLoading {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$ModulePath,
        
        [Parameter(Mandatory=$true)]
        [string]$ModuleName
    )
    
    Write-Log -Message "Test du module: $ModuleName" -Level "INFO"
    
    # Verifier si le fichier existe
    if (-not (Test-Path -Path $ModulePath -PathType Leaf)) {
        Register-TestResult -TestName "Module $ModuleName" -Result "Failure" -Details "Fichier introuvable: $ModulePath"
        
        try {
            # Creer le repertoire parent si necessaire
            $moduleDir = Split-Path -Parent $ModulePath
            if (-not (Test-Path -Path $moduleDir -PathType Container)) {
                New-Item -Path $moduleDir -ItemType Directory -Force | Out-Null
            }
            
            # Creer un fichier module minimal
            $moduleContent = @"
# Module $ModuleName (genere automatiquement)
# Date: $(Get-Date -Format 'yyyy-MM-dd')

function Test-${ModuleName}Module {
    return `$true
}
"@
            
            # Ecrire le contenu
            Set-Content -Path $ModulePath -Value $moduleContent
            Register-TestResult -TestName "Creation du module $ModuleName" -Result "Warning" -Details "Module temporaire cree pour les tests"
        }
        catch {
            Register-TestResult -TestName "Creation du module $ModuleName" -Result "Failure" -Details "Erreur: $_"
            return $false
        }
    }
    
    # Tenter de charger le module
    try {
        . $ModulePath
        Register-TestResult -TestName "Chargement du module $ModuleName" -Result "Success" -Details "Module charge avec succes"
        return $true
    }
    catch {
        Register-TestResult -TestName "Chargement du module $ModuleName" -Result "Failure" -Details "Erreur: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Teste si une fonction est disponible.

.DESCRIPTION
    Cette fonction verifie si une fonction specifique est accessible
    dans la session PowerShell actuelle.

.PARAMETER FunctionName
    Le nom de la fonction a tester.

.PARAMETER Category
    La categorie de la fonction.

.RETURNS
    True si la fonction existe, False sinon.
#>
function Test-FunctionExists {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$FunctionName,
        
        [Parameter(Mandatory=$false)]
        [string]$Category = "General"
    )
    
    # Tester l'existence de la fonction
    try {
        $exists = Get-Command -Name $FunctionName -ErrorAction SilentlyContinue
        if ($exists) {
            Register-TestResult -TestName "Fonction $FunctionName" -Result "Success" -Details "[$Category] Fonction disponible"
            return $true
        }
        else {
            Register-TestResult -TestName "Fonction $FunctionName" -Result "Failure" -Details "[$Category] Fonction non disponible"
            return $false
        }
    }
    catch {
        Register-TestResult -TestName "Fonction $FunctionName" -Result "Failure" -Details "[$Category] Erreur: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Genere un rapport HTML des resultats de test.

.DESCRIPTION
    Cette fonction cree un fichier HTML contenant un resume
    des resultats de test et des recommandations.

.PARAMETER ReportPath
    Le chemin complet du fichier HTML a generer.
#>
function New-TestReport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$ReportPath
    )
    
    # Verifier l'existence du repertoire
    $reportDir = Split-Path -Parent $ReportPath
    if (-not (Test-Path -Path $reportDir -PathType Container)) {
        New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
    }
    
    try {
        # Determiner le statut global
        $globalStatus = if ($global:testsFailed -eq 0) {
            if ($global:testsWarning -eq 0) { "SUCCESS" } else { "WARNING" }
        } else {
            "FAILURE"
        }
        
        # Classe CSS pour le statut
        $statusClass = switch ($globalStatus) {
            "SUCCESS" { "success" }
            "WARNING" { "warning" }
            "FAILURE" { "failure" }
        }
        
        # Creer le HTML ligne par ligne
        $html = @()
        $html += "<!DOCTYPE html>"
        $html += "<html>"
        $html += "<head>"
        $html += "  <meta charset='UTF-8'>"
        $html += "  <title>Rapport de test des modules</title>"
        $html += "  <style>"
        $html += "    body { font-family: Arial, sans-serif; margin: 20px; }"
        $html += "    .success { color: green; }"
        $html += "    .failure { color: red; }"
        $html += "    .warning { color: orange; }"
        $html += "    table { border-collapse: collapse; width: 100%; margin: 20px 0; }"
        $html += "    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }"
        $html += "    th { background-color: #f2f2f2; }"
        $html += "  </style>"
        $html += "</head>"
        $html += "<body>"
        $html += "  <h1>Rapport de test des modules</h1>"
        $html += "  <p>Date du test: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>"
        
        # Resume
        $html += "  <h2>Resume</h2>"
        $html += "  <p>Tests reussis: <span class='success'>$global:testsPassed</span></p>"
        $html += "  <p>Tests echoues: <span class='failure'>$global:testsFailed</span></p>"
        $html += "  <p>Avertissements: <span class='warning'>$global:testsWarning</span></p>"
        $html += "  <p>Statut global: <span class='$statusClass'>$globalStatus</span></p>"
        
        # Tableau des resultats
        $html += "  <h2>Details des tests</h2>"
        $html += "  <table>"
        $html += "    <tr>"
        $html += "      <th>Test</th>"
        $html += "      <th>Resultat</th>"
        $html += "      <th>Details</th>"
        $html += "      <th>Heure</th>"
        $html += "    </tr>"
        
        # Lignes du tableau
        foreach ($result in $global:testResults) {
            $resultClass = $result.Result.ToLower()
            $resultTime = $result.Time.ToString("HH:mm:ss")
            
            # Echapper les caracteres speciaux HTML
            $escapedName = $result.Name -replace '<', '&lt;' -replace '>', '&gt;'
            $escapedDetails = $result.Details -replace '<', '&lt;' -replace '>', '&gt;'
            
            $html += "    <tr>"
            $html += "      <td>$escapedName</td>"
            $html += "      <td class='$resultClass'>$($result.Result)</td>"
            $html += "      <td>$escapedDetails</td>"
            $html += "      <td>$resultTime</td>"
            $html += "    </tr>"
        }
        
        $html += "  </table>"
        
        # Recommandations
        $html += "  <h2>Recommandations</h2>"
        $html += "  <ul>"
        
        if ($global:testsFailed -eq 0 -and $global:testsWarning -eq 0) {
            $html += "    <li>Tous les modules sont correctement configures.</li>"
            $html += "    <li>Aucune action n'est necessaire.</li>"
        }
        elseif ($global:testsFailed -eq 0) {
            $html += "    <li>Les modules sont fonctionnels mais avec des avertissements.</li>"
            $html += "    <li>Verifiez les avertissements avant de continuer.</li>"
        }
        else {
            $html += "    <li>Des problemes ont ete detectes. Corrections necessaires.</li>"
            $html += "    <li>Assurez-vous que tous les modules sont presents et correctement configures.</li>"
        }
        
        $html += "  </ul>"
        
        # Pied de page
        $html += "  <p><small>Rapport genere automatiquement par le script de test des modules.</small></p>"
        $html += "</body>"
        $html += "</html>"
        
        # Ecrire dans le fichier
        $html | Out-File -FilePath $ReportPath
        Write-Log -Message "Rapport HTML genere: $ReportPath" -Level "SUCCESS"
        return $true
    }
    catch {
        Write-Log -Message "Erreur lors de la generation du rapport: $_" -Level "ERROR"
        return $false
    }
}

#=========================================================================
# PROGRAMME PRINCIPAL
#=========================================================================

Write-Log -Message "===== DEBUT DES TESTS DE MODULES =====" -Level "INFO"
Write-Log -Message "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Level "INFO"

# Repertoire des modules
$utilsDir = Join-Path -Path $scriptDir -ChildPath "utils"
Write-Log -Message "Repertoire des modules: $utilsDir" -Level "INFO"

# Liste des modules a tester
$modulesToTest = @(
    @{Path = "$utilsDir\staging_logger.ps1"; Name = "Logger"},
    @{Path = "$utilsDir\staging_prereqs.ps1"; Name = "Prerequisites"},
    @{Path = "$utilsDir\staging_software.ps1"; Name = "Software"},
    @{Path = "$utilsDir\staging_network.ps1"; Name = "Network"},
    @{Path = "$utilsDir\staging_security.ps1"; Name = "Security"},
    @{Path = "$utilsDir\staging_data.ps1"; Name = "Data"},
    @{Path = "$utilsDir\staging_database.ps1"; Name = "Database"}
)

# Test de chargement des modules
$allModulesLoaded = $true
foreach ($module in $modulesToTest) {
    $success = Test-ModuleLoading -ModulePath $module.Path -ModuleName $module.Name
    if (-not $success) {
        $allModulesLoaded = $false
    }
}

# Test des fonctions si les modules sont charges
if ($allModulesLoaded) {
    Write-Log -Message "Test des fonctions..." -Level "INFO"
    
    # Liste des fonctions par categorie
    $functionsToTest = @{
        "Journalisation" = @(
            "Write-LogMessage",
            "Start-LogSection",
            "Write-DetailedLog"
        );
        "Reseau" = @(
            "Test-NetworkConnectivity",
            "Set-NetworkConfiguration"
        );
        "Securite" = @(
            "Test-SecurityCompliance",
            "Set-SecurityConfiguration"
        );
        "Donnees" = @(
            "Import-SampleData",
            "Test-DataIntegrity"
        )
    }
    
    # Tester chaque fonction
    foreach ($category in $functionsToTest.Keys) {
        foreach ($function in $functionsToTest[$category]) {
            Test-FunctionExists -FunctionName $function -Category $category
        }
    }
}

# Determiner le statut global
$globalStatus = if ($global:testsFailed -eq 0) {
    if ($global:testsWarning -eq 0) { "SUCCESS" } else { "WARNING" }
} else {
    "FAILURE"
}

# Resume
Write-Log -Message "===== TESTS TERMINES =====" -Level "INFO"
Write-Log -Message "Tests reussis: $global:testsPassed" -Level "INFO"
Write-Log -Message "Tests echoues: $global:testsFailed" -Level "INFO"
Write-Log -Message "Avertissements: $global:testsWarning" -Level "INFO"
Write-Log -Message "Statut global: $globalStatus" -Level $(if ($globalStatus -eq "FAILURE") { "ERROR" } elseif ($globalStatus -eq "WARNING") { "WARNING" } else { "SUCCESS" })

# Generer le rapport HTML
if (-not $NoReport) {
    if ([string]::IsNullOrEmpty($ReportDir)) {
        $ReportDir = $LogDir
    }
    
    $reportFileName = "module_test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').html"
    $reportPath = Join-Path -Path $ReportDir -ChildPath $reportFileName
    
    New-TestReport -ReportPath $reportPath
}

# Retourner le code d'erreur approprie
if ($globalStatus -eq "FAILURE") {
    exit 1
} else {
    exit 0
}
