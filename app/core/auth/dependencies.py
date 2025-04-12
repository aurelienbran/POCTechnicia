"""
Module de dépendances pour l'authentification.

Ce module contient les fonctions de dépendance FastAPI pour l'authentification
des utilisateurs, que ce soit pour les routes HTTP standard ou les WebSockets.

Auteur: Équipe de Développement Technicia
Date: 1 avril, 2025
"""

import logging
from typing import Optional, Union
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError

from app.core.config import settings
from app.models.user import User
from app.models.token import TokenPayload
from app.services.user_service import UserService

# Configuration du logger
logger = logging.getLogger(__name__)

# Configuration OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

# Service utilisateur
user_service = UserService()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dépendance FastAPI pour obtenir l'utilisateur actuel à partir du token JWT.
    
    Cette fonction est utilisée comme dépendance dans les routes HTTP
    protégées pour authentifier l'utilisateur.
    
    Args:
        token: Token JWT d'authentification
        
    Returns:
        User: Objet utilisateur authentifié
        
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur n'existe pas
    """
    try:
        # Décodage du token JWT
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        # Vérification expiration
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expiré",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Identification impossible",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Récupération de l'utilisateur
    user = await user_service.get_user_by_id(token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé",
        )
    
    return user


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
) -> User:
    """
    Dépendance FastAPI pour obtenir l'utilisateur actuel dans un contexte WebSocket.
    
    Cette fonction est utilisée comme dépendance dans les WebSockets
    pour authentifier l'utilisateur.
    
    Args:
        websocket: Objet WebSocket de la connexion
        token: Token JWT d'authentification (passé en paramètre de requête)
        
    Returns:
        User: Objet utilisateur authentifié
        
    Raises:
        WebSocketDisconnect: Si l'authentification échoue
    """
    if not token:
        await websocket.accept()
        await websocket.send_text('{"error": "Token manquant"}')
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
    
    try:
        # Décodage du token JWT
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        # Vérification expiration
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            await websocket.accept()
            await websocket.send_text('{"error": "Token expiré"}')
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
    except (JWTError, ValidationError):
        await websocket.accept()
        await websocket.send_text('{"error": "Token invalide"}')
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
    
    # Récupération de l'utilisateur
    user = await user_service.get_user_by_id(token_data.sub)
    if not user:
        await websocket.accept()
        await websocket.send_text('{"error": "Utilisateur non trouvé"}')
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dépendance FastAPI pour obtenir l'utilisateur actuel et vérifier qu'il est actif.
    
    Args:
        current_user: Utilisateur actuel (provenant de get_current_user)
        
    Returns:
        User: Objet utilisateur authentifié et actif
        
    Raises:
        HTTPException: Si l'utilisateur est inactif
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur inactif",
        )
    
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dépendance FastAPI pour obtenir l'utilisateur actuel et vérifier qu'il est administrateur.
    
    Args:
        current_user: Utilisateur actuel (provenant de get_current_active_user)
        
    Returns:
        User: Objet utilisateur authentifié, actif et administrateur
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas administrateur
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilèges administrateur requis",
        )
    
    return current_user
