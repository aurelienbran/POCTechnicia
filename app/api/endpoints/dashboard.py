"""
Module d'API pour le tableau de bord OCR.

Ce module implémente les endpoints API REST pour le tableau de bord OCR,
permettant de récupérer des statistiques, des métriques et d'effectuer
des actions sur les tâches OCR.

Auteur: Équipe de Développement Technicia
Date: 1 avril, 2025
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.core.auth.dependencies import get_current_user, get_current_active_user
from app.core.tasks.task_manager import TaskManager
from app.core.file_processing.ocr.ocr_provider import OCRProviderRegistry
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.api.websockets.dashboard import connection_manager

# Configuration du router
router = APIRouter(prefix="/dashboard", tags=["dashboard-api"])

# Gestionnaires
task_manager = TaskManager()
ocr_provider_registry = OCRProviderRegistry()


# Modèles Pydantic pour les requêtes et réponses

class TaskActionRequest(BaseModel):
    """Modèle pour une demande d'action sur une tâche."""
    action: str = Field(..., description="Action à effectuer (pause, resume, cancel, retry)")
    

class TaskActionResponse(BaseModel):
    """Modèle pour la réponse à une action sur une tâche."""
    success: bool
    message: str
    task_id: str
    new_status: Optional[str] = None


class TaskStatisticsResponse(BaseModel):
    """Modèle pour les statistiques de tâches."""
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    avg_processing_time: float
    success_rate: float


class OCRProviderPerformance(BaseModel):
    """Modèle pour les performances d'un fournisseur OCR."""
    provider_id: str
    provider_name: str
    tasks_count: int
    avg_processing_time: float
    success_rate: float
    avg_confidence: float


class OCRPerformanceResponse(BaseModel):
    """Modèle pour les performances des fournisseurs OCR."""
    providers: List[OCRProviderPerformance]
    best_provider: str
    fastest_provider: str


# Endpoints API

@router.get("/statistics", response_model=TaskStatisticsResponse)
async def get_task_statistics(
    period: Optional[str] = Query("week", description="Période (day, week, month, quarter, year)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupère les statistiques globales des tâches OCR.
    
    Args:
        period: Période d'analyse
        
    Returns:
        Statistiques des tâches OCR
    """
    # Détermination de la période
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
    
    # Récupération des statistiques
    stats = await task_manager.get_task_statistics(start_date=start_date, end_date=end_date)
    
    return TaskStatisticsResponse(
        total_tasks=stats.get("total_tasks", 0),
        active_tasks=stats.get("active_tasks", 0),
        completed_tasks=stats.get("completed_tasks", 0),
        failed_tasks=stats.get("failed_tasks", 0),
        avg_processing_time=stats.get("avg_processing_time", 0.0),
        success_rate=stats.get("success_rate", 0.0)
    )


@router.get("/performance", response_model=OCRPerformanceResponse)
async def get_ocr_performance(
    period: Optional[str] = Query("week", description="Période (day, week, month, quarter, year)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupère les performances des différents fournisseurs OCR.
    
    Args:
        period: Période d'analyse
        
    Returns:
        Performances des fournisseurs OCR
    """
    # Détermination de la période
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
    
    # Récupération des performances
    performances = await task_manager.get_ocr_performance_metrics(
        start_date=start_date, 
        end_date=end_date
    )
    
    # Préparation de la réponse
    providers_perf = []
    best_provider = ""
    fastest_provider = ""
    best_success_rate = 0.0
    fastest_time = float('inf')
    
    for provider_id, metrics in performances.items():
        provider_perf = OCRProviderPerformance(
            provider_id=provider_id,
            provider_name=metrics.get("name", provider_id),
            tasks_count=metrics.get("tasks_count", 0),
            avg_processing_time=metrics.get("avg_processing_time", 0.0),
            success_rate=metrics.get("success_rate", 0.0),
            avg_confidence=metrics.get("avg_confidence", 0.0)
        )
        providers_perf.append(provider_perf)
        
        # Détermination du meilleur fournisseur et du plus rapide
        if provider_perf.success_rate > best_success_rate:
            best_success_rate = provider_perf.success_rate
            best_provider = provider_id
        
        if provider_perf.avg_processing_time < fastest_time and provider_perf.tasks_count > 0:
            fastest_time = provider_perf.avg_processing_time
            fastest_provider = provider_id
    
    return OCRPerformanceResponse(
        providers=providers_perf,
        best_provider=best_provider,
        fastest_provider=fastest_provider
    )


@router.post("/tasks/{task_id}/action", response_model=TaskActionResponse)
async def task_action(
    task_id: str = Path(..., description="Identifiant de la tâche"),
    action_request: TaskActionRequest = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Effectue une action sur une tâche OCR.
    
    Args:
        task_id: Identifiant de la tâche
        action_request: Action à effectuer
        
    Returns:
        Résultat de l'action sur la tâche
    """
    # Vérification que la tâche existe
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Tâche non trouvée: {task_id}")
    
    # Exécution de l'action demandée
    action = action_request.action.lower()
    success = False
    message = ""
    
    if action == "pause":
        success = await task_manager.pause_task(task_id, str(current_user.id))
        message = "Tâche mise en pause" if success else "Impossible de mettre la tâche en pause"
    
    elif action == "resume":
        success = await task_manager.resume_task(task_id, str(current_user.id))
        message = "Tâche reprise" if success else "Impossible de reprendre la tâche"
    
    elif action == "cancel":
        success = await task_manager.cancel_task(task_id, str(current_user.id))
        message = "Tâche annulée" if success else "Impossible d'annuler la tâche"
    
    elif action == "retry":
        success = await task_manager.retry_task(task_id, str(current_user.id))
        message = "Tâche relancée" if success else "Impossible de relancer la tâche"
    
    else:
        raise HTTPException(status_code=400, detail=f"Action non reconnue: {action}")
    
    # En cas de succès, récupérer le nouveau statut et notifier les clients WebSocket
    new_status = None
    if success:
        updated_task = await task_manager.get_task(task_id)
        if updated_task:
            new_status = updated_task.status.value
            
            # Notification WebSocket
            await connection_manager.broadcast_task_update(
                task_id,
                {"task": updated_task.dict(), "action": action}
            )
    
    return TaskActionResponse(
        success=success,
        message=message,
        task_id=task_id,
        new_status=new_status
    )


@router.get("/tasks/active", response_model=List[Task])
async def get_active_tasks(
    provider: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupère la liste des tâches OCR actives.
    
    Args:
        provider: Filtre par fournisseur OCR
        status: Filtre par statut
        priority: Filtre par priorité
        limit: Nombre maximum de résultats
        offset: Décalage pour la pagination
        
    Returns:
        Liste des tâches OCR actives
    """
    # Construction des filtres
    filters = {}
    if provider:
        filters["ocr_provider"] = provider
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    
    # Récupération des tâches actives
    tasks = await task_manager.get_active_tasks(
        filters=filters,
        limit=limit,
        offset=offset
    )
    
    return tasks


@router.get("/tasks/history", response_model=List[Task])
async def get_task_history(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    provider: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupère l'historique des tâches OCR terminées.
    
    Args:
        start_date: Date de début pour le filtre
        end_date: Date de fin pour le filtre
        provider: Filtre par fournisseur OCR
        status: Filtre par statut
        limit: Nombre maximum de résultats
        offset: Décalage pour la pagination
        
    Returns:
        Liste des tâches OCR de l'historique
    """
    # Construction des filtres
    filters = {}
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date
    if provider:
        filters["ocr_provider"] = provider
    if status:
        filters["status"] = status
    
    # Récupération de l'historique des tâches
    tasks = await task_manager.get_completed_tasks(
        filters=filters,
        limit=limit,
        offset=offset
    )
    
    return tasks
