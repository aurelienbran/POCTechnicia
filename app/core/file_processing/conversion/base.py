"""
Définit l'interface de base pour les services de conversion de documents.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, BinaryIO
from pathlib import Path
import logging
from dataclasses import dataclass
import mimetypes
import os

logger = logging.getLogger(__name__)

class ConversionError(Exception):
    """Exception personnalisée pour les erreurs de conversion."""
    pass

@dataclass
class ConversionResult:
    """Résultat d'une opération de conversion de document."""
    
    success: bool
    text_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    pages_processed: int = 0
    total_pages: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Si le texte est présent, ajouter des statistiques
        if self.text_content:
            # Statistiques de base sur le texte
            self.metadata.update({
                "text_length": len(self.text_content),
                "pages_processed": self.pages_processed,
                "words_count": len(self.text_content.split()),
                "lines_count": len(self.text_content.splitlines()),
            })
    
    @property
    def completion_percentage(self) -> float:
        """Pourcentage de complétion du traitement."""
        if self.total_pages == 0:
            return 100.0 if self.success else 0.0
        return (self.pages_processed / self.total_pages) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        result = {
            "success": self.success,
            "text_length": len(self.text_content) if self.text_content else 0,
            "pages_processed": self.pages_processed,
            "total_pages": self.total_pages,
            "completion_percentage": self.completion_percentage,
            "processing_time": self.processing_time,
            "metadata": self.metadata or {}
        }
        
        if self.error_message:
            result["error_message"] = self.error_message
            
        return result
    
    def get_text_preview(self, max_length: int = 500) -> str:
        """
        Retourne un aperçu du texte extrait.
        
        Args:
            max_length: Longueur maximale de l'aperçu
            
        Returns:
            Aperçu du texte
        """
        if not self.text_content:
            return ""
            
        if len(self.text_content) <= max_length:
            return self.text_content
            
        # Couper au dernier espace avant max_length
        preview = self.text_content[:max_length]
        last_space = preview.rfind(" ")
        
        if last_space > max_length // 2:
            preview = preview[:last_space]
            
        return f"{preview}... (texte tronqué, {len(self.text_content)} caractères au total)"

class DocumentConverter(ABC):
    """Interface de base pour les services de conversion de documents."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le convertisseur de documents.
        
        Args:
            config: Configuration spécifique au convertisseur
        """
        self.config = config or {}
        self.initialized = False
        
        # Initialiser les types MIME si nécessaire
        if not mimetypes.inited:
            mimetypes.init()
        
        # Ajouter des types MIME supplémentaires si non présents
        self._add_common_mimetypes()
    
    def _add_common_mimetypes(self):
        """Ajoute des types MIME courants s'ils ne sont pas déjà définis."""
        common_types = {
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.odt': 'application/vnd.oasis.opendocument.text',
            '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
            '.odp': 'application/vnd.oasis.opendocument.presentation',
            '.epub': 'application/epub+zip',
            '.rtf': 'application/rtf',
            '.md': 'text/markdown',
        }
        
        for ext, mime in common_types.items():
            if not mimetypes.types_map.get(ext):
                mimetypes.add_type(mime, ext)
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialise le convertisseur et vérifie que les dépendances sont disponibles.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abstractmethod
    async def convert_file(self, 
                    file_path: Union[str, Path],
                    output_format: str = "text",
                    **kwargs) -> ConversionResult:
        """
        Convertit un fichier en texte ou autre format.
        
        Args:
            file_path: Chemin vers le fichier à convertir
            output_format: Format de sortie (défaut: texte)
            **kwargs: Options spécifiques au convertisseur
            
        Returns:
            Résultat de la conversion
        """
        pass
    
    @abstractmethod
    async def convert_bytes(self,
                     content: Union[bytes, BinaryIO],
                     file_type: str,
                     output_format: str = "text",
                     **kwargs) -> ConversionResult:
        """
        Convertit un contenu binaire en texte ou autre format.
        
        Args:
            content: Contenu binaire à convertir
            file_type: Type du fichier (extension ou MIME type)
            output_format: Format de sortie (défaut: texte)
            **kwargs: Options spécifiques au convertisseur
            
        Returns:
            Résultat de la conversion
        """
        pass
    
    @abstractmethod
    async def extract_metadata(self,
                        file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extrait les métadonnées d'un fichier.
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            Dictionnaire des métadonnées
        """
        pass
    
    async def detect_file_type(self, file_path: Union[str, Path]) -> str:
        """
        Détecte le type de fichier.
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            Type MIME du fichier
        """
        path = Path(file_path)
        
        # Essayer d'abord avec l'extension
        mime_type, _ = mimetypes.guess_type(path.name)
        
        # Si aucun type n'est trouvé, essayer avec python-magic si disponible
        if not mime_type:
            try:
                import magic
                mime_type = magic.from_file(str(path), mime=True)
            except ImportError:
                logger.warning("python-magic non disponible, impossible de détecter le type MIME précis")
                # Utiliser un type par défaut basé sur l'extension
                mime_type = mimetypes.types_map.get(path.suffix.lower(), 'application/octet-stream')
        
        return mime_type
    
    async def supported_file_types(self) -> List[str]:
        """
        Retourne la liste des types de fichiers supportés.
        
        Returns:
            Liste des extensions de fichiers supportées
        """
        # À implémenter dans les classes concrètes
        return []
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Nom du provider de conversion.
        
        Returns:
            Nom du provider (ex: "standard", "advanced", etc.)
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """
        Indique si le convertisseur est initialisé.
        
        Returns:
            True si le convertisseur est initialisé, False sinon
        """
        return self.initialized
