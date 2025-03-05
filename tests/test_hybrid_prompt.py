import pytest
import pytest_asyncio
import asyncio
import os
import sys
from pathlib import Path
import numpy as np
from unittest.mock import MagicMock, patch, AsyncMock

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.core.llm_interface import LLMInterface

# Configuration des variables d'environnement pour les tests
os.environ.update({
    "ANTHROPIC_API_KEY": "test-key",
    "VOYAGE_API_KEY": "test-key",
    "MAX_TOKENS": "1000",
    "TEMPERATURE": "0.7",
    "MODEL_NAME": "claude-3-sonnet-20240229",
    "TESTING": "true"
})

@pytest.fixture(autouse=True)
def mock_anthropic_client():
    """Crée un mock frais pour le client Anthropic avant chaque test."""
    with patch('app.core.llm_interface.anthropic.Anthropic') as mock:
        mock.return_value = MagicMock()
        mock.return_value.messages = MagicMock()
        mock.return_value.messages.create = MagicMock()
        yield mock

@pytest.fixture(autouse=True)
def mock_voyage_client():
    """Crée un mock frais pour le client Voyage AI avant chaque test."""
    with patch('app.core.llm_interface.voyageai.Client') as mock:
        mock.return_value = MagicMock()
        mock.return_value.embed = MagicMock(return_value=MockVoyageResponse())
        yield mock

@pytest.fixture(autouse=True)
def mock_settings():
    """Crée un mock pour les settings."""
    with patch('app.core.llm_interface.settings') as mock:
        mock.ANTHROPIC_API_KEY = "test-key"
        mock.VOYAGE_API_KEY = "test-key"
        mock.MAX_TOKENS = 1000
        mock.TEMPERATURE = 0.7
        mock.MODEL_NAME = "claude-3-sonnet-20240229"
        yield mock

@pytest.fixture(autouse=True)
def mock_asyncio():
    """Crée un mock pour asyncio.to_thread."""
    with patch('app.core.llm_interface.asyncio.to_thread', side_effect=mock_to_thread):
        yield

# Créer une classe pour simuler la réponse de Voyage AI
class MockVoyageResponse:
    def __init__(self):
        self.embeddings = [[0.1] * 1024]  # Simuler un embedding de 1024 dimensions

# Créer une classe pour simuler le retour de messages.create
class MockMessage:
    def __init__(self, text):
        self.text = text

class MockResponse:
    def __init__(self, text):
        self.content = [MockMessage(text)]

async def mock_to_thread(func, *args, **kwargs):
    """Simule asyncio.to_thread."""
    return func(*args, **kwargs)

# Définir le marqueur no_mock_dependencies
def pytest_configure(config):
    """Ajouter le marqueur no_mock_dependencies."""
    config.addinivalue_line(
        "markers",
        "no_mock_dependencies: marquer un test pour ne pas utiliser le mock_dependencies"
    )

@pytest.fixture(scope="module")
def llm_modes():
    """Retourne les constantes de mode de LLMInterface."""
    return {
        "TECHNICAL": LLMInterface.MODE_TECHNICAL,
        "CONVERSATIONAL": LLMInterface.MODE_CONVERSATIONAL,
        "HYBRID": LLMInterface.MODE_HYBRID,
        "THRESHOLD": LLMInterface.TECHNICAL_THRESHOLD
    }

@pytest_asyncio.fixture
async def llm_interface():
    """Crée une instance de LLMInterface pour les tests."""
    # Créer une instance avec les mocks
    interface = LLMInterface()
    yield interface

@pytest.fixture
def mock_context_docs_technical():
    """Crée un contexte simulé avec des scores élevés."""
    return [
        {
            "text": "La fonction process_document accepte un fichier PDF et retourne un dictionnaire.",
            "score": 0.85,
            "metadata": {"source": "documentation.pdf"}
        },
        {
            "text": "L'API utilise FastAPI pour gérer les requêtes HTTP.",
            "score": 0.82,
            "metadata": {"source": "api_doc.pdf"}
        }
    ]

@pytest.fixture
def mock_context_docs_low_score():
    """Crée un contexte simulé avec des scores bas."""
    return [
        {
            "text": "Information peu pertinente",
            "score": 0.45,
            "metadata": {"source": "old_doc.pdf"}
        }
    ]

@pytest.fixture
def mock_context_docs_empty():
    """Crée un contexte vide."""
    return []

@pytest.mark.asyncio
async def test_determine_response_mode_technical(llm_interface, mock_context_docs_technical, llm_modes):
    """Teste la détection du mode technique."""
    mode, score = llm_interface._determine_response_mode(
        mock_context_docs_technical,
        "Comment fonctionne la fonction process_document ?"
    )
    assert mode == llm_modes["TECHNICAL"]
    assert score > llm_modes["THRESHOLD"]

@pytest.mark.asyncio
async def test_determine_response_mode_conversational(llm_interface, mock_context_docs_low_score, llm_modes):
    """Teste la détection du mode conversationnel."""
    mode, score = llm_interface._determine_response_mode(
        mock_context_docs_low_score,
        "Peux-tu m'expliquer le concept de RAG ?"
    )
    assert mode == llm_modes["CONVERSATIONAL"]
    assert score < llm_modes["THRESHOLD"]

@pytest.mark.asyncio
async def test_determine_response_mode_hybrid(llm_interface, mock_context_docs_technical, llm_modes):
    """Teste la détection du mode hybride."""
    mode, score = llm_interface._determine_response_mode(
        mock_context_docs_technical,
        "Explique-moi l'architecture globale du système"
    )
    assert mode == llm_modes["HYBRID"]
    assert score > llm_modes["THRESHOLD"]

@pytest.mark.asyncio
async def test_generate_response_technical(llm_interface, mock_context_docs_technical, llm_modes, mock_anthropic_client):
    """Teste la génération de réponse en mode technique."""
    mock_anthropic_client.return_value.messages.create.return_value = MockResponse(
        f"""[Mode utilisé : {llm_modes['TECHNICAL']}]
        La fonction process_document accepte un fichier PDF en entrée et retourne un dictionnaire
        contenant les métadonnées et le texte extrait.
        [Sources : documentation.pdf]"""
    )
    
    response = await llm_interface.generate_response(
        "Comment fonctionne la fonction process_document ?",
        mock_context_docs_technical
    )
    
    assert f"[Mode utilisé : {llm_modes['TECHNICAL']}]" in response
    assert "[Sources :" in response
    mock_anthropic_client.return_value.messages.create.assert_called_once()

@pytest.mark.asyncio
async def test_generate_response_conversational(llm_interface, mock_context_docs_low_score, llm_modes, mock_anthropic_client):
    """Teste la génération de réponse en mode conversationnel."""
    mock_anthropic_client.return_value.messages.create.return_value = MockResponse(
        f"""[Mode utilisé : {llm_modes['CONVERSATIONAL']}]
        Le RAG (Retrieval-Augmented Generation) est une approche qui combine la recherche
        d'informations et la génération de texte."""
    )
    
    response = await llm_interface.generate_response(
        "Explique-moi le concept de RAG",
        mock_context_docs_low_score
    )
    
    assert f"[Mode utilisé : {llm_modes['CONVERSATIONAL']}]" in response
    assert "[Sources :" not in response
    mock_anthropic_client.return_value.messages.create.assert_called_once()

@pytest.mark.asyncio
async def test_generate_response_hybrid(llm_interface, mock_context_docs_technical, llm_modes, mock_anthropic_client):
    """Teste la génération de réponse en mode hybride."""
    mock_anthropic_client.return_value.messages.create.return_value = MockResponse(
        f"""[Mode utilisé : {llm_modes['HYBRID']}]
        D'après la documentation technique, notre système utilise FastAPI pour l'API REST.
        Pour mieux comprendre, on peut voir cela comme un serveur web moderne qui...
        [Sources : api_doc.pdf]"""
    )
    
    response = await llm_interface.generate_response(
        "Explique-moi l'architecture de l'API",
        mock_context_docs_technical
    )
    
    assert f"[Mode utilisé : {llm_modes['HYBRID']}]" in response
    assert "[Sources :" in response
    mock_anthropic_client.return_value.messages.create.assert_called_once()

@pytest.mark.asyncio
async def test_generate_response_no_context(llm_interface, mock_context_docs_empty, llm_modes, mock_anthropic_client):
    """Teste la génération de réponse sans contexte."""
    mock_anthropic_client.return_value.messages.create.return_value = MockResponse(
        f"""[Mode utilisé : {llm_modes['CONVERSATIONAL']}]
        Je n'ai pas trouvé de documents pertinents pour répondre à votre question."""
    )
    
    response = await llm_interface.generate_response(
        "Explique-moi un concept",
        mock_context_docs_empty
    )
    
    assert f"[Mode utilisé : {llm_modes['CONVERSATIONAL']}]" in response
    assert "Je n'ai pas trouvé de documents pertinents" in response
    mock_anthropic_client.return_value.messages.create.assert_called_once()

@pytest.mark.asyncio
async def test_generate_response_retry_on_error(llm_interface, mock_context_docs_technical, mock_anthropic_client):
    """Teste le mécanisme de retry en cas d'erreur."""
    # Simuler 2 erreurs puis un succès
    mock_anthropic_client.return_value.messages.create.side_effect = [
        Exception("Erreur 1"),
        Exception("Erreur 2"),
        MockResponse("Réponse après retry")
    ]
    
    response = await llm_interface.generate_response(
        "Question test",
        mock_context_docs_technical
    )
    
    assert "Réponse après retry" in response
    assert mock_anthropic_client.return_value.messages.create.call_count == 3

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
