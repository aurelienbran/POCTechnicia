"""
Analyseur de benchmarks pour le POC Technicia
=============================================

Ce module analyse les résultats des benchmarks pour identifier les goulots 
d'étranglement de performance et générer des recommandations d'optimisation.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime

from .performance_optimizer import PerformanceBottleneck, CodeOptimizer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Seuils de performance pour différentes métriques
THRESHOLDS = {
    "duration": {
        "critical": 10.0,   # secondes
        "high": 5.0,
        "medium": 2.0,
        "low": 1.0
    },
    "memory_usage": {
        "critical": 500,    # MB
        "high": 200,
        "medium": 100,
        "low": 50
    },
    "cpu_usage": {
        "critical": 90,     # %
        "high": 70,
        "medium": 50,
        "low": 30
    }
}

# Mapping des composants aux fichiers source
COMPONENT_TO_FILE = {
    "orchestration": "app/core/file_processing/orchestration/orchestrator.py",
    "chunking": "app/core/file_processing/chunking/relational_chunker.py",
    "validation": "app/core/file_processing/validation/low_confidence_detector.py",
    "table_extractor": "app/core/file_processing/specialized_processors/table_extractor.py",
    "schema_analyzer": "app/core/file_processing/specialized_processors/schema_analyzer.py",
    "formula_processor": "app/core/file_processing/specialized_processors/formula_processor.py"
}


class BenchmarkAnalyzer:
    """
    Classe pour analyser les résultats des benchmarks et identifier les goulots d'étranglement.
    """
    
    def __init__(self, project_root: Path, thresholds: Dict[str, Dict[str, float]] = None):
        """
        Initialise un nouvel analyseur de benchmarks.
        
        Args:
            project_root: Répertoire racine du projet
            thresholds: Seuils pour les différentes métriques
        """
        self.project_root = project_root
        self.thresholds = thresholds or THRESHOLDS
        self.optimizer = CodeOptimizer(project_root)
        
    def analyze_benchmarks(self, benchmark_dir: Path) -> Dict[str, Any]:
        """
        Analyse les résultats des benchmarks pour identifier les goulots d'étranglement.
        
        Args:
            benchmark_dir: Répertoire contenant les résultats des benchmarks
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse
        """
        logger.info(f"Analyse des benchmarks dans {benchmark_dir}")
        
        # Charger les données de benchmark
        try:
            benchmark_data = self._load_benchmark_data(benchmark_dir)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données de benchmark: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
        
        if not benchmark_data:
            return {"success": False, "error": "Aucune donnée de benchmark trouvée"}
        
        # Analyser les performances par composant
        bottlenecks = []
        component_metrics = {}
        
        for component, data in benchmark_data.items():
            component_metrics[component] = self._analyze_component_metrics(component, data)
            bottlenecks.extend(self._identify_bottlenecks(component, component_metrics[component]))
        
        # Trier les goulots d'étranglement par sévérité
        bottlenecks.sort(key=lambda b: {"critical": 0, "high": 1, "medium": 2, "low": 3}[b.severity])
        
        # Générer des recommandations d'optimisation
        for bottleneck in bottlenecks:
            self._generate_optimizations(bottleneck)
        
        # Préparer le rapport d'analyse
        analysis_report = {
            "timestamp": datetime.now().isoformat(),
            "benchmark_dir": str(benchmark_dir),
            "components_analyzed": list(benchmark_data.keys()),
            "bottlenecks": [b.to_dict() for b in bottlenecks],
            "component_metrics": component_metrics,
            "recommendations": self._generate_recommendations(bottlenecks)
        }
        
        # Générer des visualisations
        self._generate_visualizations(benchmark_dir, bottlenecks, component_metrics)
        
        return {"success": True, "analysis": analysis_report}
    
    def _load_benchmark_data(self, benchmark_dir: Path) -> Dict[str, pd.DataFrame]:
        """
        Charge les données de benchmark à partir des fichiers CSV.
        
        Args:
            benchmark_dir: Répertoire contenant les résultats des benchmarks
            
        Returns:
            Dictionnaire avec les données de benchmark par composant
        """
        # Rechercher le fichier CSV de données de benchmark
        csv_files = list(benchmark_dir.glob("**/benchmark_data.csv"))
        if not csv_files:
            csv_files = list(benchmark_dir.glob("**/visualizations/benchmark_data.csv"))
            
        if not csv_files:
            raise FileNotFoundError("Aucun fichier de données de benchmark trouvé")
            
        # Charger les données
        data = pd.read_csv(csv_files[0])
        
        # Regrouper par composant
        component_data = {}
        for component in data["component"].unique():
            component_data[component] = data[data["component"] == component].copy()
            
        return component_data
    
    def _analyze_component_metrics(self, component: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyse les métriques d'un composant spécifique.
        
        Args:
            component: Nom du composant
            data: DataFrame contenant les données de benchmark pour ce composant
            
        Returns:
            Dictionnaire avec les statistiques des métriques
        """
        metrics = {}
        
        # Analyser chaque métrique
        for metric in ["duration", "memory_usage_mean", "cpu_usage_mean"]:
            if metric in data.columns:
                clean_metric = metric.replace("_mean", "")
                metrics[clean_metric] = {
                    "min": data[metric].min(),
                    "max": data[metric].max(),
                    "mean": data[metric].mean(),
                    "median": data[metric].median(),
                    "std": data[metric].std(),
                    "count": len(data)
                }
        
        # Analyser par type de document
        if "document_type" in data.columns:
            metrics["by_document_type"] = {}
            for doc_type in data["document_type"].unique():
                doc_data = data[data["document_type"] == doc_type]
                metrics["by_document_type"][doc_type] = {
                    "duration": doc_data["duration"].mean() if "duration" in doc_data else None,
                    "memory": doc_data["memory_usage_mean"].mean() if "memory_usage_mean" in doc_data else None,
                    "cpu": doc_data["cpu_usage_mean"].mean() if "cpu_usage_mean" in doc_data else None
                }
        
        # Analyser par configuration
        if "config_name" in data.columns:
            metrics["by_config"] = {}
            for config in data["config_name"].unique():
                config_data = data[data["config_name"] == config]
                metrics["by_config"][config] = {
                    "duration": config_data["duration"].mean() if "duration" in config_data else None,
                    "memory": config_data["memory_usage_mean"].mean() if "memory_usage_mean" in config_data else None,
                    "cpu": config_data["cpu_usage_mean"].mean() if "cpu_usage_mean" in config_data else None
                }
        
        return metrics
    
    def _identify_bottlenecks(self, component: str, metrics: Dict[str, Any]) -> List[PerformanceBottleneck]:
        """
        Identifie les goulots d'étranglement pour un composant.
        
        Args:
            component: Nom du composant
            metrics: Métriques du composant
            
        Returns:
            Liste de goulots d'étranglement identifiés
        """
        bottlenecks = []
        
        # Vérifier chaque métrique principale
        for metric in ["duration", "memory_usage", "cpu_usage"]:
            if metric in metrics:
                value = metrics[metric]["max"]  # Utiliser la valeur maximale
                
                # Déterminer la sévérité
                severity = "low"
                threshold = 0
                
                for level, threshold_value in self.thresholds[metric].items():
                    if value >= threshold_value:
                        severity = level
                        threshold = threshold_value
                        break
                
                # Ne créer un bottleneck que si la sévérité est au moins moyenne
                if severity in ["medium", "high", "critical"]:
                    # Trouver le fichier source correspondant
                    file_path = self.project_root / COMPONENT_TO_FILE.get(component, "")
                    if not file_path.exists():
                        file_path = None
                    
                    bottleneck = PerformanceBottleneck(
                        component=component,
                        metric=metric,
                        value=value,
                        threshold=threshold,
                        severity=severity,
                        file_path=file_path
                    )
                    
                    bottlenecks.append(bottleneck)
        
        return bottlenecks
    
    def _generate_optimizations(self, bottleneck: PerformanceBottleneck) -> None:
        """
        Génère des optimisations potentielles pour un goulot d'étranglement.
        
        Args:
            bottleneck: Goulot d'étranglement à optimiser
        """
        if not bottleneck.file_path or not bottleneck.file_path.exists():
            # Pas de fichier source disponible
            bottleneck.add_optimization(
                description="Analyse du code source impossible: fichier non trouvé",
                automated=False
            )
            return
        
        # Analyser le fichier source
        analysis_result = self.optimizer.analyze_file(bottleneck.file_path)
        
        if not analysis_result["success"]:
            bottleneck.add_optimization(
                description=f"Erreur lors de l'analyse du code: {analysis_result.get('error')}",
                automated=False
            )
            return
        
        analysis = analysis_result["analysis"]
        
        # Ajouter des optimisations en fonction de la métrique
        if bottleneck.metric == "duration":
            # Optimisations pour le temps d'exécution
            for opt in analysis.get("potential_optimizations", []):
                if opt["type"] in ["nested_loops", "nested_comprehension"]:
                    bottleneck.add_optimization(
                        description=f"Optimiser les boucles imbriquées à la ligne {opt['line']}: {opt['suggestion']}",
                        automated=False
                    )
                elif opt["type"] == "repeated_call":
                    bottleneck.add_optimization(
                        description=f"Optimiser l'appel répété à {opt['function']} à la ligne {opt['line']}: {opt['suggestion']}",
                        automated=False
                    )
            
            # Suggestions générales
            bottleneck.add_optimization(
                description="Envisager l'utilisation de caching pour les opérations répétées",
                automated=False
            )
            
            bottleneck.add_optimization(
                description="Évaluer l'utilisation de traitement parallèle ou asynchrone",
                automated=False
            )
            
        elif bottleneck.metric == "memory_usage":
            # Optimisations pour l'utilisation mémoire
            for opt in analysis.get("potential_optimizations", []):
                if opt["type"] == "list_comprehension":
                    bottleneck.add_optimization(
                        description=f"Utiliser des générateurs au lieu de listes en compréhension à la ligne {opt['line']}",
                        automated=True,
                        code_change=opt["code_change"]
                    )
            
            # Suggestions générales
            bottleneck.add_optimization(
                description="Envisager l'utilisation de lazy loading pour les ressources volumineuses",
                automated=False
            )
            
            bottleneck.add_optimization(
                description="Vérifier la libération des ressources (garbage collection)",
                automated=False
            )
            
        elif bottleneck.metric == "cpu_usage":
            # Suggestions pour l'utilisation CPU
            bottleneck.add_optimization(
                description="Optimiser les algorithmes de traitement intensif",
                automated=False
            )
            
            bottleneck.add_optimization(
                description="Évaluer la possibilité d'utiliser des bibliothèques optimisées (numpy, numba)",
                automated=False
            )
    
    def _generate_recommendations(self, bottlenecks: List[PerformanceBottleneck]) -> Dict[str, Any]:
        """
        Génère des recommandations globales d'optimisation.
        
        Args:
            bottlenecks: Liste des goulots d'étranglement identifiés
            
        Returns:
            Dictionnaire avec les recommandations d'optimisation
        """
        recommendations = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        # Regrouper les recommandations par sévérité
        for bottleneck in bottlenecks:
            for opt in bottleneck.optimizations:
                recommendations[bottleneck.severity].append({
                    "component": bottleneck.component,
                    "metric": bottleneck.metric,
                    "value": bottleneck.value,
                    "description": opt["description"],
                    "automated": opt["automated"]
                })
        
        # Ajouter des recommandations générales
        if any(b.severity in ["critical", "high"] for b in bottlenecks):
            recommendations["general"] = [
                "Réviser l'architecture pour les composants critiques identifiés",
                "Envisager l'optimisation des requêtes de base de données",
                "Évaluer les stratégies de mise en cache",
                "Considérer la mise à l'échelle horizontale pour les charges importantes"
            ]
        else:
            recommendations["general"] = [
                "Les performances sont généralement acceptables",
                "Continuer le monitoring régulier des performances",
                "Optimiser progressivement les composants identifiés"
            ]
        
        return recommendations
    
    def _generate_visualizations(self, benchmark_dir: Path, bottlenecks: List[PerformanceBottleneck],
                               component_metrics: Dict[str, Dict[str, Any]]) -> None:
        """
        Génère des visualisations pour les résultats d'analyse.
        
        Args:
            benchmark_dir: Répertoire contenant les résultats des benchmarks
            bottlenecks: Liste des goulots d'étranglement identifiés
            component_metrics: Métriques par composant
        """
        # Créer un répertoire pour les visualisations
        viz_dir = benchmark_dir / "analysis"
        viz_dir.mkdir(exist_ok=True)
        
        # 1. Graphique des goulots d'étranglement par sévérité
        plt.figure(figsize=(10, 6))
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for b in bottlenecks:
            severity_counts[b.severity] += 1
        
        colors = {"critical": "darkred", "high": "red", "medium": "orange", "low": "yellow"}
        plt.bar(severity_counts.keys(), severity_counts.values(), color=[colors[s] for s in severity_counts.keys()])
        plt.title("Répartition des goulots d'étranglement par sévérité")
        plt.ylabel("Nombre de goulots d'étranglement")
        plt.savefig(viz_dir / "bottlenecks_by_severity.png")
        plt.close()
        
        # 2. Graphique des métriques par composant
        metrics_to_plot = ["duration", "memory_usage", "cpu_usage"]
        for metric in metrics_to_plot:
            plt.figure(figsize=(12, 6))
            components = []
            values = []
            thresholds = []
            colors = []
            
            for component, metrics in component_metrics.items():
                if metric in metrics:
                    components.append(component)
                    values.append(metrics[metric]["max"])
                    
                    # Déterminer le seuil correspondant
                    threshold = 0
                    severity = "low"
                    for level, threshold_value in self.thresholds[metric].items():
                        if metrics[metric]["max"] >= threshold_value:
                            severity = level
                            threshold = threshold_value
                            break
                    
                    thresholds.append(threshold)
                    colors.append({"critical": "darkred", "high": "red", "medium": "orange", "low": "yellow"}[severity])
            
            if components:
                # Trier par valeur décroissante
                sorted_indices = np.argsort(values)[::-1]
                plt.bar(
                    [components[i] for i in sorted_indices],
                    [values[i] for i in sorted_indices],
                    color=[colors[i] for i in sorted_indices]
                )
                
                # Ajouter une ligne pour le seuil critique
                if metric in self.thresholds:
                    plt.axhline(y=self.thresholds[metric]["critical"], color='r', linestyle='-', label="Seuil critique")
                    plt.axhline(y=self.thresholds[metric]["high"], color='orange', linestyle='-', label="Seuil élevé")
                
                plt.title(f"{metric.capitalize()} par composant")
                plt.ylabel(metric)
                plt.xticks(rotation=45, ha="right")
                plt.legend()
                plt.tight_layout()
                plt.savefig(viz_dir / f"{metric}_by_component.png")
                plt.close()
        
        # 3. Résumé des optimisations
        plt.figure(figsize=(10, 6))
        automated_counts = {
            "Automatisable": sum(1 for b in bottlenecks for opt in b.optimizations if opt["automated"]),
            "Manuel": sum(1 for b in bottlenecks for opt in b.optimizations if not opt["automated"])
        }
        
        plt.pie(automated_counts.values(), labels=automated_counts.keys(), autopct='%1.1f%%')
        plt.title("Répartition des optimisations automatisables vs. manuelles")
        plt.savefig(viz_dir / "optimizations_automation.png")
        plt.close()
        
        # Écrire le rapport JSON
        report = {
            "bottlenecks": [b.to_dict() for b in bottlenecks],
            "component_metrics": component_metrics,
            "thresholds": self.thresholds
        }
        
        with open(viz_dir / "analysis_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Visualisations générées dans {viz_dir}")


def analyze_benchmark_results(benchmark_dir: str, project_root: str = None) -> Dict[str, Any]:
    """
    Fonction principale pour analyser les résultats des benchmarks.
    
    Args:
        benchmark_dir: Répertoire contenant les résultats des benchmarks
        project_root: Répertoire racine du projet (optionnel)
        
    Returns:
        Résultats de l'analyse
    """
    benchmark_path = Path(benchmark_dir)
    if not benchmark_path.exists():
        return {"success": False, "error": f"Répertoire {benchmark_dir} non trouvé"}
    
    # Déterminer le répertoire racine du projet
    if project_root:
        project_path = Path(project_root)
    else:
        # Essayer de trouver automatiquement
        project_path = benchmark_path
        while project_path.name not in ["", "tests"] and project_path.parent != project_path:
            project_path = project_path.parent
        
        if project_path.name == "tests":
            project_path = project_path.parent
    
    analyzer = BenchmarkAnalyzer(project_path)
    results = analyzer.analyze_benchmarks(benchmark_path)
    
    return results


if __name__ == "__main__":
    # Exécution directe du script
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyse les résultats des benchmarks")
    parser.add_argument("benchmark_dir", help="Répertoire contenant les résultats des benchmarks")
    parser.add_argument("--project-root", help="Répertoire racine du projet")
    args = parser.parse_args()
    
    results = analyze_benchmark_results(args.benchmark_dir, args.project_root)
    
    if results["success"]:
        print("Analyse réussie !")
        print(f"Nombre de goulots d'étranglement identifiés: {len(results['analysis']['bottlenecks'])}")
    else:
        print(f"Erreur: {results['error']}")
