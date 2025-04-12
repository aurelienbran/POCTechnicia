"""
Module pour les services OCR avec différents providers.
"""

from .base import OCRProcessor, OCRResult
from .ocrmypdf import OCRmyPDFProcessor
from .factory import get_ocr_processor

__all__ = [
    'OCRProcessor',
    'OCRResult',
    'OCRmyPDFProcessor',
    'get_ocr_processor',
]
