"""
Gestionnaire de file d'attente pour tâches OCR (OCR Queue Manager)
================================================================

Ce module implémente un système avancé de gestion de file d'attente pour les tâches OCR longues.
Il offre des fonctionnalités de prioritisation, pause/reprise, et suivi en temps réel des tâches.

Caractéristiques principales:
- File d'attente avec priorité configurable
- Gestion des tâches (pause, reprise, annulation)
- Limitation du nombre de tâches simultanées
- Métriques détaillées pour le tableau de bord
- Notifications en temps réel via WebSockets
- Optimisation des ressources système

Utilisation typique:
```python
# Initialiser le gestionnaire
manager = OCRQueueManager()

# Ajouter une tâche avec priorité
task_id = await manager.enqueue_task(
    document_path="path/to/document.pdf",
    priority=OCRTaskPriority.HIGH,
    metadata={"user_id": "user123", "description": "Document technique"}
)

# Récupérer le statut d'une tâche
status = await manager.get_task_status(task_id)

# Pauser/reprendre une tâche
await manager.pause_task(task_id)
await manager.resume_task(task_id)
```

Auteur: Équipe Technicia
Date: Avril 2025
"""

import logging
import time
import asyncio
import json
from typing import Dict, Any, List, Optional, Union, Callable, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from datetime import datetime, timedelta
import uuid
from functools import partial
import heapq
from collections import deque
import threading
import os

from app.config import settings
from app.core.tasks.error_handling import TaskManager, TaskState, ErrorType, TaskCheckpoint
from app.core.tasks.ocr_queue import OCRQueueManager as BaseOCRQueueManager, OCRChunk
from app.core.file_processing.ocr.base import OCRResult

logger = logging.getLogger(__name__)


class OCRTaskPriority(IntEnum):
    """
    Priorité d'une tâche OCR.
    
    Les niveaux de priorité sont:
    - CRITICAL (0): Priorité critique, exécution immédiate
    - HIGH (1): Priorité haute
    - NORMAL (2): Priorité normale
    - LOW (3): Priorité basse
    - BACKGROUND (4): Tâche d'arrière-plan, s'exécute quand les ressources sont disponibles
    """
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class OCRTaskStatus(Enum):
    """
    Statut d'une tâche OCR.
    
    Les statuts possibles sont:
    - QUEUED: En file d'attente
    - PREPROCESSING: Prétraitement en cours
    - PROCESSING: Traitement OCR en cours
    - PAUSED: Mise en pause
    - COMPLETED: Terminée avec succès
    - FAILED: Échec
    - CANCELLED: Annulée
    - WAITING_FOR_RESOURCES: En attente de ressources
    """
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_FOR_RESOURCES = "waiting_for_resources"


@dataclass
class OCRTask:
    """
    Tâche OCR dans la file d'attente.
    
    Attributes:
        task_id (str): Identifiant unique de la tâche
        document_path (Path): Chemin vers le document
        output_path (Optional[Path]): Chemin de sortie pour le document traité
        priority (OCRTaskPriority): Priorité de la tâche
        status (OCRTaskStatus): Statut de la tâche
        added_at (datetime): Date et heure d'ajout à la file d'attente
        started_at (Optional[datetime]): Date et heure de début de traitement
        completed_at (Optional[datetime]): Date et heure de fin de traitement
        progress (float): Progression (0.0 à 1.0)
        options (Dict[str, Any]): Options de traitement OCR
        metadata (Dict[str, Any]): Métadonnées associées à la tâche
        error_message (Optional[str]): Message d'erreur en cas d'échec
    """
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_path: Path = None
    output_path: Optional[Path] = None
    priority: OCRTaskPriority = OCRTaskPriority.NORMAL
    status: OCRTaskStatus = OCRTaskStatus.QUEUED
    added_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    options: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la tâche en dictionnaire.
        
        Returns:
            Dictionnaire représentant la tâche
        """
        return {
            "task_id": self.task_id,
            "document_path": str(self.document_path),
            "output_path": str(self.output_path) if self.output_path else None,
            "priority": self.priority.name,
            "priority_value": int(self.priority),
            "status": self.status.value,
            "added_at": self.added_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "estimated_time_remaining": self.get_estimated_time_remaining()
        }
    
    def get_estimated_time_remaining(self) -> Optional[int]:
        """
        Calcule le temps estimé restant en secondes.
        
        Returns:
            Temps estimé restant ou None si non calculable
        """
        if self.progress <= 0 or self.started_at is None:
            return None
        
        elapsed_time = (datetime.now() - self.started_at).total_seconds()
        if elapsed_time <= 0:
            return None
        
        # Temps estimé = (temps écoulé / progression) * (1 - progression)
        estimated_total = elapsed_time / self.progress
        estimated_remaining = estimated_total * (1 - self.progress)
        
        return int(estimated_remaining)
    
    def __lt__(self, other):
        """
        Comparaison pour la file d'attente prioritaire.
        
        Args:
            other: Autre tâche à comparer
            
        Returns:
            True si cette tâche a une priorité plus élevée (valeur numérique plus basse)
        """
        if not isinstance(other, OCRTask):
            return NotImplemented
        
        # Comparaison d'abord par priorité, puis par date d'ajout
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.added_at < other.added_at


class OCRQueueManager:
    """
    Gestionnaire avancé de file d'attente pour tâches OCR.
    
    Permet de gérer efficacement les tâches OCR avec priorité, pause/reprise,
    et suivi en temps réel.
    
    Attributes:
        config (Dict[str, Any]): Configuration du gestionnaire
        task_manager (TaskManager): Gestionnaire de tâches
        base_manager (BaseOCRQueueManager): Gestionnaire OCR de base
        task_queue (List[OCRTask]): File d'attente des tâches (heapq)
        active_tasks (Dict[str, OCRTask]): Tâches actives par ID
        completed_tasks (Dict[str, OCRTask]): Tâches terminées par ID
        paused_tasks (Set[str]): Ensemble des IDs de tâches en pause
        max_concurrent_tasks (int): Nombre maximal de tâches simultanées
        tasks_lock (asyncio.Lock): Verrou pour accès thread-safe à la file d'attente
        notification_callbacks (List[Callable]): Callbacks pour notifications
    """
    
    # Nombre maximal de tâches simultanées par défaut
    DEFAULT_MAX_CONCURRENT_TASKS = 3
    
    # Durée de conservation des tâches terminées (en heures)
    COMPLETED_TASK_RETENTION = 24
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le gestionnaire de file d'attente.
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
        self.task_manager = TaskManager()
        self.base_manager = BaseOCRQueueManager(self.config)
        
        # File d'attente prioritaire (heapq)
        self.task_queue = []
        
        # Dictionnaires de suivi des tâches
        self.active_tasks: Dict[str, OCRTask] = {}
        self.completed_tasks: Dict[str, OCRTask] = {}
        self.paused_tasks: Set[str] = set()
        
        # Limitation des tâches simultanées
        self.max_concurrent_tasks = self.config.get(
            "max_concurrent_tasks", 
            self.DEFAULT_MAX_CONCURRENT_TASKS
        )
        
        # Verrou pour accès thread-safe à la file d'attente
        self.tasks_lock = asyncio.Lock()
        
        # Callbacks pour notifications
        self.notification_callbacks: List[Callable] = []
        
        # Démarrer le nettoyage périodique des tâches terminées
        self._start_periodic_cleanup()
    
    def _start_periodic_cleanup(self):
        """
        Démarre le nettoyage périodique des tâches terminées.
        """
        async def cleanup_loop():
            while True:
                await asyncio.sleep(3600)  # Toutes les heures
                await self._cleanup_completed_tasks()
        
        # Démarrer le nettoyage en arrière-plan
        asyncio.create_task(cleanup_loop())
    
    async def _cleanup_completed_tasks(self):
        """
        Nettoie les tâches terminées anciennes.
        """
        threshold = datetime.now() - timedelta(hours=self.COMPLETED_TASK_RETENTION)
        
        async with self.tasks_lock:
            to_remove = []
            for task_id, task in self.completed_tasks.items():
                if task.completed_at and task.completed_at < threshold:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.completed_tasks[task_id]
        
        logger.info(f"Nettoyage des tâches terminées: {len(to_remove)} tâches supprimées")

    async def enqueue_task(self, document_path: Union[str, Path],
                       output_path: Optional[Union[str, Path]] = None,
                       priority: OCRTaskPriority = OCRTaskPriority.NORMAL,
                       options: Optional[Dict[str, Any]] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Ajoute une tâche OCR à la file d'attente.
        
        Cette méthode crée une nouvelle tâche OCR avec les paramètres spécifiés et l'ajoute
        à la file d'attente en fonction de sa priorité. La tâche sera traitée lorsque des
        ressources seront disponibles et en fonction de sa priorité relative.
        
        Args:
            document_path: Chemin vers le document à traiter
            output_path: Chemin de sortie pour le document traité (optionnel)
            priority: Priorité de la tâche (par défaut: NORMAL)
            options: Options de traitement OCR (provider, langue, etc.)
            metadata: Métadonnées associées à la tâche (utilisateur, description, etc.)
            
        Returns:
            ID de la tâche créée
        
        Raises:
            FileNotFoundError: Si le document n'existe pas
            ValueError: Si les paramètres sont incorrects
        """
        document_path = Path(document_path)
        
        if not document_path.exists():
            raise FileNotFoundError(f"Document non trouvé: {document_path}")
        
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = document_path.parent / f"{document_path.stem}_ocr{document_path.suffix}"
        
        options = options or {}
        metadata = metadata or {}
        
        # Créer la tâche
        task = OCRTask(
            document_path=document_path,
            output_path=output_path,
            priority=priority,
            options=options,
            metadata=metadata
        )
        
        # Enregistrer la tâche auprès du gestionnaire de tâches
        self.task_manager.register_task(
            task_id=task.task_id,
            task_type="ocr",
            context={
                "document_path": str(document_path),
                "output_path": str(output_path),
                "priority": priority.name,
                "metadata": metadata
            }
        )
        
        # Ajouter la tâche à la file d'attente
        async with self.tasks_lock:
            heapq.heappush(self.task_queue, task)
            self.active_tasks[task.task_id] = task
        
        # Notifier les observateurs
        await self._notify_task_update(task.task_id, task.status)
        
        # Démarrer le traitement si des ressources sont disponibles
        asyncio.create_task(self._process_queue())
        
        logger.info(f"Tâche OCR ajoutée à la file d'attente: {task.task_id} (priorité: {priority.name})")
        return task.task_id
    
    async def _process_queue(self):
        """
        Traite la file d'attente des tâches.
        
        Cette méthode interne vérifie si des ressources sont disponibles pour
        traiter de nouvelles tâches et démarre le traitement des tâches en attente
        selon leur priorité.
        """
        async with self.tasks_lock:
            # Vérifier si des ressources sont disponibles
            running_tasks = len([t for t in self.active_tasks.values() 
                               if t.status == OCRTaskStatus.PROCESSING])
            
            if running_tasks >= self.max_concurrent_tasks:
                return
            
            available_slots = self.max_concurrent_tasks - running_tasks
            
            # Traiter les tâches en attente par ordre de priorité
            next_tasks = []
            while self.task_queue and len(next_tasks) < available_slots:
                # Extraire la tâche de plus haute priorité
                task = heapq.heappop(self.task_queue)
                
                # Vérifier si la tâche est en pause
                if task.task_id in self.paused_tasks:
                    # Remettre la tâche dans la file d'attente pour plus tard
                    heapq.heappush(self.task_queue, task)
                else:
                    next_tasks.append(task)
            
            # Démarrer le traitement des tâches sélectionnées
            for task in next_tasks:
                asyncio.create_task(self._process_task(task))
    
    async def _process_task(self, task: OCRTask):
        """
        Traite une tâche OCR.
        
        Cette méthode interne effectue le traitement d'une tâche OCR en utilisant
        le gestionnaire OCR de base et met à jour son statut.
        
        Args:
            task: Tâche à traiter
        """
        # Mettre à jour le statut
        task.status = OCRTaskStatus.PREPROCESSING
        task.started_at = datetime.now()
        await self._notify_task_update(task.task_id, task.status)
        
        try:
            # Extraire les options
            chunk_size = task.options.get("chunk_size", None)
            ocr_provider = task.options.get("ocr_provider", "auto")
            language = task.options.get("language", "fra")
            
            # Mettre à jour le statut
            task.status = OCRTaskStatus.PROCESSING
            await self._notify_task_update(task.task_id, task.status)
            
            # Fonction de callback pour mise à jour de la progression
            async def progress_callback(progress: float, current_page: int = None, total_pages: int = None):
                task.progress = progress
                await self._notify_task_update(task.task_id, task.status, progress=progress)
            
            # Traiter le document
            result = await self.base_manager.process_document_in_chunks(
                document_path=task.document_path,
                output_path=task.output_path,
                chunk_size=chunk_size,
                ocr_provider=ocr_provider,
                language=language,
                task_id=task.task_id,
                task_manager=self.task_manager,
                **task.options
            )
            
            # Mettre à jour le statut
            if result.success:
                task.status = OCRTaskStatus.COMPLETED
                task.progress = 1.0
            else:
                task.status = OCRTaskStatus.FAILED
                task.error_message = result.error_message
            
            task.completed_at = datetime.now()
            
            # Déplacer la tâche vers la liste des tâches terminées
            async with self.tasks_lock:
                if task.task_id in self.active_tasks:
                    self.completed_tasks[task.task_id] = task
                    del self.active_tasks[task.task_id]
            
            # Notifier les observateurs
            await self._notify_task_update(task.task_id, task.status)
            
        except Exception as e:
            logger.exception(f"Erreur lors du traitement de la tâche {task.task_id}")
            
            # Mettre à jour le statut
            task.status = OCRTaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            
            # Déplacer la tâche vers la liste des tâches terminées
            async with self.tasks_lock:
                if task.task_id in self.active_tasks:
                    self.completed_tasks[task.task_id] = task
                    del self.active_tasks[task.task_id]
            
            # Notifier les observateurs
            await self._notify_task_update(task.task_id, task.status)
        
        finally:
            # Traiter la prochaine tâche dans la file d'attente
            asyncio.create_task(self._process_queue())
    
    async def pause_task(self, task_id: str) -> bool:
        """
        Met en pause une tâche OCR.
        
        Cette méthode permet de suspendre temporairement l'exécution d'une tâche.
        Si la tâche est déjà en cours de traitement, elle sera interrompue à la
        prochaine opportunité (entre deux chunks). Si elle est en attente, elle
        restera dans la file d'attente mais ne sera pas sélectionnée pour traitement.
        
        Args:
            task_id: ID de la tâche à mettre en pause
            
        Returns:
            True si la tâche a été mise en pause, False sinon
        """
        async with self.tasks_lock:
            if task_id not in self.active_tasks:
                return False
            
            task = self.active_tasks[task_id]
            
            # Vérifier si la tâche peut être mise en pause
            if task.status in [OCRTaskStatus.COMPLETED, OCRTaskStatus.FAILED, OCRTaskStatus.CANCELLED]:
                return False
            
            # Ajouter la tâche à l'ensemble des tâches en pause
            self.paused_tasks.add(task_id)
            
            # Mettre à jour le statut si la tâche est en attente
            if task.status == OCRTaskStatus.QUEUED:
                task.status = OCRTaskStatus.PAUSED
                await self._notify_task_update(task_id, task.status)
            
            # Pour les tâches en cours, le statut sera mis à jour par le processus de traitement
            
            logger.info(f"Tâche OCR mise en pause: {task_id}")
            return True
    
    async def resume_task(self, task_id: str) -> bool:
        """
        Reprend une tâche OCR mise en pause.
        
        Cette méthode permet de reprendre l'exécution d'une tâche préalablement
        mise en pause. La tâche retrouvera sa priorité originale dans la file d'attente.
        
        Args:
            task_id: ID de la tâche à reprendre
            
        Returns:
            True si la tâche a été reprise, False sinon
        """
        async with self.tasks_lock:
            if task_id not in self.active_tasks:
                return False
            
            task = self.active_tasks[task_id]
            
            # Vérifier si la tâche est en pause
            if task_id not in self.paused_tasks:
                return False
            
            # Retirer la tâche de l'ensemble des tâches en pause
            self.paused_tasks.remove(task_id)
            
            # Mettre à jour le statut
            if task.status == OCRTaskStatus.PAUSED:
                task.status = OCRTaskStatus.QUEUED
                await self._notify_task_update(task_id, task.status)
            
            # Démarrer le traitement si des ressources sont disponibles
            asyncio.create_task(self._process_queue())
            
            logger.info(f"Tâche OCR reprise: {task_id}")
            return True
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Annule une tâche OCR.
        
        Cette méthode permet d'annuler définitivement une tâche OCR. Si la tâche
        est en attente, elle sera retirée de la file d'attente. Si elle est en cours
        de traitement, elle sera interrompue à la prochaine opportunité.
        
        Args:
            task_id: ID de la tâche à annuler
            
        Returns:
            True si la tâche a été annulée, False sinon
        """
        async with self.tasks_lock:
            if task_id not in self.active_tasks:
                return False
            
            task = self.active_tasks[task_id]
            
            # Vérifier si la tâche peut être annulée
            if task.status in [OCRTaskStatus.COMPLETED, OCRTaskStatus.FAILED, OCRTaskStatus.CANCELLED]:
                return False
            
            # Mettre à jour le statut
            task.status = OCRTaskStatus.CANCELLED
            task.completed_at = datetime.now()
            
            # Retirer la tâche de l'ensemble des tâches en pause si nécessaire
            if task_id in self.paused_tasks:
                self.paused_tasks.remove(task_id)
            
            # Déplacer la tâche vers la liste des tâches terminées
            self.completed_tasks[task_id] = task
            del self.active_tasks[task_id]
            
            # Notifier les observateurs
            await self._notify_task_update(task_id, task.status)
            
            logger.info(f"Tâche OCR annulée: {task_id}")
            return True
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le statut d'une tâche OCR.
        
        Cette méthode permet d'obtenir des informations détaillées sur l'état actuel
        d'une tâche OCR, y compris sa progression, son statut et ses métadonnées.
        
        Args:
            task_id: ID de la tâche
            
        Returns:
            Dictionnaire contenant les informations de statut, ou None si la tâche n'existe pas
        """
        # Rechercher dans les tâches actives
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return task.to_dict()
        
        # Rechercher dans les tâches terminées
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return task.to_dict()
        
        return None
    
    async def list_tasks(self, status_filter: Optional[List[OCRTaskStatus]] = None,
                     limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Liste les tâches OCR selon des critères.
        
        Cette méthode permet d'obtenir la liste des tâches OCR, filtrées par statut
        et paginées.
        
        Args:
            status_filter: Liste des statuts à inclure (tous si None)
            limit: Nombre maximal de tâches à retourner
            offset: Index de départ pour la pagination
            
        Returns:
            Liste des tâches correspondant aux critères
        """
        result = []
        
        # Convertir le filtre en ensemble pour des recherches plus rapides
        status_set = set(status_filter) if status_filter else None
        
        # Collecter toutes les tâches
        all_tasks = list(self.active_tasks.values()) + list(self.completed_tasks.values())
        
        # Filtrer par statut si demandé
        if status_set:
            all_tasks = [t for t in all_tasks if t.status in status_set]
        
        # Trier par date d'ajout (plus récent en premier)
        all_tasks.sort(key=lambda t: t.added_at, reverse=True)
        
        # Appliquer pagination
        paginated_tasks = all_tasks[offset:offset + limit]
        
        # Convertir en dictionnaires
        for task in paginated_tasks:
            result.append(task.to_dict())
        
        return result
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Obtient des statistiques sur la file d'attente.
        
        Cette méthode fournit des métriques globales sur l'état de la file d'attente,
        comme le nombre de tâches dans chaque état, le temps moyen de traitement, etc.
        
        Returns:
            Dictionnaire contenant les statistiques
        """
        all_tasks = list(self.active_tasks.values()) + list(self.completed_tasks.values())
        
        # Initialiser les compteurs
        status_counts = {status.value: 0 for status in OCRTaskStatus}
        priority_counts = {priority.name: 0 for priority in OCRTaskPriority}
        
        # Temps de traitement pour les tâches terminées
        processing_times = []
        
        # Calculer les statistiques
        for task in all_tasks:
            # Compter par statut
            status_counts[task.status.value] += 1
            
            # Compter par priorité
            priority_counts[task.priority.name] += 1
            
            # Calculer le temps de traitement pour les tâches terminées
            if task.status in [OCRTaskStatus.COMPLETED, OCRTaskStatus.FAILED] and task.started_at and task.completed_at:
                processing_time = (task.completed_at - task.started_at).total_seconds()
                processing_times.append(processing_time)
        
        # Calculer les statistiques de temps
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            "queue_length": len(self.task_queue),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "paused_tasks": len(self.paused_tasks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "avg_processing_time": avg_processing_time,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _notify_task_update(self, task_id: str, status: OCRTaskStatus, progress: float = None):
        """
        Notifie les observateurs d'une mise à jour de tâche.
        
        Cette méthode interne envoie des notifications aux callbacks enregistrés
        lorsqu'une tâche est mise à jour.
        
        Args:
            task_id: ID de la tâche mise à jour
            status: Nouveau statut de la tâche
            progress: Nouvelle progression (optionnel)
        """
        # Préparer les données de notification
        task_info = await self.get_task_status(task_id)
        
        if not task_info:
            return
        
        # Notifier chaque callback
        for callback in self.notification_callbacks:
            try:
                await callback(task_id, task_info)
            except Exception as e:
                logger.error(f"Erreur lors de la notification: {str(e)}")
    
    def register_notification_callback(self, callback: Callable):
        """
        Enregistre un callback pour les notifications de tâches.
        
        Le callback sera appelé avec les arguments (task_id, task_info) à chaque
        mise à jour de statut d'une tâche.
        
        Args:
            callback: Fonction à appeler lors des notifications
        """
        if callable(callback) and callback not in self.notification_callbacks:
            self.notification_callbacks.append(callback)
    
    def unregister_notification_callback(self, callback: Callable):
        """
        Désenregistre un callback de notification.
        
        Args:
            callback: Fonction à retirer
        """
        if callback in self.notification_callbacks:
            self.notification_callbacks.remove(callback)

# Instance singleton du gestionnaire de file d'attente OCR
_ocr_queue_manager = None

async def get_ocr_queue_manager() -> OCRQueueManager:
    """
    Fonction de dépendance pour obtenir l'instance singleton du gestionnaire de file d'attente OCR.
    
    Cette fonction garantit qu'une seule instance du gestionnaire est créée et réutilisée
    dans toute l'application, assurant ainsi une gestion cohérente de la file d'attente.
    
    Returns:
        OCRQueueManager: L'instance unique du gestionnaire de file d'attente OCR
    """
    global _ocr_queue_manager
    
    if _ocr_queue_manager is None:
        _ocr_queue_manager = OCRQueueManager()
        # Démarrer le processeur de file d'attente en arrière-plan
        asyncio.create_task(_ocr_queue_manager._start_queue_processor())
        
        # Log de démarrage
        logger.info("Gestionnaire de file d'attente OCR initialisé")
    
    return _ocr_queue_manager
