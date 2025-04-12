"""
Tests d'intégration pour le pipeline de validation OCR
=====================================================

Ce module contient les tests d'intégration pour le pipeline complet de validation OCR,
incluant l'interaction entre:
- Le détecteur de basse confiance (LowConfidenceDetector)
- Le workflow de retraitement (ReprocessingWorkflow)
- Le validateur d'échantillonnage (SamplingValidator)

Ces tests vérifient que les différents composants fonctionnent correctement ensemble
et que le flux de données entre eux est cohérent.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import pytest
import os
import json
from datetime import datetime, timedelta
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.file_processing.validation.low_confidence_detector import (
    LowConfidenceDetector, ContentIssue, DocumentValidationIssues
)
from app.core.file_processing.validation.reprocessing_workflow import (
    ReprocessingWorkflow, ReprocessingJob, ProcessingAttempt
)
from app.core.file_processing.validation.sampling_validator import (
    SamplingValidator, SamplingStrategy, ValidationReport
)

# Fixtures communs
@pytest.fixture
def sample_document_path():
    """Chemin d'un document fictif pour les tests."""
    return "d:/test/documents/test_doc_123.pdf"

@pytest.fixture
def sample_processing_result():
    """Créer un résultat de traitement typique pour les tests."""
    return {
        "document_id": "test_doc_123",
        "text_content": "Ceci est un exemple de texte extrait par OCR avec quelques problèmes.",
        "page_count": 3,
        "processors_used": ["tesseract", "formula"],
        "language": "fra",
        "pages": [
            {
                "page_number": 1,
                "text_content": "Contenu de la page 1 avec une qualité acceptable.",
                "confidence": 0.85
            },
            {
                "page_number": 2,
                "text_content": "C0ntenu de la pàge 2 avec qu€lques erreurs oCR.",
                "confidence": 0.62,
                "formulas": [
                    {
                        "formula_text": "E = mc²",
                        "confidence": 0.58,
                        "region": {"x": 100, "y": 200, "width": 150, "height": 50},
                        "formula_type": "physics"
                    }
                ]
            },
            {
                "page_number": 3,
                "text_content": "Contenu de la page 3 avec schéma technique.",
                "confidence": 0.75,
                "schemas": [
                    {
                        "description": "Schéma électrique avec connexions multiples",
                        "confidence": 0.67,
                        "region": {"x": 150, "y": 300, "width": 400, "height": 300},
                        "schema_type": "electrical"
                    }
                ]
            }
        ],
        "quality_metrics": {
            "confidence": 0.72,
            "coherence": 0.75,
            "error_count": 4
        }
    }

# Fixtures pour les instances des composants
@pytest.fixture
def detector():
    """Crée une instance du détecteur de basse confiance."""
    with patch('app.core.file_processing.specialized_processors.formula_processor.FormulaProcessor'), \
         patch('app.core.file_processing.specialized_processors.schema_analyzer.SchemaAnalyzer'):
        
        detector = LowConfidenceDetector(config={
            "thresholds": {
                "text": {"acceptable": 0.7, "warning": 0.5, "critical": 0.3},
                "formula": {"acceptable": 0.75, "warning": 0.6, "critical": 0.4},
                "schema": {"acceptable": 0.65, "warning": 0.5, "critical": 0.35},
                "table": {"acceptable": 0.7, "warning": 0.55, "critical": 0.4}
            }
        })
        
        # Mock des dépendances
        detector.formula_processor = MagicMock()
        detector.schema_analyzer = MagicMock()
        detector.initialize = AsyncMock(return_value=True)
        
        return detector

@pytest.fixture
def workflow():
    """Crée une instance du workflow de retraitement."""
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

@pytest.fixture
def validator():
    """Crée une instance du validateur d'échantillonnage."""
    with patch('app.core.storage.document_store.DocumentStore'), \
         patch('app.core.analytics.metrics_collector.MetricsCollector'):
        
        validator = SamplingValidator(config={
            "sampling": {
                "default_size": 30,
                "time_period_days": 30,
                "stratified_categories": ["content_types", "processor_info.ocr_engine"]
            },
            "thresholds": {
                "confidence": 0.75,
                "critical_issues_ratio": 0.1,
                "processing_time_median": 5.0
            }
        })
        
        # Mock des dépendances
        validator.document_store = MagicMock()
        validator.metrics_collector = MagicMock()
        
        return validator

class TestValidationPipeline:
    """Tests pour le pipeline complet de validation OCR."""
    
    @pytest.mark.asyncio
    async def test_document_validation_to_reprocessing(self, 
                                               detector, 
                                               workflow, 
                                               sample_document_path, 
                                               sample_processing_result):
        """
        Teste le flux de validation de document qui conduit au retraitement.
        
        Ce test vérifie:
        1. La détection des problèmes dans un document
        2. La création d'une tâche de retraitement basée sur ces problèmes
        3. La planification de la tâche de retraitement
        """
        # 1. Détecter les problèmes dans le document
        validation_result = await detector.analyze_document(
            document_path=sample_document_path,
            processing_result=sample_processing_result
        )
        
        # Vérifier que des problèmes ont été détectés
        assert validation_result.has_issues
        assert validation_result.document_id == sample_processing_result["document_id"]
        assert len(validation_result.issues) > 0
        
        # S'assurer qu'au moins un problème nécessite un retraitement
        assert validation_result.requires_reprocessing
        
        # 2. Créer une tâche de retraitement
        job = await workflow.create_job(validation_result)
        
        # Vérifier les propriétés de la tâche
        assert job.document_id == validation_result.document_id
        assert job.document_path == validation_result.document_path
        assert job.max_attempts == 3
        assert job.status == "created"
        
        # 3. Simuler une réponse du gestionnaire de tâches
        task_mock = MagicMock()
        task_mock.id = "task_123"
        workflow.task_queue.submit_task.return_value = task_mock
        
        # Planifier la tâche
        job_id = await workflow.schedule_job(job)
        
        # Vérifier la planification
        assert job.status == "processing"
        assert len(job.attempts) == 1
        assert workflow.task_queue.submit_task.call_count == 1
        
        # Vérifier que les bons paramètres ont été transmis
        call_args = workflow.task_queue.submit_task.call_args[1]
        assert call_args["document_path"] == validation_result.document_path
    
    @pytest.mark.asyncio
    async def test_reprocessing_results_update_validation(self, 
                                                  detector, 
                                                  workflow, 
                                                  sample_document_path, 
                                                  sample_processing_result):
        """
        Teste la mise à jour des résultats de validation après retraitement.
        
        Ce test vérifie:
        1. La création d'une tâche de retraitement basée sur des problèmes détectés
        2. La mise à jour de la tâche avec les résultats améliorés
        3. La nouvelle analyse du document pour confirmer l'amélioration
        """
        # 1. Détecter les problèmes et créer une tâche
        validation_result = await detector.analyze_document(
            document_path=sample_document_path,
            processing_result=sample_processing_result
        )
        
        job = await workflow.create_job(validation_result)
        
        # Simuler la planification
        task_mock = MagicMock()
        task_mock.id = "task_123"
        workflow.task_queue.submit_task.return_value = task_mock
        await workflow.schedule_job(job)
        
        # 2. Préparer un résultat amélioré
        improved_result = sample_processing_result.copy()
        improved_result["quality_metrics"] = {
            "confidence": 0.92,  # Amélioration significative
            "coherence": 0.94,
            "error_count": 1
        }
        improved_result["pages"][1]["confidence"] = 0.88  # Page problématique améliorée
        improved_result["pages"][1]["formulas"][0]["confidence"] = 0.85  # Formule améliorée
        
        # Mise à jour avec les résultats améliorés
        updated_job = await workflow.update_job_with_results(
            job_id=job.job_id,
            attempt_id=job.attempts[0].attempt_id,
            results=improved_result
        )
        
        # Vérifier l'état final de la tâche
        assert updated_job.status == "completed"
        assert updated_job.attempts[0].is_successful is True
        assert updated_job.attempts[0].confidence_scores["confidence"] > 0.9
        
        # 3. Analyser à nouveau le document avec les résultats améliorés
        new_validation = await detector.analyze_document(
            document_path=sample_document_path,
            processing_result=improved_result
        )
        
        # Vérifier l'amélioration
        assert new_validation.has_issues is False or len(new_validation.issues) < len(validation_result.issues)
        assert new_validation.global_confidence > validation_result.global_confidence
        assert new_validation.requires_reprocessing is False
    
    @pytest.mark.asyncio
    async def test_validation_sampling_based_on_reprocessing(self, validator, workflow):
        """
        Teste l'analyse d'échantillons pour évaluer l'efficacité du retraitement.
        
        Ce test vérifie:
        1. La récupération d'un échantillon de documents traités
        2. L'identification des tendances et patterns dans les résultats
        3. La génération de recommandations pour améliorer le traitement
        """
        # Préparer un ensemble de jobs de retraitement avec différents résultats
        jobs = []
        for i in range(20):
            job = ReprocessingJob(
                job_id=f"job_{i}",
                document_id=f"doc_{i}",
                document_path=f"d:/test/docs/doc_{i}.pdf"
            )
            
            # Simuler quelques tentatives avec différents résultats
            confidence = 0.65 + (i % 10) * 0.03  # Scores variés
            
            # Première tentative
            job.attempts.append(ProcessingAttempt(
                processors_used=["tesseract"],
                parameters={"ocr": {"psm": 3}},
                status="completed",
                overall_confidence=confidence,
                result_summary={"success": True}
            ))
            
            # Pour certains documents, ajouter une deuxième tentative avec de meilleurs résultats
            if i % 3 == 0:
                job.attempts.append(ProcessingAttempt(
                    processors_used=["document_ai"],
                    parameters={"ocr": {"enhanced": True}},
                    status="completed",
                    overall_confidence=confidence + 0.15,  # Amélioration significative
                    result_summary={"success": True}
                ))
                job.status = "completed"
            else:
                job.status = "completed" if job.attempts[0].overall_confidence > 0.75 else "failed"
            
            jobs.append(job)
        
        # Simuler l'accès aux jobs de retraitement
        workflow.jobs = {job.job_id: job for job in jobs}
        workflow.list_jobs = AsyncMock(return_value=[job.to_dict() for job in jobs])
        
        # Simuler les documents dans le document_store
        processed_docs = []
        for i, job in enumerate(jobs):
            best_attempt = job.best_attempt
            if best_attempt:
                doc = {
                    "document_id": job.document_id,
                    "document_path": job.document_path,
                    "processing_date": (datetime.now() - timedelta(days=i % 10)).isoformat(),
                    "quality_metrics": {
                        "confidence": best_attempt.overall_confidence
                    },
                    "processor_info": {
                        "ocr_engine": best_attempt.processors_used[0],
                        "parameters": best_attempt.parameters.get("ocr", {})
                    },
                    "reprocessing_info": {
                        "job_id": job.job_id,
                        "attempt_count": len(job.attempts),
                        "final_status": job.status
                    }
                }
                processed_docs.append(doc)
        
        validator.document_store.get_documents_by_criteria = AsyncMock(return_value=processed_docs)
        
        # Effectuer l'échantillonnage et l'analyse
        report = await validator.validate(time_period_days=30, sample_size=15)
        
        # Vérifier le rapport
        assert report is not None
        assert report.sample_size > 0
        assert report.statistics is not None
        assert len(report.recommendations) > 0
        
        # Vérifier les statistiques spécifiques au retraitement
        reprocessing_stats = next(
            (stat for stat in report.statistics.distributions.values() 
             if "reprocessing" in str(stat).lower()),
            None
        )
        assert reprocessing_stats is not None
        
        # Vérifier les recommandations liées au retraitement
        reprocessing_recs = [
            rec for rec in report.recommendations 
            if "reprocessing" in rec.description.lower() or "ocr_engine" in rec.category
        ]
        assert len(reprocessing_recs) > 0
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation_pipeline(self, 
                                         detector, 
                                         workflow, 
                                         validator, 
                                         sample_document_path, 
                                         sample_processing_result):
        """
        Teste le flux complet du pipeline de validation, du document initial à l'analyse d'échantillons.
        
        Ce test vérifie:
        1. La détection des problèmes dans un document
        2. Le retraitement du document
        3. L'analyse d'échantillons qui inclut ce document
        4. Les recommandations générées pour améliorer le système
        """
        # 1. Détecter les problèmes dans le document
        validation_result = await detector.analyze_document(
            document_path=sample_document_path,
            processing_result=sample_processing_result
        )
        
        # 2. Créer et planifier une tâche de retraitement
        job = await workflow.create_job(validation_result)
        
        task_mock = MagicMock()
        task_mock.id = "task_123"
        workflow.task_queue.submit_task.return_value = task_mock
        await workflow.schedule_job(job)
        
        # Préparer un résultat amélioré
        improved_result = sample_processing_result.copy()
        improved_result["quality_metrics"] = {
            "confidence": 0.88,
            "coherence": 0.9,
            "error_count": 1
        }
        
        # Mettre à jour la tâche avec les résultats
        updated_job = await workflow.update_job_with_results(
            job_id=job.job_id,
            attempt_id=job.attempts[0].attempt_id,
            results=improved_result
        )
        
        # Simuler plusieurs jobs de retraitement pour l'échantillonnage
        jobs = [updated_job]
        for i in range(19):  # Ajouter 19 jobs fictifs pour atteindre 20 au total
            fake_job = ReprocessingJob(
                job_id=f"job_{i}",
                document_id=f"doc_{i}",
                document_path=f"d:/test/docs/doc_{i}.pdf",
                status="completed"
            )
            fake_job.attempts.append(ProcessingAttempt(
                processors_used=["tesseract" if i % 2 == 0 else "document_ai"],
                parameters={"ocr": {"enhanced": i % 3 == 0}},
                status="completed",
                overall_confidence=0.7 + (i % 10) * 0.02,
                result_summary={"success": True}
            ))
            jobs.append(fake_job)
        
        # Configurer les mocks pour l'échantillonnage
        workflow.jobs = {job.job_id: job for job in jobs}
        workflow.list_jobs = AsyncMock(return_value=[job.to_dict() for job in jobs])
        
        # Préparer les documents pour l'échantillonnage
        processed_docs = []
        for i, job in enumerate(jobs):
            best_attempt = job.best_attempt if hasattr(job, 'best_attempt') and job.best_attempt else job.attempts[0]
            doc = {
                "document_id": job.document_id,
                "document_path": job.document_path,
                "processing_date": (datetime.now() - timedelta(days=i % 10)).isoformat(),
                "quality_metrics": {
                    "confidence": best_attempt.overall_confidence if hasattr(best_attempt, 'overall_confidence') else 0.8,
                    "coherence": 0.85,
                    "error_count": 2
                },
                "processor_info": {
                    "ocr_engine": best_attempt.processors_used[0] if hasattr(best_attempt, 'processors_used') else "tesseract",
                    "parameters": best_attempt.parameters.get("ocr", {}) if hasattr(best_attempt, 'parameters') else {"enhanced": False}
                },
                "reprocessing_info": {
                    "job_id": job.job_id,
                    "attempt_count": len(job.attempts),
                    "final_status": job.status
                }
            }
            processed_docs.append(doc)
        
        validator.document_store.get_documents_by_criteria = AsyncMock(return_value=processed_docs)
        
        # 3. Effectuer l'échantillonnage et l'analyse
        report = await validator.validate(time_period_days=30, sample_size=15)
        
        # 4. Vérifier les recommandations générées
        assert report.recommendations is not None
        assert len(report.recommendations) > 0
        
        # Vérifier que les statistiques contiennent des informations sur notre document original
        stats = report.statistics
        assert stats is not None
        assert stats.sample_size > 0
        
        # Vérifier la présence de notre moteur OCR dans les distributions
        assert "ocr_engine" in stats.distributions
        engines = stats.distributions["ocr_engine"]
        assert "tesseract" in engines or "document_ai" in engines
        
        # Vérifier qu'il y a au moins une recommandation pertinente
        relevant_recs = [
            rec for rec in report.recommendations 
            if any(keyword in rec.description.lower() 
                for keyword in ["ocr", "retraitement", "qualité", "confiance"])
        ]
        assert len(relevant_recs) > 0
