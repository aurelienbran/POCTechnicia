"""Script pour réinitialiser la collection Qdrant."""
from qdrant_client import QdrantClient
from qdrant_client.http import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_collection():
    """Réinitialise la collection documents."""
    try:
        # Connexion à Qdrant
        client = QdrantClient("localhost", port=6333)
        
        # Supprimer la collection si elle existe
        collections = client.get_collections()
        if any(col.name == "documents" for col in collections.collections):
            logger.info("Suppression de la collection documents...")
            client.delete_collection("documents")
        
        # Recréer la collection avec la bonne configuration
        logger.info("Création de la nouvelle collection documents...")
        client.create_collection(
            collection_name="documents",
            vectors_config=models.VectorParams(
                size=1024,
                distance=models.Distance.COSINE
            ),
            optimizers_config=models.OptimizersConfigDiff(
                default_segment_number=2
            )
        )
        
        logger.info("Collection réinitialisée avec succès !")
        
    except Exception as e:
        logger.error(f"Erreur lors de la réinitialisation : {str(e)}")
        raise

if __name__ == "__main__":
    reset_collection()
