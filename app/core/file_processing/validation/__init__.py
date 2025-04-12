"""
Module de validation et d'amélioration itérative pour le traitement des documents
===============================================================================

Ce package fournit des outils pour évaluer la qualité des résultats OCR,
détecter les extractions à faible confiance, gérer le retraitement automatique
des documents problématiques et mettre en place un système de validation par échantillonnage.

Composants:
    - LowConfidenceDetector: Détection des extractions à faible confiance
    - ReprocessingWorkflow: Gestion du flux de retraitement itératif
    - SamplingValidator: Validation par échantillonnage et reporting

Auteur: Équipe Technicia
Date: Avril 2025
"""

from .low_confidence_detector import LowConfidenceDetector, ContentIssue, DocumentValidationIssues
from .reprocessing_workflow import ReprocessingWorkflow, ProcessingAttempt, ReprocessingJob
from .sampling_validator import SamplingValidator, ValidationSample, ValidationResult

__all__ = [
    'LowConfidenceDetector',
    'ContentIssue',
    'DocumentValidationIssues',
    'ReprocessingWorkflow',
    'ProcessingAttempt',
    'ReprocessingJob',
    'SamplingValidator',
    'ValidationSample',
    'ValidationResult'
]
