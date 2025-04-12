"""
API pour le tableau de bord OCR
==============================

Ce module implémente les points d'entrée API pour le tableau de bord
de suivi des tâches OCR. Il fournit des méthodes pour récupérer, mettre à jour
et gérer les tâches et les métriques de performance.

Caractéristiques principales:
- Endpoints pour la gestion des tâches OCR (création, mise à jour, récupération)
- Endpoints pour les métriques de performance des moteurs OCR
- Intégration avec le TaskManager pour la gestion des tâches
- Support pour les notifications en temps réel des changements d'état

Auteur: Équipe Technicia
Date: Mars 2025
"""

import logging
import json
import datetime
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, Path, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.core.tasks.error_handling import TaskManager, TaskState, TaskCheckpoint, TaskError
from app.core.tasks.dashboard.models import TaskInfo, OCRProviderMetrics, get_dashboard_store, DashboardStore

logger = logging.getLogger(__name__)

# Création du router FastAPI
router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)

# Modèles Pydantic pour l'API
class TaskCreate(BaseModel):
    """Modèle pour la création d'une tâche."""
    name: str = Field(..., description="Nom de la tâche")
    description: str = Field("", description="Description de la tâche")
    document_path: str = Field(..., description="Chemin vers le document à traiter")
    output_path: Optional[str] = Field(None, description="Chemin de sortie pour le document traité")
    ocr_provider: str = Field("auto", description="Fournisseur OCR à utiliser")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées supplémentaires")

class TaskUpdate(BaseModel):
    """Modèle pour la mise à jour d'une tâche."""
    state: Optional[str] = Field(None, description="Nouvel état de la tâche")
    progress: Optional[float] = Field(None, description="Nouvelle progression")
    current_page: Optional[int] = Field(None, description="Page actuelle")
    total_pages: Optional[int] = Field(None, description="Nombre total de pages")
    processing_time: Optional[float] = Field(None, description="Temps de traitement en secondes")
    output_path: Optional[str] = Field(None, description="Chemin de sortie mis à jour")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Métadonnées mises à jour")

class CheckpointCreate(BaseModel):
    """Modèle pour la création d'un checkpoint."""
    state: Dict[str, Any] = Field(..., description="État à sauvegarder")
    current_page: int = Field(0, description="Page actuelle")
    total_pages: int = Field(0, description="Nombre total de pages")

class ErrorCreate(BaseModel):
    """Modèle pour l'enregistrement d'une erreur."""
    error_type: str = Field(..., description="Type d'erreur")
    error_message: str = Field(..., description="Message d'erreur")
    traceback: Optional[str] = Field(None, description="Traceback de l'erreur")
    recoverable: bool = Field(True, description="Si l'erreur est récupérable")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contexte supplémentaire")

class TaskInfoResponse(BaseModel):
    """Modèle pour la réponse contenant les informations sur une tâche."""
    task_id: str
    name: str
    description: str
    document_path: str
    output_path: Optional[str]
    ocr_provider: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    state: str
    progress: float
    current_page: int
    total_pages: int
    processing_time: float
    checkpoints: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    duration: float
    estimated_completion_time: Optional[str]
    
    @classmethod
    def from_task_info(cls, task: TaskInfo) -> 'TaskInfoResponse':
        """Convertit un TaskInfo en TaskInfoResponse."""
        data = task.to_dict()
        
        # Ajouter les propriétés calculées
        data["duration"] = task.duration
        data["estimated_completion_time"] = task.estimated_completion_time.isoformat() if task.estimated_completion_time else None
        
        return cls(**data)

class OCRProviderMetricsResponse(BaseModel):
    """Modèle pour la réponse contenant les métriques d'un fournisseur OCR."""
    provider_name: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_pages: int
    total_processing_time: float
    average_quality_score: float
    document_types: Dict[str, int]
    error_types: Dict[str, int]
    last_updated: str
    success_rate: float
    average_processing_time_per_page: float
    
    @classmethod
    def from_provider_metrics(cls, metrics: OCRProviderMetrics) -> 'OCRProviderMetricsResponse':
        """Convertit un OCRProviderMetrics en OCRProviderMetricsResponse."""
        data = metrics.to_dict()
        
        # Ajouter les propriétés calculées
        data["success_rate"] = metrics.success_rate
        data["average_processing_time_per_page"] = metrics.average_processing_time_per_page
        
        return cls(**data)

# Dépendances
def get_store():
    """Dépendance pour récupérer le gestionnaire de stockage."""
    return get_dashboard_store()

def get_task_manager():
    """Dépendance pour récupérer le gestionnaire de tâches."""
    return TaskManager()

# Endpoints pour les tâches
@router.post("/tasks", response_model=TaskInfoResponse, status_code=201)
async def create_task(
    task_create: TaskCreate,
    background_tasks: BackgroundTasks,
    store: DashboardStore = Depends(get_store),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    Crée une nouvelle tâche OCR.
    
    Args:
        task_create: Données pour la création de la tâche
        background_tasks: Tâches d'arrière-plan FastAPI
        store: Gestionnaire de stockage
        task_manager: Gestionnaire de tâches
        
    Returns:
        TaskInfoResponse: Informations sur la tâche créée
    """
    # Générer un ID pour la tâche
    task_id = task_manager.register_task(
        task_type="ocr_processing",
        document_path=task_create.document_path
    )
    
    # Créer la tâche
    task = TaskInfo(
        task_id=task_id,
        name=task_create.name,
        description=task_create.description,
        document_path=task_create.document_path,
        output_path=task_create.output_path,
        ocr_provider=task_create.ocr_provider,
        metadata=task_create.metadata
    )
    
    # Enregistrer la tâche
    store.add_task(task)
    
    # Notifier les clients WebSocket en arrière-plan
    background_tasks.add_task(notify_task_change, task)
    
    return TaskInfoResponse.from_task_info(task)

@router.get("/tasks/{task_id}", response_model=TaskInfoResponse)
async def get_task(
    task_id: str = Path(..., description="ID de la tâche à récupérer"),
    store: DashboardStore = Depends(get_store)
):
    """
    Récupère les informations sur une tâche.
    
    Args:
        task_id: ID de la tâche
        store: Gestionnaire de stockage
        
    Returns:
        TaskInfoResponse: Informations sur la tâche
    """
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} non trouvée")
    
    return TaskInfoResponse.from_task_info(task)

@router.put("/tasks/{task_id}", response_model=TaskInfoResponse)
async def update_task(
    task_update: TaskUpdate,
    task_id: str = Path(..., description="ID de la tâche à mettre à jour"),
    background_tasks: BackgroundTasks = None,
    store: DashboardStore = Depends(get_store)
):
    """
    Met à jour une tâche existante.
    
    Args:
        task_update: Données pour la mise à jour
        task_id: ID de la tâche
        background_tasks: Tâches d'arrière-plan FastAPI
        store: Gestionnaire de stockage
        
    Returns:
        TaskInfoResponse: Informations sur la tâche mise à jour
    """
    # Récupérer la tâche
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} non trouvée")
    
    # Préparer les mises à jour
    updates = {}
    
    # État
    if task_update.state is not None:
        try:
            updates["state"] = TaskState(task_update.state)
            
            # Mettre à jour les dates de début et de fin si nécessaire
            if updates["state"] == TaskState.RUNNING and not task.started_at:
                updates["started_at"] = datetime.datetime.now()
            elif updates["state"] == TaskState.COMPLETED and not task.completed_at:
                updates["completed_at"] = datetime.datetime.now()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"État invalide: {task_update.state}")
    
    # Autres mises à jour
    for field in ["progress", "current_page", "total_pages", "processing_time", "output_path"]:
        value = getattr(task_update, field)
        if value is not None:
            updates[field] = value
    
    # Métadonnées
    if task_update.metadata is not None:
        updates["metadata"] = {**task.metadata, **task_update.metadata}
    
    # Appliquer les mises à jour
    updated_task = store.update_task(task_id, **updates)
    
    # Notifier les clients WebSocket en arrière-plan
    if background_tasks:
        background_tasks.add_task(notify_task_change, updated_task)
    
    return TaskInfoResponse.from_task_info(updated_task)

@router.post("/tasks/{task_id}/checkpoints", response_model=TaskInfoResponse)
async def create_checkpoint(
    checkpoint_create: CheckpointCreate,
    task_id: str = Path(..., description="ID de la tâche"),
    background_tasks: BackgroundTasks = None,
    store: DashboardStore = Depends(get_store),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    Crée un point de reprise pour une tâche.
    
    Args:
        checkpoint_create: Données pour la création du checkpoint
        task_id: ID de la tâche
        background_tasks: Tâches d'arrière-plan FastAPI
        store: Gestionnaire de stockage
        task_manager: Gestionnaire de tâches
        
    Returns:
        TaskInfoResponse: Informations sur la tâche mise à jour
    """
    # Vérifier que la tâche existe
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} non trouvée")
    
    # Créer le checkpoint dans le task manager
    checkpoint = task_manager.create_checkpoint(
        task_id,
        state=checkpoint_create.state,
        current_page=checkpoint_create.current_page,
        total_pages=checkpoint_create.total_pages
    )
    
    # Mettre à jour la tâche dans le store
    if checkpoint:
        updated_task = store.update_task(
            task_id,
            checkpoints=task.checkpoints + [checkpoint.to_dict()],
            current_page=checkpoint_create.current_page,
            total_pages=checkpoint_create.total_pages
        )
        
        # Notifier les clients WebSocket en arrière-plan
        if background_tasks:
            background_tasks.add_task(notify_task_change, updated_task)
        
        return TaskInfoResponse.from_task_info(updated_task)
    
    # Si le checkpoint n'a pas pu être créé, retourner la tâche sans modification
    return TaskInfoResponse.from_task_info(task)

@router.post("/tasks/{task_id}/errors", response_model=TaskInfoResponse)
async def register_error(
    error_create: ErrorCreate,
    task_id: str = Path(..., description="ID de la tâche"),
    background_tasks: BackgroundTasks = None,
    store: DashboardStore = Depends(get_store),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    Enregistre une erreur pour une tâche.
    
    Args:
        error_create: Données pour l'enregistrement de l'erreur
        task_id: ID de la tâche
        background_tasks: Tâches d'arrière-plan FastAPI
        store: Gestionnaire de stockage
        task_manager: Gestionnaire de tâches
        
    Returns:
        TaskInfoResponse: Informations sur la tâche mise à jour
    """
    # Vérifier que la tâche existe
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} non trouvée")
    
    # Créer l'erreur dans le task manager
    error = task_manager.register_error(
        task_id,
        error_type=error_create.error_type,
        error_message=error_create.error_message,
        traceback=error_create.traceback,
        recoverable=error_create.recoverable,
        context=error_create.context
    )
    
    # Mettre à jour la tâche dans le store
    if error:
        # Si l'erreur n'est pas récupérable, mettre la tâche en échec
        updates = {
            "errors": task.errors + [error.to_dict()]
        }
        
        if not error_create.recoverable:
            updates["state"] = TaskState.FAILED
            updates["completed_at"] = datetime.datetime.now()
        
        updated_task = store.update_task(task_id, **updates)
        
        # Mettre à jour les métriques si la tâche est terminée
        if updated_task.state == TaskState.FAILED:
            store.update_metrics(updated_task.ocr_provider, updated_task)
        
        # Notifier les clients WebSocket en arrière-plan
        if background_tasks:
            background_tasks.add_task(notify_task_change, updated_task)
        
        return TaskInfoResponse.from_task_info(updated_task)
    
    # Si l'erreur n'a pas pu être enregistrée, retourner la tâche sans modification
    return TaskInfoResponse.from_task_info(task)

@router.get("/tasks", response_model=List[TaskInfoResponse])
async def list_tasks(
    state: Optional[str] = Query(None, description="Filtrer par état"),
    active_only: bool = Query(False, description="Récupérer uniquement les tâches actives"),
    limit: int = Query(100, description="Nombre maximum de tâches à récupérer"),
    store: DashboardStore = Depends(get_store)
):
    """
    Récupère la liste des tâches.
    
    Args:
        state: État pour filtrer les tâches
        active_only: Si True, récupère uniquement les tâches actives
        limit: Nombre maximum de tâches à récupérer
        store: Gestionnaire de stockage
        
    Returns:
        List[TaskInfoResponse]: Liste des tâches
    """
    if active_only:
        tasks = store.get_active_tasks()
    else:
        # Récupérer toutes les tâches
        tasks = list(store.tasks.values())
    
    # Filtrer par état si nécessaire
    if state:
        try:
            state_enum = TaskState(state)
            tasks = [task for task in tasks if task.state == state_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"État invalide: {state}")
    
    # Trier par date de création (plus récent en premier)
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    
    # Limiter le nombre de résultats
    tasks = tasks[:limit]
    
    return [TaskInfoResponse.from_task_info(task) for task in tasks]

@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str = Path(..., description="ID de la tâche à supprimer"),
    background_tasks: BackgroundTasks = None,
    store: DashboardStore = Depends(get_store),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    Supprime une tâche.
    
    Args:
        task_id: ID de la tâche
        background_tasks: Tâches d'arrière-plan FastAPI
        store: Gestionnaire de stockage
        task_manager: Gestionnaire de tâches
    """
    # Vérifier que la tâche existe
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} non trouvée")
    
    # Supprimer la tâche
    store.remove_task(task_id)
    
    # Supprimer les checkpoints et erreurs associés
    task_manager.cleanup_task(task_id)
    
    # Notifier les clients WebSocket en arrière-plan
    if background_tasks:
        background_tasks.add_task(notify_task_deletion, task_id)
    
    return None

# Endpoints pour les métriques
@router.get("/metrics", response_model=List[OCRProviderMetricsResponse])
async def list_metrics(
    store: DashboardStore = Depends(get_store)
):
    """
    Récupère les métriques pour tous les fournisseurs OCR.
    
    Args:
        store: Gestionnaire de stockage
        
    Returns:
        List[OCRProviderMetricsResponse]: Liste des métriques
    """
    metrics = store.get_all_metrics()
    return [OCRProviderMetricsResponse.from_provider_metrics(m) for m in metrics.values()]

@router.get("/metrics/{provider}", response_model=OCRProviderMetricsResponse)
async def get_provider_metrics(
    provider: str = Path(..., description="Nom du fournisseur OCR"),
    store: DashboardStore = Depends(get_store)
):
    """
    Récupère les métriques pour un fournisseur OCR spécifique.
    
    Args:
        provider: Nom du fournisseur OCR
        store: Gestionnaire de stockage
        
    Returns:
        OCRProviderMetricsResponse: Métriques pour le fournisseur OCR
    """
    metrics = store.get_metrics(provider)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Métriques non trouvées pour le fournisseur {provider}")
    
    return OCRProviderMetricsResponse.from_provider_metrics(metrics)

# WebSocket pour les notifications en temps réel
active_connections: List[WebSocket] = []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Point d'entrée WebSocket pour les notifications en temps réel.
    
    Args:
        websocket: Connexion WebSocket
    """
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Garder la connexion ouverte jusqu'à la déconnexion
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def notify_task_change(task: TaskInfo):
    """
    Notifie les clients WebSocket d'un changement d'état d'une tâche.
    
    Args:
        task: Tâche mise à jour
    """
    if not active_connections:
        return
    
    # Préparer les données
    data = {
        "type": "task_update",
        "task": TaskInfoResponse.from_task_info(task).dict()
    }
    
    # Envoyer les données à tous les clients
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification WebSocket: {str(e)}")

async def notify_task_deletion(task_id: str):
    """
    Notifie les clients WebSocket de la suppression d'une tâche.
    
    Args:
        task_id: ID de la tâche supprimée
    """
    if not active_connections:
        return
    
    # Préparer les données
    data = {
        "type": "task_deletion",
        "task_id": task_id
    }
    
    # Envoyer les données à tous les clients
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification WebSocket: {str(e)}")

# Intégration avec le gestionnaire de tâches
def register_dashboard_handlers(app):
    """
    Enregistre les gestionnaires d'événements pour le tableau de bord.
    
    Cette fonction doit être appelée lors du démarrage de l'application
    pour intégrer le tableau de bord avec le gestionnaire de tâches.
    
    Args:
        app: Application FastAPI
    """
    store = get_dashboard_store()
    task_manager = TaskManager()
    
    # Gestionnaire pour la création de tâche
    def on_task_created(task_id, task_type, **kwargs):
        # Ignorer les tâches qui ne sont pas des traitements OCR
        if task_type != "ocr_processing":
            return
        
        # Créer la tâche dans le store si elle n'existe pas déjà
        if not store.get_task(task_id):
            task = TaskInfo(
                task_id=task_id,
                name=f"Traitement OCR {task_id}",
                description="Tâche créée automatiquement",
                document_path=kwargs.get("document_path", ""),
                ocr_provider=kwargs.get("ocr_provider", "auto")
            )
            store.add_task(task)
    
    # Gestionnaire pour la mise à jour de la progression
    def on_task_progress(task_id, progress, state=None, current_page=None, total_pages=None):
        # Récupérer la tâche
        task = store.get_task(task_id)
        if not task:
            return
        
        # Préparer les mises à jour
        updates = {"progress": progress}
        
        if state is not None:
            updates["state"] = state
        
        if current_page is not None:
            updates["current_page"] = current_page
        
        if total_pages is not None:
            updates["total_pages"] = total_pages
        
        # Mettre à jour les dates
        if state == TaskState.RUNNING and not task.started_at:
            updates["started_at"] = datetime.datetime.now()
        elif state == TaskState.COMPLETED and not task.completed_at:
            updates["completed_at"] = datetime.datetime.now()
        
        # Appliquer les mises à jour
        updated_task = store.update_task(task_id, **updates)
        
        # Mettre à jour les métriques si la tâche est terminée
        if state == TaskState.COMPLETED:
            store.update_metrics(updated_task.ocr_provider, updated_task)
        
        # Notifier les clients WebSocket
        asyncio.create_task(notify_task_change(updated_task))
    
    # Gestionnaire pour la création de checkpoint
    def on_checkpoint_created(task_id, checkpoint):
        # Récupérer la tâche
        task = store.get_task(task_id)
        if not task:
            return
        
        # Mettre à jour la tâche
        updated_task = store.update_task(
            task_id,
            checkpoints=task.checkpoints + [checkpoint.to_dict()],
            current_page=checkpoint.current_page,
            total_pages=checkpoint.total_pages
        )
        
        # Notifier les clients WebSocket
        asyncio.create_task(notify_task_change(updated_task))
    
    # Gestionnaire pour l'enregistrement d'erreur
    def on_error_registered(task_id, error):
        # Récupérer la tâche
        task = store.get_task(task_id)
        if not task:
            return
        
        # Mettre à jour la tâche
        updates = {
            "errors": task.errors + [error.to_dict()]
        }
        
        if not error.recoverable:
            updates["state"] = TaskState.FAILED
            updates["completed_at"] = datetime.datetime.now()
        
        updated_task = store.update_task(task_id, **updates)
        
        # Mettre à jour les métriques si la tâche est terminée
        if updated_task.state == TaskState.FAILED:
            store.update_metrics(updated_task.ocr_provider, updated_task)
        
        # Notifier les clients WebSocket
        asyncio.create_task(notify_task_change(updated_task))
    
    # Enregistrer les gestionnaires
    task_manager.register_event_handler("task_created", on_task_created)
    task_manager.register_event_handler("task_progress", on_task_progress)
    task_manager.register_event_handler("checkpoint_created", on_checkpoint_created)
    task_manager.register_event_handler("error_registered", on_error_registered)
    
    # Nettoyer régulièrement les anciennes tâches
    @app.on_event("startup")
    def cleanup_old_tasks():
        # Supprimer les tâches terminées depuis plus de 30 jours
        count = store.cleanup_old_tasks(days=30)
        if count > 0:
            logger.info(f"Nettoyage: {count} tâches anciennes supprimées")

# Fonction principale pour ajouter les routes à l'application
def add_dashboard_routes(app):
    """
    Ajoute les routes du tableau de bord à l'application.
    
    Args:
        app: Application FastAPI
    """
    app.include_router(router)
    register_dashboard_handlers(app)
