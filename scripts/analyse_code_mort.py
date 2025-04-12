#!/usr/bin/env python
"""
Script d'analyse statique pour identifier le code potentiellement mort
dans l'application Technicia.

Utilise flake8 pour détecter le code non utilisé et génère un rapport.
"""

import os
import sys
import subprocess
import re
from collections import defaultdict
import json
from datetime import datetime

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON_DIRS = ["app", "scripts", "tests"]
EXCLUDED_DIRS = ["__pycache__", ".venv", "node_modules", "dist"]
REPORT_DIR = os.path.join(PROJECT_ROOT, "documentation", "architecture")


def run_flake8_analysis():
    """Exécute flake8 pour détecter le code mort et les problèmes potentiels"""
    results = defaultdict(list)
    
    for directory in PYTHON_DIRS:
        dir_path = os.path.join(PROJECT_ROOT, directory)
        if not os.path.exists(dir_path):
            print(f"Le répertoire {directory} n'existe pas, ignoré.")
            continue
            
        print(f"Analyse de {directory}...")
        
        # Exécution de flake8 avec les plugins pertinents
        # F401: module importé mais non utilisé
        # F841: variable locale assignée mais jamais utilisée
        cmd = [
            "flake8",
            dir_path,
            "--select=F401,F841",
            "--statistics",
            "--output-file=-"
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                check=False
            )
            
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                    
                # Parse les résultats de flake8
                match = re.match(r"(.*?):(\d+):(\d+): (F\d+) (.*)", line)
                if match:
                    file_path, line_num, col, error_code, message = match.groups()
                    rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                    
                    # Ignorer les répertoires exclus
                    if any(excl in rel_path for excl in EXCLUDED_DIRS):
                        continue
                        
                    results[error_code].append({
                        "file": rel_path,
                        "line": int(line_num),
                        "message": message
                    })
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de l'exécution de flake8: {e}")
            print(e.stderr)
    
    return results


def check_dead_functions():
    """
    Analyse simple pour trouver des fonctions potentiellement non utilisées
    en cherchant les définitions de fonctions et les appels à ces fonctions
    """
    functions_defined = {}
    functions_called = set()
    
    # Regex pour trouver les définitions de fonctions
    def_pattern = re.compile(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
    
    # Regex pour trouver les appels de fonctions
    call_pattern = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
    
    for directory in PYTHON_DIRS:
        dir_path = os.path.join(PROJECT_ROOT, directory)
        if not os.path.exists(dir_path):
            continue
            
        for root, _, files in os.walk(dir_path):
            if any(excl in root for excl in EXCLUDED_DIRS):
                continue
                
            for file in files:
                if not file.endswith(".py"):
                    continue
                    
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Recherche des définitions de fonctions
                    for match in def_pattern.finditer(content):
                        func_name = match.group(1)
                        if not (func_name.startswith("__") and func_name.endswith("__")):
                            functions_defined[func_name] = rel_path
                    
                    # Recherche des appels de fonctions
                    for match in call_pattern.finditer(content):
                        func_name = match.group(1)
                        functions_called.add(func_name)
                        
                except Exception as e:
                    print(f"Erreur lors de l'analyse de {file_path}: {e}")
    
    # Fonctions définies mais potentiellement non utilisées
    # Exclusion des fonctions spéciales comme les tests, handlers, etc.
    potentially_unused = {}
    for func, file in functions_defined.items():
        if (func not in functions_called and 
            not func.startswith("test_") and 
            not func.startswith("handle_") and
            not func == "main"):
            potentially_unused[func] = file
    
    return potentially_unused


def generate_report(flake8_results, unused_functions):
    """Génère un rapport Markdown avec les résultats de l'analyse"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report_path = os.path.join(REPORT_DIR, "ANALYSE_CODE_MORT.md")
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Rapport d'analyse du code potentiellement mort\n\n")
        f.write(f"Généré le : {timestamp}\n\n")
        
        f.write("## Imports non utilisés (F401)\n\n")
        if "F401" in flake8_results and flake8_results["F401"]:
            f.write("| Fichier | Ligne | Message |\n")
            f.write("|---------|-------|--------|\n")
            for item in flake8_results["F401"]:
                f.write(f"| `{item['file']}` | {item['line']} | {item['message']} |\n")
        else:
            f.write("Aucun import non utilisé détecté.\n")
        
        f.write("\n## Variables non utilisées (F841)\n\n")
        if "F841" in flake8_results and flake8_results["F841"]:
            f.write("| Fichier | Ligne | Message |\n")
            f.write("|---------|-------|--------|\n")
            for item in flake8_results["F841"]:
                f.write(f"| `{item['file']}` | {item['line']} | {item['message']} |\n")
        else:
            f.write("Aucune variable non utilisée détectée.\n")
        
        f.write("\n## Fonctions potentiellement non utilisées\n\n")
        if unused_functions:
            f.write("| Fonction | Définie dans |\n")
            f.write("|----------|-------------|\n")
            for func, file in unused_functions.items():
                f.write(f"| `{func}` | `{file}` |\n")
        else:
            f.write("Aucune fonction potentiellement non utilisée détectée.\n")
        
        f.write("\n## Limitations de l'analyse\n\n")
        f.write("Cette analyse est basée sur des heuristiques et peut produire des faux positifs, en particulier :\n\n")
        f.write("- Les fonctions utilisées indirectement (via introspection, décorateurs, etc.)\n")
        f.write("- Les imports utilisés uniquement pour leurs effets secondaires\n")
        f.write("- Code appelé dynamiquement ou par réflexion\n")
        f.write("- Les fonctions exposées comme API publique\n\n")
        f.write("**Une validation manuelle des résultats est nécessaire avant de supprimer tout code.**\n")
    
    print(f"Rapport généré: {report_path}")
    return report_path


def main():
    """Fonction principale"""
    print("Analyse du code mort dans le projet Technicia...")
    
    # Vérifier si flake8 est installé
    try:
        subprocess.run(["flake8", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("flake8 n'est pas installé ou n'est pas dans le PATH.")
        print("Installez-le avec: pip install flake8")
        return 1
    
    # Exécuter les analyses
    flake8_results = run_flake8_analysis()
    unused_functions = check_dead_functions()
    
    # Générer le rapport
    report_path = generate_report(flake8_results, unused_functions)
    
    print("\nAnalyse terminée.")
    print(f"Imports non utilisés: {len(flake8_results.get('F401', []))}")
    print(f"Variables non utilisées: {len(flake8_results.get('F841', []))}")
    print(f"Fonctions potentiellement non utilisées: {len(unused_functions)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
