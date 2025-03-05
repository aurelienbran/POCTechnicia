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
    """Configure les variables d'environnement pour les tests."""
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
    """Mock Path.exists pour simuler l'existence de fichiers."""
    def mock_exists(*args, **kwargs):
        return True
    monkeypatch.setattr(Path, "exists", mock_exists)

@pytest.fixture
def mock_anthropic():
    """Mock pour le client Anthropic."""
    with patch('app.core.llm_interface.anthropic.Anthropic') as mock:
        mock.return_value.messages.create = AsyncMock()
        yield mock

@pytest.fixture
def mock_voyage():
    """Mock pour VoyageAI."""
    with patch('app.core.llm_interface.voyageai.Client') as mock:
        yield mock

@pytest.fixture
def mock_qdrant_client():
    """Mock pour le client Qdrant."""
    with patch('app.core.vector_store.QdrantClient') as mock:
        # Mock pour la méthode get_collections
        mock.return_value.get_collections = MagicMock(return_value=[
            {"name": "documents"}
        ])
        
        # Mock pour la méthode get_collection
        mock.return_value.get_collection = MagicMock(return_value={
            "name": "documents",
            "vectors_count": 100,
            "dimension": 1024,
            "distance": "cosine"
        })
        
        # Mock pour la méthode recreate_collection
        mock.return_value.recreate_collection = AsyncMock()
        
        # Mock pour la méthode upsert
        mock.return_value.upsert = AsyncMock()
        
        # Mock pour la méthode search
        mock.return_value.search = AsyncMock(return_value=[{
            "id": "1",
            "score": 0.9,
            "payload": {
                "text": "Test text",
                "metadata": {"source": "test.pdf"}
            }
        }])
        
        # Mock pour la méthode count
        mock.return_value.count = AsyncMock(return_value={"count": 100})
        
        # Mock pour la méthode scroll
        mock.return_value.scroll = AsyncMock(return_value=({
            "id": "1",
            "payload": {
                "text": "Test text",
                "metadata": {"source": "test.pdf"}
            }
        } for _ in range(5)))
        
        yield mock

@pytest.fixture
def test_pdf_content():
    """Contenu de test pour un PDF."""
    return "Test PDF content"

@pytest.fixture
def test_env_vars():
    """Variables d'environnement de test."""
    return {
        "MAX_UPLOAD_SIZE": 10485760,
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": 6333,
        "ANTHROPIC_API_KEY": "test-key",
        "VOYAGE_API_KEY": "test-key",
        "MAX_TOKENS": 1000,
        "TEMPERATURE": 0.7,
        "MODEL_NAME": "claude-3-sonnet-20240229"
    }

@pytest_asyncio.fixture(autouse=True)
async def mock_dependencies(request, mock_anthropic, mock_voyage, mock_qdrant_client, mock_rag_engine):
    """Mock toutes les dépendances externes."""
    # Ne pas appliquer les mocks si le marqueur no_mock_dependencies est présent
    if request.node.get_closest_marker('no_mock_dependencies'):
        yield
        return
        
    # Sinon, appliquer les mocks normalement
    patches = [
        patch('app.core.llm_interface.anthropic.Anthropic', mock_anthropic),
        patch('app.core.llm_interface.voyageai.Client', mock_voyage),
        patch('app.core.vector_store.QdrantClient', mock_qdrant_client),
        patch('app.core.rag_engine.RAGEngine', mock_rag_engine)
    ]
    
    for p in patches:
        p.start()
    
    yield
    
    for p in patches:
        p.stop()
