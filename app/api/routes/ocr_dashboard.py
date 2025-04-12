"""
API pour le tableau de bord OCR
==============================

Ce module fournit des endpoints RESTful pour interagir avec le système de file d'attente
OCR et obtenir des informations sur les tâches en cours, ainsi que pour gérer les tâches
(ajout, pause, reprise, annulation).

Les fonctionnalités principales incluent:
- Ajout de documents à la file d'attente OCR avec priorité
- Récupération du statut des tâches en cours et terminées
- Gestion des tâches (pause, reprise, annulation)
- Statistiques globales sur la file d'attente
- Endpoints pour le tableau de bord

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.tasks.ocr_queue_manager import get_ocr_queue_manager, OCRTask, OCRTaskStatus, OCRTaskPriority
from app.core.auth.dependencies import get_current_user
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/api/ocr", tags=["OCR Dashboard"])
logger = logging.getLogger(__name__)


# Modèles Pydantic pour la validation des requêtes/réponses

class TaskCreate(BaseModel):
    """Modèle pour la création d'une nouvelle tâche OCR."""
    document_path: str
    output_path: Optional[str] = None
    priority: str = "NORMAL"
    options: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskStatus(BaseModel):
    """Modèle pour le statut d'une tâche OCR."""
    task_id: str
    document_path: str
    output_path: Optional[str]
    priority: str
    priority_value: int
    status: str
    added_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    progress: float
    metadata: Dict[str, Any]
    error_message: Optional[str]
    estimated_time_remaining: Optional[int]


class QueueStats(BaseModel):
    """Modèle pour les statistiques de la file d'attente."""
    queue_length: int
    active_tasks: int
    completed_tasks: int
    paused_tasks: int
    max_concurrent_tasks: int
    status_counts: Dict[str, int]
    priority_counts: Dict[str, int]
    avg_processing_time: float
    timestamp: str


# Endpoints pour la gestion des tâches OCR

@router.post("/tasks", response_model=dict)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Ajoute une nouvelle tâche OCR à la file d'attente.
    
    Cette API permet de soumettre un document existant pour traitement OCR.
    Le document doit déjà être présent sur le serveur.
    
    Args:
        task: Informations sur la tâche à créer
        current_user: Utilisateur courant (pour l'authentification)
        
    Returns:
        Dictionnaire contenant l'ID de la tâche créée
    """
    try:
        # Obtenir le gestionnaire de file d'attente
        queue_manager = get_ocr_queue_manager()
        
        # Ajouter des métadonnées utilisateur si non spécifiées
        if "user_id" not in task.metadata and current_user:
            task.metadata["user_id"] = current_user.id
            task.metadata["user_name"] = current_user.username
        
        # Convertir la priorité en enum
        priority = OCRTaskPriority[task.priority]
        
        # Ajouter la tâche à la file d'attente
        task_id = await queue_manager.enqueue_task(
            document_path=task.document_path,
            output_path=task.output_path,
            priority=priority,
            options=task.options,
            metadata=task.metadata
        )
        
        return {"task_id": task_id, "status": "queued"}
        
    except Exception as e:
        logger.exception("Erreur lors de la création d'une tâche OCR")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la tâche: {str(e)}")


@router.post("/upload", response_model=dict)
async def upload_and_process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    priority: str = Form("NORMAL"),
    ocr_provider: str = Form("auto"),
    language: str = Form("fra"),
    metadata: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Télécharge un document et le soumet pour traitement OCR.
    
    Cette API combine le téléchargement d'un fichier et sa soumission pour OCR
    en une seule opération.
    
    Args:
        background_tasks: Tâches en arrière-plan (pour gérer le fichier)
        file: Fichier à télécharger
        priority: Priorité de la tâche
        ocr_provider: Fournisseur OCR à utiliser
        language: Langue du document
        metadata: Métadonnées au format JSON (optionnel)
        current_user: Utilisateur courant (pour l'authentification)
        
    Returns:
        Dictionnaire contenant l'ID de la tâche créée
    """
    try:
        # Créer le répertoire de téléchargement si nécessaire
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = upload_dir / f"{timestamp}_{file.filename}"
        
        # Sauvegarder le fichier
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # Préparer les métadonnées
        task_metadata = {}
        if metadata:
            try:
                task_metadata = json.loads(metadata)
            except:
                pass
        
        # Ajouter des métadonnées utilisateur
        if current_user:
            task_metadata["user_id"] = current_user.id
            task_metadata["user_name"] = current_user.username
        
        task_metadata["original_filename"] = file.filename
        
        # Préparer les options OCR
        options = {
            "ocr_provider": ocr_provider,
            "language": language
        }
        
        # Obtenir le gestionnaire de file d'attente
        queue_manager = get_ocr_queue_manager()
        
        # Convertir la priorité en enum
        task_priority = OCRTaskPriority[priority]
        
        # Ajouter la tâche à la file d'attente
        task_id = await queue_manager.enqueue_task(
            document_path=str(file_path),
            priority=task_priority,
            options=options,
            metadata=task_metadata
        )
        
        return {"task_id": task_id, "filename": file.filename, "status": "queued"}
        
    except Exception as e:
        logger.exception("Erreur lors du téléchargement et traitement OCR")
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")


@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupère le statut d'une tâche OCR.
    
    Args:
        task_id: ID de la tâche
        current_user: Utilisateur courant (pour l'authentification)
        
    Returns:
        Informations détaillées sur la tâche
    """
    try:
        # Obtenir le gestionnaire de file d'attente
        queue_manager = get_ocr_queue_manager()
        
        # Récupérer le statut
        status = await queue_manager.get_task_status(task_id)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"Tâche non trouvée: {task_id}")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur lors de la récupération du statut de la tâche {task_id}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du statut: {str(e)}")


@router.post("/tasks/{task_id}/pause", response_model=dict)
async def pause_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Met en pause une tâche OCR.
    
    Args:
        task_id: ID de la tâche à mettre en pause
        current_user: Utilisateur courant (pour l'authentification)
        
    Returns:
        Résultat de l'opération
    """
    try:
        # Obtenir le gestionnaire de file d'attente
        queue_manager = get_ocr_queue_manager()
        
        # Mettre en pause la tâche
        result = await queue_manager.pause_task(task_id)
        
        if not result:
            raise HTTPException(status_code=400, detail=f"Impossible de mettre en pause la tâche: {task_id}")
        
        return {"task_id": task_id, "status": "paused"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur lors de la mise en pause de la tâche {task_id}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise en pause: {str(e)}")


@router.post("/tasks/{task_id}/resume", response_model=dict)
async def resume_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Reprend une tâche OCR mise en pause.
    
    Args:
        task_id: ID de la tâche à reprendre
        current_user: Utilisateur courant (pour l'authentification)
        
    Returns:
        Résultat de l'opération
    """
    try:
        # Obtenir le gestionnaire de file d'attente
        queue_manager = get_ocr_queue_manager()
        
        # Reprendre la tâche
        result = await queue_manager.resume_task(task_id)
        
        if not result:
            raise HTTPException(status_code=400, detail=f"Impossible de reprendre la tâche: {task_id}")
        
        return {"task_id": task_id, "status": "resumed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur lors de la reprise de la tâche {task_id}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la reprise: {str(e)}")


@router.post("/tasks/{task_id}/cancel", response_model=dict)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Annule une tâche OCR.
    
    Args:
        task_id: ID de la tâche à annuler
        current_user: Utilisateur courant (pour l'authentification)
        
    Returns:
        Résultat de l'opération
    """
    try:
        # Obtenir le gestionnaire de file d'attente
        queue_manager = get_ocr_queue_manager()
        
        # Annuler la tâche
        result = await queue_manager.cancel_task(task_id)
        
        if not result:
            raise HTTPException(status_code=400, detail=f"Impossible d'annuler la tâche: {task_id}")
        
        return {"task_id": task_id, "status": "cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur lors de l'annulation de la tâche {task_id}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'annulation: {str(e)}")


@router.get("/tasks", response_model=List[TaskStatus])
async def list_tasks(
    status: Optional[List[str]] = Query(None, description="Filtrer par statut"),
    limit: int = Query(20, ge=1, le=100, description="Nombre maximum de résultats"),
    offset: int = Query(0, ge=0, description="Index de départ"),
    current_user: User = Depends(get_current_user)
):
    """
    Liste les tâches OCR selon des critères.
    
    Args:
        status: Liste des statuts à inclure (tous si None)
        limit: Nombre maximal de tâches à retourner
        offset: Index de départ pour la pagination
        current_user: Utilisateur courant (pour l'authentification)
        
    Returns:
        Liste des tâches correspondant aux critères
    """
    try:
        # Obtenir le gestionnaire de file d'attente
        queue_manager = get_ocr_queue_manager()
        
        # Convertir les statuts en enum si spécifiés
        status_filter = None
        if status:
            status_filter = [OCRTaskStatus(s) for s in status]
        
        # Récupérer les tâches
        tasks = await queue_manager.list_tasks(
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        
        return tasks
        
    except Exception as e:
        logger.exception("Erreur lors de la récupération des tâches")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des tâches: {str(e)}")


@router.get("/stats", response_model=QueueStats)
async def get_queue_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Obtient des statistiques sur la file d'attente OCR.
    
    Args:
        current_user: Utilisateur courant (pour l'authentification)
        
    Returns:
        Statistiques sur la file d'attente
    """
    try:
        # Obtenir le gestionnaire de file d'attente
        queue_manager = get_ocr_queue_manager()
        
        # Récupérer les statistiques
        stats = await queue_manager.get_queue_stats()
        
        return stats
        
    except Exception as e:
        logger.exception("Erreur lors de la récupération des statistiques")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des statistiques: {str(e)}")
