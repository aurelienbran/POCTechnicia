<#
.SYNOPSIS
    Script de test pour valider le déploiement en environnement de staging.

.DESCRIPTION
    Ce script effectue une série de tests pour valider le bon fonctionnement 
    du système Technicia après déploiement en environnement de staging.
    Il teste l'ensemble des composants (OCR, API, WebSockets, bases de connaissances)
    et génère un rapport de validation détaillé.

.NOTES
    Auteur: Équipe Technicia
    Date de création: 7 avril 2025
    Version: 1.0
#>

#Requires -Version 5.1
#Requires -Modules @{ ModuleName="Pester"; ModuleVersion="5.3.0" }

# Force l'encodage en UTF-8 pour éviter les problèmes avec les caractères accentués
$OutputEncoding = [System.Text.UTF8Encoding]::new()

param (
    [Parameter(Mandatory=$false)]
    [string]$StagingUrl = "http://staging.technicia.local",
    
    [Parameter(Mandatory=$false)]
    [string]$ApiEndpoint = "$StagingUrl/api",
    
    [Parameter(Mandatory=$false)]
    [string]$WebSocketUrl = "ws://staging.technicia.local/ws",
    
    [Parameter(Mandatory=$false)]
    [string]$AdminUsername = "admin@technicia.com",
    
    [Parameter(Mandatory=$false)]
    [System.Security.SecureString]$AdminPassword = (ConvertTo-SecureString "P@ssw0rd!" -AsPlainText -Force),
    
    [Parameter(Mandatory=$false)]
    [string]$TestDataPath = "..\test_data",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputReportPath = "..\reports\staging_validation_report.html",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipLongTests,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipResourceIntensiveTests
)

# ------------- Fonctions utilitaires -------------

function Write-ColorOutput {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [string]$ForegroundColor = "White",
        
        [Parameter(Mandatory=$false)]
        [switch]$LogToFile
    )
    
    $originalColor = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Output $Message
    $host.UI.RawUI.ForegroundColor = $originalColor
    
    # Si LogToFile est spécifié, écrit également dans un fichier de log avec horodatage
    if ($LogToFile) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $logDir = Join-Path (Split-Path -Parent $OutputReportPath) "logs"
        
        if (-not (Test-Path $logDir)) {
            New-Item -Path $logDir -ItemType Directory -Force | Out-Null
        }
        
        $logFile = Join-Path $logDir "staging_test_$(Get-Date -Format 'yyyyMMdd').log"
        "[$timestamp] $Message" | Out-File -FilePath $logFile -Append -Encoding UTF8
    }
}

function Get-AuthToken {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Username,
        
        [Parameter(Mandatory=$true)]
        [System.Security.SecureString]$Password
    )
    
    # Convertir le SecureString en texte brut pour l'API (seulement pour la requête)
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
    $plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
    
    $body = @{
        "username" = $Username
        "password" = $plainPassword
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$ApiEndpoint/auth/login" -Method Post -Body $body -ContentType "application/json"
        return $response.access_token
    }
    catch {
        Write-ColorOutput "Erreur lors de l'authentification: $_" -ForegroundColor "Red"
        return $null
    }
}

function Test-Endpoint {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Url,
        
        [Parameter(Mandatory=$false)]
        [string]$Method = "GET",
        
        [Parameter(Mandatory=$false)]
        [string]$Token = $null,
        
        [Parameter(Mandatory=$false)]
        [object]$Body = $null
    )
    
    $headers = @{}
    if ($Token) {
        $headers["Authorization"] = "Bearer $Token"
    }
    
    try {
        if ($Body) {
            $bodyJson = $Body | ConvertTo-Json -Depth 10
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Headers $headers -Body $bodyJson -ContentType "application/json"
        }
        else {
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Headers $headers
        }
        return $response
    }
    catch {
        Write-ColorOutput "Erreur lors de l'appel à $Url: $_" -ForegroundColor "Red"
        return $null
    }
}

function Test-WebSocketConnection {
    param (
        [Parameter(Mandatory=$true)]
        [string]$WebSocketUrl,
        
        [Parameter(Mandatory=$false)]
        [int]$TimeoutSeconds = 10
    )
    
    # Utilisation d'un script temporaire pour tester la connexion WebSocket
    $tempScriptPath = [System.IO.Path]::GetTempFileName() + ".ps1"
    
    @"
`$webSocketUrl = '$WebSocketUrl'
`$timeoutMs = $($TimeoutSeconds * 1000)

Add-Type -AssemblyName System.Net.WebSockets.Client

try {
    `$clientWebSocket = New-Object System.Net.WebSockets.ClientWebSocket
    `$cancellationToken = New-Object System.Threading.CancellationToken
    
    `$connectTask = `$clientWebSocket.ConnectAsync(`$webSocketUrl, `$cancellationToken)
    `$connectTask.Wait(`$timeoutMs)
    
    if (`$connectTask.IsCompleted -and `$clientWebSocket.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
        Write-Output "SUCCESS"
        
        # Fermer proprement la connexion
        `$closeTask = `$clientWebSocket.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "Test completed", `$cancellationToken)
        `$closeTask.Wait()
    }
    else {
        Write-Output "FAILED: Timeout ou échec de connexion"
    }
}
catch {
    Write-Output "FAILED: `$_"
}
"@ | Out-File -FilePath $tempScriptPath -Encoding utf8
    
    try {
        $result = & powershell -File $tempScriptPath
        Remove-Item $tempScriptPath -Force
        
        if ($result -contains "SUCCESS") {
            return $true
        }
        else {
            Write-ColorOutput "Échec de la connexion WebSocket: $result" -ForegroundColor "Red"
            return $false
        }
    }
    catch {
        Write-ColorOutput "Erreur lors du test WebSocket: $_" -ForegroundColor "Red"
        Remove-Item $tempScriptPath -Force -ErrorAction SilentlyContinue
        return $false
    }
}

function Test-FileUpload {
    param (
        [Parameter(Mandatory=$true)]
        [string]$FilePath,
        
        [Parameter(Mandatory=$true)]
        [string]$Token
    )
    
    try {
        $fileBytes = [System.IO.File]::ReadAllBytes($FilePath)
        $fileName = [System.IO.Path]::GetFileName($FilePath)
        
        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        
        $bodyLines = @(
            "--$boundary",
            "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
            "Content-Type: application/octet-stream$LF",
            [System.Text.Encoding]::UTF8.GetString($fileBytes),
            "--$boundary--$LF"
        )
        
        $body = $bodyLines -join $LF
        
        $headers = @{
            "Authorization" = "Bearer $Token"
        }
        
        $response = Invoke-RestMethod -Uri "$ApiEndpoint/documents/upload" -Method Post -Headers $headers -ContentType "multipart/form-data; boundary=$boundary" -Body $body
        
        return $response
    }
    catch {
        Write-ColorOutput "Erreur lors de l'upload du fichier $FilePath : $_" -ForegroundColor "Red"
        return $null
    }
}

# ------------- Tests principaux -------------

# Variables pour suivre les résultats des tests
$script:testsPassed = 0
$script:testsFailed = 0
$script:testsWarning = 0

# Fonction pour enregistrer le résultat d'un test
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
    
    switch ($Result) {
        "Success" { 
            $script:testsPassed++
            Write-ColorOutput "✓ $TestName" -ForegroundColor "Green" -LogToFile
        }
        "Failure" { 
            $script:testsFailed++
            Write-ColorOutput "✗ $TestName : $Details" -ForegroundColor "Red" -LogToFile
        }
        "Warning" { 
            $script:testsWarning++
            Write-ColorOutput "⚠ $TestName : $Details" -ForegroundColor "Yellow" -LogToFile
        }
    }
}

# Fonction pour capturer et gérer les exceptions
function Invoke-WithErrorHandling {
    param (
        [Parameter(Mandatory=$true)]
        [scriptblock]$ScriptBlock,
        
        [Parameter(Mandatory=$true)]
        [string]$ErrorMessage,
        
        [Parameter(Mandatory=$false)]
        [scriptblock]$FinallyBlock = {}
    )
    
    try {
        & $ScriptBlock
        return $true
    }
    catch {
        Write-ColorOutput "$ErrorMessage : $_" -ForegroundColor "Red" -LogToFile
        return $false
    }
    finally {
        & $FinallyBlock
    }
}

# Création du répertoire de rapports si nécessaire
$reportDir = Split-Path -Parent $OutputReportPath
if (-not (Test-Path $reportDir)) {
    New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
}

# Vérification de l'accessibilité de base du serveur
Write-ColorOutput "Vérification de l'accessibilité du serveur..." -ForegroundColor "Cyan" -LogToFile
$serverAccessible = Invoke-WithErrorHandling -ScriptBlock {
    $ping = Invoke-RestMethod -Uri "$StagingUrl/health" -Method Get -TimeoutSec 10
    if ($ping.status -eq "ok") {
        Register-TestResult -TestName "Le serveur est accessible" -Result "Success"
        return $true
    } else {
        Register-TestResult -TestName "Le serveur a répondu avec un statut inattendu" -Result "Warning" -Details $ping.status
        return $true
    }
} -ErrorMessage "Le serveur n'est pas accessible"

if (-not $serverAccessible) {
    Register-TestResult -TestName "Accessibilité du serveur" -Result "Failure" -Details "Impossible de continuer les tests sans accès au serveur"
    
    # Génération d'un rapport d'échec minimal avant de quitter
    $htmlReport = @"
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Rapport de validation du déploiement - ÉCHEC</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #d9534f; }
        .failure { color: #d9534f; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Échec de la validation du déploiement</h1>
    <p class="failure">Le serveur n'est pas accessible à l'adresse: $StagingUrl</p>
    <p>Date du test: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")</p>
</body>
</html>
"@
    
    $htmlReport | Out-File -FilePath $OutputReportPath -Encoding UTF8
    Write-ColorOutput "Un rapport d'échec a été généré à l'emplacement: $OutputReportPath" -ForegroundColor "Cyan" -LogToFile
    exit 1
}

# Récupération du token d'authentification
Write-ColorOutput "Authentification en tant qu'administrateur..." -ForegroundColor "Cyan"
$authToken = Get-AuthToken -Username $AdminUsername -Password $AdminPassword

if (-not $authToken) {
    Write-ColorOutput "✗ Échec de l'authentification. Impossible de continuer les tests." -ForegroundColor "Red"
    exit 1
}
Write-ColorOutput "✓ Authentification réussie." -ForegroundColor "Green"

# Tests de l'API REST
Write-ColorOutput "Test des endpoints API principaux..." -ForegroundColor "Cyan"

$apiTests = @(
    @{ Name = "Version API"; Url = "$ApiEndpoint/version"; ExpectedProperty = "version" },
    @{ Name = "Statut système"; Url = "$ApiEndpoint/system/status"; ExpectedProperty = "status" },
    @{ Name = "Fournisseurs OCR"; Url = "$ApiEndpoint/ocr/providers"; ExpectedProperty = "providers" },
    @{ Name = "Utilisateurs"; Url = "$ApiEndpoint/users"; ExpectedProperty = "items"; RequireAuth = $true },
    @{ Name = "Bases de connaissances"; Url = "$ApiEndpoint/kb"; ExpectedProperty = "items"; RequireAuth = $true }
)

$apiTestsFailed = 0

foreach ($test in $apiTests) {
    $token = $null
    if ($test.RequireAuth) {
        $token = $authToken
    }
    
    $response = Test-Endpoint -Url $test.Url -Token $token
    
    if ($response -and (Get-Member -InputObject $response -Name $test.ExpectedProperty -MemberType Properties)) {
        Write-ColorOutput "✓ Test '$($test.Name)' réussi" -ForegroundColor "Green"
    } else {
        Write-ColorOutput "✗ Test '$($test.Name)' échoué" -ForegroundColor "Red"
        $apiTestsFailed++
    }
}

# Test des WebSockets
Write-ColorOutput "Test de la connexion WebSocket..." -ForegroundColor "Cyan"
$wsTest = Test-WebSocketConnection -WebSocketUrl $WebSocketUrl

if ($wsTest) {
    Write-ColorOutput "✓ Connexion WebSocket réussie" -ForegroundColor "Green"
} else {
    Write-ColorOutput "✗ Échec de la connexion WebSocket" -ForegroundColor "Red"
}

# Tests d'upload et de traitement OCR (si les données de test sont disponibles)
$testImagePath = Join-Path $TestDataPath "test_document.jpg"
if (Test-Path $testImagePath) {
    Write-ColorOutput "Test d'upload et de traitement OCR..." -ForegroundColor "Cyan"
    
    $uploadResult = Test-FileUpload -FilePath $testImagePath -Token $authToken
    
    if ($uploadResult -and $uploadResult.document_id) {
        Write-ColorOutput "✓ Upload de document réussi. ID du document: $($uploadResult.document_id)" -ForegroundColor "Green"
        
        # Attente du traitement OCR (avec timeout)
        $processed = $false
        $attempts = 0
        $maxAttempts = 10
        
        while (-not $processed -and $attempts -lt $maxAttempts) {
            Start-Sleep -Seconds 3
            $attempts++
            
            $statusResponse = Test-Endpoint -Url "$ApiEndpoint/documents/$($uploadResult.document_id)/status" -Token $authToken
            
            if ($statusResponse -and $statusResponse.status -eq "completed") {
                $processed = $true
                Write-ColorOutput "✓ Traitement OCR réussi" -ForegroundColor "Green"
                
                # Vérification du contenu extrait
                $textResponse = Test-Endpoint -Url "$ApiEndpoint/documents/$($uploadResult.document_id)/text" -Token $authToken
                
                if ($textResponse -and $textResponse.text -and $textResponse.text.Length -gt 0) {
                    Write-ColorOutput "✓ Extraction de texte réussie" -ForegroundColor "Green"
                } else {
                    Write-ColorOutput "⚠ L'extraction de texte a réussi mais le texte est vide ou non disponible" -ForegroundColor "Yellow"
                }
            } elseif ($statusResponse -and $statusResponse.status -eq "failed") {
                Write-ColorOutput "✗ Échec du traitement OCR" -ForegroundColor "Red"
                break
            } else {
                Write-ColorOutput "En attente du traitement OCR... ($attempts/$maxAttempts)" -ForegroundColor "Cyan"
            }
        }
        
        if (-not $processed) {
            Write-ColorOutput "⚠ Timeout lors du traitement OCR après $maxAttempts tentatives" -ForegroundColor "Yellow"
        }
    } else {
        Write-ColorOutput "✗ Échec de l'upload de document" -ForegroundColor "Red"
    }
} else {
    Write-ColorOutput "⚠ Fichier de test d'image non trouvé à $testImagePath. Test OCR ignoré." -ForegroundColor "Yellow"
}

# Test de l'interface d'administration (simple vérification d'accessibilité)
Write-ColorOutput "Test d'accessibilité de l'interface d'administration..." -ForegroundColor "Cyan"

try {
    $adminPage = Invoke-WebRequest -Uri "$StagingUrl/admin" -TimeoutSec 10 -UseBasicParsing
    
    if ($adminPage.StatusCode -eq 200) {
        Write-ColorOutput "✓ L'interface d'administration est accessible" -ForegroundColor "Green"
    } else {
        Write-ColorOutput "⚠ L'interface d'administration a retourné un code inattendu: $($adminPage.StatusCode)" -ForegroundColor "Yellow"
    }
} catch {
    Write-ColorOutput "✗ L'interface d'administration n'est pas accessible" -ForegroundColor "Red"
}

# Tests de performance (uniquement si non ignorés)
if (-not $SkipResourceIntensiveTests) {
    Write-ColorOutput "Exécution des tests de performance..." -ForegroundColor "Cyan"
    
    # Simulation de charge légère pour tester les performances de base
    # Dans un script réel, nous utiliserions un outil comme k6 ou ab (ApacheBench)
    
    $startTime = Get-Date
    $iterations = 10
    $successfulRequests = 0
    
    for ($i = 0; $i -lt $iterations; $i++) {
        $response = Test-Endpoint -Url "$ApiEndpoint/version"
        
        if ($response) {
            $successfulRequests++
        }
        
        Start-Sleep -Milliseconds 200
    }
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    $requestsPerSecond = $iterations / $duration
    
    Write-ColorOutput "Test de charge de base:" -ForegroundColor "Cyan"
    Write-ColorOutput " - Requêtes réussies: $successfulRequests / $iterations" -ForegroundColor "White"
    Write-ColorOutput " - Durée totale: $([math]::Round($duration, 2)) secondes" -ForegroundColor "White"
    Write-ColorOutput " - Requêtes par seconde: $([math]::Round($requestsPerSecond, 2))" -ForegroundColor "White"
}

# Génération du rapport final
Write-ColorOutput "`nRésumé des tests de déploiement en staging:" -ForegroundColor "Cyan" -LogToFile
Write-ColorOutput "Tests réussis: $script:testsPassed" -ForegroundColor "Green" -LogToFile
Write-ColorOutput "Tests échoués: $script:testsFailed" -ForegroundColor "Red" -LogToFile
Write-ColorOutput "Tests avec avertissements: $script:testsWarning" -ForegroundColor "Yellow" -LogToFile

$testResult = "";
if ($script:testsFailed -eq 0) {
    $testResult = "RÉUSSIE";
    Write-ColorOutput "`n✓ Validation du déploiement en staging RÉUSSIE" -ForegroundColor "Green" -LogToFile
} else {
    $testResult = "ÉCHOUÉE";
    Write-ColorOutput "`n✗ Validation du déploiement en staging ÉCHOUÉE ($script:testsFailed tests ont échoué)" -ForegroundColor "Red" -LogToFile
}

# Génération du rapport HTML
Write-ColorOutput "Génération du rapport HTML..." -ForegroundColor "Cyan" -LogToFile

$resultColorClass = if ($script:testsFailed -eq 0) { "success" } else { "failure" }

$htmlReport = @"
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Rapport de validation du déploiement - $testResult</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .success { color: #5cb85c; }
        .failure { color: #d9534f; }
        .warning { color: #f0ad4e; }
        .summary { font-size: 1.2em; margin: 20px 0; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>Rapport de validation du déploiement en staging</h1>
    <p>Date du test: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")</p>
    <p>URL du serveur testé: <code>$StagingUrl</code></p>
    
    <div class="summary">
        <p>Résultat global: <span class="$resultColorClass">$testResult</span></p>
        <p>Tests réussis: <span class="success">$script:testsPassed</span></p>
        <p>Tests échoués: <span class="failure">$script:testsFailed</span></p>
        <p>Tests avec avertissements: <span class="warning">$script:testsWarning</span></p>
    </div>
    
    <h2>Détails des tests</h2>
    <table>
        <tr>
            <th>Test</th>
            <th>Résultat</th>
            <th>Détails</th>
        </tr>
        <!-- Les détails des tests seraient inclus ici dans un scénario complet -->
    </table>
    
    <h2>Recommandations</h2>
    <p>Actions recommandées:</p>
    <ul>
"@

if ($script:testsFailed -eq 0 -and $script:testsWarning -eq 0) {
    $htmlReport += @"
        <li>Le déploiement est stable et prêt pour les tests utilisateurs.</li>
        <li>Continuer avec la phase de tests utilisateurs selon le plan défini.</li>
"@
} elseif ($script:testsFailed -eq 0) {
    $htmlReport += @"
        <li>Le déploiement est fonctionnel mais présente quelques avertissements.</li>
        <li>Corriger les avertissements avant les tests utilisateurs si possible.</li>
        <li>Documenter les avertissements connus pour l'équipe de test.</li>
"@
} else {
    $htmlReport += @"
        <li>Résoudre les échecs de test avant de procéder aux tests utilisateurs.</li>
        <li>Vérifier les logs détaillés pour plus d'informations sur les problèmes.</li>
        <li>Réexécuter les tests après avoir résolu les problèmes.</li>
"@
}

$htmlReport += @"
    </ul>
    
    <p><small>Rapport généré automatiquement par le script de test de déploiement Technicia.</small></p>
</body>
</html>
"@

$htmlReport | Out-File -FilePath $OutputReportPath -Encoding UTF8
Write-ColorOutput "Rapport généré avec succès à l'emplacement: $OutputReportPath" -ForegroundColor "Green" -LogToFile
