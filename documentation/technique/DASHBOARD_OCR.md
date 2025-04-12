# NOTICE : DOCUMENT PARTIEL ET EN COURS DE MISE À JOUR

> ⚠️ **IMPORTANT** ⚠️  
> Ce document contient des informations partielles sur le tableau de bord OCR. 
> Pour une documentation plus complète et à jour, veuillez consulter :
> [OCR_DASHBOARD_COMPLET.md](../OCR_DASHBOARD_COMPLET.md)
>
> Le développement du tableau de bord OCR est actuellement **en cours**.
> Certaines fonctionnalités décrites dans la documentation consolidée sont encore en développement.
> Consultez [SUIVI_IMPLEMENTATION.md](../MVP/SUIVI_IMPLEMENTATION.md) pour connaître l'état d'avancement précis.
>
> Dernière mise à jour : 1 avril 2025

## Vue d'ensemble

Le tableau de bord OCR est une interface complète pour surveiller, gérer et optimiser les tâches de reconnaissance optique de caractères (OCR) au sein de l'application Technicia. Cette documentation présente les composants techniques, l'architecture et l'utilisation du tableau de bord.

**Dernière mise à jour :** 31 mars 2025  
**Auteur :** Équipe de Développement Technicia

## Architecture

Le tableau de bord OCR suit une architecture MVC (Modèle-Vue-Contrôleur) :
- **Modèle :** Représenté par les classes de gestion des tâches et des métriques dans `app/core/tasks/`
- **Vue :** Templates HTML dans `app/templates/dashboard/`
- **Contrôleur :** Logique de routage et de traitement dans `app/routes/dashboard.py`

## Composants

### 1. Interface Utilisateur

L'interface utilisateur du tableau de bord est composée de plusieurs vues principales :

#### Page d'accueil (`index.html`)
- Vue d'ensemble des tâches OCR actives et récemment terminées
- Statistiques globales de performance
- Indicateurs de santé du système OCR

#### Tâches actives (`active_tasks.html`)
- Liste des tâches OCR en cours d'exécution
- Filtres par statut, fournisseur, priorité
- Actions de gestion des tâches (pause, reprise, annulation)

#### Détail de tâche (`task_detail.html`)
- Informations détaillées sur une tâche spécifique
- Logs d'exécution
- Métriques de performance
- Visualisation des résultats pour les tâches terminées

#### Historique (`history.html`)
- Archive des tâches terminées
- Filtres par date, statut, fournisseur
- Statistiques sur les performances historiques
- Exportation des données

#### Métriques (`metrics.html`)
- Visualisation des performances par fournisseur OCR
- Graphiques de tendances
- Comparaison des différents moteurs OCR
- Filtres par période et fournisseur

#### Création de tâche (`new_task.html`)
- Formulaire de configuration et lancement de tâches OCR
- Sélection des paramètres avancés
- Estimation du temps de traitement
- Recommandations basées sur le type de document

### 2. Contrôleur

Le contrôleur du tableau de bord (`app/routes/dashboard.py`) implémente les routes FastAPI suivantes :

| Route | Méthode | Fonction | Description |
|-------|---------|----------|-------------|
| `/dashboard/` | GET | `dashboard_index` | Page d'accueil du tableau de bord |
| `/dashboard/active-tasks` | GET | `dashboard_active_tasks` | Liste des tâches actives |
| `/dashboard/task/{task_id}` | GET | `dashboard_task_detail` | Détails d'une tâche spécifique |
| `/dashboard/history` | GET | `dashboard_history` | Historique des tâches |
| `/dashboard/metrics` | GET | `dashboard_metrics` | Métriques de performance |
| `/dashboard/new-task` | GET | `dashboard_new_task` | Formulaire de création de tâche |
| `/dashboard/create-task` | POST | `dashboard_create_task` | Traitement du formulaire de création |
| `/api/dashboard/queue-status` | GET | `get_queue_status` | État de la file d'attente OCR |

### 3. Filtres Jinja2 personnalisés

Le contrôleur définit plusieurs filtres Jinja2 pour l'affichage formaté des données :

- `format_date` : Formatage des timestamps
- `format_duration` : Conversion des durées en secondes vers un format lisible
- `task_status_class` : Attribution des classes CSS selon le statut de la tâche
- `priority_class` : Attribution des classes CSS selon la priorité de la tâche

## Intégration avec le système existant

Le tableau de bord OCR s'intègre avec plusieurs composants existants :

- **TaskManager** : Gestion des tâches OCR et opérations CRUD
- **OCRProviderRegistry** : Accès aux différents moteurs OCR disponibles
- **Système d'authentification** : Contrôle d'accès via `get_current_user`
- **File d'attente Celery** : Monitoring des tâches asynchrones

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

## Modules et dépendances

- **FastAPI** : Framework web pour les routes et API
- **Jinja2** : Moteur de templates pour les vues HTML
- **Pydantic** : Validation des données pour les modèles
- **Bootstrap 5** : Framework CSS pour l'interface utilisateur
- **Chart.js** : Visualisation des données et métriques

## Sécurité

Toutes les routes du tableau de bord sont protégées par l'authentification via la dépendance `get_current_user`. Des validations supplémentaires sont effectuées pour garantir que les utilisateurs n'accèdent qu'aux ressources autorisées.

## Extensibilité

Le tableau de bord est conçu pour être facilement extensible :

- Nouveaux fournisseurs OCR peuvent être ajoutés sans modifier l'interface
- Métriques personnalisées peuvent être intégrées au système de reporting
- Filtres additionnels peuvent être implémentés selon les besoins

## Limitations connues

- Les graphiques de performance sont actuellement limités aux 30 derniers jours de données
- L'exportation des résultats volumineux peut être lente pour les documents de grande taille
- Certaines métriques avancées nécessitent un historique minimal de données

## Plans futurs

Les futures améliorations prévues pour le tableau de bord OCR incluent :

1. Intégration de notifications en temps réel pour les événements critiques
2. Amélioration des recommandations intelligentes basées sur l'apprentissage automatique
3. Support pour la définition de workflows OCR personnalisés
4. Interface mobile optimisée pour l'accès sur le terrain

## Références

- [Documentation générale OCR](../DOCUMENT_PROCESSING.md)
- [API Reference](../api/README.md)
- [Guide d'utilisation du tableau de bord](../utilisateur/TABLEAU_BORD_OCR.md)
