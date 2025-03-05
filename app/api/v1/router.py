from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Body, WebSocket, Form, Request
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
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
import aiofiles  # Nouvel import pour les opérations fichier asynchrones
import threading
import json
from collections import defaultdict

# Variables pour suivre l'état de l'indexation
indexing_status = {
    "in_progress": False,
    "current_file": None,
    "indexed_chunks": 0,
    "total_chunks": 0,
    "error_occurred": False,
    "error_message": None,
    "ocr_in_progress": False,
    "ocr_progress": 0,
    "ocr_current_page": 0,
    "ocr_total_pages": 0,
    "ocr_logs": []
}

# Cache pour le statut avec expiration
indexing_status_cache = {
    'data': None,
    'timestamp': 0,
    'cache_duration': 2  # Durée du cache en secondes
}

# Suivi du dernier upload pour éviter la fermeture prématurée des modals
last_upload_time = 0

# Rate limiting simple
request_counters = defaultdict(lambda: {"count": 0, "reset_time": 0})

# Garde une trace des dernières requêtes par IP pour limiter le taux
rate_limit_data = {}

def check_rate_limit(client_ip: str, max_requests: int = 5, window_seconds: int = 5):
    """
    Vérifie si une IP cliente dépasse la limite de taux de requêtes.
    Renvoie (is_limited, retry_after_seconds)
    """
    now = time.time()
    
    # Initialiser ou nettoyer les données pour cette IP
    if client_ip not in rate_limit_data:
        rate_limit_data[client_ip] = []
    else:
        # Supprimer les anciennes requêtes hors de la fenêtre temporelle
        rate_limit_data[client_ip] = [t for t in rate_limit_data[client_ip] if now - t <= window_seconds]
    
    # Vérifier le nombre de requêtes dans la fenêtre temporelle
    request_count = len(rate_limit_data[client_ip])
    
    # Si le client a dépassé la limite
    if request_count >= max_requests:
        # Calculer le temps le plus ancien dans la fenêtre
        oldest_request_time = min(rate_limit_data[client_ip]) if rate_limit_data[client_ip] else now
        
        # Calculer combien de temps attendre jusqu'à ce que la plus ancienne requête soit hors de la fenêtre
        retry_after = max(1, int(window_seconds - (now - oldest_request_time)) + 1)
        
        # Ajouter un délai supplémentaire progressif basé sur l'excès de requêtes
        excess_factor = min(3, 1 + (request_count - max_requests) / max_requests)
        retry_after = int(retry_after * excess_factor)
        
        return True, retry_after
    
    # Ajouter cette requête à l'historique
    rate_limit_data[client_ip].append(now)
    return False, 0

logger = logging.getLogger(__name__)

from app.core.rag_engine import RAGEngine
from app.schemas import (
    ProcessingStats,
    QueryRequest,
    QueryResponse,
    CollectionStats,
    ErrorResponse,
    Source,
    IndexingProgressEvent,
    OCRProgressEvent,
    OCRResult,
    DocumentsStatistics
)
from app.core.vector_store import VectorStore  # Import VectorStore
from app.core.websocket_manager import websocket_manager
from app.api.websocket import OCRWebSocketManager, WebSocketLogHandler
from app.core.ocr_logger import get_ocr_tracker
from .diagnostic_router import router as diagnostic_router

# Fonctions d'aide OCR
async def is_pdf_searchable(file_path: Path, sample_pages: int = 3, min_text_length: int = 100) -> bool:
    """
    Détermine si un PDF contient du texte sélectionnable.
    
    Args:
        file_path: Chemin vers le fichier PDF
        sample_pages: Nombre de pages à échantillonner
        min_text_length: Longueur minimale de texte attendue
        
    Returns:
        True si le PDF contient du texte sélectionnable, False sinon
    """
    from app.core.ocr_helper import OCRHelper
    
    # C'est l'inverse de needs_ocr
    needs_ocr_result = await OCRHelper.needs_ocr(file_path, sample_pages, min_text_length)
    return not needs_ocr_result

async def process_pdf_with_ocr(file_path: Path, progress_callback=None) -> OCRResult:
    """
    Traite un document PDF avec OCR.
    
    Args:
        file_path: Chemin vers le fichier PDF à traiter
        progress_callback: Fonction de callback pour suivre la progression
        
    Returns:
        OCRResult: Résultat de l'opération OCR
    """
    from app.core.ocr_helper import OCRHelper
    import time
    
    start_time = time.time()
    original_path = file_path
    
    try:
        # Configurer le tracker OCR
        tracker = get_ocr_tracker()
        if tracker and progress_callback:
            # Connecter le callback aux événements du tracker
            tracker.set_event_callback(progress_callback)
        
        # Appliquer l'OCR
        ocr_path = await OCRHelper.apply_ocr(file_path)
        
        # Déterminer si l'opération a réussi
        success = ocr_path != file_path
        
        # Créer l'objet résultat
        result = OCRResult(
            output_path=ocr_path,
            success=success,
            original_path=original_path,
            processing_time=time.time() - start_time
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement OCR: {str(e)}", exc_info=True)
        
        # En cas d'échec, retourner un résultat avec le même fichier
        return OCRResult(
            output_path=file_path,
            success=False,
            original_path=original_path,
            error_message=str(e),
            processing_time=time.time() - start_time
        )

router = APIRouter()

# Créer l'instance du gestionnaire WebSocket OCR
ocr_websocket_manager = OCRWebSocketManager()

# Configurer le handler de logs pour OCR
ocr_log_handler = WebSocketLogHandler(ocr_websocket_manager)
logging.getLogger("app.core.ocr_helper").addHandler(ocr_log_handler)
logging.getLogger("app.api.v1.router").addHandler(ocr_log_handler)

@router.get("/health")
async def health_check():
    """Vérifie l'état du serveur."""
    return {"status": "ok"}

def cleanup_temp_file(file_path: str):
    """Nettoie le fichier temporaire."""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Fichier temporaire nettoyé: {file_path}")
    except Exception as e:
        # Ne pas logger d'erreur si le fichier n'existe pas (déjà supprimé)
        if not isinstance(e, FileNotFoundError):
            logger.error(f"Erreur lors du nettoyage du fichier temporaire {file_path}: {str(e)}")

async def get_rag_engine():
    """Dépendance pour obtenir une instance de RAGEngine."""
    engine = RAGEngine()
    await engine.initialize()  # Initialiser le RAGEngine
    return engine

async def get_vector_store():
    """Dépendance pour obtenir une instance de VectorStore."""
    vector_store = VectorStore()
    await vector_store.initialize()
    return vector_store

# Verrou pour éviter les conflits lors des mises à jour d'indexation
processing_lock = asyncio.Lock()

async def update_indexing_status(
    status_data: Dict = None,
    in_progress: bool = None,
    total_files: int = None,
    processed_files: int = None,
    total_chunks: int = None,
    indexed_chunks: int = None,
    error: str = None,
    processing_stats: dict = None,
    current_file: str = None,
    # Nouveaux paramètres pour l'OCR
    current_step: str = None,
    ocr_in_progress: bool = None,
    ocr_progress: int = None,
    ocr_current_page: int = None,
    ocr_total_pages: int = None,
    ocr_start_time: float = None,
    ocr_logs: List[str] = None
):
    """Met à jour le statut de l'indexation avec des métriques détaillées."""
    global indexing_status
    
    # S'assurer que le dictionnaire de statut existe
    if indexing_status is None:
        indexing_status = {}
        
    async with processing_lock:
        # Si status_data est fourni, utiliser ce dictionnaire pour la mise à jour
        if status_data is not None:
            # Mise à jour du dictionnaire avec les données fournies
            for key, value in status_data.items():
                indexing_status[key] = value
        else:
            # Mise à jour des champs individuels si fournis
            if in_progress is not None:
                indexing_status["in_progress"] = in_progress
            
            if total_files is not None:
                indexing_status["total_files"] = total_files
            
            if processed_files is not None:
                indexing_status["processed_files"] = processed_files
            
            if total_chunks is not None:
                indexing_status["total_chunks"] = total_chunks
            
            if indexed_chunks is not None:
                indexing_status["indexed_chunks"] = indexed_chunks
            
            if error is not None:
                indexing_status["error_occurred"] = True
                indexing_status["error_message"] = error
                logger.error(f"Erreur d'indexation: {error}")
            
            if processing_stats is not None:
                indexing_status["processing_stats"] = processing_stats
            
            if current_file is not None:
                indexing_status["current_file"] = current_file
            
            # Nouveaux champs OCR
            if current_step is not None:
                indexing_status["current_step"] = current_step
            
            if ocr_in_progress is not None:
                indexing_status["ocr_in_progress"] = ocr_in_progress
            
            if ocr_progress is not None:
                indexing_status["ocr_progress"] = ocr_progress
            
            if ocr_current_page is not None:
                indexing_status["ocr_current_page"] = ocr_current_page
            
            if ocr_total_pages is not None:
                indexing_status["ocr_total_pages"] = ocr_total_pages
            
            if ocr_start_time is not None:
                indexing_status["ocr_start_time"] = ocr_start_time
            
            if ocr_logs is not None:
                if "ocr_logs" not in indexing_status:
                    indexing_status["ocr_logs"] = []
                indexing_status["ocr_logs"].extend(ocr_logs)
                # Limiter le nombre de logs stockés
                indexing_status["ocr_logs"] = indexing_status["ocr_logs"][-50:]
        
        # Calculer les pourcentages de progression
        if total_files and processed_files:
            indexing_status["files_progress"] = (processed_files / total_files) * 100
        if total_chunks and indexed_chunks:
            indexing_status["chunks_progress"] = (indexed_chunks / total_chunks) * 100
        
        # Ajouter un timestamp
        indexing_status["last_update"] = datetime.now().isoformat()
        
        # Définir si le traitement est terminé pour la diffusion WebSocket
        is_completed = (
            not indexing_status.get("in_progress", False) and 
            not indexing_status.get("ocr_in_progress", False)
        )
        
        # Diffuser la mise à jour via WebSocket
        try:
            # Limiter la fréquence des diffusions pour éviter la surcharge
            current_time = time.time()
            if not hasattr(update_indexing_status, "_last_ws_broadcast") or \
               current_time - update_indexing_status._last_ws_broadcast >= 0.5:  # 500ms minimum entre diffusions
                
                ws_payload = {
                    "type": "indexing_status",
                    "data": {**indexing_status, "completed": is_completed}
                }
                asyncio.create_task(websocket_manager.broadcast(ws_payload))
                # Également diffuser aux clients OCR pour la compatibilité
                asyncio.create_task(ocr_websocket_manager.broadcast(ws_payload))
                update_indexing_status._last_ws_broadcast = current_time
        except Exception as e:
            logger.error(f"Erreur lors de la diffusion WebSocket du statut d'indexation: {str(e)}")
    
    return indexing_status

async def process_document_task(tmp_path: Path, rag_engine: RAGEngine, enable_ocr: bool = True):
    """Tâche de traitement du document en arrière-plan avec gestion robuste des erreurs."""
    try:
        async with processing_lock:
            # Initialiser le statut d'indexation
            await update_indexing_status(status_data={
                "in_progress": True,
                "total_files": 1,
                "processed_files": 0,
                "total_chunks": 0,
                "indexed_chunks": 0,
                "current_file": tmp_path.name,
                "current_step": "analyzing"  # Commencer par l'analyse
            })
            
            # Configurer le tracker OCR avec le gestionnaire WebSocket
            ocr_tracker = get_ocr_tracker(ocr_websocket_manager, update_indexing_status)
            
            # Créer des callbacks pour le suivi OCR
            callbacks = None
            if enable_ocr:
                callbacks = {
                    "ocr_started": lambda file_name, total_pages: asyncio.create_task(
                        update_indexing_status(status_data={
                            "current_step": "ocr",
                            "ocr_in_progress": True,
                            "ocr_progress": 0,
                            "ocr_current_page": 0,
                            "ocr_total_pages": total_pages,
                            "ocr_start_time": time.time(),
                            "ocr_logs": [f"Démarrage OCR pour {file_name}, {total_pages} pages à traiter"]
                        })
                    ),
                    "ocr_progress": lambda current_page, total_pages, progress: asyncio.create_task(
                        update_indexing_status(status_data={
                            "ocr_current_page": current_page,
                            "ocr_progress": progress,
                            "ocr_logs": [f"OCR: traitement de la page {current_page}/{total_pages} ({progress}%)"]
                        })
                    ),
                    "ocr_completed": lambda success, file_path: asyncio.create_task(
                        update_indexing_status(status_data={
                            "current_step": "indexing",
                            "ocr_in_progress": False,
                            "ocr_progress": 100,
                            "ocr_logs": [f"OCR {'terminé avec succès' if success else 'échoué'} pour {file_path}"]
                        })
                    )
                }
            
            try:
                # Traiter le document
                stats_dict = await rag_engine.process_document(tmp_path, enable_ocr=enable_ocr)
                
                # Mettre à jour le statut final
                await update_indexing_status(status_data={
                    "in_progress": False,
                    "processed_files": 1,
                    "total_chunks": stats_dict.get("chunks_processed", 0),
                    "indexed_chunks": stats_dict.get("chunks_indexed", 0),
                    "processing_stats": stats_dict,
                    "current_step": "completed"
                })
                
                # Log de succès
                logger.info(f"Document traité avec succès: {tmp_path.name}")
                
            except Exception as e:
                # Gérer les erreurs spécifiques au traitement
                error_msg = f"Erreur lors du traitement du document {tmp_path.name}: {str(e)}"
                logger.error(error_msg)
                await update_indexing_status(status_data={
                    "in_progress": False,
                    "error": error_msg,
                    "current_step": "error"
                })
                
                # Notifier via WebSocket en cas d'erreur
                error_notification = {
                    "type": "error",
                    "message": error_msg
                }
                asyncio.create_task(ocr_websocket_manager.broadcast(error_notification))
            
            finally:
                # Nettoyer le fichier temporaire, peu importe le résultat
                if tmp_path.exists():
                    try:
                        os.unlink(tmp_path)
                        logger.debug(f"Fichier temporaire supprimé: {tmp_path}")
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer le fichier temporaire {tmp_path}: {str(e)}")
    
    except Exception as e:
        # Capture des erreurs non gérées
        logger.error(f"Erreur inattendue dans process_document_task: {str(e)}")
        await update_indexing_status(status_data={
            "in_progress": False,
            "error": f"Erreur inattendue: {str(e)}",
            "current_step": "error"
        })

@router.post("/documents", response_model=ProcessingStats)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Fichier PDF à traiter"),
    enable_ocr: bool = Form(True, description="Activer la détection et application automatique de l'OCR si nécessaire"),
    rag_engine: RAGEngine = Depends(get_rag_engine)
):
    """
    Traite un document PDF et l'indexe dans le vector store avec validation robuste.
    """
    # Enregistrement du début du traitement
    start_time = time.time()
    
    # Vérification du type de fichier
    if file.content_type != "application/pdf" and not file.filename.lower().endswith('.pdf'):
        error_msg = f"Type de fichier non supporté: {file.content_type}. Seuls les PDF sont acceptés."
        logger.warning(error_msg)
        return JSONResponse(
            status_code=400,
            content={"detail": error_msg}
        )
    
    # Création d'un fichier temporaire pour stocker le contenu
    tmp_file = None
    try:
        # Créer un fichier temporaire avec un nom plus lisible
        tmp_dir = Path(tempfile.gettempdir())
        tmp_path = tmp_dir / f"upload_{int(time.time())}_{file.filename}"
        
        # Écrire le contenu du fichier uploadé
        async def write_file():
            async with aiofiles.open(tmp_path, 'wb') as f:
                # Lire par morceaux pour éviter la saturation de la mémoire
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    await f.write(chunk)
        
        # Exécuter l'écriture du fichier dans un thread séparé
        await write_file()
        
        tmp_file = tmp_path
        file_size = tmp_path.stat().st_size
        
        # Vérifier la taille du fichier
        max_size = settings.MAX_UPLOAD_SIZE * 1024 * 1024  # En bytes
        if file_size > max_size:
            os.unlink(tmp_path)
            error_msg = f"Taille du fichier ({file_size / (1024*1024):.2f} MB) dépasse la limite de {settings.MAX_UPLOAD_SIZE} MB"
            logger.warning(error_msg)
            return JSONResponse(
                status_code=413,
                content={"detail": error_msg}
            )
        
        # Log de la réception du fichier
        logger.info(f"Fichier reçu: {file.filename} ({file_size / 1024:.2f} KB)")
        
        # Enregistrer le timestamp de cet upload
        global last_upload_time
        last_upload_time = time.time()
        logger.debug(f"Nouvel upload enregistré à {last_upload_time}")
        
        # Notifier via WebSocket de la réception du fichier
        upload_notification = {
            "type": "upload_received",
            "filename": file.filename,
            "size": file_size,
            "timestamp": datetime.now().isoformat()
        }
        asyncio.create_task(ocr_websocket_manager.broadcast(upload_notification))
        
        # Ajouter la tâche de traitement en arrière-plan
        background_tasks.add_task(process_document_task, tmp_path, rag_engine, enable_ocr)
        
        # Enregistrement pour le statut
        await update_indexing_status(status_data={
            "in_progress": True,
            "total_files": 1,
            "processed_files": 0,
            "total_chunks": 0,
            "indexed_chunks": 0,
            "current_file": file.filename,
            "current_step": "uploading"  # Indiquer l'étape de téléchargement
        })
        
        # Renvoyer un statut de réussite initiale (le traitement continue en arrière-plan)
        duration = time.time() - start_time
        return ProcessingStats(
            document=file.filename,
            chunks_processed=0,  # Sera mis à jour pendant le traitement en arrière-plan
            chunks_indexed=0,    # Sera mis à jour pendant le traitement en arrière-plan
            processing_time=duration
        )
        
    except Exception as e:
        # En cas d'erreur, nettoyer et renvoyer une erreur
        logger.error(f"Erreur lors du traitement de l'upload: {str(e)}")
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)
        
        return JSONResponse(
            status_code=500,
            content={"detail": f"Erreur lors du traitement: {str(e)}"}
        )

@router.post("/documents")
async def process_document(
    request: Request,
    file_data: UploadFile = File(...), 
    filename: Optional[str] = Form(None)
):
    """Traite un document téléchargé et lance son indexation."""
    global indexing_status
    
    # Vérifier si le traitement est déjà en cours
    if indexing_status.get("in_progress", False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un traitement de document est déjà en cours",
        )
    
    # Récupérer et vérifier le nom de fichier
    original_filename = filename or file_data.filename
    if not original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom de fichier manquant",
        )
    
    # Déterminer le type de fichier et vérifier s'il est autorisé
    file_extension = os.path.splitext(original_filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de fichier non pris en charge. Types autorisés: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    
    try:
        # Lire le contenu du fichier
        contents = await file_data.read()
        file_size = len(contents)
        
        # Vérifier la taille du fichier
        if file_size > settings.MAX_UPLOAD_SIZE:
            max_size_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            actual_size_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Fichier trop volumineux. Maximum: {max_size_mb:.2f} MB, Reçu: {actual_size_mb:.2f} MB",
            )
        
        # Créer le dossier upload s'il n'existe pas
        os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
        
        # Définir le chemin du fichier de sortie
        safe_filename = secure_filename(original_filename)
        output_path = os.path.join(settings.UPLOAD_FOLDER, safe_filename)
        
        # Écrire le fichier sur le disque
        async with aiofiles.open(output_path, "wb") as out_file:
            await out_file.write(contents)
        
        logger.info(f"Fichier reçu: {safe_filename} ({file_size / 1024:.2f} KB)")
        
        # Réinitialiser le statut d'indexation
        indexing_status = {
            "in_progress": True,
            "filename": safe_filename,
            "total_files": 1,
            "processed_files": 0,
            "total_chunks": 0,
            "indexed_chunks": 0,
            "started_at": time.time(),
            "progress": 0.0,
            "ocr_in_progress": False,
            "ocr_total_pages": 0,
            "ocr_processed_pages": 0,
        }
        
        # Diffuser le statut initial via WebSocket
        await update_indexing_status(status_data=indexing_status)
        
        # Créer une tâche en arrière-plan pour traiter le document
        asyncio.create_task(process_file_task(output_path, safe_filename))
        
        return {"message": "Traitement du document lancé", "filename": safe_filename}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du traitement du document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement du document: {str(e)}",
        )

@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine)
):
    """
    Interroge le système RAG avec une question et obtient une réponse.
    Les sources et les questions de suivi sont générées automatiquement.
    """
    try:
        # Exécuter la requête
        query_result = await rag_engine.query(
            query=request.query,
            k=request.k,
            filter=request.filter
        )
        
        # Préparer la réponse
        sources = []
        if 'sources' in query_result and query_result['sources']:
            sources = [
                Source(file=source.get('file', ''), score=source.get('score', 0.0))
                for source in query_result['sources']
            ]
        
        response = QueryResponse(
            query=request.query,
            answer=query_result['answer'],
            sources=sources,
            processing_time=query_result.get('processing_time', 0.0),
            follow_up_questions=[]  # Sera rempli de façon asynchrone
        )
        
        # Générer les questions de suivi en arrière-plan
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            generate_follow_up_questions, 
            request.query, 
            query_result['answer'], 
            rag_engine
        )
        
        return response
    except Exception as e:
        logger.error(f"Erreur lors de la requête: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=CollectionStats)
async def get_collection_stats(
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Récupère les statistiques de la collection.
    """
    try:
        # Récupérer les statistiques
        collection_info = await vector_store.get_collection_info()
        
        # Extraire les informations requises par le modèle CollectionStats
        # Naviguer dans la structure de données complexe retournée par Qdrant
        config = collection_info.get("config", {})
        params = config.get("params", {})
        vectors_config = params.get("vectors", {})
        
        # Préparer la réponse avec les champs requis par le modèle
        stats = CollectionStats(
            name=vector_store.collection_name,
            vectors_count=collection_info.get("vectors_count", 0),
            dimension=vectors_config.get("size", 1024),
            distance=vectors_config.get("distance", "Cosine")
        )
        
        return stats
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/statistics", response_model=DocumentsStatistics)
async def get_documents_statistics(
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Récupère des statistiques détaillées sur les documents indexés.
    
    Fournit des informations comme:
    - Le nombre total de vecteurs
    - Le nombre de documents uniques
    - La moyenne de vecteurs par document
    - Si la collection est vide
    """
    try:
        # Récupérer les statistiques détaillées
        stats = await vector_store.get_collection_statistics()
        return stats
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques des documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Point d'entrée WebSocket principal pour les mises à jour d'indexation en temps réel."""
    await websocket_manager.connect(websocket)
    try:
        # Envoyer un message initial pour confirmer la connexion
        await websocket.send_json({
            "type": "connected",
            "data": {"message": "Connected to main WebSocket"}
        })
        
        # Boucle de réception de messages
        while True:
            try:
                # Attendre et traiter les messages entrants avec timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(data)
                await websocket_manager.handle_message(websocket, message)
            except json.JSONDecodeError:
                logger.warning(f"Message WebSocket invalide reçu")
            except asyncio.TimeoutError:
                # Continuer la boucle sans erreur en cas de timeout
                continue
            except Exception as e:
                logger.error(f"Erreur lors du traitement du message WebSocket: {e}")
                
    except WebSocketDisconnect:
        # Gestion propre de la déconnexion
        logger.info("Client WebSocket déconnecté")
    except Exception as e:
        logger.error(f"Erreur WebSocket inattendue: {e}")
    finally:
        # S'assurer que la connexion est bien fermée et nettoyée
        websocket_manager.disconnect(websocket)

@router.websocket("/ocr-ws")
async def ocr_websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket dédié aux mises à jour OCR détaillées."""
    await ocr_websocket_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        ocr_websocket_manager.disconnect(websocket)

async def generate_follow_up_questions(query: str, response: str, rag_engine: RAGEngine):
    """Génère les questions de suivi en arrière-plan."""
    try:
        questions = await rag_engine.generate_follow_up_questions(query, response)
        message = {
            "type": "follow_up_questions",
            "questions": questions
        }
        await websocket_manager.broadcast(message)
    except Exception as e:
        logger.error(f"Erreur lors de la génération des questions de suivi: {str(e)}")
        # Diffuser un message d'erreur
        error_message = {
            "type": "error",
            "message": f"Impossible de générer des questions de suivi: {str(e)}"
        }
        await websocket_manager.broadcast(error_message)

@router.get("/indexing-status")
async def get_indexing_status(request: Request):
    """Récupère le statut actuel de l'indexation avec des métriques détaillées.
    Inclut des informations sur le processus OCR s'il est en cours.
    Ajoute un champ 'completed' pour indiquer que le traitement est terminé."""
    global indexing_status, indexing_status_cache
    
    # Appliquer rate limiting
    client_ip = request.client.host
    is_limited, retry_after = check_rate_limit(client_ip)
    if is_limited:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests, please slow down",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )
    
    # Utiliser le cache si moins de 2 secondes se sont écoulées (au lieu de 5)
    current_time = time.time()
    if indexing_status_cache['data'] and current_time - indexing_status_cache['timestamp'] < indexing_status_cache['cache_duration']:
        return indexing_status_cache['data']
    
    try:
        # Vérifier s'il y a eu un upload récent (dans les 10 dernières secondes)
        recent_upload = False
        
        # Récupérer le timestamp du dernier upload
        global last_upload_time
        if current_time - last_upload_time < 10:  # 10 secondes de délai de sécurité
            recent_upload = True
            logger.debug(f"Upload récent détecté il y a {current_time - last_upload_time:.2f}s")
        
        # Déterminer si le traitement est terminé
        is_completed = (
            not indexing_status.get("in_progress", False) and 
            not indexing_status.get("ocr_in_progress", False)
        )
        
        # Ne pas marquer comme terminé si un upload récent a eu lieu
        if recent_upload:
            is_completed = False
            logger.debug("Ignorer le statut completed=true en raison d'un upload récent")
        
        # Ajouter le champ 'completed' pour indiquer au client de ne plus poller
        result = {**indexing_status, "completed": is_completed}
        
        # Mettre à jour le cache
        indexing_status_cache['data'] = result
        indexing_status_cache['timestamp'] = current_time
        
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut d'indexation: {str(e)}", exc_info=True)
        return {
            "in_progress": False,
            "error_occurred": True,
            "error_message": str(e),
            "completed": True  # Considérer comme terminé en cas d'erreur
        }

async def process_document(pdf_path: Path, filename: str, enable_ocr: bool = True):
    """
    Traite un document PDF et l'indexe dans la base de connaissances.
    
    Args:
        pdf_path: Chemin vers le fichier PDF
        filename: Nom du fichier original
        enable_ocr: Activer la détection et application OCR si nécessaire
    """
    global indexing_status, active_connections, ocr_connections
    
    try:
        # Mise à jour du statut
        indexing_status["in_progress"] = True
        indexing_status["current_file"] = filename
        indexing_status["indexed_chunks"] = 0
        indexing_status["total_chunks"] = 0
        indexing_status["error_occurred"] = False
        indexing_status["error_message"] = None
        indexing_status["ocr_in_progress"] = False
        
        # Initialiser le RAG engine
        rag_engine = await get_rag_engine()
        
        # Vérifier si le PDF a besoin d'OCR et l'appliquer si nécessaire
        needs_ocr = False
        if enable_ocr:
            logger.info(f"Vérification si le PDF {filename} nécessite OCR")
            needs_ocr = not await is_pdf_searchable(pdf_path)
            logger.info(f"Résultat de la vérification OCR pour {filename}: {'Nécessite OCR' if needs_ocr else 'Contient du texte'}")
            
            if needs_ocr:
                # Mettre à jour le statut OCR
                indexing_status["ocr_in_progress"] = True
                indexing_status["ocr_progress"] = 0
                indexing_status["ocr_current_page"] = 0
                indexing_status["ocr_total_pages"] = 0
                indexing_status["ocr_logs"] = []
                
                # Fonction de callback pour mettre à jour le statut OCR
                async def ocr_progress_callback(event_type: str, data: dict):
                    if event_type == "progress":
                        indexing_status["ocr_progress"] = data.get("progress", 0)
                        indexing_status["ocr_current_page"] = data.get("current_page", 0)
                        indexing_status["ocr_total_pages"] = data.get("total_pages", 0)
                        
                        # Ajouter le log
                        log_message = f"OCR en cours - page {data.get('current_page', 0)}/{data.get('total_pages', 0)} - {data.get('progress', 0)}%"
                        if "message" in data:
                            log_message = data["message"]
                            
                        indexing_status["ocr_logs"].append(log_message)
                        
                        # Envoyer le statut aux clients WebSocket
                        await broadcast_ocr_update(OCRProgressEvent(
                            progress=data.get("progress", 0),
                            current_page=data.get("current_page", 0),
                            total_pages=data.get("total_pages", 0),
                            message=log_message
                        ))
                    elif event_type == "log":
                        # Ajouter le log
                        log_message = data.get("message", "")
                        indexing_status["ocr_logs"].append(log_message)
                        
                        # Envoyer le log aux clients WebSocket
                        await broadcast_ocr_update(OCRProgressEvent(
                            message=log_message
                        ))
                        
                # Appliquer OCR
                try:
                    logger.info(f"Application de l'OCR sur {filename}")
                    indexing_status["ocr_logs"].append(f"Début du traitement OCR pour {filename}")
                    
                    # Envoyer le statut aux clients WebSocket
                    await broadcast_ocr_update(OCRProgressEvent(
                        message=f"Début du traitement OCR pour {filename}"
                    ))
                    
                    ocr_result = await process_pdf_with_ocr(
                        pdf_path,
                        progress_callback=ocr_progress_callback
                    )
                    
                    # Mettre à jour le chemin du PDF avec le résultat OCR
                    pdf_path = ocr_result.output_path
                    
                    # Terminer OCR
                    indexing_status["ocr_in_progress"] = False
                    indexing_status["ocr_progress"] = 100
                    
                    # Ajouter le log final
                    indexing_status["ocr_logs"].append(f"OCR terminé avec succès pour {filename}")
                    
                    # Envoyer le statut aux clients WebSocket
                    await broadcast_ocr_update(OCRProgressEvent(
                        progress=100,
                        message=f"OCR terminé avec succès pour {filename}"
                    ))
                    
                except Exception as e:
                    error_msg = f"Erreur lors de l'OCR: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    
                    # Ajouter le log d'erreur
                    indexing_status["ocr_logs"].append(error_msg)
                    
                    # Si OCR a échoué mais que le PDF est quand même exploitable (partiellement searchable)
                    # on continue avec le PDF original
                    logger.info("Tentative de continuer avec le PDF original malgré l'échec de l'OCR")
        
        # Indexer le document
        logger.info(f"Indexation du document {filename}")
        if needs_ocr:
            indexing_status["ocr_logs"].append("Début de l'indexation du document traité par OCR")
        
        # Mise à jour pour l'étape d'indexation
        indexing_status["ocr_in_progress"] = False
        
        # Utiliser asyncio.wait_for pour éviter que l'indexation reste bloquée indéfiniment
        try:
            # Ajouter un timeout de 5 minutes pour l'indexation
            stats = await asyncio.wait_for(
                rag_engine.index_document(
                    file_path=pdf_path,
                    filename=filename,
                    progress_callback=update_indexing_progress
                ),
                timeout=300  # 5 minutes en secondes
            )
            
            logger.info(f"Indexation terminée avec succès: {stats}")
            
            # Mise à jour finale du statut
            indexing_status["in_progress"] = False
            indexing_status["indexed_chunks"] = stats.get("chunks_indexed", 0)
            indexing_status["total_chunks"] = stats.get("total_chunks", 0)
            
            # Envoyer le statut final
            await broadcast_update(IndexingProgressEvent(
                in_progress=False,
                current_file=filename,
                indexed_chunks=stats.get("chunks_indexed", 0),
                total_chunks=stats.get("total_chunks", 0)
            ))
            
            logger.info(f"Indexation terminée pour {filename}: {stats}")
            return stats
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout lors de l'indexation du document {filename} (dépassement de 5 minutes)"
            logger.error(error_msg)
            
            # Mise à jour du statut en cas de timeout
            indexing_status["in_progress"] = False
            indexing_status["error_occurred"] = True
            indexing_status["error_message"] = error_msg
            
            # Notification des clients
            await broadcast_update(IndexingProgressEvent(
                in_progress=False,
                error=True,
                error_message=error_msg
            ))
            
            raise TimeoutError(error_msg)
            
    except Exception as e:
        error_msg = f"Erreur lors du traitement du document: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Mise à jour du statut en cas d'erreur
        indexing_status["in_progress"] = False
        indexing_status["error_occurred"] = True
        indexing_status["error_message"] = error_msg
        
        # Ajouter le log d'erreur si OCR était en cours
        if indexing_status["ocr_in_progress"]:
            indexing_status["ocr_logs"].append(error_msg)
            indexing_status["ocr_in_progress"] = False
        
        # Notifier les clients
        await broadcast_update(IndexingProgressEvent(
            in_progress=False,
            error=True,
            error_message=error_msg
        ))
        
        raise

async def broadcast_update(event: IndexingProgressEvent):
    """
    Diffuse une mise à jour de l'indexation à tous les clients connectés.
    
    Args:
        event: L'événement de progression à diffuser
    """
    # Convertir l'événement en dictionnaire
    event_data = event.dict()
    
    # Mettre à jour le statut global en fusionnant les données
    global indexing_status
    for key, value in event_data.items():
        if value is not None:  # Ne mettre à jour que les valeurs non nulles
            indexing_status[key] = value
    
    # Envoyer la mise à jour via WebSocket
    await update_indexing_status(indexing_status)

async def broadcast_ocr_update(event: OCRProgressEvent):
    """
    Diffuse une mise à jour OCR à tous les clients connectés via le WebSocket OCR.
    
    Args:
        event: L'événement de progression OCR à diffuser
    """
    # Envoyer directement au WebSocket OCR
    await ocr_websocket_manager.broadcast(event.dict())
    
    # Mettre également à jour le statut global d'indexation
    global indexing_status
    event_data = event.dict()
    
    # Mettre à jour les champs OCR pertinents
    if "progress" in event_data and event_data["progress"] is not None:
        indexing_status["ocr_progress"] = event_data["progress"]
    if "current_page" in event_data and event_data["current_page"] is not None:
        indexing_status["ocr_current_page"] = event_data["current_page"]
    if "total_pages" in event_data and event_data["total_pages"] is not None:
        indexing_status["ocr_total_pages"] = event_data["total_pages"]
    if "message" in event_data and event_data["message"]:
        if "ocr_logs" not in indexing_status:
            indexing_status["ocr_logs"] = []
        indexing_status["ocr_logs"].append(event_data["message"])
    
    # Envoyer la mise à jour globale via WebSocket
    await update_indexing_status(indexing_status)

async def update_indexing_status(status_data: Dict):
    """Met à jour le statut d'indexation et le diffuse via WebSocket."""
    global indexing_status_cache
    
    try:
        # Préparer les données à diffuser
        ws_payload = {
            "type": "indexing_status",
            "data": status_data
        }
        
        # Mettre à jour le cache
        indexing_status_cache['data'] = status_data
        indexing_status_cache['timestamp'] = time.time()
        
        # Diffuser via WebSocket - sans utiliser de Lock qui n'est pas thread-safe
        try:
            await websocket_manager.broadcast(ws_payload)
            logger.debug(f"Mise à jour du statut d'indexation diffusée via WebSocket: {status_data.get('progress')}")
        except Exception as e:
            logger.error(f"Erreur lors de la diffusion WebSocket: {str(e)}")
    
    except Exception as e:
        logger.error(f"Erreur dans update_indexing_status: {str(e)}")

# Fonction de callback pour suivre la progression de l'indexation
async def update_indexing_progress(progress_data: dict):
    """Met à jour le statut d'indexation à partir des données de progression."""
    global indexing_status
    
    # Mise à jour des données d'indexation
    if "indexed_chunks" in progress_data:
        indexing_status["indexed_chunks"] = progress_data["indexed_chunks"]
    if "total_chunks" in progress_data:
        indexing_status["total_chunks"] = progress_data["total_chunks"]
    
    # Calculer la progression en pourcentage
    if indexing_status["total_chunks"] > 0:
        indexing_status["progress"] = (indexing_status["indexed_chunks"] / indexing_status["total_chunks"]) * 100
    
    # Diffuser la mise à jour via la nouvelle fonction
    await update_indexing_status(indexing_status)

# Tâche asynchrone de traitement du fichier
async def process_file_task(file_path: str, filename: str):
    """Traite un fichier téléchargé en arrière-plan."""
    global indexing_status
    
    try:
        logger.info(f"Début du traitement du fichier: {filename}")
        
        # Mise à jour du statut d'indexation
        indexing_status.update({
            "in_progress": True,
            "current_file": filename,
            "processed_files": 0,
            "total_files": 1,
            "processed_size_mb": 0,
            "total_size_mb": os.path.getsize(file_path) / (1024 * 1024),
            "progress": 0.0,
            "error_occurred": False,
            "error_message": None,
            "started_at": time.time()
        })
        
        # Diffuser la mise à jour initiale via WebSocket
        await update_indexing_status(indexing_status)
        
        # Créer une instance de RAGEngine
        rag_engine = await get_rag_engine()
        
        # Traiter le document avec OCR si nécessaire
        await process_document(
            pdf_path=Path(file_path),
            filename=filename,
            enable_ocr=True
        )
        
        # Nettoyage du fichier temporaire
        try:
            os.remove(file_path)
            logger.info(f"Fichier temporaire supprimé: {file_path}")
        except Exception as e:
            logger.warning(f"Impossible de supprimer le fichier temporaire: {str(e)}")
        
        # Mise à jour finale du statut
        indexing_status.update({
            "in_progress": False,
            "progress": 100.0,
            "processed_files": 1,
            "completed_at": time.time()
        })
        
        # Calculer la durée totale
        duration = indexing_status.get("completed_at", 0) - indexing_status.get("started_at", 0)
        indexing_status["duration_seconds"] = duration
        
        # Diffuser la mise à jour finale
        await update_indexing_status(indexing_status)
        
        logger.info(f"Traitement du fichier terminé: {filename}")
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement en arrière-plan: {str(e)}", exc_info=True)
        
        # Mise à jour du statut en cas d'erreur
        indexing_status.update({
            "in_progress": False,
            "error_occurred": True,
            "error_message": str(e),
            "completed_at": time.time()
        })
        
        # Diffuser la mise à jour d'erreur
        await update_indexing_status(indexing_status)
