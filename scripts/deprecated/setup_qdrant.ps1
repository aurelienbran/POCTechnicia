# Créer le dossier pour Qdrant s'il n'existe pas
$qdrantPath = ".\qdrant"
New-Item -ItemType Directory -Force -Path $qdrantPath

# URL de téléchargement de Qdrant (dernière version)
$qdrantUrl = "https://github.com/qdrant/qdrant/releases/download/v1.7.3/qdrant-x86_64-pc-windows-msvc.zip"
$zipPath = "$qdrantPath\qdrant.zip"

# Télécharger Qdrant
Write-Host "Téléchargement de Qdrant..."
Invoke-WebRequest -Uri $qdrantUrl -OutFile $zipPath

# Extraire l'archive
Write-Host "Extraction de l'archive..."
Expand-Archive -Path $zipPath -DestinationPath $qdrantPath -Force

# Supprimer l'archive
Remove-Item $zipPath

Write-Host "Installation de Qdrant terminée !"
Write-Host "Pour démarrer Qdrant, exécutez : .\qdrant\qdrant.exe"
