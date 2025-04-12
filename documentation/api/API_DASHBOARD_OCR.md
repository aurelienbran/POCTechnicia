# API du Tableau de Bord OCR

> **⚠️ ÉTAT DE DÉVELOPPEMENT ⚠️**  
> Ce document décrit l'API du tableau de bord OCR dont certaines parties sont encore en cours de développement.
> L'état de chaque endpoint est indiqué :
> - ✅ Entièrement implémenté et fonctionnel
> - 🔄 En cours de développement
> - ⏳ Planifié, mais pas encore implémenté
>
> Dernière mise à jour : 1 avril 2025

## Base URL

```
/api/dashboard
```

## Authentification

Toutes les routes de l'API nécessitent une authentification. Utilisez le token JWT dans l'en-tête Authorization :

```
Authorization: Bearer <token>
```

## Endpoints

### 1. Statistiques Globales

Récupère les statistiques globales des tâches OCR.

**URL** : `/api/dashboard/statistics`

**Méthode** : `GET`

**Paramètres de requête** :
- `period` (optionnel) : Période d'analyse (day, week, month, quarter, year). Par défaut : "week"

**Statut** : ✅ Implémenté

**Réponse** :
```json
{
  "total_tasks": 120,
  "active_tasks": 5,
  "completed_tasks": 105,
  "failed_tasks": 10,
  "avg_processing_time": 45.2,
  "success_rate": 0.91
}
```

**Exemple de requête** :
```bash
curl -X GET \
  -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/dashboard/statistics?period=month"
```

### 2. Performances des fournisseurs OCR

Récupère les performances des différents fournisseurs OCR.

**URL** : `/api/dashboard/ocr-performance`

**Méthode** : `GET`

**Paramètres de requête** :
- `period` (optionnel) : Période d'analyse (day, week, month, quarter, year). Par défaut : "week"

**Statut** : 🔄 En cours d'implémentation

**Réponse** :
```json
{
  "providers": [
    {
      "provider_id": "ocrmypdf",
      "provider_name": "OCRmyPDF",
      "tasks_count": 50,
      "avg_processing_time": 42.3,
      "success_rate": 0.94,
      "avg_confidence": 0.89
    },
    {
      "provider_id": "tesseract_direct",
      "provider_name": "Tesseract Direct",
      "tasks_count": 35,
      "avg_processing_time": 28.1,
      "success_rate": 0.87,
      "avg_confidence": 0.78
    }
  ],
  "best_provider": "ocrmypdf",
  "fastest_provider": "tesseract_direct"
}
```

### 3. Liste des Tâches Actives

Récupère la liste des tâches OCR actives.

**URL** : `/api/dashboard/tasks`

**Méthode** : `GET`

**Paramètres de requête** :
- `provider` (optionnel) : Filtre par fournisseur OCR
- `status` (optionnel) : Filtre par statut
- `priority` (optionnel) : Filtre par priorité
- `limit` (optionnel) : Nombre maximum de résultats (1-100). Par défaut : 50
- `offset` (optionnel) : Décalage pour la pagination. Par défaut : 0

**Statut** : ✅ Implémenté

**Réponse** :
```json
[
  {
    "task_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
    "document_id": "doc123",
    "document_name": "rapport_technique.pdf",
    "status": "processing",
    "priority": "high",
    "ocr_provider": "ocrmypdf",
    "progress": 75,
    "created_at": "2025-03-31T14:22:31Z",
    "started_at": "2025-03-31T14:22:35Z",
    "estimated_completion": "2025-03-31T14:30:00Z"
  },
  ...
]
```

### 4. Historique des Tâches

Récupère l'historique des tâches OCR terminées.

**URL** : `/api/dashboard/task-history`

**Méthode** : `GET`

**Paramètres de requête** :
- `start_date` (optionnel) : Date de début pour le filtre (format ISO)
- `end_date` (optionnel) : Date de fin pour le filtre (format ISO)
- `provider` (optionnel) : Filtre par fournisseur OCR
- `status` (optionnel) : Filtre par statut
- `limit` (optionnel) : Nombre maximum de résultats (1-100). Par défaut : 50
- `offset` (optionnel) : Décalage pour la pagination. Par défaut : 0

**Statut** : ✅ Implémenté

**Réponse** :
```json
[
  {
    "task_id": "b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7",
    "document_id": "doc456",
    "document_name": "contrat_client.pdf",
    "status": "completed",
    "ocr_provider": "ocrmypdf",
    "created_at": "2025-03-30T10:15:22Z",
    "completed_at": "2025-03-30T10:22:47Z",
    "processing_time": 445,
    "pages_processed": 12,
    "confidence_score": 0.92,
    "error": null
  },
  ...
]
```

### 5. Actions sur les Tâches

Effectue une action sur une tâche OCR spécifique.

**URL** : `/api/dashboard/tasks/{task_id}/action`

**Méthode** : `POST`

**Paramètres de chemin** :
- `task_id` : Identifiant de la tâche

**Corps de la requête** :
```json
{
  "action": "pause" // Valeurs possibles : "pause", "resume", "cancel", "retry"
}
```

**Statut** : 🔄 En cours d'implémentation

**Réponse** :
```json
{
  "success": true,
  "message": "Tâche mise en pause avec succès",
  "task_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "new_status": "paused"
}
```

## API d'Exportation

Base URL: `/api/export`

### 1. Exporter l'Historique des Tâches

Exporte l'historique des tâches OCR au format spécifié.

**URL** : `/api/export/task-history`

**Méthode** : `POST`

**Paramètres de requête** :
- `format` : Format d'exportation (csv, pdf, json)
- `start_date` (optionnel) : Date de début pour le filtre
- `end_date` (optionnel) : Date de fin pour le filtre
- `provider` (optionnel) : Filtre par fournisseur OCR
- `status` (optionnel) : Filtre par statut

**Statut** : ✅ Implémenté

**Réponse** :
- Pour CSV et JSON : Contenu direct du fichier avec le Content-Type approprié
- Pour PDF : Statut de l'exportation avec un identifiant pour télécharger le fichier ultérieurement

```json
{
  "status": "processing",
  "export_id": "exp-a1b2c3d4",
  "message": "Export PDF en cours de génération",
  "download_url": "/api/export/download/exp-a1b2c3d4"
}
```

### 2. Exporter les Métriques OCR

Exporte les métriques de performance OCR au format spécifié.

**URL** : `/api/export/ocr-metrics`

**Méthode** : `POST`

**Paramètres de requête** :
- `format` : Format d'exportation (csv, pdf, json)
- `period` (optionnel) : Période d'analyse (day, week, month, quarter, year). Par défaut : "month"
- `provider` (optionnel) : Filtre par fournisseur OCR

**Statut** : ✅ Implémenté

**Réponse** :
- Similaire à l'exportation de l'historique des tâches

### 3. Télécharger un Export

Télécharge un export généré précédemment.

**URL** : `/api/export/download/{export_id}`

**Méthode** : `GET`

**Paramètres de chemin** :
- `export_id` : Identifiant de l'exportation

**Statut** : ✅ Implémenté

**Réponse** :
- Fichier exporté avec le Content-Type approprié

## WebSockets

Le tableau de bord utilise également des WebSockets pour les mises à jour en temps réel.

### 1. Connexion WebSocket

**URL** : `/ws/dashboard`

**Protocole** : WebSocket

**Statut** : 🔄 En cours d'implémentation

### 2. Événements WebSocket

Le serveur envoie les événements suivants aux clients connectés :

- `task_update` : Mise à jour du statut d'une tâche
- `new_task` : Nouvelle tâche créée
- `task_completed` : Tâche terminée
- `task_failed` : Échec d'une tâche
- `system_status` : Statut du système OCR

**Format des messages** :
```json
{
  "event": "task_update",
  "data": {
    "task_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
    "status": "processing",
    "progress": 75,
    "timestamp": "2025-03-31T14:25:12Z"
  }
}
```

## Prochaines Évolutions de l'API (Planifiées)

Les fonctionnalités suivantes sont planifiées pour les futures versions de l'API :

1. **Création de tâches OCR manuelles** ⏳ : Endpoint pour créer des tâches OCR manuellement
2. **Optimisation des paramètres OCR** ⏳ : API pour personnaliser les paramètres OCR pour différents types de documents
3. **Gestion de profils OCR** ⏳ : CRUD pour les profils OCR prédéfinis
4. **Statistiques avancées** ⏳ : Métriques de performance détaillées et analytiques
5. **Intégration avec le système de notifications** ⏳ : Gestion des notifications pour les événements OCR importants
