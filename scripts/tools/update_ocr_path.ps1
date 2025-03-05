# Script pour ajouter les chemins des outils OCR au PATH système
# À exécuter en tant qu'administrateur

# Chemins des composants OCR
$TesseractPath = "C:\Users\aurel\AppData\Local\Programs\Tesseract-OCR"
$PopplerPath = "C:\ProgramData\chocolatey\lib\poppler\tools\Library\bin"
$GhostscriptPath = "C:\ProgramData\chocolatey\lib-bad\Ghostscript.app\10.4.0\tools"

# Vérifier si les chemins existent
$PathsToAdd = @()

if (Test-Path $TesseractPath) {
    $PathsToAdd += $TesseractPath
    Write-Host "Chemin de Tesseract trouvé: $TesseractPath" -ForegroundColor Green
} else {
    Write-Host "Chemin de Tesseract non trouvé: $TesseractPath" -ForegroundColor Red
}

if (Test-Path $PopplerPath) {
    $PathsToAdd += $PopplerPath
    Write-Host "Chemin de Poppler trouvé: $PopplerPath" -ForegroundColor Green
} else {
    Write-Host "Chemin de Poppler non trouvé: $PopplerPath" -ForegroundColor Red
}

if (Test-Path $GhostscriptPath) {
    $PathsToAdd += $GhostscriptPath
    Write-Host "Chemin de Ghostscript trouvé: $GhostscriptPath" -ForegroundColor Green
} else {
    Write-Host "Chemin de Ghostscript non trouvé: $GhostscriptPath" -ForegroundColor Red
}

# Obtenir le PATH actuel
$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")

# Vérifier quels chemins sont déjà dans le PATH
$PathsToActuallyAdd = @()
foreach ($Path in $PathsToAdd) {
    if ($CurrentPath -notlike "*$Path*") {
        $PathsToActuallyAdd += $Path
        Write-Host "Ajout du chemin au PATH: $Path" -ForegroundColor Yellow
    } else {
        Write-Host "Le chemin est déjà dans le PATH: $Path" -ForegroundColor Cyan
    }
}

# Si des chemins doivent être ajoutés
if ($PathsToActuallyAdd.Count -gt 0) {
    $NewPath = $CurrentPath
    foreach ($Path in $PathsToActuallyAdd) {
        if ($NewPath.EndsWith(";")) {
            $NewPath = "$NewPath$Path"
        } else {
            $NewPath = "$NewPath;$Path"
        }
    }
    
    try {
        [Environment]::SetEnvironmentVariable("PATH", $NewPath, "Machine")
        Write-Host "PATH système mis à jour avec succès!" -ForegroundColor Green
    } catch {
        Write-Host "Erreur lors de la mise à jour du PATH système. Assurez-vous d'exécuter en tant qu'administrateur." -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
} else {
    Write-Host "Aucun nouveau chemin à ajouter au PATH système." -ForegroundColor Green
}

# Tester les commandes
Write-Host "`nTest des commandes OCR:" -ForegroundColor Cyan

$EnvPath = $env:PATH
foreach ($Path in $PathsToAdd) {
    if ($EnvPath -notlike "*$Path*") {
        $EnvPath = "$EnvPath;$Path"
    }
}
$env:PATH = $EnvPath

Write-Host "`nTest de Tesseract:" -ForegroundColor Cyan
try {
    $TesseractVersion = & tesseract --version
    Write-Host "Tesseract OK: $($TesseractVersion[0])" -ForegroundColor Green
} catch {
    Write-Host "Erreur lors du test de Tesseract" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host "`nTest de Ghostscript:" -ForegroundColor Cyan
try {
    $GsExe = Get-ChildItem -Path $GhostscriptPath -Filter "gs*.exe" | Select-Object -First 1
    if ($GsExe) {
        $GsVersion = & "$($GsExe.FullName)" -v
        Write-Host "Ghostscript OK" -ForegroundColor Green
    } else {
        Write-Host "Exécutable Ghostscript non trouvé" -ForegroundColor Red
    }
} catch {
    Write-Host "Erreur lors du test de Ghostscript" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host "`nTest de Poppler:" -ForegroundColor Cyan
try {
    $PdfInfoVersion = & pdfinfo -v
    Write-Host "Poppler OK" -ForegroundColor Green
} catch {
    Write-Host "Erreur lors du test de Poppler" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host "`nTest d'OCRmyPDF:" -ForegroundColor Cyan
try {
    $OcrmypdfVersion = & ocrmypdf --version
    Write-Host "OCRmyPDF OK: $OcrmypdfVersion" -ForegroundColor Green
} catch {
    Write-Host "Erreur lors du test d'OCRmyPDF" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host "`nRedémarrez votre ordinateur ou votre session pour que les changements prennent effet dans toutes les applications." -ForegroundColor Yellow

Write-Host "`n===== Alternative - Configuration par variables d'environnement =====" -ForegroundColor Cyan
Write-Host "Au lieu de modifier le PATH système, vous pouvez également utiliser les variables d'environnement définies dans le fichier .env :" -ForegroundColor White
Write-Host "1. Ouvrez le fichier .env à la racine du projet" -ForegroundColor White
Write-Host "2. Ajoutez ou modifiez les lignes suivantes :" -ForegroundColor White
Write-Host "TESSERACT_PATH=$TesseractPath" -ForegroundColor Green
Write-Host "POPPLER_PATH=$PopplerPath" -ForegroundColor Green  
Write-Host "GHOSTSCRIPT_PATH=$GhostscriptPath" -ForegroundColor Green
Write-Host "3. L'application utilisera automatiquement ces chemins pour l'OCR" -ForegroundColor White
