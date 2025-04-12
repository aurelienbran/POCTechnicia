"""
Package pour le traitement de fichiers avec différents services.
Fournit une interface unifiée pour le traitement de documents 
avec la possibilité de choisir différents providers.
"""

from .ocr import OCRProcessor, get_ocr_processor
from .chunking import TextChunker, get_text_chunker
from .conversion import DocumentConverter, get_document_converter

__all__ = [
    'OCRProcessor',
    'get_ocr_processor',
    'TextChunker',
    'get_text_chunker',
    'DocumentConverter',
    'get_document_converter',
]
