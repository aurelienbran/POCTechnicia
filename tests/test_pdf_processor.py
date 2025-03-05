"""Tests pour le module PDFProcessor."""
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
import os
from datetime import datetime

from app.core.pdf_processor import PDFProcessor

# Chemin vers le fichier PDF de test
TEST_PDF_PATH = Path("D:/Projets/POC TECHNICIA/tests/performance/test_files/el.pdf")

@pytest.fixture
def temp_dir():
    """Crée un répertoire temporaire pour les tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def processor(temp_dir):
    """Crée une instance de PDFProcessor pour les tests."""
    return PDFProcessor(
        chunk_size=100,
        overlap=20,
        temp_dir=temp_dir,
        extract_images=False
    )

@pytest.mark.asyncio
async def test_init():
    """Teste l'initialisation du processeur."""
    proc = PDFProcessor()
    assert proc.chunk_size == 512
    assert proc.overlap == 150
    assert proc.extract_images is False
    assert proc.temp_dir.exists()
    await proc.close()

@pytest.mark.asyncio
async def test_get_metadata(processor):
    """Teste l'extraction des métadonnées."""
    metadata = await processor.get_metadata(TEST_PDF_PATH)
    assert isinstance(metadata, dict)
    assert "filename" in metadata
    assert "processed_at" in metadata
    assert metadata["filename"] == "el.pdf"
    assert "page_count" in metadata
    assert metadata["page_count"] > 0

@pytest.mark.asyncio
async def test_extract_section_title():
    """Teste l'extraction des titres de section."""
    processor = PDFProcessor()
    
    # Test avec différents formats de titre
    assert processor._extract_section_title("1.2.3. Mon Titre") == "Mon Titre"
    assert "Introduction" in processor._extract_section_title("Introduction: Mon texte")
    assert processor._extract_section_title("Texte sans titre\nContenu") == "Texte sans titre"
    
    # Test avec texte vide
    assert processor._extract_section_title("") == "Section sans titre"
    
    await processor.close()

@pytest.mark.asyncio
async def test_split_into_chunks():
    """Teste le découpage en chunks."""
    processor = PDFProcessor(chunk_size=50, overlap=10)
    
    # Créer un texte de test
    text = "Ceci est un texte de test. " * 10
    
    chunks = processor._split_into_chunks_with_overlap(text)
    
    assert len(chunks) > 1
    assert all("content" in chunk for chunk in chunks)
    assert all("tokens" in chunk for chunk in chunks)
    
    # Vérifier le chevauchement
    if len(chunks) > 1:
        chunk1 = chunks[0]["content"]
        chunk2 = chunks[1]["content"]
        # Le début du second chunk devrait être dans la fin du premier
        assert any(chunk2.startswith(chunk1[i:]) for i in range(len(chunk1)))
    
    await processor.close()

@pytest.mark.asyncio
async def test_process_pdf(processor):
    """Teste le traitement complet d'un PDF."""
    chunks = []
    async for chunk in processor.process_pdf(TEST_PDF_PATH):
        chunks.append(chunk)
        
        # Vérifier la structure des chunks
        assert "content" in chunk
        assert "tokens" in chunk
        assert "page" in chunk
        assert "total_pages" in chunk
        assert "section" in chunk
        assert "source" in chunk
        assert "chunk_id" in chunk
        assert "metadata" in chunk
    
    # On devrait avoir au moins un chunk
    assert len(chunks) > 0
    print(f"Nombre de chunks générés: {len(chunks)}")

@pytest.mark.asyncio
async def test_process_pdf_with_images(temp_dir):
    """Teste le traitement d'un PDF avec images activées."""
    processor = PDFProcessor(
        chunk_size=100,
        overlap=20,
        temp_dir=temp_dir,
        extract_images=True
    )
    
    chunks = []
    async for chunk in processor.process_pdf(TEST_PDF_PATH):
        chunks.append(chunk)
        assert "has_images" in chunk
        assert "image_count" in chunk
    
    # Vérifier si des images ont été extraites
    print(f"Nombre d'images trouvées: {chunks[0]['image_count'] if chunks else 0}")
    await processor.close()

@pytest.mark.asyncio
async def test_error_handling(processor):
    """Teste la gestion des erreurs."""
    # Test avec un fichier inexistant
    with pytest.raises(FileNotFoundError):
        async for _ in processor.process_pdf(Path("fichier_inexistant.pdf")):
            pass
    
    # Test avec un fichier non-PDF
    invalid_file = Path(tempfile.mktemp())
    invalid_file.write_text("Not a PDF")
    
    with pytest.raises(Exception):
        async for _ in processor.process_pdf(invalid_file):
            pass
    
    invalid_file.unlink()

@pytest.mark.asyncio
async def test_cleanup(temp_dir):
    """Teste le nettoyage des ressources."""
    processor = PDFProcessor(temp_dir=temp_dir, extract_images=True)
    
    # Créer quelques fichiers temporaires
    test_file = temp_dir / "test.txt"
    test_file.write_text("test")
    
    test_dir = temp_dir / "test_dir"
    test_dir.mkdir()
    (test_dir / "test.txt").write_text("test")
    
    # Nettoyer
    await processor.close()
    
    # Vérifier que les fichiers ont été supprimés
    assert not test_file.exists()
    assert not test_dir.exists()

def test_logging(caplog):
    """Teste le logging."""
    with caplog.at_level("INFO"):
        processor = PDFProcessor()
        assert "PDFProcessor initialisé" in caplog.text
        
        # Nettoyer
        asyncio.run(processor.close())
