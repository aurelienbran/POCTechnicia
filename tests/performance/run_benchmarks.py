#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution des benchmarks pour le système OCR.

Ce script coordonne l'exécution des benchmarks sur l'ensemble des composants
du système OCR et génère des rapports détaillés des performances.
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH pour permettre les imports relatifs
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Import des modules de benchmark
from tests.performance.benchmarking.benchmark_runner import BenchmarkRunner
from tests.performance.benchmarking.ocr_benchmarks import (
    OrchestrationBenchmarks,
    ChunkingBenchmarks,
    OCRProcessorBenchmarks,
    ValidationBenchmarks,
    SpecializedProcessorBenchmarks,
    IntegrationBenchmarks
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Exécuter les benchmarks du système OCR")
    parser.add_argument(
        "--mode",
        choices=["quick", "full", "targeted"],
        default="quick",
        help="Mode d'exécution des benchmarks (quick, full, targeted)"
    )
    parser.add_argument(
        "--components",
        nargs="+",
        choices=["orchestration", "chunking", "ocr", "validation", "specialized", "integration"],
        help="Composants spécifiques à benchmarker (utilisé avec --mode=targeted)"
    )
    parser.add_argument(
        "--output-dir",
        default=f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Répertoire de sortie pour les résultats"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Activer les logs détaillés"
    )
    return parser.parse_args()

def run_benchmarks(mode, components=None, output_dir=None, verbose=False):
    """
    Exécute les benchmarks selon le mode spécifié.
    
    Args:
        mode: Mode d'exécution ('quick', 'full', 'targeted')
        components: Liste des composants à benchmarker (pour le mode 'targeted')
        output_dir: Répertoire de sortie pour les résultats
        verbose: Activer les logs détaillés
    
    Returns:
        Dict: Résultats des benchmarks
    """
    start_time = time.time()
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Création du répertoire de sortie
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Path(f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Les résultats seront sauvegardés dans: {output_path}")
    
    # Initialisation du runner de benchmark
    benchmark_runner = BenchmarkRunner(
        output_dir=str(output_path),
        generate_visualizations=True,
        save_raw_results=True
    )
    
    # Mapping des classes de benchmark
    benchmark_classes = {
        "orchestration": OrchestrationBenchmarks,
        "chunking": ChunkingBenchmarks,
        "ocr": OCRProcessorBenchmarks,
        "validation": ValidationBenchmarks,
        "specialized": SpecializedProcessorBenchmarks,
        "integration": IntegrationBenchmarks
    }
    
    # Sélection des benchmarks à exécuter selon le mode
    benchmarks_to_run = []
    
    if mode == "quick":
        # En mode rapide, exécuter un sous-ensemble de benchmarks
        logger.info("Exécution des benchmarks en mode rapide")
        for component in ["orchestration", "ocr"]:
            benchmark_class = benchmark_classes[component]
            benchmarks_to_run.append(benchmark_class(quick_mode=True))
    
    elif mode == "full":
        # En mode complet, exécuter tous les benchmarks
        logger.info("Exécution des benchmarks en mode complet")
        for component, benchmark_class in benchmark_classes.items():
            benchmarks_to_run.append(benchmark_class(quick_mode=False))
    
    elif mode == "targeted" and components:
        # En mode ciblé, exécuter uniquement les composants spécifiés
        logger.info(f"Exécution des benchmarks en mode ciblé pour: {', '.join(components)}")
        for component in components:
            if component in benchmark_classes:
                benchmark_class = benchmark_classes[component]
                benchmarks_to_run.append(benchmark_class(quick_mode=False))
    
    # Exécution des benchmarks
    all_results = {}
    for benchmark in benchmarks_to_run:
        logger.info(f"Exécution des benchmarks pour: {benchmark.__class__.__name__}")
        results = benchmark_runner.run_benchmark(benchmark)
        all_results[benchmark.__class__.__name__] = results
    
    # Génération du rapport final
    benchmark_runner.generate_report(all_results)
    
    duration = time.time() - start_time
    logger.info(f"Tous les benchmarks ont été exécutés en {duration:.2f} secondes")
    
    return all_results

def main():
    """Point d'entrée principal du script."""
    args = parse_args()
    
    logger.info("Démarrage de l'exécution des benchmarks")
    logger.info(f"Mode: {args.mode}")
    if args.components:
        logger.info(f"Composants: {', '.join(args.components)}")
    
    try:
        run_benchmarks(
            mode=args.mode,
            components=args.components,
            output_dir=args.output_dir,
            verbose=args.verbose
        )
        logger.info("Exécution des benchmarks terminée avec succès")
    except Exception as e:
        logger.error(f"Erreur pendant l'exécution des benchmarks: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
