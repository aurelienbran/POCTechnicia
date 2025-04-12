"""
Fusion intelligente des résultats de différents processeurs
======================================================================

Ce module implémente un système de fusion des résultats provenant de différents
processeurs, avec gestion des priorités et résolution des conflits.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import logging
import json

from ..base import ProcessingResult

logger = logging.getLogger(__name__)


class ResultMerger:
    """
    Fusionneur des résultats de différents processeurs.
    
    Cette classe est responsable de combiner intelligemment les résultats
    des différents processeurs en résolvant les conflits et en respectant
    les priorités définies.
    """
    
    def __init__(self, result_priority: Optional[Dict[str, int]] = None):
        """
        Initialise le fusionneur de résultats.
        
        Args:
            result_priority: Dictionnaire de priorités pour les différentes sources:
                - "ai_orchestrator": Priorité pour l'orchestrateur AI
                - "table_extractor": Priorité pour l'extracteur de tableaux
                - "schema_analyzer": Priorité pour l'analyseur de schémas
                - "formula_processor": Priorité pour le processeur de formules
                Plus la valeur est élevée, plus la priorité est haute.
        """
        self.result_priority = result_priority or {
            "ai_orchestrator": 10,  # Priorité maximale pour l'AI
            "table_extractor": 8,
            "schema_analyzer": 7,
            "formula_processor": 6,
            "default": 5  # Priorité par défaut
        }
    
    def merge_results(self,
                     ai_result: Optional[Dict[str, Any]],
                     processor_results: Dict[str, Any],
                     document_path: Path) -> ProcessingResult:
        """
        Fusionne les résultats de différents processeurs.
        
        Args:
            ai_result: Résultat de l'orchestrateur AI (peut être None)
            processor_results: Résultats des processeurs spécialisés
            document_path: Chemin du document traité
            
        Returns:
            Résultat combiné du traitement
        """
        # Créer un résultat de base
        merged_result = ProcessingResult(
            document_path=str(document_path),
            success=True,
            error=None,
            content={},
            metadata={
                "processors": [],
                "merged_by": "ResultMerger",
                "has_conflicts": False,
                "conflict_resolution": []
            }
        )
        
        # Collecter tous les résultats
        all_results = {}
        if ai_result:
            all_results["ai_orchestrator"] = ai_result
        
        for processor_name, result in processor_results.items():
            all_results[processor_name] = result
        
        # Vérifier si des résultats ont échoué
        success_status = {name: result.get('success', False) 
                         for name, result in all_results.items()}
        
        if not any(success_status.values()):
            # Tous les processeurs ont échoué
            merged_result.success = False
            merged_result.error = "Tous les processeurs ont échoué"
            return merged_result
        
        # Fusionner le contenu par catégorie
        content_categories = self._identify_content_categories(all_results)
        merged_content, conflicts = self._merge_content_by_category(all_results, content_categories)
        
        # Fusionner les métadonnées
        merged_metadata = self._merge_metadata(all_results)
        
        # Mettre à jour le résultat
        merged_result.content = merged_content
        merged_result.metadata.update(merged_metadata)
        merged_result.metadata["processors"] = list(all_results.keys())
        merged_result.metadata["has_conflicts"] = bool(conflicts)
        merged_result.metadata["conflict_resolution"] = conflicts
        
        return merged_result
    
    def _identify_content_categories(self, results: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Identifie toutes les catégories de contenu dans les résultats.
        
        Args:
            results: Dictionnaire des résultats par processeur
            
        Returns:
            Liste des catégories de contenu
        """
        categories = set()
        for _, result in results.items():
            if not result.get('success', False):
                continue
                
            content = result.get('content', {})
            categories.update(content.keys())
        
        return list(categories)
    
    def _merge_content_by_category(self, 
                                  results: Dict[str, Dict[str, Any]],
                                  categories: List[str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Fusionne le contenu par catégorie en tenant compte des priorités.
        
        Args:
            results: Dictionnaire des résultats par processeur
            categories: Liste des catégories de contenu
            
        Returns:
            Tuple (contenu fusionné, liste des conflits résolus)
        """
        merged_content = {}
        conflicts = []
        
        for category in categories:
            category_results = {}
            
            # Collecter les résultats de cette catégorie
            for processor_name, result in results.items():
                if not result.get('success', False):
                    continue
                    
                content = result.get('content', {})
                if category in content:
                    category_results[processor_name] = content[category]
            
            # S'il n'y a qu'un seul résultat, l'utiliser directement
            if len(category_results) == 1:
                processor_name = next(iter(category_results))
                merged_content[category] = category_results[processor_name]
                continue
            
            # S'il y a plusieurs résultats, résoudre le conflit
            if len(category_results) > 1:
                winner, conflict_info = self._resolve_conflict(category, category_results)
                merged_content[category] = category_results[winner]
                conflicts.append(conflict_info)
        
        return merged_content, conflicts
    
    def _resolve_conflict(self, 
                         category: str, 
                         category_results: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Résout un conflit entre plusieurs processeurs pour une catégorie.
        
        Args:
            category: Catégorie de contenu
            category_results: Résultats par processeur pour cette catégorie
            
        Returns:
            Tuple (nom du processeur gagnant, information sur le conflit)
        """
        # Calculer les priorités
        priorities = {}
        for processor_name in category_results:
            priorities[processor_name] = self.result_priority.get(
                processor_name, 
                self.result_priority["default"]
            )
        
        # Trouver le processeur avec la priorité la plus élevée
        winner = max(priorities, key=priorities.get)
        
        # Créer une information sur le conflit
        conflict_info = {
            "category": category,
            "processors": list(category_results.keys()),
            "resolution_method": "priority",
            "winner": winner,
            "priorities": priorities
        }
        
        logger.info(f"Conflit résolu pour {category}: {winner} choisi (priorité {priorities[winner]})")
        
        return winner, conflict_info
    
    def _merge_metadata(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fusionne les métadonnées de tous les processeurs.
        
        Args:
            results: Dictionnaire des résultats par processeur
            
        Returns:
            Métadonnées fusionnées
        """
        merged_metadata = {}
        
        for processor_name, result in results.items():
            if not result.get('success', False):
                continue
                
            metadata = result.get('metadata', {})
            
            # Ajouter un préfixe au processeur pour éviter les conflits
            processor_metadata = {
                f"{processor_name}_{key}": value 
                for key, value in metadata.items()
            }
            
            merged_metadata.update(processor_metadata)
        
        return merged_metadata
