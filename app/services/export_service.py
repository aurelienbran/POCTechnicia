"""
Service d'exportation pour le tableau de bord OCR.

Ce module fournit des fonctionnalités pour exporter les données du tableau de bord
OCR dans différents formats (PDF, CSV, JSON), gérer les tâches d'exportation
asynchrones et stocker/récupérer les exports générés.

Auteur: Équipe de Développement Technicia
Date: 1 avril, 2025
"""

import os
import io
import uuid
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import LineChart

from app.core.config import settings

# Configuration du logger
logger = logging.getLogger(__name__)


class ExportService:
    """
    Service pour l'exportation des données du tableau de bord OCR.
    
    Cette classe gère la génération de rapports dans différents formats,
    le stockage des exports générés et le suivi des tâches d'exportation.
    """
    
    def __init__(self):
        """
        Initialise le service d'exportation.
        
        Crée le répertoire d'exportation s'il n'existe pas déjà.
        """
        self.export_dir = os.path.join(settings.DATA_DIR, "exports")
        os.makedirs(self.export_dir, exist_ok=True)
        
        # Dictionnaire pour suivre les exports en cours
        self.pending_exports = {}
    
    async def schedule_pdf_export(
        self, 
        export_type: str, 
        data: Any, 
        user_id: str, 
        filters: Dict[str, Any] = None
    ) -> str:
        """
        Planifie une exportation PDF en arrière-plan.
        
        Args:
            export_type: Type d'exportation (task_history, ocr_metrics)
            data: Données à exporter
            user_id: Identifiant de l'utilisateur demandant l'export
            filters: Filtres appliqués aux données
            
        Returns:
            Identifiant unique de l'exportation
        """
        export_id = str(uuid.uuid4())
        
        # Enregistrement de l'export
        self.pending_exports[export_id] = {
            "id": export_id,
            "type": export_type,
            "user_id": user_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "filters": filters or {},
            "message": "Exportation en attente de traitement",
            "file_path": None,
            "file_name": None
        }
        
        # Lancement de la tâche d'exportation en arrière-plan
        asyncio.create_task(self._process_pdf_export(export_id, export_type, data, filters))
        
        return export_id
    
    async def _process_pdf_export(
        self, 
        export_id: str, 
        export_type: str, 
        data: Any, 
        filters: Dict[str, Any] = None
    ):
        """
        Traite une exportation PDF en arrière-plan.
        
        Args:
            export_id: Identifiant de l'exportation
            export_type: Type d'exportation (task_history, ocr_metrics)
            data: Données à exporter
            filters: Filtres appliqués aux données
        """
        try:
            # Mise à jour du statut
            self.pending_exports[export_id]["status"] = "processing"
            self.pending_exports[export_id]["message"] = "Génération du PDF en cours"
            
            # Génération du PDF selon le type d'exportation
            pdf_bytes = None
            filename = f"export_{export_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            if export_type == "task_history":
                pdf_bytes = await self.generate_task_history_pdf(data, filters)
                filename = f"tasks_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            elif export_type == "ocr_metrics":
                metrics = data.get("metrics", {})
                chart_data = data.get("chart_data", {})
                period = data.get("period", "month")
                provider = data.get("provider")
                
                pdf_bytes = await self.generate_metrics_pdf(metrics, chart_data, period, provider)
                filename = f"ocr_metrics_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            else:
                raise ValueError(f"Type d'exportation non pris en charge: {export_type}")
            
            # Sauvegarde du PDF
            if pdf_bytes:
                file_path = os.path.join(self.export_dir, filename)
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)
                
                # Mise à jour du statut
                self.pending_exports[export_id]["status"] = "completed"
                self.pending_exports[export_id]["message"] = "Exportation complétée avec succès"
                self.pending_exports[export_id]["file_path"] = file_path
                self.pending_exports[export_id]["file_name"] = filename
                
                logger.info(f"Exportation {export_id} générée: {file_path}")
            else:
                raise ValueError("Aucune donnée n'a été générée pour l'exportation")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'exportation {export_id}: {str(e)}")
            
            # Mise à jour du statut
            self.pending_exports[export_id]["status"] = "failed"
            self.pending_exports[export_id]["message"] = f"Erreur: {str(e)}"
    
    async def get_export_info(self, export_id: str) -> Dict[str, Any]:
        """
        Récupère les informations sur une exportation.
        
        Args:
            export_id: Identifiant de l'exportation
            
        Returns:
            Informations sur l'exportation ou None si non trouvée
        """
        return self.pending_exports.get(export_id)
    
    async def generate_task_history_pdf(
        self, 
        tasks: List[Any], 
        filters: Dict[str, Any] = None
    ) -> bytes:
        """
        Génère un rapport PDF pour l'historique des tâches OCR.
        
        Args:
            tasks: Liste des tâches à inclure dans le rapport
            filters: Filtres appliqués aux données
            
        Returns:
            Contenu du PDF en bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                               rightMargin=30, leftMargin=30,
                               topMargin=30, bottomMargin=30)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        subtitle_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Construction du document
        elements = []
        
        # Titre
        elements.append(Paragraph("Rapport d'historique des tâches OCR", title_style))
        elements.append(Spacer(1, 12))
        
        # Date du rapport
        date_rapport = f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}"
        elements.append(Paragraph(date_rapport, normal_style))
        elements.append(Spacer(1, 12))
        
        # Filtres appliqués
        if filters:
            elements.append(Paragraph("Filtres appliqués:", subtitle_style))
            filter_text = ""
            
            for key, value in filters.items():
                if key == "start_date" and value:
                    filter_text += f"Date début: {value.strftime('%d/%m/%Y %H:%M')} | "
                elif key == "end_date" and value:
                    filter_text += f"Date fin: {value.strftime('%d/%m/%Y %H:%M')} | "
                elif key == "ocr_provider" and value:
                    filter_text += f"Fournisseur OCR: {value} | "
                elif key == "status" and value:
                    filter_text += f"Statut: {value} | "
            
            if filter_text:
                elements.append(Paragraph(filter_text[:-3], normal_style))
                elements.append(Spacer(1, 12))
        
        # Résumé
        elements.append(Paragraph("Résumé", subtitle_style))
        elements.append(Paragraph(f"Nombre total de tâches: {len(tasks)}", normal_style))
        elements.append(Spacer(1, 12))
        
        # Tableau des tâches
        if tasks:
            # Préparation des données du tableau
            table_data = [
                ["ID", "Nom", "Statut", "Priorité", "Fournisseur OCR", "Créé le", "Durée", "Format"]
            ]
            
            for task in tasks:
                task_dict = task.dict() if hasattr(task, "dict") else task
                
                # Calcul de la durée
                duration = "N/A"
                if task_dict.get("start_time") and task_dict.get("end_time"):
                    start = datetime.fromisoformat(task_dict["start_time"]) if isinstance(task_dict["start_time"], str) else task_dict["start_time"]
                    end = datetime.fromisoformat(task_dict["end_time"]) if isinstance(task_dict["end_time"], str) else task_dict["end_time"]
                    
                    seconds = (end - start).total_seconds()
                    hours, remainder = divmod(seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    if hours > 0:
                        duration = f"{int(hours)}h {int(minutes)}m"
                    else:
                        duration = f"{int(minutes)}m {int(seconds)}s"
                
                row = [
                    task_dict.get("id", "")[:8] + "...",  # ID tronqué
                    task_dict.get("name", ""),
                    task_dict.get("status", ""),
                    task_dict.get("priority", ""),
                    task_dict.get("ocr_provider", ""),
                    datetime.fromisoformat(task_dict["created_at"]).strftime("%d/%m/%Y %H:%M") if isinstance(task_dict.get("created_at"), str) else (task_dict.get("created_at", "").strftime("%d/%m/%Y %H:%M") if task_dict.get("created_at") else ""),
                    duration,
                    task_dict.get("ocr_params", {}).get("output_format", "")
                ]
                
                table_data.append(row)
            
            # Création du tableau
            table = Table(table_data, repeatRows=1)
            
            # Style du tableau
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
            ])
            
            table.setStyle(style)
            elements.append(table)
        else:
            elements.append(Paragraph("Aucune tâche ne correspond aux critères sélectionnés", normal_style))
        
        # Génération du document
        doc.build(elements)
        
        # Récupération du contenu
        buffer.seek(0)
        return buffer.getvalue()
    
    async def generate_metrics_pdf(
        self, 
        metrics: Dict[str, Any], 
        chart_data: Dict[str, Any],
        period: str = "month",
        provider: Optional[str] = None
    ) -> bytes:
        """
        Génère un rapport PDF pour les métriques de performance OCR.
        
        Args:
            metrics: Métriques de performance
            chart_data: Données pour les graphiques
            period: Période d'analyse
            provider: Fournisseur OCR filtré (optionnel)
            
        Returns:
            Contenu du PDF en bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                               rightMargin=30, leftMargin=30,
                               topMargin=30, bottomMargin=30)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        subtitle_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Construction du document
        elements = []
        
        # Titre
        title = "Rapport de performance OCR"
        if provider:
            title += f" - {provider}"
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))
        
        # Date et période
        period_text = {
            "day": "dernier jour",
            "week": "dernière semaine",
            "month": "dernier mois",
            "quarter": "dernier trimestre",
            "year": "dernière année"
        }.get(period, period)
        
        date_rapport = f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')} - Période: {period_text}"
        elements.append(Paragraph(date_rapport, normal_style))
        elements.append(Spacer(1, 20))
        
        # Métriques globales
        elements.append(Paragraph("Métriques globales", subtitle_style))
        
        global_metrics = [
            ["Métrique", "Valeur"],
            ["Nombre total de tâches", str(metrics.get("total_tasks", 0))],
            ["Taux de réussite global", f"{metrics.get('success_rate', 0):.2f}%"],
            ["Temps moyen de traitement", self._format_duration(metrics.get("avg_processing_time", 0))],
            ["Score de confiance moyen", f"{metrics.get('avg_confidence', 0):.2f}%"]
        ]
        
        global_table = Table(global_metrics, colWidths=[200, 100])
        global_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
        ]))
        
        elements.append(global_table)
        elements.append(Spacer(1, 20))
        
        # Métriques par fournisseur
        elements.append(Paragraph("Performances par fournisseur OCR", subtitle_style))
        
        if metrics.get("providers"):
            providers_data = [
                ["Fournisseur", "Tâches", "Taux de réussite", "Temps moyen", "Confiance"]
            ]
            
            for provider_id, provider_metrics in metrics.get("providers", {}).items():
                providers_data.append([
                    provider_metrics.get("name", provider_id),
                    str(provider_metrics.get("tasks_count", 0)),
                    f"{provider_metrics.get('success_rate', 0):.2f}%",
                    self._format_duration(provider_metrics.get("avg_processing_time", 0)),
                    f"{provider_metrics.get('avg_confidence', 0):.2f}%"
                ])
            
            providers_table = Table(providers_data, repeatRows=1)
            providers_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
            ]))
            
            elements.append(providers_table)
        else:
            elements.append(Paragraph("Aucune donnée disponible pour les fournisseurs OCR", normal_style))
        
        elements.append(Spacer(1, 20))
        
        # Génération du document
        doc.build(elements)
        
        # Récupération du contenu
        buffer.seek(0)
        return buffer.getvalue()
    
    def _format_duration(self, seconds: float) -> str:
        """
        Formate une durée en secondes en chaîne lisible.
        
        Args:
            seconds: Durée en secondes
            
        Returns:
            Durée formatée
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        
        minutes, seconds = divmod(seconds, 60)
        if minutes < 60:
            return f"{int(minutes)}m {int(seconds)}s"
        
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours)}h {int(minutes)}m"
