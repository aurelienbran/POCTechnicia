"""
WebSockets pour le tableau de bord OCR
======================================

Ce module implémente les fonctionnalités WebSocket pour le tableau de bord OCR,
permettant des mises à jour en temps réel des statuts des tâches sans polling.

Caractéristiques principales:
- Notification en temps réel des changements de statut des tâches OCR
- Mise à jour automatique de la progression des tâches
- Diffusion sélective par ID de tâche ou pour toutes les tâches
- Throttling intégré pour éviter la surcharge du client
- Mécanisme de reconnexion automatique côté client

Auteur: Équipe Technicia
Date: Avril 2025
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timedelta
import time
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException

from app.core.tasks.ocr_queue_manager import get_ocr_queue_manager, OCRTaskStatus
from app.core.auth.dependencies import get_current_user_ws
from app.models.user import User

logger = logging.getLogger(__name__)


class OCRDashboardManager:
    """
    Gestionnaire des connexions WebSocket pour le tableau de bord OCR.
    
    Cette classe gère les connexions WebSocket actives et la diffusion des
    mises à jour des tâches OCR en temps réel.
    
    Attributes:
        active_connections (Dict[str, List[WebSocket]]): Connexions actives par ID de tâche
        all_task_connections (List[WebSocket]): Connexions pour toutes les tâches
        last_update (Dict[str, Dict[str, Any]]): Dernière mise à jour par ID de tâche et connexion
        last_broadcast (Dict[str, float]): Heure de la dernière diffusion par ID de tâche
        throttle_interval (float): Intervalle minimum entre les diffusions (en secondes)
    """
    
    def __init__(self, throttle_interval: float = 0.5):
        """
        Initialise le gestionnaire de WebSockets pour le tableau de bord OCR.
        
        Args:
            throttle_interval: Intervalle minimum entre les diffusions (en secondes)
        """
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.all_task_connections: List[WebSocket] = []
        self.last_update: Dict[str, Dict[str, Any]] = {}
        self.last_broadcast: Dict[str, float] = {}
        self.throttle_interval = throttle_interval
        
        # Enregistrer le callback de notification
        queue_manager = get_ocr_queue_manager()
        queue_manager.register_notification_callback(self.notify_task_update)
    
    async def connect(self, websocket: WebSocket, task_id: Optional[str] = None):
        """
        Établit une connexion WebSocket.
        
        Cette méthode accepte une nouvelle connexion WebSocket et l'ajoute aux
        listes appropriées en fonction de l'ID de tâche spécifié.
        
        Args:
            websocket: Connexion WebSocket à établir
            task_id: ID de tâche pour les mises à jour spécifiques (None pour toutes les tâches)
        """
        await websocket.accept()
        
        if task_id:
            # Connexion pour une tâche spécifique
            if task_id not in self.active_connections:
                self.active_connections[task_id] = []
            self.active_connections[task_id].append(websocket)
            
            # Envoyer immédiatement le statut actuel
            queue_manager = get_ocr_queue_manager()
            status = await queue_manager.get_task_status(task_id)
            if status:
                await websocket.send_json(status)
        else:
            # Connexion pour toutes les tâches
            self.all_task_connections.append(websocket)
            
            # Envoyer immédiatement les statistiques
            queue_manager = get_ocr_queue_manager()
            stats = await queue_manager.get_queue_stats()
            await websocket.send_json({"type": "stats", "data": stats})
    
    async def disconnect(self, websocket: WebSocket, task_id: Optional[str] = None):
        """
        Ferme une connexion WebSocket.
        
        Cette méthode supprime une connexion WebSocket des listes appropriées
        en fonction de l'ID de tâche spécifié.
        
        Args:
            websocket: Connexion WebSocket à fermer
            task_id: ID de tâche associé (None pour les connexions globales)
        """
        if task_id:
            if task_id in self.active_connections:
                if websocket in self.active_connections[task_id]:
                    self.active_connections[task_id].remove(websocket)
                
                # Nettoyer si la liste est vide
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]
        else:
            if websocket in self.all_task_connections:
                self.all_task_connections.remove(websocket)
    
    async def notify_task_update(self, task_id: str, task_info: Dict[str, Any]):
        """
        Notifie les clients des mises à jour d'une tâche.
        
        Cette méthode est appelée par le gestionnaire de file d'attente OCR
        lorsqu'une tâche est mise à jour. Elle diffuse les mises à jour aux
        clients connectés, avec throttling pour éviter la surcharge.
        
        Args:
            task_id: ID de la tâche mise à jour
            task_info: Informations sur la tâche
        """
        # Vérifier le throttling pour cette tâche
        current_time = time.time()
        if task_id in self.last_broadcast:
            time_since_last = current_time - self.last_broadcast[task_id]
            if time_since_last < self.throttle_interval:
                # Stocker la mise à jour pour diffusion ultérieure
                self.last_update[task_id] = task_info
                return
        
        # Mettre à jour l'heure de dernière diffusion
        self.last_broadcast[task_id] = current_time
        
        # Supprimer toute mise à jour en attente
        if task_id in self.last_update:
            del self.last_update[task_id]
        
        # Diffuser aux connexions pour cette tâche
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(task_info)
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi d'une mise à jour à une connexion: {e}")
                    # La connexion sera nettoyée lors de la prochaine tentative
        
        # Diffuser à toutes les connexions
        message = {"type": "task_update", "task_id": task_id, "data": task_info}
        await self.broadcast_to_all(message)
        
        # Mettre à jour les statistiques pour toutes les connexions
        await self.update_stats()
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """
        Diffuse un message à toutes les connexions.
        
        Args:
            message: Message à diffuser
        """
        closed_connections = []
        
        for connection in self.all_task_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Erreur lors de la diffusion: {e}")
                closed_connections.append(connection)
        
        # Nettoyer les connexions fermées
        for connection in closed_connections:
            if connection in self.all_task_connections:
                self.all_task_connections.remove(connection)
    
    async def update_stats(self):
        """
        Met à jour les statistiques pour toutes les connexions.
        """
        # Obtenir les statistiques actuelles
        queue_manager = get_ocr_queue_manager()
        stats = await queue_manager.get_queue_stats()
        
        # Diffuser les statistiques
        message = {"type": "stats", "data": stats}
        await self.broadcast_to_all(message)
    
    async def send_updates(self):
        """
        Envoie les mises à jour en attente.
        
        Cette méthode est appelée périodiquement pour envoyer les mises à jour
        qui ont été throttled.
        """
        updates = list(self.last_update.items())
        for task_id, task_info in updates:
            await self.notify_task_update(task_id, task_info)


# Instance singleton du gestionnaire
dashboard_manager = OCRDashboardManager()


async def start_update_service():
    """
    Démarre le service de mise à jour périodique.
    
    Cette fonction doit être appelée au démarrage de l'application pour
    initialiser le service d'envoi des mises à jour en attente.
    """
    while True:
        await asyncio.sleep(0.5)  # Toutes les 500ms
        await dashboard_manager.send_updates()


# Handler WebSocket pour une tâche spécifique
async def websocket_task_endpoint(websocket: WebSocket, task_id: str):
    """
    Endpoint WebSocket pour une tâche spécifique.
    
    Cette fonction gère une connexion WebSocket pour suivre les mises à jour
    d'une tâche OCR spécifique.
    
    Args:
        websocket: Connexion WebSocket
        task_id: ID de la tâche à suivre
    """
    await dashboard_manager.connect(websocket, task_id)
    try:
        while True:
            # Attendre des messages (ping/pong)
            data = await websocket.receive_text()
            # Les messages du client sont ignorés pour l'instant
    except WebSocketDisconnect:
        await dashboard_manager.disconnect(websocket, task_id)


# Handler WebSocket pour toutes les tâches
async def websocket_all_tasks_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket pour toutes les tâches.
    
    Cette fonction gère une connexion WebSocket pour suivre les mises à jour
    de toutes les tâches OCR et les statistiques globales.
    
    Args:
        websocket: Connexion WebSocket
    """
    await dashboard_manager.connect(websocket)
    try:
        while True:
            # Attendre des messages (ping/pong)
            data = await websocket.receive_text()
            # Les messages du client sont ignorés pour l'instant
    except WebSocketDisconnect:
        await dashboard_manager.disconnect(websocket)
