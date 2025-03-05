"""Module d'analyse des réponses générées."""
from typing import Dict, List, Any
import logging
import re
from ..core.llm_interface import LLMInterface

logger = logging.getLogger(__name__)

class ResponseAnalyzer:
    """Classe pour analyser la qualité des réponses générées."""
    
    def __init__(self, llm_interface: LLMInterface = None):
        """Initialise l'analyseur avec l'interface LLM."""
        self.llm_interface = llm_interface
        
    def analyze_response_structure(self, response: str) -> Dict[str, Any]:
        """Analyse la structure d'une réponse."""
        structure_stats = {
            "sections_present": {},
            "content_stats": {},
            "formatting": [],
            "potential_issues": []
        }
        
        # Sections attendues
        expected_sections = [
            "DESCRIPTION",
            "INFORMATIONS TECHNIQUES",
            "INSTRUCTIONS ET PRÉCAUTIONS",
            "VÉRIFICATION",
            "SOURCES"
        ]
        
        # Vérifier la présence des sections
        for section in expected_sections:
            present = section in response
            structure_stats["sections_present"][section] = present
            if not present:
                structure_stats["potential_issues"].append({
                    "type": "missing_section",
                    "section": section
                })
        
        # Analyser le contenu de chaque section
        current_section = None
        section_content = {}
        
        for line in response.split('\n'):
            for section in expected_sections:
                if section in line:
                    current_section = section
                    section_content[current_section] = []
                    break
            if current_section and line.strip() and section not in line:
                section_content[current_section].append(line.strip())
        
        # Statistiques de contenu
        for section, content in section_content.items():
            structure_stats["content_stats"][section] = {
                "line_count": len(content),
                "avg_line_length": sum(len(line) for line in content) / len(content) if content else 0,
                "has_bullet_points": any(line.strip().startswith(('-', '*', '•')) for line in content)
            }
        
        # Vérifier le formatage
        if "```" in response:
            structure_stats["formatting"].append("code_blocks")
        if any(line.strip().startswith(('#', '##', '###')) for line in response.split('\n')):
            structure_stats["formatting"].append("headers")
        if re.search(r'\[.*?\]\(.*?\)', response):
            structure_stats["formatting"].append("links")
        
        return structure_stats
    
    def analyze_technical_content(self, response: str) -> Dict[str, Any]:
        """Analyse le contenu technique d'une réponse."""
        technical_stats = {
            "technical_terms": [],
            "section_references": [],
            "numerical_values": [],
            "potential_issues": []
        }
        
        # Extraire les références de section
        section_refs = re.findall(r'EL-\d+', response)
        technical_stats["section_references"] = section_refs
        
        # Extraire les termes techniques (à adapter selon le domaine)
        technical_terms = [
            "maintenance",
            "réparation",
            "diagnostic",
            "système",
            "composant",
            "panne",
            "erreur"
        ]
        found_terms = []
        for term in technical_terms:
            if term.lower() in response.lower():
                found_terms.append(term)
        technical_stats["technical_terms"] = found_terms
        
        # Extraire les valeurs numériques
        numerical_values = re.findall(r'\d+(?:\.\d+)?(?:\s*[kKmMgGtT]?[bB])?', response)
        technical_stats["numerical_values"] = numerical_values
        
        # Vérifier les problèmes potentiels
        if not section_refs:
            technical_stats["potential_issues"].append({
                "type": "no_section_refs",
                "message": "Aucune référence de section trouvée"
            })
        
        if len(found_terms) < 3:
            technical_stats["potential_issues"].append({
                "type": "low_technical_content",
                "message": "Peu de termes techniques utilisés"
            })
        
        return technical_stats
    
    def analyze_source_usage(self, response: str) -> Dict[str, Any]:
        """Analyse l'utilisation des sources dans la réponse."""
        source_stats = {
            "sources_cited": [],
            "source_distribution": {},
            "potential_issues": []
        }
        
        # Extraire les sources citées
        sources_section = ""
        if "SOURCES" in response:
            sources_section = response[response.index("SOURCES"):]
            if any(other_section in sources_section for other_section in ["DESCRIPTION", "INFORMATIONS TECHNIQUES"]):
                sources_section = sources_section[:min(sources_section.index(section) 
                    for section in ["DESCRIPTION", "INFORMATIONS TECHNIQUES"] 
                    if section in sources_section)]
        
        # Analyser les citations
        source_lines = [line.strip() for line in sources_section.split('\n') if line.strip()]
        for line in source_lines:
            if '.pdf' in line.lower():
                source_match = re.search(r'([^\s]+\.pdf)', line)
                if source_match:
                    source = source_match.group(1)
                    score_match = re.search(r'pertinence:\s*(\d+)%', line.lower())
                    score = int(score_match.group(1)) if score_match else None
                    source_stats["sources_cited"].append({
                        "file": source,
                        "score": score
                    })
        
        # Distribution des scores
        for source in source_stats["sources_cited"]:
            if source["score"]:
                score_range = f"{(source['score'] // 10) * 10}-{((source['score'] // 10) + 1) * 10}"
                source_stats["source_distribution"][score_range] = source_stats["source_distribution"].get(score_range, 0) + 1
        
        # Vérifier les problèmes potentiels
        if not source_stats["sources_cited"]:
            source_stats["potential_issues"].append({
                "type": "no_sources",
                "message": "Aucune source citée"
            })
        else:
            low_relevance_sources = [s for s in source_stats["sources_cited"] if s["score"] and s["score"] < 50]
            if low_relevance_sources:
                source_stats["potential_issues"].append({
                    "type": "low_relevance_sources",
                    "message": f"{len(low_relevance_sources)} sources avec un score < 50%"
                })
        
        return source_stats
