"""
Module de validation par échantillonnage
=====================================================

Ce module implémente un système de validation par échantillonnage pour évaluer
la qualité globale du traitement des documents et identifier les tendances
et problèmes récurrents dans les résultats d'OCR.

Caractéristiques principales:
- Sélection aléatoire de documents pour validation
- Stratégies d'échantillonnage adaptatif basées sur le niveau de confiance
- Métriques agrégées pour évaluer les performances globales du système
- Détection des tendances et problèmes récurrents
- Recommandations pour l'amélioration du système

Utilisation typique:
```python
# Initialiser le validateur
validator = SamplingValidator()
# Créer un échantillon de validation
sample = await validator.create_validation_sample(50)  # 50 documents
# Obtenir les résultats de validation
validation_results = await validator.analyze_sample(sample)
# Générer un rapport
report = await validator.generate_quality_report(validation_results)
```

Auteur: Équipe Technicia
Date: Avril 2025
"""

import logging
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, field
import uuid
import asyncio
import json
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter

from .low_confidence_detector import LowConfidenceDetector, DocumentValidationIssues
from ...storage.document_store import DocumentStore
from ..ocr.quality_metrics import OCRQualityEvaluator
from ...utils.config import get_config

logger = logging.getLogger(__name__)

@dataclass
class ValidationSample:
    """
    Échantillon de documents sélectionnés pour validation.
    
    Attributs:
        sample_id: Identifiant unique de l'échantillon
        documents: Liste des documents sélectionnés
        created_at: Date de création
        size: Taille de l'échantillon
        sampling_criteria: Critères utilisés pour la sélection
        metadata: Métadonnées supplémentaires
    """
    sample_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    documents: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    size: int = 0
    sampling_criteria: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'échantillon en dictionnaire.
        
        Returns:
            Dictionnaire représentant l'échantillon
        """
        return {
            "sample_id": self.sample_id,
            "created_at": self.created_at,
            "size": self.size,
            "documents": self.documents,
            "sampling_criteria": self.sampling_criteria,
            "metadata": self.metadata
        }

@dataclass
class ValidationResult:
    """
    Résultat de la validation d'un échantillon.
    
    Attributs:
        validation_id: Identifiant unique de la validation
        sample_id: Identifiant de l'échantillon validé
        document_results: Résultats par document
        global_metrics: Métriques globales
        completed_at: Date de complétion
        status: Statut de la validation
        detected_patterns: Patterns détectés dans les problèmes
    """
    validation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sample_id: str = ""
    document_results: Dict[str, DocumentValidationIssues] = field(default_factory=dict)
    global_metrics: Dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[str] = None
    status: str = "in_progress"
    detected_patterns: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_completed(self) -> bool:
        """
        Indique si la validation est complétée.
        
        Returns:
            True si la validation est complétée
        """
        return self.status == "completed"
    
    @property
    def document_count(self) -> int:
        """
        Retourne le nombre de documents validés.
        
        Returns:
            Nombre de documents validés
        """
        return len(self.document_results)
    
    @property
    def average_confidence(self) -> float:
        """
        Calcule la confiance moyenne pour l'ensemble des documents.
        
        Returns:
            Confiance moyenne
        """
        if not self.document_results:
            return 0.0
        
        confidences = [doc.global_confidence for doc in self.document_results.values()]
        return sum(confidences) / len(confidences)
    
    @property
    def critical_issue_count(self) -> int:
        """
        Compte le nombre total de problèmes critiques.
        
        Returns:
            Nombre de problèmes critiques
        """
        return sum(doc.has_critical_issues for doc in self.document_results.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le résultat de validation en dictionnaire.
        
        Returns:
            Dictionnaire représentant le résultat de validation
        """
        return {
            "validation_id": self.validation_id,
            "sample_id": self.sample_id,
            "document_results": {doc_id: res.to_dict() for doc_id, res in self.document_results.items()},
            "global_metrics": self.global_metrics,
            "completed_at": self.completed_at,
            "status": self.status,
            "detected_patterns": self.detected_patterns,
            "is_completed": self.is_completed,
            "document_count": self.document_count,
            "average_confidence": self.average_confidence,
            "critical_issue_count": self.critical_issue_count
        }

class SamplingValidator:
    """
    Validateur par échantillonnage pour évaluer la qualité du traitement des documents.
    
    Cette classe permet de sélectionner des échantillons de documents, de les analyser
    pour détecter les problèmes de qualité, et de générer des rapports agrégés pour
    évaluer les performances globales du système et identifier les tendances et problèmes
    récurrents.
    """
    
    # Stratégies d'échantillonnage
    SAMPLING_STRATEGIES = {
        "random": "Sélection aléatoire",
        "stratified": "Échantillonnage stratifié par type de document",
        "recent": "Documents récemment traités",
        "low_confidence": "Documents à faible confiance",
        "high_confidence": "Documents à confiance élevée",
        "critical_issues": "Documents avec problèmes critiques"
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le validateur par échantillonnage.
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or get_config().get("validation", {})
        self.document_store = DocumentStore()
        self.detector = LowConfidenceDetector()
        
        # Configuration
        self.default_sample_size = self.config.get("default_sample_size", 50)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        
        # Cache des validations
        self.validation_results: Dict[str, ValidationResult] = {}
        self.samples: Dict[str, ValidationSample] = {}
    
    async def create_validation_sample(self, size: int = None, 
                                     strategy: str = "random", 
                                     criteria: Dict[str, Any] = None) -> ValidationSample:
        """
        Crée un échantillon de documents pour validation.
        
        Args:
            size: Taille de l'échantillon
            strategy: Stratégie d'échantillonnage
            criteria: Critères supplémentaires pour la sélection
            
        Returns:
            Échantillon de validation
        """
        size = size or self.default_sample_size
        criteria = criteria or {}
        
        # Créer l'échantillon
        sample = ValidationSample(
            size=size,
            sampling_criteria={
                "strategy": strategy,
                "criteria": criteria
            }
        )
        
        # Récupérer les documents en fonction de la stratégie
        if strategy == "random":
            # Échantillonnage aléatoire
            all_documents = await self.document_store.list_documents(
                limit=1000,  # Limiter pour des raisons de performance
                include_metadata=True
            )
            
            if len(all_documents) > size:
                selected = random.sample(all_documents, size)
            else:
                selected = all_documents
        
        elif strategy == "recent":
            # Documents récemment traités
            days = criteria.get("days", 7)
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            selected = await self.document_store.list_documents(
                limit=size,
                filter_criteria={"processed_date": {"$gte": since_date}},
                sort_by="processed_date",
                sort_order="desc",
                include_metadata=True
            )
        
        elif strategy == "stratified":
            # Échantillonnage stratifié par type de document
            doc_types = criteria.get("document_types", [])
            selected = []
            
            # Répartir la taille sur les différents types
            if doc_types:
                per_type = max(1, size // len(doc_types))
                
                for doc_type in doc_types:
                    type_docs = await self.document_store.list_documents(
                        limit=per_type,
                        filter_criteria={"document_type": doc_type},
                        include_metadata=True
                    )
                    selected.extend(type_docs)
                
                # Compléter si nécessaire
                if len(selected) < size:
                    remaining = size - len(selected)
                    other_docs = await self.document_store.list_documents(
                        limit=remaining,
                        filter_criteria={"document_type": {"$nin": doc_types}},
                        include_metadata=True
                    )
                    selected.extend(other_docs)
            else:
                # Si aucun type spécifié, utiliser l'échantillonnage aléatoire
                return await self.create_validation_sample(size, "random")
        
        elif strategy in ["low_confidence", "high_confidence"]:
            # Documents par niveau de confiance
            threshold = criteria.get("threshold", self.confidence_threshold)
            
            operator = "$lt" if strategy == "low_confidence" else "$gte"
            filter_criteria = {f"quality_metrics.confidence": {operator: threshold}}
            
            selected = await self.document_store.list_documents(
                limit=size,
                filter_criteria=filter_criteria,
                include_metadata=True
            )
        
        elif strategy == "critical_issues":
            # Documents avec problèmes critiques
            selected = await self.document_store.list_documents(
                limit=size,
                filter_criteria={"quality_metrics.has_critical_issues": True},
                include_metadata=True
            )
        
        else:
            # Stratégie inconnue, utiliser l'échantillonnage aléatoire
            logger.warning(f"Stratégie d'échantillonnage inconnue: {strategy}, utilisation de la stratégie aléatoire")
            return await self.create_validation_sample(size, "random")
        
        # Stocker les documents sélectionnés dans l'échantillon
        sample.documents = selected
        sample.size = len(selected)
        
        # Ajouter des métadonnées
        sample.metadata["document_types"] = Counter([doc.get("document_type", "unknown") for doc in selected])
        sample.metadata["creation_timestamp"] = datetime.now().isoformat()
        
        # Stocker l'échantillon
        self.samples[sample.sample_id] = sample
        
        return sample
    
    async def analyze_sample(self, sample: Union[ValidationSample, str]) -> ValidationResult:
        """
        Analyse un échantillon de documents pour valider leur qualité.
        
        Args:
            sample: Échantillon de validation ou son identifiant
            
        Returns:
            Résultat de validation
        """
        # Récupérer l'échantillon si nécessaire
        if isinstance(sample, str):
            if sample not in self.samples:
                logger.error(f"Échantillon inconnu: {sample}")
                return None
            sample = self.samples[sample]
        
        # Créer le résultat de validation
        validation = ValidationResult(
            sample_id=sample.sample_id
        )
        
        # Initialiser le détecteur
        await self.detector.initialize()
        
        # Analyser chaque document de l'échantillon
        for document in sample.documents:
            document_id = document.get("document_id", "")
            document_path = document.get("file_path", "")
            
            if not document_id or not document_path:
                logger.warning(f"Informations manquantes pour le document: {document}")
                continue
            
            try:
                # Récupérer les résultats de traitement
                processing_result = await self.document_store.get_processing_result(document_id)
                
                if not processing_result:
                    logger.warning(f"Résultats de traitement non trouvés pour le document: {document_id}")
                    continue
                
                # Analyser le document
                issues = await self.detector.analyze_document(document_path, processing_result)
                
                # Stocker les résultats
                validation.document_results[document_id] = issues
            
            except Exception as e:
                logger.exception(f"Erreur lors de l'analyse du document {document_id}: {str(e)}")
        
        # Calculer les métriques globales
        await self._compute_global_metrics(validation)
        
        # Détecter les patterns récurrents
        await self._detect_patterns(validation)
        
        # Finaliser la validation
        validation.completed_at = datetime.now().isoformat()
        validation.status = "completed"
        
        # Stocker la validation
        self.validation_results[validation.validation_id] = validation
        
        return validation
    
    async def _compute_global_metrics(self, validation: ValidationResult) -> None:
        """
        Calcule les métriques globales pour la validation.
        
        Args:
            validation: Résultat de validation à mettre à jour
        """
        if not validation.document_results:
            return
        
        # Calculer les métriques de base
        confidence_scores = [res.global_confidence for res in validation.document_results.values()]
        issue_counts = [len(res.issues) for res in validation.document_results.values()]
        critical_counts = [sum(1 for issue in res.issues if issue.is_critical) 
                          for res in validation.document_results.values()]
        severe_counts = [sum(1 for issue in res.issues if issue.is_severe) 
                        for res in validation.document_results.values()]
        
        # Documents nécessitant un retraitement
        reprocessing_needed = sum(1 for res in validation.document_results.values() 
                                 if res.requires_reprocessing)
        
        # Documents nécessitant une validation manuelle
        manual_validation_needed = sum(1 for res in validation.document_results.values() 
                                      if res.requires_manual_validation)
        
        # Stocker les métriques globales
        validation.global_metrics = {
            "document_count": len(validation.document_results),
            "confidence": {
                "mean": statistics.mean(confidence_scores) if confidence_scores else 0,
                "median": statistics.median(confidence_scores) if confidence_scores else 0,
                "min": min(confidence_scores) if confidence_scores else 0,
                "max": max(confidence_scores) if confidence_scores else 0,
                "std_dev": statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0
            },
            "issues": {
                "total": sum(issue_counts),
                "mean_per_document": statistics.mean(issue_counts) if issue_counts else 0,
                "critical": sum(critical_counts),
                "severe": sum(severe_counts)
            },
            "quality_distribution": {
                "excellent": sum(1 for score in confidence_scores if score >= 0.9),
                "good": sum(1 for score in confidence_scores if 0.8 <= score < 0.9),
                "acceptable": sum(1 for score in confidence_scores if 0.7 <= score < 0.8),
                "poor": sum(1 for score in confidence_scores if 0.5 <= score < 0.7),
                "very_poor": sum(1 for score in confidence_scores if score < 0.5)
            },
            "workflow": {
                "reprocessing_needed": reprocessing_needed,
                "reprocessing_rate": reprocessing_needed / len(validation.document_results) if validation.document_results else 0,
                "manual_validation_needed": manual_validation_needed,
                "manual_validation_rate": manual_validation_needed / len(validation.document_results) if validation.document_results else 0
            }
        }
    
    async def _detect_patterns(self, validation: ValidationResult) -> None:
        """
        Détecte les patterns récurrents dans les problèmes détectés.
        
        Args:
            validation: Résultat de validation à mettre à jour
        """
        if not validation.document_results:
            return
        
        # Agréger les problèmes par type
        issue_types = {}
        content_types = {}
        issue_descriptions = []
        
        for doc_id, result in validation.document_results.items():
            for issue in result.issues:
                # Compter par type de problème
                if issue.issue_type not in issue_types:
                    issue_types[issue.issue_type] = 0
                issue_types[issue.issue_type] += 1
                
                # Compter par type de contenu
                if issue.content_type not in content_types:
                    content_types[issue.content_type] = 0
                content_types[issue.content_type] += 1
                
                # Collecter les descriptions pour analyse
                issue_descriptions.append(issue.description)
        
        # Analyser les descriptions pour trouver des motifs communs
        common_terms = self._extract_common_terms(issue_descriptions)
        
        # Stocker les patterns détectés
        validation.detected_patterns = {
            "issue_types": issue_types,
            "content_types": content_types,
            "common_terms": common_terms,
            "recommendations": await self._generate_recommendations(validation)
        }
    
    def _extract_common_terms(self, descriptions: List[str], min_occurrences: int = 3) -> Dict[str, int]:
        """
        Extrait les termes communs dans les descriptions de problèmes.
        
        Args:
            descriptions: Liste des descriptions de problèmes
            min_occurrences: Nombre minimal d'occurrences pour considérer un terme
            
        Returns:
            Dictionnaire des termes communs et leur fréquence
        """
        if not descriptions:
            return {}
        
        # Liste de mots à ignorer (stop words)
        stop_words = {"le", "la", "les", "du", "de", "des", "un", "une", "et", "pour", "avec", "par"}
        
        # Extraire les mots de toutes les descriptions
        all_words = []
        for desc in descriptions:
            # Normaliser et tokenizer
            words = desc.lower().split()
            # Filtrer les mots courts et les stop words
            words = [w for w in words if len(w) > 3 and w not in stop_words]
            all_words.extend(words)
        
        # Compter les occurrences
        word_counts = Counter(all_words)
        
        # Filtrer les termes fréquents
        common_terms = {word: count for word, count in word_counts.items() 
                      if count >= min_occurrences}
        
        return dict(sorted(common_terms.items(), key=lambda x: x[1], reverse=True))
    
    async def _generate_recommendations(self, validation: ValidationResult) -> List[str]:
        """
        Génère des recommandations basées sur les patterns détectés.
        
        Args:
            validation: Résultat de validation
            
        Returns:
            Liste de recommandations
        """
        recommendations = []
        
        # Si pas assez de données, retourner des recommandations génériques
        if not validation.document_results or len(validation.document_results) < 5:
            return [
                "Augmenter la taille de l'échantillon pour des recommandations plus précises",
                "Surveiller les métriques de qualité OCR sur une période plus longue"
            ]
        
        # Analyser les métriques globales
        metrics = validation.global_metrics
        
        # Problèmes de confiance globale
        avg_confidence = metrics["confidence"]["mean"]
        if avg_confidence < 0.7:
            recommendations.append(
                f"La confiance moyenne ({avg_confidence:.2f}) est inférieure au seuil recommandé (0.7). "
                "Considérer l'optimisation des paramètres OCR ou le changement de moteur."
            )
        
        # Taux élevé de retraitement
        reprocessing_rate = metrics["workflow"]["reprocessing_rate"]
        if reprocessing_rate > 0.2:
            recommendations.append(
                f"Taux de retraitement élevé ({reprocessing_rate:.0%}). "
                "Examiner les causes communes d'échec et améliorer le processus initial."
            )
        
        # Problèmes spécifiques
        issue_types = validation.detected_patterns.get("issue_types", {})
        content_types = validation.detected_patterns.get("content_types", {})
        
        # Si beaucoup de problèmes de formules
        if content_types.get("formula", 0) > (len(validation.document_results) * 0.3):
            recommendations.append(
                "Nombre élevé de problèmes avec les formules mathématiques. "
                "Envisager un processeur spécialisé pour ce type de contenu."
            )
        
        # Si beaucoup de problèmes de schémas
        if content_types.get("schema", 0) > (len(validation.document_results) * 0.3):
            recommendations.append(
                "Nombre élevé de problèmes avec les schémas techniques. "
                "Améliorer la détection et l'analyse des schémas."
            )
        
        # Si beaucoup de problèmes de qualité OCR globale
        if issue_types.get("global_ocr_quality", 0) > (len(validation.document_results) * 0.3):
            recommendations.append(
                "Problèmes fréquents de qualité OCR globale. "
                "Vérifier les paramètres de numérisation et prétraitement des documents."
            )
        
        # Distribution de qualité
        quality_dist = metrics["quality_distribution"]
        poor_docs = quality_dist.get("poor", 0) + quality_dist.get("very_poor", 0)
        if poor_docs > (len(validation.document_results) * 0.3):
            recommendations.append(
                f"Proportion élevée de documents de qualité insuffisante ({poor_docs / len(validation.document_results):.0%}). "
                "Envisager une révision des processus de capture et de prétraitement."
            )
        
        # Ajouter des recommandations générales si peu de recommandations spécifiques
        if len(recommendations) < 2:
            recommendations.append(
                "Maintenir une surveillance régulière des métriques de qualité OCR."
            )
            recommendations.append(
                "Effectuer des validations manuelles ciblées sur les documents à haute valeur métier."
            )
        
        return recommendations
    
    async def generate_quality_report(self, validation: Union[ValidationResult, str],
                                    format: str = "json") -> Dict[str, Any]:
        """
        Génère un rapport de qualité à partir des résultats de validation.
        
        Args:
            validation: Résultat de validation ou son identifiant
            format: Format du rapport (json, html, pdf)
            
        Returns:
            Rapport de qualité
        """
        # Récupérer la validation si nécessaire
        if isinstance(validation, str):
            if validation not in self.validation_results:
                logger.error(f"Validation inconnue: {validation}")
                return None
            validation = self.validation_results[validation]
        
        # Vérifier que la validation est complète
        if not validation.is_completed:
            logger.error(f"La validation {validation.validation_id} n'est pas complétée")
            return None
        
        # Construire le rapport
        report = {
            "validation_id": validation.validation_id,
            "sample_id": validation.sample_id,
            "created_at": datetime.now().isoformat(),
            "document_count": validation.document_count,
            "metrics": validation.global_metrics,
            "patterns": validation.detected_patterns,
            "summary": {
                "average_confidence": validation.average_confidence,
                "critical_issues": validation.critical_issue_count,
                "reprocessing_rate": validation.global_metrics.get("workflow", {}).get("reprocessing_rate", 0)
            },
            "recommendations": validation.detected_patterns.get("recommendations", [])
        }
        
        # Générer des visualisations si demandé
        if format in ["html", "pdf"]:
            report["visualizations"] = await self._generate_visualizations(validation)
        
        # Pour l'instant, on retourne toujours le format JSON
        # Le support d'autres formats pourrait être ajouté ultérieurement
        return report
    
    async def _generate_visualizations(self, validation: ValidationResult) -> Dict[str, str]:
        """
        Génère des visualisations pour le rapport de qualité.
        
        Args:
            validation: Résultat de validation
            
        Returns:
            Dictionnaire des chemins vers les visualisations générées
        """
        # Cette méthode pourrait générer des graphiques et diagrammes
        # et sauvegarder les images pour inclusion dans le rapport
        # Pour l'instant, on retourne un placeholder
        return {
            "confidence_distribution": "path/to/confidence_chart.png",
            "issue_types": "path/to/issues_chart.png",
            "content_types": "path/to/content_types_chart.png"
        }
    
    async def get_sample(self, sample_id: str) -> Optional[ValidationSample]:
        """
        Récupère un échantillon de validation.
        
        Args:
            sample_id: Identifiant de l'échantillon
            
        Returns:
            Échantillon de validation ou None si inconnu
        """
        return self.samples.get(sample_id)
    
    async def get_validation_result(self, validation_id: str) -> Optional[ValidationResult]:
        """
        Récupère un résultat de validation.
        
        Args:
            validation_id: Identifiant de la validation
            
        Returns:
            Résultat de validation ou None si inconnu
        """
        return self.validation_results.get(validation_id)
    
    async def list_samples(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Liste les échantillons de validation.
        
        Args:
            limit: Nombre maximum d'échantillons à renvoyer
            offset: Décalage pour la pagination
            
        Returns:
            Liste des échantillons de validation
        """
        samples = list(self.samples.values())
        samples.sort(key=lambda s: s.created_at, reverse=True)
        
        paginated = samples[offset:offset + limit]
        return [sample.to_dict() for sample in paginated]
    
    async def list_validations(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Liste les résultats de validation.
        
        Args:
            limit: Nombre maximum de résultats à renvoyer
            offset: Décalage pour la pagination
            
        Returns:
            Liste des résultats de validation
        """
        validations = list(self.validation_results.values())
        validations.sort(key=lambda v: v.completed_at if v.completed_at else "", reverse=True)
        
        paginated = validations[offset:offset + limit]
        return [validation.to_dict() for validation in paginated]
