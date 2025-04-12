# WebSocket Implementation

## Architecture WebSocket

### Endpoints
```python
# API principale RAG
ws://localhost:8000/api/v1/ws

# Tableau de bord OCR (en cours de développement)
ws://localhost:8000/ws/dashboard           # Mises à jour générales du tableau de bord
ws://localhost:8000/ws/active-tasks        # Mises à jour en temps réel des tâches actives
ws://localhost:8000/ws/task/{task_id}      # Mises à jour spécifiques à une tâche
ws://localhost:8000/ws/metrics             # Mises à jour des métriques de performance
```

### Implémentation Actuelle

L'implémentation du WebSocket sert à différentes fonctionnalités dans l'application :

1. **API RAG** :
   - **Diffusion des questions de suivi** : Une fois qu'une réponse a été générée par le LLM, des questions de suivi sont générées en arrière-plan et diffusées à tous les clients connectés.
   - **Mise à jour de l'état d'indexation** : Les progrès de l'indexation des documents peuvent être diffusés à tous les clients.

2. **Tableau de bord OCR** (en cours de développement) :
   - **Mises à jour en temps réel des tâches** : État, progression et logs des tâches OCR en cours (backend implémenté, intégration frontend en cours)
   - **Diffusion des métriques de performance** : Statistiques et graphiques mis à jour en temps réel (en développement)
   - **Notifications d'événements** : Alertes pour les tâches terminées, erreurs ou seuils atteints (planifié)

> **⚠️ Note importante ⚠️**  
> Les fonctionnalités WebSocket pour le tableau de bord OCR sont actuellement en cours de développement.
> Les endpoints mentionnés sont définis dans le code, mais certaines fonctionnalités backend sont encore
> en cours d'implémentation et l'intégration frontend est en développement actif.

#### Code du point d'entrée WebSocket (API RAG)
```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        websocket_manager.disconnect(websocket)
```

#### Code de diffusion des questions de suivi
```python
async def generate_follow_up_questions(query: str, response: str, rag_engine: RAGEngine):
    """Génère les questions de suivi en arrière-plan."""
    try:
        questions = await rag_engine.llm_interface.generate_follow_up_questions(query, response)
        if questions:
            await websocket_manager.broadcast({
                "type": "follow_up_questions",
                "questions": questions
            })
    except Exception as e:
        logger.error(f"Erreur lors de la génération des questions de suivi: {str(e)}")
```

### Types de Messages

1. **Messages Serveur (Actuels)**
```json
{
    "type": "follow_up_questions",
    "questions": [
        "Question 1 ?",
        "Question 2 ?",
        "Question 3 ?"
    ]
}
```

### Évolutions Prévues

Pour une implémentation future plus complète, les formats de messages suivants sont prévus :

1. **Messages Client (Futurs)**
```json
{
    "type": "query",
    "content": {
        "question": "Comment faire X ?",
        "context": {}
    }
}
```

2. **Messages Serveur (Futurs)**
```json
{
    "type": "response",
    "content": {
        "answer": "...",
        "sources": []
    }
}

{
    "type": "error",
    "content": {
        "message": "...",
        "code": "ERROR_CODE"
    }
}
```

## Gestionnaire WebSocket

La classe `WebSocketManager` gère les connexions et la diffusion des messages :

```python
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Nouvelle connexion WebSocket. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Déconnexion WebSocket. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi du message WebSocket: {str(e)}")
                # Supprimer la connexion si elle est morte
                self.active_connections.remove(connection)
```

## Intégration Frontend

Du côté frontend, une connexion WebSocket est établie et gérée comme suit :

```javascript
// Dans src/components/WebSocketHandler.jsx
import { useEffect } from 'react';

function WebSocketHandler({ onMessage }) {
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws');
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };
    
    return () => {
      ws.close();
    };
  }, [onMessage]);
  
  return null;
}

export default WebSocketHandler;
