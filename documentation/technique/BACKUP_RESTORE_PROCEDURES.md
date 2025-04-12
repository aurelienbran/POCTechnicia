# Procédures de Sauvegarde et Restauration

Ce document détaille les procédures de sauvegarde et de restauration implémentées pour le système OCR Technicia, ainsi que les tests de validation associés.

## 1. Vue d'ensemble

Le système de sauvegarde et restauration a été conçu pour assurer la continuité des opérations en cas d'incident technique. Il permet de :
- Sauvegarder régulièrement les données critiques du système
- Restaurer rapidement ces données en cas de corruption ou de perte
- Vérifier l'intégrité du système après restauration

## 2. Composants sauvegardés

Le système de sauvegarde couvre les éléments suivants :

| Composant | Description | Emplacement |
|-----------|-------------|-------------|
| Base de données | Contient toutes les métadonnées des documents et l'état du système | PostgreSQL |
| Fichiers de configuration | Paramètres du système et préférences | `/etc/technicia/` ou `C:\Program Files\Technicia\OCRSystem\config\` |
| Données utilisateur | Documents sources et traités | Dossier configurable dans les paramètres |
| Cache Redis | État temporaire et résultats de traitement en cours | Redis |

## 3. Stratégie de sauvegarde

### 3.1 Types de sauvegardes

Le système implémente trois types de sauvegardes :

- **Sauvegarde complète** : Sauvegarde de l'ensemble des données du système
- **Sauvegarde incrémentielle** : Sauvegarde uniquement des données modifiées depuis la dernière sauvegarde complète
- **Sauvegarde à chaud** : Sauvegarde effectuée pendant que le système est en fonctionnement

### 3.2 Fréquence recommandée

| Type de sauvegarde | Fréquence recommandée |
|--------------------|----------------------|
| Complète | Hebdomadaire |
| Incrémentielle | Quotidienne |
| À chaud | En cas de besoin (mise à jour majeure, etc.) |

### 3.3 Stratégie de rétention

- Conservation des 4 dernières sauvegardes complètes
- Conservation des sauvegardes incrémentielles jusqu'à la prochaine sauvegarde complète
- Rotation automatique des sauvegardes les plus anciennes

## 4. Procédure de restauration

La restauration du système suit les étapes suivantes :

1. Arrêt des services en cours
2. Restauration de la base de données
3. Restauration des fichiers de configuration
4. Restauration des données utilisateur
5. Redémarrage des services
6. Vérification de l'intégrité du système

## 5. Script de test des procédures

Un script de test automatisé (`test_backup_restore.ps1`) a été développé pour valider les procédures de sauvegarde et de restauration. Ce script effectue les opérations suivantes :

### 5.1 Fonctionnalités du script

- **Initialisation d'un environnement de test** : Création d'un environnement simulant la production
- **Sauvegarde du système** : Sauvegarde complète des composants critiques
- **Simulation de corruption** : Altération volontaire de fichiers pour simuler un incident
- **Restauration du système** : Application de la procédure de restauration
- **Vérification d'intégrité** : Tests complets pour confirmer la restauration correcte
- **Tests de performance** : Mesure des temps de sauvegarde et de restauration avec différents volumes de données

### 5.2 Paramètres configurable

```powershell
param (
    [string]$TestDir = "C:\Technicia\BackupRestoreTest",
    [string]$ProductionDir = "C:\Program Files\Technicia\OCRSystem",
    [string]$BackupDir = "C:\Technicia\Backups",
    [System.Security.SecureString]$DbPassword,
    [System.Security.SecureString]$RedisPassword,
    [switch]$CleanupAfterTest,
    [switch]$VerboseOutput
)
```

### 5.3 Indicateurs de réussite

Les tests sont considérés comme réussis lorsque :

- La sauvegarde est créée correctement avec tous les composants requis
- Après simulation de corruption, le système est inutilisable (validation de la simulation)
- Après restauration, tous les services redémarrent correctement
- Tous les tests d'intégrité passent avec succès
- Les métriques de performance sont dans les limites acceptables

### 5.4 Rapport de test

Le script génère un rapport détaillé qui inclut :

- Horodatage et informations sur l'environnement de test
- Résultat de chaque étape du test (succès/échec)
- Métriques de performance (temps de sauvegarde/restauration)
- Journal complet des erreurs éventuelles
- Recommandations pour améliorer les procédures

## 6. Bonnes pratiques

- Exécuter les tests de sauvegarde/restauration après chaque mise à jour majeure du système
- Stocker les sauvegardes sur un support externe ou distant
- Chiffrer les sauvegardes contenant des données sensibles
- Vérifier régulièrement l'intégrité des sauvegardes existantes
- Former les administrateurs système aux procédures de restauration manuelle

## 7. Dépannage

### 7.1 Problèmes courants

| Problème | Solution |
|----------|----------|
| Échec de sauvegarde de la base de données | Vérifier les permissions de l'utilisateur PostgreSQL et l'espace disque disponible |
| Corruption des fichiers de configuration après restauration | Utiliser les modèles de configuration par défaut et reconfigurer manuellement |
| Erreur de restauration Redis | Vider complètement le cache Redis avant restauration |
| Lenteur excessive de sauvegarde | Optimiser les paramètres de compression ou exclure certains répertoires non essentiels |

### 7.2 Procédure de récupération d'urgence

En cas d'échec complet de la restauration automatique :

1. Réinstaller le système à partir des médias d'installation
2. Restaurer uniquement la base de données depuis la sauvegarde
3. Reconfigurer manuellement le système
4. Importer les données utilisateur

## 8. Évolutions futures

- Implémentation d'une interface graphique pour la gestion des sauvegardes
- Sauvegarde différentielle (plus légère que l'incrémentielle)
- Intégration avec des services de stockage cloud pour les sauvegardes distantes
- Automatisation complète des tests de sauvegarde/restauration dans le pipeline CI/CD
