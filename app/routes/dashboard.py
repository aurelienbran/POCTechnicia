"""
Module de contrôleur pour le tableau de bord OCR.

Ce module implémente les routes et la logique métier pour le tableau de bord
de gestion des tâches OCR. Il permet aux utilisateurs de visualiser, créer, 
et gérer les tâches de traitement OCR dans l'application.

Auteur: Équipe de Développement Technicia
Date: 31 mars, 2025
"""

from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.config import settings
from app.core.tasks.task_manager import TaskManager
from app.core.file_processing.ocr.ocr_provider import OCRProviderRegistry
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.utils.formatters import format_datetime, format_filesize

# Configuration du router pour les routes du tableau de bord
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Configuration des templates
templates = Jinja2Templates(directory="app/templates")

# Initialisation des gestionnaires
task_manager = TaskManager()
ocr_provider_registry = OCRProviderRegistry()


# Filtres personnalisés pour Jinja2
@templates.env.filter
def format_date(value: datetime) -> str:
    """Formatage des dates pour l'affichage."""
    return format_datetime(value)


@templates.env.filter
def format_duration(seconds: int) -> str:
    """Formatage des durées en format lisible."""
    if seconds < 60:
        return f"{seconds} secondes"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} heure{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes > 1 else ''}"


@templates.env.filter
def task_status_class(status: TaskStatus) -> str:
    """Retourne la classe CSS correspondant au statut de la tâche."""
    status_classes = {
        TaskStatus.PENDING: "secondary",
        TaskStatus.PROCESSING: "primary",
        TaskStatus.PAUSED: "warning",
        TaskStatus.COMPLETED: "success",
        TaskStatus.FAILED: "danger",
        TaskStatus.CANCELLED: "dark"
    }
    return status_classes.get(status, "secondary")


@templates.env.filter
def priority_class(priority: TaskPriority) -> str:
    """Retourne la classe CSS correspondant à la priorité de la tâche."""
    priority_classes = {
        TaskPriority.LOW: "text-muted",
        TaskPriority.NORMAL: "text-primary",
        TaskPriority.HIGH: "text-warning",
        TaskPriority.URGENT: "text-danger"
    }
    return priority_classes.get(priority, "text-primary")


# Routes pour le tableau de bord

@router.get("/", response_class=HTMLResponse)
async def dashboard_index(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Page d'accueil du tableau de bord OCR.
    
    Affiche un aperçu des tâches actives, des statistiques de performance
    et des indicateurs sur l'état global du système OCR.
    """
    # Récupération des données pour le dashboard
    active_tasks = await task_manager.get_active_tasks(limit=5)
    recent_completed = await task_manager.get_completed_tasks(limit=5)
    
    # Calcul des statistiques
    task_stats = await task_manager.get_task_statistics()
    
    # Performance par fournisseur OCR
    ocr_performance = await task_manager.get_ocr_performance_metrics()
    
    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "user": current_user,
            "active_tasks": active_tasks,
            "recent_completed": recent_completed,
            "task_stats": task_stats,
            "ocr_performance": ocr_performance,
            "page": "dashboard"
        }
    )


@router.get("/active-tasks", response_class=HTMLResponse)
async def dashboard_active_tasks(
    request: Request,
    status: Optional[str] = None,
    provider: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Page des tâches OCR actives.
    
    Affiche toutes les tâches OCR en cours avec possibilité de filtrage
    et d'actions sur ces tâches.
    """
    # Construction des filtres
    filters = {}
    if status:
        filters["status"] = status
    if provider:
        filters["ocr_provider"] = provider
    if priority:
        filters["priority"] = priority
    if search:
        filters["search"] = search
    
    # Récupération des tâches actives avec filtres
    tasks = await task_manager.get_active_tasks(filters=filters)
    
    # Liste des fournisseurs OCR disponibles pour le filtre
    ocr_providers = await ocr_provider_registry.list_providers()
    
    return templates.TemplateResponse(
        "dashboard/active_tasks.html",
        {
            "request": request,
            "user": current_user,
            "tasks": tasks,
            "ocr_providers": ocr_providers,
            "filters": {
                "status": status,
                "provider": provider,
                "priority": priority,
                "search": search
            },
            "page": "active_tasks"
        }
    )


@router.get("/task/{task_id}", response_class=HTMLResponse)
async def dashboard_task_detail(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Page de détail d'une tâche OCR spécifique.
    
    Affiche les informations détaillées sur une tâche, son statut,
    ses métriques de performance et les actions possibles.
    """
    # Récupération des données de la tâche
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    # Récupération des logs de la tâche
    task_logs = await task_manager.get_task_logs(task_id)
    
    # Récupération des métriques de performance pour cette tâche
    task_metrics = await task_manager.get_task_metrics(task_id)
    
    # Si la tâche est terminée, récupérer les résultats
    task_results = None
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        task_results = await task_manager.get_task_results(task_id)
    
    return templates.TemplateResponse(
        "dashboard/task_detail.html",
        {
            "request": request,
            "user": current_user,
            "task": task,
            "task_logs": task_logs,
            "task_metrics": task_metrics,
            "task_results": task_results,
            "page": "task_detail"
        }
    )


@router.get("/history", response_class=HTMLResponse)
async def dashboard_history(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    provider: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Page d'historique des tâches OCR.
    
    Affiche l'historique des tâches OCR terminées avec possibilité
    de filtrage par date, statut, fournisseur, etc.
    """
    # Construction des filtres
    filters = {}
    if start_date:
        filters["start_date"] = datetime.fromisoformat(start_date)
    if end_date:
        filters["end_date"] = datetime.fromisoformat(end_date)
    if status:
        filters["status"] = status
    if provider:
        filters["ocr_provider"] = provider
    if search:
        filters["search"] = search
    
    # Récupération de l'historique des tâches avec filtres
    tasks = await task_manager.get_completed_tasks(filters=filters)
    
    # Calcul des statistiques pour les tâches filtrées
    stats = await task_manager.get_filtered_statistics(filters)
    
    # Liste des fournisseurs OCR disponibles pour le filtre
    ocr_providers = await ocr_provider_registry.list_providers()
    
    return templates.TemplateResponse(
        "dashboard/history.html",
        {
            "request": request,
            "user": current_user,
            "tasks": tasks,
            "stats": stats,
            "ocr_providers": ocr_providers,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "provider": provider,
                "search": search
            },
            "page": "history"
        }
    )


@router.get("/metrics", response_class=HTMLResponse)
async def dashboard_metrics(
    request: Request,
    period: Optional[str] = "week",
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Page des métriques de performance OCR.
    
    Affiche les métriques détaillées sur la performance des différents
    fournisseurs OCR, avec des graphiques et statistiques.
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
    
    # Liste des fournisseurs OCR disponibles pour le filtre
    ocr_providers = await ocr_provider_registry.list_providers()
    
    return templates.TemplateResponse(
        "dashboard/metrics.html",
        {
            "request": request,
            "user": current_user,
            "metrics": metrics,
            "chart_data": chart_data,
            "ocr_providers": ocr_providers,
            "filters": {
                "period": period,
                "provider": provider
            },
            "page": "metrics"
        }
    )


@router.get("/new-task", response_class=HTMLResponse)
async def dashboard_new_task(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Page de création d'une nouvelle tâche OCR.
    
    Affiche un formulaire permettant de configurer et lancer
    une nouvelle tâche OCR.
    """
    # Récupération des fournisseurs OCR disponibles
    ocr_providers = await ocr_provider_registry.list_providers()
    
    # Récupération des documents disponibles pour la sélection
    available_documents = await task_manager.list_available_documents()
    
    # Récupération des dossiers de sortie disponibles
    output_folders = await task_manager.list_output_folders()
    
    return templates.TemplateResponse(
        "dashboard/new_task.html",
        {
            "request": request,
            "user": current_user,
            "ocr_providers": ocr_providers,
            "available_documents": available_documents,
            "output_folders": output_folders,
            "page": "new_task"
        }
    )


# API pour le tableau de bord - endpoints de base

@router.post("/create-task")
async def dashboard_create_task(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint pour créer une nouvelle tâche OCR depuis le formulaire.
    
    Cette route traite le formulaire soumis depuis la page new-task
    et crée une nouvelle tâche OCR avec les paramètres spécifiés.
    
    Le traitement comprend:
    1. Validation des paramètres du formulaire
    2. Gestion du téléchargement de fichier ou sélection d'un document existant
    3. Création d'une nouvelle tâche OCR via le TaskManager
    4. Redirection vers la page de détail de la tâche créée
    
    Returns:
        RedirectResponse: Redirection vers la page des tâches actives ou de détail
    """
    try:
        # Récupération des données du formulaire
        form_data = await request.form()
        
        # Extraction des données de base
        task_name = form_data.get("name")
        if not task_name:
            raise ValueError("Le nom de la tâche est obligatoire")
        
        task_description = form_data.get("description", "")
        priority = form_data.get("priority", "normal")
        
        # Validation de la priorité
        valid_priorities = ["low", "normal", "high", "urgent"]
        if priority not in valid_priorities:
            priority = "normal"
        
        # Conversion de la priorité en enum
        task_priority = TaskPriority.NORMAL
        if priority == "low":
            task_priority = TaskPriority.LOW
        elif priority == "high":
            task_priority = TaskPriority.HIGH
        elif priority == "urgent":
            task_priority = TaskPriority.URGENT
        
        # Extraction des paramètres OCR
        ocr_provider = form_data.get("ocr_provider")
        if not ocr_provider:
            raise ValueError("Le fournisseur OCR est obligatoire")
        
        language = form_data.get("language", "fra")
        output_format = form_data.get("output_format", "pdf")
        dpi = int(form_data.get("dpi", "300"))
        
        # Traitement des options booléennes
        preprocess_image = "preprocess_image" in form_data
        deskew = "deskew" in form_data
        process_background = "process_background" in form_data
        force_ocr = "force_ocr" in form_data
        keep_original = "keep_original" in form_data
        auto_rotate = "auto_rotate" in form_data
        notify_completion = "notify_completion" in form_data
        notify_error = "notify_error" in form_data
        
        # Paramètres personnalisés (JSON)
        custom_parameters = {}
        custom_params_str = form_data.get("custom_parameters", "")
        if custom_params_str:
            try:
                custom_parameters = json.loads(custom_params_str)
            except json.JSONDecodeError:
                # Si le format JSON est invalide, on ignore simplement
                pass
        
        # Traitement du dossier de destination
        output_path = form_data.get("output_path", "")
        
        # Gestion du document source (téléchargement vs sélection)
        document_source = form_data.get("document_source", "upload")
        document_path = None
        
        if document_source == "upload":
            # Traitement du fichier téléchargé
            document_file = form_data.get("document_file")
            if not document_file:
                raise ValueError("Veuillez sélectionner un fichier à traiter")
            
            # Vérification que le document est bien un UploadFile
            if not hasattr(document_file, "filename"):
                raise ValueError("Format de fichier invalide")
            
            # Sauvegarde du fichier téléchargé dans un emplacement temporaire
            document_path = await task_manager.save_uploaded_document(document_file)
        else:
            # Utilisation d'un document existant
            document_path = form_data.get("document_path")
            if not document_path:
                raise ValueError("Veuillez sélectionner un document existant")
        
        # Validation finale
        if not document_path:
            raise ValueError("Impossible de traiter le document fourni")
        
        # Préparation des paramètres OCR
        ocr_params = {
            "provider": ocr_provider,
            "language": language,
            "output_format": output_format,
            "dpi": dpi,
            "preprocess_image": preprocess_image,
            "deskew": deskew,
            "force_ocr": force_ocr,
            "auto_rotate": auto_rotate,
            "custom_parameters": custom_parameters
        }
        
        # Création de la tâche
        task_id = await task_manager.create_ocr_task(
            name=task_name,
            description=task_description,
            document_path=document_path,
            ocr_params=ocr_params,
            priority=task_priority,
            user_id=current_user.id,
            output_path=output_path,
            keep_original=keep_original,
            process_background=process_background,
            notify_completion=notify_completion,
            notify_error=notify_error
        )
        
        # Enregistrement de l'action dans les logs
        logging.info(f"Nouvelle tâche OCR créée: {task_id} par utilisateur {current_user.username}")
        
        # Redirection vers la page de détail de la tâche
        return RedirectResponse(url=f"/dashboard/task/{task_id}", status_code=303)
    
    except ValueError as e:
        # En cas d'erreur de validation, retour à la page du formulaire avec message d'erreur
        return templates.TemplateResponse(
            "dashboard/new_task.html",
            {
                "request": request,
                "user": current_user,
                "error_message": str(e),
                "form_data": dict(form_data),
                "ocr_providers": await ocr_provider_registry.list_providers(),
                "available_documents": await task_manager.list_available_documents(),
                "output_folders": await task_manager.list_output_folders(),
                "page": "new_task"
            },
            status_code=400
        )
    except Exception as e:
        # En cas d'erreur système, log et message d'erreur générique
        logging.error(f"Erreur lors de la création de tâche OCR: {str(e)}")
        return templates.TemplateResponse(
            "dashboard/new_task.html",
            {
                "request": request,
                "user": current_user,
                "error_message": "Une erreur est survenue lors de la création de la tâche. Veuillez réessayer.",
                "form_data": dict(form_data),
                "ocr_providers": await ocr_provider_registry.list_providers(),
                "available_documents": await task_manager.list_available_documents(),
                "output_folders": await task_manager.list_output_folders(),
                "page": "new_task"
            },
            status_code=500
        )


@router.get("/api/dashboard/queue-status")
async def get_queue_status(
    current_user: User = Depends(get_current_user)
):
    """
    API pour récupérer l'état actuel de la file d'attente OCR.
    
    Retourne des informations sur le nombre de tâches actives et
    l'état général de la file d'attente.
    """
    # Récupération du nombre de tâches actives
    active_tasks_count = await task_manager.get_active_tasks_count()
    
    # Détermination de l'état de la file d'attente
    queue_status = "available"
    if active_tasks_count > 10:
        queue_status = "busy"
    if active_tasks_count > 20:
        queue_status = "overloaded"
    
    return {
        "active_tasks": active_tasks_count,
        "queue_status": queue_status
    }
