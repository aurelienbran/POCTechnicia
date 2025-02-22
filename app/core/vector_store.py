import uuid
import time
from typing import Dict, List, Optional, Any
import numpy as np
import logging
from qdrant_client import QdrantClient, models
from qdrant_client.http import models as rest
from qdrant_client.http.models import Distance, PointStruct, VectorParams, Filter
from app.config import settings
from app.core.llm_interface import LLMInterface
import asyncio
import shutil
import os

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Gère le stockage et la recherche des vecteurs dans Qdrant.
    """
    
    def __init__(
        self,
        collection_name: str = "documents",
        vector_size: int = 1024,
        llm_interface: Optional[LLMInterface] = None
    ):
        """
        Initialise le VectorStore.
        
        Args:
            collection_name: Nom de la collection
            vector_size: Taille des vecteurs d'embedding
            llm_interface: Interface avec le modèle de langage pour la génération d'embeddings
        """
        # Initialiser le client Qdrant
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.llm_interface = llm_interface
        self._initialized = False
    
    def __del__(self):
        """Nettoyage lors de la destruction de l'instance."""
        try:
            if hasattr(self, 'client'):
                self.client.close()
            if hasattr(self, 'storage_path') and self.storage_path.exists():
                shutil.rmtree(str(self.storage_path))
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de Qdrant: {str(e)}")
    
    @property
    def is_initialized(self) -> bool:
        """Retourne True si le VectorStore a été initialisé."""
        return self._initialized
    
    async def ensure_initialized(self) -> None:
        """S'assure que le VectorStore est initialisé."""
        if not self._initialized:
            await self.initialize()
            self._initialized = True

    async def initialize(self) -> None:
        """Initialise le VectorStore."""
        try:
            # Vérifier si la collection existe déjà
            collections = self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                # Créer la collection avec la configuration appropriée
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    ),
                    hnsw_config=dict(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000
                    ),
                    optimizers_config=dict(
                        deleted_threshold=0.2,
                        vacuum_min_vector_number=1000,
                        default_segment_number=2,
                        max_optimization_threads=2
                    )
                )
                logger.info(f"Collection {self.collection_name} créée avec succès")
            
            # Configurer la collection avec des paramètres plus conservateurs
            self.client.update_collection(
                collection_name=self.collection_name,
                optimizers_config=models.OptimizersConfigDiff(
                    deleted_threshold=0.2,
                    vacuum_min_vector_number=1000,
                    default_segment_number=1,  # Réduire le nombre de segments
                    max_optimization_threads=1,  # Limiter les threads
                    flush_interval_sec=10,      # Augmenter l'intervalle de flush
                    indexing_threshold=1000     # Indexer moins fréquemment
                )
            )
            logger.info(f"Configuration de {self.collection_name} mise à jour")
            
            # Attendre que la configuration soit appliquée
            await asyncio.sleep(2)
            
            # Vérifier l'état de la collection
            collection_info = self.client.get_collection(self.collection_name)
            logger.info(f"État de la collection: {collection_info}")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la collection: {str(e)}")
            raise e

    async def add_texts(self, texts: List[str], metadata: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Ajoute une liste de textes à la collection."""
        try:
            if not texts:
                logger.warning("Liste de textes vide")
                return []
                
            if metadata and len(metadata) != len(texts):
                raise ValueError("Le nombre de métadonnées doit correspondre au nombre de textes")
                
            # Créer les points
            points = []
            for i, text in enumerate(texts):
                try:
                    point = await self._create_point(text, metadata[i] if metadata else None)
                    if point:
                        points.append(point)
                except Exception as e:
                    logger.error(f"Erreur lors de la création du point {i}: {str(e)}")
                    raise
            
            if not points:
                logger.error("Aucun point n'a pu être créé")
                return []
            
            # Ajouter les points à Qdrant de manière asynchrone
            operation_info = await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                points=points,
                wait=True
            )
            
            if operation_info and operation_info.status == "completed":
                logger.info(f"{len(points)} points ajoutés avec succès")
                return [str(p.id) for p in points]
            else:
                logger.error("Échec de l'ajout des points")
                return []
                
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des textes: {str(e)}")
            raise

    async def _create_point(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[PointStruct]:
        """Crée un point pour Qdrant à partir d'un texte et de ses métadonnées."""
        try:
            # Générer l'embedding
            logger.info(f"Génération de l'embedding pour le texte de taille {len(text)}")
            embeddings = await self.llm_interface.get_embeddings([text])
            
            if not embeddings or len(embeddings) == 0:
                logger.error("Échec de la génération de l'embedding")
                return None
            
            embedding = embeddings[0]
            if not isinstance(embedding, np.ndarray):
                logger.error(f"Type d'embedding invalide: {type(embedding)}")
                return None
            
            # Créer le point
            point_id = str(uuid.uuid4())
            payload = {
                "text": text,
                "vector_size": len(embedding),
                "timestamp": time.time()
            }
            if metadata:
                payload.update(metadata)
                
            point = PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload
            )
            
            return point
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du point: {str(e)}")
            raise

    async def search(
        self,
        query: str,
        filter: Optional[Filter] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recherche les documents les plus similaires à la requête.
        
        Args:
            query: Texte de la requête
            filter: Filtre optionnel pour la recherche
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des documents trouvés avec leurs scores
        """
        try:
            # Générer l'embedding de la requête
            logger.info(f"Génération de l'embedding pour la requête: {query}")
            query_embedding = await self.llm_interface.get_embedding(query)
            if query_embedding is None:  # Vérification plus précise
                raise ValueError("Échec de la génération de l'embedding pour la requête")
            
            # Effectuer la recherche de manière synchrone
            logger.info("Recherche des documents similaires")
            results = await asyncio.to_thread(
                self.client.search,
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),  # Convertir en liste
                query_filter=filter,
                limit=limit,
                with_payload=True  # S'assurer d'obtenir les payloads
            )
            
            # Formater les résultats
            formatted_results = []
            for res in results:
                formatted_results.append({
                    "id": res.id,
                    "score": res.score,
                    "text": res.payload.get("text", ""),
                    "metadata": {k: v for k, v in res.payload.items() if k != "text"}
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche sémantique: {str(e)}")
            raise

    async def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Effectue une recherche sémantique dans la collection.
        Retourne les k documents les plus pertinents.
        """
        try:
            # Générer l'embedding pour la requête
            embeddings = await self.llm_interface.get_embeddings([query])
            if not embeddings:
                raise ValueError("Échec de la génération de l'embedding pour la requête")
            query_embedding = embeddings[0]

            # Préparer le filtre
            search_filter = None
            if filter:
                search_filter = Filter(**filter)

            # Effectuer la recherche de manière synchrone
            results = await asyncio.to_thread(
                self.client.search,
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=k,
                query_filter=search_filter,
                with_payload=True
            )

            # Formater les résultats
            formatted_results = []
            for res in results:
                result = {
                    'id': res.id,
                    'score': res.score,
                    'text': res.payload.get('text', ''),
                    'metadata': {k: v for k, v in res.payload.items() if k != 'text'}
                }
                formatted_results.append(result)

            return formatted_results

        except Exception as e:
            logger.error(f"Erreur lors de la recherche sémantique: {str(e)}")
            raise

    async def get_embedding(self, text: str) -> np.ndarray:
        """Génère un embedding pour le texte donné via VoyageAI."""
        try:
            logger.info(f"Génération d'embedding pour un texte de {len(text)} caractères")
            
            if self.llm_interface is None:
                raise ValueError("LLMInterface n'est pas initialisé")
            
            embedding = await self.llm_interface.get_embedding(text)
            logger.info(f"Embedding généré avec succès, dimension: {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'embedding: {str(e)}")
            logger.error(f"Type d'erreur: {type(e).__name__}")
            raise

    async def add_documents(
        self,
        embeddings: List[np.ndarray],
        texts: List[str],
        metadata_list: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Ajoute des documents avec leurs embeddings pré-calculés.
        
        Args:
            embeddings: Liste des embeddings
            texts: Liste des textes correspondants
            metadata_list: Liste des métadonnées associées
            
        Returns:
            Liste des IDs des points ajoutés
        """
        try:
            if not embeddings or not texts or not metadata_list:
                logger.error("Paramètres invalides pour add_documents")
                return []

            if len(embeddings) != len(texts) or len(texts) != len(metadata_list):
                logger.error("Les listes doivent avoir la même longueur")
                return []

            # Préparer les points à ajouter
            points = []
            point_ids = []
            for emb, text, meta in zip(embeddings, texts, metadata_list):
                point_id = str(uuid.uuid4())
                point_ids.append(point_id)
                
                # Ajouter le texte aux métadonnées
                payload = {
                    "text": text,
                    **meta
                }
                
                # Créer le point
                point = PointStruct(
                    id=point_id,
                    vector=emb.tolist(),
                    payload=payload
                )
                points.append(point)

            # Ajouter les points de manière synchrone
            logger.info(f"Ajout de {len(points)} points dans Qdrant")
            result = await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                points=points
            )

            if result and result.status == "completed":
                logger.info(f"Points ajoutés avec succès : {point_ids}")
                return point_ids
            else:
                logger.error(f"Échec de l'ajout des points : {result}")
                return []

        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des documents : {str(e)}", exc_info=True)
            return []

    async def delete_documents(self, ids: List[str]) -> bool:
        """Supprime les documents spécifiés de la collection."""
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=ids
                )
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des documents: {str(e)}")
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        """Récupère les informations de la collection Qdrant."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status,
                "optimization_status": info.optimizer_status
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations de la collection: {str(e)}")
            return {}
