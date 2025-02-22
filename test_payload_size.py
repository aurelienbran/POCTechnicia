import numpy as np
import json
from qdrant_client.http import models as rest
import sys

# Simuler un embedding (dimension 1024 comme VoyageAI)
vector = np.random.random(1024).tolist()

# Simuler des métadonnées typiques
metadata = {
    "source": "test.pdf",
    "title": "Test Document",
    "page": 1,
    "text": "X" * 1000  # Simuler 1000 caractères de texte
}

# Créer un point
point = rest.PointStruct(
    id="test",
    vector=vector,
    payload=metadata
)

# Convertir en JSON et calculer la taille
point_json = point.json()
size_bytes = sys.getsizeof(point_json)

print(f"Taille d'un point en JSON: {size_bytes:,} bytes")
print(f"Taille maximale Qdrant: 33,554,432 bytes")
print(f"Nombre maximum théorique de points par lot: {33554432 // size_bytes}")

# Afficher le détail des tailles
vector_size = sys.getsizeof(json.dumps(vector))
metadata_size = sys.getsizeof(json.dumps(metadata))

print(f"\nDétail des tailles:")
print(f"- Vector: {vector_size:,} bytes")
print(f"- Metadata: {metadata_size:,} bytes")
