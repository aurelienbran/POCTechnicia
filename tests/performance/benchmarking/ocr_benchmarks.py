"""
Tests de benchmark pour les performances du système OCR
======================================================

Ce module contient des tests de benchmark pour évaluer les performances
des différents composants du système OCR, notamment l'orchestration des 
processeurs, le chunking intelligent et le pipeline complet.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import asyncio
import logging
import time
from pathlib import Path
import tempfile
import json
import shutil
import random
from typing import Dict, List, Any, Optional, Union

from .benchmark_runner import BenchmarkSuite, BenchmarkResult, BenchmarkMetric, measure_time, measure_memory

from app.core.file_processing.orchestration.orchestrator import ProcessingOrchestrator
from app.core.file_processing.chunking.relational_chunker import RelationalChunker
from app.core.file_processing.chunking.metadata_enricher import MetadataEnricher
from app.core.file_processing.validation.low_confidence_detector import LowConfidenceDetector
from app.core.file_processing.specialized_processors.table_extractor import TableExtractor
from app.core.file_processing.specialized_processors.schema_analyzer import SchemaAnalyzer
from app.core.file_processing.specialized_processors.formula_processor import FormulaProcessor

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Répertoire pour les fichiers de test
TEST_FILES_DIR = Path(__file__).parent.parent.parent / "test_files"


async def prepare_test_environment():
    """Prépare l'environnement de test en créant des fichiers de test variés."""
    # Assurer que le répertoire de test existe
    TEST_FILES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Créer des fichiers de test avec différentes caractéristiques
    create_text_file_with_tables(TEST_FILES_DIR / "document_with_tables.txt")
    create_text_file_with_formulas(TEST_FILES_DIR / "document_with_formulas.txt")
    create_technical_manual(TEST_FILES_DIR / "technical_manual.txt")
    create_large_document(TEST_FILES_DIR / "large_document.txt", size_kb=500)
    
    logger.info(f"Environnement de test préparé avec des fichiers dans {TEST_FILES_DIR}")


def create_text_file_with_tables(filepath: Path):
    """Crée un fichier texte contenant des tableaux."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("""# Document avec tableaux

## Section 1
Voici un exemple de tableau:

| Composant | Référence | Prix |
|-----------|-----------|------|
| Pompe     | P-3421    | 1200 |
| Capteur   | C-789     | 350  |
| Filtre    | F-456     | 75   |

## Section 2
Un autre tableau plus complexe:

| ID | Nom     | Température | Pression | Status    |
|----|---------|-------------|----------|-----------|
| 1  | Zone A  | 87°C        | 2.4 bar  | Normal    |
| 2  | Zone B  | 92°C        | 2.1 bar  | Attention |
| 3  | Zone C  | 78°C        | 2.5 bar  | Normal    |
| 4  | Zone D  | 104°C       | 1.9 bar  | Critique  |
        """)


def create_text_file_with_formulas(filepath: Path):
    """Crée un fichier texte contenant des formules."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("""# Document avec formules techniques

## Équations importantes

### Équation 1: Transfert thermique
Le taux de transfert thermique à travers une paroi est donné par:

Q = k·A·(T₂ - T₁)/d

où:
- Q est le taux de transfert thermique en Watts
- k est la conductivité thermique du matériau en W/(m·K)
- A est la surface en m²
- T₂ - T₁ est la différence de température en Kelvins
- d est l'épaisseur du matériau en mètres

### Équation 2: Régulation PID
L'équation générale d'un contrôleur PID est:

u(t) = Kp·e(t) + Ki·∫e(τ)dτ + Kd·de(t)/dt

où:
- u(t) est la variable de contrôle
- e(t) est l'erreur (consigne - mesure)
- Kp, Ki, Kd sont les constantes proportionnelle, intégrale et dérivée

### Équation 3: Efficacité énergétique
L'efficacité énergétique η est calculée comme:

η = Wsortie/Wentrée × 100%
        """)


def create_technical_manual(filepath: Path):
    """Crée un fichier simulant un manuel technique."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("""# Manuel technique du système de refroidissement TX-5000

## 1. Introduction
Ce manuel contient les instructions de maintenance et d'utilisation du système de refroidissement industriel TX-5000.

## 2. Spécifications techniques
- Puissance: 75 kW
- Alimentation: 380V triphasé
- Fluide: R-134a
- Capacité: 200 litres
- Dimensions: 2.1m × 1.4m × 1.8m

## 3. Composants principaux
### 3.1 Compresseur
Le compresseur (réf. CP-7890) est le cœur du système. Il comprime le fluide frigorigène et assure sa circulation.

### 3.2 Échangeur thermique
L'échangeur (réf. ET-4567) permet le transfert de chaleur entre le fluide et l'environnement extérieur.

### 3.3 Circuit de contrôle
Le circuit de contrôle utilise un PLC Siemens S7-1200 pour réguler tous les paramètres de fonctionnement.

## 4. Procédures de maintenance
### 4.1 Maintenance mensuelle
1. Vérifier la pression du fluide frigorigène
2. Nettoyer les filtres d'entrée d'air
3. Contrôler les niveaux d'huile du compresseur
4. Inspecter les connexions électriques

### 4.2 Maintenance annuelle
1. Remplacer le fluide frigorigène
2. Vérifier l'étanchéité du circuit
3. Calibrer les capteurs de température et de pression
4. Lubrifier les éléments mécaniques mobiles

## 5. Schémas techniques
Voir les schémas du circuit de refroidissement en annexe A.
Voir les schémas électriques en annexe B.

## 6. Dépannage
| Symptôme | Cause possible | Solution |
|----------|----------------|----------|
| Chute de pression | Fuite dans le circuit | Vérifier les joints et les raccords |
| Température élevée | Filtre obstrué | Nettoyer ou remplacer le filtre |
| Bruit anormal | Palier usé | Remplacer le palier défectueux |
        """)


def create_large_document(filepath: Path, size_kb: int = 100):
    """
    Crée un grand document de test avec la taille spécifiée en kilooctets.
    
    Args:
        filepath: Chemin du fichier à créer
        size_kb: Taille approximative du fichier en kilooctets
    """
    paragraphs = [
        "Le système de refroidissement industriel TX-5000 représente une avancée significative dans le domaine de la thermodynamique appliquée. Sa conception modulaire permet une adaptation optimale aux contraintes spécifiques de chaque environnement industriel.",
        "La maintenance préventive est essentielle pour garantir les performances du système. Un entretien régulier permet d'éviter les pannes coûteuses et prolonge la durée de vie de l'équipement.",
        "Les capteurs de température distribuée offrent une surveillance en temps réel de l'ensemble du circuit de refroidissement, permettant une détection précoce des anomalies et une intervention rapide.",
        "L'échangeur thermique principal utilise une technologie de transfert à micro-canaux qui améliore significativement le coefficient de transfert thermique global du système.",
        "Le compresseur à vitesse variable ajuste automatiquement son régime en fonction de la charge thermique détectée, optimisant ainsi la consommation énergétique du système.",
        "Le fluide frigorigène R-134a a été sélectionné pour son faible impact environnemental et ses excellentes propriétés thermodynamiques dans la plage de température opérationnelle.",
        "Le circuit de contrôle utilise un algorithme PID adaptatif qui optimise en permanence les paramètres de régulation en fonction des conditions d'exploitation.",
        "La vanne d'expansion électronique permet un contrôle précis du débit de fluide frigorigène, assurant un refroidissement optimal quelle que soit la charge thermique."
    ]
    
    formulas = [
        "Q = m·Cp·ΔT - Équation de transfert thermique",
        "P = ρ·g·h - Équation de pression hydrostatique",
        "Re = ρ·v·D/μ - Nombre de Reynolds pour caractériser l'écoulement",
        "Nu = h·D/k - Nombre de Nusselt pour le transfert thermique",
        "COP = Qf/W - Coefficient de performance du système",
        "η = (h₂ - h₁)/(h₃ - h₁) - Rendement isentropique du compresseur"
    ]
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# Documentation technique du système TX-5000\n\n")
        
        # Écrire jusqu'à atteindre la taille approximative
        current_size = 0
        target_size = size_kb * 1024
        
        section_num = 1
        subsection_num = 1
        
        while current_size < target_size:
            # Ajouter une nouvelle section
            f.write(f"\n## {section_num}. Section technique\n\n")
            
            # Ajouter plusieurs paragraphes
            for _ in range(random.randint(3, 8)):
                paragraph = random.choice(paragraphs)
                f.write(paragraph + "\n\n")
            
            # Ajouter une sous-section
            f.write(f"\n### {section_num}.{subsection_num} Informations techniques\n\n")
            
            # Ajouter une formule
            formula = random.choice(formulas)
            f.write(f"La formule applicable est: {formula}\n\n")
            
            # Ajouter un petit tableau
            f.write("| Paramètre | Valeur | Unité |\n")
            f.write("|-----------|--------|-------|\n")
            for _ in range(random.randint(3, 6)):
                param = random.choice(["Température", "Pression", "Débit", "Puissance", "Rendement", "Viscosité"])
                value = round(random.uniform(10, 1000), 2)
                unit = random.choice(["°C", "bar", "m³/h", "kW", "%", "Pa·s"])
                f.write(f"| {param} | {value} | {unit} |\n")
                
            f.write("\n")
            
            # Incrémenter les numéros de section et sous-section
            subsection_num += 1
            if subsection_num > 5:
                section_num += 1
                subsection_num = 1
                
            # Vérifier la taille actuelle
            current_size = filepath.stat().st_size if filepath.exists() else 0


# Tests de benchmark pour l'orchestration des processeurs
@measure_time("total_orchestration_time")
@measure_memory("orchestration_memory")
async def benchmark_orchestration(result: BenchmarkResult, document_path: Path, config: Dict[str, Any]):
    """
    Benchmark pour l'orchestration des processeurs.
    
    Args:
        result: Objet pour stocker les résultats du benchmark
        document_path: Chemin vers le document à traiter
        config: Configuration de l'orchestrateur
    """
    # Créer et initialiser l'orchestrateur
    orchestrator = ProcessingOrchestrator(config)
    
    init_metric = BenchmarkMetric("initialization_time", "s", "Temps d'initialisation de l'orchestrateur")
    result.add_metric(init_metric)
    
    start_time = time.time()
    await orchestrator.initialize()
    init_metric.add_value(time.time() - start_time)
    
    # Configurer les processeurs spécialisés
    orchestrator.specialized_processors = [
        TableExtractor(),
        SchemaAnalyzer(),
        FormulaProcessor()
    ]
    
    # Mesurer le temps de sélection des processeurs
    selection_metric = BenchmarkMetric("processor_selection_time", "s", "Temps de sélection des processeurs")
    result.add_metric(selection_metric)
    
    start_time = time.time()
    selected_processors = await orchestrator.strategy_selector.select_processors(document_path)
    selection_metric.add_value(time.time() - start_time)
    
    # Mesurer le temps d'exécution des processeurs
    execution_metric = BenchmarkMetric("processor_execution_time", "s", "Temps d'exécution des processeurs")
    result.add_metric(execution_metric)
    
    output_dir = Path(tempfile.mkdtemp())
    try:
        start_time = time.time()
        processor_results = await orchestrator.parallel_executor.execute(
            selected_processors, document_path, output_dir
        )
        execution_metric.add_value(time.time() - start_time)
        
        # Mesurer le temps de fusion des résultats
        merger_metric = BenchmarkMetric("result_merger_time", "s", "Temps de fusion des résultats")
        result.add_metric(merger_metric)
        
        start_time = time.time()
        ai_result = {"success": True, "content": {}, "metadata": {}}  # Résultat fictif
        merged_result = orchestrator.result_merger.merge_results(ai_result, processor_results, document_path)
        merger_metric.add_value(time.time() - start_time)
        
        # Ajouter des métriques sur les résultats
        num_processors_metric = BenchmarkMetric("num_processors", "count", "Nombre de processeurs utilisés")
        num_processors_metric.add_value(len(selected_processors))
        result.add_metric(num_processors_metric)
        
    finally:
        # Nettoyer
        shutil.rmtree(output_dir)


# Tests de benchmark pour le chunking intelligent
@measure_time("total_chunking_time")
@measure_memory("chunking_memory")
async def benchmark_chunking(result: BenchmarkResult, document_path: Path, config: Dict[str, Any]):
    """
    Benchmark pour le chunking intelligent.
    
    Args:
        result: Objet pour stocker les résultats du benchmark
        document_path: Chemin vers le document à traiter
        config: Configuration du chunker
    """
    # Créer le chunker
    chunker = RelationalChunker(config)
    
    # Lire le document
    with open(document_path, "r", encoding="utf-8") as f:
        document_text = f.read()
        
    # Mesurer le temps de chunking
    chunking_metric = BenchmarkMetric("chunking_text_time", "s", "Temps de chunking du texte")
    result.add_metric(chunking_metric)
    
    start_time = time.time()
    chunking_result = await chunker.chunk_text(
        text=document_text,
        max_chunk_size=config.get("chunk_size", 500),
        overlap=config.get("overlap", 50)
    )
    chunking_metric.add_value(time.time() - start_time)
    
    # Mesurer le temps d'enrichissement des métadonnées
    enricher = MetadataEnricher(config.get("metadata_enricher_config", {}))
    
    enrichment_metric = BenchmarkMetric("metadata_enrichment_time", "s", "Temps d'enrichissement des métadonnées")
    result.add_metric(enrichment_metric)
    
    start_time = time.time()
    enriched_result = enricher.enrich_chunks(chunking_result)
    enrichment_metric.add_value(time.time() - start_time)
    
    # Ajouter des métriques sur les résultats
    num_chunks_metric = BenchmarkMetric("num_chunks", "count", "Nombre de chunks générés")
    num_chunks_metric.add_value(len(chunking_result.chunks))
    result.add_metric(num_chunks_metric)
    
    avg_chunk_size_metric = BenchmarkMetric("avg_chunk_size", "chars", "Taille moyenne des chunks")
    avg_chunk_size = sum(len(c['text']) for c in chunking_result.chunks) / len(chunking_result.chunks) if chunking_result.chunks else 0
    avg_chunk_size_metric.add_value(avg_chunk_size)
    result.add_metric(avg_chunk_size_metric)
    
    num_relations_metric = BenchmarkMetric("num_relations", "count", "Nombre de relations établies")
    num_relations = sum(len(c.get('metadata', {}).get('relations', [])) for c in enriched_result.chunks)
    num_relations_metric.add_value(num_relations)
    result.add_metric(num_relations_metric)


# Tests de benchmark pour la validation OCR
@measure_time("total_validation_time")
@measure_memory("validation_memory")
async def benchmark_validation(result: BenchmarkResult, document_path: Path, config: Dict[str, Any]):
    """
    Benchmark pour la validation OCR.
    
    Args:
        result: Objet pour stocker les résultats du benchmark
        document_path: Chemin vers le document à traiter
        config: Configuration du détecteur
    """
    # Créer le détecteur
    detector = LowConfidenceDetector(config)
    
    # Créer un résultat de traitement simulé
    processing_result = {
        "content": {
            "text": "Contenu du document avec quelques erreurs potentielles",
            "pages": [{"text": "Page 1 content", "confidence": 0.85}],
            "tables": [{"data": [[1, 2], [3, 4]], "confidence": 0.92}]
        },
        "metadata": {
            "ocr_confidence": 0.88,
            "processing_time": 1.2
        }
    }
    
    # Mesurer le temps d'analyse
    analysis_metric = BenchmarkMetric("analysis_time", "s", "Temps d'analyse du document")
    result.add_metric(analysis_metric)
    
    start_time = time.time()
    issues = detector.analyze_document(document_path, processing_result)
    analysis_metric.add_value(time.time() - start_time)
    
    # Ajouter des métriques sur les résultats
    num_issues_metric = BenchmarkMetric("num_issues", "count", "Nombre de problèmes détectés")
    num_issues_metric.add_value(len(issues) if issues else 0)
    result.add_metric(num_issues_metric)


async def run_ocr_benchmarks():
    """
    Exécute tous les benchmarks OCR et génère des rapports.
    """
    # Préparer l'environnement de test
    await prepare_test_environment()
    
    # Créer la suite de benchmarks
    suite = BenchmarkSuite("OCR_System_Benchmarks", "Tests de performance du système OCR")
    suite.start()
    
    try:
        # Charger les documents de test
        documents = {
            "tables": TEST_FILES_DIR / "document_with_tables.txt",
            "formulas": TEST_FILES_DIR / "document_with_formulas.txt",
            "manual": TEST_FILES_DIR / "technical_manual.txt",
            "large": TEST_FILES_DIR / "large_document.txt"
        }
        
        # Configurations à tester
        orchestrator_configs = [
            {
                "name": "Basic Config",
                "max_parallel": 2,
                "strategy_weights": {"has_tables": 1.0, "has_schemas": 0.8, "has_formulas": 0.9},
                "use_ai_orchestrator": False
            },
            {
                "name": "Advanced Config",
                "max_parallel": 4,
                "strategy_weights": {"has_tables": 1.0, "has_schemas": 1.0, "has_formulas": 1.0},
                "use_ai_orchestrator": True,
                "ai_weight": 0.7
            }
        ]
        
        chunking_configs = [
            {
                "name": "Small Chunks",
                "chunk_size": 200,
                "overlap": 20,
                "semantic_chunker_config": {"respect_semantic_boundaries": True},
                "metadata_enricher_config": {"extract_entities": True, "detect_key_terms": True}
            },
            {
                "name": "Medium Chunks",
                "chunk_size": 500,
                "overlap": 50,
                "semantic_chunker_config": {"respect_semantic_boundaries": True},
                "metadata_enricher_config": {"extract_entities": True, "detect_key_terms": True}
            },
            {
                "name": "Large Chunks",
                "chunk_size": 1000,
                "overlap": 100,
                "semantic_chunker_config": {"respect_semantic_boundaries": True},
                "metadata_enricher_config": {"extract_entities": True, "detect_key_terms": True}
            }
        ]
        
        validation_configs = [
            {
                "name": "Strict Validation",
                "confidence_thresholds": {"global": 0.9, "text": 0.85, "table": 0.9, "formula": 0.95}
            },
            {
                "name": "Normal Validation",
                "confidence_thresholds": {"global": 0.8, "text": 0.75, "table": 0.8, "formula": 0.85}
            }
        ]
        
        # Exécuter les benchmarks d'orchestration
        for config in orchestrator_configs:
            for doc_name, doc_path in documents.items():
                await suite.run_benchmark(
                    name=f"orchestration_{config['name']}_{doc_name}",
                    component="orchestration",
                    configuration={**config, "document_type": doc_name},
                    benchmark_func=benchmark_orchestration,
                    document_path=doc_path,
                    config=config
                )
        
        # Exécuter les benchmarks de chunking
        for config in chunking_configs:
            for doc_name, doc_path in documents.items():
                await suite.run_benchmark(
                    name=f"chunking_{config['name']}_{doc_name}",
                    component="chunking",
                    configuration={**config, "document_type": doc_name},
                    benchmark_func=benchmark_chunking,
                    document_path=doc_path,
                    config=config
                )
        
        # Exécuter les benchmarks de validation
        for config in validation_configs:
            for doc_name, doc_path in documents.items():
                await suite.run_benchmark(
                    name=f"validation_{config['name']}_{doc_name}",
                    component="validation",
                    configuration={**config, "document_type": doc_name},
                    benchmark_func=benchmark_validation,
                    document_path=doc_path,
                    config=config
                )
        
    finally:
        # Terminer la suite et générer les rapports
        suite.complete()
        
        logger.info(f"Benchmarks terminés. Résultats disponibles dans {suite.output_dir}")
        return suite.output_dir


if __name__ == "__main__":
    # Pour exécution manuelle des benchmarks
    asyncio.run(run_ocr_benchmarks())
