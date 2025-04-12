"""
API pour le traitement de documents.
Permet de traiter des documents via des endpoints REST.
"""

import logging
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import asyncio

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.core.file_processing.document_processor import get_document_processor
from app.core.tasks.document_processing_tasks import (
    process_document_task,
    batch_process_documents_task,
    process_and_index_document_task
)
from app.dependencies.auth import get_current_user
from app.utils.file_utils import save_upload_file, get_temp_file_path

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Document Processing"],
    responses={404: {"description": "Not found"}},
)

class DocumentProcessingOptions(BaseModel):
    """Options pour le traitement de documents."""
    
    chunk_size: Optional[int] = Field(
        default=None, 
        description="Taille maximale d'un chunk (nombre de caractères)"
    )
    chunk_overlap: Optional[int] = Field(
        default=None, 
        description="Chevauchement entre les chunks consécutifs"
    )
    enable_ocr: Optional[bool] = Field(
        default=None, 
        description="Activer l'OCR pour les documents numérisés"
    )
    extract_tables: Optional[bool] = Field(
        default=None, 
        description="Extraire les tableaux des documents (PDFs)"
    )
    include_text_content: Optional[bool] = Field(
        default=False, 
        description="Inclure le contenu textuel complet dans la réponse"
    )
    skip_chunking: Optional[bool] = Field(
        default=False, 
        description="Ignorer l'étape de chunking"
    )

class IndexingOptions(BaseModel):
    """Options pour l'indexation de documents."""
    
    collection_name: Optional[str] = Field(
        default=None, 
        description="Nom de la collection où indexer le document"
    )
    embedding_provider: Optional[str] = Field(
        default=None, 
        description="Provider d'embeddings à utiliser"
    )
    metadata_fields: Optional[List[str]] = Field(
        default=None, 
        description="Champs de métadonnées à inclure dans l'indexation"
    )

@router.post("/process", summary="Traite un document")
async def process_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: Optional[str] = Form(None),
    synchronous: bool = Form(False),
    current_user = Depends(get_current_user),
):
    """
    Traite un document en l'extrayant et le découpant en chunks.
    
    Args:
        file: Fichier à traiter
        options: Options de traitement au format JSON
        synchronous: Si True, le traitement est synchrone, sinon asynchrone via Celery
        
    Returns:
        Résultat du traitement ou ID de la tâche Celery
    """
    start_time = time.time()
    
    # Vérifier que le fichier est fourni
    if not file:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    # Parser les options JSON si fournies
    processing_options = {}
    if options:
        import json
        try:
            processing_options = json.loads(options)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Options JSON invalides")
    
    # Sauvegarder le fichier temporairement
    temp_file_path = await save_upload_file(file)
    
    try:
        if synchronous:
            # Traitement synchrone
            logger.info(f"Traitement synchrone du document: {file.filename}")
            
            # Obtenir le processeur de documents
            processor = await get_document_processor()
            
            # Traiter le document
            result = await processor.process_document(
                file_path=temp_file_path,
                **processing_options
            )
            
            # Préparer la réponse
            response = {
                "success": result.success,
                "metadata": result.metadata,
                "processing_time": time.time() - start_time,
                "chunks_count": len(result.chunks) if result.success else 0,
            }
            
            # Ajouter le texte complet si demandé
            if processing_options.get("include_text_content", False) and result.text_content:
                response["text_content"] = result.text_content
            
            # Ajouter les chunks
            if result.success and not processing_options.get("skip_chunking", False):
                response["chunks"] = result.chunks
            
            # Ajouter l'erreur si échec
            if not result.success:
                response["error_message"] = result.error_message
            
            # Configurer la suppression du fichier temporaire
            background_tasks.add_task(os.unlink, temp_file_path)
            
            return response
        else:
            # Traitement asynchrone avec Celery
            logger.info(f"Traitement asynchrone du document: {file.filename}")
            
            # Lancer la tâche Celery
            task = process_document_task.apply_async(
                kwargs={
                    "file_path": str(temp_file_path),
                    "options": processing_options
                }
            )
            
            # Configurer la suppression du fichier temporaire une fois la tâche terminée
            # Note: Cette approche dépend de la configuration de Celery
            
            return {
                "success": True,
                "task_id": task.id,
                "filename": file.filename,
                "status": "processing"
            }
    
    except Exception as e:
        # Supprimer le fichier temporaire en cas d'erreur
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        logger.exception(f"Erreur lors du traitement du document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

@router.post("/batch-process", summary="Traite un lot de documents")
async def batch_process_documents(
    files: List[UploadFile] = File(...),
    options: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
):
    """
    Traite un lot de documents en parallèle.
    
    Args:
        files: Liste des fichiers à traiter
        options: Options de traitement au format JSON
        
    Returns:
        ID de la tâche Celery pour le traitement par batch
    """
    # Vérifier que des fichiers sont fournis
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    # Parser les options JSON si fournies
    processing_options = {}
    if options:
        import json
        try:
            processing_options = json.loads(options)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Options JSON invalides")
    
    # Sauvegarder les fichiers temporairement
    temp_file_paths = []
    for file in files:
        temp_file_path = await save_upload_file(file)
        temp_file_paths.append(str(temp_file_path))
    
    try:
        # Lancer la tâche Celery pour le traitement par batch
        task = batch_process_documents_task.apply_async(
            kwargs={
                "file_paths": temp_file_paths,
                "options": processing_options
            }
        )
        
        return {
            "success": True,
            "task_id": task.id,
            "files_count": len(files),
            "status": "processing"
        }
    
    except Exception as e:
        # Supprimer les fichiers temporaires en cas d'erreur
        for path in temp_file_paths:
            if os.path.exists(path):
                os.unlink(path)
        
        logger.exception(f"Erreur lors du traitement par batch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement par batch: {str(e)}")

@router.post("/process-and-index", summary="Traite et indexe un document")
async def process_and_index_document(
    file: UploadFile = File(...),
    processing_options: Optional[str] = Form(None),
    indexing_options: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
):
    """
    Traite un document et indexe ses chunks dans la base vectorielle.
    
    Args:
        file: Fichier à traiter et indexer
        processing_options: Options de traitement au format JSON
        indexing_options: Options d'indexation au format JSON
        
    Returns:
        ID de la tâche Celery pour le traitement et l'indexation
    """
    # Vérifier que le fichier est fourni
    if not file:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    # Parser les options JSON si fournies
    proc_options = {}
    if processing_options:
        import json
        try:
            proc_options = json.loads(processing_options)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Options de traitement JSON invalides")
    
    idx_options = {}
    if indexing_options:
        import json
        try:
            idx_options = json.loads(indexing_options)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Options d'indexation JSON invalides")
    
    # Sauvegarder le fichier temporairement
    temp_file_path = await save_upload_file(file)
    
    try:
        # Lancer la tâche Celery pour le traitement et l'indexation
        task = process_and_index_document_task.apply_async(
            kwargs={
                "file_path": str(temp_file_path),
                "processing_options": proc_options,
                "index_options": idx_options
            }
        )
        
        return {
            "success": True,
            "task_id": task.id,
            "filename": file.filename,
            "status": "processing_and_indexing"
        }
    
    except Exception as e:
        # Supprimer le fichier temporaire en cas d'erreur
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        logger.exception(f"Erreur lors du traitement et de l'indexation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement et de l'indexation: {str(e)}")

@router.get("/task/{task_id}", summary="Récupère le statut d'une tâche de traitement")
async def get_task_status(
    task_id: str,
    current_user = Depends(get_current_user),
):
    """
    Récupère le statut d'une tâche de traitement de document.
    
    Args:
        task_id: ID de la tâche Celery
        
    Returns:
        Statut et résultat de la tâche
    """
    # Vérifier la tâche dans Celery
    try:
        from app.core.tasks.celery_app import app as celery_app
        
        # Récupérer le statut de la tâche
        result = celery_app.AsyncResult(task_id)
        
        if result.ready():
            # Tâche terminée
            if result.successful():
                # Tâche réussie
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": result.result
                }
            else:
                # Tâche échouée
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(result.result)
                }
        else:
            # Tâche en cours
            return {
                "task_id": task_id,
                "status": "processing"
            }
    
    except Exception as e:
        logger.exception(f"Erreur lors de la récupération du statut de la tâche {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du statut: {str(e)}")

@router.get("/supported-formats", summary="Liste les formats de fichiers supportés")
async def get_supported_formats():
    """
    Liste les formats de fichiers supportés par le système de traitement.
    
    Returns:
        Liste des formats supportés
    """
    try:
        # Obtenir le processeur de documents
        processor = await get_document_processor()
        
        # Obtenir les formats supportés par le convertisseur
        supported_formats = await processor.converter.supported_file_types()
        
        return {
            "success": True,
            "supported_formats": supported_formats
        }
    
    except Exception as e:
        logger.exception(f"Erreur lors de la récupération des formats supportés: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.post("/analyze", summary="Analyse un document sans le traiter complètement")
async def analyze_document(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
):
    """
    Analyse un document pour déterminer ses caractéristiques sans le traiter complètement.
    
    Args:
        file: Fichier à analyser
        
    Returns:
        Métadonnées et caractéristiques du document
    """
    # Vérifier que le fichier est fourni
    if not file:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    # Sauvegarder le fichier temporairement
    temp_file_path = await save_upload_file(file)
    
    try:
        # Obtenir le processeur de documents
        processor = await get_document_processor()
        
        # Extraire les métadonnées
        metadata = await processor.converter.extract_metadata(temp_file_path)
        
        # Vérifier si le document nécessite OCR (pour les PDFs)
        needs_ocr = False
        if Path(temp_file_path).suffix.lower() == '.pdf' and processor.ocr_processor:
            needs_ocr = await processor.ocr_processor.needs_ocr(temp_file_path)
        
        # Préparer la réponse
        response = {
            "success": True,
            "filename": file.filename,
            "metadata": metadata,
            "needs_ocr": needs_ocr,
            "mime_type": await processor.converter.detect_file_type(temp_file_path)
        }
        
        # Supprimer le fichier temporaire
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        return response
    
    except Exception as e:
        # Supprimer le fichier temporaire en cas d'erreur
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        logger.exception(f"Erreur lors de l'analyse du document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")
