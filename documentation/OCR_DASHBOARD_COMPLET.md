# Tableau de Bord OCR - Documentation Complète

> **⚠️ NOTE IMPORTANTE : ÉTAT DU DÉVELOPPEMENT ⚠️**  
> Ce document décrit le tableau de bord OCR dont le développement est **actuellement en cours**. 
> Certaines fonctionnalités décrites sont déjà implémentées, d'autres sont en cours de développement ou planifiées.
> L'état d'avancement de chaque fonctionnalité est indiqué comme suit :
> - ✅ Fonctionnalité entièrement implémentée
> - 🔄 Fonctionnalité en cours de développement
> - ⏳ Fonctionnalité planifiée, pas encore implémentée
>
> Dernière mise à jour : 1 avril 2025

## Vue d'ensemble

Le tableau de bord OCR est une interface complète pour la surveillance, la gestion et l'optimisation des tâches de reconnaissance optique de caractères (OCR) dans la plateforme Technicia. Il permet un suivi en temps réel des performances, l'analyse des métriques et l'exportation de rapports détaillés.

### Fonctionnalités principales

- Vue d'ensemble des métriques de performance OCR
- Sélection intelligente du moteur OCR selon le type de document
- Gestion des tâches OCR (création, pause, reprise, annulation)
- Surveillance en temps réel via WebSockets
- Exportation des données et génération de rapports
- Visualisations graphiques et tableaux de bord interactifs
- Optimisation des paramètres OCR basée sur les performances historiques
- Outils de diagnostic avancés pour les problèmes d'OCR

### Architecture du système

Le tableau de bord OCR suit une architecture modulaire :

### 1. Interface utilisateur
- Templates HTML dans `app/templates/dashboard/`
- Styles CSS dans `app/static/dashboard/css/`
- JavaScript pour les interactions dans `app/static/dashboard/js/`

### 2. Backend
- Contrôleurs dans `app/routes/dashboard.py`
- API REST dans `app/api/endpoints/dashboard.py` et `app/api/endpoints/export.py`
- WebSockets dans `app/api/websockets/dashboard.py`

### 3. Services
- `TaskManager` pour la gestion des tâches OCR
- `OCRProviderRegistry` pour l'accès aux différents fournisseurs OCR
- `ExportService` pour la génération d'exports et de rapports

## Accès au tableau de bord

L'accès au tableau de bord OCR se fait via une URL dédiée:

```
http://localhost:8000/dashboard
```

### Authentification

Le tableau de bord utilise le même système d'authentification que le reste de l'application Technicia. L'accès est limité aux utilisateurs autorisés avec les droits appropriés.

## Interfaces et sections principales

### Page d'accueil du tableau de bord

La page d'accueil présente une vue d'ensemble des métriques clés:

- Nombre total de tâches OCR (dernières 24h, 7 jours, 30 jours)
- Taux de réussite global
- Temps de traitement moyen par page et par document
- Graphique des tâches par statut (en attente, en cours, terminées, échouées)
- Liste des tâches récentes

### Suivi des tâches actives

Cette section permet de suivre les tâches OCR actuellement en cours:

- Liste des tâches en temps réel avec indicateurs de progression
- Filtrage par statut, priorité, fournisseur OCR
- Actions possibles: pause, reprise, annulation
- Détails de la tâche avec métriques en direct

### Historique des tâches

Consultation de l'historique complet des tâches OCR:

- Recherche et filtrage avancés
- Visualisation des métriques de performance pour chaque tâche
- Exportation des données (CSV, PDF, JSON)
- Analyse des tendances sur différentes périodes

### Performance des fournisseurs OCR

Cette section permet de comparer les performances des différents fournisseurs OCR:

- Métriques comparatives (précision, vitesse, coût)
- Graphiques de performance par type de document
- Recommandations pour l'utilisation optimale

## API du tableau de bord

Le tableau de bord expose une API REST complète pour l'intégration avec d'autres systèmes:

### Endpoints principaux

| Endpoint | Méthode | Description | État |
|----------|---------|-------------|------|
| `/api/dashboard/tasks` | GET | Liste des tâches OCR | ✅ |
| `/api/dashboard/tasks/{id}` | GET | Détails d'une tâche OCR | ✅ |
| `/api/dashboard/tasks/{id}/action` | POST | Action sur une tâche OCR | 🔄 |
| `/api/dashboard/stats` | GET | Statistiques globales | ✅ |
| `/api/dashboard/stats/provider` | GET | Statistiques par fournisseur | ⏳ |
| `/api/dashboard/export/tasks` | GET | Export des tâches (CSV, PDF, JSON) | ✅ |
| `/api/dashboard/export/metrics` | GET | Export des métriques (CSV, PDF, JSON) | ✅ |

## Fonctionnalités en temps réel

Le tableau de bord utilise WebSockets pour les mises à jour en temps réel des statuts de tâches et des métriques, sans nécessiter de rafraîchissement de page. Les WebSockets sont implémentés via FastAPI et gérés par le module `app/api/websockets/dashboard.py`.

### Architecture WebSocket

L'architecture des WebSockets du tableau de bord OCR comprend les éléments suivants :

#### Gestionnaire de connexions (`DashboardConnectionManager`)

Cette classe centrale gère toutes les connexions WebSocket et assure les fonctionnalités suivantes :
- Gestion des connexions pour différentes vues (tableau de bord, tâches actives, détail de tâche, métriques)
- Diffusion des mises à jour aux clients connectés
- Gestion des déconnexions et des erreurs

#### Endpoints WebSocket

Le module expose quatre endpoints WebSocket principaux :

| Endpoint | Route | Description |
|----------|-------|-------------|
| Tableau de bord | `/ws/dashboard` | Mises à jour générales pour la page d'accueil (statistiques, tâches récentes) |
| Tâches actives | `/ws/active-tasks` | Mises à jour en temps réel sur toutes les tâches en cours |
| Détail de tâche | `/ws/task/{task_id}` | Mises à jour spécifiques pour une tâche (logs, métriques, résultats) |
| Métriques | `/ws/metrics` | Mises à jour des métriques de performance et graphiques |

#### Types de messages

Les WebSockets du tableau de bord utilisent différents types de messages JSON pour la communication :

- `initial_data` : Données initiales envoyées lors de la connexion
- `task_update` : Mise à jour du statut ou de la progression d'une tâche
- `task_completion` : Notification de fin de tâche
- `metrics_update` : Mise à jour des métriques de performance
- `action_result` : Résultat d'une action sur une tâche
- `error` : Message d'erreur

#### Authentification WebSocket

Les connexions WebSocket sont sécurisées via un système d'authentification par token JWT, implémenté dans `app/core/auth/dependencies.py`. La fonction `get_current_user_ws` vérifie la validité du token fourni en paramètre de la requête WebSocket.

### Intégration JavaScript

Les fonctionnalités WebSocket sont intégrées côté client via JavaScript dans `app/static/dashboard/js/dashboard.js`, qui :
- Établit les connexions WebSocket
- Gère les mises à jour en temps réel
- Met à jour l'interface utilisateur dynamiquement

### Flux de données

Le flux de données en temps réel suit le modèle suivant :
1. Le client se connecte à l'endpoint WebSocket approprié
2. Le serveur envoie les données initiales
3. Le client affiche les données et reste en écoute des mises à jour
4. Lorsqu'une tâche est modifiée dans le système, le serveur diffuse la mise à jour aux clients concernés
5. Le client met à jour l'interface utilisateur sans rafraîchissement de page

### Gestion des erreurs

Le système WebSocket comprend une gestion robuste des erreurs :
- Détection des connexions perdues avec tentative de reconnexion automatique
- Validation des messages entrants et sortants
- Circuit-breaker pour éviter les connexions en boucle en cas d'erreur persistante

## API REST du tableau de bord

Le tableau de bord OCR propose une API REST complète pour permettre l'interaction programmatique avec le système et fournir les données nécessaires à l'interface utilisateur.

### Endpoints API

Le module d'API est organisé en deux grandes catégories :

#### 1. API de données du tableau de bord (`/api/dashboard-api/dashboard`)

Ces endpoints fournissent les statistiques, métriques et fonctionnalités de gestion des tâches :

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/statistics` | GET | Récupère les statistiques globales des tâches OCR |
| `/performance` | GET | Récupère les performances des différents fournisseurs OCR |
| `/tasks/{task_id}/action` | POST | Effectue une action sur une tâche OCR (pause, reprise, annulation, relance) |
| `/tasks/active` | GET | Récupère la liste des tâches OCR actives avec filtres optionnels |
| `/tasks/history` | GET | Récupère l'historique des tâches OCR terminées avec filtres optionnels |

#### 2. API d'exportation (`/api/dashboard-api/export`)

Ces endpoints permettent l'exportation des données en différents formats :

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/task-history` | POST | Exporte l'historique des tâches OCR au format CSV, PDF ou JSON |
| `/ocr-metrics` | POST | Exporte les métriques de performance OCR au format CSV, PDF ou JSON |
| `/download/{export_id}` | GET | Télécharge un export généré précédemment |

### Formats d'exportation

L'API supporte trois formats d'exportation principaux :

1. **CSV** : Format tabulaire simple pour l'importation dans des outils de tableur
2. **JSON** : Format structuré pour l'intégration avec d'autres systèmes
3. **PDF** : Rapports formatés avec graphiques et tableaux pour une présentation professionnelle

Pour les exportations PDF, qui peuvent nécessiter un temps de traitement plus long, l'API utilise un système de traitement asynchrone qui :
- Renvoie immédiatement un identifiant d'exportation
- Traite la génération du PDF en arrière-plan
- Permet de télécharger le PDF une fois généré via l'endpoint `/download/{export_id}`

### Actions sur les tâches

L'API permet d'effectuer les actions suivantes sur les tâches OCR :

- **Pause** : Suspend temporairement une tâche en cours
- **Reprise** : Reprend une tâche précédemment mise en pause
- **Annulation** : Arrête définitivement une tâche (impossible à reprendre)
- **Relance** : Redémarre une tâche terminée ou échouée

Chaque action déclenche des notifications en temps réel via WebSocket pour mettre à jour l'interface utilisateur sans rafraîchissement.

### Filtrage et pagination

Les endpoints qui renvoient des listes de tâches ou des métriques supportent le filtrage et la pagination :

- Filtrage par période, fournisseur OCR, statut, priorité
- Pagination avec paramètres `limit` et `offset`
- Tri par différents critères

### Sécurité

Tous les endpoints API sont protégés par authentification JWT via les dépendances :
- `get_current_user` : Vérifie que l'utilisateur est authentifié
- `get_current_active_user` : Vérifie que l'utilisateur est actif
- `get_current_admin_user` : Vérifie que l'utilisateur est administrateur (pour certaines opérations)

## Configuration de l'OCR

Le tableau de bord OCR s'intègre parfaitement avec différents fournisseurs OCR. Pour le traitement des PDFs sans texte (numérisés), l'application utilise une couche OCR qui nécessite les outils suivants :

1. **OCRmyPDF** : Installé via pip, cet outil permet d'ajouter une couche de texte OCR aux PDFs numérisés
2. **Tesseract OCR** : Moteur OCR de base qui doit être installé séparément sur le système
3. **Ghostscript et Poppler** : Dépendances nécessaires pour OCRmyPDF

L'OCR peut être activé via un paramètre optionnel lors de l'upload des documents. Cette fonctionnalité détecte automatiquement si un PDF a besoin d'OCR en vérifiant la présence de texte sélectionnable.

### Fournisseurs OCR supportés

Le système supporte plusieurs fournisseurs OCR, chacun avec ses propres caractéristiques :

1. **Tesseract** (local) :
   - Gratuit et open-source
   - Fonctionne entièrement en local
   - Supporte 100+ langues

2. **Microsoft Azure AI Document Intelligence** (API) :
   - Haute précision pour les documents complexes
   - Extraction structurée (tableaux, formulaires)
   - Nécessite une clé API et des coûts associés

3. **Google Document AI** (API) :
   - Excellente reconnaissance multilangue
   - Extraction de structure sémantique
   - Nécessite une clé API et des coûts associés

4. **Amazon Textract** (API) :
   - Spécialisé dans les formulaires et tableaux
   - Extraction de données de formulaires
   - Nécessite des credentials AWS et des coûts associés

## Installation et dépendances

### Prérequis système
- Python 3.11+
- Node.js et npm pour le frontend
- Base de données PostgreSQL

### Dépendances Python principales
- FastAPI et Uvicorn pour le backend
- Pydantic pour la validation de données
- ReportLab pour la génération de PDFs
- Pandas pour l'analyse de données
- PyJWT pour l'authentification

### Installation OCR (optionnelle)
Pour activer les fonctionnalités OCR complètes, les étapes suivantes sont nécessaires :

1. **Installation de Tesseract OCR** :
   - Windows : Installer via le programme d'installation officiel
   - Linux : `apt-get install tesseract-ocr`
   - macOS : `brew install tesseract`

2. **Installation de Poppler** :
   - Windows : Télécharger depuis le site officiel
   - Linux : `apt-get install poppler-utils`
   - macOS : `brew install poppler`

3. **Installation de Ghostscript** :
   - Windows : Installer via le programme d'installation officiel
   - Linux : `apt-get install ghostscript`
   - macOS : `brew install ghostscript`

4. **Vérification de l'installation** :
   ```bash
   python scripts/verify_ocr_dependencies.py
   ```

## Utilisation

### Navigation et interface utilisateur

- Accédez au tableau de bord OCR via l'URL : `http://localhost:8000/dashboard`
- Utilisez la navigation latérale pour accéder aux différentes vues
- Créez de nouvelles tâches OCR via le formulaire dédié
- Surveillez les tâches actives et consultez les statistiques en temps réel

### Surveillance et gestion des tâches

1. **Création d'une nouvelle tâche OCR** :
   - Accédez à la page d'accueil du tableau de bord
   - Cliquez sur le bouton "Nouvelle tâche OCR"
   - Sélectionnez un fichier PDF à traiter
   - Configurez les options OCR (langue, format de sortie, etc.)
   - Soumettez le formulaire pour démarrer le traitement

2. **Gestion des tâches en cours** :
   - Consultez la liste des tâches actives
   - Utilisez les boutons d'action pour gérer les tâches (pause, reprise, annulation)
   - Suivez la progression en temps réel grâce aux mises à jour WebSocket

3. **Analyse des résultats** :
   - Accédez aux détails d'une tâche en cliquant sur son identifiant
   - Consultez les métriques de performance et les logs d'exécution
   - Téléchargez les résultats OCR une fois le traitement terminé

### Rapports et exports

1. **Génération de rapports de performance** :
   - Accédez à la page de métriques
   - Sélectionnez la période d'analyse et les filtres souhaités
   - Cliquez sur "Générer rapport" et choisissez le format d'export

2. **Export de l'historique des tâches** :
   - Accédez à la page d'historique
   - Appliquez les filtres souhaités
   - Cliquez sur "Exporter" et choisissez le format d'export
   - Téléchargez le fichier d'export une fois généré

## Dépannage

### Problèmes WebSocket courants

- **Connexion WebSocket perdue** : Vérifiez votre connexion réseau et actualisez la page
- **Mises à jour en temps réel non reçues** : Assurez-vous que le service WebSocket est actif
- **Erreurs d'authentification** : Vérifiez que votre session est active et reconnectez-vous si nécessaire

### Problèmes OCR courants

- **Tâche OCR bloquée** : Vérifiez les logs système pour identifier le problème
- **Qualité OCR insuffisante** : Ajustez les paramètres OCR (résolution, langue, etc.)
- **Erreur de fournisseur OCR** : Vérifiez la connectivité avec le fournisseur et les clés API

## Annexe : Configuration avancée

### Variables d'environnement

Les variables d'environnement suivantes peuvent être configurées pour personnaliser le comportement du tableau de bord OCR :

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `DASHBOARD_REFRESH_INTERVAL` | Intervalle de rafraîchissement des données (ms) | 5000 |
| `MAX_CONCURRENT_OCR_TASKS` | Nombre maximum de tâches OCR simultanées | 5 |
| `OCR_DEFAULT_PROVIDER` | Fournisseur OCR par défaut | tesseract |
| `OCR_OUTPUT_DIR` | Répertoire de sortie des résultats OCR | ./data/ocr_results |

### Personnalisation de l'interface

L'interface du tableau de bord peut être personnalisée en modifiant les fichiers CSS et templates HTML. Les principaux fichiers de style se trouvent dans `app/static/dashboard/css/`.

### Extension des fournisseurs OCR

Pour ajouter un nouveau fournisseur OCR au système, suivez ces étapes :

1. Créez une nouvelle classe héritant de `BaseOCRProvider` dans `app/core/ocr/providers/`
2. Implémentez les méthodes requises : `process_document()`, `get_supported_languages()`, etc.
3. Enregistrez le nouveau fournisseur dans `OCRProviderRegistry`

## Roadmap future

### Fonctionnalités planifiées

1. **Phase 1 (Complétée)** :
   - Interface utilisateur de base pour le tableau de bord
   - Intégration WebSocket pour les mises à jour en temps réel
   - API REST pour les données et actions sur les tâches

2. **Phase 2 (En cours)** :
   - Amélioration des rapports et exports
   - Interface utilisateur pour la configuration des fournisseurs OCR
   - Système d'alerte et de notification avancé

3. **Phase 3 (Planifiée)** :
   - Intégration de l'IA pour l'optimisation automatique des paramètres OCR
   - Support pour les formats de documents additionnels (TIFF, JPEG, etc.)
   - Dashboard mobile responsive

## Documentation associée

Pour une compréhension complète du système OCR intégré à la plateforme Technicia, consultez également les documents suivants :

- [INSTALLATION_OCR.md](./INSTALLATION_OCR.md) - Guide d'installation détaillé des dépendances OCR
- [OCR_HYBRIDE.md](./OCR_HYBRIDE.md) - Documentation technique du système hybride d'OCR
- [DOCUMENT_PROCESSING.md](./DOCUMENT_PROCESSING.md) - Traitement des documents et extraction de texte
- [API_DOCUMENT_PROCESSING.md](./api/API_DOCUMENT_PROCESSING.md) - API pour le traitement des documents
- [DIAGNOSTICS.md](./DIAGNOSTICS.md) - Outils de diagnostic et d'analyse de qualité OCR
- [MONITORING.md](./MONITORING.md) - Surveillance et métriques de performance OCR

Ces documents complémentaires fournissent des informations détaillées sur les aspects spécifiques du système OCR qui peuvent être utiles pour les développeurs, administrateurs et utilisateurs avancés.
