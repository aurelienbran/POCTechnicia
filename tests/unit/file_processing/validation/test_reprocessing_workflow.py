"""
Tests unitaires pour le workflow de retraitement
================================================

Ce module contient les tests unitaires pour le workflow de retraitement
du système de validation et d'amélioration itérative. Ces tests vérifient:
- La création et la gestion des tâches de retraitement
- L'adaptation intelligente des stratégies en fonction des résultats précédents
- La persistance et le suivi des tentatives multiples de traitement
- La logique de sélection des meilleurs résultats

Auteur: Équipe Technicia
Date: Avril 2025
"""

import pytest
import json
from datetime import datetime, timedelta
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.file_processing.validation.reprocessing_workflow import (
    ReprocessingWorkflow, ReprocessingJob, ProcessingAttempt
)
from app.core.file_processing.validation.low_confidence_detector import (
    DocumentValidationIssues, ContentIssue
)

# Fixtures pour les tests
@pytest.fixture
def sample_validation_issues():
    """Crée un exemple d'issues de validation pour les tests."""
    issues = DocumentValidationIssues(
        document_id="test_doc_123",
        document_path="d:/test/docs/test_doc_123.pdf",
        global_confidence=0.45
    )
    
    # Ajouter quelques problèmes
    issues.issues.extend([
        ContentIssue(
            issue_type="global_ocr_quality",
            content_type="text",
            confidence=0.45,
            description="Qualité OCR globale insuffisante"
        ),
        ContentIssue(
            issue_type="formula_quality",
            content_type="formula",
            page_number=2,
            confidence=0.35,
            description="Formule avec confiance insuffisante"
        ),
        ContentIssue(
            issue_type="text_pattern_issue",
            content_type="text",
            page_number=3,
            confidence=0.4,
            description="Problème de texte détecté: suspect_characters"
        )
    ])
    
    return issues

@pytest.fixture
def sample_processing_result():
    """Crée un exemple de résultat de traitement pour les tests."""
    return {
        "document_id": "test_doc_123",
        "success": True,
        "processing_time": 4.2,
        "page_count": 3,
        "text_content": "Contenu extrait du document",
        "quality_metrics": {
            "confidence": 0.68,
            "error_count": 2,
            "coherence": 0.7
        }
    }

@pytest.fixture
def workflow():
    """Crée une instance du workflow de retraitement pour les tests."""
    with patch('app.core.tasks.task_queue.TaskQueueManager'), \
         patch('app.core.storage.document_store.DocumentStore'), \
         patch('app.core.file_processing.document_processor.DocumentProcessor'):
        
        workflow = ReprocessingWorkflow(config={
            "max_attempts": 3,
            "strategies": {
                "default": ["tesseract"],
                "fallback": ["document_ai"]
            }
        })
        
        # Mock des dépendances
        workflow.task_queue = MagicMock()
        workflow.task_queue.submit_task = AsyncMock()
        workflow.task_queue.get_task_result = AsyncMock()
        workflow.document_store = MagicMock()
        workflow.document_processor = MagicMock()
        
        return workflow

class TestReprocessingWorkflow:
    """Tests pour le workflow de retraitement."""
    
    @pytest.mark.asyncio
    async def test_create_job(self, workflow, sample_validation_issues):
        """Teste la création d'une tâche de retraitement."""
        job = await workflow.create_job(sample_validation_issues)
        
        # Vérifier les propriétés de base
        assert job.document_id == "test_doc_123"
        assert job.document_path == "d:/test/docs/test_doc_123.pdf"
        assert job.issues is sample_validation_issues
        assert job.max_attempts == 3
        assert job.status == "created"
        assert len(job.attempts) == 0
        
        # Vérifier les métadonnées
        assert job.metadata["issue_count"] == 3
        assert job.metadata["critical_issue_count"] > 0
        assert job.metadata["initial_confidence"] == 0.45
        
        # Vérifier les propriétés calculées
        assert job.attempt_count == 0
        assert job.is_completed is False
        assert job.best_attempt is None
        
        # Vérifier que le job a été stocké
        assert job.job_id in workflow.jobs
    
    @pytest.mark.asyncio
    async def test_schedule_job(self, workflow, sample_validation_issues):
        """Teste la planification d'une tâche de retraitement."""
        job = await workflow.create_job(sample_validation_issues)
        
        # Simuler la réponse du gestionnaire de tâches
        task_mock = MagicMock()
        task_mock.id = "task_123"
        workflow.task_queue.submit_task.return_value = task_mock
        
        # Planifier la tâche
        job_id = await workflow.schedule_job(job)
        
        # Vérifier les mises à jour
        assert job_id == job.job_id
        assert job.status == "processing"
        assert len(job.attempts) == 1
        assert job.attempts[0].status == "processing"
        assert job.attempts[0].task_id == "task_123"
        
        # Vérifier que la tâche a été soumise
        workflow.task_queue.submit_task.assert_called_once()
        
        # Vérifier les paramètres de la soumission
        call_args = workflow.task_queue.submit_task.call_args[1]
        assert call_args["document_path"] == "d:/test/docs/test_doc_123.pdf"
        assert call_args["job_id"] == job.job_id
        assert call_args["attempt_id"] == job.attempts[0].attempt_id
    
    @pytest.mark.asyncio
    async def test_update_job_with_results(self, workflow, sample_validation_issues, sample_processing_result):
        """Teste la mise à jour d'une tâche avec les résultats d'une tentative."""
        # Créer et planifier une tâche
        job = await workflow.create_job(sample_validation_issues)
        
        task_mock = MagicMock()
        task_mock.id = "task_123"
        workflow.task_queue.submit_task.return_value = task_mock
        
        await workflow.schedule_job(job)
        
        # Vérifier l'état initial
        assert job.status == "processing"
        assert job.attempts[0].status == "processing"
        
        # Mettre à jour la tâche avec les résultats
        updated_job = await workflow.update_job_with_results(
            job_id=job.job_id,
            attempt_id=job.attempts[0].attempt_id,
            results=sample_processing_result
        )
        
        # Vérifier les mises à jour
        assert updated_job.job_id == job.job_id
        assert updated_job.attempts[0].status == "completed"
        assert updated_job.attempts[0].result_summary["success"] is True
        assert "text_length" in updated_job.attempts[0].result_summary
        
        # Vérifier les scores de confiance
        assert updated_job.attempts[0].confidence_scores["confidence"] == 0.68
        assert updated_job.attempts[0].is_successful is True
        
        # Vérifier l'état global de la tâche (devrait être completed car score suffisant)
        assert updated_job.status == "completed"
    
    @pytest.mark.asyncio
    async def test_update_job_with_poor_results(self, workflow, sample_validation_issues):
        """Teste la mise à jour d'une tâche avec des résultats insuffisants."""
        # Créer et planifier une tâche
        job = await workflow.create_job(sample_validation_issues)
        
        task_mock = MagicMock()
        task_mock.id = "task_123"
        workflow.task_queue.submit_task.return_value = task_mock
        
        await workflow.schedule_job(job)
        
        # Résultats avec une confiance insuffisante
        poor_results = {
            "document_id": "test_doc_123",
            "success": True,
            "processing_time": 4.5,
            "page_count": 3,
            "quality_metrics": {
                "confidence": 0.48,  # Confiance insuffisante
                "error_count": 8,
                "coherence": 0.45
            }
        }
        
        # Mettre à jour la tâche avec les résultats
        updated_job = await workflow.update_job_with_results(
            job_id=job.job_id,
            attempt_id=job.attempts[0].attempt_id,
            results=poor_results
        )
        
        # La tâche devrait être toujours en cours car les résultats sont insuffisants
        # et une nouvelle tentative devrait être planifiée
        assert updated_job.status != "completed"
        
        # Vérifier que la planification d'une nouvelle tentative a été initiée
        assert workflow.task_queue.submit_task.call_count > 1
    
    @pytest.mark.asyncio
    async def test_determine_processing_strategy(self, workflow, sample_validation_issues):
        """Teste la détermination de la stratégie de traitement."""
        job = await workflow.create_job(sample_validation_issues)
        
        # Première tentative (basée sur les problèmes détectés)
        processors, parameters = await workflow._determine_processing_strategy(job)
        
        # Vérifier la stratégie initiale
        assert "tesseract" in processors or "document_ai" in processors  # Au moins un processeur OCR
        assert "formula" in processors  # Le processeur de formules doit être inclus
        assert "preprocessing" in parameters
        assert "ocr" in parameters
        
        # Simuler une tentative échouée
        job.attempts.append(ProcessingAttempt(
            processors_used=["tesseract", "formula"],
            parameters={"ocr": {"psm": 3}},
            status="completed",
            overall_confidence=0.45,
            result_summary={"success": True}
        ))
        
        # Déterminer la stratégie pour la deuxième tentative
        processors2, parameters2 = await workflow._determine_processing_strategy(job)
        
        # Vérifier l'adaptation de la stratégie
        assert processors2 != processors  # La stratégie doit changer
        assert any(p not in processors for p in processors2)  # Au moins un nouveau processeur
        assert parameters2 != parameters  # Les paramètres doivent changer
    
    @pytest.mark.asyncio
    async def test_get_job_results(self, workflow, sample_validation_issues, sample_processing_result):
        """Teste la récupération des résultats d'une tâche."""
        # Créer et planifier une tâche
        job = await workflow.create_job(sample_validation_issues)
        
        task_mock = MagicMock()
        task_mock.id = "task_123"
        workflow.task_queue.submit_task.return_value = task_mock
        
        await workflow.schedule_job(job)
        
        # Mettre à jour la tâche avec les résultats
        await workflow.update_job_with_results(
            job_id=job.job_id,
            attempt_id=job.attempts[0].attempt_id,
            results=sample_processing_result
        )
        
        # Simuler la récupération des résultats complets
        workflow.task_queue.get_task_result.return_value = sample_processing_result
        
        # Récupérer les résultats
        results = await workflow.get_job_results(job.job_id)
        
        # Vérifier les résultats
        assert results["job_id"] == job.job_id
        assert results["status"] == "completed"
        assert results["attempt_count"] == 1
        assert results["confidence"] > 0
        assert "results" in results
        assert results["results"] == sample_processing_result
    
    @pytest.mark.asyncio
    async def test_cancel_job(self, workflow, sample_validation_issues):
        """Teste l'annulation d'une tâche en cours."""
        # Créer et planifier une tâche
        job = await workflow.create_job(sample_validation_issues)
        
        task_mock = MagicMock()
        task_mock.id = "task_123"
        workflow.task_queue.submit_task.return_value = task_mock
        
        await workflow.schedule_job(job)
        
        # Annuler la tâche
        workflow.task_queue.cancel_task = AsyncMock(return_value=True)
        result = await workflow.cancel_job(job.job_id)
        
        # Vérifier l'annulation
        assert result is True
        assert job.status == "cancelled"
        assert job.attempts[0].status == "cancelled"
        workflow.task_queue.cancel_task.assert_called_once_with("task_123")
    
    @pytest.mark.asyncio
    async def test_list_jobs(self, workflow, sample_validation_issues):
        """Teste la liste des tâches."""
        # Créer plusieurs tâches avec différents statuts
        job1 = await workflow.create_job(sample_validation_issues)
        job1.status = "completed"
        
        job2 = await workflow.create_job(sample_validation_issues)
        job2.status = "processing"
        
        job3 = await workflow.create_job(sample_validation_issues)
        job3.status = "failed"
        
        # Récupérer la liste des tâches
        all_jobs = await workflow.list_jobs()
        completed_jobs = await workflow.list_jobs(status="completed")
        
        # Vérifier les résultats
        assert len(all_jobs) == 3
        assert len(completed_jobs) == 1
        assert all_jobs[0]["status"] in ["completed", "processing", "failed"]
        assert completed_jobs[0]["status"] == "completed"

class TestProcessingAttempt:
    """Tests pour la classe ProcessingAttempt."""
    
    def test_properties(self):
        """Teste les propriétés d'une tentative de traitement."""
        # Tentative réussie
        successful_attempt = ProcessingAttempt(
            processors_used=["tesseract", "formula"],
            status="completed",
            confidence_scores={"confidence": 0.85, "coherence": 0.9}
        )
        
        # Tentative échouée
        failed_attempt = ProcessingAttempt(
            processors_used=["tesseract"],
            status="failed",
            error="Timeout during processing"
        )
        
        # Vérifier les propriétés
        assert successful_attempt.is_successful is True
        assert successful_attempt.overall_confidence == 0.875
        
        assert failed_attempt.is_successful is False
        assert failed_attempt.overall_confidence == 0.0
        
        # Vérifier la conversion en dictionnaire
        attempt_dict = successful_attempt.to_dict()
        assert attempt_dict["processors_used"] == ["tesseract", "formula"]
        assert attempt_dict["status"] == "completed"
        assert attempt_dict["is_successful"] is True
        assert attempt_dict["overall_confidence"] == 0.875

class TestReprocessingJob:
    """Tests pour la classe ReprocessingJob."""
    
    def test_properties(self):
        """Teste les propriétés d'une tâche de retraitement."""
        # Créer une tâche avec plusieurs tentatives
        job = ReprocessingJob(
            document_id="test_doc",
            document_path="test_doc.pdf",
            max_attempts=3
        )
        
        # Ajouter des tentatives
        job.attempts.append(ProcessingAttempt(
            attempt_id="attempt1",
            status="completed",
            confidence_scores={"confidence": 0.6},
            result_summary={"success": True}
        ))
        
        job.attempts.append(ProcessingAttempt(
            attempt_id="attempt2",
            status="completed",
            confidence_scores={"confidence": 0.75},
            result_summary={"success": True}
        ))
        
        # Tâche en cours
        assert job.attempt_count == 2
        assert job.is_completed is False
        
        # Meilleure tentative
        best = job.best_attempt
        assert best is not None
        assert best.attempt_id == "attempt2"
        assert best.confidence_scores["confidence"] == 0.75
        
        # Terminer la tâche
        job.status = "completed"
        
        # Vérifier l'état final
        assert job.is_completed is True
        assert job.is_successful is True
        
        # Vérifier la conversion en dictionnaire
        job_dict = job.to_dict()
        assert job_dict["document_id"] == "test_doc"
        assert job_dict["attempt_count"] == 2
        assert job_dict["is_completed"] is True
        assert job_dict["is_successful"] is True
        assert job_dict["best_attempt"]["attempt_id"] == "attempt2"
