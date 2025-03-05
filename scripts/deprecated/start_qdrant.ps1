# Démarrer Qdrant
$qdrantPath = ".\qdrant\qdrant.exe"

if (Test-Path $qdrantPath) {
    Write-Host "Démarrage de Qdrant..."
    Start-Process -FilePath $qdrantPath -NoNewWindow
} else {
    Write-Host "Qdrant n'est pas installé. Veuillez d'abord exécuter setup_qdrant.ps1"
    exit 1
}
