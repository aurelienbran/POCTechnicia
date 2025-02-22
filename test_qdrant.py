from qdrant_client import QdrantClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
host = "localhost"
port = 6333

try:
    # Connexion à Qdrant
    client = QdrantClient(host=host, port=port)
    
    # Test simple : obtenir la liste des collections
    collections = client.get_collections()
    
    print(f"Connexion à Qdrant réussie!")
    print(f"Collections disponibles : {collections}")
    
except Exception as e:
    print(f"Erreur lors de la connexion à Qdrant: {str(e)}")
    print(f"Type d'erreur: {type(e).__name__}")
