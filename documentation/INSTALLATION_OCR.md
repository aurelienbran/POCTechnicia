# Installation des dépendances OCR pour Technicia

Pour que la fonctionnalité OCR fonctionne correctement, vous devez installer les dépendances suivantes sur votre système et les ajouter au PATH:

## 1. Tesseract OCR

Sur votre système, Tesseract est déjà installé à l'emplacement suivant:
```
C:\Users\aurel\AppData\Local\Programs\Tesseract-OCR
```

Si Tesseract n'est pas déjà installé:
1. Téléchargez l'installateur Windows depuis la page officielle: [Tesseract OCR Downloads](https://github.com/UB-Mannheim/tesseract/wiki)
2. Choisissez la version appropriée (32-bit ou 64-bit) et exécutez l'installateur
3. Important: Lors de l'installation, assurez-vous de cocher l'option pour ajouter Tesseract au PATH système
4. Sélectionnez le pack de langues françaises (fra) pendant l'installation

## 2. Ghostscript

Sur votre système, Ghostscript est partiellement installé via Chocolatey à l'emplacement suivant:
```
C:\ProgramData\chocolatey\lib-bad\Ghostscript.app\10.4.0\tools
```

Si Ghostscript n'est pas correctement installé ou ne fonctionne pas:
1. Téléchargez la dernière version de Ghostscript pour Windows depuis [Ghostscript Downloads](https://www.ghostscript.com/releases/gsdnld.html)
2. Exécutez l'installateur et suivez les instructions
3. Ajoutez manuellement le chemin d'installation (généralement `C:\Program Files\gs\gs[version]\bin`) à votre variable d'environnement PATH

## 3. Poppler

Sur votre système, Poppler est déjà installé via Chocolatey à l'emplacement suivant:
```
C:\ProgramData\chocolatey\lib\poppler\tools\Library\bin
```

Si Poppler n'est pas correctement installé:
1. Téléchargez les binaires Windows de Poppler depuis [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
2. Extrayez l'archive dans un dossier permanent (par exemple `C:\Program Files\poppler`)
3. Ajoutez le chemin du dossier `bin` (par exemple `C:\Program Files\poppler\bin`) à votre variable d'environnement PATH

## Ajout des chemins au PATH système

### Option 1: Script automatique

Nous avons créé un script PowerShell qui ajoute automatiquement les chemins nécessaires au PATH système:

1. Ouvrez PowerShell en tant qu'administrateur
2. Naviguez vers le dossier du projet
3. Exécutez la commande suivante:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\scripts\update_ocr_path.ps1
   ```

### Option 2: Ajout manuel

Pour ajouter manuellement les chemins au PATH système:

1. Appuyez sur Win+R, tapez `sysdm.cpl` et appuyez sur Entrée
2. Allez dans l'onglet "Avancé"
3. Cliquez sur "Variables d'environnement"
4. Dans la section "Variables système", sélectionnez "Path" et cliquez sur "Modifier"
5. Cliquez sur "Nouveau" et ajoutez les chemins suivants un par un:
   ```
   C:\Users\aurel\AppData\Local\Programs\Tesseract-OCR
   C:\ProgramData\chocolatey\lib\poppler\tools\Library\bin
   C:\ProgramData\chocolatey\lib-bad\Ghostscript.app\10.4.0\tools
   ```
6. Cliquez sur "OK" pour fermer toutes les fenêtres

## Configuration par variables d'environnement

Au lieu de modifier le PATH système, vous pouvez configurer les chemins des outils OCR directement dans le fichier `.env` à la racine du projet:

```
# OCR Configuration - Chemins des dépendances OCR
TESSERACT_PATH=C:\Users\aurel\AppData\Local\Programs\Tesseract-OCR
POPPLER_PATH=C:\ProgramData\chocolatey\lib\poppler\tools\Library\bin
GHOSTSCRIPT_PATH=C:\ProgramData\chocolatey\lib-bad\Ghostscript.app\10.4.0\tools
```

Cette méthode présente plusieurs avantages:
- Pas besoin de modifier le PATH système (nécessitant des privilèges administrateur)
- Configuration spécifique à l'application sans affecter d'autres programmes
- Facilité de déploiement sur plusieurs postes avec des configurations différentes

Vous pouvez facilement obtenir les chemins corrects en exécutant le script PowerShell:
```powershell
.\scripts\tools\update_ocr_path.ps1
```
Ce script détectera automatiquement les chemins et affichera les paramètres à ajouter dans le fichier `.env`.

## Vérification de l'installation

Après l'installation et l'ajout des chemins au PATH, ouvrez une nouvelle fenêtre PowerShell et vérifiez que chaque outil est correctement installé:

```powershell
# Vérifier Tesseract
tesseract --version

# Vérifier Ghostscript 
gs10040w64 -v  # Utilisez le nom exact du fichier exécutable

# Vérifier Poppler
pdfinfo -v

# Vérifier OCRmyPDF
ocrmypdf --version
```

## Tests de la fonctionnalité OCR

### Script de diagnostic

Le script de diagnostic vérifie automatiquement toutes les dépendances OCR et leurs emplacements :

```powershell
# Exécution du script de diagnostic
python .\scripts\diagnose_ocr.py

# Diagnostic avec test sur un fichier PDF spécifique
python .\scripts\diagnose_ocr.py chemin/vers/fichier.pdf
```

Ce script effectue les vérifications suivantes :
- Présence des chemins Tesseract, Poppler et Ghostscript
- Accessibilité des exécutables dans le PATH
- Test de reconnaissance directe via Tesseract
- Test d'OCRmyPDF si un fichier est spécifié

### Test d'OCR sur un fichier

Nous avons également développé un script de test plus simple pour vérifier rapidement si l'OCR fonctionne correctement:

```powershell
# Test de base avec OCR automatique
python .\scripts\test_ocr.py chemin/vers/fichier.pdf

# Test sans OCR
python .\scripts\test_ocr.py chemin/vers/fichier.pdf false
```

Le script détectera automatiquement si le document nécessite l'OCR et l'appliquera si nécessaire.

## Fonctionnement technique de l'OCR

### Détection automatique des documents nécessitant OCR

L'application détecte automatiquement si un document a besoin d'OCR en:
1. Vérifiant si le nom du fichier contient des indications d'OCR (comme "ocr_" ou "_ocr_")
2. Examinant les métadonnées pour identifier les signatures des logiciels d'OCR courants
3. Analysant les premières pages pour détecter la présence ou l'absence de texte

### Extraction de texte améliorée

Le processus d'extraction de texte utilise une approche hybride:
1. Utilisation de PyMuPDF (fitz) comme méthode principale
2. Si peu ou pas de texte est extrait, utilisation automatique de pdftotext (Poppler)
3. Pour les documents avec OCR, une méthode spécialisée est utilisée pour garantir la meilleure extraction possible

### Compatibilité Windows

Toutes les fonctionnalités OCR sont maintenant pleinement compatibles avec Windows:
- Utilisation de `subprocess.run` au lieu de `asyncio.create_subprocess_exec`
- Détection automatique des exécutables dans le PATH système
- Gestion améliorée des erreurs pour fournir des diagnostics clairs

## Redémarrage du serveur

Une fois toutes les dépendances installées, redémarrez le serveur Technicia pour que les changements prennent effet.

## Résolution des problèmes

Si après l'installation des dépendances, l'OCR ne fonctionne toujours pas:

1. Vérifiez que les chemins ont été correctement ajoutés au PATH
   ```powershell
   # Vérifier si les outils sont accessibles
   where tesseract
   where pdfinfo
   where ocrmypdf
   ```

2. Consultez les logs d'erreur pour plus de détails (vérifiez particulièrement les messages contenant "OCR" ou "Tesseract")

3. Assurez-vous que les fichiers de langues pour Tesseract sont correctement installés:
   ```powershell
   # Vérifier les langues disponibles
   tesseract --list-langs
   ```
   Vous devriez voir "fra" dans la liste des langues

4. Si l'erreur persiste, essayez de lancer manuellement OCRmyPDF dans une console:
   ```powershell
   ocrmypdf --skip-text -l fra chemin/vers/fichier_source.pdf chemin/vers/fichier_sortie.pdf
   ```

5. Vérifiez le chemin des fichiers temporaires: assurez-vous que le dossier `%TEMP%\technicia_ocr` est accessible en écriture
