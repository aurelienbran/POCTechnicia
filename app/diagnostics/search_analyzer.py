"""Module d'analyse de la recherche sémantique."""
from typing import Dict, List, Any
import logging
from ..core.vector_store import VectorStore
from ..core.rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class SearchAnalyzer:
    """Classe pour analyser la qualité de la recherche."""
    
    def __init__(self, vector_store: VectorStore = None, rag_engine: RAGEngine = None):
        """Initialise l'analyseur avec les composants nécessaires."""
        self.vector_store = vector_store
        self.rag_engine = rag_engine
        
    async def analyze_search_results(self, query: str, k: int = 6) -> Dict[str, Any]:
        """Analyse les résultats de recherche pour une requête."""
        search_stats = {
            "query": query,
            "total_results": 0,
            "avg_score": 0,
            "score_distribution": {},
            "section_coverage": {},
            "content_analysis": [],
            "potential_issues": []
        }
        
        try:
            results = await self.vector_store.similarity_search(query, k=k)
            search_stats["total_results"] = len(results)
            
            if not results:
                search_stats["potential_issues"].append({
                    "type": "no_results",
                    "message": "Aucun résultat trouvé pour la requête"
                })
                return search_stats
            
            # Analyser les scores
            scores = [doc["score"] for doc in results]
            search_stats["avg_score"] = sum(scores) / len(scores)
            
            # Distribution des scores
            for score in scores:
                score_range = f"{(score // 0.1) * 0.1:.1f}-{((score // 0.1) + 1) * 0.1:.1f}"
                search_stats["score_distribution"][score_range] = search_stats["score_distribution"].get(score_range, 0) + 1
            
            # Analyser la couverture des sections
            for doc in results:
                section = doc.get("metadata", {}).get("section", "unknown")
                search_stats["section_coverage"][section] = search_stats["section_coverage"].get(section, 0) + 1
            
            # Analyser le contenu
            for doc in results:
                content_analysis = {
                    "score": doc["score"],
                    "section": doc.get("metadata", {}).get("section", "unknown"),
                    "content_preview": doc["content"][:200],
                    "token_count": len(doc.get("content", "").split())
                }
                search_stats["content_analysis"].append(content_analysis)
            
            # Détecter les problèmes potentiels
            if search_stats["avg_score"] < 0.5:
                search_stats["potential_issues"].append({
                    "type": "low_relevance",
                    "message": f"Score moyen bas: {search_stats['avg_score']:.2f}"
                })
            
            if len(set(doc.get("metadata", {}).get("section", "") for doc in results)) < 2:
                search_stats["potential_issues"].append({
                    "type": "limited_coverage",
                    "message": "Résultats concentrés dans peu de sections"
                })
            
            return search_stats
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de la recherche: {str(e)}")
            raise
            
    async def analyze_query_patterns(self, query: str) -> Dict[str, Any]:
        """Analyse les patterns de la requête."""
        pattern_stats = {
            "query": query,
            "identified_patterns": [],
            "suggestions": []
        }
        
        # Identifier les patterns de requête
        if "EL-" in query:
            pattern_stats["identified_patterns"].append({
                "type": "section_reference",
                "value": query[query.index("EL-"):].split()[0]
            })
        
        # Mots-clés techniques
        technical_keywords = ["problème", "erreur", "panne", "maintenance"]
        found_keywords = [kw for kw in technical_keywords if kw.lower() in query.lower()]
        if found_keywords:
            pattern_stats["identified_patterns"].append({
                "type": "technical_keywords",
                "value": found_keywords
            })
        
        # Suggestions d'amélioration
        if len(query.split()) < 3:
            pattern_stats["suggestions"].append({
                "type": "query_length",
                "message": "La requête pourrait être plus détaillée"
            })
        
        if not any(pattern["type"] == "section_reference" for pattern in pattern_stats["identified_patterns"]):
            pattern_stats["suggestions"].append({
                "type": "missing_section",
                "message": "Ajouter une référence de section pourrait améliorer les résultats"
            })
        
        return pattern_stats
