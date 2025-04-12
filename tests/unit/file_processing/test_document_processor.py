"""
Tests unitaires pour la classe DocumentProcessor.
"""
import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from app.core.file_processing.document_processor import DocumentProcessor, DocumentProcessingResult
from app.core.file_processing.conversion.base import DocumentConverter, ConversionResult
from app.core.file_processing.chunking.base import TextChunker, ChunkingResult
from app.core.file_processing.ocr.base import OCRProcessor, OCRResult

@pytest.fixture
def sample_text():
    """Fixture pour un exemple de texte."""
    return """Ceci est un exemple de texte pour les tests unitaires.
    Il comprend plusieurs lignes.
    Le but est de tester la fonctionnalité de chunking.
    Le texte doit être suffisamment long pour être divisé en chunks."""

@pytest.fixture
def mock_converter():
    """Fixture pour un convertisseur de documents simulé."""
    converter = MagicMock(spec=DocumentConverter)
    
    # Configuration du convertisseur mock pour les tests
    async def mock_convert_file(file_path, **kwargs):
        return ConversionResult(
            success=True,
            text_content="Contenu texte simulé pour les tests.",
            metadata={"pages": 5, "title": "Document Test"},
            pages_processed=5,
            total_pages=5
        )
    
    converter.convert_file = AsyncMock(side_effect=mock_convert_file)
    converter.extract_metadata = AsyncMock(return_value={"pages": 5, "title": "Document Test"})
    converter.supported_file_types = AsyncMock(return_value=[".pdf", ".docx", ".txt"])
    
    return converter

@pytest.fixture
def mock_chunker():
    """Fixture pour un chunker de texte simulé."""
    chunker = MagicMock(spec=TextChunker)
    
    # Configuration du chunker mock pour les tests
    async def mock_chunk_text(text, **kwargs):
        chunks = [f"Chunk {i+1}" for i in range(3)]
        return ChunkingResult(
            success=True,
            chunks=chunks,
            metadata={"chunk_count": len(chunks)}
        )
    
    chunker.chunk_text = AsyncMock(side_effect=mock_chunk_text)
    return chunker

@pytest.fixture
def mock_ocr_processor():
    """Fixture pour un processeur OCR simulé."""
    ocr_processor = MagicMock(spec=OCRProcessor)
    
    # Configuration du processeur OCR mock pour les tests
    async def mock_process_document(input_path, **kwargs):
        return OCRResult(
            success=True,
            output_path=f"{input_path}_ocr.pdf",
            pages_processed=5
        )
    
    ocr_processor.process_document = AsyncMock(side_effect=mock_process_document)
    ocr_processor.needs_ocr = AsyncMock(return_value=True)
    
    return ocr_processor

@pytest.fixture
def document_processor(mock_converter, mock_chunker, mock_ocr_processor):
    """Fixture pour un processeur de documents avec des dépendances simulées."""
    return DocumentProcessor(
        converter=mock_converter,
        chunker=mock_chunker,
        ocr_processor=mock_ocr_processor
    )

@pytest.mark.asyncio
async def test_process_document_basic(document_processor, tmp_path):
    """Teste le traitement de base d'un document sans OCR."""
    # Créer un fichier temporaire pour le test
    test_file = tmp_path / "test_doc.pdf"
    test_file.write_text("Contenu test")
    
    # Désactiver l'OCR pour ce test
    result = await document_processor.process_document(
        file_path=str(test_file),
        enable_ocr=False
    )
    
    # Vérifier que le résultat est correct
    assert result.success is True
    assert len(result.chunks) == 3
    assert result.text_content == "Contenu texte simulé pour les tests."
    assert "pages" in result.metadata
    assert result.metadata["pages"] == 5
    
    # Vérifier que le convertisseur a été appelé correctement
    document_processor.converter.convert_file.assert_called_once()
    
    # Vérifier que le chunker a été appelé correctement
    document_processor.chunker.chunk_text.assert_called_once()
    
    # Vérifier que l'OCR n'a pas été appelé
    document_processor.ocr_processor.process_document.assert_not_called()

@pytest.mark.asyncio
async def test_process_document_with_ocr(document_processor, tmp_path):
    """Teste le traitement d'un document avec OCR."""
    # Créer un fichier temporaire pour le test
    test_file = tmp_path / "test_doc_scan.pdf"
    test_file.write_text("Contenu test scanné")
    
    # Configurer le processeur OCR pour indiquer que le document nécessite OCR
    document_processor.ocr_processor.needs_ocr.return_value = True
    
    # Activer l'OCR pour ce test
    result = await document_processor.process_document(
        file_path=str(test_file),
        enable_ocr=True
    )
    
    # Vérifier que le résultat est correct
    assert result.success is True
    assert len(result.chunks) == 3
    assert "ocr_processed" in result.metadata
    assert result.metadata["ocr_processed"] is True
    
    # Vérifier que l'OCR a été appelé correctement
    document_processor.ocr_processor.process_document.assert_called_once()
    
    # Vérifier que le convertisseur a été appelé avec le fichier OCR
    assert document_processor.converter.convert_file.called

@pytest.mark.asyncio
async def test_process_document_without_chunking(document_processor, tmp_path):
    """Teste le traitement d'un document sans chunking."""
    # Créer un fichier temporaire pour le test
    test_file = tmp_path / "test_doc.pdf"
    test_file.write_text("Contenu test")
    
    # Désactiver le chunking pour ce test
    result = await document_processor.process_document(
        file_path=str(test_file),
        enable_ocr=False,
        skip_chunking=True
    )
    
    # Vérifier que le résultat est correct
    assert result.success is True
    assert result.chunks == []
    assert result.text_content == "Contenu texte simulé pour les tests."
    
    # Vérifier que le convertisseur a été appelé correctement
    document_processor.converter.convert_file.assert_called_once()
    
    # Vérifier que le chunker n'a pas été appelé
    document_processor.chunker.chunk_text.assert_not_called()

@pytest.mark.asyncio
async def test_process_document_with_custom_chunk_size(document_processor, tmp_path):
    """Teste le traitement d'un document avec une taille de chunk personnalisée."""
    # Créer un fichier temporaire pour le test
    test_file = tmp_path / "test_doc.pdf"
    test_file.write_text("Contenu test")
    
    # Définir une taille de chunk personnalisée
    custom_chunk_size = 2000
    custom_overlap = 100
    
    # Traiter le document avec les paramètres personnalisés
    result = await document_processor.process_document(
        file_path=str(test_file),
        enable_ocr=False,
        chunk_size=custom_chunk_size,
        chunk_overlap=custom_overlap
    )
    
    # Vérifier que le résultat est correct
    assert result.success is True
    
    # Vérifier que le chunker a été appelé avec les bonnes options
    document_processor.chunker.chunk_text.assert_called_once()
    call_kwargs = document_processor.chunker.chunk_text.call_args[1]
    assert call_kwargs["max_chunk_size"] == custom_chunk_size
    assert call_kwargs["overlap"] == custom_overlap

@pytest.mark.asyncio
async def test_process_document_conversion_error(document_processor, tmp_path):
    """Teste le comportement en cas d'erreur de conversion."""
    # Créer un fichier temporaire pour le test
    test_file = tmp_path / "test_doc.pdf"
    test_file.write_text("Contenu test")
    
    # Configurer le convertisseur pour simuler une erreur
    error_message = "Erreur de conversion simulée"
    document_processor.converter.convert_file.return_value = ConversionResult(
        success=False,
        error_message=error_message,
        text_content="",
        metadata={},
        pages_processed=0,
        total_pages=0
    )
    
    # Traiter le document
    result = await document_processor.process_document(
        file_path=str(test_file),
        enable_ocr=False
    )
    
    # Vérifier que le résultat indique l'échec
    assert result.success is False
    assert result.error_message == error_message
    assert result.chunks == []
    
    # Vérifier que le convertisseur a été appelé
    document_processor.converter.convert_file.assert_called_once()
    
    # Vérifier que le chunker n'a pas été appelé
    document_processor.chunker.chunk_text.assert_not_called()

@pytest.mark.asyncio
async def test_process_document_chunking_error(document_processor, tmp_path):
    """Teste le comportement en cas d'erreur de chunking."""
    # Créer un fichier temporaire pour le test
    test_file = tmp_path / "test_doc.pdf"
    test_file.write_text("Contenu test")
    
    # Configurer le chunker pour simuler une erreur
    error_message = "Erreur de chunking simulée"
    document_processor.chunker.chunk_text.return_value = ChunkingResult(
        success=False,
        chunks=[],
        metadata={},
        error_message=error_message
    )
    
    # Traiter le document
    result = await document_processor.process_document(
        file_path=str(test_file),
        enable_ocr=False
    )
    
    # Vérifier que le résultat indique l'échec
    assert result.success is False
    assert error_message in result.error_message
    assert result.chunks == []
    
    # Vérifier que le convertisseur a été appelé
    document_processor.converter.convert_file.assert_called_once()
    
    # Vérifier que le chunker a été appelé
    document_processor.chunker.chunk_text.assert_called_once()

@pytest.mark.asyncio
async def test_process_document_ocr_error(document_processor, tmp_path):
    """Teste le comportement en cas d'erreur OCR."""
    # Créer un fichier temporaire pour le test
    test_file = tmp_path / "test_doc_scan.pdf"
    test_file.write_text("Contenu test scanné")
    
    # Configurer le processeur OCR pour indiquer que le document nécessite OCR
    document_processor.ocr_processor.needs_ocr.return_value = True
    
    # Configurer le processeur OCR pour simuler une erreur
    error_message = "Erreur OCR simulée"
    document_processor.ocr_processor.process_document.return_value = OCRResult(
        success=False,
        error_message=error_message,
        output_path="",
        pages_processed=0
    )
    
    # Activer l'OCR pour ce test
    result = await document_processor.process_document(
        file_path=str(test_file),
        enable_ocr=True
    )
    
    # Vérifier que le résultat indique l'échec
    assert result.success is False
    assert error_message in result.error_message
    
    # Vérifier que l'OCR a été appelé correctement
    document_processor.ocr_processor.process_document.assert_called_once()
    
    # Vérifier que le convertisseur n'a pas été appelé avec le fichier OCR
    assert document_processor.converter.convert_file.call_count == 0

@pytest.mark.asyncio
async def test_process_document_file_not_found(document_processor):
    """Teste le comportement lorsque le fichier spécifié n'existe pas."""
    # Spécifier un chemin de fichier inexistant
    non_existent_file = "/chemin/vers/fichier_inexistant.pdf"
    
    # Traiter le document
    result = await document_processor.process_document(
        file_path=non_existent_file,
        enable_ocr=False
    )
    
    # Vérifier que le résultat indique l'échec
    assert result.success is False
    assert "fichier" in result.error_message.lower() and "existe" in result.error_message.lower()
    assert result.chunks == []
    
    # Vérifier qu'aucune des dépendances n'a été appelée
    document_processor.converter.convert_file.assert_not_called()
    document_processor.chunker.chunk_text.assert_not_called()
    document_processor.ocr_processor.process_document.assert_not_called()
