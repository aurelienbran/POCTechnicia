"""
Module contenant les processeurs spécialisés pour l'extraction de contenus techniques.

Ce package fournit des processeurs spécialisés pour différents types de contenus techniques:
- Extracteur de tableaux
- Processeur de formules techniques
- Analyseur de schémas techniques

Ces processeurs sont conçus pour être utilisés en complément des processeurs OCR standards
afin d'améliorer l'extraction et l'analyse de contenus techniques spécifiques.
"""

from .base import SpecializedProcessor, SpecializedProcessingResult
from .table_extractor import TableExtractor
from .formula_processor import FormulaProcessor
from .schema_analyzer import SchemaAnalyzer

__all__ = [
    'SpecializedProcessor',
    'SpecializedProcessingResult',
    'TableExtractor',
    'FormulaProcessor',
    'SchemaAnalyzer',
]
