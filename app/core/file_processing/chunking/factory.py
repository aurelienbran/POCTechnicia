"""
Factory pour les services de chunking de texte.
Permet d'instancier dynamiquement différents chunkers.
"""

from typing import Dict, Any, Optional, List, Type
import logging

from app.config import settings
from .base import TextChunker
from .simple import SimpleTextChunker
from .semantic import SemanticTextChunker

logger = logging.getLogger(__name__)

# Registre des chunkers disponibles
TEXT_CHUNKERS = {
    "simple": SimpleTextChunker,
    "semantic": SemanticTextChunker
}

async def get_text_chunker(provider_name: Optional[str] = None, 
                    config: Optional[Dict[str, Any]] = None,
                    fallback: bool = True) -> TextChunker:
    """
    Obtient une instance de chunker de texte en fonction du provider spécifié.
    
    Args:
        provider_name: Nom du provider à utiliser (défaut: valeur de configuration)
        config: Configuration spécifique au provider
        fallback: Si True, tente d'utiliser un provider alternatif en cas d'échec
        
    Returns:
        Instance du chunker de texte
        
    Raises:
        ValueError: Si aucun provider n'est disponible
    """
    # Utiliser le provider par défaut de la configuration si non spécifié
    if not provider_name:
        provider_name = getattr(settings, "TEXT_CHUNKER_PROVIDER", "simple")
    
    # Liste des providers à essayer (principal + fallbacks)
    providers_to_try = [provider_name]
    
    # Ajouter les fallbacks si demandé
    if fallback and provider_name != "simple":
        # Le chunker simple est toujours un bon fallback
        providers_to_try.append("simple")
    
    # Essayer d'initialiser chaque provider dans l'ordre
    for provider in providers_to_try:
        if provider not in TEXT_CHUNKERS:
            logger.warning(f"Provider de chunking inconnu: {provider}")
            continue
        
        try:
            logger.info(f"Initialisation du provider de chunking: {provider}")
            chunker_class = TEXT_CHUNKERS[provider]
            chunker = chunker_class(config)
            
            return chunker
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du provider de chunking {provider}: {str(e)}")
    
    # Si aucun provider n'a pu être initialisé, utiliser le chunker simple par défaut
    logger.warning("Fallback sur le chunker simple par défaut")
    return SimpleTextChunker(config)

def register_chunker(name: str, chunker_class: Type[TextChunker]) -> None:
    """
    Enregistre un nouveau provider de chunking.
    
    Args:
        name: Nom du provider
        chunker_class: Classe du chunker
    """
    if name in TEXT_CHUNKERS:
        logger.warning(f"Écrasement du provider de chunking existant: {name}")
    
    TEXT_CHUNKERS[name] = chunker_class
    logger.info(f"Provider de chunking enregistré: {name}")

def list_available_chunkers() -> List[str]:
    """
    Liste les noms des providers de chunking disponibles.
    
    Returns:
        Liste des noms de providers
    """
    return list(TEXT_CHUNKERS.keys())
