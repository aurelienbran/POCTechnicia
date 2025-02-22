import pytest
from app.core.rag_engine import RAGEngine
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import asyncio
from typing import AsyncGenerator, List

class MockAnthropicResponse:
    def __init__(self, text):
        self.content = [MagicMock(text=text)]

class AsyncIterator:
    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return self.items.pop(0)
        except IndexError:
            raise StopAsyncIteration

@pytest.fixture
def mock_vector_store():
    mock = MagicMock()
    mock.similarity_search = AsyncMock(return_value=[
        {
            "id": "1",
            "score": 0.9,
            "metadata": {
                "source": "test.pdf",
                "text": "Sample text 1"
            }
        }
    ])
    mock.add_texts = AsyncMock(return_value=["1", "2", "3"])
    return mock

@pytest.fixture
def mock_llm_interface():
    mock = MagicMock()
    mock.generate_response = AsyncMock(return_value="Test response")
    mock.generate_follow_up_questions = AsyncMock(return_value=["Q1?", "Q2?", "Q3?"])
    mock.summarize_document = AsyncMock(return_value="Test summary")
    return mock

@pytest.fixture
def mock_pdf_processor():
    mock = MagicMock()
    mock.process_pdf.return_value = AsyncIterator(["Chunk 1", "Chunk 2"])
    mock.extract_metadata = AsyncMock(return_value={"title": "Test Doc", "page_count": 2})
    return mock

@pytest.fixture
def rag_engine(mock_vector_store, mock_llm_interface, mock_pdf_processor):
    with patch('app.core.rag_engine.VectorStore', return_value=mock_vector_store), \
         patch('app.core.rag_engine.LLMInterface', return_value=mock_llm_interface), \
         patch('app.core.rag_engine.PDFProcessor', return_value=mock_pdf_processor):
        engine = RAGEngine()
        engine.vector_store = mock_vector_store
        engine.llm_interface = mock_llm_interface
        engine.pdf_processor = mock_pdf_processor
        return engine

@pytest.mark.asyncio
async def test_process_document(rag_engine):
    file_path = Path("test.pdf")
    result = await rag_engine.process_document(file_path)
    
    assert isinstance(result, dict)
    assert "chunks_processed" in result
    assert "chunks_indexed" in result
    assert result["chunks_processed"] == 2
    rag_engine.pdf_processor.process_pdf.assert_called_once()
    rag_engine.vector_store.add_texts.assert_called_once()

@pytest.mark.asyncio
async def test_query(rag_engine):
    question = "Test question?"
    result = await rag_engine.query(question)
    
    assert isinstance(result, dict)
    assert "question" in result
    assert "answer" in result
    assert "follow_up_questions" in result
    assert "sources" in result
    
    rag_engine.vector_store.similarity_search.assert_called_once()
    rag_engine.llm_interface.generate_response.assert_called_once()
    rag_engine.llm_interface.generate_follow_up_questions.assert_called_once()

@pytest.mark.asyncio
async def test_query_with_filter(rag_engine):
    question = "Test question?"
    filter_dict = {"metadata_field": {"$eq": "test_value"}}
    
    result = await rag_engine.query(question, filter=filter_dict)
    
    assert isinstance(result, dict)
    rag_engine.vector_store.similarity_search.assert_called_once_with(
        query=question,
        k=4,
        filter=filter_dict
    )

@pytest.mark.asyncio
async def test_get_document_summary(rag_engine):
    file_path = Path("test.pdf")
    summary = await rag_engine.get_document_summary(file_path)
    
    assert isinstance(summary, str)
    rag_engine.pdf_processor.process_pdf.assert_called_once()
    rag_engine.llm_interface.summarize_document.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling_process_document(rag_engine):
    rag_engine.pdf_processor.process_pdf.side_effect = Exception("Test error")
    
    with pytest.raises(Exception):
        await rag_engine.process_document(Path("test.pdf"))

@pytest.mark.asyncio
async def test_error_handling_query(rag_engine):
    rag_engine.vector_store.similarity_search.side_effect = Exception("Test error")
    
    with pytest.raises(Exception):
        await rag_engine.query("Test question?")

def test_get_collection_stats(rag_engine):
    rag_engine.vector_store.get_collection_info.return_value = {
        "name": "test",
        "vectors_count": 100
    }
    
    stats = rag_engine.get_collection_stats()
    
    assert isinstance(stats, dict)
    assert "name" in stats
    assert "vectors_count" in stats
    rag_engine.vector_store.get_collection_info.assert_called_once()
