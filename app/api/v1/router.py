from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Body
from fastapi.responses import JSONResponse
from typing import List, Optional
import time
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
import os
import logging
import psutil
from app.config import settings  # Correction de l'import
import asyncio

logger = logging.getLogger(__name__)

from app.core.rag_engine import RAGEngine
from app.schemas import (
    ProcessingStats,
    QueryRequest,
    QueryResponse,
    CollectionStats,
    ErrorResponse,
    Source
)
from app.core.vector_store import VectorStore  # Import VectorStore

router = APIRouter()

def cleanup_temp_file(file_path: str):
    """Nettoie le fichier temporaire."""
    try:
        os.unlink(file_path)
    except Exception as e:
        print(f"Erreur lors du nettoyage du fichier temporaire {file_path}: {str(e)}")

async def get_rag_engine():
    """Dépendance pour obtenir une instance de RAGEngine."""
    engine = RAGEngine()
    await engine.initialize()  # Initialiser le RAGEngine
    try:
        yield engine
    finally:
        # Nettoyage si nécessaire
        pass

async def get_vector_store():
    """Dépendance pour obtenir une instance de VectorStore."""
    vector_store = VectorStore()
    await vector_store.ensure_initialized()  # Initialiser le VectorStore
    try:
        yield vector_store
    finally:
        # Nettoyage si nécessaire
        pass

# Variables globales pour le statut d'indexation
indexing_status = {
    "in_progress": False,
    "total_files": 0,
    "processed_files": 0,
    "total_chunks": 0,
    "indexed_chunks": 0,
    "files_progress": 0,
    "chunks_progress": 0,
    "error": None,
    "processing_stats": {},
    "current_file": None,
    "last_update": None
}

# Verrou global pour éviter les traitements simultanés
processing_lock = asyncio.Lock()

async def update_indexing_status(
    in_progress: bool = None,
    total_files: int = None,
    processed_files: int = None,
    total_chunks: int = None,
    indexed_chunks: int = None,
    error: str = None,
    processing_stats: dict = None,
    current_file: str = None
):
    """Met à jour le statut de l'indexation avec des métriques détaillées."""
    global indexing_status
    
    if indexing_status is None:
        indexing_status = {}
    
    if in_progress is not None:
        indexing_status['in_progress'] = in_progress
    if total_files is not None:
        indexing_status['total_files'] = total_files
    if processed_files is not None:
        indexing_status['processed_files'] = processed_files
    if total_chunks is not None:
        indexing_status['total_chunks'] = total_chunks
    if indexed_chunks is not None:
        indexing_status['indexed_chunks'] = indexed_chunks
    if error is not None:
        indexing_status['error'] = error
        indexing_status['error_occurred'] = True
        indexing_status['error_message'] = error
        logger.error(f"Erreur d'indexation: {error}")
    if processing_stats is not None:
        indexing_status['processing_stats'] = processing_stats
    if current_file is not None:
        indexing_status['current_file'] = current_file
        
    # Calculer les pourcentages de progression
    if total_files and processed_files:
        indexing_status['files_progress'] = (processed_files / total_files) * 100
    if total_chunks and indexed_chunks:
        indexing_status['chunks_progress'] = (indexed_chunks / total_chunks) * 100
        
    # Ajouter un timestamp
    indexing_status['last_update'] = datetime.now().isoformat()

async def process_document_task(tmp_path: Path, rag_engine: RAGEngine):
    """Tâche de traitement du document en arrière-plan avec gestion robuste des erreurs."""
    if indexing_status["in_progress"]:
        error_msg = "Un document est déjà en cours de traitement"
        logger.error(error_msg)
        raise HTTPException(status_code=409, detail=error_msg)
        
    try:
        async with processing_lock:
            start_time = time.time()
            
            # Initialiser le statut d'indexation
            await update_indexing_status(
                in_progress=True,
                total_files=1,
                processed_files=0,
                total_chunks=0,
                indexed_chunks=0,
                current_file=tmp_path.name
            )
            
            # Traiter le document
            stats_dict = await rag_engine.process_document(tmp_path)
            
            # Convertir le dictionnaire en ProcessingStats
            stats = ProcessingStats(
                document=stats_dict['document'],
                chunks_processed=stats_dict['chunks_processed'],
                chunks_indexed=stats_dict['chunks_indexed'],
                processing_time=time.time() - start_time
            )
            
            # Mettre à jour le statut avec les statistiques complètes
            await update_indexing_status(
                in_progress=False,
                processed_files=1,
                total_chunks=stats.chunks_processed,
                indexed_chunks=stats.chunks_indexed,
                processing_stats={
                    'processing_time': stats.processing_time,
                    'success_rate': stats_dict.get('success_rate', 1.0),
                    'metadata': stats_dict.get('metadata', {}),
                    'memory_usage': psutil.Process().memory_info().rss / (1024 * 1024),  # En MB
                    'processing_speed': stats.chunks_processed / stats.processing_time if stats.processing_time > 0 else 0
                }
            )
            
            return stats
            
    except Exception as e:
        error_msg = f"Erreur lors du traitement du document: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await update_indexing_status(
            in_progress=False,
            error=error_msg
        )
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        # Nettoyage du fichier temporaire
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du fichier temporaire: {str(e)}")

@router.post("/documents", response_model=ProcessingStats)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Fichier PDF à traiter"),
    rag_engine: RAGEngine = Depends(get_rag_engine)
):
    """
    Traite un document PDF et l'indexe dans le vector store avec validation robuste.
    """
    # Vérifier qu'aucun traitement n'est en cours
    if indexing_status["in_progress"]:
        raise HTTPException(
            status_code=409,
            detail="Un document est déjà en cours de traitement"
        )
        
    # Validation du type de fichier
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Type de fichier non supporté. Seuls les fichiers PDF sont acceptés."
        )
    
    try:
        # Créer un fichier temporaire
        tmp_path = Path(tempfile.gettempdir()) / f"upload_{int(time.time())}_{file.filename}"
        
        # Vérifier l'espace disque disponible
        free_space = shutil.disk_usage(tmp_path.parent).free
        if free_space < settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=507,
                detail=f"Espace disque insuffisant. Minimum requis: {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"
            )
        
        # Sauvegarder le fichier avec validation de la taille
        file_size = 0
        with open(tmp_path, 'wb') as f:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > settings.MAX_UPLOAD_SIZE:
                    f.close()
                    tmp_path.unlink()
                    raise HTTPException(
                        status_code=413,
                        detail=f"Fichier trop volumineux. Maximum autorisé: {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"
                    )
                f.write(chunk)
        
        # Lancer le traitement en arrière-plan
        background_tasks.add_task(process_document_task, tmp_path, rag_engine)
        background_tasks.add_task(cleanup_temp_file, str(tmp_path))  # Ajouter le nettoyage en tâche de fond
        
        return JSONResponse(
            status_code=202,
            content={
                "message": "Traitement du document lancé",
                "filename": file.filename,
                "size": file_size
            }
        )
        
    except HTTPException:
        # Nettoyer en cas d'erreur HTTP
        if 'tmp_path' in locals():
            tmp_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        # Nettoyer en cas d'erreur générale
        if 'tmp_path' in locals():
            tmp_path.unlink(missing_ok=True)
        error_msg = f"Erreur lors de l'upload: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/indexing-status")
async def get_indexing_status():
    """Récupère le statut actuel de l'indexation avec des métriques détaillées."""
    global indexing_status
    if indexing_status is None:
        return {
            "in_progress": False,
            "error_occurred": False
        }
    return indexing_status

@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest = Body(...),
    rag_engine: RAGEngine = Depends(get_rag_engine)
) -> QueryResponse:
    """
    Traite une requête de recherche.
    
    Args:
        request: La requête de recherche
        rag_engine: Instance du RAG Engine
    
    Returns:
        QueryResponse: La réponse générée avec les sources
    """
    try:
        start_time = time.time()
        
        result = await rag_engine.query(
            query=request.query,
            k=request.k,
            filter=request.filter
        )
        
        # Ajouter le temps de traitement
        result["processing_time"] = time.time() - start_time
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la requête: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement de la requête: {str(e)}"
        )

@router.get(
    "/documents/{file_path:path}/summary",
    response_model=str,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_document_summary(
    file_path: str,
    rag_engine: RAGEngine = Depends(get_rag_engine)
) -> str:
    """
    Génère un résumé pour le document spécifié.
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="Fichier introuvable",
                    detail=f"Le fichier {file_path} n'existe pas",
                    timestamp=datetime.now().isoformat()
                ).model_dump()
            )
            
        return await rag_engine.get_document_summary(file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Erreur lors de la génération du résumé",
                detail=str(e),
                timestamp=datetime.now().isoformat()
            ).model_dump()
        )

@router.get("/stats")
async def get_stats(vector_store: VectorStore = Depends(get_vector_store)):
    """
    Récupère les statistiques de la collection.
    """
    try:
        # Récupérer les statistiques de Qdrant
        collection_info = await vector_store.get_collection_info()
        vectors_count = collection_info.get("vectors_count", 0)
        
        # Récupérer le statut d'indexation
        status = indexing_status
        
        # Fusionner les statistiques
        stats = {
            "indexing_in_progress": status["in_progress"],
            "total_files": status["total_files"],
            "processed_files": status["processed_files"],
            "total_chunks": status["total_chunks"],
            "indexed_chunks": status["indexed_chunks"],
            "vectors_count": vectors_count,
            "error_occurred": "error" in status,
            "error_message": status.get("error", None),
            "last_update": status["last_update"]
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Erreur lors de la récupération des statistiques",
                detail=str(e),
                timestamp=datetime.now().isoformat()
            ).model_dump()
        )

@router.get("/health")
async def health_check():
    """Vérifie l'état du système."""
    try:
        # Vérifier la connexion à Qdrant
        vector_store = VectorStore()
        await vector_store.client.http.health()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "components": {
                    "qdrant": "connected",
                    "api": "running"
                },
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error="Service Unavailable",
                detail=str(e),
                timestamp=datetime.now().isoformat()
            ).model_dump()
        )
