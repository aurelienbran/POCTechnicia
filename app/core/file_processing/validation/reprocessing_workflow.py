"""
Module de workflow de retraitement itératif
=====================================================

Ce module fournit un système pour gérer le retraitement automatique des documents
présentant des problèmes de qualité, en utilisant des stratégies adaptatives et
des mécanismes de rétroaction.

Caractéristiques principales:
- Gestion des tâches de retraitement basée sur les problèmes détectés
- Workflow adaptatif avec sélection des processeurs optimaux
- Intégration avec la file d'attente et le système de tâches
- Mécanismes de rétroaction et d'amélioration continue
- Historique des tentatives de retraitement et de leur résultat

Utilisation typique:
```python
# Créer une tâche de retraitement pour un document problématique
workflow = ReprocessingWorkflow()
job = await workflow.create_job(validation_issues)
job_id = await workflow.schedule_job(job)

# Récupérer les résultats d'une tâche
results = await workflow.get_job_results(job_id)
```

Auteur: Équipe Technicia
Date: Avril 2025
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, field
import uuid

from .low_confidence_detector import DocumentValidationIssues, ContentIssue
from ...tasks.task_queue import TaskQueueManager
from ...tasks.document_processing_tasks import process_document_task
from ...storage.document_store import DocumentStore
from ..ocr.factory import get_ocr_processor
from ..ocr.ocr_selector import select_optimal_processor
from ..document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

@dataclass
class ProcessingAttempt:
    """
    Tentative de traitement d'un document.
    
    Attributs:
        attempt_id: Identifiant unique de la tentative
        timestamp: Horodatage de la tentative
        processors_used: Liste des processeurs utilisés
        parameters: Paramètres spécifiques utilisés
        result_summary: Résumé du résultat
        confidence_scores: Scores de confiance obtenus
        task_id: Identifiant de la tâche Celery associée
        status: Statut de la tentative
        error: Message d'erreur éventuel
    """
    attempt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    processors_used: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    result_summary: Dict[str, Any] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    task_id: Optional[str] = None
    status: str = "pending"
    error: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """
        Indique si la tentative a réussi.
        
        Returns:
            True si la tentative a réussi
        """
        return self.status == "completed" and self.error is None
    
    @property
    def overall_confidence(self) -> float:
        """
        Calcule la confiance globale de la tentative.
        
        Returns:
            Score de confiance global
        """
        if not self.confidence_scores:
            return 0.0
        
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la tentative de traitement en dictionnaire.
        
        Returns:
            Dictionnaire représentant la tentative
        """
        return {
            "attempt_id": self.attempt_id,
            "timestamp": self.timestamp,
            "processors_used": self.processors_used,
            "parameters": self.parameters,
            "result_summary": self.result_summary,
            "confidence_scores": self.confidence_scores,
            "task_id": self.task_id,
            "status": self.status,
            "error": self.error,
            "is_successful": self.is_successful,
            "overall_confidence": self.overall_confidence
        }

@dataclass
class ReprocessingJob:
    """
    Tâche de retraitement d'un document.
    
    Attributs:
        job_id: Identifiant unique de la tâche
        document_id: Identifiant du document
        document_path: Chemin du document
        issues: Problèmes détectés qui ont déclenché le retraitement
        attempts: Liste des tentatives de traitement
        created_at: Date de création de la tâche
        updated_at: Date de dernière mise à jour
        status: Statut de la tâche
        max_attempts: Nombre maximal de tentatives autorisées
        requires_manual_validation: Indique si une validation manuelle est requise
        metadata: Métadonnées supplémentaires
    """
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    document_path: str = ""
    issues: DocumentValidationIssues = None
    attempts: List[ProcessingAttempt] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "created"
    max_attempts: int = 3
    requires_manual_validation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def attempt_count(self) -> int:
        """
        Retourne le nombre de tentatives effectuées.
        
        Returns:
            Nombre de tentatives
        """
        return len(self.attempts)
    
    @property
    def best_attempt(self) -> Optional[ProcessingAttempt]:
        """
        Retourne la meilleure tentative.
        
        Returns:
            Meilleure tentative ou None si aucune tentative réussie
        """
        successful_attempts = [a for a in self.attempts if a.is_successful]
        if not successful_attempts:
            return None
        
        return max(successful_attempts, key=lambda a: a.overall_confidence)
    
    @property
    def is_completed(self) -> bool:
        """
        Indique si la tâche est terminée.
        
        Returns:
            True si la tâche est terminée
        """
        return self.status in ["completed", "failed", "manual_validation"]
    
    @property
    def is_successful(self) -> bool:
        """
        Indique si la tâche a réussi.
        
        Returns:
            True si au moins une tentative a réussi
        """
        return self.status == "completed" and self.best_attempt is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la tâche de retraitement en dictionnaire.
        
        Returns:
            Dictionnaire représentant la tâche
        """
        return {
            "job_id": self.job_id,
            "document_id": self.document_id,
            "document_path": self.document_path,
            "issues": self.issues.to_dict() if self.issues else None,
            "attempts": [a.to_dict() for a in self.attempts],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "max_attempts": self.max_attempts,
            "requires_manual_validation": self.requires_manual_validation,
            "metadata": self.metadata,
            "attempt_count": self.attempt_count,
            "best_attempt": self.best_attempt.to_dict() if self.best_attempt else None,
            "is_completed": self.is_completed,
            "is_successful": self.is_successful
        }

class ReprocessingWorkflow:
    """
    Workflow de retraitement des documents problématiques.
    
    Cette classe gère le processus de retraitement automatique des documents
    qui présentent des problèmes de qualité, en utilisant des stratégies adaptatives
    et des mécanismes de rétroaction.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le workflow de retraitement.
        
        Args:
            config: Configuration optionnelle
        """
        from ...utils.config import get_config
        
        self.config = config or get_config().get("reprocessing", {})
        self.max_attempts = self.config.get("max_attempts", 3)
        self.task_queue = TaskQueueManager()
        self.document_store = DocumentStore()
        self.document_processor = DocumentProcessor()
        
        # Mémoire des jobs de retraitement
        self.jobs: Dict[str, ReprocessingJob] = {}
    
    async def create_job(self, validation_issues: DocumentValidationIssues) -> ReprocessingJob:
        """
        Crée une tâche de retraitement à partir des problèmes détectés.
        
        Args:
            validation_issues: Problèmes détectés dans le document
            
        Returns:
            Tâche de retraitement créée
        """
        job = ReprocessingJob(
            document_id=validation_issues.document_id,
            document_path=validation_issues.document_path,
            issues=validation_issues,
            max_attempts=self.max_attempts,
            requires_manual_validation=validation_issues.requires_manual_validation
        )
        
        # Ajouter des métadonnées
        job.metadata["issue_count"] = len(validation_issues.issues)
        job.metadata["critical_issue_count"] = sum(1 for i in validation_issues.issues if i.is_critical)
        job.metadata["severe_issue_count"] = sum(1 for i in validation_issues.issues if i.is_severe)
        job.metadata["initial_confidence"] = validation_issues.global_confidence
        
        # Stocker le job
        self.jobs[job.job_id] = job
        
        return job
    
    async def schedule_job(self, job: ReprocessingJob) -> str:
        """
        Planifie l'exécution d'une tâche de retraitement.
        
        Args:
            job: Tâche de retraitement à planifier
            
        Returns:
            Identifiant de la tâche planifiée
        """
        if job.is_completed:
            logger.warning(f"Tentative de planification d'une tâche déjà terminée: {job.job_id}")
            return job.job_id
        
        if job.attempt_count >= job.max_attempts:
            job.status = "failed"
            job.updated_at = datetime.now().isoformat()
            logger.warning(f"Nombre maximum de tentatives atteint pour la tâche {job.job_id}")
            
            # Si aucune tentative n'a réussi et que la validation manuelle est requise
            if not job.best_attempt and job.requires_manual_validation:
                job.status = "manual_validation"
                logger.info(f"Tâche {job.job_id} envoyée pour validation manuelle")
            
            return job.job_id
        
        # Préparer la nouvelle tentative
        attempt = ProcessingAttempt()
        
        # Déterminer les processeurs et paramètres à utiliser en fonction des tentatives précédentes
        processors, parameters = await self._determine_processing_strategy(job)
        attempt.processors_used = processors
        attempt.parameters = parameters
        
        # Ajouter la tentative à la tâche
        job.attempts.append(attempt)
        job.status = "processing"
        job.updated_at = datetime.now().isoformat()
        
        # Créer et planifier la tâche asynchrone
        document_path = Path(job.document_path)
        
        try:
            # Soumettre la tâche à la file d'attente
            task = await self.task_queue.submit_task(
                process_document_task,
                document_path=str(document_path),
                processors=processors,
                parameters=parameters,
                job_id=job.job_id,
                attempt_id=attempt.attempt_id
            )
            
            # Mettre à jour la tentative avec l'ID de tâche
            attempt.task_id = task.id
            attempt.status = "processing"
            
            logger.info(f"Tâche de retraitement planifiée: {job.job_id}, tentative {job.attempt_count}")
            
            return job.job_id
        
        except Exception as e:
            logger.exception(f"Erreur lors de la planification de la tâche {job.job_id}: {str(e)}")
            attempt.status = "error"
            attempt.error = str(e)
            
            # Vérifier s'il faut réessayer
            if job.attempt_count < job.max_attempts:
                # Attendre un peu avant de réessayer
                await asyncio.sleep(2)
                return await self.schedule_job(job)
            else:
                job.status = "failed"
                job.updated_at = datetime.now().isoformat()
                return job.job_id
    
    async def update_job_with_results(self, job_id: str, attempt_id: str, 
                                     results: Dict[str, Any]) -> ReprocessingJob:
        """
        Met à jour une tâche de retraitement avec les résultats d'une tentative.
        
        Args:
            job_id: Identifiant de la tâche
            attempt_id: Identifiant de la tentative
            results: Résultats du traitement
            
        Returns:
            Tâche mise à jour
        """
        if job_id not in self.jobs:
            logger.error(f"Tentative de mise à jour d'une tâche inconnue: {job_id}")
            return None
        
        job = self.jobs[job_id]
        
        # Rechercher la tentative correspondante
        attempt = next((a for a in job.attempts if a.attempt_id == attempt_id), None)
        if not attempt:
            logger.error(f"Tentative inconnue {attempt_id} pour la tâche {job_id}")
            return job
        
        # Mettre à jour la tentative
        attempt.status = "completed" if results.get("success", False) else "failed"
        attempt.result_summary = {
            "success": results.get("success", False),
            "processing_time": results.get("processing_time", 0),
            "pages_processed": results.get("page_count", 0),
            "text_length": len(results.get("text_content", ""))
        }
        
        # Mettre à jour les scores de confiance
        confidence_metrics = results.get("quality_metrics", {})
        for key, value in confidence_metrics.items():
            if isinstance(value, (int, float)):
                attempt.confidence_scores[key] = float(value)
        
        # Mettre à jour le statut global de la tâche
        job.updated_at = datetime.now().isoformat()
        
        # Décider de la suite du workflow
        if attempt.is_successful:
            # Vérifier si le résultat est suffisamment bon
            if attempt.overall_confidence >= 0.7:
                job.status = "completed"
                logger.info(f"Tâche {job_id} complétée avec succès")
            else:
                # Si la confiance est insuffisante, essayer une autre tentative
                if job.attempt_count < job.max_attempts:
                    logger.info(f"Confiance insuffisante pour la tâche {job_id}, planification d'une nouvelle tentative")
                    await self.schedule_job(job)
                else:
                    # Si c'était la dernière tentative, terminer avec le meilleur résultat
                    job.status = "completed"
                    logger.info(f"Nombre maximum de tentatives atteint pour la tâche {job_id}, terminaison avec le meilleur résultat")
        else:
            # Si la tentative a échoué, essayer à nouveau
            if job.attempt_count < job.max_attempts:
                logger.info(f"Échec de la tentative pour la tâche {job_id}, planification d'une nouvelle tentative")
                await self.schedule_job(job)
            else:
                # Si c'était la dernière tentative et qu'aucune n'a réussi
                if job.best_attempt:
                    job.status = "completed"
                    logger.info(f"Nombre maximum de tentatives atteint pour la tâche {job_id}, utilisation du meilleur résultat")
                else:
                    job.status = "failed"
                    logger.warning(f"Tâche {job_id} échouée après {job.max_attempts} tentatives")
                    
                    # Si la validation manuelle est requise
                    if job.requires_manual_validation:
                        job.status = "manual_validation"
                        logger.info(f"Tâche {job_id} envoyée pour validation manuelle")
        
        return job
    
    async def get_job(self, job_id: str) -> Optional[ReprocessingJob]:
        """
        Récupère une tâche de retraitement.
        
        Args:
            job_id: Identifiant de la tâche
            
        Returns:
            Tâche de retraitement ou None si inconnue
        """
        return self.jobs.get(job_id)
    
    async def get_job_results(self, job_id: str) -> Dict[str, Any]:
        """
        Récupère les résultats d'une tâche de retraitement.
        
        Args:
            job_id: Identifiant de la tâche
            
        Returns:
            Résultats du traitement ou None si la tâche est inconnue ou incomplète
        """
        job = await self.get_job(job_id)
        if not job:
            return None
        
        # Si la tâche n'est pas terminée, renvoyer son état actuel
        if not job.is_completed:
            return {
                "job_id": job.job_id,
                "status": job.status,
                "attempt_count": job.attempt_count,
                "message": f"Tâche en cours, {job.attempt_count}/{job.max_attempts} tentatives effectuées"
            }
        
        # Si la tâche a échoué, renvoyer l'erreur
        if job.status == "failed":
            return {
                "job_id": job.job_id,
                "status": "failed",
                "attempt_count": job.attempt_count,
                "message": "Toutes les tentatives ont échoué"
            }
        
        # Si la tâche nécessite une validation manuelle
        if job.status == "manual_validation":
            return {
                "job_id": job.job_id,
                "status": "manual_validation",
                "attempt_count": job.attempt_count,
                "message": "Validation manuelle requise",
                "best_attempt": job.best_attempt.to_dict() if job.best_attempt else None
            }
        
        # Si la tâche est terminée, renvoyer les résultats de la meilleure tentative
        best_attempt = job.best_attempt
        if not best_attempt:
            return {
                "job_id": job.job_id,
                "status": "error",
                "message": "Aucune tentative réussie trouvée"
            }
        
        # Récupérer les résultats complets de la meilleure tentative
        task_result = await self.task_queue.get_task_result(best_attempt.task_id)
        if not task_result:
            return {
                "job_id": job.job_id,
                "status": "completed",
                "message": "Résultats détaillés indisponibles",
                "summary": best_attempt.result_summary,
                "confidence": best_attempt.overall_confidence
            }
        
        return {
            "job_id": job.job_id,
            "status": "completed",
            "attempt_count": job.attempt_count,
            "best_attempt_id": best_attempt.attempt_id,
            "confidence": best_attempt.overall_confidence,
            "results": task_result
        }
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Annule une tâche de retraitement en cours.
        
        Args:
            job_id: Identifiant de la tâche
            
        Returns:
            True si la tâche a été annulée avec succès
        """
        job = await self.get_job(job_id)
        if not job or job.is_completed:
            return False
        
        # Annuler la tâche en cours
        current_attempt = job.attempts[-1] if job.attempts else None
        if current_attempt and current_attempt.status == "processing" and current_attempt.task_id:
            await self.task_queue.cancel_task(current_attempt.task_id)
            current_attempt.status = "cancelled"
        
        # Mettre à jour l'état de la tâche
        job.status = "cancelled"
        job.updated_at = datetime.now().isoformat()
        
        return True
    
    async def list_jobs(self, status: Optional[str] = None, 
                      limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Liste les tâches de retraitement.
        
        Args:
            status: Filtrer par statut
            limit: Nombre maximum de tâches à renvoyer
            offset: Décalage pour la pagination
            
        Returns:
            Liste des tâches de retraitement
        """
        jobs = list(self.jobs.values())
        
        # Filtrer par statut si spécifié
        if status:
            jobs = [job for job in jobs if job.status == status]
        
        # Trier par date de mise à jour (plus récent en premier)
        jobs.sort(key=lambda j: j.updated_at, reverse=True)
        
        # Appliquer la pagination
        paginated = jobs[offset:offset + limit]
        
        # Convertir en dictionnaires pour la sérialisation
        return [job.to_dict() for job in paginated]
    
    async def _determine_processing_strategy(self, job: ReprocessingJob) -> Tuple[List[str], Dict[str, Any]]:
        """
        Détermine la stratégie de traitement à utiliser pour la prochaine tentative.
        
        Args:
            job: Tâche de retraitement
            
        Returns:
            Tuple (processeurs à utiliser, paramètres)
        """
        # Analyser les tentatives précédentes et les problèmes détectés
        prior_attempts = job.attempts
        issues = job.issues.issues if job.issues else []
        
        # Classifier les problèmes par type
        issue_types = {}
        for issue in issues:
            if issue.content_type not in issue_types:
                issue_types[issue.content_type] = []
            issue_types[issue.content_type].append(issue)
        
        # Stratégie de base: utiliser les processeurs standards avec des paramètres optimisés
        processors = ["tesseract"]
        parameters = {
            "preprocessing": {
                "deskew": True,
                "denoise": True,
                "enhance_contrast": True
            },
            "ocr": {
                "language": "fra+eng",  # Langues par défaut
                "dpi": 300,
                "psm": 3  # Page segmentation mode: Auto
            }
        }
        
        # Si c'est la première tentative, choisir une stratégie basée sur les problèmes détectés
        if not prior_attempts:
            # Si de nombreux problèmes de texte, essayer un OCR plus robuste
            if "text" in issue_types and len(issue_types["text"]) > 3:
                # Vérifier si les problèmes sont critiques
                if any(i.is_critical for i in issue_types["text"]):
                    processors = ["document_ai"]  # Utiliser Google Document AI pour les cas difficiles
                else:
                    processors = ["ocrmypdf"]  # OCRmyPDF est un bon compromis
            
            # Si problèmes avec des formules, ajouter le processeur spécialisé
            if "formula" in issue_types:
                processors.append("formula")
                parameters["formula"] = {
                    "recognition_mode": "auto",
                    "confidence_threshold": 0.6
                }
            
            # Si problèmes avec des schémas, ajouter l'analyseur de schémas
            if "schema" in issue_types:
                processors.append("schema")
                parameters["schema"] = {
                    "detection_level": "detailed",
                    "min_confidence": 0.5
                }
            
            # Si problèmes avec des tableaux, ajouter l'extracteur de tableaux
            if "table" in issue_types:
                processors.append("table")
                parameters["table"] = {
                    "detect_headers": True,
                    "preserve_structure": True
                }
        
        # Si ce n'est pas la première tentative, adapter la stratégie en fonction des résultats précédents
        else:
            last_attempt = prior_attempts[-1]
            
            # Si la dernière tentative a échoué ou a une confiance faible, essayer une approche différente
            if not last_attempt.is_successful or last_attempt.overall_confidence < 0.6:
                # Alterner entre les moteurs OCR
                if "tesseract" in last_attempt.processors_used:
                    processors = ["ocrmypdf"]
                elif "ocrmypdf" in last_attempt.processors_used:
                    processors = ["document_ai"]
                else:
                    processors = ["tesseract"]
                
                # Si des processeurs spécialisés étaient utilisés, les conserver
                specialized = [p for p in last_attempt.processors_used if p in ["formula", "schema", "table"]]
                processors.extend(specialized)
                
                # Ajuster les paramètres en fonction des problèmes persistants
                if "ocr" in parameters:
                    # Essayer des paramètres plus agressifs pour le prétraitement
                    parameters["preprocessing"]["enhance_contrast"] = True
                    parameters["preprocessing"]["binarize"] = True
                    
                    # Modifier le mode de segmentation de page
                    if last_attempt.parameters.get("ocr", {}).get("psm") == 3:
                        parameters["ocr"]["psm"] = 6  # Suppose a single block of text
                    else:
                        parameters["ocr"]["psm"] = 3  # Auto
            
            # Si la tentative était proche du succès, affiner les paramètres
            elif last_attempt.overall_confidence >= 0.6:
                # Conserver les mêmes processeurs mais ajuster les paramètres
                processors = last_attempt.processors_used
                
                # Copier les paramètres de la dernière tentative
                parameters = last_attempt.parameters.copy()
                
                # Ajuster légèrement les paramètres pour améliorer les résultats
                if "preprocessing" in parameters:
                    # Augmenter la qualité du prétraitement
                    parameters["preprocessing"]["quality"] = "high"
                
                if "ocr" in parameters:
                    # Augmenter la résolution
                    current_dpi = parameters["ocr"].get("dpi", 300)
                    parameters["ocr"]["dpi"] = min(600, current_dpi + 150)
        
        # Ajouter toujours les postprocesseurs pour améliorer la qualité
        if "postprocessing" not in parameters:
            parameters["postprocessing"] = {}
        
        parameters["postprocessing"]["spell_check"] = True
        parameters["postprocessing"]["structure_preservation"] = True
        
        return processors, parameters
