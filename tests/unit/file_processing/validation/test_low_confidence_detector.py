"""
Tests unitaires pour le détecteur d'extractions à faible confiance
==================================================================

Ce module contient les tests unitaires pour le détecteur d'extractions à faible confiance
du système de validation de l'OCR. Ces tests vérifient la capacité du détecteur à:
- Identifier correctement les problèmes dans différents types de contenu (texte, formules, schémas, tableaux)
- Appliquer les seuils de confiance appropriés selon le type de contenu
- Générer les métadonnées et actions pertinentes pour chaque type de problème détecté

Auteur: Équipe Technicia
Date: Avril 2025
"""

import pytest
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.core.file_processing.validation.low_confidence_detector import (
    LowConfidenceDetector, ContentIssue, DocumentValidationIssues
)
from app.core.file_processing.ocr.quality_metrics import OCRQualityResult

# Fixtures pour simuler les résultats de traitement
@pytest.fixture
def sample_text_content():
    return """
    Ceci est un exemple de texte pour tester le détecteur de basse confiance.
    Il contient des mots en français qui devraient être reconnus correctement.
    Cependant, nous allons également inclure quelques erreurs typiques d'OCR
    comme des caractères mal reconnus: 0l (zéro et l) ou 1I (un et I majuscule).
    """

@pytest.fixture
def sample_processing_result():
    """Crée un résultat de traitement de document typique pour les tests."""
    return {
        "document_id": "test_doc_123",
        "text_content": sample_text_content(),
        "language": "fra",
        "page_count": 3,
        "processors_used": ["tesseract", "schema"],
        "pages": [
            {
                "page_number": 1,
                "text_content": "Contenu de la page 1 avec une qualité acceptable.",
                "confidence": 0.85
            },
            {
                "page_number": 2,
                "text_content": "C0ntenu d€ la pàge 2 avec qu€lques erreurs oCR.",
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
                ],
                "tables": [
                    {
                        "confidence": 0.72,
                        "rows": 5,
                        "columns": 3,
                        "region": {"x": 50, "y": 600, "width": 500, "height": 200},
                        "cells": [
                            {"text": "Colonne 1", "row": 0, "column": 0},
                            {"text": "Colonne 2", "row": 0, "column": 1},
                            {"text": "Colonne 3", "row": 0, "column": 2},
                            {"text": "", "row": 2, "column": 1}
                        ]
                    }
                ]
            }
        ]
    }

@pytest.fixture
def mock_ocr_quality_result():
    """Simule un résultat d'évaluation de qualité OCR."""
    return OCRQualityResult(
        provider_name="tesseract",
        overall_score=0.72,
        confidence_score=0.68,
        coherence_score=0.75,
        error_count=4,
        warnings=["Plusieurs caractères suspects détectés"],
        errors=["Incohérence avec le dictionnaire: 'qu€lques'"]
    )

@pytest.fixture
def detector():
    """Crée une instance du détecteur de basse confiance pour les tests."""
    detector = LowConfidenceDetector(config={
        "thresholds": {
            "text": {"acceptable": 0.7, "warning": 0.5, "critical": 0.3},
            "formula": {"acceptable": 0.75, "warning": 0.6, "critical": 0.4},
            "schema": {"acceptable": 0.65, "warning": 0.5, "critical": 0.35},
            "table": {"acceptable": 0.7, "warning": 0.55, "critical": 0.4}
        }
    })
    # Simuler l'initialisation des détecteurs spécialisés
    detector.formula_processor = MagicMock()
    detector.schema_analyzer = MagicMock()
    return detector

class TestLowConfidenceDetector:
    """Tests pour le détecteur d'extractions à faible confiance."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Teste l'initialisation du détecteur avec ses processeurs spécialisés."""
        detector = LowConfidenceDetector()
        
        with patch('app.core.file_processing.specialized_processors.formula_processor.FormulaProcessor') as mock_formula, \
             patch('app.core.file_processing.specialized_processors.schema_analyzer.SchemaAnalyzer') as mock_schema:
            
            # Simuler l'initialisation réussie des processeurs
            mock_formula.return_value.initialize = AsyncMock(return_value=True)
            mock_schema.return_value.initialize = AsyncMock(return_value=True)
            
            result = await detector.initialize()
            
            assert result is True
            mock_formula.return_value.initialize.assert_called_once()
            mock_schema.return_value.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_document_global_quality(self, detector, sample_processing_result, mock_ocr_quality_result):
        """Teste l'analyse de la qualité globale d'un document."""
        with patch('app.core.file_processing.ocr.quality_metrics.OCRQualityEvaluator.evaluate_text',
                  return_value=mock_ocr_quality_result):
            
            result = await detector.analyze_document("test_doc.pdf", sample_processing_result)
            
            # Vérifier que l'analyse a bien fonctionné
            assert result.document_id == "test_doc_123"
            assert result.global_confidence == mock_ocr_quality_result.overall_score
            
            # Vérifier la détection des problèmes globaux
            global_issues = [i for i in result.issues if i.issue_type == "global_ocr_quality"]
            assert len(global_issues) == 1
            assert global_issues[0].confidence == mock_ocr_quality_result.overall_score
            assert len(global_issues[0].suggested_actions) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_document_page_quality(self, detector, sample_processing_result):
        """Teste l'analyse de la qualité par page."""
        # Simuler des résultats de qualité différents par page
        page_quality_results = [
            OCRQualityResult(provider_name="tesseract", overall_score=0.85),
            OCRQualityResult(provider_name="tesseract", overall_score=0.45, 
                            warnings=["Qualité OCR insuffisante"]),
            OCRQualityResult(provider_name="tesseract", overall_score=0.75)
        ]
        
        with patch('app.core.file_processing.ocr.quality_metrics.OCRQualityEvaluator.evaluate_text',
                  side_effect=[OCRQualityResult(provider_name="tesseract", overall_score=0.72)] + page_quality_results):
            
            result = await detector.analyze_document("test_doc.pdf", sample_processing_result)
            
            # Vérifier la détection des problèmes par page
            page_issues = [i for i in result.issues if i.issue_type == "page_ocr_quality"]
            assert len(page_issues) == 1  # Seulement la page 2 devrait avoir un problème
            assert page_issues[0].page_number == 2
            assert page_issues[0].confidence == 0.45
    
    @pytest.mark.asyncio
    async def test_check_formulas(self, detector, sample_processing_result):
        """Teste la détection des problèmes dans les formules."""
        # Simuler la méthode _check_formulas
        formulas = sample_processing_result["pages"][1]["formulas"]
        issues = DocumentValidationIssues(document_id="test_doc", document_path="test_doc.pdf")
        
        await detector._check_formulas(formulas, 2, issues)
        
        # Vérifier les problèmes détectés
        formula_issues = [i for i in issues.issues if i.content_type == "formula"]
        assert len(formula_issues) == 1
        assert formula_issues[0].confidence == 0.58
        assert formula_issues[0].page_number == 2
        assert "formula_type" in formula_issues[0].metadata
        assert formula_issues[0].content_sample == "E = mc²"
    
    @pytest.mark.asyncio
    async def test_check_schemas(self, detector, sample_processing_result):
        """Teste la détection des problèmes dans les schémas."""
        # Simuler la méthode _check_schemas
        schemas = sample_processing_result["pages"][2]["schemas"]
        issues = DocumentValidationIssues(document_id="test_doc", document_path="test_doc.pdf")
        
        await detector._check_schemas(schemas, 3, issues)
        
        # Vérifier les problèmes détectés
        schema_issues = [i for i in issues.issues if i.content_type == "schema"]
        assert len(schema_issues) > 0
        assert "schema_type" in schema_issues[0].metadata
    
    def test_check_tables(self, detector, sample_processing_result):
        """Teste la détection des problèmes dans les tableaux."""
        # Simuler la méthode _check_tables
        tables = sample_processing_result["pages"][2]["tables"]
        issues = DocumentValidationIssues(document_id="test_doc", document_path="test_doc.pdf")
        
        detector._check_tables(tables, 3, issues)
        
        # Vérifier les problèmes détectés
        table_issues = [i for i in issues.issues if i.content_type == "table"]
        assert len(table_issues) == 0  # Le tableau est au-dessus du seuil
        
        # Modifier la confiance du tableau pour tester la détection
        tables[0]["confidence"] = 0.65
        detector._check_tables(tables, 3, issues)
        
        # Maintenant on devrait avoir un problème
        table_issues = [i for i in issues.issues if i.content_type == "table"]
        assert len(table_issues) == 1
        assert table_issues[0].confidence == 0.65
        assert "row_count" in table_issues[0].metadata
    
    def test_check_problem_patterns(self, detector):
        """Teste la détection des patterns problématiques dans le texte."""
        # Texte avec des patterns problématiques
        text_with_problems = """
        Ce texte contient des patterns problématiques comme des caractères non-latins: 你好世界
        Et des suites de caractères spéciaux: @#$%^&*!@#$
        Et aussi des ponctuations répétées: !!!???...
        """
        
        issues = DocumentValidationIssues(document_id="test_doc", document_path="test_doc.pdf")
        
        detector._check_problem_patterns(text_with_problems, 1, issues)
        
        # Vérifier les problèmes détectés
        pattern_issues = [i for i in issues.issues if i.issue_type == "text_pattern_issue"]
        assert len(pattern_issues) > 0
        
        # Vérifier que les échantillons contiennent bien les problèmes
        found_non_latin = False
        found_special_chars = False
        found_punctuation = False
        
        for issue in pattern_issues:
            if "你好世界" in issue.content_sample:
                found_non_latin = True
            if "@#$%^&*!@#$" in issue.content_sample:
                found_special_chars = True
            if "!!!???" in issue.content_sample:
                found_punctuation = True
        
        assert found_non_latin or found_special_chars or found_punctuation
    
    def test_content_issue_properties(self):
        """Teste les propriétés des objets ContentIssue."""
        # Tester différents niveaux de confiance
        critical_issue = ContentIssue(
            issue_type="test_issue",
            content_type="text",
            confidence=0.3
        )
        severe_issue = ContentIssue(
            issue_type="test_issue",
            content_type="text",
            confidence=0.5
        )
        minor_issue = ContentIssue(
            issue_type="test_issue",
            content_type="text",
            confidence=0.7
        )
        
        # Vérifier les propriétés
        assert critical_issue.is_critical is True
        assert critical_issue.is_severe is True
        
        assert severe_issue.is_critical is False
        assert severe_issue.is_severe is True
        
        assert minor_issue.is_critical is False
        assert minor_issue.is_severe is False
        
        # Vérifier la conversion en dictionnaire
        issue_dict = critical_issue.to_dict()
        assert issue_dict["issue_type"] == "test_issue"
        assert issue_dict["content_type"] == "text"
        assert issue_dict["confidence"] == 0.3
        assert issue_dict["is_critical"] is True
    
    def test_document_validation_issues_properties(self):
        """Teste les propriétés des objets DocumentValidationIssues."""
        # Créer un objet avec différents types de problèmes
        issues = DocumentValidationIssues(
            document_id="test_doc",
            document_path="test_doc.pdf",
            global_confidence=0.65
        )
        
        # Ajouter des problèmes de différentes gravités
        issues.issues.append(ContentIssue(
            issue_type="critical_issue",
            content_type="text",
            confidence=0.3
        ))
        issues.issues.append(ContentIssue(
            issue_type="severe_issue",
            content_type="formula",
            confidence=0.5
        ))
        issues.issues.append(ContentIssue(
            issue_type="minor_issue",
            content_type="table",
            confidence=0.7
        ))
        
        # Vérifier les propriétés
        assert issues.has_critical_issues is True
        assert issues.has_severe_issues is True
        assert issues.requires_reprocessing is True
        
        # Vérifier la propriété de validation manuelle
        # Par défaut, seuls des problèmes très spécifiques requièrent une validation manuelle
        assert issues.requires_manual_validation is False
        
        # Ajouter un problème critique sur une formule (nécessite validation manuelle)
        issues.issues.append(ContentIssue(
            issue_type="critical_formula_issue",
            content_type="formula",
            confidence=0.2
        ))
        
        # Maintenant la validation manuelle devrait être requise
        assert issues.requires_manual_validation is True
        
        # Vérifier la conversion en dictionnaire
        issues_dict = issues.to_dict()
        assert issues_dict["document_id"] == "test_doc"
        assert issues_dict["global_confidence"] == 0.65
        assert len(issues_dict["issues"]) == 4
        assert issues_dict["has_critical_issues"] is True
        assert issues_dict["requires_reprocessing"] is True
