"""
Tâches Celery pour le traitement des documents.
Intègre les services de conversion, OCR et chunking dans un pipeline asynchrone.
"""

import logging
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery.signals import task_failure, task_success, task_retry

from app.config import settings
from app.core.file_processing.document_processor import get_document_processor, DocumentProcessingResult
from app.core.file_processing.ocr.factory import get_ocr_processor, get_smart_processor
from app.core.file_processing.ai_orchestrator import AIOrchestrator
from app.utils.logging_utils import setup_task_logger

logger = logging.getLogger(__name__)

@shared_task(
    name="process_document",
    bind=True,
    max_retries=3,
    soft_time_limit=600,  # 10 minutes
    time_limit=900,       # 15 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
async def process_document_task(
    self,
    file_path: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    enable_ocr: Optional[bool] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tâche Celery qui traite un document en l'extrayant et le découpant en chunks.
    
    Args:
        file_path: Chemin vers le document à traiter
        chunk_size: Taille des chunks (défaut: valeur de configuration)
        chunk_overlap: Chevauchement des chunks (défaut: valeur de configuration)
        enable_ocr: Activer l'OCR pour ce document (défaut: valeur de configuration)
        options: Options additionnelles pour le traitement
            - conversion_options: Options spécifiques à la conversion
            - chunking_options: Options spécifiques au chunking
            - ocr_options: Options spécifiques à l'OCR
            - skip_chunking: Ignorer l'étape de chunking
            - extract_tables: Extraire les tableaux des PDFs
            
    Returns:
        Dictionnaire contenant le résultat du traitement
            - success: Succès de l'opération
            - chunks: Liste des chunks générés (si demandé)
            - text_content: Contenu textuel extrait (si demandé)
            - metadata: Métadonnées du traitement
            - error_message: Message d'erreur le cas échéant
    """
    task_id = self.request.id
    start_time = time.time()
    
    # Configuration du logger pour cette tâche
    task_logger = setup_task_logger(f"document_processing.{task_id}")
    task_logger.info(f"Démarrage du traitement du document: {file_path}")
    
    # Options par défaut
    options = options or {}
    chunk_size = chunk_size or getattr(settings, "DEFAULT_CHUNK_SIZE", 1000)
    chunk_overlap = chunk_overlap or getattr(settings, "DEFAULT_CHUNK_OVERLAP", 100)
    
    # Vérifier l'existence du fichier
    file_path = Path(file_path)
    if not file_path.exists():
        task_logger.error(f"Le fichier {file_path} n'existe pas")
        return {
            "success": False,
            "error_message": f"Le fichier {file_path} n'existe pas",
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time
            }
        }
    
    try:
        # Obtenir le processeur de documents
        processor = await get_document_processor()
        
        # Traiter le document
        result = await processor.process_document(
            file_path=file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            enable_ocr=enable_ocr,
            **options
        )
        
        # Préparer la réponse
        response = {
            "success": result.success,
            "metadata": {
                **result.metadata,
                "task_id": task_id,
                "processing_time": time.time() - start_time
            }
        }
        
        # Ajouter les chunks et le texte si demandés
        if result.success:
            # Inclure le texte complet si explicitement demandé
            if options.get("include_text_content", False):
                response["text_content"] = result.text_content
            
            # Toujours inclure les chunks pour faciliter l'intégration avec le RAG
            response["chunks"] = result.chunks
            
            task_logger.info(f"Traitement réussi: {len(result.chunks)} chunks générés")
        else:
            response["error_message"] = result.error_message
            task_logger.error(f"Échec du traitement: {result.error_message}")
        
        return response
        
    except SoftTimeLimitExceeded:
        task_logger.error(f"Dépassement du délai souple pour le traitement de {file_path}")
        return {
            "success": False,
            "error_message": "Dépassement du délai imparti pour le traitement",
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time,
                "error_type": "SoftTimeLimitExceeded"
            }
        }
    except TimeLimitExceeded:
        task_logger.error(f"Dépassement du délai maximal pour le traitement de {file_path}")
        return {
            "success": False,
            "error_message": "Dépassement du délai maximal pour le traitement",
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time,
                "error_type": "TimeLimitExceeded"
            }
        }
    except Exception as e:
        task_logger.exception(f"Erreur lors du traitement de {file_path}: {str(e)}")
        
        # Décider si on relance la tâche
        current_retry = self.request.retries
        if current_retry < self.max_retries:
            task_logger.info(f"Nouvelle tentative prévue ({current_retry + 1}/{self.max_retries})")
            self.retry(exc=e, countdown=2 ** current_retry * 10)  # Backoff exponentiel
        
        return {
            "success": False,
            "error_message": f"Erreur de traitement: {str(e)}",
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time,
                "error_type": type(e).__name__,
                "retries": current_retry
            }
        }

@shared_task(
    name="batch_process_documents",
    bind=True,
    soft_time_limit=3600,  # 1 heure
    time_limit=4200,       # 1h10
)
async def batch_process_documents_task(
    self,
    file_paths: List[str],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tâche Celery qui traite un lot de documents en parallèle.
    
    Args:
        file_paths: Liste des chemins de fichiers à traiter
        chunk_size: Taille des chunks (défaut: valeur de configuration)
        chunk_overlap: Chevauchement des chunks (défaut: valeur de configuration)
        options: Options additionnelles pour le traitement
            
    Returns:
        Dictionnaire contenant les résultats du traitement par batch
            - success: Succès global de l'opération
            - results: Résultats individuels par fichier
            - metadata: Métadonnées du traitement par batch
    """
    task_id = self.request.id
    start_time = time.time()
    
    # Configuration du logger pour cette tâche
    task_logger = setup_task_logger(f"document_batch.{task_id}")
    task_logger.info(f"Démarrage du traitement par batch de {len(file_paths)} documents")
    
    # Options par défaut
    options = options or {}
    chunk_size = chunk_size or getattr(settings, "DEFAULT_CHUNK_SIZE", 1000)
    chunk_overlap = chunk_overlap or getattr(settings, "DEFAULT_CHUNK_OVERLAP", 100)
    
    # Résultats
    results = []
    success_count = 0
    error_count = 0
    total_chunks = 0
    
    try:
        # Obtenir le processeur de documents
        processor = await get_document_processor()
        
        # Traitement séquentiel (pour éviter de surcharger le système)
        # Note: Pour un traitement vraiment parallèle, on pourrait utiliser asyncio.gather
        for file_path in file_paths:
            task_logger.info(f"Traitement du document: {file_path}")
            
            # Vérifier l'existence du fichier
            if not Path(file_path).exists():
                task_logger.warning(f"Le fichier {file_path} n'existe pas, ignoré")
                results.append({
                    "file_path": file_path,
                    "success": False,
                    "error_message": "Le fichier n'existe pas"
                })
                error_count += 1
                continue
            
            try:
                # Traiter le document
                result = await processor.process_document(
                    file_path=file_path,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    **options
                )
                
                # Ajouter le résultat
                file_result = {
                    "file_path": file_path,
                    "success": result.success,
                    "chunks_count": len(result.chunks) if result.success else 0,
                    "metadata": result.metadata
                }
                
                if not result.success:
                    file_result["error_message"] = result.error_message
                    error_count += 1
                else:
                    success_count += 1
                    total_chunks += len(result.chunks)
                
                results.append(file_result)
                
            except Exception as e:
                task_logger.exception(f"Erreur lors du traitement de {file_path}: {str(e)}")
                results.append({
                    "file_path": file_path,
                    "success": False,
                    "error_message": str(e)
                })
                error_count += 1
        
        # Métadonnées globales
        metadata = {
            "task_id": task_id,
            "processing_time": time.time() - start_time,
            "total_documents": len(file_paths),
            "success_count": success_count,
            "error_count": error_count,
            "total_chunks": total_chunks
        }
        
        task_logger.info(f"Traitement par batch terminé: {success_count} réussis, {error_count} échecs")
        
        return {
            "success": error_count == 0,  # Succès seulement si tous les documents ont réussi
            "results": results,
            "metadata": metadata
        }
        
    except Exception as e:
        task_logger.exception(f"Erreur lors du traitement par batch: {str(e)}")
        
        return {
            "success": False,
            "error_message": f"Erreur de traitement par batch: {str(e)}",
            "results": results,
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time,
                "total_documents": len(file_paths),
                "success_count": success_count,
                "error_count": error_count + 1,  # +1 pour l'erreur globale
                "total_chunks": total_chunks
            }
        }

@shared_task(
    name="process_and_index_document",
    bind=True,
    max_retries=3,
    soft_time_limit=1200,  # 20 minutes
    time_limit=1800,       # 30 minutes
)
async def process_and_index_document_task(
    self,
    file_path: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    enable_ocr: Optional[bool] = None,
    index_options: Optional[Dict[str, Any]] = None,
    processing_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tâche Celery qui traite un document puis indexe ses chunks dans la base vectorielle.
    
    Args:
        file_path: Chemin vers le document à traiter
        chunk_size: Taille des chunks (défaut: valeur de configuration)
        chunk_overlap: Chevauchement des chunks (défaut: valeur de configuration)
        enable_ocr: Activer l'OCR pour ce document (défaut: valeur de configuration)
        index_options: Options spécifiques à l'indexation
            - collection_name: Nom de la collection pour l'indexation
            - metadata_fields: Champs de métadonnées à inclure
            - embedding_provider: Provider d'embeddings à utiliser
        processing_options: Options spécifiques au traitement du document
            
    Returns:
        Dictionnaire contenant le résultat du traitement et de l'indexation
    """
    task_id = self.request.id
    start_time = time.time()
    
    # Configuration du logger pour cette tâche
    task_logger = setup_task_logger(f"process_and_index.{task_id}")
    task_logger.info(f"Démarrage du traitement et de l'indexation du document: {file_path}")
    
    # Options par défaut
    processing_options = processing_options or {}
    index_options = index_options or {}
    chunk_size = chunk_size or getattr(settings, "DEFAULT_CHUNK_SIZE", 1000)
    chunk_overlap = chunk_overlap or getattr(settings, "DEFAULT_CHUNK_OVERLAP", 100)
    
    try:
        # Étape 1: Traiter le document
        task_logger.info(f"Étape 1: Traitement du document {file_path}")
        
        # Obtenir le processeur de documents
        processor = await get_document_processor()
        
        # Traiter le document
        processing_result = await processor.process_document(
            file_path=file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            enable_ocr=enable_ocr,
            **processing_options
        )
        
        if not processing_result.success:
            task_logger.error(f"Échec du traitement du document: {processing_result.error_message}")
            return {
                "success": False,
                "error_message": f"Échec du traitement: {processing_result.error_message}",
                "stage": "processing",
                "metadata": {
                    **processing_result.metadata,
                    "task_id": task_id,
                    "processing_time": time.time() - start_time
                }
            }
        
        # Étape 2: Calculer les embeddings et indexer le document
        task_logger.info(f"Étape 2: Indexation des {len(processing_result.chunks)} chunks")
        
        # Préparer les données pour l'indexation
        chunks = processing_result.chunks
        file_metadata = {
            "filename": Path(file_path).name,
            "path": str(file_path),
            "extension": Path(file_path).suffix.lower(),
            "processing_time": processing_result.metadata.get("processing_time", 0),
            "ocr_processed": processing_result.metadata.get("ocr_processed", False),
        }
        
        # Ajouter des métadonnées spécifiques si nécessaire
        for field in index_options.get("metadata_fields", []):
            if field in processing_result.metadata:
                file_metadata[field] = processing_result.metadata[field]
        
        # Lancer la tâche d'indexation des chunks
        # Note: Cette partie dépend de l'implémentation exacte du système d'embeddings
        from app.core.tasks.embedding_tasks import batch_create_embeddings_task
        
        collection_name = index_options.get("collection_name", getattr(settings, "DEFAULT_COLLECTION", "documents"))
        embedding_provider = index_options.get("embedding_provider", getattr(settings, "EMBEDDING_PROVIDER", "voyage"))
        
        indexing_result = await batch_create_embeddings_task.apply_async(
            kwargs={
                "texts": chunks,
                "collection_name": collection_name,
                "metadata": file_metadata,
                "provider": embedding_provider,
                "batch_size": getattr(settings, "EMBEDDING_BATCH_SIZE", 10)
            }
        )
        
        task_logger.info(f"Traitement et indexation terminés avec succès")
        
        return {
            "success": True,
            "chunks_count": len(chunks),
            "collection_name": collection_name,
            "document_metadata": file_metadata,
            "processing_metadata": processing_result.metadata,
            "indexing_task_id": indexing_result.id,
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time,
                "embedding_provider": embedding_provider
            }
        }
        
    except Exception as e:
        task_logger.exception(f"Erreur lors du traitement et de l'indexation: {str(e)}")
        
        # Décider si on relance la tâche
        current_retry = self.request.retries
        if current_retry < self.max_retries:
            task_logger.info(f"Nouvelle tentative prévue ({current_retry + 1}/{self.max_retries})")
            self.retry(exc=e, countdown=2 ** current_retry * 30)  # Backoff exponentiel plus long
        
        return {
            "success": False,
            "error_message": f"Erreur de traitement et d'indexation: {str(e)}",
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time,
                "error_type": type(e).__name__,
                "retries": current_retry
            }
        }

@shared_task(
    name="process_technical_document",
    bind=True,
    max_retries=3,
    soft_time_limit=1200,  # 20 minutes
    time_limit=1800,       # 30 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
async def process_technical_document_task(
    self,
    file_path: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    ocr_options: Optional[Dict[str, Any]] = None,
    processing_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tâche Celery qui traite un document technique en utilisant l'orchestrateur AI.
    
    Cette tâche utilise l'orchestrateur AI qui combine Document AI et Vision AI pour
    une analyse avancée des documents techniques, incluant la reconnaissance de schémas
    et l'extraction de contenu technique complexe.
    
    Args:
        file_path: Chemin vers le document technique à traiter
        chunk_size: Taille des chunks (défaut: valeur de configuration)
        chunk_overlap: Chevauchement des chunks (défaut: valeur de configuration)
        ocr_options: Options spécifiques pour l'orchestrateur AI
            - document_ai_config: Configuration pour Document AI
            - vision_ai_config: Configuration pour Vision AI
            - extract_images: Extraire les images pour analyse (défaut: True)
            - confidence_threshold: Seuil de confiance pour les résultats
        processing_options: Options additionnelles pour le traitement
            - conversion_options: Options pour la conversion
            - chunking_options: Options pour le chunking
            - include_text_content: Inclure le texte complet dans la réponse
            - output_dir: Répertoire pour les sorties intermédiaires
            
    Returns:
        Dictionnaire contenant le résultat du traitement
            - success: Succès de l'opération
            - chunks: Liste des chunks générés
            - text_content: Contenu textuel extrait (si demandé)
            - technical_elements: Éléments techniques identifiés (schémas, formules, tableaux)
            - metadata: Métadonnées du traitement
            - error_message: Message d'erreur le cas échéant
    """
    task_id = self.request.id
    start_time = time.time()
    
    # Configuration du logger pour cette tâche
    task_logger = setup_task_logger(f"technical_document.{task_id}")
    task_logger.info(f"Démarrage du traitement du document technique: {file_path}")
    
    # Options par défaut
    processing_options = processing_options or {}
    ocr_options = ocr_options or {}
    chunk_size = chunk_size or getattr(settings, "DEFAULT_CHUNK_SIZE", 1000)
    chunk_overlap = chunk_overlap or getattr(settings, "DEFAULT_CHUNK_OVERLAP", 100)
    
    # Vérifier l'existence du fichier
    file_path = Path(file_path)
    if not file_path.exists():
        task_logger.error(f"Le fichier {file_path} n'existe pas")
        return {
            "success": False,
            "error_message": f"Le fichier {file_path} n'existe pas",
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time
            }
        }
    
    try:
        # Déterminer le type de document
        document_type = file_path.suffix.lower().lstrip('.')
        is_technical = processing_options.get("is_technical", True)  # Par défaut, considéré comme technique
        
        # Initialiser l'orchestrateur AI
        orchestrator_config = {
            "document_ai_config": ocr_options.get("document_ai_config", {}),
            "vision_ai_config": ocr_options.get("vision_ai_config", {}),
            "extract_images": ocr_options.get("extract_images", True),
            "confidence_threshold": ocr_options.get("confidence_threshold", 0.7)
        }
        
        # Obtenir le processeur intelligent
        processor = await get_smart_processor(
            document_type=document_type,
            has_images=processing_options.get("has_images", True),
            is_technical=is_technical,
            config=orchestrator_config
        )
        
        # Vérifier si nous avons bien obtenu l'orchestrateur
        if isinstance(processor, AIOrchestrator):
            task_logger.info("Utilisation de l'orchestrateur AI pour le traitement du document technique")
            
            # Préparer le répertoire de sortie
            output_dir = processing_options.get("output_dir")
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(exist_ok=True, parents=True)
            
            # Traiter le document avec l'orchestrateur
            result = await processor.process_document(
                input_file=file_path,
                output_dir=output_dir,
                language=processing_options.get("language", "fra"),
                document_type=processing_options.get("document_type", "technical"),
                **processing_options
            )
            
            # Créer les chunks à partir du texte extrait
            from app.core.file_processing.chunking.factory import get_chunker
            chunker = await get_chunker(
                processor_name=processing_options.get("chunker", "semantic"),
                config=processing_options.get("chunking_options", {})
            )
            
            chunks = []
            if result.get("success", False) and result.get("combined_text"):
                chunks = await chunker.split_text(
                    result["combined_text"],
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                
                # Enrichir les chunks avec les métadonnées techniques
                if "metadata" in result:
                    for chunk in chunks:
                        chunk["metadata"] = {
                            **chunk.get("metadata", {}),
                            "document_path": str(file_path),
                            "is_technical": True,
                            "processing_type": "ai_orchestrator",
                            "ai_metadata": result.get("metadata", {})
                        }
            
            # Préparer la réponse
            response = {
                "success": result.get("success", False),
                "chunks": chunks,
                "metadata": {
                    **result.get("metadata", {}),
                    "task_id": task_id,
                    "processing_time": time.time() - start_time,
                    "chunks_count": len(chunks)
                }
            }
            
            # Ajouter le texte complet si demandé
            if processing_options.get("include_text_content", False) and result.get("combined_text"):
                response["text_content"] = result["combined_text"]
            
            # Ajouter les éléments techniques si disponibles
            if "vision_ai_results" in result and result["vision_ai_results"]:
                technical_elements = []
                for vision_result in result["vision_ai_results"]:
                    if vision_result.get("success", False):
                        # Extraire les éléments techniques détectés
                        elements = {
                            "type": "technical_drawing",
                            "image_path": vision_result.get("image_path", ""),
                            "symbols": vision_result.get("symbol_annotations", []),
                            "objects": vision_result.get("object_annotations", []),
                            "text": vision_result.get("text_annotations", [])[:1]  # Juste le texte principal
                        }
                        technical_elements.append(elements)
                
                if technical_elements:
                    response["technical_elements"] = technical_elements
            
            task_logger.info(f"Traitement technique réussi: {len(chunks)} chunks générés")
            return response
            
        else:
            # Si on n'a pas l'orchestrateur, utiliser le pipeline standard
            task_logger.warning("Orchestrateur AI non disponible, utilisation du pipeline standard")
            processor = await get_document_processor()
            
            # Traiter avec le pipeline standard
            result = await processor.process_document(
                file_path=file_path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                enable_ocr=True,  # Toujours activer l'OCR pour les documents techniques
                **processing_options
            )
            
            # Préparer la réponse
            response = {
                "success": result.success,
                "chunks": result.chunks,
                "metadata": {
                    **result.metadata,
                    "task_id": task_id,
                    "processing_time": time.time() - start_time,
                    "fallback_processing": True
                }
            }
            
            if processing_options.get("include_text_content", False):
                response["text_content"] = result.text_content
                
            task_logger.info(f"Traitement standard (fallback) réussi: {len(result.chunks)} chunks générés")
            return response
            
    except SoftTimeLimitExceeded:
        task_logger.error(f"Dépassement du délai souple pour le traitement de {file_path}")
        return {
            "success": False,
            "error_message": "Dépassement du délai imparti pour le traitement technique",
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time,
                "error_type": "SoftTimeLimitExceeded"
            }
        }
    except TimeLimitExceeded:
        task_logger.error(f"Dépassement du délai maximal pour le traitement de {file_path}")
        return {
            "success": False,
            "error_message": "Dépassement du délai maximal pour le traitement technique",
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time,
                "error_type": "TimeLimitExceeded"
            }
        }
    except Exception as e:
        task_logger.exception(f"Erreur lors du traitement technique de {file_path}: {str(e)}")
        
        # Décider si on relance la tâche
        current_retry = self.request.retries
        if current_retry < self.max_retries:
            task_logger.info(f"Nouvelle tentative prévue ({current_retry + 1}/{self.max_retries})")
            self.retry(exc=e, countdown=2 ** current_retry * 10)  # Backoff exponentiel
        
        return {
            "success": False,
            "error_message": f"Erreur de traitement technique: {str(e)}",
            "metadata": {
                "task_id": task_id,
                "processing_time": time.time() - start_time,
                "error_type": type(e).__name__,
                "retries": current_retry
            }
        }
