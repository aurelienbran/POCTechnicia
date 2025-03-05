from qdrant_client import QdrantClient
from collections import defaultdict

def check_qdrant_status():
    try:
        client = QdrantClient("localhost", port=6333)
        
        # Obtenir les informations de la collection
        collection_info = client.get_collection("documents")
        print("\nÉtat de la collection:")
        print(f"Nombre de vecteurs: {collection_info.vectors_count}")
        print(f"Vecteurs indexés: {collection_info.indexed_vectors_count}")
        print(f"Nombre de segments: {collection_info.segments_count}")
        print(f"Status: {collection_info.status}")
        print(f"Status de l'optimiseur: {collection_info.optimizer_status}")
        
        # Récupérer les points
        points = client.scroll(
            collection_name="documents",
            limit=500,
            with_payload=True,
            with_vectors=False
        )[0]
        
        # Analyser la distribution des tailles de texte
        sizes = defaultdict(int)
        total_chars = 0
        for point in points:
            text = point.payload.get("text", "")
            text_size = len(text)
            total_chars += text_size
            # Grouper par tranches de 500 caractères
            size_group = (text_size // 500) * 500
            sizes[size_group] += 1
        
        print("\nDistribution des tailles de chunks:")
        for size, count in sorted(sizes.items()):
            print(f"{size}-{size+499} caractères: {count} chunks")
        
        print(f"\nNombre total de chunks: {len(points)}")
        if len(points) > 0:
            print(f"Taille moyenne des chunks: {total_chars/len(points):.0f} caractères")
            
    except Exception as e:
        print(f"Erreur: {str(e)}")

if __name__ == "__main__":
    check_qdrant_status()
