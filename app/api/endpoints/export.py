"""
Module d'API pour l'exportation des données du tableau de bord OCR.

Ce module implémente les endpoints API REST pour l'exportation des données
du tableau de bord OCR, permettant de générer des rapports au format CSV, PDF,
ou autres formats pour une utilisation externe.

Auteur: Équipe de Développement Technicia
Date: 1 avril, 2025
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import io
import csv
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.core.auth.dependencies import get_current_user, get_current_active_user
from app.core.tasks.task_manager import TaskManager
from app.core.file_processing.ocr.ocr_provider import OCRProviderRegistry
from app.models.user import User
from app.services.export_service import ExportService
from app.utils.formatters import format_datetime, format_duration

# Configuration du router
router = APIRouter(prefix="/export", tags=["export-api"])

# Gestionnaires
task_manager = TaskManager()
export_service = ExportService()


# Modèles Pydantic

class ExportRequest(BaseModel):
    """Modèle pour une demande d'exportation."""
    export_type: str = Field(..., description="Type d'exportation (history, metrics)")
    format: str = Field(..., description="Format d'exportation (csv, pdf, json)")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filtres à appliquer")
    

class ExportStatusResponse(BaseModel):
    """Modèle pour la réponse de statut d'exportation."""
    status: str
    export_id: Optional[str] = None
    message: str
    download_url: Optional[str] = None


# Endpoints API

@router.post("/task-history", response_model=ExportStatusResponse)
async def export_task_history(
    format: str = Query(..., description="Format d'exportation (csv, pdf, json)"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    provider: Optional[str] = None,
    status: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Exporte l'historique des tâches OCR au format spécifié.
    
    Args:
        format: Format d'exportation (csv, pdf, json)
        start_date: Date de début pour le filtre
        end_date: Date de fin pour le filtre
        provider: Filtre par fournisseur OCR
        status: Filtre par statut
        background_tasks: Tâches d'arrière-plan FastAPI
        
    Returns:
        Données exportées au format demandé ou statut de l'exportation
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
    tasks = await task_manager.get_completed_tasks(filters=filters)
    
    # Exportation selon le format demandé
    if format.lower() == "csv":
        # Export CSV direct (streaming)
        return await export_tasks_to_csv(tasks)
    
    elif format.lower() == "json":
        # Export JSON direct
        tasks_dict = [task.dict() for task in tasks]
        return JSONResponse(content={"tasks": tasks_dict})
    
    elif format.lower() == "pdf":
        # Génération PDF en arrière-plan (peut être longue)
        if background_tasks:
            export_id = await export_service.schedule_pdf_export(
                "task_history",
                tasks, 
                current_user.id,
                filters
            )
            return ExportStatusResponse(
                status="processing",
                export_id=export_id,
                message="L'exportation PDF est en cours de traitement",
                download_url=f"/api/export/download/{export_id}"
            )
        else:
            # Génération synchrone (non recommandée)
            pdf_bytes = await export_service.generate_task_history_pdf(tasks, filters)
            
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="tasks_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'}
            )
    
    else:
        raise HTTPException(status_code=400, detail=f"Format d'exportation non supporté: {format}")


@router.post("/ocr-metrics", response_model=ExportStatusResponse)
async def export_ocr_metrics(
    format: str = Query(..., description="Format d'exportation (csv, pdf, json)"),
    period: str = Query("month", description="Période (day, week, month, quarter, year)"),
    provider: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Exporte les métriques de performance OCR au format spécifié.
    
    Args:
        format: Format d'exportation (csv, pdf, json)
        period: Période d'analyse
        provider: Filtre par fournisseur OCR
        background_tasks: Tâches d'arrière-plan FastAPI
        
    Returns:
        Données exportées au format demandé ou statut de l'exportation
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
    
    # Récupération des métriques
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
    
    # Combinaison des données
    export_data = {
        "metrics": metrics,
        "chart_data": chart_data,
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "provider": provider
    }
    
    # Exportation selon le format demandé
    if format.lower() == "csv":
        # Export CSV direct (streaming)
        return await export_metrics_to_csv(metrics, chart_data)
    
    elif format.lower() == "json":
        # Export JSON direct
        return JSONResponse(content=export_data)
    
    elif format.lower() == "pdf":
        # Génération PDF en arrière-plan (peut être longue)
        if background_tasks:
            export_id = await export_service.schedule_pdf_export(
                "ocr_metrics",
                export_data, 
                current_user.id,
                {"period": period, "provider": provider}
            )
            return ExportStatusResponse(
                status="processing",
                export_id=export_id,
                message="L'exportation PDF est en cours de traitement",
                download_url=f"/api/export/download/{export_id}"
            )
        else:
            # Génération synchrone (non recommandée)
            pdf_bytes = await export_service.generate_metrics_pdf(metrics, chart_data, period, provider)
            
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="ocr_metrics_{period}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'}
            )
    
    else:
        raise HTTPException(status_code=400, detail=f"Format d'exportation non supporté: {format}")


@router.get("/download/{export_id}")
async def download_export(
    export_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Télécharge un export généré précédemment.
    
    Args:
        export_id: Identifiant de l'exportation
        
    Returns:
        Fichier exporté
    """
    # Vérification que l'export existe et appartient à l'utilisateur
    export_info = await export_service.get_export_info(export_id)
    
    if not export_info:
        raise HTTPException(status_code=404, detail="Export non trouvé")
    
    if export_info.get("user_id") != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé à cet export")
    
    # Vérification du statut
    if export_info.get("status") != "completed":
        return ExportStatusResponse(
            status=export_info.get("status", "unknown"),
            export_id=export_id,
            message=export_info.get("message", "L'exportation est toujours en cours de traitement"),
            download_url=f"/api/export/download/{export_id}"
        )
    
    # Récupération du fichier
    file_path = export_info.get("file_path")
    if not file_path:
        raise HTTPException(status_code=500, detail="Fichier d'export introuvable")
    
    # Détermination du type de contenu
    content_type = "application/octet-stream"
    file_name = export_info.get("file_name", f"export_{export_id}")
    
    if file_path.endswith(".pdf"):
        content_type = "application/pdf"
    elif file_path.endswith(".csv"):
        content_type = "text/csv"
    elif file_path.endswith(".json"):
        content_type = "application/json"
    
    # Lecture et envoi du fichier
    try:
        with open(file_path, "rb") as file:
            content = file.read()
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la lecture du fichier: {str(e)}")


# Fonctions utilitaires

async def export_tasks_to_csv(tasks: List[Any]):
    """
    Exporte une liste de tâches au format CSV.
    
    Args:
        tasks: Liste des tâches à exporter
        
    Returns:
        StreamingResponse avec le contenu CSV
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # En-têtes
    headers = [
        "ID", "Nom", "Statut", "Priorité", "Fournisseur OCR", 
        "Date de création", "Date de début", "Date de fin", 
        "Durée de traitement", "Document", "Taille",
        "Langue", "Format", "Utilisateur"
    ]
    writer.writerow(headers)
    
    # Données
    for task in tasks:
        task_dict = task.dict() if hasattr(task, "dict") else task
        
        duration = ""
        if task_dict.get("start_time") and task_dict.get("end_time"):
            start = datetime.fromisoformat(task_dict["start_time"]) if isinstance(task_dict["start_time"], str) else task_dict["start_time"]
            end = datetime.fromisoformat(task_dict["end_time"]) if isinstance(task_dict["end_time"], str) else task_dict["end_time"]
            duration = format_duration((end - start).total_seconds())
        
        row = [
            task_dict.get("id", ""),
            task_dict.get("name", ""),
            task_dict.get("status", ""),
            task_dict.get("priority", ""),
            task_dict.get("ocr_provider", ""),
            format_datetime(task_dict.get("created_at")),
            format_datetime(task_dict.get("start_time")),
            format_datetime(task_dict.get("end_time")),
            duration,
            task_dict.get("document_path", "").split("/")[-1],
            task_dict.get("document_size", ""),
            task_dict.get("ocr_params", {}).get("language", ""),
            task_dict.get("ocr_params", {}).get("output_format", ""),
            task_dict.get("user_id", "")
        ]
        writer.writerow(row)
    
    # Retour du fichier CSV
    output.seek(0)
    
    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="tasks_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'}
    )


async def export_metrics_to_csv(metrics: Dict[str, Any], chart_data: Dict[str, Any]):
    """
    Exporte les métriques de performance OCR au format CSV.
    
    Args:
        metrics: Métriques générales
        chart_data: Données pour les graphiques
        
    Returns:
        StreamingResponse avec le contenu CSV
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # En-têtes pour les métriques globales
    writer.writerow(["MÉTRIQUES GLOBALES"])
    writer.writerow(["Métrique", "Valeur"])
    writer.writerow(["Nombre total de tâches", metrics.get("total_tasks", 0)])
    writer.writerow(["Taux de réussite", f"{metrics.get('success_rate', 0):.2f}%"])
    writer.writerow(["Temps moyen de traitement", format_duration(metrics.get("avg_processing_time", 0))])
    writer.writerow([])
    
    # Métriques par fournisseur
    writer.writerow(["MÉTRIQUES PAR FOURNISSEUR OCR"])
    writer.writerow(["Fournisseur", "Tâches", "Taux de réussite", "Temps moyen", "Confiance moyenne"])
    
    for provider, provider_metrics in metrics.get("providers", {}).items():
        writer.writerow([
            provider_metrics.get("name", provider),
            provider_metrics.get("tasks_count", 0),
            f"{provider_metrics.get('success_rate', 0):.2f}%",
            format_duration(provider_metrics.get("avg_processing_time", 0)),
            f"{provider_metrics.get('avg_confidence', 0):.2f}%"
        ])
    
    writer.writerow([])
    
    # Données temporelles
    if "time_series" in chart_data:
        writer.writerow(["ÉVOLUTION TEMPORELLE"])
        
        # Déterminer toutes les dates
        dates = set()
        for provider_data in chart_data["time_series"].values():
            dates.update(point["date"] for point in provider_data)
        
        dates = sorted(dates)
        
        # En-têtes avec tous les fournisseurs
        header_row = ["Date"]
        for provider in chart_data["time_series"].keys():
            header_row.extend([f"{provider} - Tâches", f"{provider} - Taux", f"{provider} - Temps"])
        
        writer.writerow(header_row)
        
        # Organiser les données par date
        for date in dates:
            row = [date]
            
            for provider, data_points in chart_data["time_series"].items():
                # Trouver les données pour cette date et ce fournisseur
                point = next((p for p in data_points if p["date"] == date), None)
                
                if point:
                    row.extend([
                        point.get("tasks_count", 0),
                        f"{point.get('success_rate', 0):.2f}%",
                        format_duration(point.get("avg_processing_time", 0))
                    ])
                else:
                    row.extend(["0", "0%", "0s"])
            
            writer.writerow(row)
    
    # Retour du fichier CSV
    output.seek(0)
    
    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="ocr_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'}
    )
