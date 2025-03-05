"""Gestionnaire de WebSocket pour les communications en temps réel."""
from fastapi import WebSocket
from typing import List, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # Dictionnaire pour suivre le moment du dernier message envoyé à chaque client
        self.last_broadcast_time: Dict[WebSocket, float] = {}
        # Limite la fréquence des broadcasts à un message toutes les 2 secondes par client
        self.broadcast_cooldown = 2.0

    async def connect(self, websocket: WebSocket) -> None:
        """Établit une connexion WebSocket et l'ajoute à la liste des connexions actives."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.last_broadcast_time[websocket] = 0  # Initialiser le timestamp
        # Envoyer un message de type "connected" pour confirmer la connexion
        await websocket.send_json({"type": "connected", "data": {"message": "Connected to indexing WebSocket"}})
        logger.info(f"Nouvelle connexion WebSocket. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Ferme une connexion WebSocket et la retire de la liste des connexions actives."""
        try:
            self.active_connections.remove(websocket)
            if websocket in self.last_broadcast_time:
                del self.last_broadcast_time[websocket]  # Nettoyer le timestamp
            logger.info(f"Déconnexion WebSocket. Total: {len(self.active_connections)}")
        except ValueError:
            pass

    async def handle_message(self, websocket: WebSocket, message: dict) -> None:
        """Gère les messages reçus du client WebSocket."""
        try:
            # Gestion du ping/pong pour vérifier l'état de la connexion
            if message.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "data": {
                        "timestamp": int(time.time() * 1000),
                        "received_timestamp": message.get("data", {}).get("timestamp")
                    }
                })
                return
            
            # Autres types de messages peuvent être gérés ici
            logger.debug(f"Message WebSocket reçu: {message}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message WebSocket: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        current_time = time.time()
        connections_to_remove = []

        for connection in self.active_connections:
            try:
                # Vérifier si on respecte le cooldown pour ce client
                last_time = self.last_broadcast_time.get(connection, 0)
                if current_time - last_time >= self.broadcast_cooldown:
                    await connection.send_json(message)
                    self.last_broadcast_time[connection] = current_time
                else:
                    # Sauter ce client, trop tôt pour lui envoyer un autre message
                    logger.debug(f"Message throttled pour un client (dernier envoi il y a {current_time - last_time:.2f}s)")
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi du message WebSocket: {str(e)}")
                # Marquer la connexion pour suppression
                connections_to_remove.append(connection)
        
        # Supprimer les connexions mortes
        for connection in connections_to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)
            if connection in self.last_broadcast_time:
                del self.last_broadcast_time[connection]

websocket_manager = WebSocketManager()
