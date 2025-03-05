"""
Script pour créer un snapshot Qdrant
"""
from qdrant_client import QdrantClient
import sys
import os
from datetime import datetime

# Chemin pour les snapshots
snapshot_dir = sys.argv[1] if len(sys.argv) > 1 else None

if not snapshot_dir:
    print("Erreur: Chemin du dossier de snapshots non fourni.")
    sys.exit(1)

try:
    # Créer le dossier de snapshots s'il n'existe pas
    if not os.path.exists(snapshot_dir):
        os.makedirs(snapshot_dir)
    
    # Connexion au serveur Qdrant
    client = QdrantClient(host='localhost', port=6333)
    
    # Récupérer la liste des collections
    collections = client.get_collections().collections
    collection_names = [collection.name for collection in collections]
    
    if not collections:
        print("Aucune collection n'existe dans Qdrant. Rien à sauvegarder.")
        sys.exit(0)
    
    # Créer un nom de fichier de snapshot avec l'horodatage
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"qdrant_snapshot_{timestamp}"
    snapshot_path = os.path.join(snapshot_dir, snapshot_name)
    
    # Créer le snapshot
    for collection_name in collection_names:
        try:
            client.create_snapshot(collection_name=collection_name, 
                                  snapshot_path=os.path.join(snapshot_dir, f"{collection_name}_{snapshot_name}"))
            print(f"Snapshot de la collection '{collection_name}' créé avec succès.")
        except Exception as inner_e:
            print(f"Erreur lors de la création du snapshot pour la collection '{collection_name}': {str(inner_e)}")
    
    print(f"Snapshots créés dans le dossier: {snapshot_dir}")
    sys.exit(0)
except Exception as e:
    print(f"Erreur: {str(e)}")
    sys.exit(1)
