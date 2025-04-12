"""
Sélecteur de stratégie pour l'orchestration des processeurs
======================================================================

Ce module implémente un sélecteur de stratégie qui détermine quels processeurs
utiliser pour un document donné en fonction de son contenu et de ses caractéristiques.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple, Type
from pathlib import Path
import logging
import mimetypes
import magic
import numpy as np
from PIL import Image

from ..specialized_processors.base import SpecializedProcessor
from ..specialized_processors.table_extractor import TableExtractor
from ..specialized_processors.schema_analyzer import SchemaAnalyzer
from ..specialized_processors.formula_processor import FormulaProcessor

logger = logging.getLogger(__name__)


class ProcessingStrategySelector:
    """
    Sélecteur de stratégie pour déterminer les processeurs à utiliser.
    
    Cette classe analyse un document et détermine quels processeurs spécialisés
    doivent être utilisés en fonction de ses caractéristiques.
    """
    
    def __init__(self, strategy_weights: Optional[Dict[str, float]] = None):
        """
        Initialise le sélecteur de stratégie.
        
        Args:
            strategy_weights: Poids pour les différentes caractéristiques:
                - has_tables: Poids pour la présence de tableaux
                - has_schemas: Poids pour la présence de schémas
                - has_formulas: Poids pour la présence de formules
                - text_density: Poids pour la densité de texte
                - image_complexity: Poids pour la complexité des images
        """
        self.strategy_weights = strategy_weights or {
            "has_tables": 1.0,
            "has_schemas": 0.8,
            "has_formulas": 0.9,
            "text_density": 0.7,
            "image_complexity": 0.6
        }
        
        # Seuils de décision pour les différentes caractéristiques
        self.decision_thresholds = {
            "table_extractor": 0.6,
            "schema_analyzer": 0.5,
            "formula_processor": 0.7
        }
        
        # Mapping des processeurs disponibles
        self.processor_mapping = {
            "table_extractor": TableExtractor,
            "schema_analyzer": SchemaAnalyzer,
            "formula_processor": FormulaProcessor
        }
    
    async def select_processors(self,
                              document_path: Path,
                              force_processors: Optional[List[str]] = None,
                              skip_processors: Optional[List[str]] = None,
                              document_type: Optional[str] = None) -> List[SpecializedProcessor]:
        """
        Sélectionne les processeurs appropriés pour un document.
        
        Args:
            document_path: Chemin vers le document à analyser
            force_processors: Liste des processeurs à forcer
            skip_processors: Liste des processeurs à ignorer
            document_type: Type de document ('technical', 'text', 'mixed')
            
        Returns:
            Liste des processeurs à utiliser
        """
        force_processors = force_processors or []
        skip_processors = skip_processors or []
        document_type = document_type or self._detect_document_type(document_path)
        
        # Si des processeurs sont forcés, les utiliser directement
        if force_processors:
            return [self._instantiate_processor(p) for p in force_processors 
                    if p not in skip_processors]
        
        # Analyser le document pour déterminer ses caractéristiques
        document_features = await self._analyze_document_features(document_path)
        
        # Calculer les scores pour chaque processeur
        processor_scores = self._calculate_processor_scores(document_features)
        
        # Sélectionner les processeurs qui dépassent leurs seuils
        selected_processors = []
        for processor_name, score in processor_scores.items():
            if (processor_name not in skip_processors and 
                    score >= self.decision_thresholds.get(processor_name, 0.5)):
                selected_processors.append(self._instantiate_processor(processor_name))
        
        logger.info(f"Scores des processeurs: {processor_scores}")
        logger.info(f"Processeurs sélectionnés: {[p.__class__.__name__ for p in selected_processors]}")
        
        return selected_processors
    
    def _instantiate_processor(self, processor_name: str) -> SpecializedProcessor:
        """
        Instancie un processeur par son nom.
        
        Args:
            processor_name: Nom du processeur à instancier
            
        Returns:
            Instance du processeur
        """
        processor_class = self.processor_mapping.get(processor_name)
        if not processor_class:
            raise ValueError(f"Processeur inconnu: {processor_name}")
        
        return processor_class()
    
    def _detect_document_type(self, document_path: Path) -> str:
        """
        Détecte le type de document.
        
        Args:
            document_path: Chemin vers le document
            
        Returns:
            Type de document ('technical', 'text', 'mixed')
        """
        mime_type = magic.from_file(str(document_path), mime=True)
        
        if mime_type.startswith('image/'):
            return 'technical'  # Les images sont souvent des schémas techniques
        elif mime_type == 'application/pdf':
            # Estimation basée sur la taille et le nom du fichier
            if document_path.stat().st_size > 5000000:  # > 5MB
                return 'mixed'  # Les gros PDF contiennent souvent des éléments mixtes
            
            filename = document_path.name.lower()
            technical_keywords = ['schema', 'tech', 'diagram', 'manual', 'guide', 'spec']
            if any(kw in filename for kw in technical_keywords):
                return 'technical'
        
        # Par défaut, considérer comme du texte
        return 'text'
    
    async def _analyze_document_features(self, document_path: Path) -> Dict[str, float]:
        """
        Analyse les caractéristiques d'un document.
        
        Args:
            document_path: Chemin vers le document
            
        Returns:
            Dictionnaire des caractéristiques avec leurs valeurs
        """
        # Note: Une implémentation complète analyserait réellement le document
        # Ceci est une version simplifiée pour démonstration
        
        features = {
            "has_tables": 0.0,
            "has_schemas": 0.0,
            "has_formulas": 0.0,
            "text_density": 0.5,  # Valeur par défaut
            "image_complexity": 0.0
        }
        
        # Estimation basée sur le type MIME
        mime_type = magic.from_file(str(document_path), mime=True)
        
        if mime_type == 'application/pdf':
            # Pour les PDF, estimer en fonction de la taille
            size_mb = document_path.stat().st_size / (1024 * 1024)
            
            # Les gros PDF ont plus de chance d'avoir des tableaux et des schémas
            if size_mb > 2:
                features["has_tables"] = min(0.7, size_mb / 10)
                features["has_schemas"] = min(0.8, size_mb / 8)
                features["text_density"] = max(0.3, 1 - (size_mb / 20))
            
            # Estimation basée sur le nom du fichier
            filename = document_path.name.lower()
            if 'table' in filename or 'tab' in filename:
                features["has_tables"] = max(features["has_tables"], 0.8)
            
            if 'schema' in filename or 'diagram' in filename:
                features["has_schemas"] = max(features["has_schemas"], 0.9)
            
            if 'formula' in filename or 'equation' in filename:
                features["has_formulas"] = 0.9
                
        elif mime_type.startswith('image/'):
            # Pour les images, estimer la complexité
            try:
                img = Image.open(document_path)
                # Une heuristique simple: plus l'image est grande, plus elle est susceptible d'être complexe
                width, height = img.size
                pixels = width * height
                features["image_complexity"] = min(0.9, pixels / (1920 * 1080))
                features["has_schemas"] = min(0.9, features["image_complexity"] + 0.2)
            except Exception as e:
                logger.warning(f"Erreur lors de l'analyse de l'image {document_path}: {str(e)}")
        
        return features
    
    def _calculate_processor_scores(self, document_features: Dict[str, float]) -> Dict[str, float]:
        """
        Calcule les scores pour chaque processeur en fonction des caractéristiques.
        
        Args:
            document_features: Caractéristiques du document
            
        Returns:
            Scores pour chaque processeur
        """
        processor_scores = {}
        
        # Calculer le score pour l'extracteur de tableaux
        processor_scores["table_extractor"] = (
            document_features["has_tables"] * self.strategy_weights["has_tables"]
        )
        
        # Calculer le score pour l'analyseur de schémas
        processor_scores["schema_analyzer"] = (
            document_features["has_schemas"] * self.strategy_weights["has_schemas"] +
            document_features["image_complexity"] * self.strategy_weights["image_complexity"] * 0.5
        ) / 1.5  # Normaliser
        
        # Calculer le score pour le processeur de formules
        processor_scores["formula_processor"] = (
            document_features["has_formulas"] * self.strategy_weights["has_formulas"]
        )
        
        return processor_scores
