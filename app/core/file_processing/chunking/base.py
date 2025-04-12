"""
Définit l'interface de base pour les services de chunking de texte.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ChunkingResult:
    """Résultat d'une opération de chunking."""
    
    chunks: List[str]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Ajouter des statistiques de base
        self.metadata.update({
            "chunk_count": len(self.chunks),
            "avg_chunk_length": sum(len(chunk) for chunk in self.chunks) / max(len(self.chunks), 1),
            "min_chunk_length": min((len(chunk) for chunk in self.chunks), default=0),
            "max_chunk_length": max((len(chunk) for chunk in self.chunks), default=0),
        })
    
    @property
    def count(self) -> int:
        """Nombre de chunks générés."""
        return len(self.chunks)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "chunks": self.chunks,
            "metadata": self.metadata or {},
            "count": self.count,
        }

class TextChunker(ABC):
    """Interface de base pour les services de chunking de texte."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le service de chunking.
        
        Args:
            config: Configuration spécifique au chunker
        """
        self.config = config or {}
    
    @abstractmethod
    async def chunk_text(self, 
                  text: str, 
                  max_chunk_size: Optional[int] = None,
                  overlap: Optional[int] = None,
                  **kwargs) -> ChunkingResult:
        """
        Découpe un texte en chunks.
        
        Args:
            text: Texte à découper
            max_chunk_size: Taille maximale d'un chunk (caractères ou tokens)
            overlap: Chevauchement entre les chunks
            **kwargs: Options spécifiques au chunker
            
        Returns:
            Résultat du chunking contenant les chunks générés
        """
        pass
    
    @abstractmethod
    async def chunk_document(self,
                     document_text: str,
                     document_metadata: Optional[Dict[str, Any]] = None,
                     **kwargs) -> ChunkingResult:
        """
        Découpe un document entier en chunks en tenant compte de sa structure.
        
        Args:
            document_text: Texte du document à découper
            document_metadata: Métadonnées du document (titre, auteur, etc.)
            **kwargs: Options spécifiques au chunker
            
        Returns:
            Résultat du chunking contenant les chunks générés
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Nom du provider de chunking.
        
        Returns:
            Nom du provider (ex: "simple", "semantic", etc.)
        """
        pass
