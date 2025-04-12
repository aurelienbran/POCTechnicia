"""
Définit l'interface de base pour les services OCR.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OCRResult:
    """Résultat d'une opération OCR."""
    
    success: bool
    output_path: Optional[Path] = None
    text_content: Optional[str] = None
    pages_processed: int = 0
    total_pages: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    @property
    def completion_percentage(self) -> float:
        """Pourcentage de complétion du traitement OCR."""
        if self.total_pages == 0:
            return 100.0 if self.success else 0.0
        return (self.pages_processed / self.total_pages) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "success": self.success,
            "output_path": str(self.output_path) if self.output_path else None,
            "pages_processed": self.pages_processed,
            "total_pages": self.total_pages,
            "completion_percentage": self.completion_percentage,
            "processing_time": self.processing_time,
            "error_message": self.error_message,
            "metadata": self.metadata or {}
        }

class OCRProcessor(ABC):
    """Interface de base pour les services OCR."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le processeur OCR.
        
        Args:
            config: Configuration spécifique au provider
        """
        self.config = config or {}
        self.initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialise le processeur OCR et vérifie que les dépendances sont disponibles.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abstractmethod
    async def process_document(self, 
                        input_file: Union[str, Path], 
                        output_file: Optional[Union[str, Path]] = None,
                        language: str = "fra",
                        **kwargs) -> OCRResult:
        """
        Traite un document avec OCR.
        
        Args:
            input_file: Chemin vers le fichier d'entrée
            output_file: Chemin vers le fichier de sortie (optionnel)
            language: Code de langue pour l'OCR
            **kwargs: Options spécifiques au provider
            
        Returns:
            Résultat de l'opération OCR
        """
        pass
    
    @abstractmethod
    async def extract_text(self, 
                    document_path: Union[str, Path],
                    page_numbers: Optional[List[int]] = None) -> str:
        """
        Extrait le texte d'un document déjà traité par OCR.
        
        Args:
            document_path: Chemin vers le document
            page_numbers: Liste des numéros de page à extraire (None = toutes)
            
        Returns:
            Texte extrait du document
        """
        pass
    
    @abstractmethod
    async def needs_ocr(self, document_path: Union[str, Path]) -> bool:
        """
        Détermine si un document nécessite un traitement OCR.
        
        Args:
            document_path: Chemin vers le document
            
        Returns:
            True si le document nécessite un OCR, False sinon
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Nom du provider OCR.
        
        Returns:
            Nom du provider (ex: "ocrmypdf", "tesseract", etc.)
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """
        Indique si le processeur est initialisé.
        
        Returns:
            True si le processeur est initialisé, False sinon
        """
        return self.initialized
