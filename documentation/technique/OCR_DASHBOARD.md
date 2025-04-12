# Tableau de bord OCR - Documentation technique

## Vue d'ensemble

Le tableau de bord OCR est une interface utilisateur complète permettant de suivre et de gérer les tâches de reconnaissance optique de caractères (OCR) dans l'application Technicia. Il offre des fonctionnalités de surveillance en temps réel, de contrôle des tâches et de visualisation de statistiques.

Date de création : Avril 2025  
Statut : Opérationnel  
Auteur : Équipe Technicia

## Architecture

Le tableau de bord OCR repose sur une architecture à plusieurs couches :

1. **Backend**
   - Gestionnaire de file d'attente OCR (OCRQueueManager)
   - API RESTful pour les opérations CRUD
   - Système WebSocket pour les mises à jour en temps réel

2. **Frontend**
   - Interface utilisateur HTML/CSS
   - Script JavaScript pour la gestion des données et des interactions
   - Visualisations graphiques pour les métriques

3. **Communication**
   - WebSockets pour les mises à jour asynchrones
   - API REST pour les opérations manuelles
   - Notifications en temps réel

## Composants principaux

### Backend

#### OCRQueueManager (`app/core/tasks/ocr_queue_manager.py`)

- **Responsabilité** : Gestion de la file d'attente des tâches OCR
- **Fonctionnalités** :
  - Ajout de tâches avec niveau de priorité
  - Pause/reprise/annulation des tâches
  - Allocation des ressources
  - Suivi de la progression
  - Notifications d'événements

```python
# Exemple d'utilisation
from app.core.tasks.ocr_queue_manager import get_ocr_queue_manager

# Obtenir l'instance singleton
manager = get_ocr_queue_manager()

# Ajouter une tâche OCR
task_id = await manager.enqueue_task(
    document_path="/path/to/document.pdf",
    priority=OCRTaskPriority.HIGH
)

# Pause d'une tâche
await manager.pause_task(task_id)

# Reprise d'une tâche
await manager.resume_task(task_id)

# Annulation d'une tâche
await manager.cancel_task(task_id)
```

#### OCR Dashboard API (`app/api/routes/ocr_dashboard.py`)

- **Responsabilité** : Exposition des endpoints API pour l'interface utilisateur
- **Endpoints** :
  - `GET /api/ocr/tasks` : Liste des tâches OCR
  - `POST /api/ocr/tasks` : Ajouter une nouvelle tâche OCR
  - `GET /api/ocr/tasks/{task_id}` : Détails d'une tâche spécifique
  - `PUT /api/ocr/tasks/{task_id}/pause` : Mettre en pause une tâche
  - `PUT /api/ocr/tasks/{task_id}/resume` : Reprendre une tâche
  - `DELETE /api/ocr/tasks/{task_id}` : Annuler une tâche
  - `GET /api/ocr/statistics` : Statistiques globales OCR

#### OCR Socket (`app/api/websocket/ocr_socket.py`)

- **Responsabilité** : Gestion des WebSockets pour les mises à jour en temps réel
- **Fonctionnalités** :
  - Notification des changements d'état des tâches
  - Mise à jour des pourcentages de progression
  - Statistiques en temps réel
  - Notification d'erreurs

```python
# Exemple de handler WebSocket
@socket.on('connect', namespace='/ocr')
async def handle_ocr_connect(sid, environ):
    session_id = environ.get('HTTP_X_SESSION_ID')
    await socket.emit('connection_status', {'status': 'connected'}, room=sid, namespace='/ocr')
    # Ajouter le client à la liste des observateurs
    await add_ocr_observer(sid)
```

### Frontend

#### HTML (`app/templates/ocr_dashboard.html`)

- **Responsabilité** : Structure de l'interface utilisateur
- **Éléments clés** :
  - Tableau des tâches OCR
  - Statistiques et graphiques
  - Formulaire d'upload de documents
  - Zone de détails des tâches

#### JavaScript (`app/static/js/ocr_dashboard.js`)

- **Responsabilité** : Logique client et interaction utilisateur
- **Fonctionnalités** :
  - Connection WebSocket
  - Gestion des interactions utilisateur
  - Mise à jour du tableau de tâches
  - Visualisation des graphiques
  - Gestion du formulaire d'upload

```javascript
// Exemple d'initialisation de la connexion WebSocket
function initializeWebSocket() {
    socket = io('/ocr', {
        path: '/ws/socket.io',
        transports: ['websocket'],
        autoConnect: true
    });
    
    socket.on('connect', () => {
        updateConnectionStatus('connected');
        // Demander les tâches actuelles
        socket.emit('get_tasks');
    });
    
    socket.on('task_update', (data) => {
        updateTaskInTable(data);
        updateStatistics();
    });
}
```

#### CSS (`app/static/css/ocr_dashboard.css`)

- **Responsabilité** : Styles et mise en forme de l'interface
- **Caractéristiques** :
  - Styles pour les différents statuts de tâches
  - Mise en page responsive
  - Animations pour les barres de progression
  - Styles pour les graphiques et statistiques

## Flux de données

1. **Ajout d'une tâche OCR**
   - L'utilisateur soumet un document via le formulaire
   - Les données sont envoyées à l'API (`POST /api/ocr/tasks`)
   - Le backend ajoute la tâche à la file d'attente
   - Une notification WebSocket est envoyée à tous les clients
   - L'interface utilisateur se met à jour pour afficher la nouvelle tâche

2. **Mise à jour d'une tâche**
   - Le gestionnaire de file d'attente modifie l'état d'une tâche
   - Le système WebSocket envoie une notification de mise à jour
   - L'interface JavaScript met à jour l'affichage
   - Les statistiques sont recalculées

3. **Action utilisateur (pause, reprise, annulation)**
   - L'utilisateur clique sur un bouton d'action
   - Une requête API est envoyée
   - Le backend applique l'action et met à jour l'état
   - Une notification WebSocket est envoyée
   - L'interface se met à jour pour refléter le changement

## Considérations techniques

### Performance

- **Optimisations côté serveur**
  - Utilisation d'un gestionnaire de file d'attente asynchrone
  - Limitation de la fréquence des mises à jour WebSocket
  - Mise en cache des statistiques

- **Optimisations côté client**
  - Mise à jour sélective du DOM
  - Throttling des mises à jour fréquentes
  - Lazy loading des composants

### Sécurité

- **Validation des entrées**
  - Filtrage des types de fichiers acceptés (.pdf uniquement)
  - Limite de taille des fichiers uploadés (50 MB)
  - Sanitisation des métadonnées

- **Authentification et autorisation**
  - Middleware d'authentification sur les routes sensibles
  - Validation des sessions WebSocket

### Gestion des erreurs

- **Côté serveur**
  - Logging complet des erreurs
  - Système de retry pour les tâches échouées
  - Notification des erreurs critiques aux administrateurs

- **Côté client**
  - Affichage des messages d'erreur conviviaux
  - Gestion des déconnexions WebSocket
  - Retry automatique des opérations échouées

## Intégration avec d'autres systèmes

Le tableau de bord OCR s'intègre avec plusieurs autres composants du système :

1. **Système de gestion des documents**
   - Récupération des métadonnées des documents
   - Mise à jour de l'index après OCR réussi

2. **Système RAG (Retrieval-Augmented Generation)**
   - Alimente le système RAG avec les documents traités par OCR
   - Contribue à l'amélioration de la recherche sémantique

3. **Système de notification**
   - Envoie des notifications aux utilisateurs pour les tâches longues
   - Alerte sur l'achèvement des tâches critiques

## Évolutions futures

- **Améliorations prévues**
  - Interface de diagnostic avancé pour les problèmes OCR
  - Rapports personnalisés sur la qualité OCR
  - Support pour traitement par lots (batch processing)
  - Interface d'administration pour la configuration globale OCR

- **Intégrations planifiées**
  - Système d'archivage automatique des tâches anciennes
  - Intégration avec des fournisseurs OCR supplémentaires
  - Système de feedback pour améliorer la qualité OCR

## Dépendances

- **Bibliothèques Backend**
  - FastAPI pour l'API RESTful
  - python-socketio pour les WebSockets
  - OCRmyPDF/Tesseract pour le traitement OCR
  - Google Document AI (optionnel)

- **Bibliothèques Frontend**
  - Bootstrap 5 pour l'interface utilisateur
  - Socket.IO client pour les WebSockets
  - Chart.js pour les visualisations
  - Font Awesome pour les icônes

## Références

- [Documentation OCRmyPDF](https://ocrmypdf.readthedocs.io/)
- [API Tesseract](https://github.com/tesseract-ocr/tesseract)
- [Documentation Google Document AI](https://cloud.google.com/document-ai)
- [Documentation OCR Queue Manager](./OCR_QUEUE_SYSTEM.md)
