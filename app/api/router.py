"""
Configuration du routeur principal pour les API du tableau de bord OCR.

Ce module regroupe tous les routeurs d'API du tableau de bord OCR
et les expose via un routeur principal qui sera intégré à l'application FastAPI.

Auteur: Équipe de Développement Technicia
Date: 1 avril, 2025
"""

from fastapi import APIRouter

from app.api.endpoints.dashboard import router as dashboard_router
from app.api.endpoints.export import router as export_router

# Router principal pour les API du tableau de bord
router = APIRouter(prefix="/dashboard-api")

# Inclusion des sous-routeurs
router.include_router(dashboard_router)
router.include_router(export_router)
