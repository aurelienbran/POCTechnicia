"""
Script d'optimisation du système OCR pour le POC Technicia
==========================================================

Ce script orchestre l'ensemble du processus d'optimisation du système OCR:
1. Exécution des benchmarks
2. Analyse des résultats
3. Identification des goulots d'étranglement
4. Application des optimisations automatiques
5. Génération de rapports et recommandations

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import sys
import json
import logging
import argparse
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ajouter le répertoire racine au path pour importer les modules du projet
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.performance.benchmarking.ocr_benchmarks import run_ocr_benchmarks
from tests.performance.optimizations.benchmark_analyzer import BenchmarkAnalyzer, analyze_benchmark_results
from tests.performance.optimizations.performance_optimizer import CodeOptimizer, PerformanceBottleneck

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("optimization_log.txt")
    ]
)
logger = logging.getLogger(__name__)

# Répertoire racine du projet
PROJECT_ROOT = Path(__file__).parent.parent.parent


class SystemOptimizer:
    """
    Classe qui orchestre le processus complet d'optimisation du système OCR.
    """
    
    def __init__(self, output_dir: Path = None, auto_apply: bool = False, 
                threshold: str = "high"):
        """
        Initialise l'optimiseur du système.
        
        Args:
            output_dir: Répertoire de sortie pour les résultats (par défaut: timestamp dans "optimization_results")
            auto_apply: Si True, applique automatiquement les optimisations identifiées
            threshold: Seuil de sévérité à partir duquel appliquer les optimisations (critical, high, medium, low)
        """
        self.auto_apply = auto_apply
        self.threshold_level = threshold
        
        # Créer le répertoire de sortie
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = PROJECT_ROOT / "optimization_results" / timestamp
            
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Sous-répertoires
        self.benchmark_dir = self.output_dir / "benchmarks"
        self.analysis_dir = self.output_dir / "analysis"
        self.optimization_dir = self.output_dir / "optimizations"
        
        for dir_path in [self.benchmark_dir, self.analysis_dir, self.optimization_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Initialiser les objets d'analyse et d'optimisation
        self.analyzer = BenchmarkAnalyzer(PROJECT_ROOT)
        self.optimizer = CodeOptimizer(PROJECT_ROOT)
        
        logger.info(f"Optimiseur initialisé. Résultats dans: {self.output_dir}")
        
    async def run_full_optimization(self) -> Dict[str, Any]:
        """
        Exécute l'ensemble du processus d'optimisation:
        1. Exécution des benchmarks
        2. Analyse des résultats
        3. Identification des goulots d'étranglement
        4. Application des optimisations (si auto_apply est True)
        5. Génération de rapports
        
        Returns:
            Rapport d'optimisation
        """
        start_time = datetime.now()
        report = {
            "start_time": start_time.isoformat(),
            "project_root": str(PROJECT_ROOT),
            "output_dir": str(self.output_dir),
            "auto_apply": self.auto_apply,
            "threshold_level": self.threshold_level,
            "steps": {}
        }
        
        try:
            # 1. Exécuter les benchmarks
            logger.info("Étape 1: Exécution des benchmarks")
            benchmark_result = await self._run_benchmarks()
            report["steps"]["benchmarks"] = {
                "success": benchmark_result.get("success", False),
                "directory": str(benchmark_result.get("directory", ""))
            }
            
            if not benchmark_result["success"]:
                report["error"] = f"Erreur lors de l'exécution des benchmarks: {benchmark_result.get('error', 'Erreur inconnue')}"
                report["success"] = False
                return report
                
            # 2. Analyser les résultats
            logger.info("Étape 2: Analyse des résultats de benchmark")
            analysis_result = self._analyze_benchmarks(benchmark_result["directory"])
            report["steps"]["analysis"] = {
                "success": analysis_result.get("success", False),
                "bottlenecks_count": len(analysis_result.get("analysis", {}).get("bottlenecks", []))
            }
            
            if not analysis_result["success"]:
                report["error"] = f"Erreur lors de l'analyse des benchmarks: {analysis_result.get('error', 'Erreur inconnue')}"
                report["success"] = False
                return report
                
            # 3. Identifier les optimisations
            logger.info("Étape 3: Identification des optimisations possibles")
            optimizations = self._identify_optimizations(analysis_result["analysis"]["bottlenecks"])
            report["steps"]["optimizations"] = {
                "total_count": len(optimizations),
                "automated_count": sum(1 for o in optimizations if o["automated"]),
                "manual_count": sum(1 for o in optimizations if not o["automated"])
            }
            
            # 4. Appliquer les optimisations automatiques si demandé
            if self.auto_apply and optimizations:
                logger.info("Étape 4: Application des optimisations automatiques")
                optimization_results = self._apply_optimizations(optimizations)
                report["steps"]["application"] = {
                    "successful_count": sum(1 for r in optimization_results if r["success"]),
                    "failed_count": sum(1 for r in optimization_results if not r["success"]),
                    "results": optimization_results
                }
            else:
                logger.info("Application automatique des optimisations désactivée")
                report["steps"]["application"] = {
                    "status": "skipped",
                    "reason": "auto_apply is False" if not self.auto_apply else "No optimizations found"
                }
                
            # 5. Générer le rapport final
            logger.info("Étape 5: Génération du rapport d'optimisation")
            self._generate_final_report(report, analysis_result["analysis"], optimizations)
            
            # Marquer comme réussi
            report["success"] = True
            report["end_time"] = datetime.now().isoformat()
            report["duration"] = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Processus d'optimisation terminé avec succès en {report['duration']:.2f}s")
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors du processus d'optimisation: {str(e)}", exc_info=True)
            report["success"] = False
            report["error"] = str(e)
            report["end_time"] = datetime.now().isoformat()
            report["duration"] = (datetime.now() - start_time).total_seconds()
            return report
    
    async def _run_benchmarks(self) -> Dict[str, Any]:
        """
        Exécute les benchmarks du système OCR.
        
        Returns:
            Résultat des benchmarks
        """
        try:
            logger.info("Exécution des benchmarks OCR...")
            benchmark_result_dir = await run_ocr_benchmarks()
            
            # Copier les résultats dans notre répertoire de sortie
            if Path(benchmark_result_dir).exists():
                # Copier récursivement tout le contenu
                for item in Path(benchmark_result_dir).glob("**/*"):
                    if item.is_file():
                        rel_path = item.relative_to(benchmark_result_dir)
                        dest_path = self.benchmark_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_path)
                
            return {
                "success": True,
                "directory": self.benchmark_dir
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution des benchmarks: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_benchmarks(self, benchmark_dir: Path) -> Dict[str, Any]:
        """
        Analyse les résultats des benchmarks.
        
        Args:
            benchmark_dir: Répertoire contenant les résultats des benchmarks
            
        Returns:
            Résultats de l'analyse
        """
        try:
            logger.info(f"Analyse des benchmarks dans {benchmark_dir}...")
            analysis_result = self.analyzer.analyze_benchmarks(benchmark_dir)
            
            # Sauvegarder le résultat de l'analyse
            if analysis_result["success"]:
                with open(self.analysis_dir / "analysis_report.json", "w", encoding="utf-8") as f:
                    json.dump(analysis_result["analysis"], f, indent=2, ensure_ascii=False)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des benchmarks: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _identify_optimizations(self, bottlenecks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identifie les optimisations possibles à partir des goulots d'étranglement.
        
        Args:
            bottlenecks: Liste des goulots d'étranglement identifiés
            
        Returns:
            Liste des optimisations possibles
        """
        optimizations = []
        severity_levels = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        threshold_value = severity_levels.get(self.threshold_level, 2)
        
        logger.info(f"Identification des optimisations (seuil: {self.threshold_level})...")
        
        for bottleneck in bottlenecks:
            # Vérifier si ce goulot d'étranglement dépasse notre seuil
            bottleneck_severity = bottleneck.get("severity", "low")
            if severity_levels.get(bottleneck_severity, 3) > threshold_value:
                continue
                
            # Parcourir les optimisations proposées
            for opt in bottleneck.get("optimizations", []):
                optimizations.append({
                    "component": bottleneck.get("component"),
                    "metric": bottleneck.get("metric"),
                    "severity": bottleneck_severity,
                    "description": opt.get("description", ""),
                    "automated": opt.get("automated", False),
                    "code_change": opt.get("code_change"),
                    "file_path": bottleneck.get("file_path")
                })
        
        logger.info(f"Identifié {len(optimizations)} optimisations possibles ({sum(1 for o in optimizations if o['automated'])} automatisables)")
        
        # Sauvegarder la liste des optimisations
        with open(self.optimization_dir / "optimizations.json", "w", encoding="utf-8") as f:
            json.dump(optimizations, f, indent=2, ensure_ascii=False)
            
        return optimizations
    
    def _apply_optimizations(self, optimizations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Applique les optimisations automatisables.
        
        Args:
            optimizations: Liste des optimisations possibles
            
        Returns:
            Résultats de l'application des optimisations
        """
        results = []
        
        # Filtrer les optimisations automatisables
        auto_optimizations = [o for o in optimizations if o["automated"] and o["code_change"] and o["file_path"]]
        
        if not auto_optimizations:
            logger.info("Aucune optimisation automatisable trouvée")
            return results
            
        logger.info(f"Application de {len(auto_optimizations)} optimisations automatiques...")
        
        # Regrouper les optimisations par fichier
        optimizations_by_file = {}
        for opt in auto_optimizations:
            file_path = opt["file_path"]
            if file_path not in optimizations_by_file:
                optimizations_by_file[file_path] = []
            optimizations_by_file[file_path].append(opt)
        
        # Appliquer les optimisations pour chaque fichier
        for file_path, file_opts in optimizations_by_file.items():
            try:
                logger.info(f"Optimisation du fichier: {file_path}")
                
                # Convertir en liste d'optimisations pour l'optimiseur
                opt_list = []
                for opt in file_opts:
                    opt_list.append({
                        "description": opt["description"],
                        "code_change": opt["code_change"]
                    })
                
                # Appliquer les optimisations
                result = self.optimizer.optimize_file(Path(file_path), opt_list)
                
                # Enregistrer le résultat
                results.append({
                    "file": file_path,
                    "success": result["success"],
                    "optimizations_count": len(file_opts),
                    "applied_count": len(result.get("applied_optimizations", [])) if result["success"] else 0,
                    "details": result
                })
                
            except Exception as e:
                logger.error(f"Erreur lors de l'optimisation du fichier {file_path}: {str(e)}", exc_info=True)
                results.append({
                    "file": file_path,
                    "success": False,
                    "error": str(e),
                    "optimizations_count": len(file_opts),
                    "applied_count": 0
                })
        
        # Sauvegarder les résultats
        with open(self.optimization_dir / "optimization_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        return results
    
    def _generate_final_report(self, main_report: Dict[str, Any], 
                            analysis: Dict[str, Any], 
                            optimizations: List[Dict[str, Any]]) -> None:
        """
        Génère le rapport final d'optimisation.
        
        Args:
            main_report: Rapport principal du processus
            analysis: Résultats de l'analyse
            optimizations: Liste des optimisations identifiées
        """
        # Générer un rapport JSON complet
        report = {
            **main_report,
            "analysis_summary": {
                "bottlenecks_count": len(analysis.get("bottlenecks", [])),
                "components_analyzed": analysis.get("components_analyzed", []),
                "recommendations": analysis.get("recommendations", {})
            },
            "optimizations_summary": {
                "total_count": len(optimizations),
                "automated_count": sum(1 for o in optimizations if o["automated"]),
                "manual_count": sum(1 for o in optimizations if not o["automated"]),
                "by_severity": {
                    "critical": sum(1 for o in optimizations if o["severity"] == "critical"),
                    "high": sum(1 for o in optimizations if o["severity"] == "high"),
                    "medium": sum(1 for o in optimizations if o["severity"] == "medium"),
                    "low": sum(1 for o in optimizations if o["severity"] == "low")
                },
                "by_metric": {
                    "duration": sum(1 for o in optimizations if o["metric"] == "duration"),
                    "memory_usage": sum(1 for o in optimizations if o["metric"] == "memory_usage"),
                    "cpu_usage": sum(1 for o in optimizations if o["metric"] == "cpu_usage")
                }
            }
        }
        
        # Sauvegarder le rapport final
        with open(self.output_dir / "optimization_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # Générer un rapport HTML plus lisible
        self._generate_html_report(report, analysis, optimizations)
        
        logger.info(f"Rapport final généré dans {self.output_dir}")
    
    def _generate_html_report(self, report: Dict[str, Any], 
                           analysis: Dict[str, Any], 
                           optimizations: List[Dict[str, Any]]) -> None:
        """
        Génère un rapport HTML pour une meilleure lisibilité.
        
        Args:
            report: Rapport principal du processus
            analysis: Résultats de l'analyse
            optimizations: Liste des optimisations identifiées
        """
        # Générer le contenu HTML
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Rapport d'optimisation - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .card {{ background-color: #f9f9f9; border-radius: 5px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .warning {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .metrics {{ display: flex; flex-wrap: wrap; }}
        .metric-card {{ flex: 1; min-width: 250px; margin: 10px; padding: 15px; border-radius: 5px; background-color: #f0f7ff; }}
        .critical {{ background-color: #ffdddd; }}
        .high {{ background-color: #ffe0cc; }}
        .medium {{ background-color: #fff6cc; }}
        .low {{ background-color: #e8f5e9; }}
    </style>
</head>
<body>
    <h1>Rapport d'optimisation du système OCR</h1>
    <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>Durée totale:</strong> {report.get('duration', 0):.2f} secondes</p>
    <p><strong>Statut:</strong> <span class="{'success' if report.get('success', False) else 'failure'}">
        {'Succès' if report.get('success', False) else 'Échec'}
    </span></p>
    
    <div class="card">
        <h2>Résumé des résultats</h2>
        <div class="metrics">
            <div class="metric-card">
                <h3>Analyse des benchmarks</h3>
                <p><strong>Composants analysés:</strong> {len(analysis.get('components_analyzed', []))}</p>
                <p><strong>Goulots d'étranglement:</strong> {len(analysis.get('bottlenecks', []))}</p>
            </div>
            <div class="metric-card">
                <h3>Optimisations identifiées</h3>
                <p><strong>Total:</strong> {len(optimizations)}</p>
                <p><strong>Automatisables:</strong> {sum(1 for o in optimizations if o['automated'])}</p>
                <p><strong>Manuelles:</strong> {sum(1 for o in optimizations if not o['automated'])}</p>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>Goulots d'étranglement par sévérité</h2>
        <table>
            <tr>
                <th>Sévérité</th>
                <th>Nombre</th>
            </tr>
            <tr class="critical">
                <td>Critique</td>
                <td>{sum(1 for b in analysis.get('bottlenecks', []) if b.get('severity') == 'critical')}</td>
            </tr>
            <tr class="high">
                <td>Élevée</td>
                <td>{sum(1 for b in analysis.get('bottlenecks', []) if b.get('severity') == 'high')}</td>
            </tr>
            <tr class="medium">
                <td>Moyenne</td>
                <td>{sum(1 for b in analysis.get('bottlenecks', []) if b.get('severity') == 'medium')}</td>
            </tr>
            <tr class="low">
                <td>Faible</td>
                <td>{sum(1 for b in analysis.get('bottlenecks', []) if b.get('severity') == 'low')}</td>
            </tr>
        </table>
    </div>
    
    <div class="card">
        <h2>Optimisations par type de métrique</h2>
        <table>
            <tr>
                <th>Métrique</th>
                <th>Nombre d'optimisations</th>
            </tr>
            <tr>
                <td>Temps d'exécution</td>
                <td>{sum(1 for o in optimizations if o['metric'] == 'duration')}</td>
            </tr>
            <tr>
                <td>Utilisation mémoire</td>
                <td>{sum(1 for o in optimizations if o['metric'] == 'memory_usage')}</td>
            </tr>
            <tr>
                <td>Utilisation CPU</td>
                <td>{sum(1 for o in optimizations if o['metric'] == 'cpu_usage')}</td>
            </tr>
        </table>
    </div>
    
    <div class="card">
        <h2>Détail des optimisations automatisables</h2>
        <table>
            <tr>
                <th>Composant</th>
                <th>Métrique</th>
                <th>Sévérité</th>
                <th>Description</th>
            </tr>
"""
        
        # Ajouter les optimisations automatisables
        for opt in sorted([o for o in optimizations if o["automated"]], 
                          key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[x["severity"]]):
            html_content += f"""
            <tr class="{opt['severity']}">
                <td>{opt['component']}</td>
                <td>{opt['metric']}</td>
                <td>{opt['severity'].capitalize()}</td>
                <td>{opt['description']}</td>
            </tr>"""
        
        # Si aucune optimisation automatisable
        if not any(o["automated"] for o in optimizations):
            html_content += """
            <tr>
                <td colspan="4" style="text-align: center;">Aucune optimisation automatisable identifiée</td>
            </tr>"""
            
        html_content += """
        </table>
    </div>
    
    <div class="card">
        <h2>Recommandations générales</h2>
        <ul>
"""
        
        # Ajouter les recommandations générales
        for rec in analysis.get("recommendations", {}).get("general", []):
            html_content += f"            <li>{rec}</li>\n"
            
        html_content += """
        </ul>
    </div>
    
    <footer>
        <p>Généré automatiquement par le système d'optimisation Technicia</p>
    </footer>
</body>
</html>
"""
        
        # Écrire le rapport HTML
        with open(self.output_dir / "optimization_report.html", "w", encoding="utf-8") as f:
            f.write(html_content)


async def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(description="Optimise le système OCR")
    
    parser.add_argument("--output-dir", type=str, help="Répertoire de sortie pour les résultats")
    parser.add_argument("--auto-apply", action="store_true", help="Appliquer automatiquement les optimisations")
    parser.add_argument("--threshold", type=str, default="high", 
                        choices=["critical", "high", "medium", "low"],
                        help="Seuil de sévérité pour les optimisations")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    
    args = parser.parse_args()
    
    # Configurer le niveau de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Créer et exécuter l'optimiseur
    optimizer = SystemOptimizer(
        output_dir=args.output_dir,
        auto_apply=args.auto_apply,
        threshold=args.threshold
    )
    
    result = await optimizer.run_full_optimization()
    
    # Afficher le résultat
    if result["success"]:
        print(f"Optimisation terminée avec succès. Rapport disponible dans: {optimizer.output_dir}")
        return 0
    else:
        print(f"Erreur lors de l'optimisation: {result.get('error', 'Erreur inconnue')}")
        return 1


if __name__ == "__main__":
    # Exécuter la fonction principale de manière asynchrone
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
