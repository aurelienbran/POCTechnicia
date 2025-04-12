"""
Implémentation du service d'embeddings utilisant Voyage AI.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from .base import EmbeddingService, EmbeddingResult, EmbeddingError, EmbeddingAuthenticationError

logger = logging.getLogger(__name__)

class VoyageAIEmbeddingService(EmbeddingService):
    """Service d'embeddings utilisant l'API Voyage AI."""
    
    def __init__(self, model_name: str = "voyage-2", api_key: Optional[str] = None):
        """
        Initialise le service d'embeddings Voyage AI.
        
        Args:
            model_name: Nom du modèle Voyage AI à utiliser
            api_key: Clé API Voyage AI (si non fournie, utilise celle des settings)
        """
        super().__init__(model_name)
        self.api_key = api_key or settings.VOYAGE_API_KEY
        self._client = None
        self._initialized = False
    
    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def initialize(self) -> bool:
        """
        Initialise le client Voyage AI et vérifie sa connectivité.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        try:
            if not self.api_key:
                logger.error("VOYAGE_API_KEY non définie")
                raise EmbeddingAuthenticationError("Clé API Voyage AI non définie")
            
            # Définir la clé API dans l'environnement
            os.environ["VOYAGE_API_KEY"] = self.api_key
            
            # Import ici pour éviter les problèmes de dépendance circulaire
            import voyageai
            self._client = voyageai.Client()
            
            # Test de connexion avec un texte simple
            test_text = "Test de connexion Voyage AI"
            test_result = await self.embed_batch([test_text])
            
            # Vérifier que l'embedding généré est valide
            if (not test_result.embeddings or 
                not isinstance(test_result.embeddings[0], list) or 
                len(test_result.embeddings[0]) != 1024):
                raise ValueError(f"Embedding de test invalide: attendu 1024 dimensions")
            
            self._initialized = True
            logger.info("Service Voyage AI initialisé avec succès")
            return True
            
        except Exception as e:
            self._initialized = False
            logger.error(f"Erreur lors de l'initialisation du service Voyage AI: {str(e)}")
            
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                raise EmbeddingAuthenticationError(f"Erreur d'authentification Voyage AI: {str(e)}")
            else:
                raise EmbeddingError(f"Erreur d'initialisation Voyage AI: {str(e)}")
    
    async def embed_batch(self, texts: List[str], timeout: int = 120) -> EmbeddingResult:
        """
        Génère des embeddings pour un lot de textes via l'API Voyage AI.
        
        Args:
            texts: Liste des textes à encoder
            timeout: Timeout en secondes
            
        Returns:
            Résultat contenant les embeddings générés
        """
        if not self._initialized or not self._client:
            success = await self.initialize()
            if not success:
                raise EmbeddingError("Le service Voyage AI n'est pas initialisé correctement")
        
        try:
            # Appel à l'API avec timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.embed,
                    texts,
                    model=self.model_name
                ),
                timeout=timeout
            )
            
            # Validation de la réponse
            batch_embeddings = response.embeddings
            if len(batch_embeddings) != len(texts):
                raise ValueError(f"Nombre d'embeddings ({len(batch_embeddings)}) différent du nombre de textes ({len(texts)})")
            
            return EmbeddingResult(
                embeddings=batch_embeddings,
                original_texts=texts,
                metadata={"model": self.model_name}
            )
            
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout lors de l'appel à Voyage AI (timeout={timeout}s): {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Voyage AI: {str(e)}")
            raise
