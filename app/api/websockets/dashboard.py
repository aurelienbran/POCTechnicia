"""
Module de gestion des WebSockets pour le tableau de bord OCR.

Ce module implémente les connexions WebSocket permettant de fournir
des mises à jour en temps réel sur les tâches OCR aux clients connectés
au tableau de bord. Il permet notamment de notifier les changements
de statut des tâches, les mises à jour de progression et les résultats.

Auteur: Équipe de Développement Technicia
Date: 1 avril, 2025
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth.dependencies import get_current_user_ws
from app.core.tasks.task_manager import TaskManager
from app.core.file_processing.ocr.ocr_provider import OCRProviderRegistry
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.utils.formatters import format_datetime, format_filesize

# Configuration du router
router = APIRouter(prefix="/ws", tags=["websockets"])

# Journalisation
logger = logging.getLogger(__name__)

# Gestionnaires
task_manager = TaskManager()

# Classe de gestionnaire de connexion
class DashboardConnectionManager:
    """
    Gestionnaire de connexions WebSocket pour le tableau de bord.
    
    Cette classe gère toutes les connexions WebSocket actives au tableau de bord,
    permettant d'envoyer des mises à jour aux clients connectés et de gérer
    les abonnements aux tâches et événements.
    """
    
    def __init__(self):
        """Initialisation du gestionnaire de connexion."""
        # Connexions générales (tableau de bord principal)
        self.dashboard_connections: Dict[str, List[WebSocket]] = {}
        
        # Connexions par tâche (pour les pages de détail)
        self.task_connections: Dict[str, List[WebSocket]] = {}
        
        # Connexions par type (vue des tâches actives, historique, métriques)
        self.view_connections: Dict[str, List[WebSocket]] = {
            "active_tasks": [],
            "history": [],
            "metrics": []
        }

    async def connect(self, websocket: WebSocket, user_id: str, view_type: str = "dashboard", task_id: Optional[str] = None):
        """
        Établit une connexion WebSocket.
        
        Args:
            websocket: Objet WebSocket de la connexion
            user_id: Identifiant de l'utilisateur connecté
            view_type: Type de vue (dashboard, active_tasks, history, metrics)
            task_id: Identifiant de la tâche si en vue détaillée
        """
        # Accepter la connexion
        await websocket.accept()
        
        # Enregistrer dans les connexions générales du tableau de bord
        if user_id not in self.dashboard_connections:
            self.dashboard_connections[user_id] = []
        self.dashboard_connections[user_id].append(websocket)
        
        # Si en vue détaillée d'une tâche, enregistrer dans les connexions par tâche
        if task_id:
            if task_id not in self.task_connections:
                self.task_connections[task_id] = []
            self.task_connections[task_id].append(websocket)
        
        # Enregistrer dans les connexions par type de vue
        if view_type in self.view_connections:
            self.view_connections[view_type].append(websocket)
        
        # Log de connexion
        logger.info(f"Nouvelle connexion WebSocket: User {user_id}, View {view_type}, Task {task_id}")

    async def disconnect(self, websocket: WebSocket, user_id: str, view_type: str = "dashboard", task_id: Optional[str] = None):
        """
        Gère la déconnexion d'un WebSocket.
        
        Args:
            websocket: Objet WebSocket de la connexion
            user_id: Identifiant de l'utilisateur connecté
            view_type: Type de vue (dashboard, active_tasks, history, metrics)
            task_id: Identifiant de la tâche si en vue détaillée
        """
        # Supprimer des connexions générales
        if user_id in self.dashboard_connections:
            if websocket in self.dashboard_connections[user_id]:
                self.dashboard_connections[user_id].remove(websocket)
            if not self.dashboard_connections[user_id]:
                del self.dashboard_connections[user_id]
        
        # Supprimer des connexions par tâche
        if task_id and task_id in self.task_connections:
            if websocket in self.task_connections[task_id]:
                self.task_connections[task_id].remove(websocket)
            if not self.task_connections[task_id]:
                del self.task_connections[task_id]
        
        # Supprimer des connexions par type de vue
        if view_type in self.view_connections:
            if websocket in self.view_connections[view_type]:
                self.view_connections[view_type].remove(websocket)
        
        # Log de déconnexion
        logger.info(f"Déconnexion WebSocket: User {user_id}, View {view_type}, Task {task_id}")

    async def broadcast_task_update(self, task_id: str, update_data: Dict[str, Any]):
        """
        Diffuse une mise à jour pour une tâche spécifique.
        
        Args:
            task_id: Identifiant de la tâche mise à jour
            update_data: Données de mise à jour à envoyer
        """
        # Préparer les données de mise à jour
        message = {
            "type": "task_update",
            "task_id": task_id,
            "data": update_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Encodage en JSON
        json_message = json.dumps(message)
        
        # Envoyer aux connexions spécifiques à cette tâche
        if task_id in self.task_connections:
            for connection in self.task_connections[task_id]:
                try:
                    await connection.send_text(json_message)
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi de mise à jour de tâche {task_id}: {str(e)}")
        
        # Envoyer aux connexions de la vue des tâches actives
        for connection in self.view_connections["active_tasks"]:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi aux tâches actives: {str(e)}")
        
        # Envoyer aux connexions du tableau de bord principal
        for user_connections in self.dashboard_connections.values():
            for connection in user_connections:
                try:
                    await connection.send_text(json_message)
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi au tableau de bord: {str(e)}")

    async def broadcast_task_completion(self, task_id: str, task_data: Dict[str, Any]):
        """
        Diffuse une notification de complétion de tâche.
        
        Args:
            task_id: Identifiant de la tâche terminée
            task_data: Données de la tâche à envoyer
        """
        # Préparer les données de mise à jour
        message = {
            "type": "task_completion",
            "task_id": task_id,
            "data": task_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Encodage en JSON
        json_message = json.dumps(message)
        
        # Envoyer aux connexions concernées
        # Tâche spécifique, tâches actives, historique et tableau de bord principal
        connection_sets = []
        
        if task_id in self.task_connections:
            connection_sets.append(self.task_connections[task_id])
        
        connection_sets.append(self.view_connections["active_tasks"])
        connection_sets.append(self.view_connections["history"])
        
        for user_connections in self.dashboard_connections.values():
            connection_sets.append(user_connections)
        
        # Envoi aux connexions
        for connections in connection_sets:
            for connection in connections:
                try:
                    await connection.send_text(json_message)
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi de notification de complétion: {str(e)}")

    async def broadcast_metrics_update(self, metrics_data: Dict[str, Any]):
        """
        Diffuse une mise à jour des métriques de performance.
        
        Args:
            metrics_data: Données de métriques à envoyer
        """
        # Préparer les données de mise à jour
        message = {
            "type": "metrics_update",
            "data": metrics_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Encodage en JSON
        json_message = json.dumps(message)
        
        # Envoyer aux connexions de la vue des métriques
        for connection in self.view_connections["metrics"]:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi des métriques: {str(e)}")
        
        # Envoyer aux connexions du tableau de bord principal (statistiques simplifiées)
        if "summary" in metrics_data:
            dashboard_message = {
                "type": "metrics_summary",
                "data": metrics_data["summary"],
                "timestamp": datetime.now().isoformat()
            }
            dashboard_json = json.dumps(dashboard_message)
            
            for user_connections in self.dashboard_connections.values():
                for connection in user_connections:
                    try:
                        await connection.send_text(dashboard_json)
                    except Exception as e:
                        logger.error(f"Erreur lors de l'envoi du résumé des métriques: {str(e)}")

    async def send_error(self, websocket: WebSocket, error_code: str, error_message: str):
        """
        Envoie un message d'erreur à une connexion WebSocket spécifique.
        
        Args:
            websocket: Objet WebSocket de la connexion
            error_code: Code d'erreur
            error_message: Message d'erreur
        """
        message = {
            "type": "error",
            "error_code": error_code,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message d'erreur: {str(e)}")


# Initialisation du gestionnaire de connexion
connection_manager = DashboardConnectionManager()


# Routes WebSocket

@router.websocket("/dashboard")
async def ws_dashboard(
    websocket: WebSocket,
    user: User = Depends(get_current_user_ws)
):
    """
    WebSocket pour la page d'accueil du tableau de bord.
    
    Fournit des mises à jour en temps réel sur les tâches actives, 
    les tâches récemment terminées et les statistiques globales.
    """
    await connection_manager.connect(websocket, str(user.id), view_type="dashboard")
    
    try:
        # Envoyer l'état initial
        initial_data = await get_dashboard_initial_data()
        await websocket.send_text(json.dumps({
            "type": "initial_data",
            "data": initial_data,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Boucle de maintien de la connexion et traitement des messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Traitement des commandes client
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, str(user.id), view_type="dashboard")
    except Exception as e:
        logger.error(f"Erreur WebSocket dashboard: {str(e)}")
        await connection_manager.disconnect(websocket, str(user.id), view_type="dashboard")


@router.websocket("/active-tasks")
async def ws_active_tasks(
    websocket: WebSocket,
    user: User = Depends(get_current_user_ws)
):
    """
    WebSocket pour la page des tâches actives.
    
    Fournit des mises à jour en temps réel sur toutes les tâches
    en cours, avec leurs statuts et progressions.
    """
    await connection_manager.connect(websocket, str(user.id), view_type="active_tasks")
    
    try:
        # Envoyer l'état initial des tâches actives
        active_tasks = await task_manager.get_active_tasks()
        await websocket.send_text(json.dumps({
            "type": "initial_data",
            "data": {"tasks": [task.dict() for task in active_tasks]},
            "timestamp": datetime.now().isoformat()
        }))
        
        # Boucle de maintien de la connexion et traitement des messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Traitement des commandes client
            if message.get("type") == "task_action":
                task_id = message.get("task_id")
                action = message.get("action")
                
                if task_id and action:
                    result = await process_task_action(task_id, action, str(user.id))
                    await websocket.send_text(json.dumps({
                        "type": "action_result",
                        "task_id": task_id,
                        "action": action,
                        "success": result.get("success", False),
                        "message": result.get("message", ""),
                        "timestamp": datetime.now().isoformat()
                    }))
    
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, str(user.id), view_type="active_tasks")
    except Exception as e:
        logger.error(f"Erreur WebSocket active_tasks: {str(e)}")
        await connection_manager.disconnect(websocket, str(user.id), view_type="active_tasks")


@router.websocket("/task/{task_id}")
async def ws_task_detail(
    websocket: WebSocket,
    task_id: str,
    user: User = Depends(get_current_user_ws)
):
    """
    WebSocket pour la page de détail d'une tâche.
    
    Fournit des mises à jour en temps réel sur une tâche spécifique,
    incluant les logs, métriques et résultats.
    
    Args:
        task_id: Identifiant de la tâche à surveiller
    """
    # Vérification que la tâche existe
    task = await task_manager.get_task(task_id)
    if not task:
        await websocket.accept()
        await connection_manager.send_error(
            websocket, 
            "task_not_found", 
            f"Tâche non trouvée: {task_id}"
        )
        await websocket.close()
        return
    
    await connection_manager.connect(websocket, str(user.id), view_type="task_detail", task_id=task_id)
    
    try:
        # Envoyer l'état initial de la tâche
        task_data = await get_task_detail_data(task_id)
        await websocket.send_text(json.dumps({
            "type": "initial_data",
            "data": task_data,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Boucle de maintien de la connexion et traitement des messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Traitement des commandes client
            if message.get("type") == "task_action":
                action = message.get("action")
                
                if action:
                    result = await process_task_action(task_id, action, str(user.id))
                    await websocket.send_text(json.dumps({
                        "type": "action_result",
                        "action": action,
                        "success": result.get("success", False),
                        "message": result.get("message", ""),
                        "timestamp": datetime.now().isoformat()
                    }))
            
            elif message.get("type") == "get_logs":
                # Récupérer les nouveaux logs depuis un timestamp
                since = message.get("since")
                logs = await task_manager.get_task_logs(task_id, since=since)
                
                await websocket.send_text(json.dumps({
                    "type": "logs_update",
                    "data": logs,
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, str(user.id), view_type="task_detail", task_id=task_id)
    except Exception as e:
        logger.error(f"Erreur WebSocket task_detail: {str(e)}")
        await connection_manager.disconnect(websocket, str(user.id), view_type="task_detail", task_id=task_id)


@router.websocket("/metrics")
async def ws_metrics(
    websocket: WebSocket,
    period: str = "week",
    provider: Optional[str] = None,
    user: User = Depends(get_current_user_ws)
):
    """
    WebSocket pour la page des métriques.
    
    Fournit des mises à jour en temps réel sur les métriques de performance
    des différents fournisseurs OCR.
    
    Args:
        period: Période d'analyse (day, week, month, quarter, year)
        provider: Filtre par fournisseur OCR
    """
    await connection_manager.connect(websocket, str(user.id), view_type="metrics")
    
    try:
        # Envoyer les données initiales des métriques
        metrics_data = await get_metrics_data(period, provider)
        await websocket.send_text(json.dumps({
            "type": "initial_data",
            "data": metrics_data,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Boucle de maintien de la connexion et traitement des messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Traitement des commandes client
            if message.get("type") == "change_filter":
                new_period = message.get("period", period)
                new_provider = message.get("provider", provider)
                
                # Récupérer les métriques avec les nouveaux filtres
                metrics_data = await get_metrics_data(new_period, new_provider)
                await websocket.send_text(json.dumps({
                    "type": "metrics_update",
                    "data": metrics_data,
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, str(user.id), view_type="metrics")
    except Exception as e:
        logger.error(f"Erreur WebSocket metrics: {str(e)}")
        await connection_manager.disconnect(websocket, str(user.id), view_type="metrics")


# Fonctions utilitaires

async def get_dashboard_initial_data():
    """
    Récupère les données initiales pour le tableau de bord.
    
    Returns:
        Dict[str, Any]: Données pour l'initialisation du tableau de bord
    """
    # Récupération des données pour le dashboard
    active_tasks = await task_manager.get_active_tasks(limit=5)
    recent_completed = await task_manager.get_completed_tasks(limit=5)
    task_stats = await task_manager.get_task_statistics()
    ocr_performance = await task_manager.get_ocr_performance_metrics()
    
    return {
        "active_tasks": [task.dict() for task in active_tasks],
        "recent_completed": [task.dict() for task in recent_completed],
        "task_stats": task_stats,
        "ocr_performance": ocr_performance
    }


async def get_task_detail_data(task_id: str):
    """
    Récupère les données détaillées d'une tâche.
    
    Args:
        task_id: Identifiant de la tâche
        
    Returns:
        Dict[str, Any]: Données détaillées de la tâche
    """
    # Récupération des données de la tâche
    task = await task_manager.get_task(task_id)
    task_logs = await task_manager.get_task_logs(task_id)
    task_metrics = await task_manager.get_task_metrics(task_id)
    
    task_results = None
    if task and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        task_results = await task_manager.get_task_results(task_id)
    
    return {
        "task": task.dict() if task else None,
        "logs": task_logs,
        "metrics": task_metrics,
        "results": task_results
    }


async def get_metrics_data(period: str, provider: Optional[str] = None):
    """
    Récupère les données de métriques de performance.
    
    Args:
        period: Période d'analyse (day, week, month, quarter, year)
        provider: Filtre par fournisseur OCR
        
    Returns:
        Dict[str, Any]: Données de métriques
    """
    # Définition de la période
    end_date = datetime.now()
    if period == "day":
        start_date = end_date - timedelta(days=1)
    elif period == "week":
        start_date = end_date - timedelta(weeks=1)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "quarter":
        start_date = end_date - timedelta(days=90)
    else:  # year
        start_date = end_date - timedelta(days=365)
    
    # Récupération des métriques pour la période
    metrics = await task_manager.get_performance_metrics(
        start_date=start_date,
        end_date=end_date,
        provider=provider
    )
    
    # Récupération des données pour les graphiques
    chart_data = await task_manager.get_metrics_chart_data(
        start_date=start_date,
        end_date=end_date,
        provider=provider
    )
    
    return {
        "metrics": metrics,
        "chart_data": chart_data,
        "period": period,
        "provider": provider,
        "summary": {
            "avg_processing_time": metrics.get("avg_processing_time"),
            "success_rate": metrics.get("success_rate"),
            "total_tasks": metrics.get("total_tasks")
        }
    }


async def process_task_action(task_id: str, action: str, user_id: str):
    """
    Traite une action sur une tâche.
    
    Args:
        task_id: Identifiant de la tâche
        action: Action à effectuer (pause, resume, cancel, retry)
        user_id: Identifiant de l'utilisateur effectuant l'action
        
    Returns:
        Dict[str, Any]: Résultat de l'action
    """
    try:
        if action == "pause":
            success = await task_manager.pause_task(task_id, user_id)
            message = "Tâche mise en pause" if success else "Impossible de mettre la tâche en pause"
        
        elif action == "resume":
            success = await task_manager.resume_task(task_id, user_id)
            message = "Tâche reprise" if success else "Impossible de reprendre la tâche"
        
        elif action == "cancel":
            success = await task_manager.cancel_task(task_id, user_id)
            message = "Tâche annulée" if success else "Impossible d'annuler la tâche"
        
        elif action == "retry":
            success = await task_manager.retry_task(task_id, user_id)
            message = "Tâche relancée" if success else "Impossible de relancer la tâche"
        
        else:
            return {"success": False, "message": f"Action non reconnue: {action}"}
        
        # Si l'action a réussi, récupérer la tâche mise à jour
        if success:
            task = await task_manager.get_task(task_id)
            if task:
                # Diffuser la mise à jour aux clients connectés
                await connection_manager.broadcast_task_update(
                    task_id, 
                    {"task": task.dict(), "action": action}
                )
        
        return {"success": success, "message": message}
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'action {action} sur la tâche {task_id}: {str(e)}")
        return {"success": False, "message": f"Erreur système: {str(e)}"}
