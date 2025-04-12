"""
Tests unitaires pour les métriques de qualité OCR
================================================

Ce module contient les tests unitaires pour le système de métriques de qualité OCR.
Ces tests vérifient:
- L'évaluation correcte de la qualité du texte extrait
- Le calcul précis des scores de confiance et de cohérence linguistique
- La comparaison entre différents résultats d'OCR
- La détection des erreurs typiques d'OCR

Auteur: Équipe Technicia
Date: Avril 2025
"""

import pytest
import os
import re
import difflib
from unittest.mock import MagicMock, patch

from app.core.file_processing.ocr.quality_metrics import (
    OCRQualityEvaluator, OCRQualityResult, TextQualityMetrics
)

# Échantillons de texte pour les tests
@pytest.fixture
def sample_french_text():
    return """
    Ceci est un échantillon de texte en français pour tester l'évaluateur de qualité OCR.
    Il contient plusieurs mots courants qui devraient être reconnus correctement.
    Ce texte est suffisamment long pour permettre une évaluation statistique significative.
    """

@pytest.fixture
def sample_ocr_text_good():
    return """
    Ceci est un échantillon de texte en français pour tester l'évaluateur de qualité OCR.
    Il contient plusieurs mots courants qui devraient être reconnus correctement.
    Ce texte est suffisamment long pour permettre une évaluation statistique significative.
    """

@pytest.fixture
def sample_ocr_text_medium():
    return """
    Ceci est un échantill0n de texte en français pour testér l'évaluateur de qualité OCR.
    Il c0ntient plusieurs m0ts courants qui devraient être rec0nnus correctement.
    Ce texte est suffisamment l0ng pour permettre une évaluation statistique significative.
    """

@pytest.fixture
def sample_ocr_text_poor():
    return """
    C€ci €st un échantill0n d€ t€xt€ €n français p0ur t€st€r l'évaluat€ur d€ qualité OCR.
    Il c0nti€nt plusi€urs m0ts c0urants qui d€vrai€nt êtr€ r€c0nnus c0rr€ct€m€nt.
    C€ t€xt€ €st suffisam€nt l0ng p0ur p€rm€ttr€ un€ évaluati0n statistiqu€ significativ€.
    """

@pytest.fixture
def sample_formula_text():
    return "E = mc² où m représente la masse et c la vitesse de la lumière."

@pytest.fixture
def sample_technical_text():
    return """
    Le circuit électrique comprend un résistor de 220Ω connecté à une source de 12V.
    La tension aux bornes du condensateur est de 5.6V avec une capacité de 100μF.
    Le courant traversant la diode D1 est limité à 500mA par le fusible F1.
    """

@pytest.fixture
def evaluator():
    """Crée une instance de l'évaluateur de qualité OCR pour les tests."""
    return OCRQualityEvaluator()

class TestOCRQualityEvaluator:
    """Tests pour l'évaluateur de qualité OCR."""
    
    def test_evaluate_text_good_quality(self, evaluator, sample_ocr_text_good):
        """Teste l'évaluation d'un texte de bonne qualité."""
        result = evaluator.evaluate_text(sample_ocr_text_good, language="fra")
        
        # Vérifier que les scores sont élevés
        assert result.confidence_score > 0.9
        assert result.coherence_score > 0.9
        assert result.overall_score > 0.9
        assert result.error_count == 0
        assert len(result.warnings) == 0
        assert len(result.errors) == 0
    
    def test_evaluate_text_medium_quality(self, evaluator, sample_ocr_text_medium):
        """Teste l'évaluation d'un texte de qualité moyenne avec quelques erreurs."""
        result = evaluator.evaluate_text(sample_ocr_text_medium, language="fra")
        
        # Vérifier les scores
        assert 0.6 <= result.confidence_score <= 0.85
        assert 0.6 <= result.coherence_score <= 0.9
        assert 0.6 <= result.overall_score <= 0.85
        assert result.error_count > 0
        assert len(result.warnings) > 0
    
    def test_evaluate_text_poor_quality(self, evaluator, sample_ocr_text_poor):
        """Teste l'évaluation d'un texte de mauvaise qualité avec beaucoup d'erreurs."""
        result = evaluator.evaluate_text(sample_ocr_text_poor, language="fra")
        
        # Vérifier les scores
        assert result.confidence_score < 0.6
        assert result.coherence_score < 0.7
        assert result.overall_score < 0.6
        assert result.error_count > 5
        assert len(result.warnings) > 0
        assert len(result.errors) > 0
    
    def test_evaluate_text_different_languages(self, evaluator, sample_ocr_text_good):
        """Teste l'évaluation d'un texte avec différents paramètres de langue."""
        # Le même texte devrait avoir un score de cohérence différent selon la langue spécifiée
        result_fra = evaluator.evaluate_text(sample_ocr_text_good, language="fra")
        result_eng = evaluator.evaluate_text(sample_ocr_text_good, language="eng")
        
        # Le texte est en français, donc le score devrait être meilleur avec "fra"
        assert result_fra.coherence_score > result_eng.coherence_score
    
    def test_evaluate_formula(self, evaluator, sample_formula_text):
        """Teste l'évaluation d'un texte contenant des formules."""
        result = evaluator.evaluate_text(sample_formula_text, language="fra")
        
        # Les formules peuvent être traitées différemment
        assert result.confidence_score > 0.5
        assert "formula" in str(result.metadata).lower()
    
    def test_evaluate_technical_text(self, evaluator, sample_technical_text):
        """Teste l'évaluation d'un texte technique avec symboles spéciaux."""
        result = evaluator.evaluate_text(sample_technical_text, language="fra")
        
        # Les textes techniques peuvent contenir des symboles légitimes
        assert result.confidence_score > 0.7
        assert "technical" in str(result.metadata).lower()
    
    def test_compare_results(self, evaluator, sample_french_text, sample_ocr_text_medium, sample_ocr_text_poor):
        """Teste la comparaison entre un texte de référence et des résultats OCR."""
        # Comparaison avec un texte de qualité moyenne
        similarity_medium, metrics_medium = evaluator.compare_results(sample_french_text, sample_ocr_text_medium)
        
        # Comparaison avec un texte de mauvaise qualité
        similarity_poor, metrics_poor = evaluator.compare_results(sample_french_text, sample_ocr_text_poor)
        
        # Vérifier que les similarités sont correctement ordonnées
        assert similarity_medium > similarity_poor
        assert 0.7 <= similarity_medium <= 1.0
        assert similarity_poor < 0.7
        
        # Vérifier la présence des métriques détaillées
        assert "precision" in metrics_medium
        assert "recall" in metrics_medium
        assert "edit_distance" in metrics_medium
        
        # Vérifier que les métriques reflètent la qualité
        assert metrics_medium["precision"] > metrics_poor["precision"]
        assert metrics_medium["recall"] > metrics_poor["recall"]
        assert metrics_medium["edit_distance"] < metrics_poor["edit_distance"]
    
    def test_detect_ocr_errors(self, evaluator, sample_ocr_text_medium, sample_ocr_text_poor):
        """Teste la détection des erreurs typiques d'OCR."""
        # Détection dans un texte de qualité moyenne
        errors_medium = evaluator.detect_ocr_errors(sample_ocr_text_medium, language="fra")
        
        # Détection dans un texte de mauvaise qualité
        errors_poor = evaluator.detect_ocr_errors(sample_ocr_text_poor, language="fra")
        
        # Vérifier que plus d'erreurs sont détectées dans le texte de mauvaise qualité
        assert len(errors_poor) > len(errors_medium)
        
        # Vérifier la structure des erreurs détectées
        for error in errors_poor:
            assert "type" in error
            assert "position" in error
            assert "context" in error
            assert "suggestion" in error
        
        # Vérifier la détection des substitutions de caractères typiques (0 pour o, € pour e)
        substitution_errors = [e for e in errors_poor if e["type"] == "substitution"]
        assert len(substitution_errors) > 0
        assert any("0" in e["context"] for e in substitution_errors)
        assert any("€" in e["context"] for e in substitution_errors)
    
    def test_normalize_text(self, evaluator):
        """Teste la normalisation du texte pour la comparaison."""
        # Texte avec des espaces, majuscules et ponctuations
        original = "  Ceci est UN test! De normalisation... \n Avec des ESPACES supplémentaires.  "
        
        normalized = evaluator._normalize_text(original)
        
        # Vérifier la normalisation
        assert normalized == "ceci est un test de normalisation avec des espaces supplementaires"
        
        # Texte avec des caractères accentués
        accented = "Voici un texte avec des caractères accentués: éèêëàâäôöùûüçÉÈÊËÀÂÄÔÖÙÛÜÇ"
        
        normalized_accented = evaluator._normalize_text(accented, remove_accents=True)
        
        # Vérifier que les accents sont supprimés
        assert "é" not in normalized_accented
        assert "è" not in normalized_accented
        assert "ê" not in normalized_accented
    
    def test_calculate_confidence_from_text(self, evaluator, sample_ocr_text_good, sample_ocr_text_poor):
        """Teste le calcul du score de confiance à partir du texte."""
        # Calcul pour un texte de bonne qualité
        confidence_good = evaluator._calculate_confidence_from_text(sample_ocr_text_good)
        
        # Calcul pour un texte de mauvaise qualité
        confidence_poor = evaluator._calculate_confidence_from_text(sample_ocr_text_poor)
        
        # Vérifier que les scores reflètent la qualité
        assert confidence_good > 0.9
        assert confidence_poor < 0.7
        assert confidence_good > confidence_poor
    
    def test_evaluate_linguistic_coherence(self, evaluator, sample_ocr_text_good, sample_ocr_text_poor):
        """Teste l'évaluation de la cohérence linguistique."""
        # Évaluation pour un texte de bonne qualité
        coherence_good = evaluator._evaluate_linguistic_coherence(sample_ocr_text_good, language="fra")
        
        # Évaluation pour un texte de mauvaise qualité
        coherence_poor = evaluator._evaluate_linguistic_coherence(sample_ocr_text_poor, language="fra")
        
        # Vérifier que les scores reflètent la qualité
        assert coherence_good > 0.8
        assert coherence_poor < 0.7
        assert coherence_good > coherence_poor
    
    def test_quality_result_properties(self):
        """Teste les propriétés des objets OCRQualityResult."""
        # Créer des résultats avec différents scores
        good_result = OCRQualityResult(
            provider_name="tesseract",
            overall_score=0.92,
            confidence_score=0.94,
            coherence_score=0.90,
            error_count=0
        )
        
        medium_result = OCRQualityResult(
            provider_name="tesseract",
            overall_score=0.75,
            confidence_score=0.72,
            coherence_score=0.78,
            error_count=2,
            warnings=["Quelques caractères suspects détectés"]
        )
        
        poor_result = OCRQualityResult(
            provider_name="tesseract",
            overall_score=0.45,
            confidence_score=0.42,
            coherence_score=0.48,
            error_count=10,
            errors=["Nombreux caractères non reconnus", "Cohérence linguistique faible"]
        )
        
        # Vérifier les propriétés
        assert good_result.is_acceptable is True
        assert good_result.is_high_quality is True
        assert good_result.requires_verification is False
        
        assert medium_result.is_acceptable is True
        assert medium_result.is_high_quality is False
        assert medium_result.requires_verification is True
        
        assert poor_result.is_acceptable is False
        assert poor_result.is_high_quality is False
        assert poor_result.requires_verification is True
        
        # Vérifier la conversion en dictionnaire
        result_dict = medium_result.to_dict()
        assert result_dict["provider_name"] == "tesseract"
        assert result_dict["overall_score"] == 0.75
        assert result_dict["is_acceptable"] is True
        assert result_dict["is_high_quality"] is False
        assert len(result_dict["warnings"]) == 1

class TestTextQualityMetrics:
    """Tests pour les métriques de qualité de texte."""
    
    def test_calculate_char_confidence(self):
        """Teste le calcul de la confiance au niveau des caractères."""
        metrics = TextQualityMetrics()
        
        # Texte sans caractères suspects
        clean_text = "Ceci est un texte sans caractères suspects."
        confidence_clean = metrics.calculate_char_confidence(clean_text)
        
        # Texte avec caractères suspects
        suspect_text = "C€ci €st un t€xt€ av€c d€s caract€r€s susp€cts."
        confidence_suspect = metrics.calculate_char_confidence(suspect_text)
        
        # Vérifier les scores
        assert confidence_clean > 0.9
        assert confidence_suspect < 0.7
        assert confidence_clean > confidence_suspect
    
    def test_calculate_word_confidence(self):
        """Teste le calcul de la confiance au niveau des mots."""
        metrics = TextQualityMetrics()
        
        # Texte avec mots communs
        common_text = "Ceci est un texte avec des mots communs et fréquents en français."
        confidence_common = metrics.calculate_word_confidence(common_text, language="fra")
        
        # Texte avec mots rares ou mal orthographiés
        rare_text = "Cxci ewt um texve avoc des mogs reres et mwl orthogrsphiés."
        confidence_rare = metrics.calculate_word_confidence(rare_text, language="fra")
        
        # Vérifier les scores
        assert confidence_common > 0.8
        assert confidence_rare < 0.5
        assert confidence_common > confidence_rare
    
    def test_identify_suspicious_patterns(self):
        """Teste l'identification des patterns suspects dans le texte."""
        metrics = TextQualityMetrics()
        
        # Texte avec différents patterns suspects
        text_with_patterns = """
        Ce texte contient plusieurs patterns suspects:
        1. Des caractères répétés: aaaaaaaa
        2. Des séquences improbables: xzqw
        3. Des caractères non-latins: 你好世界
        4. Des mélanges chiffres/lettres suspects: l1l1l1O0O0O
        5. Des caractères rares dans le contexte français: þæð
        """
        
        suspicious_patterns = metrics.identify_suspicious_patterns(text_with_patterns, language="fra")
        
        # Vérifier la détection des patterns
        assert len(suspicious_patterns) >= 3
        
        # Vérifier les types de patterns détectés
        pattern_types = [p["type"] for p in suspicious_patterns]
        assert "repeated_chars" in pattern_types
        assert "non_latin_chars" in pattern_types
        assert "confusable_chars" in pattern_types or "rare_chars" in pattern_types
        
        # Vérifier la structure des patterns détectés
        for pattern in suspicious_patterns:
            assert "type" in pattern
            assert "text" in pattern
            assert "position" in pattern or "count" in pattern
    
    def test_evaluate_text_structure(self):
        """Teste l'évaluation de la structure du texte."""
        metrics = TextQualityMetrics()
        
        # Texte bien structuré
        well_structured = """
        Ceci est un texte bien structuré avec des paragraphes.
        
        Ce deuxième paragraphe contient plusieurs phrases. Il a une structure
        normale avec des espaces et de la ponctuation correcte.
        
        Le troisième paragraphe termine le texte de manière cohérente.
        """
        
        # Texte mal structuré
        poorly_structured = """CeciEstUnTexteSansEspaceCorrectementPlacéEtSansPonctuationCorrecteLesMotsSont
        CollésEtLaStructureDesParagraphesEst InexistanteOuIncohérenteDesEspacesSontParfoisMalPlacés"""
        
        # Évaluer les textes
        structure_score_good = metrics.evaluate_text_structure(well_structured)
        structure_score_poor = metrics.evaluate_text_structure(poorly_structured)
        
        # Vérifier les scores
        assert structure_score_good > 0.8
        assert structure_score_poor < 0.6
        assert structure_score_good > structure_score_poor
    
    def test_calculate_edit_distance_metrics(self):
        """Teste le calcul des métriques basées sur la distance d'édition."""
        metrics = TextQualityMetrics()
        
        reference = "Ceci est un texte de référence pour le test."
        similar = "Ceci est un texte de référence pour le test"  # Ponctuation manquante
        different = "Ceci est texte référence pour test."  # Mots manquants
        very_different = "C'est un autre texte complètement différent."  # Très différent
        
        # Calculer les métriques
        similar_metrics = metrics.calculate_edit_distance_metrics(reference, similar)
        different_metrics = metrics.calculate_edit_distance_metrics(reference, different)
        very_different_metrics = metrics.calculate_edit_distance_metrics(reference, very_different)
        
        # Vérifier les valeurs de distance d'édition (plus petit = plus similaire)
        assert similar_metrics["edit_distance"] < different_metrics["edit_distance"]
        assert different_metrics["edit_distance"] < very_different_metrics["edit_distance"]
        
        # Vérifier les ratios de similarité (plus grand = plus similaire)
        assert similar_metrics["similarity_ratio"] > different_metrics["similarity_ratio"]
        assert different_metrics["similarity_ratio"] > very_different_metrics["similarity_ratio"]
        
        # Vérifier la précision et le rappel (doivent être entre 0 et 1)
        assert 0 <= similar_metrics["precision"] <= 1
        assert 0 <= similar_metrics["recall"] <= 1
        assert similar_metrics["precision"] >= different_metrics["precision"]
        assert similar_metrics["recall"] >= different_metrics["recall"]
