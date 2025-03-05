"""
Script pour supprimer toutes les collections dans Qdrant
"""
from qdrant_client import QdrantClient
import sys

try:
    # Connexion au serveur Qdrant
    client = QdrantClient(host='localhost', port=6333)
    
    # Récupérer la liste des collections
    collections = client.get_collections().collections
    
    if collections:
        collection_count = len(collections)
        for collection in collections:
            client.delete_collection(collection_name=collection.name)
            print(f"Collection '{collection.name}' supprimee.")
        
        print(f"Toutes les collections ({collection_count}) ont ete supprimees avec succes.")
    else:
        print("Aucune collection n'existe dans Qdrant.")
    
    sys.exit(0)
except Exception as e:
    print(f"Erreur: {str(e)}")
    sys.exit(1)
