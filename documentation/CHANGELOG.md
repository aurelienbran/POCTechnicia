# Changelog

Toutes les modifications notables du projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-03-03

### Ajouté
- **Installation Portable**
  - Script de génération d'installateur auto-extractible
  - Support pour les dépendances portables (Python, Node.js, Qdrant)
  - Configuration automatique de l'environnement

- **Scripts de Portabilité**
  - `portable_installer.bat` pour créer la structure d'installation
  - `setup_portable.bat` pour configurer les dépendances portables
  - `start_portable.bat` pour démarrer avec les versions portables
  - `clean_qdrant_portable.bat` pour le nettoyage

### Nettoyage
- Suppression des fichiers temporaires et de test
- Organisation des scripts et de la documentation
- Optimisation de la structure du projet

### Documentation
- Nouvelle documentation `PORTABLE.md` pour l'installation portable
- Mise à jour du README avec la section sur la portabilité
- Mise à jour de NEXT.md avec les dernières fonctionnalités

## [0.2.0] - 2025-02-25

### Amélioré
- **Recherche de Documents**
  - Augmentation du nombre de documents retournés de 4 à 6
  - Réduction du seuil de similarité de 0.6 à 0.5
  - Meilleure couverture des informations pertinentes

- **Génération de Réponses**
  - Ajustement de la température de 0.3 à 0.5
  - Meilleur équilibre entre précision et naturel des réponses
  - Utilisation du modèle Claude 3 Sonnet

- **Gestion des Sources**
  - Réduction du seuil de score pour les sources de 0.7 à 0.6
  - Ajout des informations de page et section dans les métadonnées
  - Tri des sources par score de pertinence

### Documentation
- Mise à jour de NEXT.md avec les dernières améliorations
- Mise à jour de MONITORING.md avec les nouveaux paramètres
- Ajout du CHANGELOG.md pour suivre l'historique des modifications

## [0.1.0] - 2025-02-24

### Ajouté
- Implémentation initiale du système RAG
- Interface avec Claude pour la génération de réponses
- Système de recherche sémantique avec VoyageAI
- Classification des questions (simples/techniques)

### Documentation
- Documentation initiale du projet
- Guide de configuration
- Instructions de déploiement

## Types de Changements
- `Ajouté` pour les nouvelles fonctionnalités
- `Modifié` pour les changements dans les fonctionnalités existantes
- `Déprécié` pour les fonctionnalités bientôt supprimées
- `Supprimé` pour les fonctionnalités supprimées
- `Corrigé` pour les corrections de bugs
- `Sécurité` pour les mises à jour de sécurité
- `Documentation` pour les mises à jour de la documentation
