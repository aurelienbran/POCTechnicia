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
            
            # Considérer que l'initialisation a réussi même si la vérification échoue
            # à cause des problèmes de compatibilité avec les versions de Qdrant
            try:
                # Vérifier l'état de la collection
                collection_info = self.client.get_collection(self.collection_name)
                logger.info(f"État de la collection: {collection_info}")
            except Exception as validation_error:
                # Ne pas échouer si c'est une erreur de validation
                logger.warning(f"Impossible de récupérer les infos de collection (problème de version): {str(validation_error)}")
                
            # Marquer comme initialisé
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la collection: {str(e)}")
            # Essayer de continuer malgré l'erreur pour permettre le démarrage
            if "validation error" in str(e).lower() or "Extra inputs are not permitted" in str(e):
                logger.warning(f"Incompatibilité de version Qdrant détectée, mais on continue: {str(e)}")
                self._initialized = True
            else:
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

    async def add_text(self, collection_name: str, document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Ajoute un seul texte à la collection spécifiée.
        
        Args:
            collection_name: Nom de la collection où ajouter le texte
            document_id: Identifiant du document
            text: Texte à ajouter
            metadata: Métadonnées associées au texte
            
        Returns:
            ID du point ajouté
        """
        try:
            # Configurer la collection si nécessaire
            if collection_name != self.collection_name:
                logger.warning(f"Collection demandée ({collection_name}) différente de la collection actuelle ({self.collection_name})")
                # On garde la collection actuelle pour simplifier
                
            # Créer un dictionnaire de métadonnées si non fourni
            if metadata is None:
                metadata = {}
                
            # Ajouter l'ID du document aux métadonnées
            metadata["document_id"] = document_id
            
            # Créer le point
            point = await self._create_point(text, metadata)
            
            if not point:
                logger.error("Échec de la création du point")
                return ""
                
            # Ajouter le point à Qdrant
            operation_info = await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                points=[point],
                wait=True
            )
            
            if operation_info and operation_info.status == "completed":
                logger.info(f"Point ajouté avec succès: {point.id}")
                return str(point.id)
            else:
                logger.error(f"Échec de l'ajout du point: {operation_info}")
                return ""
                
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du texte: {str(e)}")
            return ""

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
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            elif not isinstance(embedding, list):
                logger.error(f"Type d'embedding invalide: {type(embedding)}")
                return None
            
            # Créer le point
            point_id = str(uuid.uuid4())
            payload = {
                "content": text,  # Changé de "text" à "content"
                "vector_size": len(embedding),
                "timestamp": time.time()
            }
            if metadata:
                payload.update(metadata)
                
            point = PointStruct(
                id=point_id,
                vector=embedding,  # Déjà une liste, pas besoin de tolist()
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
            embeddings = await self.llm_interface.get_embeddings([query])
            if not embeddings or len(embeddings) == 0:
                raise ValueError("Échec de la génération de l'embedding pour la requête")
            query_embedding = np.array(embeddings[0])
            
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
                try:
                    payload = res.payload or {}
                    formatted_results.append({
                        "id": str(res.id),
                        "score": float(res.score),
                        "payload": payload,
                        "text": payload.get("content", ""),
                        "metadata": {k: v for k, v in payload.items() if k != "content"}
                    })
                except Exception as e:
                    logger.error(f"Erreur lors du formatage d'un résultat: {str(e)}")
                    continue
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche sémantique: {str(e)}")
            raise

    async def similarity_search(
        self,
        query: str,
        k: int = 6,  # Augmenté de 4 à 6
        filter: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.5  # Réduit de 0.6 à 0.5
    ) -> List[Dict[str, Any]]:
        """
        Effectue une recherche sémantique dans la collection.
        Retourne les k documents les plus pertinents.
        """
        try:
            # Rechercher les documents similaires
            results = await self.search(query, filter=filter, limit=k * 2)  # On récupère plus de résultats pour filtrer
            
            # Filtrer les résultats par score de similarité
            filtered_results = [
                doc for doc in results 
                if doc["score"] >= score_threshold
            ]
            
            # Trier par score et prendre les k premiers
            sorted_results = sorted(filtered_results, key=lambda x: x["score"], reverse=True)[:k]
            
            # Enrichir les résultats avec des métadonnées utiles
            for result in sorted_results:
                result["content"] = result["text"]  # Pour la compatibilité
                result["relevance"] = f"{int(result['score'] * 100)}%"
                
            return sorted_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {str(e)}")
            return []

    async def get_embedding(self, text: str) -> np.ndarray:
        """Génère un embedding pour le texte donné via VoyageAI."""
        try:
            logger.info(f"Génération d'embedding pour un texte de {len(text)} caractères")
            
            if self.llm_interface is None:
                raise ValueError("LLMInterface n'est pas initialisé")
            
            embeddings = await self.llm_interface.get_embeddings([text])
            if not embeddings or len(embeddings) == 0:
                raise ValueError("Aucun embedding généré")
                
            embedding = embeddings[0]
            logger.info(f"Embedding généré avec succès, dimension: {len(embedding)}")
            return np.array(embedding)
            
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
                    "content": text,  # Changé de "text" à "content"
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

    async def get_collection_info(self) -> Dict[str, Any]:
        """Récupère les informations de la collection Qdrant."""
        try:
            collection_info = await asyncio.to_thread(
                self.client.get_collection,
                collection_name=self.collection_name
            )
            
            # Vérifier si nous avons un objet avec model_dump ou juste un dict
            if hasattr(collection_info, 'model_dump'):
                return collection_info.model_dump()
            elif isinstance(collection_info, dict):
                return collection_info
            else:
                # Construire un dictionnaire minimal en cas de problème
                return {
                    "name": self.collection_name,
                    "status": "active",  # Supposer que c'est actif
                    "vectors_count": 0,  # Valeur par défaut
                    "indexed_vectors_count": 0,  # Valeur par défaut
                    "config": {
                        "params": {
                            "vectors": {
                                "size": self.vector_size,
                                "distance": "cosine"
                            }
                        }
                    }
                }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations de la collection: {str(e)}")
            # Retourner un dictionnaire minimal avec des informations de base
            # pour éviter les erreurs en aval
            return {
                "name": self.collection_name,
                "status": "unknown",
                "error": str(e),
                "vectors_count": 0,
                "indexed_vectors_count": 0
            }
    
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """
        Récupère des statistiques détaillées sur la collection et les documents indexés.
        
        Returns:
            Un dictionnaire contenant des statistiques détaillées:
            - vectors_count: Nombre total de vecteurs
            - indexed_vectors_count: Nombre de vecteurs indexés
            - documents_count: Nombre de documents uniques
            - points_count: Nombre de points indexés
            - avg_vectors_per_document: Moyenne de vecteurs par document
            - collection_name: Nom de la collection
            - created_at: Date de création de la collection (si disponible)
            - metadata: Métadonnées supplémentaires
        """
        try:
            # Récupérer les informations de base de la collection
            collection_info = await self.get_collection_info()
            
            # Récupérer le nombre de points/vecteurs et vecteurs indexés
            vectors_count = collection_info.get("vectors_count", 0)
            indexed_vectors_count = collection_info.get("indexed_vectors_count", 0)
            
            # Récupérer les métadonnées uniques pour estimer le nombre de documents
            scroll_result = await asyncio.to_thread(
                self.client.scroll,
                collection_name=self.collection_name,
                limit=10000,  # Récupérer un maximum de 10000 points
                with_payload=True,
                with_vectors=False  # Pas besoin des vecteurs
            )
            
            # Extraire les métadonnées pour compter les documents uniques
            unique_documents = set()
            if scroll_result and scroll_result[0]:
                for point in scroll_result[0]:
                    if point.payload and "document_id" in point.payload:
                        unique_documents.add(point.payload["document_id"])
                    elif point.payload and "filename" in point.payload:
                        unique_documents.add(point.payload["filename"])
            
            documents_count = len(unique_documents)
            
            # Calculer la moyenne de vecteurs par document
            avg_vectors_per_document = 0
            if documents_count > 0:
                avg_vectors_per_document = vectors_count / documents_count
            
            # Compiler les statistiques
            stats = {
                "vectors_count": vectors_count,
                "indexed_vectors_count": indexed_vectors_count,
                "indexing_percentage": round((indexed_vectors_count / vectors_count * 100) if vectors_count > 0 else 0, 1),
                "documents_count": documents_count,
                "points_count": vectors_count,  # Synonyme, pour compatibilité
                "avg_vectors_per_document": round(avg_vectors_per_document, 2),
                "collection_name": self.collection_name,
                "is_empty": vectors_count == 0,
                "is_fully_indexed": indexed_vectors_count >= vectors_count,
                "metadata": {
                    "vector_size": collection_info.get("config", {}).get("params", {}).get("vectors", {}).get("size", 0),
                    "distance": collection_info.get("config", {}).get("params", {}).get("vectors", {}).get("distance", "unknown")
                }
            }
            
            logger.info(f"Statistiques de la collection récupérées: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques détaillées: {str(e)}", exc_info=True)
            return {
                "vectors_count": 0,
                "indexed_vectors_count": 0,
                "indexing_percentage": 0,
                "documents_count": 0,
                "points_count": 0,
                "avg_vectors_per_document": 0,
                "collection_name": self.collection_name,
                "is_empty": True,
                "is_fully_indexed": False,
                "error": str(e)
            }
