"""
Module d'orchestration intelligente des processeurs de traitement de documents
==========================================================================

Ce package fournit les outils nécessaires pour orchestrer intelligemment 
l'exécution des différents processeurs spécialisés et OCR.

Il permet notamment:
- La sélection dynamique des processeurs en fonction du contenu
- L'exécution parallèle des traitements pour optimiser les performances
- La fusion intelligente des résultats des différents processeurs
- L'adaptation des stratégies en fonction des résultats intermédiaires

Auteur: Équipe Technicia
Date: Avril 2025
"""

from .orchestrator import ProcessingOrchestrator
from .strategy_selector import ProcessingStrategySelector
from .result_merger import ResultMerger
from .parallel_executor import ParallelExecutor

__all__ = [
    'ProcessingOrchestrator',
    'ProcessingStrategySelector',
    'ResultMerger',
    'ParallelExecutor'
]
