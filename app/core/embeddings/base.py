"""
Module de base pour les services d'embeddings.
Définit les interfaces abstraites pour les différents fournisseurs d'embeddings.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import time
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class EmbeddingError(Exception):
    """Exception personnalisée pour les erreurs d'embeddings."""
    pass

class EmbeddingRequestTimeoutError(EmbeddingError):
    """Exception spécifique pour les erreurs de timeout."""
    pass

class EmbeddingServiceUnavailableError(EmbeddingError):
    """Exception spécifique pour les services indisponibles."""
    pass

class EmbeddingAuthenticationError(EmbeddingError):
    """Exception spécifique pour les erreurs d'authentification."""
    pass

class EmbeddingResult:
    """Conteneur pour les résultats d'embedding."""
    
    def __init__(self, 
                 embeddings: List[List[float]], 
                 original_texts: List[str],
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialise un résultat d'embedding.
        
        Args:
            embeddings: Liste des vecteurs d'embedding
            original_texts: Liste des textes originaux
            metadata: Métadonnées additionnelles (temps de traitement, etc.)
        """
        self.embeddings = embeddings
        self.original_texts = original_texts
        self.metadata = metadata or {}
        
    @property
    def dimensions(self) -> int:
        """Retourne la dimension des embeddings."""
        if not self.embeddings or not self.embeddings[0]:
            return 0
        return len(self.embeddings[0])
    
    @property
    def count(self) -> int:
        """Retourne le nombre d'embeddings."""
        return len(self.embeddings)

class BatchProcessor:
    """Gestionnaire pour le traitement par lots."""
    
    def __init__(self, 
                 batch_size: int = 10, 
                 max_retries: int = 3, 
                 base_timeout: int = 120,
                 max_timeout: int = 600):
        """
        Initialise un processeur par lots.
        
        Args:
            batch_size: Taille de chaque lot
            max_retries: Nombre maximal de tentatives en cas d'échec
            base_timeout: Timeout de base en secondes
            max_timeout: Timeout maximal en secondes
        """
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.base_timeout = base_timeout
        self.max_timeout = max_timeout
    
    def split_into_batches(self, items: List[Any]) -> List[List[Any]]:
        """
        Divise une liste d'éléments en lots.
        
        Args:
            items: Liste des éléments à diviser
            
        Returns:
            Liste des lots
        """
        batches = []
        for i in range(0, len(items), self.batch_size):
            batches.append(items[i:i + self.batch_size])
        return batches
    
    def calculate_timeout(self, retry_count: int) -> int:
        """
        Calcule le timeout pour une tentative donnée.
        
        Args:
            retry_count: Numéro de la tentative
            
        Returns:
            Timeout en secondes
        """
        # Augmenter progressivement le timeout à chaque tentative
        timeout = min(self.base_timeout * (1.5 ** retry_count), self.max_timeout)
        return int(timeout)

class EmbeddingService(ABC):
    """Interface abstraite pour les services d'embeddings."""
    
    def __init__(self, model_name: str):
        """
        Initialise le service d'embedding.
        
        Args:
            model_name: Nom du modèle à utiliser
        """
        self.model_name = model_name
        self.batch_processor = BatchProcessor()
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialise le service d'embedding.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abstractmethod
    async def embed_batch(self, 
                   texts: List[str], 
                   timeout: int = 120) -> EmbeddingResult:
        """
        Génère des embeddings pour un lot de textes.
        
        Args:
            texts: Liste des textes à encoder
            timeout: Timeout en secondes
            
        Returns:
            Résultat contenant les embeddings générés
        """
        pass
    
    @retry(reraise=True,
           stop=stop_after_attempt(3), 
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def embed(self, 
              texts: List[str], 
              batch_size: Optional[int] = None,
              max_retries: Optional[int] = None, 
              base_timeout: Optional[int] = None) -> EmbeddingResult:
        """
        Génère des embeddings pour une liste de textes en traitant par lots.
        
        Args:
            texts: Liste des textes à encoder
            batch_size: Taille de chaque lot (défaut: valeur du BatchProcessor)
            max_retries: Nombre maximal de tentatives (défaut: valeur du BatchProcessor)
            base_timeout: Timeout de base en secondes (défaut: valeur du BatchProcessor)
            
        Returns:
            Résultat contenant tous les embeddings générés
        """
        if not texts:
            return EmbeddingResult([], [])
        
        # Configuration du traitement par lots
        if batch_size is not None:
            self.batch_processor.batch_size = batch_size
        if max_retries is not None:
            self.batch_processor.max_retries = max_retries
        if base_timeout is not None:
            self.batch_processor.base_timeout = base_timeout
            
        batches = self.batch_processor.split_into_batches(texts)
        total_batches = len(batches)
        all_embeddings = []
        processed_batches = 0
        
        logger.info(f"Traitement de {len(texts)} textes en {total_batches} lots de maximum {self.batch_processor.batch_size} textes")
        start_time_total = time.time()
        
        for batch_num, batch in enumerate(batches, 1):
            # Traitement du lot avec mécanisme de retry
            retry_count = 0
            batch_success = False
            
            while not batch_success and retry_count < self.batch_processor.max_retries:
                try:
                    current_timeout = self.batch_processor.calculate_timeout(retry_count)
                    logger.info(f"Traitement du lot {batch_num}/{total_batches} ({len(batch)} textes) avec timeout={current_timeout}s")
                    
                    start_time_batch = time.time()
                    batch_result = await self.embed_batch(batch, timeout=current_timeout)
                    
                    all_embeddings.extend(batch_result.embeddings)
                    processing_time = time.time() - start_time_batch
                    
                    logger.info(f"Lot {batch_num}/{total_batches} traité en {processing_time:.2f}s")
                    batch_success = True
                    processed_batches += 1
                    
                except asyncio.TimeoutError:
                    retry_count += 1
                    logger.warning(f"Timeout lors du traitement du lot {batch_num}/{total_batches}. Tentative {retry_count}/{self.batch_processor.max_retries}")
                    
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Erreur lors du traitement du lot {batch_num}/{total_batches}: {str(e)}. Tentative {retry_count}/{self.batch_processor.max_retries}")
                    await asyncio.sleep(2 ** retry_count)  # Backoff exponentiel
            
            # Si le lot a échoué après toutes les tentatives
            if not batch_success:
                total_time = time.time() - start_time_total
                logger.error(f"Échec du traitement du lot {batch_num}/{total_batches} après {self.batch_processor.max_retries} tentatives. Temps total: {total_time:.2f}s")
                raise EmbeddingError(f"Impossible de générer les embeddings pour le lot {batch_num}")
        
        total_time = time.time() - start_time_total
        logger.info(f"Génération des embeddings terminée: {processed_batches}/{total_batches} lots traités en {total_time:.2f}s")
        
        metadata = {
            "processing_time": total_time,
            "processed_batches": processed_batches,
            "total_batches": total_batches,
            "model_name": self.model_name
        }
        
        return EmbeddingResult(all_embeddings, texts, metadata=metadata)
