"""
Factory pour les services OCR.
Permet d'instancier dynamiquement différents providers OCR.
"""

from typing import Dict, Any, Optional, List, Type
import logging

from app.config import settings
from .base import OCRProcessor
from .ocrmypdf import OCRmyPDFProcessor
from .tesseract_direct import TesseractDirectProcessor
from .document_ai import DocumentAIProcessor
from ..ai_orchestrator import AIOrchestrator

logger = logging.getLogger(__name__)

# Registre des providers OCR disponibles
OCR_PROVIDERS = {
    "ocrmypdf": OCRmyPDFProcessor,
    "tesseract_direct": TesseractDirectProcessor,
    "document_ai": DocumentAIProcessor,
    "ai_orchestrator": AIOrchestrator
}

async def get_ocr_processor(provider_name: Optional[str] = None, 
                     config: Optional[Dict[str, Any]] = None,
                     fallback: bool = True) -> OCRProcessor:
    """
    Obtient une instance de processeur OCR en fonction du provider spécifié.
    
    Args:
        provider_name: Nom du provider à utiliser (défaut: valeur de configuration)
        config: Configuration spécifique au provider
        fallback: Si True, tente d'utiliser un provider alternatif en cas d'échec
        
    Returns:
        Instance du processeur OCR
        
    Raises:
        ValueError: Si aucun provider n'est disponible
    """
    # Utiliser le provider par défaut de la configuration si non spécifié
    if not provider_name:
        provider_name = getattr(settings, "OCR_PROVIDER", "ocrmypdf")
    
    # Liste des providers à essayer (principal + fallbacks)
    providers_to_try = [provider_name]
    
    # Ajouter les fallbacks si demandé
    if fallback:
        # Prioriser l'orchestrateur si disponible, puis les autres providers
        # mais ne pas ajouter le provider principal comme fallback
        fallbacks = []
        if provider_name != "ai_orchestrator":
            fallbacks.append("ai_orchestrator")  # L'orchestrateur est le premier fallback
        
        fallbacks.extend([p for p in OCR_PROVIDERS.keys() if p != provider_name and p != "ai_orchestrator"])
        providers_to_try.extend(fallbacks)
    
    # Essayer d'initialiser chaque provider dans l'ordre
    for provider in providers_to_try:
        if provider not in OCR_PROVIDERS:
            logger.warning(f"Provider OCR inconnu: {provider}")
            continue
        
        try:
            logger.info(f"Initialisation du provider OCR: {provider}")
            processor_class = OCR_PROVIDERS[provider]
            processor = processor_class(config)
            
            # Initialiser le processeur
            success = await processor.initialize()
            
            if success:
                logger.info(f"Provider OCR initialisé avec succès: {provider}")
                return processor
            else:
                logger.warning(f"Échec de l'initialisation du provider OCR: {provider}")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du provider OCR {provider}: {str(e)}")
    
    # Si aucun provider n'a pu être initialisé
    raise ValueError("Aucun provider OCR disponible. Vérifiez l'installation des dépendances.")

async def get_smart_processor(document_type: Optional[str] = None,
                      has_images: bool = False,
                      is_technical: bool = False,
                      config: Optional[Dict[str, Any]] = None) -> OCRProcessor:
    """
    Détermine intelligemment le meilleur processeur OCR en fonction du type de document.
    
    Args:
        document_type: Type de document ('pdf', 'image', 'scan', etc.)
        has_images: Indique si le document contient des images
        is_technical: Indique si le document est un document technique
        config: Configuration spécifique au provider
        
    Returns:
        Instance du processeur OCR le plus adapté
    """
    # Si c'est un document technique avec des images, utiliser l'orchestrateur
    if is_technical or has_images:
        try:
            processor = await get_ocr_processor("ai_orchestrator", config)
            return processor
        except ValueError:
            logger.warning("Orchestrateur AI non disponible, recherche d'une alternative")
    
    # Pour les documents PDF standards sans contenu technique particulier
    if document_type == "pdf" and not is_technical:
        try:
            return await get_ocr_processor("ocrmypdf", config)
        except ValueError:
            logger.warning("OCRmyPDF non disponible, recherche d'une alternative")
    
    # Pour les images individuelles
    if document_type in ["image", "jpg", "jpeg", "png", "tiff", "tif"]:
        try:
            # Document AI est généralement bon pour les images
            return await get_ocr_processor("document_ai", config)
        except ValueError:
            # Tesseract en fallback
            logger.warning("Document AI non disponible, recherche d'une alternative")
            try:
                return await get_ocr_processor("tesseract_direct", config)
            except ValueError:
                logger.warning("Tesseract non disponible, recherche d'une alternative")
    
    # Par défaut, essayer tous les providers disponibles
    return await get_ocr_processor(None, config)

def register_ocr_provider(name: str, processor_class: Type[OCRProcessor]) -> None:
    """
    Enregistre un nouveau provider OCR.
    
    Args:
        name: Nom du provider
        processor_class: Classe du processeur OCR
    """
    if name in OCR_PROVIDERS:
        logger.warning(f"Écrasement du provider OCR existant: {name}")
    
    OCR_PROVIDERS[name] = processor_class
    logger.info(f"Provider OCR enregistré: {name}")

def list_available_ocr_providers() -> List[str]:
    """
    Liste les noms des providers OCR disponibles.
    
    Returns:
        Liste des noms de providers
    """
    return list(OCR_PROVIDERS.keys())
