"""
Intégration OCR-RAG
=================

Ce module assure l'intégration entre le système OCR et le système RAG.
Il fournit des fonctions pour indexer automatiquement les documents
après leur traitement par OCR.

Principales fonctionnalités:
- Indexation automatique des documents traités par OCR
- Gestion des métadonnées OCR pour le système RAG
- Notification des événements d'indexation

Auteur: Équipe Technicia
Date: Avril 2025
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Union

from app.core.tasks.document_processing_tasks import process_and_index_document_task
from app.config import settings

# Configuration du logger
logger = logging.getLogger(__name__)

async def index_ocr_document(
    document_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    ocr_metadata: Optional[Dict[str, Any]] = None,
    collection_name: Optional[str] = None,
    embedding_provider: Optional[str] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Indexe un document traité par OCR dans le système RAG.
    
    Cette fonction prend un document qui a été traité par OCR et lance le processus
    d'indexation pour l'intégrer dans le système RAG, permettant ainsi de le retrouver
    via les recherches sémantiques.
    
    Args:
        document_path: Chemin du document original
        output_path: Chemin du document traité par OCR (si différent)
        ocr_metadata: Métadonnées du traitement OCR
        collection_name: Nom de la collection pour l'indexation
        embedding_provider: Provider d'embeddings à utiliser
        task_id: ID de la tâche OCR associée (pour la traçabilité)
        
    Returns:
        Dictionnaire contenant le résultat de l'indexation:
            - success: Booléen indiquant le succès de l'opération
            - indexing_task_id: ID de la tâche d'indexation
            - error: Message d'erreur (si échec)
    """
    try:
        # Préparer le chemin du document
        path_to_index = str(output_path) if output_path else str(document_path)
        
        # Préparer les métadonnées
        ocr_metadata = ocr_metadata or {}
        
        # Préparer les options d'indexation
        index_options = {
            "collection_name": collection_name or getattr(settings, "DEFAULT_RAG_COLLECTION", "documents"),
            "embedding_provider": embedding_provider or getattr(settings, "DEFAULT_EMBEDDING_PROVIDER", "voyage"),
            "metadata_fields": ["ocr_quality", "ocr_confidence", "ocr_provider", "ocr_language", "processing_time"]
        }
        
        # Ajouter des métadonnées OCR spécifiques
        processing_options = {
            "skip_ocr": True,  # Le document a déjà été traité par OCR
            "ocr_metadata": {
                "ocr_processed": True,
                "ocr_task_id": task_id,
                **ocr_metadata
            }
        }
        
        # Lancer la tâche d'indexation
        logger.info(f"Lancement de l'indexation du document OCR: {path_to_index}")
        
        result = await process_and_index_document_task.apply_async(
            kwargs={
                "file_path": path_to_index,
                "enable_ocr": False,  # OCR déjà fait
                "index_options": index_options,
                "processing_options": processing_options
            }
        )
        
        # Récupérer l'ID de la tâche d'indexation
        indexing_task_id = result.id
        logger.info(f"Indexation lancée avec succès: {indexing_task_id}")
        
        return {
            "success": True,
            "indexing_task_id": indexing_task_id,
            "document": path_to_index
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'indexation du document OCR: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "document": str(document_path)
        }

async def register_ocr_rag_integration() -> None:
    """
    Enregistre les callbacks d'intégration OCR-RAG.
    
    Cette fonction configure les points d'intégration entre le système OCR
    et le système RAG, notamment en enregistrant un callback qui sera appelé
    après chaque tâche OCR complétée avec succès.
    """
    from app.core.tasks.ocr_queue_manager import get_ocr_queue_manager
    
    # Obtenir l'instance du gestionnaire de file d'attente OCR
    ocr_manager = get_ocr_queue_manager()
    
    # Définir le callback de notification
    async def ocr_completed_callback(task_id: str, task_info: Dict[str, Any]) -> None:
        # Vérifier si la tâche est terminée avec succès
        if task_info.get("status") == "completed":
            logger.info(f"Tâche OCR {task_id} terminée, lancement de l'indexation")
            
            # Extraire les informations nécessaires
            document_path = task_info.get("document_path")
            output_path = task_info.get("output_path")
            
            # Préparer les métadonnées OCR pour l'indexation
            ocr_metadata = {
                "ocr_quality": task_info.get("ocr_quality", 0),
                "ocr_confidence": task_info.get("ocr_confidence", 0),
                "ocr_provider": task_info.get("ocr_provider", "unknown"),
                "ocr_language": task_info.get("language", "unknown"),
                "processing_time": task_info.get("processing_time", 0),
                "pages_count": task_info.get("pages_count", 0)
            }
            
            # Lancer l'indexation
            await index_ocr_document(
                document_path=document_path,
                output_path=output_path,
                ocr_metadata=ocr_metadata,
                task_id=task_id
            )
    
    # Enregistrer le callback
    ocr_manager.register_notification_callback(ocr_completed_callback)
    logger.info("Intégration OCR-RAG enregistrée avec succès")
    
async def unregister_ocr_rag_integration() -> None:
    """
    Désenregistre les callbacks d'intégration OCR-RAG.
    """
    # Cette fonction peut être étendue si nécessaire pour nettoyer les ressources
    pass
