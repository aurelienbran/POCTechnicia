"""
Tests unitaires pour le validateur d'échantillonnage
===================================================

Ce module contient les tests unitaires pour le validateur d'échantillonnage
du système de validation et d'amélioration itérative. Ces tests vérifient:
- L'échantillonnage représentatif des documents traités
- L'identification des tendances et problèmes récurrents
- La génération de recommandations d'amélioration basées sur les données
- La validation statistique des résultats

Auteur: Équipe Technicia
Date: Avril 2025
"""

import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from app.core.file_processing.validation.sampling_validator import (
    SamplingValidator, SamplingStrategy, ValidationReport, SamplingStatistics, 
    ImprovementRecommendation
)

@pytest.fixture
def sample_processed_documents():
    """Fournit un échantillon de documents traités pour les tests."""
    return [
        {
            "document_id": f"doc_{i}",
            "document_path": f"d:/test/docs/doc_{i}.pdf",
            "processing_date": (datetime.now() - timedelta(days=i)).isoformat(),
            "processing_time": float(np.random.uniform(1.5, 10)),
            "page_count": np.random.randint(1, 30),
            "quality_metrics": {
                "confidence": float(np.random.uniform(0.4, 0.95)),
                "coherence": float(np.random.uniform(0.5, 0.95)),
                "error_count": np.random.randint(0, 20)
            },
            "processor_info": {
                "ocr_engine": "tesseract" if i % 3 != 0 else "document_ai",
                "version": "5.3.0" if i % 3 != 0 else "2.1",
                "parameters": {
                    "psm": np.random.randint(1, 13),
                    "preprocessed": bool(i % 2)
                }
            },
            "content_types": {
                "text": float(np.random.uniform(0.5, 0.9)),
                "formula": float(np.random.uniform(0, 0.3)) if i % 5 == 0 else 0,
                "schema": float(np.random.uniform(0, 0.4)) if i % 3 == 0 else 0,
                "table": float(np.random.uniform(0, 0.3)) if i % 4 == 0 else 0
            },
            "validation_issues": {
                "global_confidence": float(np.random.uniform(0.5, 0.95)),
                "issue_count": np.random.randint(0, 10),
                "critical_issues": np.random.randint(0, 3),
                "issue_types": ["text_quality"] if i % 2 == 0 else ["schema_quality", "table_quality"]
            }
        }
        for i in range(50)  # 50 documents de test
    ]

@pytest.fixture
def validator():
    """Crée une instance du validateur d'échantillonnage pour les tests."""
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

class TestSamplingValidator:
    """Tests pour le validateur d'échantillonnage."""
    
    @pytest.mark.asyncio
    async def test_get_document_sample(self, validator, sample_processed_documents):
        """Teste la récupération d'un échantillon de documents."""
        # Configurer le mock du document_store
        validator.document_store.get_documents_by_criteria = AsyncMock(
            return_value=sample_processed_documents
        )
        
        # Récupérer un échantillon avec la stratégie par défaut
        sample = await validator.get_document_sample(
            strategy=SamplingStrategy.RANDOM,
            sample_size=20
        )
        
        # Vérifier le résultat
        assert len(sample) == 20
        assert all(isinstance(doc, dict) for doc in sample)
        assert "document_id" in sample[0]
        validator.document_store.get_documents_by_criteria.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_document_sample_stratified(self, validator, sample_processed_documents):
        """Teste la récupération d'un échantillon stratifié de documents."""
        # Configurer le mock du document_store
        validator.document_store.get_documents_by_criteria = AsyncMock(
            return_value=sample_processed_documents
        )
        
        # Récupérer un échantillon stratifié
        sample = await validator.get_document_sample(
            strategy=SamplingStrategy.STRATIFIED,
            sample_size=30,
            stratify_by="processor_info.ocr_engine"
        )
        
        # Vérifier le résultat
        assert len(sample) == 30
        
        # Vérifier qu'on a bien une stratification
        engines = set(doc["processor_info"]["ocr_engine"] for doc in sample)
        assert len(engines) > 1
    
    @pytest.mark.asyncio
    async def test_get_document_sample_recent_first(self, validator, sample_processed_documents):
        """Teste la récupération d'un échantillon de documents récents."""
        # Configurer le mock du document_store
        validator.document_store.get_documents_by_criteria = AsyncMock(
            return_value=sample_processed_documents
        )
        
        # Récupérer un échantillon avec priorité aux plus récents
        sample = await validator.get_document_sample(
            strategy=SamplingStrategy.RECENT_FIRST,
            sample_size=10
        )
        
        # Vérifier le résultat
        assert len(sample) == 10
        
        # Vérifier que les documents sont triés par date (du plus récent au plus ancien)
        dates = [datetime.fromisoformat(doc["processing_date"]) for doc in sample]
        assert all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
    
    @pytest.mark.asyncio
    async def test_compute_statistics(self, validator, sample_processed_documents):
        """Teste le calcul des statistiques sur un échantillon."""
        # Effectuer le calcul des statistiques
        stats = await validator.compute_statistics(sample_processed_documents)
        
        # Vérifier les résultats
        assert isinstance(stats, SamplingStatistics)
        assert stats.sample_size == len(sample_processed_documents)
        assert 0 <= stats.mean_confidence <= 1
        assert stats.median_processing_time > 0
        assert stats.issue_ratio >= 0
        
        # Vérifier les distributions
        assert "ocr_engine" in stats.distributions
        assert len(stats.distributions["ocr_engine"]) > 0
        
        # Vérifier l'analyse par type de contenu
        assert "text" in stats.content_type_stats
        assert stats.content_type_stats["text"]["mean_confidence"] > 0
    
    @pytest.mark.asyncio
    async def test_trend_analysis(self, validator, sample_processed_documents):
        """Teste l'analyse des tendances."""
        # Trier les documents par date
        sorted_docs = sorted(
            sample_processed_documents,
            key=lambda d: datetime.fromisoformat(d["processing_date"]),
            reverse=True
        )
        
        # Effectuer l'analyse des tendances
        trends = await validator.analyze_trends(sorted_docs)
        
        # Vérifier les résultats
        assert "confidence_trend" in trends
        assert "processing_time_trend" in trends
        assert "issue_count_trend" in trends
        
        # Vérifier la valeur du trend (upward, downward, stable)
        assert trends["confidence_trend"] in ["upward", "downward", "stable"]
    
    @pytest.mark.asyncio
    async def test_identify_patterns(self, validator, sample_processed_documents):
        """Teste l'identification des patterns et problèmes récurrents."""
        # Simuler des problèmes spécifiques
        for doc in sample_processed_documents[:10]:
            doc["quality_metrics"]["confidence"] = 0.42
            doc["validation_issues"]["issue_types"] = ["text_quality", "suspicious_chars"]
        
        # Identifier les patterns
        patterns = await validator.identify_patterns(sample_processed_documents)
        
        # Vérifier les résultats
        assert len(patterns) > 0
        assert all(isinstance(p, dict) for p in patterns)
        assert "pattern_type" in patterns[0]
        assert "frequency" in patterns[0]
        assert "affected_documents" in patterns[0]
        
        # Vérifier qu'au moins un pattern correspond aux problèmes simulés
        suspicious_chars_pattern = next(
            (p for p in patterns if "suspicious_chars" in p.get("description", "")),
            None
        )
        assert suspicious_chars_pattern is not None
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self, validator, sample_processed_documents):
        """Teste la génération de recommandations d'amélioration."""
        # Simuler des statistiques montrant des problèmes particuliers
        stats = await validator.compute_statistics(sample_processed_documents)
        
        # Pour simuler des problèmes, modifions certaines valeurs manuellement
        stats.mean_confidence = 0.65  # En dessous du seuil de 0.75
        stats.content_type_stats["formula"] = {
            "mean_confidence": 0.55,
            "document_count": 10,
            "critical_issue_ratio": 0.3
        }
        
        # Simuler des tendances
        trends = {
            "confidence_trend": "downward",
            "processing_time_trend": "upward",
            "issue_count_trend": "upward"
        }
        
        # Générer des recommandations
        recommendations = await validator.generate_recommendations(
            stats=stats,
            trends=trends,
            patterns=[
                {"pattern_type": "recurring_issue", "description": "Caractères suspects détectés", "frequency": 0.25}
            ]
        )
        
        # Vérifier les recommandations
        assert len(recommendations) > 0
        assert all(isinstance(r, ImprovementRecommendation) for r in recommendations)
        
        # Vérifier les types de recommandations
        categories = set(r.category for r in recommendations)
        assert len(categories) > 0
        
        # Vérifier les priorités
        assert any(r.priority == "high" for r in recommendations)
        
        # Vérifier les actions suggérées
        assert all(len(r.suggested_actions) > 0 for r in recommendations)
    
    @pytest.mark.asyncio
    async def test_full_validation_process(self, validator, sample_processed_documents):
        """Teste le processus complet de validation."""
        # Configurer les mocks
        validator.document_store.get_documents_by_criteria = AsyncMock(
            return_value=sample_processed_documents
        )
        validator.metrics_collector.record_validation_report = AsyncMock()
        
        # Exécuter le processus complet de validation
        report = await validator.validate(
            time_period_days=30,
            sample_size=40
        )
        
        # Vérifier le rapport
        assert isinstance(report, ValidationReport)
        assert report.sample_size == 40
        assert report.timestamp is not None
        assert report.statistics is not None
        assert len(report.recommendations) > 0
        
        # Vérifier l'enregistrement du rapport
        validator.metrics_collector.record_validation_report.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimize_processing_parameters(self, validator, sample_processed_documents):
        """Teste l'optimisation des paramètres de traitement."""
        # Préparer un échantillon avec différentes configurations
        # Modifier le sample pour avoir des tendances claires
        for i, doc in enumerate(sample_processed_documents):
            if doc["processor_info"]["parameters"]["psm"] == 6:
                doc["quality_metrics"]["confidence"] = 0.85 + float(np.random.uniform(-0.05, 0.05))
                doc["processing_time"] = 3.0 + float(np.random.uniform(-1.0, 1.0))
        
        # Exécuter l'optimisation
        optimized_params = await validator.optimize_processing_parameters(sample_processed_documents)
        
        # Vérifier les paramètres optimisés
        assert isinstance(optimized_params, dict)
        assert "ocr" in optimized_params
        assert "psm" in optimized_params["ocr"]
        assert "preprocessed" in optimized_params["ocr"]
        assert all(isinstance(v, (int, bool, float, str)) for k, v in optimized_params["ocr"].items())
    
    @pytest.mark.asyncio
    async def test_report_to_dict(self, validator, sample_processed_documents):
        """Teste la conversion du rapport en dictionnaire."""
        # Créer un rapport
        stats = await validator.compute_statistics(sample_processed_documents)
        recommendations = [
            ImprovementRecommendation(
                category="ocr_quality",
                description="Améliorer la qualité globale de l'OCR",
                priority="high",
                suggested_actions=["Mettre à jour le moteur OCR", "Ajuster les paramètres de prétraitement"]
            ),
            ImprovementRecommendation(
                category="formula_processing",
                description="Améliorer la reconnaissance des formules",
                priority="medium",
                suggested_actions=["Utiliser un modèle spécialisé pour les formules"]
            )
        ]
        
        report = ValidationReport(
            timestamp=datetime.now(),
            sample_size=len(sample_processed_documents),
            statistics=stats,
            trends={
                "confidence_trend": "stable",
                "processing_time_trend": "downward",
                "issue_count_trend": "downward"
            },
            patterns=[
                {"pattern_type": "success_pattern", "description": "Meilleurs résultats avec prétraitement"}
            ],
            recommendations=recommendations
        )
        
        # Convertir en dictionnaire
        report_dict = report.to_dict()
        
        # Vérifier la structure du dictionnaire
        assert "timestamp" in report_dict
        assert "sample_size" in report_dict
        assert "statistics" in report_dict
        assert "recommendations" in report_dict
        assert isinstance(report_dict["recommendations"], list)
        assert len(report_dict["recommendations"]) == 2

class TestSamplingStatistics:
    """Tests pour la classe SamplingStatistics."""
    
    def test_properties(self):
        """Teste les propriétés des statistiques d'échantillonnage."""
        # Créer un objet SamplingStatistics
        stats = SamplingStatistics(
            sample_size=50,
            mean_confidence=0.78,
            median_processing_time=3.5,
            critical_issue_ratio=0.08,
            issue_ratio=0.15,
            distributions={
                "ocr_engine": {"tesseract": 0.7, "document_ai": 0.3}
            },
            content_type_stats={
                "text": {"mean_confidence": 0.82, "document_count": 50},
                "formula": {"mean_confidence": 0.68, "document_count": 10}
            }
        )
        
        # Vérifier les propriétés calculées
        assert stats.is_confidence_acceptable is True  # 0.78 > 0.75 (seuil par défaut)
        assert stats.is_processing_time_acceptable is True  # 3.5 < 5.0 (seuil par défaut)
        assert stats.is_issue_ratio_acceptable is True  # 0.08 < 0.1 (seuil par défaut)
        
        # Modifier les valeurs pour tester les seuils
        stats.mean_confidence = 0.65
        assert stats.is_confidence_acceptable is False  # 0.65 < 0.75
        
        # Vérifier la conversion en dictionnaire
        stats_dict = stats.to_dict()
        assert stats_dict["sample_size"] == 50
        assert stats_dict["mean_confidence"] == 0.65
        assert stats_dict["is_confidence_acceptable"] is False
        assert "distributions" in stats_dict
        assert "content_type_stats" in stats_dict

class TestImprovementRecommendation:
    """Tests pour la classe ImprovementRecommendation."""
    
    def test_properties(self):
        """Teste les propriétés des recommandations d'amélioration."""
        # Créer une recommandation
        recommendation = ImprovementRecommendation(
            category="ocr_quality",
            description="Améliorer la qualité OCR pour les formules",
            priority="high",
            impact_estimate=0.85,
            suggested_actions=[
                "Utiliser un modèle spécialisé pour les formules",
                "Ajuster le prétraitement pour les formules"
            ],
            affected_documents=["doc_1", "doc_3", "doc_5"]
        )
        
        # Vérifier les propriétés
        assert recommendation.category == "ocr_quality"
        assert recommendation.priority == "high"
        assert len(recommendation.suggested_actions) == 2
        
        # Vérifier la conversion en dictionnaire
        rec_dict = recommendation.to_dict()
        assert rec_dict["category"] == "ocr_quality"
        assert rec_dict["priority"] == "high"
        assert rec_dict["impact_estimate"] == 0.85
        assert len(rec_dict["suggested_actions"]) == 2
        assert len(rec_dict["affected_documents"]) == 3
