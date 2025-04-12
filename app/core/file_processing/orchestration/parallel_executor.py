"""
Exécuteur parallèle pour les processeurs de documents
======================================================================

Ce module implémente un système d'exécution parallèle pour les processeurs
de documents, permettant d'optimiser les performances de traitement.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from pathlib import Path
import logging
import concurrent.futures
import time

from ..specialized_processors.base import SpecializedProcessor

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """
    Exécuteur parallèle pour les processeurs de documents.
    
    Cette classe permet d'exécuter plusieurs processeurs en parallèle
    afin d'optimiser les performances de traitement.
    """
    
    def __init__(self, max_workers: int = 3):
        """
        Initialise l'exécuteur parallèle.
        
        Args:
            max_workers: Nombre maximum de travailleurs pour l'exécution parallèle
        """
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    
    async def execute(self,
                     processors: List[SpecializedProcessor],
                     document_path: Path,
                     output_dir: Path,
                     **kwargs) -> Dict[str, Any]:
        """
        Exécute plusieurs processeurs en parallèle.
        
        Args:
            processors: Liste des processeurs à exécuter
            document_path: Chemin vers le document à traiter
            output_dir: Répertoire de sortie
            **kwargs: Arguments supplémentaires pour les processeurs
            
        Returns:
            Dictionnaire des résultats par processeur
        """
        if not processors:
            logger.warning("Aucun processeur fourni pour l'exécution parallèle")
            return {}
        
        logger.info(f"Exécution parallèle de {len(processors)} processeurs avec {self.max_workers} workers")
        
        # Préparer les tâches
        processing_tasks = []
        processor_names = []
        
        for processor in processors:
            processor_name = processor.__class__.__name__
            processor_names.append(processor_name)
            
            # Créer un répertoire spécifique pour ce processeur
            processor_output_dir = output_dir / processor_name
            processor_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Créer la tâche
            task = self._create_processing_task(
                processor, 
                document_path, 
                processor_output_dir,
                **kwargs
            )
            
            processing_tasks.append(task)
        
        # Exécuter les tâches en parallèle
        start_time = time.time()
        results = {}
        
        # Utiliser gather pour exécuter toutes les tâches en parallèle
        gathered_results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        
        # Associer les résultats aux processeurs
        for i, result in enumerate(gathered_results):
            processor_name = processor_names[i]
            
            if isinstance(result, Exception):
                logger.error(f"Erreur lors de l'exécution du processeur {processor_name}: {str(result)}")
                results[processor_name] = {
                    "success": False,
                    "error": str(result),
                    "content": {},
                    "metadata": {"error_type": type(result).__name__}
                }
            else:
                results[processor_name] = result
        
        elapsed_time = time.time() - start_time
        logger.info(f"Exécution parallèle terminée en {elapsed_time:.2f} secondes")
        
        return results
    
    async def _create_processing_task(self,
                                     processor: SpecializedProcessor,
                                     document_path: Path,
                                     output_dir: Path,
                                     **kwargs) -> Dict[str, Any]:
        """
        Crée une tâche d'exécution pour un processeur.
        
        Args:
            processor: Processeur à exécuter
            document_path: Chemin vers le document
            output_dir: Répertoire de sortie
            **kwargs: Arguments supplémentaires
            
        Returns:
            Résultat du traitement
        """
        loop = asyncio.get_event_loop()
        processor_name = processor.__class__.__name__
        
        try:
            # Exécuter le processeur dans un thread séparé pour ne pas bloquer la boucle d'événements
            logger.info(f"Démarrage du processeur {processor_name} pour {document_path}")
            
            # Utiliser run_in_executor pour les opérations bloquantes
            result = await loop.run_in_executor(
                self.executor,
                lambda: processor.process_document(
                    document_path=document_path,
                    output_dir=output_dir,
                    **kwargs
                )
            )
            
            logger.info(f"Processeur {processor_name} terminé avec succès")
            return result
            
        except Exception as e:
            logger.error(f"Erreur dans le processeur {processor_name}: {str(e)}")
            raise e
