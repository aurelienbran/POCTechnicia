#!/usr/bin/env python
"""Outil de diagnostic pour le système RAG."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
import httpx
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress
except ImportError:
    print("Erreur: Le module 'rich' n'est pas installé.")
    print("Installez-le avec: pip install rich==13.7.0")
    sys.exit(1)
from typing import Dict, Any, Optional
import uvicorn

console = Console()

class DiagnosticTool:
    """Classe principale pour l'outil de diagnostic."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialise l'outil avec l'URL de base de l'API."""
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)  # Augmentation du timeout
    
    async def close(self):
        """Ferme le client HTTP."""
        await self.client.aclose()
    
    async def check_server(self) -> bool:
        """Vérifie si le serveur est accessible."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False

    async def start_server(self):
        """Démarre le serveur si nécessaire."""
        if not await self.check_server():
            console.print("[yellow]Serveur non détecté. Démarrage du serveur...[/yellow]")
            # Démarrer le serveur en arrière-plan
            cmd = ["uvicorn", "app.main:app", "--host", "localhost", "--port", "8000"]
            process = await asyncio.create_subprocess_exec(*cmd)
            # Attendre que le serveur soit prêt
            for _ in range(5):  # 5 tentatives
                await asyncio.sleep(2)
                if await self.check_server():
                    console.print("[green]Serveur démarré avec succès![/green]")
                    return True
            raise Exception("Impossible de démarrer le serveur")

    async def analyze_pdf(self, file_path: str) -> Dict[str, Any]:
        """Analyse un fichier PDF."""
        # Vérifier si le fichier existe
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Le fichier {file_path} n'existe pas")
            
        url = f"{self.base_url}/api/v1/diagnostic/pdf"
        try:
            response = await self.client.post(url, json={"file_path": file_path})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Erreur lors de l'analyse du PDF: {str(e)}")
    
    async def analyze_search(self, query: str) -> Dict[str, Any]:
        """Analyse une recherche."""
        url = f"{self.base_url}/api/v1/diagnostic/search"
        try:
            response = await self.client.post(url, json={"query": query})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Erreur lors de l'analyse de la recherche: {str(e)}")
    
    async def analyze_response(self, response_text: str) -> Dict[str, Any]:
        """Analyse une réponse."""
        url = f"{self.base_url}/api/v1/diagnostic/response"
        try:
            response = await self.client.post(url, json={"response": response_text})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Erreur lors de l'analyse de la réponse: {str(e)}")

    async def full_diagnostic(self, file_path: Optional[str] = None, 
                            query: Optional[str] = None,
                            response: Optional[str] = None) -> Dict[str, Any]:
        """Effectue un diagnostic complet."""
        url = f"{self.base_url}/api/v1/diagnostic/full"
        data = {
            "file_path": file_path,
            "query": query,
            "response": response
        }
        try:
            response = await self.client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Erreur lors du diagnostic complet: {str(e)}")

def display_pdf_analysis(analysis: Dict[str, Any]):
    """Affiche l'analyse du PDF."""
    console.print(Panel("Analyse PDF", style="bold magenta"))
    
    # Statistiques des sections
    section_table = Table(show_header=True, header_style="bold cyan")
    section_table.add_column("Métrique")
    section_table.add_column("Valeur")
    
    stats = analysis["section_analysis"]
    section_table.add_row("Total sections", str(stats["total_sections"]))
    section_table.add_row("Sections avec contenu", str(stats["sections_with_content"]))
    section_table.add_row("Longueur moyenne", f"{stats['avg_section_length']:.2f}")
    
    console.print(section_table)
    
    # Distribution des chunks
    chunk_stats = analysis["chunk_analysis"]
    console.print("\n[bold]Distribution des Chunks:[/bold]")
    for size_range, count in chunk_stats["size_distribution"].items():
        console.print(f"  {size_range}: {'█' * count} ({count})")
    
    # Problèmes potentiels
    if chunk_stats["potential_issues"]:
        console.print("\n[bold red]Problèmes Potentiels:[/bold red]")
        for issue in chunk_stats["potential_issues"]:
            console.print(f"  • {issue['type']}: {issue.get('message', '')}")

def display_search_analysis(analysis: Dict[str, Any]):
    """Affiche l'analyse de la recherche."""
    console.print(Panel("Analyse de la Recherche", style="bold magenta"))
    
    # Résultats de recherche
    search_table = Table(show_header=True, header_style="bold cyan")
    search_table.add_column("Métrique")
    search_table.add_column("Valeur")
    
    stats = analysis["search_analysis"]
    search_table.add_row("Total résultats", str(stats["total_results"]))
    search_table.add_row("Score moyen", f"{stats['avg_score']:.2f}")
    
    console.print(search_table)
    
    # Patterns identifiés
    patterns = analysis["pattern_analysis"]["identified_patterns"]
    if patterns:
        console.print("\n[bold]Patterns Identifiés:[/bold]")
        for pattern in patterns:
            console.print(f"  • {pattern['type']}: {pattern['value']}")
    
    # Suggestions
    suggestions = analysis["pattern_analysis"]["suggestions"]
    if suggestions:
        console.print("\n[bold yellow]Suggestions:[/bold yellow]")
        for suggestion in suggestions:
            console.print(f"  • {suggestion['message']}")

def display_response_analysis(analysis: Dict[str, Any]):
    """Affiche l'analyse de la réponse."""
    console.print(Panel("Analyse de la Réponse", style="bold magenta"))
    
    # Structure
    structure = analysis["structure_analysis"]
    console.print("[bold]Structure de la Réponse:[/bold]")
    for section, present in structure["sections_present"].items():
        status = "✓" if present else "✗"
        color = "green" if present else "red"
        console.print(f"  {status} {section}", style=color)
    
    # Contenu technique
    tech_stats = analysis["technical_analysis"]
    console.print("\n[bold]Contenu Technique:[/bold]")
    if tech_stats["technical_terms"]:
        console.print("  Termes techniques:", ", ".join(tech_stats["technical_terms"]))
    if tech_stats["section_references"]:
        console.print("  Références sections:", ", ".join(tech_stats["section_references"]))
    
    # Sources
    source_stats = analysis["source_analysis"]
    if source_stats["sources_cited"]:
        console.print("\n[bold]Sources:[/bold]")
        for source in source_stats["sources_cited"]:
            console.print(f"  • {source['file']} (score: {source['score']}%)")

async def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Outil de diagnostic RAG")
    parser.add_argument("--pdf", help="Chemin vers le fichier PDF à analyser")
    parser.add_argument("--query", help="Requête à analyser")
    parser.add_argument("--response", help="Fichier contenant la réponse à analyser")
    parser.add_argument("--full", action="store_true", help="Effectuer un diagnostic complet")
    parser.add_argument("--output", help="Fichier de sortie pour les résultats (JSON)")
    args = parser.parse_args()
    
    tool = DiagnosticTool()
    
    try:
        # Vérifier/démarrer le serveur
        await tool.start_server()
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Diagnostic en cours...", total=100)
            
            if args.full:
                response_text = None
                if args.response:
                    try:
                        with open(args.response, 'r', encoding='utf-8') as f:
                            response_text = f.read()
                    except FileNotFoundError:
                        console.print(f"[red]Erreur: Le fichier {args.response} n'existe pas[/red]")
                        return
                
                try:
                    results = await tool.full_diagnostic(
                        file_path=args.pdf,
                        query=args.query,
                        response=response_text
                    )
                    
                    progress.update(task, completed=100)
                    
                    if "pdf_analysis" in results:
                        display_pdf_analysis(results["pdf_analysis"])
                    if "search_analysis" in results:
                        display_search_analysis(results["search_analysis"])
                    if "response_analysis" in results:
                        display_response_analysis(results["response_analysis"])
                    
                    if args.output:
                        with open(args.output, 'w', encoding='utf-8') as f:
                            json.dump(results, f, indent=2, ensure_ascii=False)
                        console.print(f"\n[green]Résultats sauvegardés dans {args.output}[/green]")
                
                except Exception as e:
                    console.print(f"[red]Erreur lors du diagnostic: {str(e)}[/red]")
            
            else:
                if args.pdf:
                    try:
                        results = await tool.analyze_pdf(args.pdf)
                        progress.update(task, completed=33)
                        display_pdf_analysis(results)
                    except Exception as e:
                        console.print(f"[red]Erreur lors de l'analyse PDF: {str(e)}[/red]")
                
                if args.query:
                    try:
                        results = await tool.analyze_search(args.query)
                        progress.update(task, completed=66)
                        display_search_analysis(results)
                    except Exception as e:
                        console.print(f"[red]Erreur lors de l'analyse de la recherche: {str(e)}[/red]")
                
                if args.response:
                    try:
                        with open(args.response, 'r', encoding='utf-8') as f:
                            response_text = f.read()
                        results = await tool.analyze_response(response_text)
                        progress.update(task, completed=100)
                        display_response_analysis(results)
                    except FileNotFoundError:
                        console.print(f"[red]Erreur: Le fichier {args.response} n'existe pas[/red]")
                    except Exception as e:
                        console.print(f"[red]Erreur lors de l'analyse de la réponse: {str(e)}[/red]")
    
    finally:
        await tool.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[red]Diagnostic interrompu[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Erreur: {str(e)}[/red]")
        sys.exit(1)
