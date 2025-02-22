import pytest
from app.core.llm_interface import LLMInterface
from unittest.mock import patch, MagicMock
import anthropic

class MockAnthropicResponse:
    def __init__(self, text):
        self.content = [MagicMock(text=text)]

@pytest.fixture
def mock_anthropic():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MockAnthropicResponse("Test response")
    with patch('anthropic.Client', return_value=mock_client):
        yield mock_client

@pytest.fixture
def llm_interface(mock_anthropic):
    return LLMInterface()

@pytest.fixture
def sample_context_docs():
    return [
        {
            "metadata": {"text": "Sample text 1"},
            "score": 0.9
        },
        {
            "metadata": {"text": "Sample text 2"},
            "score": 0.8
        }
    ]

@pytest.mark.asyncio
async def test_generate_response(llm_interface, sample_context_docs):
    query = "Test question?"
    response = await llm_interface.generate_response(query, sample_context_docs)
    
    assert isinstance(response, str)
    assert len(response) > 0
    llm_interface.client.messages.create.assert_called_once()

@pytest.mark.asyncio
async def test_generate_response_no_context(llm_interface):
    query = "Test question?"
    response = await llm_interface.generate_response(query, [])
    
    assert isinstance(response, str)
    assert "pas trouvé de contexte pertinent" in response

@pytest.mark.asyncio
async def test_generate_response_low_scores(llm_interface):
    query = "Test question?"
    context_docs = [
        {
            "metadata": {"text": "Sample text"},
            "score": 0.5  # Score en dessous du seuil
        }
    ]
    
    response = await llm_interface.generate_response(query, context_docs)
    assert "pas trouvé de contexte pertinent" in response

@pytest.mark.asyncio
async def test_generate_follow_up_questions(llm_interface, sample_context_docs):
    query = "Test question?"
    previous_response = "Test response"
    
    questions = await llm_interface.generate_follow_up_questions(
        query,
        sample_context_docs,
        previous_response
    )
    
    assert isinstance(questions, list)
    assert len(questions) <= 3  # Nombre maximum de questions par défaut

@pytest.mark.asyncio
async def test_summarize_document(llm_interface):
    document_text = "This is a test document that needs to be summarized."
    summary = await llm_interface.summarize_document(document_text)
    
    assert isinstance(summary, str)
    assert len(summary) > 0
    llm_interface.client.messages.create.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(llm_interface):
    # Simuler une erreur de l'API
    llm_interface.client.messages.create.side_effect = Exception("API Error")
    
    with pytest.raises(Exception):
        await llm_interface.generate_response("Test question?", [])

@pytest.mark.asyncio
async def test_custom_parameters(llm_interface, sample_context_docs):
    query = "Test question?"
    response = await llm_interface.generate_response(
        query,
        sample_context_docs,
        max_tokens=500,
        temperature=0.5
    )
    
    assert isinstance(response, str)
    # Vérifier que les paramètres personnalisés ont été utilisés
    call_kwargs = llm_interface.client.messages.create.call_args[1]
    assert call_kwargs["max_tokens"] == 500
    assert call_kwargs["temperature"] == 0.5
