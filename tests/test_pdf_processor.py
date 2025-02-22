import pytest
import asyncio
from pathlib import Path
from app.core.pdf_processor import PDFProcessor
import tempfile
import fitz  # PyMuPDF
import os

# Création d'un PDF de test
def create_test_pdf(path: Path, pages: int = 3) -> None:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        text = f"Page {i + 1}\nCeci est un test de contenu pour la page {i + 1}.\n"
        text += "Lorem ipsum " * 50  # Ajoute du contenu substantiel
        page.insert_text((50, 50), text)
    doc.save(str(path))  # Convertir Path en str pour fitz
    doc.close()

@pytest.fixture(scope="function")
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)

@pytest.fixture(scope="function")
def test_pdf(temp_dir):
    pdf_path = temp_dir / "test.pdf"
    create_test_pdf(pdf_path)
    yield pdf_path
    try:
        if pdf_path.exists():
            pdf_path.unlink()
    except Exception as e:
        print(f"Erreur lors du nettoyage du fichier test: {e}")

@pytest.fixture(scope="function")
def pdf_processor(temp_dir):
    return PDFProcessor(temp_dir=temp_dir)

@pytest.mark.asyncio
async def test_pdf_processor_initialization(pdf_processor, temp_dir):
    assert pdf_processor.temp_dir == temp_dir
    assert pdf_processor.temp_dir.exists()

@pytest.mark.asyncio
async def test_process_pdf_basic(pdf_processor, test_pdf):
    chunks = []
    async for chunk in pdf_processor.process_pdf(test_pdf):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert all(isinstance(chunk, str) for chunk in chunks)
    assert any("Page 1" in chunk for chunk in chunks)

@pytest.mark.asyncio
async def test_pdf_metadata(pdf_processor, test_pdf):
    metadata = await pdf_processor.get_metadata(test_pdf)
    assert isinstance(metadata, dict)
    assert "page_count" in metadata
    assert metadata["page_count"] == 3
    assert "file_size" in metadata
    assert metadata["file_size"] > 0

@pytest.mark.asyncio
async def test_large_pdf_handling(pdf_processor, temp_dir):
    # Créer un PDF plus volumineux pour tester la gestion de la mémoire
    large_pdf_path = temp_dir / "large.pdf"
    create_test_pdf(large_pdf_path, pages=20)
    
    try:
        chunks = []
        async for chunk in pdf_processor.process_pdf(large_pdf_path):
            chunks.append(chunk)
            # Vérifier que chaque chunk ne dépasse pas une taille raisonnable
            assert len(chunk) <= 5000  # Taille maximale raisonnable pour un chunk
        
        assert len(chunks) > 0
    finally:
        if large_pdf_path.exists():
            large_pdf_path.unlink()

@pytest.mark.asyncio
async def test_invalid_pdf_path(pdf_processor):
    with pytest.raises(FileNotFoundError):
        async for _ in pdf_processor.process_pdf(Path("nonexistent.pdf")):
            pass

@pytest.mark.asyncio
async def test_cleanup(pdf_processor, test_pdf):
    async for _ in pdf_processor.process_pdf(test_pdf):
        pass
    # Vérifier que les fichiers temporaires sont nettoyés
    temp_files = list(pdf_processor.temp_dir.glob("*"))
    assert len(temp_files) == 0

# Test de performance basique
@pytest.mark.asyncio
async def test_memory_usage(pdf_processor, temp_dir):
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # En MB
    
    # Créer un PDF plus grand
    large_pdf_path = temp_dir / "memory_test.pdf"
    create_test_pdf(large_pdf_path, pages=30)
    
    try:
        chunks = []
        async for chunk in pdf_processor.process_pdf(large_pdf_path):
            chunks.append(chunk)
            current_memory = process.memory_info().rss / 1024 / 1024
            # Vérifier que l'utilisation de la mémoire ne dépasse pas 1GB
            assert current_memory - initial_memory < 1024
    finally:
        if large_pdf_path.exists():
            large_pdf_path.unlink()
