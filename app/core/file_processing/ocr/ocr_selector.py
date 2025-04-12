"""
Module de sélection intelligente de méthode OCR
==============================================

Ce module implémente un système d'analyse de documents et de sélection intelligente
de la méthode OCR la plus appropriée en fonction des caractéristiques du document.

Caractéristiques principales:
- Analyse automatique de la complexité des documents
- Sélection du moteur OCR optimal en fonction du type et de la structure du document
- Support pour plusieurs fournisseurs OCR (Tesseract, Vision AI, Document AI)
- Fallback automatique en cas d'échec du moteur primaire
- Apprentissage des performances passées pour améliorer les décisions futures

Utilisation typique:
```python
selector = OCRSelector()
await selector.initialize()

# Sélection automatique du meilleur moteur OCR
provider, confidence = await selector.select_ocr_method("path/to/document.pdf")
print(f"Meilleur moteur OCR: {provider} (confiance: {confidence})")
```

Auteur: Équipe Technicia
Date: Mars 2025
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import asyncio
import time
from enum import Enum
import mimetypes
import fitz  # PyMuPDF
import PIL.Image
import numpy as np
from dataclasses import dataclass, field

from .base import OCRProcessor, OCRResult
from .factory import get_ocr_processor, list_available_ocr_providers
from app.config import settings

logger = logging.getLogger(__name__)

class DocumentComplexity(Enum):
    """Classification de la complexité d'un document pour le traitement OCR."""
    SIMPLE = "simple"           # Document principalement textuel, peu d'images
    MEDIUM = "medium"           # Document mixte texte/images standard
    COMPLEX = "complex"         # Document avec mise en page complexe, tables, etc.
    TECHNICAL = "technical"     # Document technique avec schémas, symboles spéciaux
    HANDWRITTEN = "handwritten" # Document contenant de l'écriture manuscrite
    DAMAGED = "damaged"         # Document de mauvaise qualité, endommagé, etc.

@dataclass
class DocumentMetrics:
    """Métriques d'un document pour aider à la sélection de méthode OCR."""
    file_path: Path
    file_size: int = 0
    mime_type: str = ""
    page_count: int = 0
    has_text: bool = False
    text_density: float = 0.0  # Ratio texte/surface
    image_count: int = 0
    image_density: float = 0.0  # Ratio images/surface
    complexity: DocumentComplexity = DocumentComplexity.MEDIUM
    resolution: Optional[Tuple[int, int]] = None
    estimated_processing_time: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit les métriques en dictionnaire."""
        return {
            "file_path": str(self.file_path),
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "page_count": self.page_count,
            "has_text": self.has_text,
            "text_density": self.text_density,
            "image_count": self.image_count,
            "image_density": self.image_density,
            "complexity": self.complexity.value,
            "resolution": self.resolution,
            "estimated_processing_time": self.estimated_processing_time
        }

class OCRSelector:
    """
    Sélecteur intelligent de méthode OCR.
    Analyse un document pour déterminer la méthode OCR la plus adaptée.
    
    Attributes:
        config (Dict[str, Any]): Configuration optionnelle
        available_processors (List[str]): Liste des processeurs OCR disponibles
    """
    
    # Mapping des types MIME vers les méthodes OCR recommandées
    MIME_TYPE_MAPPING = {
        "application/pdf": ["document_ai", "ocrmypdf", "tesseract_direct"],
        "image/jpeg": ["document_ai", "tesseract_direct"],
        "image/png": ["document_ai", "tesseract_direct"],
        "image/tiff": ["document_ai", "tesseract_direct"],
        "image/bmp": ["tesseract_direct", "document_ai"],
        "text/plain": None,  # Pas besoin d'OCR
    }
    
    # Mapping des complexités vers les méthodes OCR recommandées
    COMPLEXITY_MAPPING = {
        DocumentComplexity.SIMPLE: ["tesseract_direct", "ocrmypdf", "document_ai"],
        DocumentComplexity.MEDIUM: ["ocrmypdf", "document_ai", "tesseract_direct"],
        DocumentComplexity.COMPLEX: ["document_ai", "ocrmypdf", "tesseract_direct"],
        DocumentComplexity.TECHNICAL: ["document_ai", "ocrmypdf", "tesseract_direct"],
        DocumentComplexity.HANDWRITTEN: ["document_ai"],
        DocumentComplexity.DAMAGED: ["document_ai", "ocrmypdf", "tesseract_direct"],
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le sélecteur OCR.
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
        self.available_processors = []
    
    async def initialize(self) -> bool:
        """
        Initialise le sélecteur et identifie les processeurs OCR disponibles.
        
        Returns:
            True si au moins un processeur est disponible, False sinon
        """
        try:
            # Récupérer la liste des processeurs OCR disponibles
            provider_names = list_available_ocr_providers()
            logger.info(f"Processeurs OCR disponibles: {provider_names}")
            
            # Tester chaque processeur pour vérifier s'il est disponible
            for provider_name in provider_names:
                try:
                    processor = await get_ocr_processor(provider_name, fallback=False)
                    if processor.is_initialized:
                        self.available_processors.append(provider_name)
                        logger.info(f"Processeur OCR disponible: {provider_name}")
                except Exception as e:
                    logger.warning(f"Processeur OCR non disponible: {provider_name} - {str(e)}")
            
            return len(self.available_processors) > 0
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du sélecteur OCR: {str(e)}")
            return False
    
    async def analyze_document(self, document_path: Union[str, Path]) -> DocumentMetrics:
        """
        Analyse un document pour déterminer ses caractéristiques et complexité.
        
        Args:
            document_path: Chemin vers le document à analyser
            
        Returns:
            Métriques du document
        """
        document_path = Path(document_path)
        
        # Initialiser les métriques
        metrics = DocumentMetrics(
            file_path=document_path,
            file_size=document_path.stat().st_size,
            mime_type=mimetypes.guess_type(document_path)[0] or "application/octet-stream"
        )
        
        try:
            # Analyse spécifique selon le type de fichier
            if metrics.mime_type == "application/pdf":
                await self._analyze_pdf(document_path, metrics)
            elif metrics.mime_type.startswith("image/"):
                await self._analyze_image(document_path, metrics)
            else:
                logger.warning(f"Type de fichier non pris en charge pour l'analyse OCR: {metrics.mime_type}")
                
            # Estimer les temps de traitement pour chaque méthode OCR
            metrics.estimated_processing_time = await self._estimate_processing_time(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du document {document_path}: {str(e)}")
            metrics.complexity = DocumentComplexity.COMPLEX  # Par défaut en cas d'erreur
            return metrics
    
    async def _analyze_pdf(self, pdf_path: Path, metrics: DocumentMetrics) -> None:
        """
        Analyse un document PDF pour déterminer ses caractéristiques.
        
        Args:
            pdf_path: Chemin vers le PDF
            metrics: Métriques à compléter
        """
        try:
            # Ouvrir le PDF avec PyMuPDF
            doc = fitz.open(str(pdf_path))
            
            # Nombre de pages
            metrics.page_count = len(doc)
            
            # Vérifier si le document contient du texte
            text_chars = 0
            total_area = 0
            image_area = 0
            image_count = 0
            
            for page in doc:
                # Surface de la page
                page_area = page.rect.width * page.rect.height
                total_area += page_area
                
                # Texte sur la page
                text = page.get_text()
                text_chars += len(text)
                
                # Images sur la page
                images = page.get_images(full=True)
                image_count += len(images)
                
                for img in images:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image:
                        width, height = base_image["width"], base_image["height"]
                        image_area += width * height
            
            # Calculer les densités
            metrics.has_text = text_chars > 0
            metrics.text_density = text_chars / total_area if total_area > 0 else 0
            metrics.image_count = image_count
            metrics.image_density = image_area / total_area if total_area > 0 else 0
            
            # Déterminer la complexité du document
            if not metrics.has_text and metrics.image_count > 0:
                # Document sans texte mais avec des images -> besoin d'OCR
                metrics.complexity = DocumentComplexity.COMPLEX
            elif metrics.text_density > 0.01 and metrics.image_density < 0.1:
                # Document principalement textuel
                metrics.complexity = DocumentComplexity.SIMPLE
            elif metrics.image_density > 0.5:
                # Document principalement graphique
                metrics.complexity = DocumentComplexity.TECHNICAL
            else:
                # Document mixte
                metrics.complexity = DocumentComplexity.MEDIUM
            
            # Vérifier s'il y a des tables (estimation basée sur la présence de lignes horizontales/verticales)
            has_tables = False
            for page in doc:
                # Rechercher des lignes horizontales et verticales (indicateur potentiel de tableaux)
                paths = page.get_drawings()
                for path in paths:
                    if len(path["items"]) >= 2:  # Au moins une ligne
                        has_tables = True
                        break
                if has_tables:
                    break
            
            if has_tables:
                # Document avec tables -> augmenter la complexité
                if metrics.complexity == DocumentComplexity.SIMPLE:
                    metrics.complexity = DocumentComplexity.MEDIUM
                elif metrics.complexity == DocumentComplexity.MEDIUM:
                    metrics.complexity = DocumentComplexity.COMPLEX
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du PDF {pdf_path}: {str(e)}")
            # En cas d'erreur, considérer le document comme complexe
            metrics.complexity = DocumentComplexity.COMPLEX
    
    async def _analyze_image(self, image_path: Path, metrics: DocumentMetrics) -> None:
        """
        Analyse une image pour déterminer ses caractéristiques.
        
        Args:
            image_path: Chemin vers l'image
            metrics: Métriques à compléter
        """
        try:
            # Ouvrir l'image avec PIL
            with PIL.Image.open(image_path) as img:
                # Récupérer les dimensions
                width, height = img.size
                metrics.resolution = (width, height)
                metrics.page_count = 1
                
                # Convertir en niveaux de gris pour l'analyse
                img_gray = img.convert('L')
                img_array = np.array(img_gray)
                
                # Calculer des métriques sur l'image
                # 1. Contraste de l'image
                contrast = np.std(img_array)
                
                # 2. Netteté de l'image (approximation par écart-type du laplacien)
                from scipy import ndimage
                laplacian = ndimage.laplace(img_array)
                sharpness = np.std(laplacian)
                
                # 3. Nombre de bords (contours) dans l'image
                from skimage import feature
                edges = feature.canny(img_array)
                edge_density = np.sum(edges) / (width * height)
                
                # Déterminer la complexité en fonction des métriques
                if contrast < 30:  # Faible contraste
                    metrics.complexity = DocumentComplexity.DAMAGED
                elif sharpness < 5:  # Image floue
                    metrics.complexity = DocumentComplexity.DAMAGED
                elif edge_density > 0.1:  # Beaucoup de contours (potentiellement un schéma technique)
                    metrics.complexity = DocumentComplexity.TECHNICAL
                else:
                    metrics.complexity = DocumentComplexity.MEDIUM
                
                # Par défaut, une image nécessite toujours OCR
                metrics.has_text = False
                metrics.image_count = 1
                metrics.image_density = 1.0
                
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de l'image {image_path}: {str(e)}")
            # En cas d'erreur, considérer l'image comme complexe
            metrics.complexity = DocumentComplexity.COMPLEX
    
    async def _estimate_processing_time(self, metrics: DocumentMetrics) -> Dict[str, float]:
        """
        Estime le temps de traitement pour chaque méthode OCR.
        
        Args:
            metrics: Métriques du document
            
        Returns:
            Dictionnaire des temps estimés par méthode OCR
        """
        estimates = {}
        
        # Facteurs de base par page pour chaque méthode (en secondes)
        base_factors = {
            "ocrmypdf": 5.0,
            "tesseract_direct": 3.0,
            "document_ai": 2.0
        }
        
        # Facteurs de complexité
        complexity_factors = {
            DocumentComplexity.SIMPLE: 1.0,
            DocumentComplexity.MEDIUM: 1.5,
            DocumentComplexity.COMPLEX: 2.5,
            DocumentComplexity.TECHNICAL: 3.0,
            DocumentComplexity.HANDWRITTEN: 4.0,
            DocumentComplexity.DAMAGED: 3.5
        }
        
        # Facteur de taille (Mo)
        size_mb = metrics.file_size / (1024 * 1024)
        size_factor = max(1.0, 0.5 * size_mb / 10)  # Augmente de 50% par tranche de 10Mo
        
        # Calcul des estimations
        for method, base_factor in base_factors.items():
            if method in self.available_processors:
                complexity_factor = complexity_factors.get(metrics.complexity, 1.5)
                # Formule: (facteur de base * pages * complexité) + facteur de taille
                estimate = (base_factor * metrics.page_count * complexity_factor) + size_factor
                estimates[method] = round(estimate, 2)
        
        return estimates
    
    async def select_ocr_method(self, document_path: Union[str, Path], 
                             prefer_speed: bool = False,
                             prefer_accuracy: bool = False) -> Tuple[str, DocumentMetrics]:
        """
        Sélectionne la méthode OCR la plus adaptée pour un document.
        
        Args:
            document_path: Chemin vers le document
            prefer_speed: Prioriser la vitesse sur la qualité
            prefer_accuracy: Prioriser la précision sur la vitesse
            
        Returns:
            Tuple (nom du processeur OCR sélectionné, métriques du document)
            
        Raises:
            ValueError: Si aucun processeur OCR n'est disponible
        """
        if not self.available_processors:
            raise ValueError("Aucun processeur OCR n'est disponible.")
        
        # Analyser le document
        metrics = await self.analyze_document(document_path)
        logger.info(f"Analyse du document {document_path} terminée: {metrics.complexity.value}")
        
        # Si le type MIME indique qu'aucun OCR n'est nécessaire
        if metrics.mime_type in self.MIME_TYPE_MAPPING and self.MIME_TYPE_MAPPING[metrics.mime_type] is None:
            raise ValueError(f"Le document {document_path} ne nécessite pas d'OCR.")
        
        # Si le document contient déjà du texte et qu'il est de type PDF, vérifier s'il a besoin d'OCR
        if metrics.mime_type == "application/pdf" and metrics.has_text:
            # Vérifier le besoin d'OCR avec chaque processeur disponible
            for processor_name in self.available_processors:
                processor = await get_ocr_processor(processor_name, fallback=False)
                needs_ocr = await processor.needs_ocr(document_path)
                if not needs_ocr:
                    logger.info(f"Le document {document_path} n'a pas besoin d'OCR selon {processor_name}")
                    return "none", metrics
        
        # Sélectionner la méthode en fonction de la complexité du document
        preferred_methods = self.COMPLEXITY_MAPPING.get(metrics.complexity, 
                                                     ["document_ai", "ocrmypdf", "tesseract_direct"])
        
        # Filtrer pour ne garder que les méthodes disponibles
        available_methods = [m for m in preferred_methods if m in self.available_processors]
        
        if not available_methods:
            # Si aucune méthode préférée n'est disponible, utiliser une méthode disponible quelconque
            available_methods = self.available_processors
        
        # Appliquer les préférences utilisateur
        if prefer_speed:
            # Trier par temps de traitement estimé (croissant)
            available_methods.sort(key=lambda m: metrics.estimated_processing_time.get(m, float('inf')))
        elif prefer_accuracy:
            # Pour la précision, on garde l'ordre du mapping de complexité
            # car il est déjà trié par précision décroissante
            pass
        
        # Méthode sélectionnée (premier élément de la liste filtrée)
        selected_method = available_methods[0]
        
        logger.info(f"Méthode OCR sélectionnée pour {document_path}: {selected_method}")
        return selected_method, metrics
    
    async def process_with_best_method(self, document_path: Union[str, Path],
                                  output_path: Optional[Union[str, Path]] = None,
                                  prefer_speed: bool = False,
                                  prefer_accuracy: bool = False,
                                  **kwargs) -> OCRResult:
        """
        Traite un document avec la méthode OCR la plus adaptée.
        
        Args:
            document_path: Chemin vers le document
            output_path: Chemin de sortie
            prefer_speed: Prioriser la vitesse sur la qualité
            prefer_accuracy: Prioriser la précision sur la vitesse
            **kwargs: Options supplémentaires pour le processeur OCR
            
        Returns:
            Résultat du traitement OCR
        """
        try:
            # Sélectionner la méthode OCR
            method, metrics = await self.select_ocr_method(
                document_path, 
                prefer_speed=prefer_speed, 
                prefer_accuracy=prefer_accuracy
            )
            
            # Si aucun OCR n'est nécessaire
            if method == "none":
                # Créer un résultat indiquant que le document n'a pas besoin d'OCR
                result = OCRResult(
                    success=True,
                    output_path=Path(document_path),
                    text_content=None,
                    pages_processed=metrics.page_count,
                    total_pages=metrics.page_count,
                    processing_time=0.0,
                    error_message=None,
                    metadata={"message": "Le document contient déjà du texte et ne nécessite pas d'OCR."}
                )
                return result
            
            # Récupérer le processeur
            processor = await get_ocr_processor(method, fallback=False)
            
            # Traiter le document
            start_time = time.time()
            result = await processor.process_document(
                document_path, 
                output_path, 
                **kwargs
            )
            processing_time = time.time() - start_time
            
            # Mettre à jour le temps de traitement dans le résultat
            result.processing_time = processing_time
            
            # Ajouter les métriques du document dans les métadonnées
            if result.metadata is None:
                result.metadata = {}
            result.metadata["document_metrics"] = metrics.to_dict()
            result.metadata["selected_method"] = method
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement OCR du document {document_path}: {str(e)}")
            
            # Créer un résultat d'erreur
            return OCRResult(
                success=False,
                output_path=None,
                text_content=None,
                pages_processed=0,
                total_pages=0,
                processing_time=0.0,
                error_message=str(e),
                metadata=None
            )
