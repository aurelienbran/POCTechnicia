from qdrant_client import QdrantClient
from qdrant_client.http import models
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_qdrant():
    try:
        # Connexion à Qdrant
        client = QdrantClient("localhost", port=6333)
        
        # Supprimer la collection si elle existe
        collections = client.get_collections()
        if any(col.name == "documents" for col in collections.collections):
            logger.info("Suppression de la collection existante 'documents'")
            client.delete_collection("documents")
        
        # Créer une nouvelle collection avec des paramètres optimisés pour RAG
        client.create_collection(
            collection_name="documents",
            vectors_config=models.VectorParams(
                size=1024,  # Taille des vecteurs de VoyageAI
                distance=models.Distance.COSINE  # Distance cosinus pour la similarité sémantique
            ),
            optimizers_config=models.OptimizersConfigDiff(
                deleted_threshold=0.1,  # Réduit pour un nettoyage plus fréquent
                vacuum_min_vector_number=5000,  # Augmenté pour les gros PDFs
                default_segment_number=5,  # Augmenté pour une meilleure distribution (PDFs de 150Mo)
                max_optimization_threads=2,  # Limité pour respecter la contrainte de 1GB
                flush_interval_sec=20,  # Réduit pour une meilleure durabilité
                indexing_threshold=10000  # Ajusté pour un bon compromis performance/mémoire
            ),
            hnsw_config=models.HnswConfigDiff(
                m=16,  # Valeur standard pour un bon compromis précision/performance
                ef_construct=100,  # Réduit pour économiser la mémoire
                full_scan_threshold=10000,  # Seuil pour basculer en scan complet
                max_indexing_threads=2,  # Limité pour la contrainte mémoire
                on_disk=True  # Stockage sur disque pour les gros volumes
            ),
            on_disk_payload=True  # Stockage payload sur disque (PDFs volumineux)
        )
        
        logger.info("Collection 'documents' créée avec succès")
        
        # Vérifier la création
        collection_info = client.get_collection("documents")
        logger.info(f"État de la collection : {collection_info.status}")
        logger.info(f"Configuration : {collection_info.config}")
        
        # Vérifier les paramètres de performance
        logger.info("Vérification des paramètres de performance...")
        logger.info(f"Nombre de segments : {collection_info.segments_count}")
        logger.info(f"Nombre de vecteurs : {collection_info.vectors_count}")
        logger.info(f"Statut de l'optimiseur : {collection_info.optimizer_status}")
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de Qdrant : {str(e)}")
        return False

if __name__ == "__main__":
    success = initialize_qdrant()
    sys.exit(0 if success else 1)
