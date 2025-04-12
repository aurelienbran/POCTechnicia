"""
Package pour le tableau de bord OCR
==================================

Ce package implémente un tableau de bord complet pour le suivi et la gestion
des tâches OCR. Il fournit une interface utilisateur web ainsi qu'une API
REST pour interagir avec les tâches OCR.

Modules:
- models.py: Modèles de données pour le tableau de bord
- api.py: API REST pour interagir avec le tableau de bord
- ui.py: Interface utilisateur web du tableau de bord

Auteur: Équipe Technicia
Date: Mars 2025
"""

from app.core.tasks.dashboard.models import TaskInfo, OCRProviderMetrics, get_dashboard_store
from app.core.tasks.dashboard.api import router as dashboard_api_router, add_dashboard_routes

__all__ = [
    'TaskInfo',
    'OCRProviderMetrics',
    'get_dashboard_store',
    'dashboard_api_router',
    'add_dashboard_routes'
]
