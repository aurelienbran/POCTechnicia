"""
Enregistrement des routes de l'API.
Ce module centralise l'enregistrement de toutes les routes de l'API.
"""

from fastapi import APIRouter
from app.api.routes import document_processing
from app.api.routes import ocr_dashboard
from app.api.routes import ui_routes

def register_routes(app):
    """
    Enregistre toutes les routes de l'API dans l'application FastAPI.
    
    Args:
        app: L'application FastAPI principale
    """
    # Créer un routeur API principal
    api_router = APIRouter(prefix="/api")
    
    # Enregistrer les sous-routeurs
    api_router.include_router(document_processing.router)
    api_router.include_router(ocr_dashboard.router)
    
    # Ajouter d'autres routeurs ici au besoin
    # api_router.include_router(autre_module.router)
    
    # Inclure le routeur principal dans l'application
    app.include_router(api_router)
    
    # Inclure les routes UI (sans préfixe /api)
    app.include_router(ui_routes.router)
    
    return app
