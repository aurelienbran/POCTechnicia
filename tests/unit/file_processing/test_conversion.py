"""
Tests unitaires pour les composants de conversion de documents.
"""
import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from app.core.file_processing.conversion.base import DocumentConverter, ConversionResult
from app.core.file_processing.conversion.standard import StandardDocumentConverter
from app.core.file_processing.conversion.advanced import AdvancedDocumentConverter
from app.core.file_processing.conversion.factory import get_document_converter

@pytest.fixture
def sample_pdf_bytes():
    """Fixture pour un exemple de contenu PDF minimal."""
    # PDF minimaliste valide (en-tête + xref)
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Contents 4 0 R/Parent 2 0 R>>endobj\n4 0 obj<</Length 21>>stream\nBT /F1 12 Tf (Test) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000056 00000 n\n0000000107 00000 n\n0000000183 00000 n\ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n254\n%%EOF"

@pytest.fixture
def sample_docx_bytes():
    """Fixture pour un exemple de contenu DOCX minimal."""
    # Création d'un fichier DOCX minimaliste simulé
    import io
    import zipfile
    
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as zf:
        zf.writestr('word/document.xml', '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Test document</w:t></w:r></w:p></w:body></w:document>')
        zf.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    
    return stream.getvalue()

@pytest.fixture
def sample_text_bytes():
    """Fixture pour un exemple de contenu texte."""
    return b"Ceci est un exemple de texte pour les tests unitaires."

@pytest.fixture
def create_temp_file(tmp_path):
    """Fixture pour créer un fichier temporaire avec un contenu spécifique."""
    def _create_file(content, filename):
        file_path = tmp_path / filename
        with open(file_path, 'wb') as f:
            f.write(content)
        return file_path
    return _create_file

@pytest.mark.asyncio
async def test_standard_converter_pdf(create_temp_file, sample_pdf_bytes):
    """Teste la conversion d'un fichier PDF avec le convertisseur standard."""
    # Créer un fichier PDF temporaire
    pdf_path = create_temp_file(sample_pdf_bytes, "test.pdf")
    
    # Créer le convertisseur standard
    converter = StandardDocumentConverter()
    
    try:
        # Tester la détection du type de fichier
        file_type = await converter.detect_file_type(pdf_path)
        assert file_type.lower() in ["application/pdf", "pdf"]
        
        # Tester la conversion en texte
        result = await converter.convert_file(pdf_path)
        
        # Le PDF minimal contient le mot "Test"
        assert result.success is True
        assert "test" in result.text_content.lower()
        assert result.metadata is not None
        assert "pages" in result.metadata
        
    except ModuleNotFoundError:
        pytest.skip("Modules nécessaires pour la conversion PDF non disponibles")

@pytest.mark.asyncio
async def test_standard_converter_txt(create_temp_file, sample_text_bytes):
    """Teste la conversion d'un fichier texte avec le convertisseur standard."""
    # Créer un fichier texte temporaire
    txt_path = create_temp_file(sample_text_bytes, "test.txt")
    
    # Créer le convertisseur standard
    converter = StandardDocumentConverter()
    
    # Tester la détection du type de fichier
    file_type = await converter.detect_file_type(txt_path)
    assert file_type.lower() in ["text/plain", "txt"]
    
    # Tester la conversion en texte
    result = await converter.convert_file(txt_path)
    
    # Vérifier le résultat
    assert result.success is True
    assert sample_text_bytes.decode('utf-8') in result.text_content
    assert result.metadata is not None

@pytest.mark.asyncio
async def test_standard_converter_docx(create_temp_file, sample_docx_bytes):
    """Teste la conversion d'un fichier DOCX avec le convertisseur standard."""
    # Créer un fichier DOCX temporaire
    docx_path = create_temp_file(sample_docx_bytes, "test.docx")
    
    # Créer le convertisseur standard
    converter = StandardDocumentConverter()
    
    try:
        # Tester la détection du type de fichier
        file_type = await converter.detect_file_type(docx_path)
        assert file_type.lower() in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"]
        
        # Tester la conversion en texte
        result = await converter.convert_file(docx_path)
        
        # Vérifier le résultat
        assert result.success is True
        assert "test document" in result.text_content.lower()
        assert result.metadata is not None
        
    except ModuleNotFoundError:
        pytest.skip("Modules nécessaires pour la conversion DOCX non disponibles")

@pytest.mark.asyncio
async def test_advanced_converter_with_ocr(monkeypatch):
    """Teste le convertisseur avancé avec simulation OCR."""
    # Simuler le module OCR
    class MockOCRProcessor:
        async def process_document(self, input_path, **kwargs):
            from app.core.file_processing.ocr.base import OCRResult
            return OCRResult(
                success=True,
                output_path=f"{input_path}_ocr.pdf",
                pages_processed=3
            )
        
        async def needs_ocr(self, file_path):
            return True
    
    # Simuler le convertisseur standard sous-jacent
    class MockStandardConverter:
        async def convert_file(self, file_path, **kwargs):
            return ConversionResult(
                success=True,
                text_content="Texte extrait après OCR",
                metadata={"pages": 3},
                pages_processed=3,
                total_pages=3
            )
        
        async def detect_file_type(self, file_path):
            return "application/pdf"
        
        async def extract_metadata(self, file_path):
            return {"pages": 3, "author": "Test"}
        
        async def supported_file_types(self):
            return [".pdf", ".docx", ".txt"]
    
    # Monkeypatch pour utiliser nos mocks
    monkeypatch.setattr("app.core.file_processing.ocr.get_ocr_processor", 
                        lambda: AsyncMock(return_value=MockOCRProcessor()))
    
    # Créer le convertisseur avancé avec notre mock
    converter = AdvancedDocumentConverter()
    converter.standard_converter = MockStandardConverter()
    converter.ocr_processor = MockOCRProcessor()
    
    # Tester la conversion avec OCR
    result = await converter.convert_file("test.pdf", enable_ocr=True)
    
    # Vérifier le résultat
    assert result.success is True
    assert "texte extrait après ocr" in result.text_content.lower()
    assert result.metadata is not None
    assert result.metadata.get("ocr_applied") is True

@pytest.mark.asyncio
async def test_converter_factory():
    """Teste la factory de convertisseurs de documents."""
    # Tester l'obtention d'un convertisseur standard
    standard_converter = await get_document_converter("standard")
    assert isinstance(standard_converter, StandardDocumentConverter)
    
    # Tester l'obtention d'un convertisseur avancé
    advanced_converter = await get_document_converter("advanced")
    assert isinstance(advanced_converter, AdvancedDocumentConverter)
    
    # Tester avec un type inconnu (devrait retourner le convertisseur par défaut)
    default_converter = await get_document_converter("unknown_type")
    assert isinstance(default_converter, StandardDocumentConverter)

@pytest.mark.asyncio
async def test_metadata_extraction(create_temp_file, sample_pdf_bytes):
    """Teste l'extraction de métadonnées à partir d'un fichier PDF."""
    # Créer un fichier PDF temporaire
    pdf_path = create_temp_file(sample_pdf_bytes, "test.pdf")
    
    # Créer le convertisseur standard
    converter = StandardDocumentConverter()
    
    try:
        # Tester l'extraction de métadonnées
        metadata = await converter.extract_metadata(pdf_path)
        
        # Vérifier les métadonnées
        assert metadata is not None
        assert isinstance(metadata, dict)
        assert "pages" in metadata
        
    except ModuleNotFoundError:
        pytest.skip("Modules nécessaires pour l'extraction de métadonnées PDF non disponibles")

@pytest.mark.asyncio
async def test_unsupported_file_type(create_temp_file):
    """Teste le comportement avec un type de fichier non supporté."""
    # Créer un fichier d'un type non supporté
    unsupported_path = create_temp_file(b"Contenu binaire", "test.bin")
    
    # Créer le convertisseur standard
    converter = StandardDocumentConverter()
    
    # Tester la conversion
    result = await converter.convert_file(unsupported_path)
    
    # Vérifier que la conversion a échoué
    assert result.success is False
    assert "non supporté" in result.error_message.lower() or "unsupported" in result.error_message.lower()

@pytest.mark.asyncio
async def test_nonexistent_file():
    """Teste le comportement avec un fichier inexistant."""
    # Chemin vers un fichier inexistant
    nonexistent_path = "/chemin/vers/fichier_inexistant.pdf"
    
    # Créer le convertisseur standard
    converter = StandardDocumentConverter()
    
    # Tester la conversion
    result = await converter.convert_file(nonexistent_path)
    
    # Vérifier que la conversion a échoué
    assert result.success is False
    assert "existe" in result.error_message.lower() or "found" in result.error_message.lower()

@pytest.mark.asyncio
async def test_batch_conversion(create_temp_file, sample_pdf_bytes, sample_text_bytes):
    """Teste la conversion par lots de plusieurs fichiers."""
    # Créer plusieurs fichiers temporaires
    pdf_path = create_temp_file(sample_pdf_bytes, "test1.pdf")
    txt_path = create_temp_file(sample_text_bytes, "test2.txt")
    
    # Créer le convertisseur standard
    converter = StandardDocumentConverter()
    
    # Liste des fichiers à convertir
    files = [pdf_path, txt_path]
    
    # Convertir chaque fichier
    results = []
    for file_path in files:
        try:
            result = await converter.convert_file(file_path)
            results.append((file_path, result))
        except Exception as e:
            results.append((file_path, None))
    
    # Vérifier les résultats
    assert len(results) == len(files)
    
    # Vérifier que chaque conversion a réussi
    for file_path, result in results:
        if result:
            assert result.success is True
            assert result.text_content is not None

@pytest.mark.asyncio
async def test_extract_tables_option(create_temp_file, sample_pdf_bytes):
    """Teste l'option d'extraction de tableaux."""
    # Créer un fichier PDF temporaire
    pdf_path = create_temp_file(sample_pdf_bytes, "test_tables.pdf")
    
    # Créer le convertisseur avancé
    converter = AdvancedDocumentConverter()
    
    try:
        # Simuler un module d'extraction de tableaux
        with patch.object(converter, '_extract_tables_from_pdf', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = [{"data": [["Col1", "Col2"], ["Val1", "Val2"]]}]
            
            # Tester la conversion avec extraction de tableaux
            result = await converter.convert_file(pdf_path, extract_tables=True)
            
            # Vérifier que la fonction d'extraction a été appelée
            mock_extract.assert_called_once()
            
            # Vérifier que les tableaux sont dans les métadonnées
            assert result.success is True
            assert "tables" in result.metadata
            assert len(result.metadata["tables"]) == 1
            
    except ModuleNotFoundError:
        pytest.skip("Modules nécessaires pour l'extraction de tableaux non disponibles")

@pytest.mark.asyncio
async def test_large_file_handling(monkeypatch):
    """Teste le traitement de fichiers volumineux avec une approche par lots."""
    # Simuler un grand fichier PDF de 30 Mo
    class MockLargeFile:
        def __init__(self, path):
            self.path = path
            self.size = 30 * 1024 * 1024  # 30 Mo
        
        def stat(self):
            return MagicMock(st_size=self.size)
    
    # Monkeypatch pour Path
    original_path = Path
    def mock_path_init(path_obj, *args, **kwargs):
        result = original_path(*args, **kwargs)
        if str(result).endswith("large.pdf"):
            return MockLargeFile(result)
        return result
    
    monkeypatch.setattr("pathlib.Path", mock_path_init)
    
    # Simuler le convertisseur standard
    class MockStandardConverter:
        async def convert_file(self, file_path, batch_size=None, **kwargs):
            # Simuler une approche par lots pour les grands fichiers
            if batch_size:
                # Simuler un traitement par lots
                text_parts = []
                for i in range(10):  # Simuler 10 lots
                    text_parts.append(f"Contenu du lot {i+1}")
                
                return ConversionResult(
                    success=True,
                    text_content="\n".join(text_parts),
                    metadata={"pages": 100, "processed_in_batches": True, "batch_count": 10},
                    pages_processed=100,
                    total_pages=100
                )
            else:
                # Simuler une erreur de timeout pour un grand fichier sans approche par lots
                return ConversionResult(
                    success=False,
                    error_message="Timeout lors de la conversion du fichier (>28 Mo)",
                    text_content="",
                    metadata={},
                    pages_processed=0,
                    total_pages=100
                )
        
        async def detect_file_type(self, file_path):
            return "application/pdf"
    
    # Créer le convertisseur avancé avec notre mock
    converter = AdvancedDocumentConverter()
    converter.standard_converter = MockStandardConverter()
    
    # Tester la conversion sans approche par lots (devrait échouer avec timeout)
    result_without_batch = await converter.convert_file("large.pdf", enable_ocr=False)
    assert result_without_batch.success is False
    assert "timeout" in result_without_batch.error_message.lower()
    
    # Tester la conversion avec approche par lots
    result_with_batch = await converter.convert_file("large.pdf", enable_ocr=False, batch_size=10)
    assert result_with_batch.success is True
    assert "lot" in result_with_batch.text_content.lower()
    assert result_with_batch.metadata.get("processed_in_batches") is True
