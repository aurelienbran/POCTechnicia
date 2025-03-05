"""Modèles de données pour l'application."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class DiagnosticRequest(BaseModel):
    """Modèle pour les requêtes de diagnostic."""
    file_path: Optional[str] = None
    query: Optional[str] = None
    response: Optional[str] = None

class ErrorResponse(BaseModel):
    """Modèle pour les réponses d'erreur."""
    error: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthResponse(BaseModel):
    """Modèle pour les réponses de santé."""
    status: str
    components: Dict[str, str]
    timestamp: datetime = Field(default_factory=datetime.now)
