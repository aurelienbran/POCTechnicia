import pytest
from app.core.vector_store import VectorStore
import numpy as np
from unittest.mock import patch, MagicMock, PropertyMock
import asyncio
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http import models as rest

class MockQdrantResponse:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

@pytest.fixture
def mock_qdrant():
    mock_client = MagicMock()
    
    # Mock collection info
    mock_collection = MockQdrantResponse(
        name="test_collection",
        vectors_count=0,
        status="green",
        config=MagicMock(
            params=MagicMock(
                vectors=MagicMock(
                    size=1024,
                    distance=Distance.COSINE
                )
            )
        )
    )
    mock_client.get_collection.return_value = mock_collection
    
    # Mock create collection
    mock_client.create_collection.return_value = None
    
    # Mock search results
    mock_search_result = MockQdrantResponse(
        id="1",
        payload={"text": "test"},
        score=0.9,
        version=1
    )
    mock_client.search.return_value = [mock_search_result]
    
    # Mock upsert
    mock_client.upsert.return_value = rest.UpdateResult(
        operation_id=1,
        status="completed"
    )
    
    # Mock delete
    mock_client.delete.return_value = rest.UpdateResult(
        operation_id=1,
        status="completed"
    )
    
    with patch('qdrant_client.QdrantClient', return_value=mock_client):
        yield mock_client

@pytest.fixture
def vector_store(mock_qdrant):
    return VectorStore(collection_name="test_collection")

@pytest.fixture
def mock_embedding():
    return np.random.rand(1024).tolist()

@pytest.mark.asyncio
async def test_vector_store_initialization(vector_store):
    assert vector_store.collection_name == "test_collection"
    assert vector_store.dimension == 1024
    collection_info = vector_store.get_collection_info()
    assert collection_info["name"] == "test_collection"
    assert collection_info["dimension"] == 1024

@pytest.mark.asyncio
@patch('app.core.vector_store.get_embedding')
async def test_get_embedding(mock_get_embedding, vector_store, mock_embedding):
    mock_get_embedding.return_value = mock_embedding
    
    text = "Test text"
    embedding = await vector_store.get_embedding(text)
    
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (1024,)
    mock_get_embedding.assert_called_once()

@pytest.mark.asyncio
@patch('app.core.vector_store.get_embedding')
async def test_add_texts(mock_get_embedding, vector_store, mock_embedding):
    mock_get_embedding.return_value = mock_embedding
    
    texts = ["Text 1", "Text 2"]
    metadata = [{"source": "test1"}, {"source": "test2"}]
    ids = ["1", "2"]
    
    result_ids = await vector_store.add_texts(texts, metadata, ids)
    
    assert len(result_ids) == 2
    assert result_ids == ids
    assert mock_get_embedding.call_count == 2
    vector_store.client.upsert.assert_called_once()

@pytest.mark.asyncio
@patch('app.core.vector_store.get_embedding')
async def test_similarity_search(mock_get_embedding, vector_store, mock_embedding):
    mock_get_embedding.return_value = mock_embedding
    
    query = "Test query"
    results = await vector_store.similarity_search(query, k=2)
    
    assert isinstance(results, list)
    assert len(results) > 0
    assert "score" in results[0]
    assert "metadata" in results[0]
    mock_get_embedding.assert_called_once()
    vector_store.client.search.assert_called_once()

@pytest.mark.asyncio
async def test_delete_documents(vector_store):
    ids_to_delete = ["1", "2"]
    await vector_store.delete_documents(ids_to_delete)
    vector_store.client.delete.assert_called_once()

@pytest.mark.asyncio
async def test_collection_info(vector_store):
    info = vector_store.get_collection_info()
    assert isinstance(info, dict)
    assert "name" in info
    assert "dimension" in info
    assert "distance" in info
    assert info["distance"] == "cosine"

@pytest.mark.asyncio
@patch('app.core.vector_store.get_embedding')
async def test_batch_processing(mock_get_embedding, vector_store, mock_embedding):
    mock_get_embedding.return_value = mock_embedding
    
    num_texts = 120
    texts = [f"Text {i}" for i in range(num_texts)]
    metadata = [{"source": f"test{i}"} for i in range(num_texts)]
    
    result_ids = await vector_store.add_texts(texts, metadata)
    
    assert len(result_ids) == num_texts
    assert mock_get_embedding.call_count == num_texts
    # Vérifier que upsert a été appelé le bon nombre de fois (3 lots de 50)
    assert vector_store.client.upsert.call_count == 3

@pytest.mark.asyncio
@patch('app.core.vector_store.get_embedding')
async def test_error_handling(mock_get_embedding, vector_store):
    mock_get_embedding.side_effect = Exception("Test error")
    
    with pytest.raises(Exception):
        await vector_store.get_embedding("Test text")

@pytest.mark.asyncio
@patch('app.core.vector_store.get_embedding')
async def test_search_with_filter(mock_get_embedding, vector_store, mock_embedding):
    mock_get_embedding.return_value = mock_embedding
    
    query = "Test query"
    filter_dict = {"metadata_field": {"$eq": "test_value"}}
    
    results = await vector_store.similarity_search(
        query,
        k=2,
        filter=filter_dict
    )
    
    assert isinstance(results, list)
    assert len(results) > 0
    mock_get_embedding.assert_called_once()
    vector_store.client.search.assert_called_once()

@pytest.mark.asyncio
async def test_embedding_memory_performance(vector_store):
    """Test de performance mémoire pour la génération d'embeddings."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # En MB
    
    # Générer un grand jeu de données de test
    num_texts = 100
    text_length = 1000  # caractères par texte
    test_texts = [
        "x" * text_length + f" test text {i}" 
        for i in range(num_texts)
    ]
    
    memory_usage = []
    embeddings = []
    
    try:
        # Générer les embeddings par lots
        batch_size = 10
        for i in range(0, len(test_texts), batch_size):
            batch = test_texts[i:i + batch_size]
            
            # Mesurer la mémoire avant le traitement du lot
            before_memory = process.memory_info().rss / 1024 / 1024
            
            # Générer les embeddings pour le lot
            batch_embeddings = await asyncio.gather(*[
                vector_store.get_embedding(text) 
                for text in batch
            ])
            embeddings.extend(batch_embeddings)
            
            # Mesurer la mémoire après le traitement
            after_memory = process.memory_info().rss / 1024 / 1024
            memory_usage.append(after_memory - before_memory)
            
            # Vérifier que l'utilisation de la mémoire reste raisonnable
            assert after_memory - initial_memory < 1024, \
                f"Utilisation mémoire excessive: {after_memory - initial_memory:.2f}MB"
            
            # Vérifier que les embeddings sont de la bonne dimension
            for emb in batch_embeddings:
                assert isinstance(emb, np.ndarray)
                assert emb.shape == (1024,)
        
        # Calculer et logger les statistiques
        avg_memory = sum(memory_usage) / len(memory_usage)
        max_memory = max(memory_usage)
        
        print(f"\nStatistiques d'utilisation mémoire pour {num_texts} textes:")
        print(f"- Mémoire moyenne par lot: {avg_memory:.2f}MB")
        print(f"- Pic mémoire: {max_memory:.2f}MB")
        print(f"- Utilisation totale: {after_memory - initial_memory:.2f}MB")
        
    except Exception as e:
        print(f"Erreur pendant le test de mémoire: {str(e)}")
        raise
