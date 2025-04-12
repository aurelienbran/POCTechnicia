"""
Système de File d'Attente OCR (OCR Queue System)
===============================================

Ce module implémente un système robuste pour le traitement par lots des documents volumineux
nécessitant un OCR. Il résout spécifiquement les problèmes de timeout rencontrés avec les
fichiers de grande taille (>28 Mo) en divisant le traitement en chunks gérables.

Caractéristiques principales:
- Division automatique des documents en chunks de taille configurable
- Traitement parallèle des chunks via Celery
- Gestion de l'état des tâches avec checkpoints et reprise après erreur
- Fusion automatique des résultats

Utilisation typique:
```python
# Utilisation synchrone
queue_manager = OCRQueueManager({"chunk_size": 5})
result = await queue_manager.process_document_in_chunks(
    "path/to/large_document.pdf",
    ocr_provider="auto",
    language="fra"
)

# Utilisation asynchrone avec Celery
task_id = process_document_chunked(
    "path/to/large_document.pdf",
    chunk_size=5,
    ocr_provider="auto",
    language="fra"
)
```

Auteur: Équipe Technicia
Date: Mars 2025
"""

import os
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import uuid
from functools import partial

from celery import Task, chain, group, chord
from kombu.utils.uuid import uuid as celery_uuid

from app.config import settings
from app.core.tasks.celery_app import celery_app
from app.core.tasks.error_handling import TaskManager, TaskState, with_error_handling, TaskCheckpoint
from app.core.file_processing.ocr.base import OCRResult

logger = logging.getLogger(__name__)

@dataclass
class OCRChunk:
    """
    Chunk de document pour traitement OCR par lots.
    
    Attributes:
        document_path (Path): Chemin vers le document
        output_path (Optional[Path]): Chemin de sortie pour le chunk
        start_page (int): Première page du chunk (0-indexed)
        end_page (int): Dernière page du chunk (0-indexed)
        chunk_id (str): ID unique du chunk
        processed (bool): Indicateur de traitement du chunk
        result (Optional[OCRResult]): Résultat du traitement OCR
    """
    document_path: Path
    output_path: Optional[Path] = None
    start_page: int = 0
    end_page: int = 0
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    processed: bool = False
    result: Optional[OCRResult] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le chunk en dictionnaire.
        
        Returns:
            Dictionnaire représentant le chunk
        """
        return {
            "document_path": str(self.document_path),
            "output_path": str(self.output_path) if self.output_path else None,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "chunk_id": self.chunk_id,
            "processed": self.processed
        }

class OCRQueueManager:
    """
    Gestionnaire de file d'attente pour tâches OCR.
    Permet de traiter efficacement les documents volumineux en les divisant en chunks.
    
    Attributes:
        config (Optional[Dict[str, Any]]): Configuration optionnelle
        task_manager (TaskManager): Gestionnaire de tâches
        chunk_size (int): Taille par défaut des chunks (en nombre de pages)
        chunk_timeout (int): Timeout par défaut pour le traitement d'un chunk (en secondes)
        temp_dir (Path): Répertoire temporaire pour les chunks
    """
    
    # Taille par défaut des chunks (en nombre de pages)
    DEFAULT_CHUNK_SIZE = 5
    
    # Timeout par défaut pour le traitement d'un chunk (en secondes)
    DEFAULT_CHUNK_TIMEOUT = 300  # 5 minutes
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le gestionnaire de file d'attente.
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
        self.task_manager = TaskManager()
        
        # Paramètres de chunking
        self.chunk_size = self.config.get("chunk_size", self.DEFAULT_CHUNK_SIZE)
        self.chunk_timeout = self.config.get("chunk_timeout", self.DEFAULT_CHUNK_TIMEOUT)
        
        # Répertoire temporaire pour les chunks
        self.temp_dir = Path(self.config.get("temp_dir", settings.TEMP_DIR or "temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def split_document(self, document_path: Union[str, Path],
                        output_dir: Optional[Union[str, Path]] = None,
                        chunk_size: Optional[int] = None) -> List[OCRChunk]:
        """
        Divise un document en chunks pour traitement par lots.
        
        Args:
            document_path: Chemin vers le document
            output_dir: Répertoire de sortie pour les chunks
            chunk_size: Taille des chunks (en nombre de pages)
            
        Returns:
            Liste des chunks créés
        """
        document_path = Path(document_path)
        
        if not document_path.exists():
            raise FileNotFoundError(f"Document non trouvé: {document_path}")
        
        # Déterminer le nombre de pages
        total_pages = await self._get_page_count(document_path)
        
        if total_pages == 0:
            raise ValueError(f"Impossible de déterminer le nombre de pages pour {document_path}")
        
        # Déterminer la taille des chunks
        chunk_size = chunk_size or self.chunk_size
        
        # Créer le répertoire de sortie
        if output_dir:
            output_dir = Path(output_dir)
        else:
            output_dir = self.temp_dir / f"{document_path.stem}_chunks_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Créer les chunks
        chunks = []
        for i in range(0, total_pages, chunk_size):
            start_page = i
            end_page = min(i + chunk_size - 1, total_pages - 1)
            
            chunk = OCRChunk(
                document_path=document_path,
                output_path=output_dir / f"chunk_{start_page+1}_{end_page+1}.pdf",
                start_page=start_page,
                end_page=end_page
            )
            
            chunks.append(chunk)
        
        logger.info(f"Document {document_path} divisé en {len(chunks)} chunks")
        return chunks
    
    async def _get_page_count(self, document_path: Path) -> int:
        """
        Détermine le nombre de pages d'un document.
        
        Args:
            document_path: Chemin vers le document
            
        Returns:
            Nombre de pages
        """
        if document_path.suffix.lower() == '.pdf':
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(document_path))
                return len(doc)
            except ImportError:
                logger.warning("PyMuPDF non disponible, utilisation de méthode alternative")
                try:
                    from pdf2image.pdf2image import pdfinfo_from_path
                    info = pdfinfo_from_path(document_path)
                    return info["Pages"]
                except:
                    logger.error(f"Impossible de déterminer le nombre de pages pour {document_path}")
                    return 0
        elif document_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            # Images = 1 page
            return 1
        else:
            # Pour les autres types de documents, considérer 1 page par défaut
            return 1
    
    async def _extract_chunk(self, document_path: Path, 
                         output_path: Path,
                         start_page: int,
                         end_page: int) -> bool:
        """
        Extrait un chunk de pages d'un document.
        
        Args:
            document_path: Chemin vers le document
            output_path: Chemin de sortie pour le chunk
            start_page: Première page (0-indexed)
            end_page: Dernière page (0-indexed)
            
        Returns:
            True si l'extraction a réussi
        """
        if document_path.suffix.lower() == '.pdf':
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(document_path))
                chunk_doc = fitz.open()
                
                for i in range(start_page, end_page + 1):
                    if i < len(doc):
                        chunk_doc.insert_pdf(doc, from_page=i, to_page=i)
                
                chunk_doc.save(str(output_path))
                return True
            except Exception as e:
                logger.error(f"Erreur lors de l'extraction du chunk {start_page}-{end_page}: {str(e)}")
                return False
        else:
            # Pour les autres types de documents, simplement copier le fichier
            import shutil
            shutil.copy2(document_path, output_path)
            return True
    
    @with_error_handling(max_retries=2, timeout=600)
    async def process_chunk(self, chunk: OCRChunk,
                         ocr_provider: str = "auto",
                         language: str = "fra",
                         task_id: Optional[str] = None,
                         task_manager: Optional[TaskManager] = None,
                         **kwargs) -> OCRResult:
        """
        Traite un chunk de document avec OCR.
        
        Args:
            chunk: Chunk à traiter
            ocr_provider: Provider OCR à utiliser
            language: Code de langue pour OCR
            task_id: ID de tâche pour le suivi
            task_manager: Gestionnaire de tâches
            **kwargs: Options supplémentaires pour l'OCR
            
        Returns:
            Résultat du traitement OCR
        """
        from app.core.file_processing.ocr.factory import get_ocr_processor
        from app.core.file_processing.ocr.ocr_selector import OCRSelector
        
        # Mettre à jour la progression
        if task_manager:
            task_manager.update_task_progress(
                task_id,
                progress=0.1,
                current_page=chunk.start_page,
                total_pages=chunk.end_page,
                state=TaskState.RUNNING
            )
        
        # Extraire le chunk si nécessaire
        if not await self._extract_chunk(
            chunk.document_path,
            chunk.output_path,
            chunk.start_page,
            chunk.end_page
        ):
            return OCRResult(
                success=False,
                error_message=f"Échec de l'extraction du chunk {chunk.start_page}-{chunk.end_page}"
            )
        
        # Sélectionner le provider OCR approprié
        if ocr_provider == "auto":
            selector = OCRSelector()
            await selector.initialize()
            ocr_provider, _ = await selector.select_ocr_method(chunk.output_path)
        
        # Obtenir le processeur OCR
        processor = await get_ocr_processor(ocr_provider)
        
        # Traiter le chunk avec OCR
        progress_callback = None
        if task_manager:
            # Fonction de callback pour mise à jour de progression
            def update_progress(current_page, total_pages):
                nonlocal task_manager, task_id, chunk
                progress = (current_page / total_pages) if total_pages > 0 else 0
                task_manager.update_task_progress(
                    task_id,
                    progress=0.1 + 0.8 * progress,
                    current_page=chunk.start_page + current_page,
                    total_pages=chunk.end_page
                )
            
            progress_callback = update_progress
        
        # Traiter le document
        result = await processor.process_document(
            chunk.output_path,
            language=language,
            progress_callback=progress_callback,
            **kwargs
        )
        
        # Mettre à jour la progression
        if task_manager:
            task_manager.update_task_progress(
                task_id,
                progress=0.9,
                current_page=chunk.end_page,
                total_pages=chunk.end_page
            )
        
        # Mettre à jour le chunk
        chunk.processed = True
        chunk.result = result
        
        # Créer un checkpoint
        if task_manager:
            task_manager.create_checkpoint(
                task_id,
                state={"chunk": chunk.to_dict(), "result": result.to_dict()},
                current_page=chunk.end_page,
                total_pages=chunk.end_page
            )
            
            task_manager.update_task_progress(
                task_id,
                progress=1.0,
                state=TaskState.COMPLETED
            )
        
        return result
    
    @with_error_handling(max_retries=3, timeout=7200)  # 2 heures max
    async def process_document_in_chunks(self, document_path: Union[str, Path],
                                    output_path: Optional[Union[str, Path]] = None,
                                    chunk_size: Optional[int] = None,
                                    ocr_provider: str = "auto",
                                    language: str = "fra",
                                    task_id: Optional[str] = None,
                                    task_manager: Optional[TaskManager] = None,
                                    **kwargs) -> OCRResult:
        """
        Traite un document en le divisant en chunks.
        
        Args:
            document_path: Chemin vers le document
            output_path: Chemin de sortie pour le document traité
            chunk_size: Taille des chunks (en nombre de pages)
            ocr_provider: Provider OCR à utiliser
            language: Code de langue pour OCR
            task_id: ID de tâche pour le suivi
            task_manager: Gestionnaire de tâches
            **kwargs: Options supplémentaires pour l'OCR
            
        Returns:
            Résultat du traitement OCR
        """
        document_path = Path(document_path)
        
        if not document_path.exists():
            raise FileNotFoundError(f"Document non trouvé: {document_path}")
        
        # Déterminer le chemin de sortie
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = document_path.parent / f"{document_path.stem}_ocr{document_path.suffix}"
        
        # Mettre à jour la progression
        if task_manager:
            task_manager.update_task_progress(
                task_id,
                progress=0.05,
                state=TaskState.RUNNING
            )
        
        # Diviser le document en chunks
        chunks = await self.split_document(
            document_path,
            chunk_size=chunk_size
        )
        
        if not chunks:
            return OCRResult(
                success=False,
                error_message=f"Échec de la division du document {document_path} en chunks"
            )
        
        # Créer un checkpoint
        if task_manager:
            task_manager.create_checkpoint(
                task_id,
                state={"chunks": [c.to_dict() for c in chunks]},
                current_page=0,
                total_pages=chunks[-1].end_page + 1
            )
            
            task_manager.update_task_progress(
                task_id,
                progress=0.1,
                current_page=0,
                total_pages=chunks[-1].end_page + 1
            )
        
        # Traiter chaque chunk
        results = []
        for i, chunk in enumerate(chunks):
            try:
                # Mettre à jour la progression
                if task_manager:
                    progress = 0.1 + 0.8 * (i / len(chunks))
                    task_manager.update_task_progress(
                        task_id,
                        progress=progress,
                        current_page=chunk.start_page,
                        total_pages=chunks[-1].end_page + 1
                    )
                
                # Créer un sous-ID de tâche pour ce chunk
                chunk_task_id = f"{task_id}_chunk_{i}" if task_id else None
                
                # Traiter le chunk
                result = await self.process_chunk(
                    chunk,
                    ocr_provider=ocr_provider,
                    language=language,
                    task_id=chunk_task_id,
                    task_manager=task_manager,
                    **kwargs
                )
                
                results.append(result)
                
                # Vérifier si l'OCR a réussi
                if not result.success:
                    logger.warning(f"Échec du traitement OCR pour le chunk {i} ({chunk.start_page}-{chunk.end_page})")
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement du chunk {i}: {str(e)}")
                # Continuer avec le chunk suivant
        
        # Fusionner les résultats
        if all(r.success for r in results):
            # Fusionner les PDF traités
            merged_result = await self._merge_results(chunks, output_path)
            
            if merged_result:
                # Mettre à jour la progression
                if task_manager:
                    task_manager.update_task_progress(
                        task_id,
                        progress=1.0,
                        current_page=chunks[-1].end_page + 1,
                        total_pages=chunks[-1].end_page + 1,
                        state=TaskState.COMPLETED
                    )
                
                # Calculer le temps total de traitement
                total_time = sum(r.processing_time for r in results)
                
                return OCRResult(
                    success=True,
                    output_path=output_path,
                    text_content=None,  # À extraire séparément
                    pages_processed=chunks[-1].end_page + 1,
                    total_pages=chunks[-1].end_page + 1,
                    processing_time=total_time,
                    metadata={"chunked_processing": True, "chunks": len(chunks)}
                )
        
        # Si au moins un chunk a été traité avec succès, fusionner ceux qui ont réussi
        successful_chunks = [chunks[i] for i, result in enumerate(results) if result.success]
        if successful_chunks:
            merged_result = await self._merge_results(successful_chunks, output_path)
            
            if merged_result:
                # Mettre à jour la progression
                if task_manager:
                    task_manager.update_task_progress(
                        task_id,
                        progress=0.95,
                        state=TaskState.COMPLETED
                    )
                
                # Calculer le temps total de traitement
                successful_results = [r for r in results if r.success]
                total_time = sum(r.processing_time for r in successful_results)
                
                return OCRResult(
                    success=True,
                    output_path=output_path,
                    text_content=None,  # À extraire séparément
                    pages_processed=sum(chunk.end_page - chunk.start_page + 1 for chunk in successful_chunks),
                    total_pages=chunks[-1].end_page + 1,
                    processing_time=total_time,
                    error_message="Certains chunks n'ont pas pu être traités",
                    metadata={"chunked_processing": True, "chunks": len(chunks), "successful_chunks": len(successful_chunks)}
                )
        
        # Si tous les chunks ont échoué
        return OCRResult(
            success=False,
            error_message=f"Échec du traitement OCR pour tous les chunks du document {document_path}"
        )
    
    async def _merge_results(self, chunks: List[OCRChunk], output_path: Path) -> bool:
        """
        Fusionne les résultats des chunks.
        
        Args:
            chunks: Liste des chunks traités
            output_path: Chemin de sortie pour le document fusionné
            
        Returns:
            True si la fusion a réussi
        """
        if not chunks:
            return False
        
        try:
            import fitz  # PyMuPDF
            
            # Ouvrir un nouveau document
            merged_doc = fitz.open()
            
            # Ajouter chaque chunk dans l'ordre
            for chunk in sorted(chunks, key=lambda c: c.start_page):
                if chunk.output_path.exists() and chunk.processed:
                    chunk_doc = fitz.open(str(chunk.output_path))
                    merged_doc.insert_pdf(chunk_doc)
            
            # Sauvegarder le document fusionné
            merged_doc.save(str(output_path))
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la fusion des chunks: {str(e)}")
            return False

# Tâches Celery pour l'intégration avec le système de file d'attente
@celery_app.task(bind=True, name='app.core.tasks.ocr_queue.process_chunk_task')
def process_chunk_task(self, chunk_dict, ocr_provider="auto", language="fra", **kwargs):
    """
    Tâche Celery pour traiter un chunk de document.
    
    Args:
        chunk_dict: Dictionnaire représentant le chunk
        ocr_provider: Provider OCR à utiliser
        language: Code de langue pour OCR
        **kwargs: Options supplémentaires
        
    Returns:
        Résultat du traitement OCR
    """
    # Convertir le dictionnaire en OCRChunk
    chunk = OCRChunk(
        document_path=Path(chunk_dict["document_path"]),
        output_path=Path(chunk_dict["output_path"]) if chunk_dict.get("output_path") else None,
        start_page=chunk_dict["start_page"],
        end_page=chunk_dict["end_page"],
        chunk_id=chunk_dict.get("chunk_id", "")
    )
    
    # Créer le gestionnaire de queue
    queue_manager = OCRQueueManager()
    
    # Exécuter la fonction de traitement de chunk de manière synchrone
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(
        queue_manager.process_chunk(
            chunk,
            ocr_provider=ocr_provider,
            language=language,
            task_id=self.request.id,
            **kwargs
        )
    )
    
    # Retourner le résultat
    return result.to_dict()

@celery_app.task(bind=True, name='app.core.tasks.ocr_queue.merge_chunks_task')
def merge_chunks_task(self, chunk_results, output_path, document_path):
    """
    Tâche Celery pour fusionner les résultats des chunks.
    
    Args:
        chunk_results: Liste des résultats des chunks
        output_path: Chemin de sortie pour le document fusionné
        document_path: Chemin vers le document
        
    Returns:
        Résultat de la fusion
    """
    # Convertir les résultats en OCRChunk
    chunks = []
    for i, result_dict in enumerate(chunk_results):
        # Récupérer le chemin de sortie du chunk
        chunk_output = result_dict.get("output_path")
        if not chunk_output:
            continue
        
        # Créer le chunk
        chunk = OCRChunk(
            document_path=Path(document_path),
            output_path=Path(chunk_output),
            start_page=i,  # Approximatif
            end_page=i,    # Approximatif
            processed=True
        )
        
        chunks.append(chunk)
    
    # Créer le gestionnaire de queue
    queue_manager = OCRQueueManager()
    
    # Fusionner les chunks
    loop = asyncio.get_event_loop()
    success = loop.run_until_complete(queue_manager._merge_results(chunks, Path(output_path)))
    
    if not success:
        raise Exception(f"Échec de la fusion des chunks pour {document_path}")
    
    # Créer un résultat
    return {
        "success": True,
        "output_path": output_path,
        "pages_processed": len(chunks),
        "total_pages": len(chunks),
        "processing_time": sum(r.get("processing_time", 0) for r in chunk_results),
        "metadata": {"chunked_processing": True, "chunks": len(chunks)}
    }

def process_document_chunked(document_path, output_path=None, chunk_size=5, 
                           ocr_provider="auto", language="fra", **kwargs):
    """
    Traite un document en chunks via Celery.
    Cette fonction est la façade pour le traitement OCR asynchrone par lots.
    
    Args:
        document_path: Chemin vers le document
        output_path: Chemin de sortie
        chunk_size: Taille des chunks
        ocr_provider: Provider OCR
        language: Code de langue
        **kwargs: Options supplémentaires
        
    Returns:
        ID de tâche Celery
    """
    document_path = str(Path(document_path).absolute())
    
    if output_path:
        output_path = str(Path(output_path).absolute())
    else:
        output_path = str(Path(document_path).parent / f"{Path(document_path).stem}_ocr{Path(document_path).suffix}")
    
    # Créer le gestionnaire de queue
    queue_manager = OCRQueueManager({"chunk_size": chunk_size})
    
    # Obtenir le nombre de pages de façon synchrone
    loop = asyncio.get_event_loop()
    page_count = loop.run_until_complete(queue_manager._get_page_count(Path(document_path)))
    
    # Calculer les chunks
    chunks = []
    for i in range(0, page_count, chunk_size):
        start_page = i
        end_page = min(i + chunk_size - 1, page_count - 1)
        
        # Créer le répertoire temporaire
        temp_dir = Path(settings.TEMP_DIR or "temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Créer le chemin de sortie pour le chunk
        chunk_output = temp_dir / f"{Path(document_path).stem}_chunk_{start_page+1}_{end_page+1}.pdf"
        
        # Créer le chunk
        chunk_dict = {
            "document_path": document_path,
            "output_path": str(chunk_output),
            "start_page": start_page,
            "end_page": end_page,
            "chunk_id": f"chunk_{start_page}_{end_page}"
        }
        
        chunks.append(chunk_dict)
    
    # Créer la tâche Celery pour le traitement
    task_group = group(
        process_chunk_task.s(chunk, ocr_provider, language, **kwargs)
        for chunk in chunks
    )
    
    # Ajouter la tâche de fusion des résultats
    workflow = chord(
        task_group,
        merge_chunks_task.s(output_path, document_path)
    )
    
    # Lancer le workflow
    async_result = workflow.apply_async()
    
    return async_result.id
