"""
Tests d'intégration pour le pipeline d'orchestration des processeurs
====================================================================

Ce module contient les tests d'intégration pour vérifier le bon fonctionnement
de l'orchestrateur central et ses interactions avec les différents composants
(sélecteur de stratégie, fusionneur de résultats, exécuteur parallèle).

Ces tests assurent que le système d'orchestration complet fonctionne correctement
dans des scénarios réels, avec différents types de documents et de configurations.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
import logging
from typing import List, Dict, Any, Optional

from app.core.file_processing.orchestration.orchestrator import ProcessingOrchestrator
from app.core.file_processing.orchestration.strategy_selector import ProcessingStrategySelector
from app.core.file_processing.orchestration.result_merger import ResultMerger
from app.core.file_processing.orchestration.parallel_executor import ParallelExecutor
from app.core.file_processing.specialized_processors.table_extractor import TableExtractor
from app.core.file_processing.specialized_processors.schema_analyzer import SchemaAnalyzer
from app.core.file_processing.specialized_processors.formula_processor import FormulaProcessor

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Répertoire de test pour les fichiers d'exemple
TEST_FILES_DIR = Path(__file__).parent.parent.parent.parent / "test_files"
if not TEST_FILES_DIR.exists():
    TEST_FILES_DIR.mkdir(parents=True)


@pytest.fixture
async def orchestrator():
    """
    Fixture qui crée un orchestrateur de traitement pour les tests.
    
    Returns:
        Une instance configurée de ProcessingOrchestrator
    """
    # Configuration de base pour les tests
    config = {
        "max_parallel": 2,
        "strategy_weights": {
            "has_tables": 1.0,
            "has_schemas": 0.8,
            "has_formulas": 0.9,
            "text_density": 0.7,
            "image_complexity": 0.6
        },
        "result_priority": {
            "table_extractor": 8,
            "schema_analyzer": 7,
            "formula_processor": 6,
            "default": 5
        },
        "use_ai_orchestrator": False  # Désactiver pour les tests
    }
    
    # Créer et initialiser l'orchestrateur
    orchestrator = ProcessingOrchestrator(config)
    await orchestrator.initialize()
    
    # Préparer des processeurs spécialisés pour les tests
    orchestrator.specialized_processors = [
        TableExtractor(),
        SchemaAnalyzer(),
        FormulaProcessor()
    ]
    
    yield orchestrator


@pytest.fixture
def test_document():
    """
    Fixture qui crée un document de test temporaire.
    
    Returns:
        Chemin vers le document de test
    """
    # Créer un fichier temporaire pour les tests
    temp_dir = tempfile.mkdtemp()
    test_doc_path = Path(temp_dir) / "test_document.txt"
    
    # Écrire un contenu minimal pour les tests
    with open(test_doc_path, "w", encoding="utf-8") as f:
        f.write("""# Document de test pour l'orchestration
        
## Section avec tableau
| Colonne 1 | Colonne 2 | Colonne 3 |
|-----------|-----------|-----------|
| Valeur 1  | Valeur 2  | Valeur 3  |
| Valeur 4  | Valeur 5  | Valeur 6  |

## Section avec formule
L'équation suivante montre la relation:
E = mc²

## Section avec schéma
Ce schéma représente l'architecture du système.
[Schéma technique ici]
        """)
    
    yield test_doc_path
    
    # Nettoyer
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """
    Vérifie que l'orchestrateur s'initialise correctement.
    
    Args:
        orchestrator: Fixture de l'orchestrateur
    """
    # Vérifier que l'initialisation a réussi
    assert orchestrator.initialized
    
    # Vérifier que les composants sont correctement initialisés
    assert orchestrator.strategy_selector is not None
    assert orchestrator.result_merger is not None
    assert orchestrator.parallel_executor is not None
    
    # Vérifier que les processeurs spécialisés sont disponibles
    assert len(orchestrator.specialized_processors) == 3


@pytest.mark.asyncio
async def test_strategy_selection(orchestrator, test_document):
    """
    Vérifie que le sélecteur de stratégie choisit correctement les processeurs.
    
    Args:
        orchestrator: Fixture de l'orchestrateur
        test_document: Fixture du document de test
    """
    # Sélectionner les processeurs pour le document de test
    selected_processors = await orchestrator.strategy_selector.select_processors(test_document)
    
    # Vérifier qu'au moins un processeur a été sélectionné
    assert len(selected_processors) > 0
    
    # Vérifier les types des processeurs sélectionnés
    processor_names = [p.__class__.__name__ for p in selected_processors]
    logger.info(f"Processeurs sélectionnés: {processor_names}")
    
    # Le document de test contient des références à un tableau, une formule et un schéma
    # donc ces processeurs devraient être sélectionnés
    assert any("TableExtractor" in name for name in processor_names)
    assert any("FormulaProcessor" in name for name in processor_names)
    assert any("SchemaAnalyzer" in name for name in processor_names)


@pytest.mark.asyncio
async def test_parallel_execution(orchestrator, test_document):
    """
    Vérifie que l'exécution parallèle des processeurs fonctionne correctement.
    
    Args:
        orchestrator: Fixture de l'orchestrateur
        test_document: Fixture du document de test
    """
    # Créer un répertoire de sortie temporaire
    output_dir = Path(tempfile.mkdtemp())
    
    try:
        # Sélectionner les processeurs
        selected_processors = await orchestrator.strategy_selector.select_processors(test_document)
        
        # Exécuter les processeurs en parallèle
        results = await orchestrator.parallel_executor.execute(
            selected_processors,
            test_document,
            output_dir
        )
        
        # Vérifier que des résultats ont été produits pour chaque processeur
        assert len(results) == len(selected_processors)
        
        # Vérifier que les résultats contiennent les champs attendus
        for processor_name, result in results.items():
            assert 'success' in result
            assert 'content' in result
            assert 'metadata' in result
            
    finally:
        # Nettoyer
        shutil.rmtree(output_dir)


@pytest.mark.asyncio
async def test_result_merger(orchestrator, test_document):
    """
    Vérifie que le fusionneur de résultats combine correctement les données.
    
    Args:
        orchestrator: Fixture de l'orchestrateur
        test_document: Fixture du document de test
    """
    # Créer des résultats de test
    ai_result = {
        'success': True,
        'content': {
            'text': "Contenu textuel détecté par AI",
            'tables': [{'name': 'Table AI', 'data': [[1, 2], [3, 4]]}]
        },
        'metadata': {
            'confidence': 0.8,
            'processing_time': 1.5
        }
    }
    
    processor_results = {
        'TableExtractor': {
            'success': True,
            'content': {
                'tables': [{'name': 'Table spécialisée', 'data': [[1, 2, 3], [4, 5, 6]]}]
            },
            'metadata': {
                'confidence': 0.9,
                'table_count': 1
            }
        },
        'SchemaAnalyzer': {
            'success': True,
            'content': {
                'schemas': [{'name': 'Schéma détecté', 'complexity': 'medium'}]
            },
            'metadata': {
                'confidence': 0.7,
                'schema_count': 1
            }
        }
    }
    
    # Fusionner les résultats
    merged_result = orchestrator.result_merger.merge_results(
        ai_result,
        processor_results,
        test_document
    )
    
    # Vérifier que le résultat fusionné contient toutes les données
    assert merged_result.success
    assert 'text' in merged_result.content
    assert 'tables' in merged_result.content
    assert 'schemas' in merged_result.content
    
    # Vérifier que les métadonnées ont été combinées
    assert 'processors' in merged_result.metadata
    assert len(merged_result.metadata['processors']) == 3  # AI + 2 processeurs
    
    # Vérifier que les conflits ont été gérés
    assert 'has_conflicts' in merged_result.metadata
    assert 'conflict_resolution' in merged_result.metadata


@pytest.mark.asyncio
async def test_complete_orchestration_pipeline(orchestrator, test_document):
    """
    Teste le pipeline d'orchestration complet, de l'entrée à la sortie.
    
    Args:
        orchestrator: Fixture de l'orchestrateur
        test_document: Fixture du document de test
    """
    # Créer un répertoire de sortie temporaire
    output_dir = Path(tempfile.mkdtemp())
    
    try:
        # Traiter le document avec l'orchestrateur
        result = await orchestrator.process_document(
            test_document,
            output_dir,
            language="fra"
        )
        
        # Vérifier que le traitement a réussi
        assert result.success
        assert result.document_path == str(test_document)
        
        # Vérifier que le contenu a été extrait
        assert result.content
        
        # Vérifier que les métadonnées sont présentes
        assert result.metadata
        assert 'processors' in result.metadata
        
        # Vérifier que le répertoire de sortie contient des fichiers générés
        assert any(output_dir.iterdir())
        
    finally:
        # Nettoyer
        shutil.rmtree(output_dir)


@pytest.mark.asyncio
async def test_orchestrator_error_handling(orchestrator):
    """
    Vérifie que l'orchestrateur gère correctement les erreurs.
    
    Args:
        orchestrator: Fixture de l'orchestrateur
    """
    # Tester avec un fichier inexistant
    with pytest.raises(FileNotFoundError):
        await orchestrator.process_document(
            "fichier_inexistant.txt"
        )
    
    # Tester avec un processeur qui échoue
    class FailingProcessor:
        async def process_document(self, *args, **kwargs):
            raise RuntimeError("Erreur simulée")
        
        async def initialize(self):
            return True
    
    # Sauvegarder les processeurs originaux
    original_processors = orchestrator.specialized_processors
    
    try:
        # Remplacer par un processeur qui échoue
        orchestrator.specialized_processors = [FailingProcessor()]
        
        # Le processus global devrait continuer malgré l'échec d'un processeur
        result = await orchestrator.process_document(
            test_document,
            Path(tempfile.mkdtemp())
        )
        
        # Vérifier que le résultat indique des problèmes
        assert 'error' in result.metadata
        
    finally:
        # Restaurer les processeurs originaux
        orchestrator.specialized_processors = original_processors


if __name__ == "__main__":
    # Pour exécution manuelle des tests
    pytest.main(["-xvs", __file__])
