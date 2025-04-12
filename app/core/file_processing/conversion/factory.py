"""
Factory pour les services de conversion de documents.
Permet d'instancier dynamiquement différents convertisseurs.
"""

from typing import Dict, Any, Optional, List, Type
import logging

from app.config import settings
from .base import DocumentConverter
from .standard import StandardDocumentConverter
from .advanced import AdvancedDocumentConverter

logger = logging.getLogger(__name__)

# Registre des convertisseurs disponibles
DOCUMENT_CONVERTERS = {
    "standard": StandardDocumentConverter,
    "advanced": AdvancedDocumentConverter
}

async def get_document_converter(provider_name: Optional[str] = None, 
                          config: Optional[Dict[str, Any]] = None,
                          fallback: bool = True) -> DocumentConverter:
    """
    Obtient une instance de convertisseur de documents en fonction du provider spécifié.
    
    Args:
        provider_name: Nom du provider à utiliser (défaut: valeur de configuration)
        config: Configuration spécifique au provider
        fallback: Si True, tente d'utiliser un provider alternatif en cas d'échec
        
    Returns:
        Instance du convertisseur de documents
        
    Raises:
        ValueError: Si aucun provider n'est disponible
    """
    # Utiliser le provider par défaut de la configuration si non spécifié
    if not provider_name:
        provider_name = getattr(settings, "DOCUMENT_CONVERTER_PROVIDER", "advanced")
    
    # Liste des providers à essayer (principal + fallbacks)
    providers_to_try = [provider_name]
    
    # Ajouter les fallbacks si demandé
    if fallback and provider_name != "standard":
        # Le convertisseur standard est toujours un bon fallback
        providers_to_try.append("standard")
    
    # Essayer d'initialiser chaque provider dans l'ordre
    for provider in providers_to_try:
        if provider not in DOCUMENT_CONVERTERS:
            logger.warning(f"Provider de conversion inconnu: {provider}")
            continue
        
        try:
            logger.info(f"Initialisation du provider de conversion: {provider}")
            converter_class = DOCUMENT_CONVERTERS[provider]
            converter = converter_class(config)
            
            # Initialiser le convertisseur
            if await converter.initialize():
                logger.info(f"Provider de conversion {provider} initialisé avec succès")
                return converter
            else:
                logger.warning(f"Échec de l'initialisation du provider de conversion {provider}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du provider de conversion {provider}: {str(e)}")
    
    # Si aucun provider n'a pu être initialisé, essayer le standard sans fallback
    if "standard" not in providers_to_try:
        logger.warning("Tentative d'initialisation du convertisseur standard par défaut")
        try:
            converter = StandardDocumentConverter(config)
            await converter.initialize()
            return converter
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du convertisseur standard par défaut: {str(e)}")
    
    # Si vraiment aucun provider n'est disponible
    raise ValueError("Aucun provider de conversion de documents n'est disponible")

def register_converter(name: str, converter_class: Type[DocumentConverter]) -> None:
    """
    Enregistre un nouveau provider de conversion.
    
    Args:
        name: Nom du provider
        converter_class: Classe du convertisseur
    """
    if name in DOCUMENT_CONVERTERS:
        logger.warning(f"Écrasement du provider de conversion existant: {name}")
    
    DOCUMENT_CONVERTERS[name] = converter_class
    logger.info(f"Provider de conversion enregistré: {name}")

def list_available_converters() -> List[str]:
    """
    Liste les noms des providers de conversion disponibles.
    
    Returns:
        Liste des noms de providers
    """
    return list(DOCUMENT_CONVERTERS.keys())
