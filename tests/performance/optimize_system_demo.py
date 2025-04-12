"""
Script de démonstration du système d'optimisation des performances pour le POC Technicia
=====================================================================================

Cette version démo du système d'optimisation simule le processus complet
sans nécessiter les dépendances du projet, afin de démontrer le fonctionnement
et générer des rapports illustratifs.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import sys
import json
import logging
import argparse
import time
import random
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("optimization_demo_log.txt")
    ]
)
logger = logging.getLogger(__name__)

# Répertoire racine du projet
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Liste des composants simulés
COMPONENTS = [
    "orchestration", 
    "chunking", 
    "validation", 
    "table_extractor", 
    "schema_analyzer", 
    "formula_processor"
]

# Types de documents simulés
DOCUMENT_TYPES = [
    "texte_simple", 
    "document_technique", 
    "schema_complexe", 
    "tableau_donnees", 
    "formules_mathematiques"
]

# Classe simulant un goulot d'étranglement de performance
class PerformanceBottleneck:
    """Simulation d'un goulot d'étranglement de performance."""
    
    def __init__(self, component, metric, value, threshold, severity, file_path=None):
        self.component = component
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.severity = severity
        self.file_path = file_path
        self.optimizations = []
        
    def add_optimization(self, description, automated=False, code_change=None):
        """Ajoute une optimisation potentielle."""
        self.optimizations.append({
            "description": description,
            "automated": automated,
            "code_change": code_change
        })
        
    def to_dict(self):
        """Convertit l'objet en dictionnaire."""
        return {
            "component": self.component,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
            "file_path": str(self.file_path) if self.file_path else None,
            "optimizations": self.optimizations
        }


class BenchmarkDemoRunner:
    """Simule l'exécution des benchmarks pour la démonstration."""
    
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def run_benchmarks(self):
        """Simule l'exécution des benchmarks et génère des données synthétiques."""
        logger.info("Exécution des benchmarks de démonstration...")
        
        # Simuler un délai d'exécution
        for i in range(5):
            logger.info(f"Benchmark en cours... {i+1}/5")
            await asyncio.sleep(0.5)
            
        # Créer des données de benchmark synthétiques
        data = []
        
        for component in COMPONENTS:
            for doc_type in DOCUMENT_TYPES:
                # Générer des métriques aléatoires pour chaque combinaison
                num_tests = random.randint(3, 8)
                
                for i in range(num_tests):
                    # Des valeurs plus élevées pour certains composants pour simuler des problèmes
                    duration_factor = 1.5 if component in ["schema_analyzer", "formula_processor"] else 1.0
                    memory_factor = 2.0 if component == "orchestration" else 1.0
                    cpu_factor = 1.2 if component == "validation" else 1.0
                    
                    data.append({
                        "component": component,
                        "document_type": doc_type,
                        "test_id": f"test_{i+1}",
                        "duration": random.uniform(0.5, 12.0) * duration_factor,
                        "memory_usage_mean": random.uniform(30, 600) * memory_factor,
                        "memory_usage_peak": random.uniform(50, 800) * memory_factor,
                        "cpu_usage_mean": random.uniform(20, 95) * cpu_factor,
                        "cpu_usage_peak": random.uniform(30, 100) * cpu_factor,
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Créer le répertoire de visualisations
        viz_dir = self.output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        # Sauvegarder les données dans un fichier CSV
        import pandas as pd
        df = pd.DataFrame(data)
        df.to_csv(viz_dir / "benchmark_data.csv", index=False)
        
        # Générer quelques visualisations simulées
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Graphique des durées moyennes par composant
            plt.figure(figsize=(10, 6))
            duration_by_component = df.groupby("component")["duration"].mean().sort_values(ascending=False)
            plt.bar(duration_by_component.index, duration_by_component.values)
            plt.title("Durée moyenne d'exécution par composant")
            plt.ylabel("Durée (secondes)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(viz_dir / "duration_by_component.png")
            plt.close()
            
            # Graphique d'utilisation de la mémoire
            plt.figure(figsize=(10, 6))
            memory_by_component = df.groupby("component")["memory_usage_mean"].mean().sort_values(ascending=False)
            plt.bar(memory_by_component.index, memory_by_component.values)
            plt.title("Utilisation moyenne de la mémoire par composant")
            plt.ylabel("Mémoire (MB)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(viz_dir / "memory_by_component.png")
            plt.close()
            
            # Graphique d'utilisation du CPU
            plt.figure(figsize=(10, 6))
            cpu_by_component = df.groupby("component")["cpu_usage_mean"].mean().sort_values(ascending=False)
            plt.bar(cpu_by_component.index, cpu_by_component.values)
            plt.title("Utilisation moyenne du CPU par composant")
            plt.ylabel("CPU (%)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(viz_dir / "cpu_by_component.png")
            plt.close()
            
            # Heatmap des performances par type de document
            plt.figure(figsize=(12, 8))
            pivot_data = df.pivot_table(
                values="duration", 
                index="component", 
                columns="document_type", 
                aggfunc="mean"
            )
            import seaborn as sns
            sns.heatmap(pivot_data, annot=True, cmap="YlOrRd", fmt=".2f")
            plt.title("Durée d'exécution par composant et type de document")
            plt.tight_layout()
            plt.savefig(viz_dir / "performance_heatmap.png")
            plt.close()
            
            logger.info(f"Visualisations générées dans {viz_dir}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des visualisations: {str(e)}")
        
        logger.info(f"Benchmarks terminés. Données disponibles dans {self.output_dir}")
        return {"success": True, "directory": self.output_dir}


class AnalyzerDemo:
    """Simule l'analyse des benchmarks pour la démonstration."""
    
    def __init__(self):
        # Seuils simulés
        self.thresholds = {
            "duration": {
                "critical": 10.0,
                "high": 5.0,
                "medium": 2.0,
                "low": 1.0
            },
            "memory_usage": {
                "critical": 500,
                "high": 200,
                "medium": 100,
                "low": 50
            },
            "cpu_usage": {
                "critical": 90,
                "high": 70,
                "medium": 50,
                "low": 30
            }
        }
        
    def analyze_benchmarks(self, benchmark_dir):
        """Simule l'analyse des benchmarks et génère des résultats synthétiques."""
        logger.info(f"Analyse des benchmarks dans {benchmark_dir}...")
        
        try:
            # Charger les données de benchmark
            import pandas as pd
            csv_file = benchmark_dir / "visualizations" / "benchmark_data.csv"
            if not csv_file.exists():
                raise FileNotFoundError(f"Fichier de données introuvable: {csv_file}")
                
            df = pd.read_csv(csv_file)
            
            # Analyser les données et créer des bottlenecks simulés
            bottlenecks = []
            component_metrics = {}
            
            for component in COMPONENTS:
                component_data = df[df["component"] == component]
                
                if component_data.empty:
                    continue
                    
                # Calculer les métriques
                metrics = {
                    "duration": {
                        "min": component_data["duration"].min(),
                        "max": component_data["duration"].max(),
                        "mean": component_data["duration"].mean(),
                        "median": component_data["duration"].median()
                    },
                    "memory_usage": {
                        "min": component_data["memory_usage_mean"].min(),
                        "max": component_data["memory_usage_mean"].max(),
                        "mean": component_data["memory_usage_mean"].mean(),
                        "median": component_data["memory_usage_mean"].median()
                    },
                    "cpu_usage": {
                        "min": component_data["cpu_usage_mean"].min(),
                        "max": component_data["cpu_usage_mean"].max(),
                        "mean": component_data["cpu_usage_mean"].mean(),
                        "median": component_data["cpu_usage_mean"].median()
                    }
                }
                component_metrics[component] = metrics
                
                # Identifier les bottlenecks
                for metric_name, metric_data in metrics.items():
                    max_value = metric_data["max"]
                    
                    # Déterminer la sévérité
                    severity = "low"
                    threshold = 0
                    
                    for level, threshold_value in self.thresholds[metric_name].items():
                        if max_value >= threshold_value:
                            severity = level
                            threshold = threshold_value
                            break
                            
                    # Ne créer un bottleneck que si la sévérité est au moins moyenne
                    if severity in ["medium", "high", "critical"]:
                        # Simuler un chemin de fichier pour le composant
                        file_path = PROJECT_ROOT / "app" / "core" / "file_processing" / f"{component}.py"
                        
                        bottleneck = PerformanceBottleneck(
                            component=component,
                            metric=metric_name,
                            value=max_value,
                            threshold=threshold,
                            severity=severity,
                            file_path=file_path
                        )
                        
                        # Ajouter des optimisations simulées
                        self._add_simulated_optimizations(bottleneck)
                        bottlenecks.append(bottleneck)
            
            # Créer le répertoire d'analyse
            analysis_dir = benchmark_dir.parent / "analysis"
            analysis_dir.mkdir(exist_ok=True)
            
            # Générer des visualisations d'analyse
            try:
                import matplotlib.pyplot as plt
                import numpy as np
                import seaborn as sns
                
                # Graphique des bottlenecks par sévérité
                plt.figure(figsize=(10, 6))
                severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                for b in bottlenecks:
                    severity_counts[b.severity] += 1
                
                colors = {"critical": "darkred", "high": "red", "medium": "orange", "low": "yellow"}
                plt.bar(severity_counts.keys(), severity_counts.values(), color=[colors[s] for s in severity_counts.keys()])
                plt.title("Répartition des goulots d'étranglement par sévérité")
                plt.ylabel("Nombre de goulots d'étranglement")
                plt.savefig(analysis_dir / "bottlenecks_by_severity.png")
                plt.close()
                
                # Graphique des métriques par composant
                for metric in ["duration", "memory_usage", "cpu_usage"]:
                    plt.figure(figsize=(12, 6))
                    components = []
                    values = []
                    colors = []
                    
                    for component, metrics in component_metrics.items():
                        if metric in metrics:
                            components.append(component)
                            values.append(metrics[metric]["max"])
                            
                            # Déterminer la sévérité
                            severity = "low"
                            for level, threshold in self.thresholds[metric].items():
                                if metrics[metric]["max"] >= threshold:
                                    severity = level
                                    break
                                    
                            colors.append({"critical": "darkred", "high": "red", "medium": "orange", "low": "yellow"}[severity])
                    
                    if components:
                        # Trier par valeur
                        idx = np.argsort(values)[::-1]
                        plt.bar([components[i] for i in idx], [values[i] for i in idx], color=[colors[i] for i in idx])
                        plt.title(f"{metric.capitalize()} par composant")
                        plt.ylabel(metric)
                        plt.xticks(rotation=45, ha="right")
                        plt.tight_layout()
                        plt.savefig(analysis_dir / f"{metric}_by_component.png")
                        plt.close()
                
                logger.info(f"Visualisations d'analyse générées dans {analysis_dir}")
                
            except Exception as e:
                logger.error(f"Erreur lors de la génération des visualisations d'analyse: {str(e)}")
            
            # Générer le rapport d'analyse
            recommendations = self._generate_recommendations(bottlenecks)
            
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "benchmark_dir": str(benchmark_dir),
                "components_analyzed": list(set(df["component"])),
                "bottlenecks": [b.to_dict() for b in bottlenecks],
                "component_metrics": component_metrics,
                "recommendations": recommendations
            }
            
            # Sauvegarder le rapport
            with open(analysis_dir / "analysis_report.json", "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Analyse terminée. Rapport disponible dans {analysis_dir}")
            return {"success": True, "analysis": analysis}
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des benchmarks: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _add_simulated_optimizations(self, bottleneck):
        """Ajoute des optimisations simulées à un goulot d'étranglement."""
        if bottleneck.metric == "duration":
            bottleneck.add_optimization(
                description="Optimiser les boucles imbriquées en réduisant la complexité algorithmique",
                automated=False
            )
            bottleneck.add_optimization(
                description="Utiliser du caching pour éviter les calculs répétés",
                automated=True,
                code_change={
                    "type": "add_cache",
                    "line": 42,
                    "original": "result = expensive_calculation(input_data)",
                    "new": "@lru_cache(maxsize=128)\ndef cached_calculation(input_data):\n    return expensive_calculation(input_data)\n\nresult = cached_calculation(input_data)"
                }
            )
            
        elif bottleneck.metric == "memory_usage":
            bottleneck.add_optimization(
                description="Utiliser des générateurs au lieu de listes pour les grandes collections",
                automated=True,
                code_change={
                    "type": "list_to_generator",
                    "line": 78,
                    "original": "results = [process(item) for item in large_collection]",
                    "new": "results = (process(item) for item in large_collection)"
                }
            )
            bottleneck.add_optimization(
                description="Implémenter une stratégie de chargement paresseux (lazy loading)",
                automated=False
            )
            
        elif bottleneck.metric == "cpu_usage":
            bottleneck.add_optimization(
                description="Utiliser des bibliothèques optimisées comme NumPy pour les opérations intensives",
                automated=False
            )
            bottleneck.add_optimization(
                description="Considérer l'utilisation du multiprocessing pour les tâches parallélisables",
                automated=False
            )
    
    def _generate_recommendations(self, bottlenecks):
        """Génère des recommandations basées sur les goulots d'étranglement identifiés."""
        recommendations = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        # Grouper les recommandations par sévérité
        for bottleneck in bottlenecks:
            for opt in bottleneck.optimizations:
                recommendations[bottleneck.severity].append({
                    "component": bottleneck.component,
                    "metric": bottleneck.metric,
                    "description": opt["description"],
                    "automated": opt["automated"]
                })
        
        # Recommandations générales
        if any(b.severity in ["critical", "high"] for b in bottlenecks):
            recommendations["general"] = [
                "Revoir l'architecture des composants critiques identifiés",
                "Optimiser en priorité les processeurs spécialisés qui consomment le plus de ressources",
                "Envisager l'utilisation de caching pour les opérations répétées",
                "Évaluer les stratégies de mise à l'échelle horizontale pour les charges importantes"
            ]
        else:
            recommendations["general"] = [
                "Les performances sont généralement acceptables",
                "Continuer le monitoring régulier des performances",
                "Optimiser progressivement les composants identifiés"
            ]
            
        return recommendations


class OptimizerDemo:
    """Simule l'optimisation du code pour la démonstration."""
    
    def optimize_file(self, file_path, optimizations):
        """Simule l'optimisation d'un fichier de code."""
        logger.info(f"Optimisation du fichier: {file_path}")
        
        # Simuler un délai pour l'optimisation
        time.sleep(0.5)
        
        # Résultats simulés
        applied_optimizations = []
        
        for i, opt in enumerate(optimizations):
            # Simuler que 70% des optimisations sont appliquées avec succès
            if random.random() < 0.7:
                applied_optimizations.append({
                    "id": i + 1,
                    "description": opt["description"],
                    "successful": True,
                    "line": random.randint(10, 200) if "code_change" not in opt else opt["code_change"].get("line", 0)
                })
            else:
                applied_optimizations.append({
                    "id": i + 1,
                    "description": opt["description"],
                    "successful": False,
                    "error": "Contexte de code incompatible avec l'optimisation automatique"
                })
        
        return {
            "success": True,
            "file": str(file_path),
            "applied_optimizations": applied_optimizations,
            "total_optimizations": len(optimizations),
            "successful_optimizations": sum(1 for opt in applied_optimizations if opt["successful"])
        }


class SystemOptimizerDemo:
    """
    Classe qui orchestre le processus complet d'optimisation du système OCR.
    Version de démonstration qui simule les étapes sans dépendances réelles.
    """
    
    def __init__(self, output_dir=None, auto_apply=False, threshold="high"):
        """
        Initialise l'optimiseur de démonstration.
        
        Args:
            output_dir: Répertoire de sortie pour les résultats (par défaut: timestamp dans "optimization_results")
            auto_apply: Si True, simule l'application automatique des optimisations
            threshold: Seuil de sévérité (critical, high, medium, low)
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
            
        # Initialiser les objets de démonstration
        self.benchmark_runner = BenchmarkDemoRunner(self.benchmark_dir)
        self.analyzer = AnalyzerDemo()
        self.optimizer = OptimizerDemo()
        
        logger.info(f"Optimiseur de démonstration initialisé. Résultats dans: {self.output_dir}")
        
    async def run_full_optimization(self):
        """
        Exécute l'ensemble du processus d'optimisation simulé:
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
            logger.info("Étape 1: Exécution des benchmarks de démonstration")
            benchmark_result = await self.benchmark_runner.run_benchmarks()
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
            analysis_result = self.analyzer.analyze_benchmarks(benchmark_result["directory"])
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
                logger.info("Étape 4: Simulation de l'application des optimisations automatiques")
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
    
    def _identify_optimizations(self, bottlenecks):
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
    
    def _apply_optimizations(self, optimizations):
        """
        Simule l'application des optimisations automatisables.
        
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
            
        logger.info(f"Simulation de l'application de {len(auto_optimizations)} optimisations automatiques...")
        
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
                
                # Simuler l'application des optimisations
                result = self.optimizer.optimize_file(file_path, opt_list)
                
                # Enregistrer le résultat
                results.append({
                    "file": file_path,
                    "success": result["success"],
                    "optimizations_count": len(file_opts),
                    "applied_count": result["successful_optimizations"],
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
    
    def _generate_final_report(self, main_report, analysis, optimizations):
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
    
    def _generate_html_report(self, report, analysis, optimizations):
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
    <title>Rapport d'optimisation (DÉMO) - {datetime.now().strftime('%Y-%m-%d')}</title>
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
        .demo-notice {{ background-color: #e8f5f2; border-left: 5px solid #00796b; padding: 10px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>Rapport d'optimisation du système OCR (Version de démonstration)</h1>
    
    <div class="demo-notice">
        <p><strong>Note:</strong> Ce rapport est généré par une version de démonstration du système d'optimisation. 
        Les données présentées sont simulées à des fins d'illustration.</p>
    </div>
    
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
        <p>Généré automatiquement par le système d'optimisation Technicia (Version DÉMO)</p>
    </footer>
</body>
</html>
"""
        
        # Écrire le rapport HTML
        with open(self.output_dir / "optimization_report.html", "w", encoding="utf-8") as f:
            f.write(html_content)


async def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(description="Démonstration du système d'optimisation OCR")
    
    parser.add_argument("--output-dir", type=str, help="Répertoire de sortie pour les résultats")
    parser.add_argument("--auto-apply", action="store_true", help="Simuler l'application automatique des optimisations")
    parser.add_argument("--threshold", type=str, default="high", 
                        choices=["critical", "high", "medium", "low"],
                        help="Seuil de sévérité pour les optimisations")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    
    args = parser.parse_args()
    
    # Configurer le niveau de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("=== DÉMONSTRATION DU SYSTÈME D'OPTIMISATION DES PERFORMANCES ===")
    print("Cette version simule le processus d'optimisation avec des données synthétiques")
    print("pour illustrer le fonctionnement du système.")
    print("-" * 70)
    
    # Créer et exécuter l'optimiseur
    optimizer = SystemOptimizerDemo(
        output_dir=args.output_dir,
        auto_apply=args.auto_apply,
        threshold=args.threshold
    )
    
    print(f"Résultats dans: {optimizer.output_dir}")
    print("Exécution du processus d'optimisation...")
    
    result = await optimizer.run_full_optimization()
    
    # Afficher le résultat
    if result["success"]:
        print("\n✅ Optimisation terminée avec succès.")
        print(f"📊 Nombre de goulots d'étranglement identifiés: {result['steps']['analysis'].get('bottlenecks_count', 0)}")
        print(f"🔧 Nombre d'optimisations identifiées: {result['steps']['optimizations'].get('total_count', 0)}")
        print(f"📑 Rapport complet disponible dans: {optimizer.output_dir / 'optimization_report.html'}")
        return 0
    else:
        print(f"\n❌ Erreur lors de l'optimisation: {result.get('error', 'Erreur inconnue')}")
        return 1


if __name__ == "__main__":
    # Exécuter la fonction principale de manière asynchrone
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
