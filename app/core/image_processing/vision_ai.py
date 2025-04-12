"""
Module d'intégration avec Google Cloud Vision AI.
Permet l'analyse d'images et de schémas techniques.
"""

import os
import asyncio
import tempfile
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging
import base64
import time
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Tentative d'importation des bibliothèques Vision AI
try:
    from google.cloud import vision
    from google.api_core.exceptions import GoogleAPIError
    VISION_AI_AVAILABLE = True
except ImportError:
    logger.warning("Google Cloud Vision AI n'est pas disponible. "
                   "Installez-le avec: pip install google-cloud-vision")
    VISION_AI_AVAILABLE = False


@dataclass
class VisionAnalysisResult:
    """Résultat d'une analyse d'image par Vision AI."""
    
    success: bool
    image_path: Optional[Path] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    
    # Résultats d'analyse
    text_annotations: List[Dict[str, Any]] = field(default_factory=list)
    label_annotations: List[Dict[str, Any]] = field(default_factory=list)
    object_annotations: List[Dict[str, Any]] = field(default_factory=list)
    symbol_annotations: List[Dict[str, Any]] = field(default_factory=list)
    technical_drawing_annotations: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "success": self.success,
            "image_path": str(self.image_path) if self.image_path else None,
            "error_message": self.error_message,
            "processing_time": self.processing_time,
            "text_annotations": self.text_annotations,
            "label_annotations": self.label_annotations,
            "object_annotations": self.object_annotations,
            "symbol_annotations": self.symbol_annotations,
            "technical_drawing_annotations": self.technical_drawing_annotations
        }


class VisionAIService:
    """
    Service d'analyse d'images utilisant Google Cloud Vision AI.
    
    Cette classe fournit des méthodes pour analyser des images et des schémas techniques
    en utilisant l'API Vision AI de Google Cloud Platform.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le service Vision AI.
        
        Args:
            config: Configuration du service
                - project_id: ID du projet GCP (facultatif)
                - timeout: Timeout pour les requêtes API en secondes (défaut: 120)
                - max_results: Nombre maximum de résultats par catégorie (défaut: 10)
        """
        self.config = config or {}
        self.client = None
        self.initialized = False
        self.timeout = self.config.get("timeout", 120)
        self.max_results = self.config.get("max_results", 10)
    
    async def initialize(self) -> bool:
        """
        Initialise le client Vision AI et vérifie la disponibilité du service.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if not VISION_AI_AVAILABLE:
            logger.error("Google Cloud Vision AI n'est pas disponible")
            return False
            
        try:
            # Vérifier que les variables d'environnement nécessaires sont définies
            if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                logger.error("La variable d'environnement GOOGLE_APPLICATION_CREDENTIALS n'est pas définie")
                return False
            
            # Initialiser le client Vision AI dans un thread pour éviter de bloquer l'event loop
            loop = asyncio.get_event_loop()
            self.client = await loop.run_in_executor(
                None, 
                lambda: vision.ImageAnnotatorClient()
            )
            
            logger.info("Client Vision AI initialisé avec succès")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Vision AI: {str(e)}")
            return False
    
    async def analyze_image(self, 
                     image_path: Union[str, Path],
                     features: Optional[List[str]] = None) -> VisionAnalysisResult:
        """
        Analyse une image avec Vision AI.
        
        Args:
            image_path: Chemin vers l'image à analyser
            features: Liste des fonctionnalités à utiliser (par défaut: toutes)
                Options: 'text', 'label', 'object', 'symbol', 'technical_drawing'
                
        Returns:
            Résultat de l'analyse
        """
        if not self.initialized:
            logger.error("Vision AI n'est pas initialisé")
            return VisionAnalysisResult(
                success=False,
                error_message="Vision AI n'est pas initialisé"
            )
        
        image_path = Path(image_path)
        if not image_path.exists():
            return VisionAnalysisResult(
                success=False,
                error_message=f"L'image n'existe pas: {image_path}"
            )
        
        # Par défaut, utiliser toutes les fonctionnalités
        if not features:
            features = ['text', 'label', 'object', 'symbol', 'technical_drawing']
        
        start_time = time.time()
        
        try:
            # Préparer l'image
            with open(image_path, "rb") as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            
            # Préparer les fonctionnalités à utiliser
            feature_types = []
            if 'text' in features:
                feature_types.append(vision.Feature.Type.TEXT_DETECTION)
            if 'label' in features:
                feature_types.append(vision.Feature.Type.LABEL_DETECTION)
            if 'object' in features:
                feature_types.append(vision.Feature.Type.OBJECT_LOCALIZATION)
            if 'symbol' in features:
                feature_types.append(vision.Feature.Type.LOGO_DETECTION)  # Utile pour les symboles techniques
            if 'technical_drawing' in features:
                feature_types.append(vision.Feature.Type.DOCUMENT_TEXT_DETECTION)  # Pour les schémas techniques
            
            # Créer les objets Feature
            vision_features = [vision.Feature(type_=ft, max_results=self.max_results) for ft in feature_types]
            
            # Exécuter l'analyse dans un thread pour éviter de bloquer
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.annotate_image({
                    'image': image,
                    'features': vision_features,
                })
            )
            
            # Traiter les résultats
            result = VisionAnalysisResult(
                success=True,
                image_path=image_path,
                processing_time=time.time() - start_time
            )
            
            # Extraire les annotations de texte
            if 'text' in features and response.text_annotations:
                for annotation in response.text_annotations:
                    result.text_annotations.append({
                        'description': annotation.description,
                        'locale': annotation.locale,
                        'bounds': [
                            {'x': vertex.x, 'y': vertex.y} 
                            for vertex in annotation.bounding_poly.vertices
                        ] if annotation.bounding_poly else []
                    })
            
            # Extraire les annotations d'étiquettes
            if 'label' in features and response.label_annotations:
                for annotation in response.label_annotations:
                    result.label_annotations.append({
                        'description': annotation.description,
                        'score': annotation.score,
                        'topicality': annotation.topicality
                    })
            
            # Extraire les annotations d'objets
            if 'object' in features and response.localized_object_annotations:
                for annotation in response.localized_object_annotations:
                    result.object_annotations.append({
                        'name': annotation.name,
                        'score': annotation.score,
                        'bounds': [
                            {'x': vertex.x, 'y': vertex.y} 
                            for vertex in annotation.bounding_poly.normalized_vertices
                        ] if annotation.bounding_poly else []
                    })
            
            # Extraire les annotations de symboles (logos)
            if 'symbol' in features and response.logo_annotations:
                for annotation in response.logo_annotations:
                    result.symbol_annotations.append({
                        'description': annotation.description,
                        'score': annotation.score,
                        'bounds': [
                            {'x': vertex.x, 'y': vertex.y} 
                            for vertex in annotation.bounding_poly.vertices
                        ] if annotation.bounding_poly else []
                    })
            
            # Extraire les annotations de texte de document (pour schémas techniques)
            if 'technical_drawing' in features and response.full_text_annotation:
                # Extraire le texte complet
                full_text = response.full_text_annotation.text
                
                # Extraire les blocs de texte avec leur position
                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        block_text = ""
                        for paragraph in block.paragraphs:
                            for word in paragraph.words:
                                word_text = ''.join([symbol.text for symbol in word.symbols])
                                block_text += word_text + " "
                        
                        result.technical_drawing_annotations.append({
                            'text': block_text.strip(),
                            'confidence': block.confidence,
                            'bounds': [
                                {'x': vertex.x, 'y': vertex.y} 
                                for vertex in block.bounding_box.vertices
                            ] if block.bounding_box else []
                        })
            
            return result
            
        except GoogleAPIError as api_error:
            error_message = f"Erreur API Google Vision AI: {str(api_error)}"
            logger.error(error_message)
            return VisionAnalysisResult(
                success=False,
                image_path=image_path,
                error_message=error_message
            )
        except Exception as e:
            error_message = f"Erreur lors de l'analyse de l'image: {str(e)}"
            logger.error(error_message)
            return VisionAnalysisResult(
                success=False,
                image_path=image_path,
                error_message=error_message
            )
    
    async def extract_schema_from_pdf(self, 
                               pdf_path: Union[str, Path],
                               output_dir: Optional[Union[str, Path]] = None) -> List[Path]:
        """
        Extrait les schémas techniques d'un document PDF.
        
        Args:
            pdf_path: Chemin vers le document PDF
            output_dir: Répertoire de sortie pour les images extraites
            
        Returns:
            Liste des chemins vers les images extraites
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.error(f"Le document PDF n'existe pas: {pdf_path}")
            return []
        
        # Créer le répertoire de sortie si nécessaire
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = pdf_path.parent / f"{pdf_path.stem}_schemas"
            output_dir.mkdir(parents=True, exist_ok=True)
        
        extracted_images = []
        
        try:
            # Importer les dépendances nécessaires
            from pdf2image import convert_from_path
            import cv2
            import numpy as np
            
            # Convertir les pages du PDF en images
            loop = asyncio.get_event_loop()
            images = await loop.run_in_executor(
                None,
                lambda: convert_from_path(
                    pdf_path, 
                    dpi=300,  # Haute résolution pour une meilleure analyse
                    fmt="png"
                )
            )
            
            for i, image in enumerate(images):
                # Convertir l'image Pillow en format OpenCV
                image_np = np.array(image)
                image_cv = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
                
                # Détecter les contours pour identifier les zones potentielles de schémas
                gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
                _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Filtrer les contours par taille pour éviter les petits éléments
                min_area = 10000  # Ajuster selon les besoins
                filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
                
                for j, contour in enumerate(filtered_contours):
                    # Extraire la région d'intérêt
                    x, y, w, h = cv2.boundingRect(contour)
                    roi = image_cv[y:y+h, x:x+w]
                    
                    # Sauvegarder l'image extraite
                    output_path = output_dir / f"schema_page{i+1}_region{j+1}.png"
                    cv2.imwrite(str(output_path), roi)
                    extracted_images.append(output_path)
                
                # Si aucun schéma n'a été détecté, sauvegarder la page entière comme schéma potentiel
                if len(filtered_contours) == 0:
                    output_path = output_dir / f"page{i+1}.png"
                    cv2.imwrite(str(output_path), image_cv)
                    extracted_images.append(output_path)
            
            logger.info(f"Extraction de {len(extracted_images)} schémas potentiels depuis {pdf_path}")
            return extracted_images
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des schémas: {str(e)}")
            return []
