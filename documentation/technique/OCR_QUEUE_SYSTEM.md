# Système de File d'Attente OCR

## Vue d'ensemble

Le système de file d'attente OCR est une solution complète pour gérer efficacement les tâches OCR longues et complexes, en particulier pour les documents volumineux. Il résout les problèmes de timeout et de ressources limités en introduisant un mécanisme robuste de mise en file d'attente avec priorité, de traitement par lots, et de reprise sur erreur.

**Fonctionnalités principales:**
- File d'attente avec gestion des priorités
- Traitement de documents par chunks
- Interface de gestion des tâches (pause, reprise, annulation)
- Système de notification en temps réel via WebSockets
- Métriques détaillées et tableau de bord
- API RESTful pour l'intégration avec d'autres systèmes

## Architecture

Le système est composé de plusieurs modules interdépendants:

```
┌───────────────────┐      ┌────────────────────┐     ┌────────────────────┐
│                   │      │                    │     │                    │
│  OCRQueueManager  │◄────►│  BaseOCRQueueMgr   │◄───►│    TaskManager     │
│                   │      │                    │     │                    │
└─────────┬─────────┘      └────────────────────┘     └────────────────────┘
          │
          │
┌─────────▼─────────┐      ┌────────────────────┐
│                   │      │                    │
│   REST API        │◄────►│  WebSocket API     │
│                   │      │                    │
└───────────────────┘      └────────────────────┘
          ▲
          │
┌─────────▼─────────┐      ┌────────────────────┐
│                   │      │                    │
│  Dashboard UI     │◄────►│ Document Processor │
│                   │      │                    │
└───────────────────┘      └────────────────────┘
```

### Composants clés

1. **OCRQueueManager**: Gestionnaire principal de la file d'attente
2. **BaseOCRQueueManager**: Gestionnaire de base pour les opérations OCR
3. **TaskManager**: Gestion des tâches, checkpoints et reprise sur erreur
4. **REST API**: Endpoints pour interagir avec le système
5. **WebSocket API**: Notifications en temps réel
6. **Dashboard UI**: Interface utilisateur pour le suivi et la gestion
7. **Document Processor**: Traitement OCR des documents

## Flux de traitement

1. **Soumission de document**:
   - Le document est soumis via l'API REST
   - Une tâche est créée et ajoutée à la file d'attente avec priorité

2. **Mise en file d'attente**:
   - La tâche attend dans la file selon sa priorité
   - Les tâches critiques sont traitées en premier

3. **Traitement par chunks**:
   - Le document est divisé en chunks de taille configurable
   - Chaque chunk est traité indépendamment
   - Progrès et statut sont mis à jour en temps réel

4. **Gestion des erreurs**:
   - Les erreurs sont capturées et classifiées
   - Les chunks défaillants peuvent être automatiquement réessayés
   - Des checkpoints permettent la reprise après interruption

5. **Fusion des résultats**:
   - Les chunks traités sont fusionnés en un document final
   - Le document est stocké à l'emplacement spécifié

6. **Notification**:
   - Les clients sont notifiés via WebSockets de l'avancement
   - Le tableau de bord est mis à jour en temps réel

## API REST

L'API REST expose les fonctionnalités suivantes:

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/ocr/tasks` | POST | Ajoute une tâche OCR à la file d'attente |
| `/api/ocr/upload` | POST | Télécharge et soumet un document pour OCR |
| `/api/ocr/tasks/{task_id}` | GET | Récupère le statut d'une tâche |
| `/api/ocr/tasks/{task_id}/pause` | POST | Met en pause une tâche |
| `/api/ocr/tasks/{task_id}/resume` | POST | Reprend une tâche en pause |
| `/api/ocr/tasks/{task_id}/cancel` | POST | Annule une tâche |
| `/api/ocr/tasks` | GET | Liste les tâches selon des critères |
| `/api/ocr/stats` | GET | Récupère des statistiques sur la file d'attente |

## WebSockets

Les WebSockets permettent de recevoir des mises à jour en temps réel:

| Endpoint | Description |
|----------|-------------|
| `/ws/ocr/task/{task_id}` | Mises à jour pour une tâche spécifique |
| `/ws/ocr/all` | Mises à jour pour toutes les tâches et statistiques |

## Configuration

Le système est configurable via plusieurs paramètres:

| Paramètre | Description | Valeur par défaut |
|-----------|-------------|-------------------|
| `max_concurrent_tasks` | Nombre maximal de tâches simultanées | 3 |
| `chunk_size` | Taille des chunks en nombre de pages | 5 |
| `chunk_timeout` | Timeout pour le traitement d'un chunk (secondes) | 300 |
| `throttle_interval` | Intervalle minimal entre notifications WebSocket (secondes) | 0.5 |
| `completed_task_retention` | Durée de conservation des tâches terminées (heures) | 24 |

## Exemples d'utilisation

### Soumettre un document pour OCR

```python
import requests

response = requests.post(
    "http://localhost:8000/api/ocr/tasks",
    json={
        "document_path": "/path/to/document.pdf",
        "priority": "HIGH",
        "options": {
            "ocr_provider": "document_ai",
            "language": "fra"
        },
        "metadata": {
            "description": "Document technique"
        }
    }
)

task_id = response.json()["task_id"]
print(f"Tâche OCR créée: {task_id}")
```

### Suivre l'avancement via WebSocket

```javascript
const socket = new WebSocket(`ws://localhost:8000/ws/ocr/task/${taskId}`);

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`Progression: ${data.progress * 100}%`);
    updateProgressBar(data.progress);
};
```

## Diagnostic et Dépannage

### Problèmes courants

1. **Timeouts**: Si les documents sont très volumineux, augmenter `chunk_size` et `chunk_timeout`.
2. **Ressources insuffisantes**: Réduire `max_concurrent_tasks` si le serveur manque de ressources.
3. **Erreurs OCR**: Vérifier les logs pour identifier le fournisseur OCR défaillant.

### Logs

Les logs détaillés sont disponibles dans:
- `logs/ocr_queue.log`: Logs de la file d'attente
- `logs/tasks.log`: Logs des tâches individuelles
- `logs/api.log`: Logs des appels API

## Prochaines améliorations

Le système pourra être étendu avec:

1. **Gestion des ressources adaptative**: Ajustement dynamique des ressources allouées
2. **Priorisation intelligente**: Apprentissage des priorités basé sur l'historique
3. **Métriques avancées**: Analyses de performance par type de document
4. **Interface de diagnostic**: Outils visuels pour identifier les problèmes OCR
5. **Intégration avec d'autres systèmes**: Webhooks pour notifications externes
