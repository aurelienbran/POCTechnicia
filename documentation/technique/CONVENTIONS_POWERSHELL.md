# Conventions PowerShell du Projet Technicia

## Introduction

Ce document définit les standards et conventions de codage PowerShell adoptés pour le projet Technicia. Il sert de référence pour tous les développeurs travaillant sur les scripts d'automatisation du projet, notamment les scripts de préparation de l'environnement de staging.

## Objectifs

1. Standardiser le code PowerShell à travers le projet
2. Améliorer la lisibilité et la maintenabilité du code
3. Réduire les avertissements de lint et autres problèmes de qualité
4. Faciliter la collaboration entre les membres de l'équipe

## Conventions de nommage

### Verbes approuvés pour les fonctions

Toutes les fonctions PowerShell doivent utiliser des verbes approuvés selon les recommandations officielles de Microsoft. Cette standardisation a été appliquée à tous les scripts du projet Technicia avec les correspondances suivantes:

| Ancien verbe | Nouveau verbe approuvé | Exemples |
|--------------|------------------------|----------|
| `Configure-` | `Set-`                 | `Configure-Network` → `Set-NetworkConfiguration` |
| `Initialize-` | `New-`               | `Initialize-Database` → `New-Database` |
| `Prepare-` | `Start-`                | `Prepare-Data` → `Start-DataPreparation` |
| `Load-` | `Import-`                  | `Load-TestData` → `Import-TestData` |
| `Validate-` | `Test-`                | `Validate-DataIntegrity` → `Test-DataIntegrity` |
| `End-` | `Stop-` ou `Complete-`      | `End-LogSection` → `Stop-LogSection` |
| `Log-` | `Write-`                    | `Log-Exception` → `Write-ExceptionLog` |

Pour une liste complète des verbes approuvés, exécuter la commande PowerShell:
```powershell
Get-Verb | Sort-Object -Property Verb | Format-Table -AutoSize
```

### Noms des fonctions

- Les noms de fonctions doivent suivre le format `Verbe-Nom` où le verbe est un verbe approuvé
- Pour les fonctions qui configurent un système, le format `Set-NomConfiguration` est préféré
- Pour les fonctions qui démarrent un processus, le format `Start-NomProcessus` est préféré
- Pour les fonctions qui testent une condition, le format `Test-Condition` est préféré

### Variables

- Les noms de variables doivent être explicites et descriptifs
- Utiliser le camelCase pour les variables locales: `$nomVariable`
- Les variables représentant des chemins doivent se terminer par "Path" ou "Dir": `$certPath`, `$baseDir`
- Les variables globales doivent être préfixées par `$global:`
- Les variables globales exposant des fonctions doivent utiliser des underscores: `$global:Set_NetworkConfiguration`

### Paramètres

- Les paramètres de fonctions doivent suivre le format PascalCase: `[string]$ServerName`
- Tous les paramètres doivent avoir un type explicite: `[bool]`, `[string]`, `[int]`, etc.
- Utiliser `[Parameter(Mandatory=$true)]` pour les paramètres obligatoires
- Fournir des valeurs par défaut pour les paramètres optionnels

## Organisation du code

### Structure des scripts

- Chaque script et fonction doit comencer par un bloc de commentaires avec:
  - `.SYNOPSIS`: Résumé court de l'objectif
  - `.DESCRIPTION`: Description détaillée
  - `.PARAMETER`: Description de chaque paramètre
  - `.EXAMPLE`: Au moins un exemple d'utilisation

### Gestion des erreurs

- Utiliser des blocs Try/Catch pour la gestion des erreurs
- Journaliser les exceptions avec `Write-ExceptionLog`
- Pour les fonctions retournant des valeurs, retourner `$false` en cas d'erreur
- Utiliser `Write-LogMessage` avec le niveau approprié ("INFO", "WARN", "ERROR")

### Dot-sourcing et exposition des fonctions

- Ne pas utiliser `Export-ModuleMember` mais plutôt des variables globales:
  ```powershell
  $global:Function_Name = ${function:Function-Name}
  ```
- Cette approche est plus compatible avec le dot-sourcing et améliore la réutilisabilité

## Bonnes pratiques

### Sécurité

- Utiliser `SecureString` pour les mots de passe et informations sensibles
- Ne pas exposer de données sensibles dans les logs
- Minimiser l'utilisation de paramètres en texte clair pour les informations sensibles

### Performance

- Éviter les variables inutilisées
- Utiliser `Out-Null` plutôt que `| null` pour supprimer la sortie
- Privilégier les opérations orientées objet plutôt que le traitement de texte

### Compatibilité

- Tester les scripts avec PowerShell 5.1 (Windows) et PowerShell Core lorsque applicable
- Vérifier les scripts avec PSScriptAnalyzer pour identifier les problèmes potentiels
- Documenter les dépendances particulières (modules requis, versions minimales)

## Tests et validation

### Tests unitaires

- Créer des scripts de test pour vérifier les modules et fonctions
- Vérifier que les modules se chargent correctement
- Tester l'accessibilité des fonctions après renommage

### Tests d'intégration

- Exécuter le script principal avec diverses combinaisons de paramètres
- Vérifier les interactions entre les différents modules
- S'assurer que toutes les fonctionnalités fonctionnent harmonieusement ensemble

## Conclusion

Ces conventions et standards ont été appliqués à tous les scripts PowerShell du projet Technicia. Tout nouveau développement ou modification devra respecter ces conventions pour maintenir la cohérence et la qualité du code.

## Références

- [PowerShell Approved Verbs](https://learn.microsoft.com/en-us/powershell/scripting/developer/cmdlet/approved-verbs-for-windows-powershell-commands)
- [PowerShell Coding Conventions](https://learn.microsoft.com/en-us/powershell/scripting/developer/cmdlet/cmdlet-development-guidelines)
- [PSScriptAnalyzer](https://github.com/PowerShell/PSScriptAnalyzer)
