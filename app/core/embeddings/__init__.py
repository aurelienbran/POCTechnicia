"""
Package pour la gestion des services d'embeddings.
"""

from .base import (
    EmbeddingService, 
    EmbeddingResult, 
    EmbeddingError,
    EmbeddingRequestTimeoutError,
    EmbeddingServiceUnavailableError,
    EmbeddingAuthenticationError,
    BatchProcessor
)
from .voyage import VoyageAIEmbeddingService

__all__ = [
    'EmbeddingService',
    'EmbeddingResult',
    'EmbeddingError',
    'EmbeddingRequestTimeoutError',
    'EmbeddingServiceUnavailableError',
    'EmbeddingAuthenticationError',
    'BatchProcessor',
    'VoyageAIEmbeddingService',
    'get_embedding_service',
]

def get_embedding_service(provider: str = "voyage", **kwargs) -> EmbeddingService:
    """
    Factory pour obtenir une instance de service d'embeddings.
    
    Args:
        provider: Fournisseur d'embeddings ("voyage" par défaut)
        **kwargs: Arguments spécifiques au fournisseur
        
    Returns:
        Instance de service d'embeddings
        
    Raises:
        ValueError: Si le fournisseur n'est pas supporté
    """
    if provider.lower() == "voyage":
        return VoyageAIEmbeddingService(**kwargs)
    else:
        raise ValueError(f"Fournisseur d'embeddings non supporté: {provider}")
