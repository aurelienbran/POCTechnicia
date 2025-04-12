"""
Script d'exécution de tous les tests du système OCR
===================================================

Ce script permet d'exécuter tous les tests du système OCR :
- Tests unitaires
- Tests d'intégration
- Tests de performance/benchmarking

Il génère des rapports détaillés et identifie les problèmes potentiels
et les goulots d'étranglement.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import sys
import time
import asyncio
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
import subprocess
from typing import List, Dict, Any, Optional, Union

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Répertoire racine du projet
PROJECT_ROOT = Path(__file__).parent.parent


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Exécute les tests du système OCR")
    
    parser.add_argument("--unit", action="store_true", help="Exécuter les tests unitaires")
    parser.add_argument("--integration", action="store_true", help="Exécuter les tests d'intégration")
    parser.add_argument("--performance", action="store_true", help="Exécuter les tests de performance")
    parser.add_argument("--all", action="store_true", help="Exécuter tous les types de tests")
    parser.add_argument("--report-dir", type=str, default="test_reports", 
                        help="Répertoire où stocker les rapports de tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    
    args = parser.parse_args()
    
    # Si aucun type de test n'est spécifié, exécuter tous les tests
    if not (args.unit or args.integration or args.performance):
        args.all = True
        
    return args


def setup_report_directory(report_dir: str) -> Path:
    """
    Crée le répertoire pour les rapports de tests.
    
    Args:
        report_dir: Chemin du répertoire pour les rapports
        
    Returns:
        Path: Chemin absolu du répertoire créé
    """
    report_path = PROJECT_ROOT / report_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Rapports de tests seront stockés dans: {report_path}")
    return report_path


def run_unit_tests(report_dir: Path, verbose: bool = False) -> bool:
    """
    Exécute les tests unitaires et génère un rapport.
    
    Args:
        report_dir: Répertoire où stocker les rapports
        verbose: Mode verbeux
    
    Returns:
        bool: True si tous les tests ont réussi, False sinon
    """
    logger.info("Exécution des tests unitaires...")
    unit_report_dir = report_dir / "unit"
    unit_report_dir.mkdir(exist_ok=True)
    
    # Construire la commande pytest
    cmd = [
        sys.executable, "-m", "pytest",
        str(PROJECT_ROOT / "tests" / "unit"),
        "-v" if verbose else "",
        f"--junitxml={unit_report_dir / 'unit_results.xml'}",
        "--html", str(unit_report_dir / "unit_report.html")
    ]
    
    # Filtrer les options vides
    cmd = [c for c in cmd if c]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time
    
    # Enregistrer la sortie
    with open(unit_report_dir / "stdout.log", "w") as f:
        f.write(result.stdout)
        
    with open(unit_report_dir / "stderr.log", "w") as f:
        f.write(result.stderr)
    
    # Créer un rapport de synthèse
    success = result.returncode == 0
    summary = {
        "type": "unit_tests",
        "timestamp": datetime.now().isoformat(),
        "duration": duration,
        "success": success,
        "returncode": result.returncode,
        "command": " ".join(cmd)
    }
    
    with open(unit_report_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    if success:
        logger.info(f"Tests unitaires terminés avec succès en {duration:.2f}s")
    else:
        logger.error(f"Tests unitaires ont échoué (code {result.returncode}) en {duration:.2f}s")
        if verbose:
            print(result.stderr)
    
    return success


def run_integration_tests(report_dir: Path, verbose: bool = False) -> bool:
    """
    Exécute les tests d'intégration et génère un rapport.
    
    Args:
        report_dir: Répertoire où stocker les rapports
        verbose: Mode verbeux
    
    Returns:
        bool: True si tous les tests ont réussi, False sinon
    """
    logger.info("Exécution des tests d'intégration...")
    integration_report_dir = report_dir / "integration"
    integration_report_dir.mkdir(exist_ok=True)
    
    # Construire la commande pytest
    cmd = [
        sys.executable, "-m", "pytest",
        str(PROJECT_ROOT / "tests" / "integration"),
        "-v" if verbose else "",
        f"--junitxml={integration_report_dir / 'integration_results.xml'}",
        "--html", str(integration_report_dir / "integration_report.html")
    ]
    
    # Filtrer les options vides
    cmd = [c for c in cmd if c]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time
    
    # Enregistrer la sortie
    with open(integration_report_dir / "stdout.log", "w") as f:
        f.write(result.stdout)
        
    with open(integration_report_dir / "stderr.log", "w") as f:
        f.write(result.stderr)
    
    # Créer un rapport de synthèse
    success = result.returncode == 0
    summary = {
        "type": "integration_tests",
        "timestamp": datetime.now().isoformat(),
        "duration": duration,
        "success": success,
        "returncode": result.returncode,
        "command": " ".join(cmd)
    }
    
    with open(integration_report_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    if success:
        logger.info(f"Tests d'intégration terminés avec succès en {duration:.2f}s")
    else:
        logger.error(f"Tests d'intégration ont échoué (code {result.returncode}) en {duration:.2f}s")
        if verbose:
            print(result.stderr)
    
    return success


async def run_performance_tests(report_dir: Path, verbose: bool = False) -> bool:
    """
    Exécute les tests de performance et génère un rapport.
    
    Args:
        report_dir: Répertoire où stocker les rapports
        verbose: Mode verbeux
    
    Returns:
        bool: True si tous les tests ont réussi, False sinon
    """
    logger.info("Exécution des tests de performance...")
    perf_report_dir = report_dir / "performance"
    perf_report_dir.mkdir(exist_ok=True)
    
    try:
        # Importer le module de benchmarking OCR
        sys.path.insert(0, str(PROJECT_ROOT))
        from tests.performance.benchmarking.ocr_benchmarks import run_ocr_benchmarks
        
        start_time = time.time()
        # Exécuter les benchmarks
        benchmark_result_dir = await run_ocr_benchmarks()
        duration = time.time() - start_time
        
        # Copier les résultats vers le répertoire de rapport
        if Path(benchmark_result_dir).exists():
            import shutil
            for item in Path(benchmark_result_dir).glob("**/*"):
                if item.is_file():
                    rel_path = item.relative_to(benchmark_result_dir)
                    dest_path = perf_report_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
            
        # Créer un rapport de synthèse
        summary = {
            "type": "performance_tests",
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "success": True,
            "benchmark_result_dir": str(benchmark_result_dir)
        }
        
        with open(perf_report_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Tests de performance terminés avec succès en {duration:.2f}s")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution des tests de performance: {str(e)}", exc_info=True)
        
        # Créer un rapport d'erreur
        summary = {
            "type": "performance_tests",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": str(e)
        }
        
        with open(perf_report_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
            
        return False


def generate_final_report(report_dir: Path, unit_success: Optional[bool] = None, 
                        integration_success: Optional[bool] = None,
                        performance_success: Optional[bool] = None) -> None:
    """
    Génère un rapport final consolidant les résultats de tous les tests.
    
    Args:
        report_dir: Répertoire contenant les rapports
        unit_success: Succès des tests unitaires
        integration_success: Succès des tests d'intégration
        performance_success: Succès des tests de performance
    """
    logger.info("Génération du rapport final...")
    
    # Collecter toutes les informations des rapports
    unit_summary = None
    if (report_dir / "unit" / "summary.json").exists():
        with open(report_dir / "unit" / "summary.json", "r") as f:
            unit_summary = json.load(f)
    
    integration_summary = None
    if (report_dir / "integration" / "summary.json").exists():
        with open(report_dir / "integration" / "summary.json", "r") as f:
            integration_summary = json.load(f)
    
    performance_summary = None
    if (report_dir / "performance" / "summary.json").exists():
        with open(report_dir / "performance" / "summary.json", "r") as f:
            performance_summary = json.load(f)
    
    # Générer le rapport final
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "report_dir": str(report_dir),
        "tests": {
            "unit": unit_summary,
            "integration": integration_summary,
            "performance": performance_summary
        },
        "overall_success": all(s for s in [unit_success, integration_success, performance_success] if s is not None)
    }
    
    with open(report_dir / "final_report.json", "w") as f:
        json.dump(final_report, f, indent=2)
    
    # Générer un rapport HTML
    html_report = f"""<!DOCTYPE html>
<html>
<head>
    <title>Rapport de tests OCR</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>Rapport de tests du système OCR</h1>
    <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>Statut global:</strong> 
        <span class="{'success' if final_report['overall_success'] else 'failure'}">
            {"Succès" if final_report['overall_success'] else "Échec"}
        </span>
    </p>
    
    <h2>Résumé des tests</h2>
    <table>
        <tr>
            <th>Type de test</th>
            <th>Statut</th>
            <th>Durée (s)</th>
            <th>Détails</th>
        </tr>
    """
    
    if unit_summary:
        html_report += f"""
        <tr>
            <td>Tests unitaires</td>
            <td class="{'success' if unit_summary['success'] else 'failure'}">
                {"Succès" if unit_summary['success'] else "Échec"}
            </td>
            <td>{unit_summary.get('duration', 'N/A'):.2f}</td>
            <td><a href="unit/unit_report.html">Voir détails</a></td>
        </tr>
        """
    
    if integration_summary:
        html_report += f"""
        <tr>
            <td>Tests d'intégration</td>
            <td class="{'success' if integration_summary['success'] else 'failure'}">
                {"Succès" if integration_summary['success'] else "Échec"}
            </td>
            <td>{integration_summary.get('duration', 'N/A'):.2f}</td>
            <td><a href="integration/integration_report.html">Voir détails</a></td>
        </tr>
        """
    
    if performance_summary:
        html_report += f"""
        <tr>
            <td>Tests de performance</td>
            <td class="{'success' if performance_summary['success'] else 'failure'}">
                {"Succès" if performance_summary['success'] else "Échec"}
            </td>
            <td>{performance_summary.get('duration', 'N/A'):.2f}</td>
            <td><a href="performance/visualizations/benchmark_data.csv">Voir données</a></td>
        </tr>
        """
    
    html_report += """
    </table>
    
    <h2>Résultats détaillés</h2>
    <p>Pour plus de détails, consultez les rapports individuels dans les sous-répertoires.</p>
    
    <h2>Actions recommandées</h2>
    <ul>
    """
    
    if unit_summary and not unit_summary['success']:
        html_report += "<li>Corriger les erreurs dans les tests unitaires</li>"
    
    if integration_summary and not integration_summary['success']:
        html_report += "<li>Résoudre les problèmes d'intégration entre les composants</li>"
    
    if performance_summary and not performance_summary['success']:
        html_report += "<li>Investiguer les problèmes de performance</li>"
    
    html_report += """
    </ul>
    
    <footer>
        <p>Généré automatiquement par le système de test Technicia</p>
    </footer>
</body>
</html>
    """
    
    with open(report_dir / "final_report.html", "w") as f:
        f.write(html_report)
    
    logger.info(f"Rapport final généré dans {report_dir}")


async def main():
    """Fonction principale du script."""
    args = parse_arguments()
    
    # Configurer le niveau de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Créer le répertoire pour les rapports
    report_dir = setup_report_directory(args.report_dir)
    
    unit_success = None
    integration_success = None
    performance_success = None
    
    # Exécuter les tests selon les options
    if args.all or args.unit:
        unit_success = run_unit_tests(report_dir, args.verbose)
    
    if args.all or args.integration:
        integration_success = run_integration_tests(report_dir, args.verbose)
    
    if args.all or args.performance:
        performance_success = await run_performance_tests(report_dir, args.verbose)
    
    # Générer le rapport final
    generate_final_report(report_dir, unit_success, integration_success, performance_success)
    
    # Déterminer le code de retour
    success = all(s for s in [unit_success, integration_success, performance_success] if s is not None)
    
    logger.info(f"Tous les tests sont terminés. Résultat global: {'Succès' if success else 'Échec'}")
    logger.info(f"Rapports disponibles dans: {report_dir}")
    
    return 0 if success else 1


if __name__ == "__main__":
    # Exécuter la fonction principale de manière asynchrone
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
