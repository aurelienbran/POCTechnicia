"""
Module pour le découpage de texte en chunks avec différentes stratégies.
"""

from .base import TextChunker, ChunkingResult
from .simple import SimpleTextChunker
from .semantic import SemanticTextChunker
from .factory import get_text_chunker

__all__ = [
    'TextChunker',
    'ChunkingResult',
    'SimpleTextChunker',
    'SemanticTextChunker',
    'get_text_chunker',
]
