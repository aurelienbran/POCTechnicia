"""
Script pour supprimer la collection 'documents' dans Qdrant
"""
from qdrant_client import QdrantClient
import sys

try:
    # Connexion au serveur Qdrant
    client = QdrantClient(host='localhost', port=6333)
    
    # Récupérer les collections existantes pour vérifier si 'documents' existe
    collections_list = client.get_collections().collections
    collection_names = [collection.name for collection in collections_list]
    
    if 'documents' in collection_names:
        # La collection existe, on peut la supprimer
        client.delete_collection(collection_name='documents')
        print("Collection 'documents' supprimee avec succes.")
    else:
        print("La collection 'documents' n'existe pas.")
    
    sys.exit(0)
except Exception as e:
    print(f"Erreur: {str(e)}")
    sys.exit(1)
