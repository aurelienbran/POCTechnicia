"""
Script pour restaurer un snapshot Qdrant
"""
from qdrant_client import QdrantClient
import sys
import os
import glob

# Chemin pour les snapshots
snapshot_dir = sys.argv[1] if len(sys.argv) > 1 else None
snapshot_name = sys.argv[2] if len(sys.argv) > 2 else None

if not snapshot_dir or not snapshot_name:
    print("Erreur: Chemin du dossier de snapshots ou nom du snapshot non fourni.")
    sys.exit(1)

try:
    # Connexion au serveur Qdrant
    client = QdrantClient(host='localhost', port=6333)
    
    # Récupérer les fichiers de snapshots correspondant au nom
    snapshot_files = glob.glob(os.path.join(snapshot_dir, f"*{snapshot_name}*"))
    
    if not snapshot_files:
        print(f"Aucun snapshot trouvé avec le nom: {snapshot_name}")
        sys.exit(1)
    
    # Restaurer chaque snapshot
    for snapshot_file in snapshot_files:
        snapshot_basename = os.path.basename(snapshot_file)
        collection_name = snapshot_basename.split('_')[0]
        
        try:
            # Vérifier si la collection existe déjà
            collections = client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if collection_name in collection_names:
                print(f"La collection '{collection_name}' existe déjà. Suppression...")
                client.delete_collection(collection_name=collection_name)
            
            # Restaurer le snapshot
            client.recover_snapshot(collection_name=collection_name, 
                                   snapshot_path=snapshot_file)
            
            print(f"Snapshot restauré pour la collection '{collection_name}'.")
        except Exception as inner_e:
            print(f"Erreur lors de la restauration du snapshot pour la collection '{collection_name}': {str(inner_e)}")
    
    print("Restauration des snapshots terminée.")
    sys.exit(0)
except Exception as e:
    print(f"Erreur: {str(e)}")
    sys.exit(1)
