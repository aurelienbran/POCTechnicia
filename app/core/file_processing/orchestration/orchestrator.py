"""
Orchestrateur central pour le traitement intelligent des documents
======================================================================

Ce module implémente l'orchestrateur central qui coordonne l'exécution
des différents processeurs de documents, sélectionne les stratégies appropriées,
et gère la fusion des résultats.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple, Type
from pathlib import Path
import logging
from datetime import datetime
import json
import concurrent.futures

from ..base import DocumentProcessor, ProcessingResult
from ..ocr.base import OCRProcessor
from ..specialized_processors.base import SpecializedProcessor
from ..ai_orchestrator import AIOrchestrator
from .strategy_selector import ProcessingStrategySelector
from .result_merger import ResultMerger
from .parallel_executor import ParallelExecutor

logger = logging.getLogger(__name__)


class ProcessingOrchestrator:
    """
    Orchestrateur central pour le traitement intelligent des documents.
    
    Cette classe coordonne l'exécution des différents processeurs de documents,
    sélectionne les stratégies les plus appropriées en fonction du contenu,
    exécute les traitements en parallèle lorsque c'est possible, et fusionne
    les résultats de manière intelligente.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'orchestrateur de traitement.
        
        Args:
            config: Configuration de l'orchestrateur
                - max_parallel: Nombre maximum de traitements parallèles (défaut: 3)
                - strategy_weights: Poids pour les différentes stratégies de sélection
                - result_priority: Priorités pour la fusion des résultats
                - ai_orchestrator_config: Configuration pour l'AIOrchestrator
                - specialized_processors: Liste des processeurs spécialisés à utiliser
        """
        self.config = config or {}
        self.max_parallel = self.config.get("max_parallel", 3)
        
        # Initialiser les composants
        self.strategy_selector = ProcessingStrategySelector(
            self.config.get("strategy_weights", {})
        )
        self.result_merger = ResultMerger(
            self.config.get("result_priority", {})
        )
        self.parallel_executor = ParallelExecutor(
            max_workers=self.max_parallel
        )
        
        # Initialiser l'orchestrateur AI si configuré
        self.ai_orchestrator = None
        if self.config.get("use_ai_orchestrator", True):
            self.ai_orchestrator = AIOrchestrator(
                self.config.get("ai_orchestrator_config", {})
            )
        
        # Liste des processeurs spécialisés disponibles
        self.specialized_processors = self.config.get("specialized_processors", [])
        
        self.initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialise l'orchestrateur et ses composants.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        try:
            # Initialiser l'orchestrateur AI si présent
            if self.ai_orchestrator:
                ai_init = await self.ai_orchestrator.initialize()
                if not ai_init:
                    logger.warning("L'initialisation de l'orchestrateur AI a échoué")
            
            # Initialiser les processeurs spécialisés
            for processor in self.specialized_processors:
                await processor.initialize()
            
            self.initialized = True
            logger.info("Orchestrateur de traitement initialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'orchestrateur: {str(e)}")
            return False
    
    async def process_document(self, 
                              document_path: Union[str, Path],
                              output_dir: Optional[Union[str, Path]] = None,
                              **kwargs) -> ProcessingResult:
        """
        Traite un document en orchestrant les différents processeurs.
        
        Cette méthode analyse le document, détermine les meilleurs processeurs à utiliser,
        les exécute (en parallèle si possible), et fusionne les résultats de manière intelligente.
        
        Args:
            document_path: Chemin vers le document à traiter
            output_dir: Répertoire de sortie pour les fichiers générés
            **kwargs: Options supplémentaires
                - language: Code de langue pour l'OCR
                - force_processors: Liste des processeurs à forcer
                - skip_processors: Liste des processeurs à ignorer
                - document_type: Type de document ('technical', 'text', 'mixed')
                
        Returns:
            Résultat combiné du traitement
        """
        if not self.initialized:
            await self.initialize()
        
        document_path = Path(document_path)
        if not document_path.exists():
            raise FileNotFoundError(f"Le document {document_path} n'existe pas")
        
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Créer un répertoire temporaire si aucun n'est fourni
            output_dir = Path(os.path.join(
                os.path.dirname(document_path),
                f"output_{document_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            ))
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Analyser le document pour sélectionner la stratégie
        logger.info(f"Analyse du document {document_path} pour sélection de stratégie")
        selected_processors = await self.strategy_selector.select_processors(
            document_path, 
            force_processors=kwargs.get("force_processors"),
            skip_processors=kwargs.get("skip_processors"),
            document_type=kwargs.get("document_type")
        )
        
        logger.info(f"Processeurs sélectionnés: {[p.__class__.__name__ for p in selected_processors]}")
        
        # Utiliser l'orchestrateur AI si disponible et approprié
        if self.ai_orchestrator and not kwargs.get("skip_ai_orchestrator"):
            ai_result = await self.ai_orchestrator.process_document(
                document_path,
                output_dir,
                language=kwargs.get("language", "fra"),
                **{k: v for k, v in kwargs.items() if k not in ["force_processors", "skip_processors"]}
            )
        else:
            ai_result = None
        
        # Exécuter les processeurs spécialisés en parallèle
        processor_results = await self.parallel_executor.execute(
            selected_processors,
            document_path,
            output_dir,
            **kwargs
        )
        
        # Fusionner les résultats
        merged_result = self.result_merger.merge_results(
            ai_result,
            processor_results,
            document_path
        )
        
        return merged_result
    
    async def process_batch(self,
                           document_paths: List[Union[str, Path]],
                           output_base_dir: Optional[Union[str, Path]] = None,
                           **kwargs) -> Dict[str, ProcessingResult]:
        """
        Traite un lot de documents.
        
        Args:
            document_paths: Liste des chemins vers les documents à traiter
            output_base_dir: Répertoire de base pour les sorties
            **kwargs: Options supplémentaires (voir process_document)
            
        Returns:
            Dictionnaire des résultats de traitement par chemin de document
        """
        if not self.initialized:
            await self.initialize()
        
        if output_base_dir:
            output_base_dir = Path(output_base_dir)
            output_base_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        for doc_path in document_paths:
            doc_path = Path(doc_path)
            if not doc_path.exists():
                logger.warning(f"Document {doc_path} non trouvé, ignoré.")
                continue
            
            if output_base_dir:
                output_dir = output_base_dir / doc_path.stem
            else:
                output_dir = None
            
            try:
                result = await self.process_document(doc_path, output_dir, **kwargs)
                results[str(doc_path)] = result
            except Exception as e:
                logger.error(f"Erreur lors du traitement de {doc_path}: {str(e)}")
                results[str(doc_path)] = {"error": str(e), "status": "failed"}
        
        return results
