"""
Package de gestion WebSocket pour l'application.
"""
from .ocr_socket import OCRWebSocketManager, WebSocketLogHandler, router as ws_router

__all__ = ['OCRWebSocketManager', 'WebSocketLogHandler', 'ws_router']
