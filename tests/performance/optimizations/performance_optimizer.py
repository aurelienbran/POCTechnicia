"""
Script d'optimisation des performances pour le POC Technicia
===========================================================

Ce module analyse les résultats des benchmarks pour identifier les goulots 
d'étranglement du système et appliquer automatiquement des optimisations
ciblées. Il offre également des recommandations pour les optimisations
qui nécessitent une intervention manuelle.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import sys
import json
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import importlib
import inspect
import ast
import re
import time
from datetime import datetime

# Ajouter le répertoire racine au path pour importer les modules du projet
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceBottleneck:
    """
    Classe représentant un goulot d'étranglement de performance identifié.
    """
    
    def __init__(self, component: str, metric: str, value: float, threshold: float,
                severity: str, file_path: Optional[Path] = None,
                function_name: Optional[str] = None, line_number: Optional[int] = None):
        """
        Initialise un nouveau goulot d'étranglement de performance.
        
        Args:
            component: Composant affecté par le goulot d'étranglement
            metric: Métrique de performance concernée (temps, mémoire, CPU)
            value: Valeur mesurée pour la métrique
            threshold: Seuil à partir duquel la métrique est considérée problématique
            severity: Gravité du problème (low, medium, high, critical)
            file_path: Chemin du fichier contenant le code problématique
            function_name: Nom de la fonction ou méthode problématique
            line_number: Numéro de ligne approximatif du problème
        """
        self.component = component
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.severity = severity
        self.file_path = file_path
        self.function_name = function_name
        self.line_number = line_number
        self.optimizations = []
        
    def add_optimization(self, description: str, automated: bool = False, 
                        code_change: Optional[Dict[str, Any]] = None):
        """
        Ajoute une optimisation possible pour ce goulot d'étranglement.
        
        Args:
            description: Description de l'optimisation
            automated: Si True, l'optimisation peut être appliquée automatiquement
            code_change: Détails des changements de code à effectuer
        """
        self.optimizations.append({
            "description": description,
            "automated": automated,
            "code_change": code_change
        })
        
    def __str__(self) -> str:
        """Représentation textuelle du goulot d'étranglement."""
        location = ""
        if self.file_path:
            location = f" dans {self.file_path}"
            if self.function_name:
                location += f"::{self.function_name}"
            if self.line_number:
                location += f" (ligne {self.line_number})"
                
        return (f"Bottleneck[{self.severity.upper()}]: {self.component} - {self.metric} = {self.value}"
                f" (seuil: {self.threshold}){location}")
        
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le goulot d'étranglement en dictionnaire."""
        return {
            "component": self.component,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
            "file_path": str(self.file_path) if self.file_path else None,
            "function_name": self.function_name,
            "line_number": self.line_number,
            "optimizations": self.optimizations
        }


class CodeOptimizer:
    """
    Classe pour analyser et optimiser le code source Python.
    """
    
    def __init__(self, project_root: Path):
        """
        Initialise un optimiseur de code.
        
        Args:
            project_root: Répertoire racine du projet
        """
        self.project_root = project_root
        
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyse un fichier Python pour identifier des optimisations potentielles.
        
        Args:
            file_path: Chemin du fichier à analyser
            
        Returns:
            Dict avec les résultats d'analyse
        """
        if not file_path.exists() or file_path.suffix != '.py':
            return {"success": False, "error": "Fichier non trouvé ou non Python"}
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                
            tree = ast.parse(code)
            
            # Résultats d'analyse
            analysis = {
                "file": str(file_path),
                "imports": self._extract_imports(tree),
                "functions": self._extract_functions(tree),
                "classes": self._extract_classes(tree),
                "complexity": self._compute_complexity(tree),
                "potential_optimizations": []
            }
            
            # Identifier des optimisations potentielles
            analysis["potential_optimizations"].extend(self._find_expensive_operations(tree, code))
            analysis["potential_optimizations"].extend(self._find_redundant_operations(tree, code))
            analysis["potential_optimizations"].extend(self._find_memory_issues(tree, code))
            
            return {"success": True, "analysis": analysis}
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du fichier {file_path}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
        
    def optimize_file(self, file_path: Path, optimizations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applique des optimisations à un fichier Python.
        
        Args:
            file_path: Chemin du fichier à optimiser
            optimizations: Liste des optimisations à appliquer
            
        Returns:
            Dictionnaire avec les résultats de l'optimisation
        """
        if not file_path.exists() or file_path.suffix != '.py':
            return {"success": False, "error": "Fichier non trouvé ou non Python"}
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_code = f.read()
                
            # Créer une sauvegarde du fichier original
            backup_path = file_path.with_suffix('.py.bak')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_code)
                
            # Appliquer les optimisations
            modified_code = original_code
            applied_optimizations = []
            
            for opt in optimizations:
                if opt.get("code_change"):
                    if opt["code_change"].get("type") == "replace":
                        pattern = opt["code_change"]["pattern"]
                        replacement = opt["code_change"]["replacement"]
                        
                        new_code = re.sub(pattern, replacement, modified_code)
                        
                        if new_code != modified_code:
                            modified_code = new_code
                            applied_optimizations.append({
                                "description": opt["description"],
                                "type": "replace",
                                "success": True
                            })
                        else:
                            applied_optimizations.append({
                                "description": opt["description"],
                                "type": "replace",
                                "success": False,
                                "reason": "Pattern not found"
                            })
                    
                    elif opt["code_change"].get("type") == "insert":
                        line_number = opt["code_change"]["line"]
                        code_to_insert = opt["code_change"]["code"]
                        
                        lines = modified_code.split('\n')
                        if 0 <= line_number < len(lines):
                            lines.insert(line_number, code_to_insert)
                            modified_code = '\n'.join(lines)
                            applied_optimizations.append({
                                "description": opt["description"],
                                "type": "insert",
                                "success": True
                            })
                        else:
                            applied_optimizations.append({
                                "description": opt["description"],
                                "type": "insert",
                                "success": False,
                                "reason": "Invalid line number"
                            })
            
            # Écrire le code modifié si des optimisations ont été appliquées
            if applied_optimizations:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_code)
                    
                return {
                    "success": True, 
                    "file": str(file_path),
                    "backup": str(backup_path),
                    "applied_optimizations": applied_optimizations
                }
            else:
                # Supprimer la sauvegarde si aucune optimisation n'a été appliquée
                backup_path.unlink()
                return {
                    "success": True,
                    "file": str(file_path),
                    "message": "No optimizations applied"
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation du fichier {file_path}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _extract_imports(self, tree: ast.Module) -> List[Dict[str, Any]]:
        """Extrait les imports du code."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append({
                        "type": "import",
                        "name": name.name,
                        "asname": name.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                for name in node.names:
                    imports.append({
                        "type": "from",
                        "module": node.module,
                        "name": name.name,
                        "asname": name.asname
                    })
        return imports
    
    def _extract_functions(self, tree: ast.Module) -> List[Dict[str, Any]]:
        """Extrait les fonctions du code."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "is_async": isinstance(node, ast.AsyncFunctionDef)
                })
        return functions
    
    def _extract_classes(self, tree: ast.Module) -> List[Dict[str, Any]]:
        """Extrait les classes du code."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        methods.append({
                            "name": child.name,
                            "line": child.lineno,
                            "is_async": isinstance(child, ast.AsyncFunctionDef)
                        })
                
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                    "bases": [base.id for base in node.bases if isinstance(base, ast.Name)]
                })
        return classes
    
    def _compute_complexity(self, tree: ast.Module) -> Dict[str, Any]:
        """Calcule la complexité du code."""
        complexity = {
            "functions": 0,
            "classes": 0,
            "lines": 0,
            "cyclomatic_complexity": 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                complexity["functions"] += 1
                # Calcul approximatif de la complexité cyclomatique
                cc = 1  # Base value
                for subnode in ast.walk(node):
                    if isinstance(subnode, (ast.If, ast.While, ast.For)):
                        cc += 1
                    elif isinstance(subnode, ast.BoolOp) and isinstance(subnode.op, ast.And):
                        cc += len(subnode.values) - 1
                complexity["cyclomatic_complexity"] += cc
            elif isinstance(node, ast.ClassDef):
                complexity["classes"] += 1
        
        # Compter les lignes (approximatif)
        complexity["lines"] = len(ast.unparse(tree).split('\n'))
        
        return complexity
        
    def _find_expensive_operations(self, tree: ast.Module, code: str) -> List[Dict[str, Any]]:
        """Identifie les opérations coûteuses dans le code."""
        expensive_ops = []
        
        # Rechercher les boucles imbriquées profondes
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                depth = self._get_loop_depth(node)
                if depth >= 3:
                    expensive_ops.append({
                        "type": "nested_loops",
                        "line": node.lineno,
                        "depth": depth,
                        "description": f"Boucle imbriquée de profondeur {depth} détectée",
                        "suggestion": "Considérer une refactorisation avec des algorithmes plus efficaces ou utiliser numpy/pandas",
                        "code_change": None
                    })
        
        # Rechercher les listes en compréhension imbriquées
        for node in ast.walk(tree):
            if isinstance(node, ast.ListComp):
                generators = node.generators
                if len(generators) > 1:
                    expensive_ops.append({
                        "type": "nested_comprehension",
                        "line": node.lineno,
                        "depth": len(generators),
                        "description": f"Liste en compréhension imbriquée avec {len(generators)} niveaux",
                        "suggestion": "Considérer numpy/pandas ou restructurer le code",
                        "code_change": None
                    })
        
        return expensive_ops
        
    def _find_redundant_operations(self, tree: ast.Module, code: str) -> List[Dict[str, Any]]:
        """Identifie les opérations redondantes dans le code."""
        redundant_ops = []
        
        # Rechercher les calculs répétés dans les boucles
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call):
                        # Approximation: Identifier les appels de fonction qui pourraient être extraits
                        func_name = self._get_function_name(subnode)
                        if func_name:
                            redundant_ops.append({
                                "type": "repeated_call",
                                "line": subnode.lineno,
                                "function": func_name,
                                "description": f"Appel potentiellement redondant à {func_name} dans une boucle",
                                "suggestion": "Extraire l'appel de fonction hors de la boucle si possible",
                                "code_change": None
                            })
        
        return redundant_ops
        
    def _find_memory_issues(self, tree: ast.Module, code: str) -> List[Dict[str, Any]]:
        """Identifie les problèmes d'utilisation mémoire dans le code."""
        memory_issues = []
        
        # Rechercher les grandes listes générées qui pourraient être remplacées par des générateurs
        for node in ast.walk(tree):
            if isinstance(node, ast.ListComp):
                # Détecter les listes potentiellement larges
                memory_issues.append({
                    "type": "list_comprehension",
                    "line": node.lineno,
                    "description": "Liste en compréhension potentiellement large",
                    "suggestion": "Considérer l'utilisation d'un générateur (generator expression) pour économiser la mémoire",
                    "code_change": {
                        "type": "replace",
                        "pattern": r"\[(.*) for (.*) in (.*)\]",
                        "replacement": r"(\1 for \2 in \3)"
                    }
                })
        
        return memory_issues
    
    def _get_loop_depth(self, node, depth=1):
        """Calcule la profondeur d'imbrication d'une boucle."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                return self._get_loop_depth(child, depth + 1)
        return depth
    
    def _get_function_name(self, node):
        """Obtient le nom d'une fonction à partir d'un nœud d'appel."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return f"{node.func.value.id}.{node.func.attr}" if hasattr(node.func.value, 'id') else None
        return None
