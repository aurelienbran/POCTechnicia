"""
Routes UI pour l'application Technicia
======================================

Ce module définit les routes pour l'interface utilisateur de l'application,
incluant les pages web et les templates rendus.

Les routes principales incluent:
- Tableau de bord principal
- Tableau de bord OCR
- Interface de gestion des documents
- Pages d'assistance

Auteur: Équipe Technicia
Date: Avril 2025
"""

import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.core.auth.dependencies import get_current_user, get_optional_user
from app.models.user import User

# Initialiser le logger
logger = logging.getLogger(__name__)

# Initialiser le router
router = APIRouter(tags=["UI"])

# Configurer les templates
templates_path = Path("app/templates")
templates = Jinja2Templates(directory=str(templates_path))


@router.get("/ocr-dashboard", response_class=HTMLResponse)
async def ocr_dashboard(
    request: Request,
    user: User = Depends(get_optional_user)
):
    """
    Affiche le tableau de bord OCR.
    
    Cette page permet aux utilisateurs de:
    - Suivre les tâches OCR en cours
    - Gérer la file d'attente (pause, reprise, annulation)
    - Soumettre de nouveaux documents pour traitement OCR
    - Visualiser les statistiques et métriques OCR
    
    Args:
        request: La requête HTTP
        user: L'utilisateur actuel (optionnel)
        
    Returns:
        Page HTML du tableau de bord OCR
    """
    try:
        # Log de l'accès
        username = user.username if user else "Utilisateur anonyme"
        logger.info(f"Accès au tableau de bord OCR par {username}")
        
        # Rendre le template
        return templates.TemplateResponse(
            "ocr_dashboard.html",
            {
                "request": request,
                "user": user,
                "page_title": "Tableau de bord OCR"
            }
        )
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage du tableau de bord OCR: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de l'affichage du tableau de bord OCR")
