# Scripts de test pour le déploiement en environnement de staging

Ce répertoire contient plusieurs scripts de test conçus pour valider les modules et les fonctionnalités du projet Technicia avant le déploiement en environnement de staging.

## Liste des scripts

### 1. `test_modules_basic.ps1` (Recommandé)

Script optimisé pour une compatibilité maximale. Utilise uniquement des caractères ASCII pour éviter les problèmes d'encodage.

```powershell
# Utilisation simple
.\test_modules_basic.ps1

# Avec des paramètres spécifiques
.\test_modules_basic.ps1 -LogDir "D:\Logs" -ReportDir "D:\Reports" -NoReport
```

**Paramètres :**
- `-LogDir` : Répertoire de destination pour les fichiers log (optionnel)
- `-ReportDir` : Répertoire de destination pour les rapports HTML (optionnel)
- `-NoReport` : Ne pas générer de rapport HTML (switch)

### 2. `test_modules_pwsh7.ps1`

Version optimisée pour PowerShell 7+ avec une meilleure prise en charge de l'encodage UTF-8.

```powershell
# Utilisation avec PowerShell 7
pwsh -File .\test_modules_pwsh7.ps1 -GenerateReport
```

### 3. `run_module_tests.ps1`

Script wrapper qui tente d'utiliser PowerShell 7 s'il est disponible, sinon utilise PowerShell standard. Idéal pour les environnements mixtes.

```powershell
.\run_module_tests.ps1 -GenerateReport
```

### 4. `test_backup_restore.ps1`

Script pour tester les fonctionnalités de sauvegarde et de restauration.

```powershell
.\test_backup_restore.ps1 -SkipAdminCheck
```

### 5. `test_staging_deployment.ps1`

Script pour valider le déploiement complet en environnement de staging.

```powershell
.\test_staging_deployment.ps1 -StagingUrl "http://staging.technicia.local"
```

## Fonctionnalités communes

Tous les scripts de test offrent :

1. **Journalisation détaillée** : Les résultats des tests sont enregistrés dans un fichier log daté.
2. **Rapports HTML** : Option de génération de rapports HTML pour une analyse visuelle facile.
3. **Substitution automatique des modules manquants** : Si un module n'existe pas, une version de substitution est créée.
4. **Statistiques des tests** : Comptage des tests réussis, échoués et des avertissements.

## Résolution des problèmes courants

### Problèmes d'encodage de caractères

Si vous rencontrez des problèmes d'affichage des caractères accentués :

1. Utilisez de préférence `test_modules_basic.ps1` qui évite les caractères spéciaux
2. Si disponible, utilisez PowerShell 7+ qui a une meilleure prise en charge de l'UTF-8
3. Exécutez la commande `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` avant d'exécuter les scripts

### Erreurs d'accès aux fichiers

Assurez-vous que :

1. Vous avez les droits d'écriture dans les répertoires logs et reports
2. Les chemins spécifiés n'ont pas d'espaces ou utilisez des guillemets
3. Les fichiers ne sont pas verrouillés par une autre application

## Interprétation des résultats

Le code de retour du script (accessible via `$LASTEXITCODE` après l'exécution) indique le statut global :

- `0` : Tous les tests ont réussi (avec ou sans avertissements)
- `1` : Au moins un test a échoué

Pour une analyse détaillée, consultez le rapport HTML généré ou le fichier log.
