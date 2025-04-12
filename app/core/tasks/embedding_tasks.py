"""
Tâches Celery pour le traitement asynchrone des embeddings.
Ce module permet de traiter de gros documents par lots pour éviter les timeouts.
"""

import os
import json
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pickle
from uuid import uuid4
from more_itertools import chunked

from celery import Task, shared_task
from celery.signals import task_prerun, task_postrun
from tqdm import tqdm

from app.core.embeddings import get_embedding_service, EmbeddingResult, EmbeddingError
from app.config import settings

logger = logging.getLogger(__name__)

# Dossier pour stocker les résultats intermédiaires
TEMP_DIR = Path(settings.TEMP_DIR) if hasattr(settings, 'TEMP_DIR') else Path('temp')
TEMP_DIR.mkdir(exist_ok=True)

class LoggingTask(Task):
    """Classe de base pour les tâches avec logging amélioré et gestion des erreurs."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Gestionnaire d'erreurs pour les tâches."""
        logger.error(f"Tâche {self.name}[{task_id}] a échoué: {str(exc)}")
        super().on_failure(exc, task_id, args, kwargs, einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Gestionnaire de succès pour les tâches."""
        logger.info(f"Tâche {self.name}[{task_id}] terminée avec succès")
        super().on_success(retval, task_id, args, kwargs)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Gestionnaire de retry pour les tâches."""
        logger.warning(f"Tâche {self.name}[{task_id}] sera réessayée: {str(exc)}")
        super().on_retry(exc, task_id, args, kwargs, einfo)

@shared_task(bind=True, base=LoggingTask, max_retries=3, retry_backoff=True)
def generate_embeddings_batch(self, 
                             texts: List[str], 
                             task_id: str,
                             batch_id: int,
                             provider: str = "voyage",
                             model_name: Optional[str] = None) -> str:
    """
    Génère des embeddings pour un lot de textes.
    
    Args:
        texts: Liste des textes à encoder
        task_id: Identifiant de la tâche parente
        batch_id: Identifiant du lot
        provider: Fournisseur d'embeddings
        model_name: Nom du modèle à utiliser
        
    Returns:
        Chemin vers le fichier contenant les résultats
    """
    start_time = time.time()
    logger.info(f"Démarrage du traitement du lot {batch_id} ({len(texts)} textes)")
    
    # Configuration du modèle
    model = model_name or (
        "voyage-2" if provider == "voyage" else None
    )
    
    # Chemin pour sauvegarder les résultats intermédiaires
    result_path = TEMP_DIR / f"embedding_batch_{task_id}_{batch_id}.pkl"
    
    try:
        # Obtenir le service d'embeddings
        embedding_service = get_embedding_service(provider=provider, model_name=model)
        
        # Exécuter dans une boucle asyncio
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(embedding_service.embed(texts))
        
        # Sauvegarder les résultats intermédiaires
        with open(result_path, 'wb') as f:
            pickle.dump(result, f)
        
        processing_time = time.time() - start_time
        logger.info(f"Lot {batch_id} traité en {processing_time:.2f}s")
        
        return str(result_path)
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du lot {batch_id}: {str(e)}")
        if self.request.retries < self.max_retries:
            logger.warning(f"Réessai du lot {batch_id} ({self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)
        else:
            logger.error(f"Échec définitif du lot {batch_id} après {self.max_retries} tentatives")
            raise

@shared_task(bind=True, base=LoggingTask)
def assemble_embedding_results(self, 
                              result_paths: List[str], 
                              task_id: str) -> Dict[str, Any]:
    """
    Assemble les résultats d'embeddings à partir des fichiers intermédiaires.
    
    Args:
        result_paths: Liste des chemins vers les fichiers de résultats
        task_id: Identifiant de la tâche parente
        
    Returns:
        Dictionnaire contenant les embeddings assemblés
    """
    logger.info(f"Assemblage des résultats d'embeddings ({len(result_paths)} lots)")
    
    all_embeddings = []
    all_texts = []
    metadata = {}
    
    try:
        # Charger et assembler les résultats
        for path_str in result_paths:
            path = Path(path_str)
            if not path.exists():
                logger.warning(f"Fichier de résultats introuvable: {path}")
                continue
                
            with open(path, 'rb') as f:
                result = pickle.load(f)
                
            all_embeddings.extend(result.embeddings)
            all_texts.extend(result.original_texts)
            
            # Fusionner les métadonnées
            for key, value in result.metadata.items():
                if key in metadata and isinstance(value, (int, float)):
                    metadata[key] += value
                else:
                    metadata[key] = value
        
        # Mettre à jour les métadonnées
        metadata["total_embeddings"] = len(all_embeddings)
        metadata["total_texts"] = len(all_texts)
        
        # Nettoyer les fichiers intermédiaires
        for path_str in result_paths:
            path = Path(path_str)
            if path.exists():
                path.unlink()
        
        return {
            "embeddings": all_embeddings,
            "texts": all_texts,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'assemblage des résultats: {str(e)}")
        raise

@shared_task(bind=True, base=LoggingTask)
def process_document_embeddings(self, 
                               document_id: str, 
                               chunks: List[str],
                               provider: str = "voyage",
                               model_name: Optional[str] = None,
                               batch_size: int = 10,
                               callback_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Traite un document entier pour générer des embeddings par lots.
    
    Args:
        document_id: Identifiant du document
        chunks: Liste des chunks de texte à encoder
        provider: Fournisseur d'embeddings
        model_name: Nom du modèle à utiliser
        batch_size: Taille de chaque lot
        callback_url: URL pour notifier de l'avancement (optionnel)
        
    Returns:
        Résultats des embeddings
    """
    task_id = str(uuid4())
    logger.info(f"Démarrage du traitement du document {document_id} ({len(chunks)} chunks)")
    
    # Informations de progression
    progress_file = TEMP_DIR / f"progress_{task_id}.json"
    progress = {
        "document_id": document_id,
        "task_id": task_id,
        "total_chunks": len(chunks),
        "processed_chunks": 0,
        "status": "running",
        "start_time": time.time(),
        "provider": provider,
        "model": model_name,
    }
    
    # Sauvegarder l'état initial
    with open(progress_file, 'w') as f:
        json.dump(progress, f)
    
    # Diviser les chunks en lots
    batch_chunks = list(chunked(chunks, batch_size))
    batch_results = []
    
    try:
        # Traitement par lots en parallèle
        logger.info(f"Lancement de {len(batch_chunks)} tâches d'embedding")
        
        for i, batch in enumerate(batch_chunks):
            result = generate_embeddings_batch.delay(
                texts=batch,
                task_id=task_id,
                batch_id=i,
                provider=provider,
                model_name=model_name
            )
            batch_results.append(result)
        
        # Attendre que tous les lots soient traités
        result_paths = []
        for i, result in enumerate(batch_results):
            try:
                # Attendre le résultat avec un délai maximum
                path = result.get(timeout=3600)  # 1 heure max
                result_paths.append(path)
                
                # Mettre à jour la progression
                progress["processed_chunks"] += len(batch_chunks[i])
                progress["progress"] = progress["processed_chunks"] / progress["total_chunks"]
                
                with open(progress_file, 'w') as f:
                    json.dump(progress, f)
                
                # Notifier via callback si configuré
                if callback_url:
                    self._notify_progress(callback_url, progress)
                
            except Exception as e:
                logger.error(f"Erreur en attendant le résultat du lot {i}: {str(e)}")
        
        # Assembler les résultats
        logger.info(f"Assemblage des résultats ({len(result_paths)} lots)")
        final_result = assemble_embedding_results.delay(result_paths, task_id).get(timeout=300)
        
        # Mettre à jour la progression
        progress["status"] = "completed"
        progress["end_time"] = time.time()
        progress["duration"] = progress["end_time"] - progress["start_time"]
        
        with open(progress_file, 'w') as f:
            json.dump(progress, f)
        
        # Nettoyer le fichier de progression après un délai
        cleanup_progress_file.apply_async(args=[str(progress_file)], countdown=3600)  # Suppression après 1h
        
        return final_result
        
    except Exception as e:
        # Mettre à jour la progression en cas d'erreur
        progress["status"] = "failed"
        progress["error"] = str(e)
        progress["end_time"] = time.time()
        progress["duration"] = progress["end_time"] - progress["start_time"]
        
        with open(progress_file, 'w') as f:
            json.dump(progress, f)
        
        logger.error(f"Erreur lors du traitement du document {document_id}: {str(e)}")
        raise
    
    def _notify_progress(self, callback_url: str, progress: Dict[str, Any]):
        """Notifie l'avancement via une requête HTTP."""
        try:
            import httpx
            httpx.post(callback_url, json=progress, timeout=10)
        except Exception as e:
            logger.warning(f"Erreur lors de la notification via callback: {str(e)}")

@shared_task
def cleanup_progress_file(file_path: str):
    """Nettoie un fichier de progression après un certain délai."""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
    except Exception as e:
        logger.warning(f"Erreur lors du nettoyage du fichier {file_path}: {str(e)}")

# Tâches de maintenance
@shared_task
def cleanup_temp_files():
    """Nettoie les fichiers temporaires obsolètes."""
    try:
        current_time = time.time()
        count = 0
        
        for file in TEMP_DIR.glob("*"):
            # Supprimer les fichiers de plus de 24h
            if current_time - file.stat().st_mtime > 86400:
                file.unlink()
                count += 1
        
        logger.info(f"Nettoyage des fichiers temporaires terminé: {count} fichiers supprimés")
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des fichiers temporaires: {str(e)}")
