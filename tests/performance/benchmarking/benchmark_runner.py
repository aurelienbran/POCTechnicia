"""
Module d'exécution des benchmarks pour le POC Technicia
=======================================================

Ce module fournit les outils nécessaires pour exécuter des benchmarks sur les différents
composants du système OCR et RAG. Il permet de mesurer les performances, d'identifier
les goulots d'étranglement et de générer des rapports détaillés.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import time
import asyncio
import logging
import psutil
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from functools import wraps
import tempfile
import traceback
import gc
import statistics

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkMetric:
    """Classe pour stocker et calculer une métrique de benchmark."""
    
    def __init__(self, name: str, unit: str, description: str = ""):
        """
        Initialise une nouvelle métrique de benchmark.
        
        Args:
            name: Nom de la métrique
            unit: Unité de mesure (s, ms, MB, etc.)
            description: Description de la métrique
        """
        self.name = name
        self.unit = unit
        self.description = description
        self.values = []
        
    def add_value(self, value: float):
        """Ajoute une nouvelle valeur mesurée."""
        self.values.append(value)
        
    def get_statistics(self) -> Dict[str, float]:
        """Calcule les statistiques pour cette métrique."""
        if not self.values:
            return {
                "min": 0,
                "max": 0,
                "mean": 0,
                "median": 0,
                "stdev": 0,
                "p95": 0,
                "p99": 0,
                "count": 0
            }
            
        return {
            "min": min(self.values),
            "max": max(self.values),
            "mean": statistics.mean(self.values),
            "median": statistics.median(self.values),
            "stdev": statistics.stdev(self.values) if len(self.values) > 1 else 0,
            "p95": sorted(self.values)[int(0.95 * len(self.values) - 1)],
            "p99": sorted(self.values)[int(0.99 * len(self.values) - 1)],
            "count": len(self.values)
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la métrique en dictionnaire."""
        return {
            "name": self.name,
            "unit": self.unit,
            "description": self.description,
            "statistics": self.get_statistics(),
            "values": self.values
        }


class BenchmarkResult:
    """Classe pour stocker les résultats d'un benchmark."""
    
    def __init__(self, name: str, component: str, configuration: Dict[str, Any]):
        """
        Initialise un nouveau résultat de benchmark.
        
        Args:
            name: Nom du benchmark
            component: Composant testé
            configuration: Configuration utilisée pour le test
        """
        self.name = name
        self.component = component
        self.configuration = configuration
        self.start_time = datetime.now()
        self.end_time = None
        self.metrics = {}
        self.errors = []
        self.success = True
        
    def add_metric(self, metric: BenchmarkMetric):
        """Ajoute une métrique au résultat."""
        self.metrics[metric.name] = metric
        
    def record_error(self, error: str, exception: Optional[Exception] = None):
        """Enregistre une erreur survenue pendant le benchmark."""
        error_info = {
            "message": error,
            "timestamp": datetime.now().isoformat()
        }
        
        if exception:
            error_info["exception"] = str(exception)
            error_info["traceback"] = traceback.format_exc()
            
        self.errors.append(error_info)
        self.success = False
        
    def complete(self):
        """Marque le benchmark comme terminé."""
        self.end_time = datetime.now()
        
    def get_duration(self) -> float:
        """Calcule la durée totale du benchmark en secondes."""
        if not self.end_time:
            self.complete()
            
        return (self.end_time - self.start_time).total_seconds()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "name": self.name,
            "component": self.component,
            "configuration": self.configuration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.get_duration(),
            "metrics": {name: metric.to_dict() for name, metric in self.metrics.items()},
            "errors": self.errors,
            "success": self.success
        }


class BenchmarkSuite:
    """
    Classe qui gère une suite de benchmarks, permettant d'exécuter plusieurs
    tests et de collecter les résultats.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialise une nouvelle suite de benchmarks.
        
        Args:
            name: Nom de la suite
            description: Description de la suite
        """
        self.name = name
        self.description = description
        self.results = []
        self.start_time = None
        self.end_time = None
        self.output_dir = Path(tempfile.mkdtemp(prefix="benchmark_"))
        
        # Assurer que le répertoire existe
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Répertoire de sortie des benchmarks: {self.output_dir}")
        
    async def run_benchmark(self, name: str, component: str, configuration: Dict[str, Any], 
                           benchmark_func: Callable, *args, **kwargs) -> BenchmarkResult:
        """
        Exécute un benchmark et collecte les résultats.
        
        Args:
            name: Nom du benchmark
            component: Composant testé
            configuration: Configuration du test
            benchmark_func: Fonction à exécuter pour le benchmark
            args, kwargs: Arguments à passer à la fonction de benchmark
            
        Returns:
            Le résultat du benchmark
        """
        result = BenchmarkResult(name, component, configuration)
        self.results.append(result)
        
        try:
            # Collecter l'usage CPU et mémoire avant le test
            process = psutil.Process()
            mem_before = process.memory_info().rss / 1024 / 1024  # MB
            cpu_percent_before = process.cpu_percent(interval=0.1)
            
            # Exécuter le benchmark
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(benchmark_func):
                await benchmark_func(result, *args, **kwargs)
            else:
                benchmark_func(result, *args, **kwargs)
                
            end_time = time.time()
            
            # Collecter l'usage CPU et mémoire après le test
            mem_after = process.memory_info().rss / 1024 / 1024  # MB
            cpu_percent_after = process.cpu_percent(interval=0.1)
            
            # Ajouter des métriques standard
            duration_metric = BenchmarkMetric("duration", "s", "Durée d'exécution")
            duration_metric.add_value(end_time - start_time)
            result.add_metric(duration_metric)
            
            memory_usage_metric = BenchmarkMetric("memory_usage", "MB", "Utilisation mémoire")
            memory_usage_metric.add_value(mem_after - mem_before)
            result.add_metric(memory_usage_metric)
            
            cpu_usage_metric = BenchmarkMetric("cpu_usage", "%", "Utilisation CPU")
            cpu_usage_metric.add_value(cpu_percent_after)
            result.add_metric(cpu_usage_metric)
            
        except Exception as e:
            result.record_error(f"Erreur lors de l'exécution du benchmark: {str(e)}", e)
            logger.error(f"Benchmark {name} a échoué: {str(e)}", exc_info=True)
            
        finally:
            # Marquer le benchmark comme terminé
            result.complete()
            
            # Libérer les ressources
            gc.collect()
            
            # Enregistrer le résultat individuel dans un fichier
            self._save_result(result)
            
        return result
    
    def start(self):
        """Démarre l'exécution de la suite de benchmarks."""
        self.start_time = datetime.now()
        logger.info(f"Démarrage de la suite de benchmarks: {self.name}")
        
    def complete(self):
        """Termine l'exécution de la suite de benchmarks et génère les rapports."""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"Suite de benchmarks {self.name} terminée en {duration:.2f}s")
        
        # Générer les rapports
        self._generate_reports()
        
    def _save_result(self, result: BenchmarkResult):
        """Enregistre un résultat de benchmark dans un fichier JSON."""
        result_file = self.output_dir / f"{result.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            
        logger.info(f"Résultat du benchmark {result.name} enregistré dans {result_file}")
        
    def _generate_reports(self):
        """Génère des rapports basés sur tous les résultats collectés."""
        if not self.results:
            logger.warning("Aucun résultat à analyser pour générer des rapports")
            return
            
        # Générer un rapport JSON consolidé
        summary_file = self.output_dir / f"summary_{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        summary = {
            "name": self.name,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": (self.end_time - self.start_time).total_seconds(),
            "total_benchmarks": len(self.results),
            "successful_benchmarks": sum(1 for r in self.results if r.success),
            "failed_benchmarks": sum(1 for r in self.results if not r.success),
            "results": [r.to_dict() for r in self.results]
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Rapport de synthèse enregistré dans {summary_file}")
        
        # Générer des graphiques pour visualiser les performances
        self._generate_visualizations()
        
    def _generate_visualizations(self):
        """Génère des visualisations graphiques des résultats de benchmark."""
        # Répertoire pour les visualisations
        viz_dir = self.output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        # Extraire les données pour le DataFrame
        data = []
        
        for result in self.results:
            if not result.success:
                continue
                
            row = {
                "benchmark": result.name,
                "component": result.component,
                "duration": result.get_duration()
            }
            
            # Ajouter les métriques importantes
            for metric_name, metric in result.metrics.items():
                stats = metric.get_statistics()
                for stat_name, stat_value in stats.items():
                    if stat_name in ["mean", "median", "max"]:
                        row[f"{metric_name}_{stat_name}"] = stat_value
                        
            # Ajouter les paramètres de configuration importants
            for key, value in result.configuration.items():
                if isinstance(value, (int, float, str, bool)):
                    row[f"config_{key}"] = value
                    
            data.append(row)
            
        if not data:
            logger.warning("Pas de données valides pour générer des visualisations")
            return
            
        # Créer un DataFrame
        df = pd.DataFrame(data)
        
        # 1. Graphique de durée par benchmark
        plt.figure(figsize=(12, 6))
        ax = sns.barplot(x="benchmark", y="duration", hue="component", data=df)
        plt.title("Durée d'exécution par benchmark")
        plt.xlabel("Benchmark")
        plt.ylabel("Durée (s)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(viz_dir / "duration_by_benchmark.png")
        plt.close()
        
        # 2. Graphique d'utilisation mémoire
        if "memory_usage_mean" in df.columns:
            plt.figure(figsize=(12, 6))
            ax = sns.barplot(x="benchmark", y="memory_usage_mean", hue="component", data=df)
            plt.title("Utilisation mémoire par benchmark")
            plt.xlabel("Benchmark")
            plt.ylabel("Utilisation mémoire (MB)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(viz_dir / "memory_by_benchmark.png")
            plt.close()
            
        # 3. Graphique d'utilisation CPU
        if "cpu_usage_mean" in df.columns:
            plt.figure(figsize=(12, 6))
            ax = sns.barplot(x="benchmark", y="cpu_usage_mean", hue="component", data=df)
            plt.title("Utilisation CPU par benchmark")
            plt.xlabel("Benchmark")
            plt.ylabel("Utilisation CPU (%)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(viz_dir / "cpu_by_benchmark.png")
            plt.close()
            
        # 4. Heatmap de corrélation
        numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
        if len(numeric_cols) > 1:
            corr = df[numeric_cols].corr()
            plt.figure(figsize=(10, 8))
            sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
            plt.title("Corrélation entre les métriques")
            plt.tight_layout()
            plt.savefig(viz_dir / "metric_correlation.png")
            plt.close()
            
        # 5. Exporter le DataFrame en CSV pour analyse ultérieure
        df.to_csv(viz_dir / "benchmark_data.csv", index=False)
        logger.info(f"Visualisations générées dans {viz_dir}")


# Décorateurs utilitaires pour les benchmarks
def measure_time(metric_name: str = "execution_time"):
    """
    Décorateur pour mesurer le temps d'exécution d'une fonction.

    Args:
        metric_name: Nom de la métrique pour stocker le temps d'exécution
        
    Returns:
        Fonction décorée
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(result, *args, **kwargs):
            start_time = time.time()
            value = await func(result, *args, **kwargs)
            end_time = time.time()
            
            metric = result.metrics.get(metric_name)
            if not metric:
                metric = BenchmarkMetric(metric_name, "s", f"Temps d'exécution pour {func.__name__}")
                result.add_metric(metric)
                
            metric.add_value(end_time - start_time)
            return value
            
        @wraps(func)
        def sync_wrapper(result, *args, **kwargs):
            start_time = time.time()
            value = func(result, *args, **kwargs)
            end_time = time.time()
            
            metric = result.metrics.get(metric_name)
            if not metric:
                metric = BenchmarkMetric(metric_name, "s", f"Temps d'exécution pour {func.__name__}")
                result.add_metric(metric)
                
            metric.add_value(end_time - start_time)
            return value
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
        
    return decorator


def measure_memory(metric_name: str = "memory_usage"):
    """
    Décorateur pour mesurer l'utilisation mémoire d'une fonction.

    Args:
        metric_name: Nom de la métrique pour stocker l'utilisation mémoire
        
    Returns:
        Fonction décorée
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(result, *args, **kwargs):
            process = psutil.Process()
            gc.collect()  # Force garbage collection
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            value = await func(result, *args, **kwargs)
            
            gc.collect()  # Force garbage collection
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            
            metric = result.metrics.get(metric_name)
            if not metric:
                metric = BenchmarkMetric(metric_name, "MB", f"Utilisation mémoire pour {func.__name__}")
                result.add_metric(metric)
                
            metric.add_value(memory_after - memory_before)
            return value
            
        @wraps(func)
        def sync_wrapper(result, *args, **kwargs):
            process = psutil.Process()
            gc.collect()  # Force garbage collection
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            value = func(result, *args, **kwargs)
            
            gc.collect()  # Force garbage collection
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            
            metric = result.metrics.get(metric_name)
            if not metric:
                metric = BenchmarkMetric(metric_name, "MB", f"Utilisation mémoire pour {func.__name__}")
                result.add_metric(metric)
                
            metric.add_value(memory_after - memory_before)
            return value
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
        
    return decorator
