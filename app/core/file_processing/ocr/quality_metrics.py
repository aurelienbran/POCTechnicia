"""
Module d'évaluation de la qualité des résultats OCR
=================================================

Ce module fournit des outils pour évaluer la précision et la qualité des 
résultats d'OCR, ainsi que pour comparer les performances de différents 
moteurs OCR sur les mêmes documents.

Caractéristiques principales:
- Calcul de scores de confiance pour les résultats OCR
- Détection des erreurs courantes (caractères mal reconnus, mots incohérents)
- Métriques d'évaluation basées sur diverses heuristiques (dictionnaires, expressions régulières)
- Système de comparaison pour déterminer la méthode OCR la plus performante
- Génération de rapports détaillés sur la qualité des résultats

Utilisation typique:
```python
# Évaluation d'un résultat OCR
evaluator = OCRQualityEvaluator()
score = await evaluator.evaluate_result(ocr_result)
print(f"Score global: {score.overall_score}")

# Comparaison de deux résultats OCR
comparison = await evaluator.compare_results(result1, result2)
print(f"Meilleur résultat: {comparison.best_result}")
```

Auteur: Équipe Technicia
Date: Mars 2025
"""

import logging
import re
import json
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import difflib
import statistics
import time

logger = logging.getLogger(__name__)

@dataclass
class OCRQualityResult:
    """
    Résultat d'évaluation de la qualité OCR.
    
    Attributs:
        provider_name (str): Nom du fournisseur OCR
        processing_time (float): Temps de traitement en secondes
        character_count (int): Nombre de caractères dans le texte
        word_count (int): Nombre de mots dans le texte
        confidence_score (float): Score de confiance (0.0 à 1.0)
        language_score (float): Score de cohérence linguistique (0.0 à 1.0)
        formatting_score (float): Score de formatage (0.0 à 1.0)
        overall_score (float): Score global (0.0 à 1.0)
        error_count (int): Nombre d'erreurs détectées
        warnings (List[str]): Liste d'avertissements
        details (Dict[str, Any]): Détails supplémentaires
    """
    provider_name: str
    processing_time: float = 0.0
    character_count: int = 0
    word_count: int = 0
    confidence_score: float = 0.0  # 0.0 à 1.0
    language_score: float = 0.0  # 0.0 à 1.0
    formatting_score: float = 0.0  # 0.0 à 1.0
    overall_score: float = 0.0  # 0.0 à 1.0
    error_count: int = 0
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le résultat en dictionnaire.
        
        Returns:
            Dictionnaire représentant le résultat
        """
        return {
            "provider_name": self.provider_name,
            "processing_time": self.processing_time,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "confidence_score": self.confidence_score,
            "language_score": self.language_score,
            "formatting_score": self.formatting_score,
            "overall_score": self.overall_score,
            "error_count": self.error_count,
            "warnings": self.warnings,
            "details": self.details
        }
    
    @property
    def is_acceptable(self) -> bool:
        """
        Indique si la qualité OCR est acceptable.
        
        Returns:
            True si le score global est supérieur ou égal à 0.7 et le nombre d'erreurs est inférieur à 10
        """
        return self.overall_score >= 0.7 and self.error_count < 10

class OCRQualityEvaluator:
    """
    Système d'évaluation de la qualité OCR.
    
    Permet de comparer et d'évaluer les résultats de différentes méthodes OCR.
    
    Attributs:
        COMMON_WORDS (Dict[str, Set[str]]): Dictionnaires de mots courants par langue
        ERROR_PATTERNS (Dict[str, re.Pattern]): Expressions régulières pour détecter des erreurs courantes
    """
    
    # Dictionnaires de mots courants par langue pour vérification de cohérence linguistique
    COMMON_WORDS = {
        "fra": set(["le", "la", "les", "un", "une", "des", "et", "ou", "pour", "dans", 
                   "avec", "sur", "par", "qui", "que", "quoi", "comment", "est", "sont"]),
        "eng": set(["the", "a", "an", "and", "or", "for", "in", "with", "on", "by", 
                   "who", "what", "how", "is", "are", "was", "were"])
    }
    
    # Expressions régulières pour détecter des erreurs courantes
    ERROR_PATTERNS = {
        "garbage_chars": re.compile(r'[^\w\s.,;:!?()[\]{}"\'-]'),
        "repeated_chars": re.compile(r'(\w)\1{3,}'),
        "isolated_chars": re.compile(r'\b[a-zA-Z]\b'),
        "whitespace_errors": re.compile(r'\s{3,}')
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'évaluateur de qualité OCR.
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
    
    def evaluate_text(self, text: str, language: str = "fra") -> OCRQualityResult:
        """
        Évalue la qualité d'un texte extrait par OCR.
        
        Args:
            text: Texte à évaluer
            language: Code de langue du texte
            
        Returns:
            Résultat d'évaluation de qualité
        """
        result = OCRQualityResult(provider_name="unknown")
        
        if not text:
            result.overall_score = 0.0
            result.warnings.append("Texte vide")
            return result
        
        # Analyser le texte
        words = re.findall(r'\b\w+\b', text.lower())
        result.character_count = len(text)
        result.word_count = len(words)
        
        # Évaluer la cohérence linguistique
        if language in self.COMMON_WORDS:
            common_words = self.COMMON_WORDS[language]
            recognized_common_words = sum(1 for word in words if word in common_words)
            expected_common_words = min(len(common_words), result.word_count * 0.1)
            if expected_common_words > 0:
                language_ratio = recognized_common_words / expected_common_words
                result.language_score = min(1.0, language_ratio)
            else:
                result.language_score = 0.5  # Neutre si pas assez de texte
        else:
            result.language_score = 0.5  # Neutre si langue non supportée
        
        # Détecter les erreurs
        errors = []
        for error_type, pattern in self.ERROR_PATTERNS.items():
            matches = pattern.findall(text)
            errors.extend(matches)
        
        result.error_count = len(errors)
        
        # Calculer les scores
        # 1. Score de confiance basé sur la présence d'erreurs
        error_ratio = min(1.0, result.error_count / max(1, result.character_count / 100))
        result.confidence_score = 1.0 - error_ratio
        
        # 2. Score de formatage
        # Vérifier la présence de structure (paragraphes, sauts de ligne, etc.)
        has_paragraphs = text.count('\n\n') > 0
        has_lines = text.count('\n') > 0
        has_punctuation = sum(1 for c in text if c in '.,;:!?') > 0
        
        format_features = [has_paragraphs, has_lines, has_punctuation]
        result.formatting_score = sum(1 for f in format_features if f) / len(format_features)
        
        # 3. Score global
        result.overall_score = statistics.mean([
            result.confidence_score * 0.5,  # Confiance a plus de poids
            result.language_score * 0.3,
            result.formatting_score * 0.2
        ])
        
        # Ajouter des avertissements
        if result.error_count > 10:
            result.warnings.append(f"Nombre élevé d'erreurs potentielles: {result.error_count}")
        if result.language_score < 0.5:
            result.warnings.append(f"Faible cohérence linguistique pour la langue {language}")
        if result.formatting_score < 0.3:
            result.warnings.append("Formatage de texte minimal ou absent")
        
        return result
    
    def compare_results(self, reference_text: str, ocr_text: str) -> Tuple[float, Dict[str, Any]]:
        """
        Compare un texte OCR avec un texte de référence.
        
        Args:
            reference_text: Texte de référence
            ocr_text: Texte extrait par OCR
            
        Returns:
            Tuple (score de similarité, détails de comparaison)
        """
        if not reference_text or not ocr_text:
            return 0.0, {"error": "Un des textes est vide"}
        
        # Nettoyer les textes pour comparaison
        ref_clean = self._normalize_text(reference_text)
        ocr_clean = self._normalize_text(ocr_text)
        
        # Calculer la similarité avec difflib
        similarity = difflib.SequenceMatcher(None, ref_clean, ocr_clean).ratio()
        
        # Analyser les différences au niveau des mots
        ref_words = re.findall(r'\b\w+\b', ref_clean.lower())
        ocr_words = re.findall(r'\b\w+\b', ocr_clean.lower())
        
        # Calculer la précision au niveau des mots
        correct_words = sum(1 for w in ocr_words if w in ref_words)
        word_precision = correct_words / max(1, len(ocr_words))
        
        # Calculer le rappel au niveau des mots
        word_recall = correct_words / max(1, len(ref_words))
        
        # F1-score (moyenne harmonique de précision et rappel)
        f1_score = 0.0
        if word_precision + word_recall > 0:
            f1_score = 2 * (word_precision * word_recall) / (word_precision + word_recall)
        
        details = {
            "similarity": similarity,
            "word_precision": word_precision,
            "word_recall": word_recall,
            "f1_score": f1_score,
            "ref_word_count": len(ref_words),
            "ocr_word_count": len(ocr_words),
            "correct_word_count": correct_words
        }
        
        return similarity, details
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalise un texte pour la comparaison.
        
        Args:
            text: Texte à normaliser
            
        Returns:
            Texte normalisé
        """
        # Convertir en minuscules
        text = text.lower()
        
        # Supprimer les sauts de ligne et tabulations
        text = re.sub(r'[\n\r\t]+', ' ', text)
        
        # Supprimer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Supprimer la ponctuation
        text = re.sub(r'[^\w\s]', '', text)
        
        # Supprimer les espaces en début et fin
        text = text.strip()
        
        return text
    
    async def benchmark_providers(self, document_path: Union[str, Path], 
                             providers: List[str],
                             reference_text: Optional[str] = None) -> Dict[str, OCRQualityResult]:
        """
        Compare la qualité OCR entre différents providers.
        
        Args:
            document_path: Chemin vers le document
            providers: Liste des providers à comparer
            reference_text: Texte de référence optionnel
            
        Returns:
            Dictionnaire des résultats par provider
        """
        from .factory import get_ocr_processor
        
        results = {}
        document_path = Path(document_path)
        
        for provider_name in providers:
            try:
                # Obtenir le processeur
                processor = await get_ocr_processor(provider_name, fallback=False)
                
                # Mesurer le temps de traitement
                start_time = time.time()
                
                # Effectuer l'OCR
                ocr_result = await processor.process_document(document_path)
                
                if not ocr_result.success:
                    logger.warning(f"Échec OCR avec {provider_name}: {ocr_result.error_message}")
                    continue
                
                # Extraire le texte
                if ocr_result.text_content:
                    text = ocr_result.text_content
                else:
                    text = await processor.extract_text(ocr_result.output_path)
                
                processing_time = time.time() - start_time
                
                # Évaluer la qualité
                quality_result = self.evaluate_text(text)
                quality_result.provider_name = provider_name
                quality_result.processing_time = processing_time
                
                # Si un texte de référence est fourni, comparer les résultats
                if reference_text:
                    similarity, comparison_details = self.compare_results(reference_text, text)
                    quality_result.details["comparison"] = comparison_details
                    quality_result.details["similarity"] = similarity
                
                results[provider_name] = quality_result
                
            except Exception as e:
                logger.error(f"Erreur lors du benchmark du provider {provider_name}: {str(e)}")
        
        return results
    
    def get_recommended_provider(self, benchmark_results: Dict[str, OCRQualityResult],
                             prioritize_speed: bool = False) -> Optional[str]:
        """
        Détermine le provider OCR recommandé en fonction des résultats de benchmark.
        
        Args:
            benchmark_results: Résultats de benchmark
            prioritize_speed: Si True, donne plus de poids à la vitesse
            
        Returns:
            Nom du provider recommandé ou None si aucun résultat valide
        """
        if not benchmark_results:
            return None
        
        # Filtrer les résultats valides
        valid_results = {name: result for name, result in benchmark_results.items() 
                        if result.overall_score > 0}
        
        if not valid_results:
            return None
        
        if prioritize_speed:
            # Trier par score global puis par temps de traitement (le plus rapide)
            sorted_results = sorted(
                valid_results.items(),
                key=lambda x: (x[1].overall_score > 0.7, -x[1].processing_time if x[1].processing_time > 0 else float('inf')),
                reverse=True
            )
        else:
            # Trier uniquement par score global
            sorted_results = sorted(
                valid_results.items(),
                key=lambda x: x[1].overall_score,
                reverse=True
            )
        
        # Retourner le meilleur provider
        if sorted_results:
            return sorted_results[0][0]
        
        return None
