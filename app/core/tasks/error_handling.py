"""
Module de gestion d'erreurs pour tâches OCR
==========================================

Ce module implémente un système robuste pour gérer les erreurs et les interruptions
lors des traitements OCR, particulièrement pour les tâches longues. Il fournit
des mécanismes de checkpoint, de reprise sur erreur et de suivi de l'état des tâches.

Caractéristiques principales:
- Système de checkpoints pour sauvegarder l'état des tâches en cours
- Mécanisme de reprise après erreur, timeout ou interruption
- Classification intelligente des erreurs et stratégies de retry adaptatives
- Suivi de la progression des tâches avec métriques détaillées
- Intégration avec Celery pour les tâches asynchrones

Utilisation typique:
```python
# Utilisation du gestionnaire de tâches
task_manager = TaskManager()
task_id = task_manager.register_task("ocr_processing", document_path="/path/to/doc.pdf")

# Utilisation du décorateur pour la gestion d'erreurs
@with_error_handling(max_retries=3, timeout=600)
async def process_document(document_path, task_id):
    # Traitement du document...
    task_manager.create_checkpoint(task_id, state={"page": current_page})
    task_manager.update_task_progress(task_id, progress=0.5)
```

Auteur: Équipe Technicia
Date: Mars 2025
"""

import logging
import time
import json
import pickle
import os
from typing import Dict, Any, Optional, List, Union, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import functools
import traceback
import uuid

from app.config import settings

logger = logging.getLogger(__name__)

class TaskState(Enum):
    """
    État d'une tâche.
    
    Les états possibles sont:
    - PENDING: En attente
    - RUNNING: En cours d'exécution
    - FAILED: Échec
    - PAUSED: Mise en pause
    - COMPLETED: Terminée avec succès
    - RETRYING: En cours de nouvelle tentative
    """
    PENDING = "pending"      # En attente
    RUNNING = "running"      # En cours d'exécution
    FAILED = "failed"        # Échec
    PAUSED = "paused"        # Mise en pause
    COMPLETED = "completed"  # Terminée avec succès
    RETRYING = "retrying"    # En cours de nouvelle tentative

class ErrorType(Enum):
    """
    Types d'erreurs pouvant survenir lors du traitement OCR.
    
    Les types d'erreurs possibles sont:
    - SYSTEM: Erreur système (mémoire, disque, etc.)
    - TIMEOUT: Délai d'exécution dépassé
    - VALIDATION: Erreur de validation (format, configuration, etc.)
    - OCR: Erreur spécifique au traitement OCR
    - NETWORK: Erreur réseau (API externe, etc.)
    - UNKNOWN: Erreur indéterminée
    """
    SYSTEM = "system"        # Erreur système (mémoire, disque, etc.)
    TIMEOUT = "timeout"      # Délai d'exécution dépassé
    VALIDATION = "validation" # Erreur de validation (format, configuration, etc.)
    OCR = "ocr"              # Erreur spécifique au traitement OCR
    NETWORK = "network"      # Erreur réseau (API externe, etc.)
    UNKNOWN = "unknown"      # Erreur indéterminée

@dataclass
class TaskCheckpoint:
    """
    Point de reprise pour une tâche.
    
    Un point de reprise contient les informations suivantes:
    - task_id: Identifiant de la tâche
    - timestamp: Date et heure de création du point de reprise
    - state: État de la tâche au moment de la création du point de reprise
    - progress: Progression de la tâche au moment de la création du point de reprise
    - current_page: Page actuelle au moment de la création du point de reprise
    - total_pages: Nombre total de pages au moment de la création du point de reprise
    """
    task_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    state: Dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0  # 0.0 à 1.0
    current_page: int = 0
    total_pages: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le point de reprise en dictionnaire.
        
        Returns:
            Dictionnaire représentant le point de reprise
        """
        return {
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "state": self.state,
            "progress": self.progress,
            "current_page": self.current_page,
            "total_pages": self.total_pages
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskCheckpoint':
        """
        Crée un point de reprise à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire représentant le point de reprise
        
        Returns:
            Point de reprise créé
        """
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            state=data.get("state", {}),
            progress=data.get("progress", 0.0),
            current_page=data.get("current_page", 0),
            total_pages=data.get("total_pages", 0)
        )

@dataclass
class TaskError:
    """
    Information sur une erreur survenue lors d'une tâche.
    
    Une erreur contient les informations suivantes:
    - task_id: Identifiant de la tâche
    - timestamp: Date et heure de l'erreur
    - error_type: Type d'erreur
    - error_message: Message d'erreur
    - traceback: Traceback de l'erreur
    - recoverable: Si l'erreur est récupérable
    - context: Contexte supplémentaire
    """
    task_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    error_type: ErrorType = ErrorType.UNKNOWN
    error_message: str = ""
    traceback: Optional[str] = None
    recoverable: bool = True
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'erreur en dictionnaire.
        
        Returns:
            Dictionnaire représentant l'erreur
        """
        return {
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type.value,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "recoverable": self.recoverable,
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskError':
        """
        Crée une erreur à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire représentant l'erreur
        
        Returns:
            Erreur créée
        """
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            error_type=ErrorType(data.get("error_type", ErrorType.UNKNOWN.value)),
            error_message=data.get("error_message", ""),
            traceback=data.get("traceback"),
            recoverable=data.get("recoverable", True),
            context=data.get("context", {})
        )

class TaskManager:
    """
    Gestionnaire de tâches avec support pour les reprises sur erreur et les checkpoints.
    
    Le gestionnaire de tâches permet de suivre l'état des tâches longues et de reprendre
    en cas d'erreur. Il fournit des méthodes pour enregistrer des tâches, créer des
    checkpoints, mettre à jour la progression des tâches, gérer les erreurs et terminer
    les tâches.
    """
    
    def __init__(self, checkpoint_dir: Optional[Union[str, Path]] = None):
        """
        Initialise le gestionnaire de tâches.
        
        Args:
            checkpoint_dir: Répertoire pour stocker les checkpoints de tâche
        """
        self.checkpoint_dir = Path(checkpoint_dir or settings.TASK_CHECKPOINT_DIR or "checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Dictionnaire de suivi des tâches en cours
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
    
    def register_task(self, task_id: Optional[str] = None, 
                     task_type: str = "ocr",
                     context: Optional[Dict[str, Any]] = None) -> str:
        """
        Enregistre une nouvelle tâche.
        
        Args:
            task_id: Identifiant de tâche (généré automatiquement si non fourni)
            task_type: Type de tâche
            context: Contexte additionnel pour la tâche
            
        Returns:
            Identifiant de la tâche
        """
        task_id = task_id or str(uuid.uuid4())
        
        # Initialiser le suivi de tâche
        self.active_tasks[task_id] = {
            "task_id": task_id,
            "task_type": task_type,
            "state": TaskState.PENDING.value,
            "start_time": datetime.now(),
            "last_update": datetime.now(),
            "progress": 0.0,
            "checkpoints": [],
            "errors": [],
            "retry_count": 0,
            "context": context or {}
        }
        
        logger.info(f"Tâche enregistrée: {task_id} (type: {task_type})")
        return task_id
    
    def update_task_progress(self, task_id: str, progress: float,
                           current_page: Optional[int] = None,
                           total_pages: Optional[int] = None,
                           state: Optional[TaskState] = None) -> None:
        """
        Met à jour la progression d'une tâche.
        
        Args:
            task_id: Identifiant de la tâche
            progress: Progression (0.0 à 1.0)
            current_page: Page actuelle (pour OCR)
            total_pages: Nombre total de pages
            state: Nouvel état de la tâche
        """
        if task_id not in self.active_tasks:
            logger.warning(f"Tentative de mise à jour d'une tâche inconnue: {task_id}")
            return
        
        task = self.active_tasks[task_id]
        task["progress"] = progress
        task["last_update"] = datetime.now()
        
        if current_page is not None:
            task["current_page"] = current_page
        
        if total_pages is not None:
            task["total_pages"] = total_pages
        
        if state is not None:
            task["state"] = state.value
            logger.info(f"Tâche {task_id} - État: {state.value}, Progression: {progress:.1%}")
        else:
            logger.debug(f"Tâche {task_id} - Progression: {progress:.1%}")
    
    def create_checkpoint(self, task_id: str, state: Dict[str, Any],
                       current_page: Optional[int] = None,
                       total_pages: Optional[int] = None) -> Optional[TaskCheckpoint]:
        """
        Crée un point de reprise pour une tâche.
        
        Args:
            task_id: Identifiant de la tâche
            state: État à sauvegarder pour reprise
            current_page: Page actuelle
            total_pages: Nombre total de pages
            
        Returns:
            Checkpoint créé ou None en cas d'erreur
        """
        if task_id not in self.active_tasks:
            logger.warning(f"Tentative de créer un checkpoint pour une tâche inconnue: {task_id}")
            return None
        
        task = self.active_tasks[task_id]
        
        # Créer le checkpoint
        checkpoint = TaskCheckpoint(
            task_id=task_id,
            timestamp=datetime.now(),
            state=state,
            progress=task.get("progress", 0.0),
            current_page=current_page if current_page is not None else task.get("current_page", 0),
            total_pages=total_pages if total_pages is not None else task.get("total_pages", 0)
        )
        
        # Ajouter à la liste des checkpoints
        task["checkpoints"].append(checkpoint.to_dict())
        
        # Sauvegarder le checkpoint sur disque
        self._save_checkpoint_to_disk(checkpoint)
        
        logger.info(f"Checkpoint créé pour la tâche {task_id} (page {checkpoint.current_page}/{checkpoint.total_pages})")
        return checkpoint
    
    def _save_checkpoint_to_disk(self, checkpoint: TaskCheckpoint) -> bool:
        """
        Sauvegarde un checkpoint sur disque.
        
        Args:
            checkpoint: Checkpoint à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi
        """
        try:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint.task_id}.checkpoint"
            
            # Sauvegarder en JSON
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f)
            
            # Sauvegarder aussi en pickle pour les états complexes
            pickle_file = self.checkpoint_dir / f"{checkpoint.task_id}.pickle"
            with open(pickle_file, 'wb') as f:
                pickle.dump(checkpoint, f)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du checkpoint {checkpoint.task_id}: {str(e)}")
            return False
    
    def load_checkpoint(self, task_id: str) -> Optional[TaskCheckpoint]:
        """
        Charge le dernier checkpoint d'une tâche.
        
        Args:
            task_id: Identifiant de la tâche
            
        Returns:
            Dernier checkpoint ou None si introuvable
        """
        try:
            # Essayer d'abord le fichier pickle pour les états complexes
            pickle_file = self.checkpoint_dir / f"{task_id}.pickle"
            if pickle_file.exists():
                with open(pickle_file, 'rb') as f:
                    return pickle.load(f)
            
            # Sinon, essayer le fichier JSON
            checkpoint_file = self.checkpoint_dir / f"{task_id}.checkpoint"
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    return TaskCheckpoint.from_dict(data)
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du checkpoint {task_id}: {str(e)}")
            return None
    
    def register_error(self, task_id: str, exception: Exception,
                    error_type: ErrorType = ErrorType.UNKNOWN,
                    recoverable: bool = True,
                    context: Optional[Dict[str, Any]] = None) -> Optional[TaskError]:
        """
        Enregistre une erreur survenue lors d'une tâche.
        
        Args:
            task_id: Identifiant de la tâche
            exception: Exception survenue
            error_type: Type d'erreur
            recoverable: Si l'erreur est récupérable
            context: Contexte supplémentaire
            
        Returns:
            Erreur enregistrée ou None en cas d'échec
        """
        if task_id not in self.active_tasks:
            logger.warning(f"Tentative d'enregistrer une erreur pour une tâche inconnue: {task_id}")
            return None
        
        task = self.active_tasks[task_id]
        
        # Créer l'erreur
        error = TaskError(
            task_id=task_id,
            error_type=error_type,
            error_message=str(exception),
            traceback=traceback.format_exc(),
            recoverable=recoverable,
            context=context or {}
        )
        
        # Ajouter à la liste des erreurs
        task["errors"].append(error.to_dict())
        
        # Mettre à jour l'état de la tâche
        if not recoverable:
            task["state"] = TaskState.FAILED.value
        else:
            task["state"] = TaskState.RETRYING.value
            task["retry_count"] += 1
        
        logger.error(f"Erreur enregistrée pour la tâche {task_id}: {str(exception)}")
        
        # Sauvegarder l'erreur sur disque
        self._save_error_to_disk(error)
        
        return error
    
    def _save_error_to_disk(self, error: TaskError) -> bool:
        """
        Sauvegarde une erreur sur disque.
        
        Args:
            error: Erreur à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi
        """
        try:
            error_file = self.checkpoint_dir / f"{error.task_id}.error"
            
            # Sauvegarder en JSON
            with open(error_file, 'w') as f:
                json.dump(error.to_dict(), f)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'erreur {error.task_id}: {str(e)}")
            return False
    
    def should_retry(self, task_id: str, max_retries: int = 3) -> bool:
        """
        Détermine si une tâche doit être réessayée.
        
        Args:
            task_id: Identifiant de la tâche
            max_retries: Nombre maximal de tentatives
            
        Returns:
            True si la tâche doit être réessayée
        """
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        
        # Vérifier si la tâche est en état d'échec ou de nouvelle tentative
        if task["state"] not in [TaskState.FAILED.value, TaskState.RETRYING.value]:
            return False
        
        # Vérifier si le nombre maximal de tentatives est atteint
        if task["retry_count"] >= max_retries:
            logger.warning(f"Nombre maximal de tentatives atteint pour la tâche {task_id}: {task['retry_count']}/{max_retries}")
            return False
        
        # Vérifier si toutes les erreurs sont récupérables
        for error_dict in task["errors"]:
            if not error_dict.get("recoverable", True):
                logger.warning(f"Erreur non récupérable pour la tâche {task_id}")
                return False
        
        logger.info(f"La tâche {task_id} sera réessayée (tentative {task['retry_count'] + 1}/{max_retries})")
        return True
    
    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """
        Marque une tâche comme terminée.
        
        Args:
            task_id: Identifiant de la tâche
            result: Résultat final de la tâche
            
        Returns:
            True si la tâche a été marquée comme terminée
        """
        if task_id not in self.active_tasks:
            logger.warning(f"Tentative de terminer une tâche inconnue: {task_id}")
            return False
        
        task = self.active_tasks[task_id]
        task["state"] = TaskState.COMPLETED.value
        task["end_time"] = datetime.now()
        task["result"] = result
        task["progress"] = 1.0
        
        # Calculer la durée
        duration = task["end_time"] - task["start_time"]
        task["duration"] = duration.total_seconds()
        
        logger.info(f"Tâche {task_id} terminée en {duration.total_seconds():.2f} secondes")
        
        # Nettoyer les fichiers de checkpoint
        self._cleanup_task_files(task_id)
        
        return True
    
    def _cleanup_task_files(self, task_id: str) -> None:
        """
        Nettoie les fichiers de checkpoint d'une tâche terminée.
        
        Args:
            task_id: Identifiant de la tâche
        """
        try:
            checkpoint_file = self.checkpoint_dir / f"{task_id}.checkpoint"
            pickle_file = self.checkpoint_dir / f"{task_id}.pickle"
            error_file = self.checkpoint_dir / f"{task_id}.error"
            
            for file in [checkpoint_file, pickle_file, error_file]:
                if file.exists():
                    file.unlink()
            
        except Exception as e:
            logger.warning(f"Erreur lors du nettoyage des fichiers de la tâche {task_id}: {str(e)}")
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations sur une tâche.
        
        Args:
            task_id: Identifiant de la tâche
            
        Returns:
            Informations sur la tâche ou None si introuvable
        """
        return self.active_tasks.get(task_id)
    
    def list_active_tasks(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Liste les tâches actives.
        
        Args:
            task_type: Filtrer par type de tâche
            
        Returns:
            Liste des tâches actives
        """
        tasks = list(self.active_tasks.values())
        
        # Filtrer par type
        if task_type:
            tasks = [t for t in tasks if t.get("task_type") == task_type]
        
        # Filtrer par état (exclure les tâches terminées)
        tasks = [t for t in tasks if t.get("state") != TaskState.COMPLETED.value]
        
        return tasks
    
    def list_recoverable_tasks(self) -> List[Dict[str, Any]]:
        """
        Liste les tâches récupérables (en erreur mais pouvant être reprises).
        
        Returns:
            Liste des tâches récupérables
        """
        recoverable = []
        
        for task_id, task in self.active_tasks.items():
            if task["state"] == TaskState.RETRYING.value:
                # Vérifier si toutes les erreurs sont récupérables
                all_recoverable = all(
                    error.get("recoverable", True) 
                    for error in task.get("errors", [])
                )
                
                if all_recoverable:
                    recoverable.append(task)
        
        return recoverable

def with_error_handling(max_retries: int = 3, timeout: int = 600):
    """
    Décorateur pour ajouter la gestion des erreurs et la reprise aux fonctions.
    
    Args:
        max_retries: Nombre maximal de tentatives
        timeout: Délai d'expiration en secondes
        
    Returns:
        Décorateur
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Créer un gestionnaire de tâches
            task_manager = TaskManager()
            
            # Générer un ID de tâche basé sur la fonction et les arguments
            func_name = func.__name__
            task_id = kwargs.pop('task_id', None) or f"{func_name}_{uuid.uuid4()}"
            
            # Enregistrer la tâche
            task_manager.register_task(task_id, task_type=func_name, context={"args": str(args), "kwargs": str(kwargs)})
            
            # Vérifier s'il existe un checkpoint pour cette tâche
            checkpoint = task_manager.load_checkpoint(task_id)
            if checkpoint:
                # Restaurer l'état depuis le checkpoint
                logger.info(f"Reprise de la tâche {task_id} depuis le checkpoint (progression: {checkpoint.progress:.1%})")
                kwargs["checkpoint"] = checkpoint
            
            # Nombre de tentatives
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    # Mettre à jour l'état de la tâche
                    task_manager.update_task_progress(
                        task_id, 
                        progress=0.0 if retry_count == 0 else checkpoint.progress if checkpoint else 0.0,
                        state=TaskState.RUNNING
                    )
                    
                    # Exécuter la fonction avec timeout
                    result = await asyncio.wait_for(func(*args, task_id=task_id, task_manager=task_manager, **kwargs), timeout)
                    
                    # Marquer la tâche comme terminée
                    task_manager.complete_task(task_id, result)
                    
                    return result
                    
                except asyncio.TimeoutError:
                    # Gérer l'erreur de timeout
                    error = task_manager.register_error(
                        task_id, 
                        Exception(f"Délai d'exécution dépassé ({timeout}s)"),
                        error_type=ErrorType.TIMEOUT,
                        recoverable=True
                    )
                    
                    retry_count += 1
                    
                    # Si nombre maximal de tentatives atteint, propager l'erreur
                    if retry_count > max_retries:
                        logger.error(f"Nombre maximal de tentatives atteint pour la tâche {task_id}")
                        raise
                    
                    # Sinon, réessayer après un délai
                    delay = min(30, 2 ** retry_count)  # Délai exponentiel (2, 4, 8, 16, 30, 30...)
                    logger.info(f"Nouvelle tentative pour la tâche {task_id} dans {delay}s (tentative {retry_count}/{max_retries})")
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    # Gérer les autres erreurs
                    error_type = ErrorType.UNKNOWN
                    recoverable = True
                    
                    # Déterminer le type d'erreur et s'il est récupérable
                    if "mémoire" in str(e).lower() or "memory" in str(e).lower():
                        error_type = ErrorType.SYSTEM
                        recoverable = False
                    elif "réseau" in str(e).lower() or "network" in str(e).lower() or "connection" in str(e).lower():
                        error_type = ErrorType.NETWORK
                        recoverable = True
                    elif "validation" in str(e).lower() or "format" in str(e).lower() or "invalid" in str(e).lower():
                        error_type = ErrorType.VALIDATION
                        recoverable = False
                    elif "ocr" in str(e).lower():
                        error_type = ErrorType.OCR
                        recoverable = True
                    
                    error = task_manager.register_error(
                        task_id, 
                        e,
                        error_type=error_type,
                        recoverable=recoverable
                    )
                    
                    # Si erreur non récupérable, propager l'erreur
                    if not recoverable:
                        logger.error(f"Erreur non récupérable pour la tâche {task_id}: {str(e)}")
                        raise
                    
                    retry_count += 1
                    
                    # Si nombre maximal de tentatives atteint, propager l'erreur
                    if retry_count > max_retries:
                        logger.error(f"Nombre maximal de tentatives atteint pour la tâche {task_id}")
                        raise
                    
                    # Sinon, réessayer après un délai
                    delay = min(30, 2 ** retry_count)  # Délai exponentiel
                    logger.info(f"Nouvelle tentative pour la tâche {task_id} dans {delay}s (tentative {retry_count}/{max_retries})")
                    await asyncio.sleep(delay)
            
            # Ce code ne devrait jamais être atteint (si max_retries dépassé, une exception est levée)
            raise Exception(f"Échec de la tâche {task_id} après {max_retries} tentatives")
            
        return wrapper
    return decorator
