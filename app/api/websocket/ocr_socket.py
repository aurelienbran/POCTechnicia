"""
Module de gestion WebSocket pour les mises à jour OCR.
"""
import logging
import json
import time
from typing import Dict, List, Any, Optional, Set, Callable
import asyncio
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, APIRouter

# Import du nouveau gestionnaire OCRDashboardManager
from app.api.websockets.ocr_dashboard import dashboard_manager, websocket_task_endpoint, websocket_all_tasks_endpoint, start_update_service

# Créer un router pour les endpoints WebSocket
router = APIRouter()

logger = logging.getLogger(__name__)

class OCRWebSocketManager:
    """
    Gestionnaire de connexions WebSocket pour diffuser les mises à jour OCR.
    """
    
    def __init__(self):
        """Initialise le gestionnaire de connexions WebSocket."""
        self.active_connections: Set[WebSocket] = set()
        # Buffer pour stocker les derniers messages (utile pour les clients qui se connectent en cours de processus)
        self.recent_messages: List[Dict[str, Any]] = []
        self.max_buffer_size = 50
        # Ajout du système de throttling
        self.last_broadcast_time: Dict[WebSocket, float] = {}
        # Cooldown légèrement plus court pour les messages OCR (plus importants)
        self.broadcast_cooldown = 1.0
    
    async def connect(self, websocket: WebSocket) -> None:
        """
        Connecte un client WebSocket et envoie l'historique récent.
        
        Args:
            websocket: La connexion WebSocket à ajouter
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        # Initialiser le timestamp pour ce client
        self.last_broadcast_time[websocket] = 0
        
        # Envoyer les messages récents au nouveau client
        if self.recent_messages:
            try:
                await websocket.send_json({
                    "type": "history",
                    "messages": self.recent_messages
                })
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'historique: {e}")
    
    def disconnect(self, websocket: WebSocket) -> None:
        """
        Déconnecte un client WebSocket.
        
        Args:
            websocket: La connexion WebSocket à supprimer
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # Nettoyer le timestamp
        if websocket in self.last_broadcast_time:
            del self.last_broadcast_time[websocket]
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Diffuse un message à tous les clients connectés.
        
        Args:
            message: Le message à diffuser
        """
        # Ajouter un timestamp s'il n'existe pas
        if "timestamp" not in message:
            message["timestamp"] = time.time()
        
        # Stocker le message dans le buffer
        self.recent_messages.append(message)
        if len(self.recent_messages) > self.max_buffer_size:
            self.recent_messages = self.recent_messages[-self.max_buffer_size:]
        
        current_time = time.time()
        # Diffuser à tous les clients
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                # Vérifier le cooldown pour ce client
                last_time = self.last_broadcast_time.get(connection, 0)
                if current_time - last_time >= self.broadcast_cooldown:
                    await connection.send_json(message)
                    self.last_broadcast_time[connection] = current_time
                else:
                    # Sauter ce client, trop tôt pour envoyer un autre message
                    logger.debug(f"Message OCR throttled (dernier envoi il y a {current_time - last_time:.2f}s)")
            except Exception:
                # Marquer pour suppression
                disconnected.add(connection)
        
        # Supprimer les connexions fermées
        for conn in disconnected:
            self.disconnect(conn)

    async def handle_message(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """
        Traite un message entrant d'un client WebSocket.
        
        Args:
            websocket: La connexion WebSocket qui a envoyé le message
            message: Le message à traiter
        """
        try:
            msg_type = message.get("type")
            
            # Gestion du ping/pong pour maintenir la connexion active
            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "data": {
                        "timestamp": int(time.time() * 1000),
                        "received_timestamp": message.get("data", {}).get("timestamp", 0)
                    }
                })
                logger.debug(f"Message ping reçu, pong envoyé à {websocket.client.host}")
                return
                
            # Gestion d'autres types de messages
            logger.debug(f"Message WebSocket reçu: {msg_type}")
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message WebSocket: {str(e)}")

    def check_and_disconnect_inactive_connections(self):
        """Vérifie et déconnecte les connexions inactives."""
        current_time = time.time()
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                # Vérifier si la connexion est inactive depuis plus de 60 secondes
                last_time = self.last_broadcast_time.get(connection, 0)
                if current_time - last_time >= 60:
                    disconnected.add(connection)
            except Exception:
                # Marquer pour suppression
                disconnected.add(connection)
        
        # Supprimer les connexions fermées
        for conn in disconnected:
            self.disconnect(conn)

class WebSocketLogHandler(logging.Handler):
    """
    Handler de logging qui envoie les messages via WebSocket.
    """
    
    def __init__(self, websocket_manager: OCRWebSocketManager):
        """
        Initialise le handler de logs WebSocket.
        
        Args:
            websocket_manager: Le gestionnaire WebSocket pour diffuser les logs
        """
        super().__init__()
        self.websocket_manager = websocket_manager
        # Filtrer uniquement les logs OCR et indexation
        self.setLevel(logging.INFO)
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Émet un enregistrement de log via WebSocket.
        
        Args:
            record: L'enregistrement de log à émettre
        """
        try:
            # Vérifier si c'est un log pertinent (OCR ou indexation)
            msg = self.format(record)
            if "[OCR]" in msg or "indexation" in msg.lower():
                # Créer un message structuré pour le frontend
                log_entry = {
                    "type": "log",
                    "level": record.levelname,
                    "message": msg,
                    "timestamp": time.time(),
                    "source": "OCR" if "[OCR]" in msg else "indexation"
                }
                
                # Analyser pour la progression
                progress_info = self._extract_progress_info(msg)
                if progress_info:
                    log_entry.update(progress_info)
                
                # Diffuser via WebSocket
                asyncio.create_task(self.websocket_manager.broadcast(log_entry))
        except Exception as e:
            logger.error(f"Erreur lors de l'émission du log WebSocket: {e}")
    
    def _extract_progress_info(self, msg: str) -> Optional[Dict[str, Any]]:
        """
        Extrait les informations de progression des messages de log.
        
        Args:
            msg: Le message de log à analyser
            
        Returns:
            Optional[Dict[str, Any]]: Les informations de progression extraites ou None
        """
        # Pour les logs de progression OCR
        if "[OCR]" in msg and "traitement de la page" in msg:
            try:
                # Extraire les chiffres de progression
                import re
                match = re.search(r'page (\d+)/(\d+) \((\d+)%\)', msg)
                if match:
                    current, total, percent = match.groups()
                    return {
                        "current_page": int(current),
                        "total_pages": int(total),
                        "progress": int(percent),
                        "step": "ocr"
                    }
            except Exception:
                pass
        return None

async def disconnect_inactive_connections(websocket_manager):
    """Tâche périodique pour déconnecter les connexions inactives."""
    while True:
        await asyncio.sleep(30)  # Vérifier toutes les 30 secondes
        try:
            websocket_manager.check_and_disconnect_inactive_connections()
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion des clients inactifs: {e}")

# Initialisation du gestionnaire WebSocket
websocket_manager = OCRWebSocketManager()

# Tâche en arrière-plan pour nettoyer les connexions inactives
background_tasks = set()

async def start_background_tasks():
    """Démarre les tâches en arrière-plan pour le gestionnaire WebSocket."""
    loop = asyncio.get_event_loop()
    task = loop.create_task(disconnect_inactive_connections(websocket_manager))
    background_tasks.add(task)
    
    # Démarrer le service de mise à jour pour le gestionnaire de dashboard OCR
    ocr_task = loop.create_task(start_update_service())
    background_tasks.add(ocr_task)
    
    # S'assurer que les tâches sont correctement suivies
    for task in background_tasks:
        task.add_done_callback(background_tasks.discard)

# Point d'entrée WebSocket principal
@router.websocket("/ws/ocr")
async def websocket_endpoint(websocket: WebSocket):
    """
    Point d'entrée WebSocket pour les mises à jour en temps réel.
    
    Args:
        websocket: La connexion WebSocket à gérer
    """
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                # Si c'est un ping, on répond par un pong
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                
            except json.JSONDecodeError:
                logger.warning(f"Message WebSocket invalide reçu: {data}")
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

# Points d'entrée WebSocket pour le tableau de bord OCR
@router.websocket("/ws/ocr/task/{task_id}")
async def ocr_task_websocket(websocket: WebSocket, task_id: str):
    """
    Point d'entrée WebSocket pour suivre une tâche OCR spécifique.
    
    Args:
        websocket: La connexion WebSocket
        task_id: L'identifiant de la tâche à suivre
    """
    await websocket_task_endpoint(websocket, task_id)

@router.websocket("/ws/ocr/all")
async def ocr_all_tasks_websocket(websocket: WebSocket):
    """
    Point d'entrée WebSocket pour suivre toutes les tâches OCR.
    
    Args:
        websocket: La connexion WebSocket
    """
    await websocket_all_tasks_endpoint(websocket)
