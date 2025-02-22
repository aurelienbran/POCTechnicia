"""Tests des endpoints de l'API."""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import json
from datetime import datetime
import pytest_asyncio

from app.main import app
from app.core.rag_engine import RAGEngine
from app.api.v1.router import get_rag_engine
from tests.conftest import MockRAGEngine

@pytest_asyncio.fixture
async def async_client():
    """Client HTTP asynchrone pour les tests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_health_check(async_client):
    """Test de la route /health."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"

@pytest.mark.asyncio
async def test_upload_document(async_client):
    """Test de l'upload d'un document PDF."""
    test_file_content = b"%PDF-1.4\nTest PDF content"
    files = {
        "file": ("test.pdf", test_file_content, "application/pdf")
    }
    
    response = await async_client.post("/api/v1/documents", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert "document" in data
    assert "chunks_processed" in data
    assert "chunks_indexed" in data
    assert "processing_time" in data

@pytest.mark.asyncio
async def test_upload_invalid_document(async_client):
    """Test de l'upload d'un document non-PDF."""
    test_file_content = b"Not a PDF"
    files = {
        "file": ("test.txt", test_file_content, "text/plain")
    }
    
    response = await async_client.post("/api/v1/documents", files=files)
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]

@pytest.mark.asyncio
async def test_query_documents(async_client):
    """Test de la route de requête."""
    question = "Test question?"
    response = await async_client.post(
        "/api/v1/query",
        json={
            "question": question,
            "k": 4
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == question
    assert data["answer"] == "Test response"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["file"] == "test.pdf"
    assert data["sources"][0]["score"] == 0.9
    assert "processing_time" in data

@pytest.mark.asyncio
async def test_query_with_filter(async_client):
    """Test de la requête avec filtre."""
    question = "Test question?"
    filter_dict = {"metadata_field": {"$eq": "test_value"}}
    
    response = await async_client.post(
        "/api/v1/query",
        json={
            "question": question,
            "k": 4,
            "filter": filter_dict
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == question
    assert data["answer"] == "Test response"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["file"] == "test.pdf"
    assert data["sources"][0]["score"] == 0.9

@pytest.mark.asyncio
async def test_get_document_summary(async_client, mock_path_exists):
    """Test de la génération de résumé."""
    # Créer un fichier temporaire pour le test
    test_file = "test.pdf"
    
    response = await async_client.get(f"/api/v1/documents/{test_file}/summary")
    assert response.status_code == 200
    assert isinstance(response.json(), str)
    assert response.json() == "Test document summary"

@pytest.mark.asyncio
async def test_get_document_summary_not_found(async_client):
    """Test de la génération de résumé pour un document inexistant."""
    response = await async_client.get("/api/v1/documents/nonexistent.pdf/summary")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_stats(async_client):
    """Test de la récupération des statistiques."""
    response = await async_client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "documents"
    assert data["vectors_count"] == 100
    assert data["dimension"] == 1024
    assert data["distance"] == "cosine"

@pytest.mark.asyncio
async def test_error_handling(async_client, override_get_rag_engine):
    """Test de la gestion des erreurs."""
    # Créer un nouveau mock qui lève une exception
    class ErrorMockRAGEngine(MockRAGEngine):
        async def query(self, *args, **kwargs):
            raise Exception("Test error")
    
    # Remplacer le mock existant
    async def get_error_mock():
        yield ErrorMockRAGEngine()
    
    app.dependency_overrides[get_rag_engine] = get_error_mock
    
    response = await async_client.post(
        "/api/v1/query",
        json={
            "question": "Test question?",
            "k": 4
        }
    )
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Test error" in data["detail"]
