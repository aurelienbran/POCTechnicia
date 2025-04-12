"""
Module de modèles pour les tokens d'authentification.

Ce module définit les modèles Pydantic pour la gestion des tokens
d'authentification JWT dans l'application Technicia.

Auteur: Équipe de Développement Technicia
Date: 1 avril, 2025
"""

from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """
    Modèle Pydantic pour représenter un token d'authentification.
    
    Attributes:
        access_token: Token JWT d'accès
        token_type: Type de token (généralement "bearer")
        refresh_token: Token de rafraîchissement optionnel
    """
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None


class TokenPayload(BaseModel):
    """
    Modèle Pydantic pour représenter le contenu (payload) d'un token JWT.
    
    Attributes:
        sub: Sujet du token (généralement l'ID utilisateur)
        exp: Timestamp d'expiration
        iat: Timestamp de création
        type: Type de token (access, refresh)
    """
    sub: str
    exp: int
    iat: Optional[int] = None
    type: Optional[str] = "access"
