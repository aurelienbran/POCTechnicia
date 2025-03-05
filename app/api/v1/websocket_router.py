"""
Configuration du routeur pour les WebSockets.
"""
from fastapi import APIRouter
from app.api.websocket.ocr_socket import router as ws_socket_router

# Créer un routeur pour combiner tous les endpoints WebSocket
websocket_router = APIRouter()

# Inclure le routeur WebSocket OCR
websocket_router.include_router(ws_socket_router)

# Exporter le routeur pour qu'il soit accessible
__all__ = ['websocket_router']
