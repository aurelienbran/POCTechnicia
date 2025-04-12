"""
Module de détection des extractions à faible confiance
=====================================================

Ce module fournit des outils pour identifier les documents et extractions qui présentent
une faible confiance ou des problèmes potentiels, et pour les soumettre à un système
de retraitement et d'amélioration itérative.

Caractéristiques principales:
- Détection des résultats OCR de faible qualité
- Identification des portions de texte problématiques
- Métriques spécifiques pour différents types de contenus (formules, schémas, tableaux)
- Gestion des seuils de confiance adaptés au type de document

Utilisation typique:
```python
# Analyse d'un résultat de traitement pour détecter les parties de basse confiance
detector = LowConfidenceDetector()
issues = await detector.analyze_document(document_path, processing_result)
if issues.requires_reprocessing:
    reprocessing_job = await reprocessing_workflow.create_job(issues)
```

Auteur: Équipe Technicia
Date: Avril 2025
"""

import logging
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, field
import asyncio

from ..ocr.quality_metrics import OCRQualityResult, OCRQualityEvaluator
from ...utils.config import get_config
from ...storage.document_store import DocumentStore
from ..specialized_processors.formula_processor import FormulaProcessor
from ..specialized_processors.schema_analyzer import SchemaAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class ContentIssue:
    """
    Problème détecté dans un contenu traité.
    
    Attributs:
        issue_type: Type de problème ('ocr_quality', 'formula_detection', 'schema_recognition', etc.)
        content_type: Type de contenu concerné ('text', 'formula', 'schema', 'table', etc.)
        page_number: Numéro de page (optionnel)
        region: Coordonnées de la région concernée (optionnel)
        confidence: Score de confiance (0.0 à 1.0)
        description: Description du problème
        content_sample: Échantillon du contenu problématique
        metadata: Métadonnées supplémentaires
        suggested_actions: Actions suggérées pour résoudre le problème
    """
    issue_type: str
    content_type: str
    page_number: Optional[int] = None
    region: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    description: str = ""
    content_sample: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)
    
    @property
    def is_critical(self) -> bool:
        """
        Indique si le problème est critique.
        
        Returns:
            True si le problème est critique (confidence < 0.4)
        """
        return self.confidence < 0.4
    
    @property
    def is_severe(self) -> bool:
        """
        Indique si le problème est sévère.
        
        Returns:
            True si le problème est sévère (confidence < 0.6)
        """
        return self.confidence < 0.6
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le problème en dictionnaire.
        
        Returns:
            Dictionnaire représentant le problème
        """
        return {
            "issue_type": self.issue_type,
            "content_type": self.content_type,
            "page_number": self.page_number,
            "region": self.region,
            "confidence": self.confidence,
            "description": self.description,
            "content_sample": self.content_sample,
            "metadata": self.metadata,
            "suggested_actions": self.suggested_actions,
            "is_critical": self.is_critical,
            "is_severe": self.is_severe
        }

@dataclass
class DocumentValidationIssues:
    """
    Ensemble des problèmes détectés pour un document.
    
    Attributs:
        document_id: Identifiant du document
        document_path: Chemin du document
        issues: Liste des problèmes détectés
        global_confidence: Score de confiance global pour le document
        validation_timestamp: Horodatage de la validation
        metadata: Métadonnées supplémentaires
    """
    document_id: str
    document_path: str
    issues: List[ContentIssue] = field(default_factory=list)
    global_confidence: float = 0.0
    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_critical_issues(self) -> bool:
        """
        Indique si le document a des problèmes critiques.
        
        Returns:
            True si au moins un problème critique est détecté
        """
        return any(issue.is_critical for issue in self.issues)
    
    @property
    def has_severe_issues(self) -> bool:
        """
        Indique si le document a des problèmes sévères.
        
        Returns:
            True si au moins un problème sévère est détecté
        """
        return any(issue.is_severe for issue in self.issues)
    
    @property
    def requires_reprocessing(self) -> bool:
        """
        Indique si le document nécessite un retraitement.
        
        Returns:
            True si le document nécessite un retraitement (problèmes critiques ou sévères)
        """
        # Retraitement si problèmes critiques ou nombreux problèmes sévères
        critical_issues = sum(1 for issue in self.issues if issue.is_critical)
        severe_issues = sum(1 for issue in self.issues if issue.is_severe and not issue.is_critical)
        
        return critical_issues > 0 or severe_issues >= 3 or self.global_confidence < 0.5
    
    @property
    def requires_manual_validation(self) -> bool:
        """
        Indique si le document nécessite une validation manuelle.
        
        Returns:
            True si le document nécessite une validation manuelle
        """
        # La validation manuelle est requise dans certains cas spécifiques
        critical_formula_issues = any(issue.is_critical and issue.content_type == "formula" 
                                     for issue in self.issues)
        critical_schema_issues = any(issue.is_critical and issue.content_type == "schema" 
                                    for issue in self.issues)
        
        # Validation manuelle pour les problèmes critiques spécifiques ou si la confiance globale est très basse
        return critical_formula_issues or critical_schema_issues or self.global_confidence < 0.3
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'ensemble des problèmes en dictionnaire.
        
        Returns:
            Dictionnaire représentant l'ensemble des problèmes
        """
        return {
            "document_id": self.document_id,
            "document_path": self.document_path,
            "issues": [issue.to_dict() for issue in self.issues],
            "global_confidence": self.global_confidence,
            "validation_timestamp": self.validation_timestamp,
            "metadata": self.metadata,
            "has_critical_issues": self.has_critical_issues,
            "has_severe_issues": self.has_severe_issues,
            "requires_reprocessing": self.requires_reprocessing,
            "requires_manual_validation": self.requires_manual_validation
        }

class LowConfidenceDetector:
    """
    Détecteur de contenus à faible confiance.
    
    Cette classe permet d'analyser les résultats de traitement de documents pour
    identifier les portions qui présentent une faible confiance ou des problèmes
    potentiels, et les soumettre à un système de retraitement si nécessaire.
    """
    
    # Seuils de confiance par type de contenu
    DEFAULT_THRESHOLDS = {
        "text": {
            "acceptable": 0.7,
            "warning": 0.5,
            "critical": 0.3
        },
        "formula": {
            "acceptable": 0.75,
            "warning": 0.6,
            "critical": 0.4
        },
        "schema": {
            "acceptable": 0.65,
            "warning": 0.5,
            "critical": 0.35
        },
        "table": {
            "acceptable": 0.7,
            "warning": 0.55,
            "critical": 0.4
        }
    }
    
    # Expressions régulières pour détecter des patterns problématiques spécifiques
    PROBLEM_PATTERNS = {
        "suspect_characters": re.compile(r'[^\x00-\x7F\u00C0-\u00FF]{3,}'),  # Suite de caractères non latins
        "character_salad": re.compile(r'[^\s\w.,;:!?()[\]{}"\'-]{4,}'),  # Suite de caractères spéciaux
        "repeated_punctuation": re.compile(r'[.,;:!?]{3,}')  # Ponctuation répétée
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le détecteur de basse confiance.
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or get_config().get("validation", {})
        self.thresholds = self.config.get("thresholds", self.DEFAULT_THRESHOLDS)
        self.evaluator = OCRQualityEvaluator()
        self.document_store = DocumentStore()
        
        # Initialiser les détecteurs spécialisés si nécessaire
        self.formula_processor = None
        self.schema_analyzer = None
    
    async def initialize(self) -> bool:
        """
        Initialise les détecteurs spécialisés.
        
        Returns:
            True si l'initialisation a réussi
        """
        try:
            # Initialiser les processeurs spécialisés pour la validation
            self.formula_processor = FormulaProcessor()
            await self.formula_processor.initialize()
            
            self.schema_analyzer = SchemaAnalyzer()
            await self.schema_analyzer.initialize()
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des détecteurs spécialisés: {str(e)}")
            return False
    
    async def analyze_document(self, document_path: Union[str, Path], 
                              processing_result: Dict[str, Any]) -> DocumentValidationIssues:
        """
        Analyse un document pour détecter les problèmes potentiels.
        
        Args:
            document_path: Chemin du document
            processing_result: Résultat du traitement du document
            
        Returns:
            Ensemble des problèmes détectés
        """
        document_path = Path(document_path) if isinstance(document_path, str) else document_path
        document_id = processing_result.get("document_id", str(document_path))
        
        # Créer l'objet de résultat
        validation_issues = DocumentValidationIssues(
            document_id=document_id,
            document_path=str(document_path)
        )
        
        try:
            # 1. Vérifier la qualité OCR globale
            if "text_content" in processing_result:
                ocr_quality = self.evaluator.evaluate_text(
                    processing_result["text_content"],
                    language=processing_result.get("language", "fra")
                )
                
                validation_issues.global_confidence = ocr_quality.overall_score
                
                # Ajouter des problèmes si la qualité est insuffisante
                if ocr_quality.overall_score < self.thresholds["text"]["acceptable"]:
                    # Créer un problème global pour la qualité OCR
                    issue = ContentIssue(
                        issue_type="global_ocr_quality",
                        content_type="text",
                        confidence=ocr_quality.overall_score,
                        description=f"Qualité OCR globale insuffisante (score: {ocr_quality.overall_score:.2f})"
                    )
                    
                    # Ajouter les avertissements de l'évaluation
                    if ocr_quality.warnings:
                        issue.description += f" - {', '.join(ocr_quality.warnings)}"
                    
                    # Ajouter des actions suggérées
                    if ocr_quality.overall_score < self.thresholds["text"]["critical"]:
                        issue.suggested_actions = [
                            "Relancer l'OCR avec un autre moteur",
                            "Augmenter la résolution lors de la numérisation",
                            "Vérifier manuellement le document"
                        ]
                    elif ocr_quality.overall_score < self.thresholds["text"]["warning"]:
                        issue.suggested_actions = [
                            "Relancer l'OCR avec des paramètres optimisés",
                            "Appliquer des prétraitements d'image"
                        ]
                    
                    validation_issues.issues.append(issue)
            
            # 2. Analyser par page et par région (si disponible)
            if "pages" in processing_result:
                for page_idx, page_data in enumerate(processing_result["pages"]):
                    page_number = page_idx + 1
                    
                    # Vérifier la qualité OCR par page
                    if "text_content" in page_data:
                        page_quality = self.evaluator.evaluate_text(
                            page_data["text_content"],
                            language=processing_result.get("language", "fra")
                        )
                        
                        if page_quality.overall_score < self.thresholds["text"]["warning"]:
                            # Créer un problème pour cette page
                            issue = ContentIssue(
                                issue_type="page_ocr_quality",
                                content_type="text",
                                page_number=page_number,
                                confidence=page_quality.overall_score,
                                description=f"Qualité OCR insuffisante pour la page {page_number} (score: {page_quality.overall_score:.2f})"
                            )
                            
                            # Ajouter un échantillon du contenu problématique
                            if page_data["text_content"]:
                                sample = page_data["text_content"][:200] + "..." if len(page_data["text_content"]) > 200 else page_data["text_content"]
                                issue.content_sample = sample
                            
                            validation_issues.issues.append(issue)
                    
                    # Vérifier les formules détectées
                    if "formulas" in page_data:
                        await self._check_formulas(page_data["formulas"], page_number, validation_issues)
                    
                    # Vérifier les schémas détectés
                    if "schemas" in page_data:
                        await self._check_schemas(page_data["schemas"], page_number, validation_issues)
                    
                    # Vérifier les tableaux détectés
                    if "tables" in page_data:
                        self._check_tables(page_data["tables"], page_number, validation_issues)
            
            # 3. Vérifier les patterns problématiques dans le texte complet
            if "text_content" in processing_result:
                self._check_problem_patterns(
                    processing_result["text_content"],
                    None,
                    validation_issues
                )
            
            # 4. Agréger les métriques et calculer la confiance globale finale
            if validation_issues.issues:
                # Ajuster la confiance globale en fonction du nombre et de la gravité des problèmes
                critical_count = sum(1 for issue in validation_issues.issues if issue.is_critical)
                severe_count = sum(1 for issue in validation_issues.issues if issue.is_severe and not issue.is_critical)
                
                # Diminuer la confiance globale proportionnellement au nombre de problèmes
                confidence_penalty = min(0.5, (critical_count * 0.1 + severe_count * 0.05))
                validation_issues.global_confidence = max(0.1, validation_issues.global_confidence - confidence_penalty)
            
            # 5. Ajouter des métadonnées supplémentaires
            validation_issues.metadata["document_type"] = processing_result.get("document_type", "unknown")
            validation_issues.metadata["page_count"] = processing_result.get("page_count", 0)
            validation_issues.metadata["processors_used"] = processing_result.get("processors_used", [])
            
            return validation_issues
        
        except Exception as e:
            logger.exception(f"Erreur lors de l'analyse du document {document_id}: {str(e)}")
            
            # Créer un problème pour l'erreur d'analyse
            error_issue = ContentIssue(
                issue_type="validation_error",
                content_type="document",
                confidence=0.0,
                description=f"Erreur lors de l'analyse du document: {str(e)}"
            )
            validation_issues.issues.append(error_issue)
            validation_issues.global_confidence = 0.0
            
            return validation_issues
    
    async def _check_formulas(self, formulas: List[Dict[str, Any]], page_number: int, 
                             issues: DocumentValidationIssues) -> None:
        """
        Vérifie la qualité des formules détectées.
        
        Args:
            formulas: Liste des formules détectées
            page_number: Numéro de page
            issues: Objet de résultat à mettre à jour
        """
        if not formulas:
            return
        
        if not self.formula_processor:
            if not await self.initialize():
                # Ne pas bloquer la validation si l'initialisation échoue
                return
        
        for idx, formula in enumerate(formulas):
            confidence = formula.get("confidence", 0.0)
            formula_text = formula.get("formula_text", "")
            
            # Vérifier si la confiance est sous le seuil
            if confidence < self.thresholds["formula"]["acceptable"]:
                issue = ContentIssue(
                    issue_type="formula_quality",
                    content_type="formula",
                    page_number=page_number,
                    region=formula.get("region"),
                    confidence=confidence,
                    description=f"Formule avec confiance insuffisante (score: {confidence:.2f})"
                )
                
                # Ajouter un échantillon de la formule
                issue.content_sample = formula_text
                
                # Ajouter des métadonnées spécifiques
                issue.metadata["formula_type"] = formula.get("formula_type", "unknown")
                issue.metadata["formula_complexity"] = formula.get("complexity", 0)
                
                # Suggérer des actions en fonction de la confiance
                if confidence < self.thresholds["formula"]["critical"]:
                    issue.suggested_actions = [
                        "Utiliser un processeur spécialisé pour formules mathématiques",
                        "Améliorer la résolution de l'image source",
                        "Vérifier manuellement la formule"
                    ]
                elif confidence < self.thresholds["formula"]["warning"]:
                    issue.suggested_actions = [
                        "Réanalyser avec des paramètres optimisés pour les formules",
                        "Essayer un autre algorithme de détection"
                    ]
                
                issues.issues.append(issue)
    
    async def _check_schemas(self, schemas: List[Dict[str, Any]], page_number: int, 
                            issues: DocumentValidationIssues) -> None:
        """
        Vérifie la qualité des schémas détectés.
        
        Args:
            schemas: Liste des schémas détectés
            page_number: Numéro de page
            issues: Objet de résultat à mettre à jour
        """
        if not schemas:
            return
        
        if not self.schema_analyzer:
            if not await self.initialize():
                # Ne pas bloquer la validation si l'initialisation échoue
                return
        
        for idx, schema in enumerate(schemas):
            confidence = schema.get("confidence", 0.0)
            
            # Vérifier si la confiance est sous le seuil
            if confidence < self.thresholds["schema"]["acceptable"]:
                issue = ContentIssue(
                    issue_type="schema_quality",
                    content_type="schema",
                    page_number=page_number,
                    region=schema.get("region"),
                    confidence=confidence,
                    description=f"Schéma avec confiance insuffisante (score: {confidence:.2f})"
                )
                
                # Ajouter un échantillon de description du schéma
                if "description" in schema:
                    issue.content_sample = schema["description"][:200] + "..." if len(schema["description"]) > 200 else schema["description"]
                
                # Ajouter des métadonnées spécifiques
                issue.metadata["schema_type"] = schema.get("schema_type", "unknown")
                issue.metadata["component_count"] = len(schema.get("components", []))
                issue.metadata["text_annotation_count"] = len(schema.get("text_annotations", []))
                
                # Suggérer des actions en fonction de la confiance
                if confidence < self.thresholds["schema"]["critical"]:
                    issue.suggested_actions = [
                        "Utiliser un processeur spécialisé pour analyse de schémas",
                        "Améliorer la résolution de l'image source",
                        "Vérifier manuellement le schéma"
                    ]
                elif confidence < self.thresholds["schema"]["warning"]:
                    issue.suggested_actions = [
                        "Réanalyser avec des paramètres optimisés pour les schémas",
                        "Essayer un autre algorithme de détection"
                    ]
                
                issues.issues.append(issue)
    
    def _check_tables(self, tables: List[Dict[str, Any]], page_number: int, 
                     issues: DocumentValidationIssues) -> None:
        """
        Vérifie la qualité des tableaux détectés.
        
        Args:
            tables: Liste des tableaux détectés
            page_number: Numéro de page
            issues: Objet de résultat à mettre à jour
        """
        if not tables:
            return
        
        for idx, table in enumerate(tables):
            confidence = table.get("confidence", 0.0)
            
            # Vérifier si la confiance est sous le seuil
            if confidence < self.thresholds["table"]["acceptable"]:
                issue = ContentIssue(
                    issue_type="table_quality",
                    content_type="table",
                    page_number=page_number,
                    region=table.get("region"),
                    confidence=confidence,
                    description=f"Tableau avec confiance insuffisante (score: {confidence:.2f})"
                )
                
                # Ajouter des métadonnées spécifiques
                issue.metadata["row_count"] = table.get("rows", 0)
                issue.metadata["column_count"] = table.get("columns", 0)
                issue.metadata["cell_count"] = table.get("rows", 0) * table.get("columns", 0)
                
                # Vérifier les cellules vides ou avec peu de contenu
                cells = table.get("cells", [])
                empty_cells = sum(1 for cell in cells if not cell.get("text", "").strip())
                if cells:
                    empty_ratio = empty_cells / len(cells)
                    if empty_ratio > 0.3:
                        issue.description += f" - {empty_ratio:.0%} de cellules vides ou non détectées"
                
                # Suggérer des actions en fonction de la confiance
                if confidence < self.thresholds["table"]["critical"]:
                    issue.suggested_actions = [
                        "Utiliser un processeur spécialisé pour tableaux",
                        "Améliorer la résolution de l'image source",
                        "Extraire le tableau manuellement"
                    ]
                elif confidence < self.thresholds["table"]["warning"]:
                    issue.suggested_actions = [
                        "Réanalyser avec des paramètres optimisés pour les tableaux",
                        "Vérifier manuellement l'extraction du tableau"
                    ]
                
                issues.issues.append(issue)
    
    def _check_problem_patterns(self, text: str, page_number: Optional[int], 
                               issues: DocumentValidationIssues) -> None:
        """
        Vérifie si le texte contient des patterns problématiques.
        
        Args:
            text: Texte à vérifier
            page_number: Numéro de page
            issues: Objet de résultat à mettre à jour
        """
        if not text:
            return
        
        # Vérifier chaque pattern problématique
        for pattern_name, pattern in self.PROBLEM_PATTERNS.items():
            matches = list(pattern.finditer(text))
            
            if matches:
                for match in matches[:5]:  # Limiter le nombre de problèmes signalés
                    start, end = match.span()
                    context_start = max(0, start - 20)
                    context_end = min(len(text), end + 20)
                    
                    issue = ContentIssue(
                        issue_type="text_pattern_issue",
                        content_type="text",
                        page_number=page_number,
                        confidence=0.4,  # Confiance fixe pour les problèmes de pattern
                        description=f"Problème de texte détecté: {pattern_name}"
                    )
                    
                    # Ajouter le contexte autour du problème
                    context = text[context_start:start] + "[" + text[start:end] + "]" + text[end:context_end]
                    issue.content_sample = context
                    
                    # Suggérer des actions
                    issue.suggested_actions = [
                        "Vérifier manuellement cette portion de texte",
                        "Relancer l'OCR avec un moteur différent"
                    ]
                    
                    issues.issues.append(issue)
        
        # Vérifier également des heuristiques supplémentaires
        self._check_text_heuristics(text, page_number, issues)
    
    def _check_text_heuristics(self, text: str, page_number: Optional[int], 
                              issues: DocumentValidationIssues) -> None:
        """
        Applique des heuristiques supplémentaires pour détecter des problèmes de texte.
        
        Args:
            text: Texte à vérifier
            page_number: Numéro de page
            issues: Objet de résultat à mettre à jour
        """
        if not text:
            return
        
        # 1. Vérifier le ratio de caractères non alphanumériques
        total_chars = len(text)
        if total_chars > 0:
            non_alnum = sum(1 for c in text if not (c.isalnum() or c.isspace()))
            non_alnum_ratio = non_alnum / total_chars
            
            if non_alnum_ratio > 0.3:
                issue = ContentIssue(
                    issue_type="high_non_alnum_ratio",
                    content_type="text",
                    page_number=page_number,
                    confidence=0.5,
                    description=f"Ratio élevé de caractères non alphanumériques: {non_alnum_ratio:.0%}"
                )
                
                # Ajouter un échantillon
                sample = text[:200] + "..." if len(text) > 200 else text
                issue.content_sample = sample
                
                issues.issues.append(issue)
        
        # 2. Vérifier le nombre moyen de caractères par mot (détection de mots mal séparés)
        words = [w for w in text.split() if w.strip()]
        if words:
            avg_word_length = sum(len(w) for w in words) / len(words)
            
            if avg_word_length > 12:
                issue = ContentIssue(
                    issue_type="words_too_long",
                    content_type="text",
                    page_number=page_number,
                    confidence=0.5,
                    description=f"Longueur moyenne des mots anormalement élevée: {avg_word_length:.1f} caractères"
                )
                
                # Ajouter quelques exemples de mots longs
                long_words = [w for w in words if len(w) > 15][:5]
                if long_words:
                    issue.content_sample = "Exemples: " + ", ".join(long_words)
                
                issues.issues.append(issue)
