"""
Modèles de données pour le tableau de bord OCR
=============================================

Ce module définit les structures de données utilisées par le tableau de bord
de suivi des tâches OCR. Il permet de stocker et de gérer les informations
sur les tâches en cours et terminées, ainsi que les métriques de performance.

Caractéristiques principales:
- Structure de données pour l'état des tâches OCR
- Modèles pour les métriques de performance des moteurs OCR
- Gestion de l'historique des tâches terminées
- Support pour le filtrage et la recherche des tâches

Auteur: Équipe Technicia
Date: Mars 2025
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, List, Optional, Union, Set
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

from app.core.tasks.error_handling import TaskState, ErrorType, TaskCheckpoint, TaskError
from app.config import settings

logger = logging.getLogger(__name__)

@dataclass
class TaskInfo:
    """
    Information complète sur une tâche OCR.
    
    Attributes:
        task_id (str): Identifiant unique de la tâche
        name (str): Nom de la tâche
        description (str): Description de la tâche
        document_path (str): Chemin vers le document traité
        output_path (Optional[str]): Chemin vers le document de sortie
        ocr_provider (str): Fournisseur OCR utilisé
        created_at (datetime.datetime): Date et heure de création
        started_at (Optional[datetime.datetime]): Date et heure de démarrage
        completed_at (Optional[datetime.datetime]): Date et heure de complétion
        state (TaskState): État actuel de la tâche
        progress (float): Progression entre 0 et 1
        current_page (int): Page actuellement traitée
        total_pages (int): Nombre total de pages
        processing_time (float): Temps de traitement en secondes
        checkpoints (List[Dict[str, Any]]): Points de reprise de la tâche
        errors (List[Dict[str, Any]]): Erreurs survenues pendant le traitement
        metadata (Dict[str, Any]): Métadonnées supplémentaires
    """
    task_id: str
    name: str
    description: str = ""
    document_path: str = ""
    output_path: Optional[str] = None
    ocr_provider: str = "auto"
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    state: TaskState = TaskState.PENDING
    progress: float = 0.0
    current_page: int = 0
    total_pages: int = 0
    processing_time: float = 0.0
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'information de tâche en dictionnaire.
        
        Returns:
            Dict[str, Any]: Dictionnaire représentant l'information de tâche
        """
        data = asdict(self)
        
        # Convertir les dates en chaînes ISO
        for key in ["created_at", "started_at", "completed_at"]:
            if data[key] is not None:
                data[key] = data[key].isoformat()
        
        # Convertir l'état en chaîne
        if isinstance(data["state"], TaskState):
            data["state"] = data["state"].value
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskInfo':
        """
        Crée une information de tâche à partir d'un dictionnaire.
        
        Args:
            data (Dict[str, Any]): Dictionnaire représentant l'information de tâche
            
        Returns:
            TaskInfo: Information de tâche créée
        """
        # Créer une copie pour ne pas modifier l'original
        task_data = dict(data)
        
        # Convertir les chaînes ISO en dates
        for key in ["created_at", "started_at", "completed_at"]:
            if task_data.get(key):
                task_data[key] = datetime.datetime.fromisoformat(task_data[key])
            else:
                task_data[key] = None
        
        # Convertir la chaîne d'état en enum
        if "state" in task_data and isinstance(task_data["state"], str):
            try:
                task_data["state"] = TaskState(task_data["state"])
            except ValueError:
                task_data["state"] = TaskState.PENDING
        
        return cls(**task_data)
    
    @property
    def is_active(self) -> bool:
        """
        Vérifie si la tâche est active (non terminée).
        
        Returns:
            bool: True si la tâche est active
        """
        return self.state not in [TaskState.COMPLETED, TaskState.FAILED]
    
    @property
    def duration(self) -> float:
        """
        Calcule la durée totale de la tâche.
        
        Returns:
            float: Durée en secondes
        """
        if not self.started_at:
            return 0.0
        
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        
        # Si la tâche est toujours en cours, calculer la durée jusqu'à maintenant
        return (datetime.datetime.now() - self.started_at).total_seconds()
    
    @property
    def estimated_completion_time(self) -> Optional[datetime.datetime]:
        """
        Estime la date et l'heure de complétion de la tâche.
        
        Returns:
            Optional[datetime.datetime]: Date et heure estimée de complétion
        """
        if not self.is_active or not self.started_at or self.progress <= 0:
            return None
        
        # Calculer le temps écoulé depuis le début
        elapsed = (datetime.datetime.now() - self.started_at).total_seconds()
        
        # Estimer le temps total en fonction de la progression
        if self.progress < 0.01:  # Éviter la division par zéro
            return None
        
        total_time = elapsed / self.progress
        remaining_time = total_time - elapsed
        
        # Ajouter le temps restant à l'heure actuelle
        return datetime.datetime.now() + datetime.timedelta(seconds=remaining_time)

@dataclass
class OCRProviderMetrics:
    """
    Métriques de performance pour un fournisseur OCR.
    
    Attributes:
        provider_name (str): Nom du fournisseur OCR
        total_tasks (int): Nombre total de tâches traitées
        successful_tasks (int): Nombre de tâches réussies
        failed_tasks (int): Nombre de tâches échouées
        total_pages (int): Nombre total de pages traitées
        total_processing_time (float): Temps total de traitement en secondes
        average_quality_score (float): Score moyen de qualité (0.0 à 1.0)
        document_types (Dict[str, int]): Types de documents traités et leur fréquence
        error_types (Dict[str, int]): Types d'erreurs rencontrées et leur fréquence
        last_updated (datetime.datetime): Date et heure de dernière mise à jour
    """
    provider_name: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_pages: int = 0
    total_processing_time: float = 0.0
    average_quality_score: float = 0.0
    document_types: Dict[str, int] = field(default_factory=dict)
    error_types: Dict[str, int] = field(default_factory=dict)
    last_updated: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit les métriques en dictionnaire.
        
        Returns:
            Dict[str, Any]: Dictionnaire représentant les métriques
        """
        data = asdict(self)
        
        # Convertir la date en chaîne ISO
        data["last_updated"] = data["last_updated"].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OCRProviderMetrics':
        """
        Crée des métriques à partir d'un dictionnaire.
        
        Args:
            data (Dict[str, Any]): Dictionnaire représentant les métriques
            
        Returns:
            OCRProviderMetrics: Métriques créées
        """
        # Créer une copie pour ne pas modifier l'original
        metrics_data = dict(data)
        
        # Convertir la chaîne ISO en date
        if metrics_data.get("last_updated"):
            metrics_data["last_updated"] = datetime.datetime.fromisoformat(metrics_data["last_updated"])
        
        return cls(**metrics_data)
    
    @property
    def success_rate(self) -> float:
        """
        Calcule le taux de réussite des tâches.
        
        Returns:
            float: Taux de réussite (0.0 à 1.0)
        """
        if self.total_tasks == 0:
            return 0.0
        
        return self.successful_tasks / self.total_tasks
    
    @property
    def average_processing_time_per_page(self) -> float:
        """
        Calcule le temps moyen de traitement par page.
        
        Returns:
            float: Temps moyen en secondes par page
        """
        if self.total_pages == 0:
            return 0.0
        
        return self.total_processing_time / self.total_pages
    
    def update_from_task(self, task: TaskInfo, quality_score: float = 0.0) -> None:
        """
        Met à jour les métriques à partir d'une tâche terminée.
        
        Args:
            task (TaskInfo): Information de tâche
            quality_score (float): Score de qualité OCR
        """
        # Incrémenter le nombre de tâches
        self.total_tasks += 1
        
        # Mettre à jour le statut
        if task.state == TaskState.COMPLETED:
            self.successful_tasks += 1
        elif task.state == TaskState.FAILED:
            self.failed_tasks += 1
        
        # Mettre à jour les pages et le temps
        self.total_pages += task.total_pages
        self.total_processing_time += task.processing_time
        
        # Mettre à jour le score de qualité moyen
        if quality_score > 0:
            if self.average_quality_score > 0:
                # Calculer la moyenne pondérée
                self.average_quality_score = (
                    (self.average_quality_score * (self.total_tasks - 1) + quality_score) / self.total_tasks
                )
            else:
                self.average_quality_score = quality_score
        
        # Mettre à jour les types de documents
        doc_type = Path(task.document_path).suffix.lower()
        self.document_types[doc_type] = self.document_types.get(doc_type, 0) + 1
        
        # Mettre à jour les types d'erreurs
        for error in task.errors:
            if isinstance(error, dict) and "error_type" in error:
                error_type = error["error_type"]
                if isinstance(error_type, ErrorType):
                    error_type = error_type.value
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        
        # Mettre à jour la date de dernière mise à jour
        self.last_updated = datetime.datetime.now()

class DashboardStore:
    """
    Gestionnaire de stockage pour les données du tableau de bord.
    
    Cette classe fournit des méthodes pour stocker et récupérer des informations
    sur les tâches OCR et les métriques de performance des fournisseurs OCR.
    Les données sont persistées sur le disque pour pouvoir être récupérées
    après un redémarrage du serveur.
    
    Attributes:
        data_dir (Path): Répertoire de stockage des données
        tasks (Dict[str, TaskInfo]): Dictionnaire des tâches indexées par ID
        metrics (Dict[str, OCRProviderMetrics]): Dictionnaire des métriques indexées par fournisseur OCR
    """
    
    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        """
        Initialise le gestionnaire de stockage.
        
        Args:
            data_dir (Optional[Union[str, Path]]): Répertoire de stockage des données
        """
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(settings.DATA_DIR) / "dashboard"
        
        # Créer le répertoire s'il n'existe pas
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialiser les collections
        self.tasks: Dict[str, TaskInfo] = {}
        self.metrics: Dict[str, OCRProviderMetrics] = {}
        
        # Charger les données existantes
        self._load_data()
    
    def _load_data(self) -> None:
        """
        Charge les données à partir du disque.
        
        Cette méthode est automatiquement appelée lors de l'initialisation
        pour charger les tâches et les métriques précédemment enregistrées.
        """
        # Charger les tâches
        tasks_file = self.data_dir / "tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    tasks_data = json.load(f)
                    
                    for task_id, task_data in tasks_data.items():
                        self.tasks[task_id] = TaskInfo.from_dict(task_data)
                        
                logger.info(f"Chargé {len(self.tasks)} tâches depuis {tasks_file}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement des tâches: {str(e)}")
        
        # Charger les métriques
        metrics_file = self.data_dir / "metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    metrics_data = json.load(f)
                    
                    for provider, provider_data in metrics_data.items():
                        self.metrics[provider] = OCRProviderMetrics.from_dict(provider_data)
                        
                logger.info(f"Chargé {len(self.metrics)} métriques depuis {metrics_file}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement des métriques: {str(e)}")
    
    def _save_data(self) -> None:
        """
        Enregistre les données sur le disque.
        
        Cette méthode est automatiquement appelée après chaque modification
        des tâches ou des métriques pour assurer la persistance des données.
        """
        # Enregistrer les tâches
        tasks_file = self.data_dir / "tasks.json"
        try:
            with open(tasks_file, "w", encoding="utf-8") as f:
                tasks_data = {task_id: task.to_dict() for task_id, task in self.tasks.items()}
                json.dump(tasks_data, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des tâches: {str(e)}")
        
        # Enregistrer les métriques
        metrics_file = self.data_dir / "metrics.json"
        try:
            with open(metrics_file, "w", encoding="utf-8") as f:
                metrics_data = {provider: metrics.to_dict() for provider, metrics in self.metrics.items()}
                json.dump(metrics_data, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des métriques: {str(e)}")
    
    def add_task(self, task: TaskInfo) -> None:
        """
        Ajoute ou met à jour une tâche.
        
        Args:
            task (TaskInfo): Information de tâche à ajouter
        """
        self.tasks[task.task_id] = task
        self._save_data()
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        Récupère une tâche par son ID.
        
        Args:
            task_id (str): ID de la tâche à récupérer
            
        Returns:
            Optional[TaskInfo]: Information de tâche ou None si non trouvée
        """
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **updates) -> Optional[TaskInfo]:
        """
        Met à jour une tâche existante.
        
        Args:
            task_id (str): ID de la tâche à mettre à jour
            **updates: Attributs à mettre à jour
            
        Returns:
            Optional[TaskInfo]: Information de tâche mise à jour ou None si non trouvée
        """
        task = self.get_task(task_id)
        if not task:
            return None
        
        # Appliquer les mises à jour
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        # Enregistrer les modifications
        self.add_task(task)
        
        return task
    
    def remove_task(self, task_id: str) -> bool:
        """
        Supprime une tâche.
        
        Args:
            task_id (str): ID de la tâche à supprimer
            
        Returns:
            bool: True si la tâche a été supprimée, False sinon
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_data()
            return True
        return False
    
    def update_metrics(self, provider: str, task: TaskInfo, quality_score: float = 0.0) -> None:
        """
        Met à jour les métriques pour un fournisseur OCR.
        
        Args:
            provider (str): Nom du fournisseur OCR
            task (TaskInfo): Information de tâche terminée
            quality_score (float): Score de qualité OCR
        """
        # Obtenir ou créer les métriques pour ce fournisseur
        metrics = self.metrics.get(provider)
        if not metrics:
            metrics = OCRProviderMetrics(provider_name=provider)
            self.metrics[provider] = metrics
        
        # Mettre à jour les métriques
        metrics.update_from_task(task, quality_score)
        
        # Enregistrer les modifications
        self._save_data()
    
    def get_metrics(self, provider: str) -> Optional[OCRProviderMetrics]:
        """
        Récupère les métriques pour un fournisseur OCR.
        
        Args:
            provider (str): Nom du fournisseur OCR
            
        Returns:
            Optional[OCRProviderMetrics]: Métriques ou None si non trouvées
        """
        return self.metrics.get(provider)
    
    def get_all_metrics(self) -> Dict[str, OCRProviderMetrics]:
        """
        Récupère les métriques pour tous les fournisseurs OCR.
        
        Returns:
            Dict[str, OCRProviderMetrics]: Dictionnaire des métriques indexées par fournisseur OCR
        """
        return dict(self.metrics)
    
    def get_active_tasks(self) -> List[TaskInfo]:
        """
        Récupère toutes les tâches actives.
        
        Returns:
            List[TaskInfo]: Liste des tâches actives
        """
        return [task for task in self.tasks.values() if task.is_active]
    
    def get_completed_tasks(self, limit: int = 100) -> List[TaskInfo]:
        """
        Récupère les tâches terminées.
        
        Args:
            limit (int): Nombre maximum de tâches à récupérer
            
        Returns:
            List[TaskInfo]: Liste des tâches terminées
        """
        completed = [task for task in self.tasks.values() if not task.is_active]
        
        # Trier par date de complétion (plus récent en premier)
        completed.sort(key=lambda t: t.completed_at or datetime.datetime.min, reverse=True)
        
        return completed[:limit]
    
    def cleanup_old_tasks(self, days: int = 30) -> int:
        """
        Supprime les tâches terminées depuis plus d'un certain nombre de jours.
        
        Args:
            days (int): Nombre de jours après lesquels les tâches sont considérées comme anciennes
            
        Returns:
            int: Nombre de tâches supprimées
        """
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Identifier les tâches à supprimer
        to_remove = [
            task_id for task_id, task in self.tasks.items()
            if not task.is_active and task.completed_at and task.completed_at < cutoff_date
        ]
        
        # Supprimer les tâches
        for task_id in to_remove:
            self.remove_task(task_id)
        
        return len(to_remove)


# Singleton pour le store
_dashboard_store: Optional[DashboardStore] = None

def get_dashboard_store() -> DashboardStore:
    """
    Obtient l'instance unique du gestionnaire de stockage du tableau de bord.
    
    Returns:
        DashboardStore: Instance du gestionnaire de stockage
    """
    global _dashboard_store
    
    if _dashboard_store is None:
        _dashboard_store = DashboardStore()
    
    return _dashboard_store
