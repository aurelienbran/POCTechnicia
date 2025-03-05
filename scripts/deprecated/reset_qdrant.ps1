# Arrêter le service Qdrant s'il est en cours d'exécution
$qdrantProcess = Get-Process -Name "qdrant" -ErrorAction SilentlyContinue
if ($qdrantProcess) {
    Write-Host "Arrêt de Qdrant..."
    $qdrantProcess | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Supprimer le dossier de données de Qdrant
$qdrantDataPath = ".\qdrant\storage"
if (Test-Path $qdrantDataPath) {
    Write-Host "Suppression des données Qdrant..."
    Remove-Item -Path $qdrantDataPath -Recurse -Force
}

# Redémarrer Qdrant
Write-Host "Redémarrage de Qdrant..."
Start-Process -FilePath ".\qdrant\qdrant.exe" -WindowStyle Hidden

Write-Host "Qdrant a été réinitialisé avec succès !"
