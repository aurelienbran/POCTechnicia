"""Configuration des tests."""
import os
import sys
import asyncio
from pathlib import Path
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator, Dict, Any
from httpx import AsyncClient, ASGITransport

# Empêcher le chargement de .env pendant les tests
os.environ["TESTING"] = "true"

# Définir les variables d'environnement avant tout import
os.environ.update({
    "MAX_UPLOAD_SIZE": "10485760",
    "QDRANT_HOST": "localhost",
    "QDRANT_PORT": "6333",
    "ANTHROPIC_API_KEY": "test-key",
    "VOYAGE_API_KEY": "test-key",
    "MAX_TOKENS": "1000",
    "TEMPERATURE": "0.7",
    "MODEL_NAME": "claude-3-sonnet-20240229",
    "CHUNK_SIZE": "500",
    "CHUNK_OVERLAP": "50",
    "MAX_MEMORY_MB": "1024"
})

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Importer app après avoir configuré l'environnement
from app.main import app
from app.core.rag_engine import RAGEngine
from app.api.v1.router import get_rag_engine

@pytest.fixture(scope="session")
def event_loop():
    """Créer une nouvelle boucle d'événements pour la session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

class MockRAGEngine:
    """Mock de RAGEngine pour les tests."""
    
    async def get_document_summary(self, *args, **kwargs):
        return "Test document summary"
    
    def get_collection_stats(self, *args, **kwargs):
        return {
            "name": "documents",
            "vectors_count": 100,
            "dimension": 1024,
            "distance": "cosine"
        }
    
    async def query(self, *args, **kwargs):
        return {
            "answer": "Test response",
            "sources": [{
                "file": "test.pdf",
                "score": 0.9
            }]
        }
    
    async def process_document(self, *args, **kwargs):
        return {
            "document": "test.pdf",
            "chunks_processed": 5,
            "chunks_indexed": 5,
            "processing_time": 0.1
        }

@pytest.fixture
def mock_rag_engine():
    """Fixture pour mocker RAGEngine."""
    return MockRAGEngine()

@pytest.fixture(autouse=True)
def override_get_rag_engine(mock_rag_engine):
    """Override la dépendance get_rag_engine."""
    async def get_mock_engine():
        yield mock_rag_engine
    app.dependency_overrides[get_rag_engine] = get_mock_engine

@pytest_asyncio.fixture
async def async_client():
    """Client HTTP asynchrone pour les tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
    # Nettoyer les overrides après les tests
    app.dependency_overrides.clear()

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock les variables d'environnement pour les tests."""
    env_vars = {
        "MAX_UPLOAD_SIZE": "10485760",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "ANTHROPIC_API_KEY": "test-key",
        "VOYAGE_API_KEY": "test-key",
        "MAX_TOKENS": "1000",
        "TEMPERATURE": "0.7",
        "MODEL_NAME": "claude-3-sonnet-20240229",
        "CHUNK_SIZE": "500",
        "CHUNK_OVERLAP": "50",
        "MAX_MEMORY_MB": "1024",
        "TESTING": "true"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

@pytest.fixture
def mock_path_exists(monkeypatch):
    """Mock pour Path.exists."""
    def mock_exists(self):
        return True
    monkeypatch.setattr(Path, "exists", mock_exists)

@pytest.fixture
def mock_anthropic():
    """Mock pour le client Anthropic."""
    mock = MagicMock()
    mock.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text="Test response")]
    ))
    return mock

@pytest.fixture
def mock_voyage():
    """Mock pour VoyageAI."""
    mock = AsyncMock()
    mock.return_value = [0.1] * 1024  # Retourne un vecteur de test
    return mock

@pytest.fixture
def mock_qdrant_client():
    """Mock pour le client Qdrant."""
    mock = MagicMock()
    
    # Mock pour get_collection
    mock.get_collection = MagicMock(return_value=MagicMock(
        vectors_count=100,
        config=MagicMock(params=MagicMock(
            dimension=1024,
            distance=MagicMock(distance_type="Cosine")
        ))
    ))
    
    # Mock pour search
    async def async_search(*args, **kwargs):
        return [
            MagicMock(
                payload={"text": "Test text", "metadata": {"source": "test.pdf"}},
                score=0.9
            )
        ]
    
    mock.search = AsyncMock(side_effect=async_search)
    
    # Mock pour upsert
    mock.upsert = AsyncMock(return_value=None)
    
    # Mock pour create_collection
    mock.create_collection = MagicMock()
    
    # Mock pour get_collections
    mock.get_collections = MagicMock(return_value=MagicMock(
        collections=[MagicMock(name="test_collection")]
    ))
    
    # Mock pour delete_collection
    mock.delete_collection = MagicMock()
    
    # Mock pour collection_exists
    mock.collection_exists = MagicMock(return_value=True)
    
    # Mock pour recreate_collection
    mock.recreate_collection = MagicMock()
    
    return mock

@pytest.fixture
def test_pdf_content():
    """Contenu de test pour un PDF."""
    return b"%PDF-1.4\nTest PDF content"

@pytest.fixture
def test_env_vars():
    """Variables d'environnement de test."""
    return {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "VOYAGE_API_KEY": os.getenv("VOYAGE_API_KEY"),
        "QDRANT_HOST": os.getenv("QDRANT_HOST", "localhost"),
        "QDRANT_PORT": os.getenv("QDRANT_PORT", "6333"),
        "COLLECTION_NAME": os.getenv("COLLECTION_NAME", "documents"),
        "MAX_TOKENS": os.getenv("MAX_TOKENS", "1000"),
        "TEMPERATURE": os.getenv("TEMPERATURE", "0.7"),
        "MODEL_NAME": os.getenv("MODEL_NAME", "claude-3-sonnet-20240229")
    }

@pytest_asyncio.fixture(autouse=True)
async def mock_dependencies(mock_anthropic, mock_voyage, mock_qdrant_client, mock_rag_engine):
    """Mock toutes les dépendances externes."""
    with patch('anthropic.Client', return_value=mock_anthropic), \
         patch('app.core.vector_store.QdrantClient', return_value=mock_qdrant_client), \
         patch('app.core.vector_store.get_embedding', mock_voyage), \
         patch('app.api.v1.router.RAGEngine', return_value=mock_rag_engine):
        yield
