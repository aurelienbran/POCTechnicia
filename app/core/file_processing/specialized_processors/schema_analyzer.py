"""
Module d'analyse de schémas et diagrammes techniques.

Ce module fournit des fonctionnalités pour détecter, analyser et interpréter
des schémas techniques, diagrammes et plans contenus dans des documents.
Il permet d'extraire le contenu significatif et de le structurer pour
faciliter son utilisation dans un contexte technique.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import logging
import tempfile
import json
import re
from datetime import datetime

import numpy as np
from PIL import Image

from .base import SpecializedProcessor, SpecializedProcessingResult

logger = logging.getLogger(__name__)

# Tentative d'importation des bibliothèques d'analyse d'images
try:
    import cv2
    import pytesseract
    from skimage import feature, measure, morphology, filters
    SCHEMA_LIBS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Certaines bibliothèques d'analyse de schémas ne sont pas disponibles: {str(e)}. "
                  "Installez-les avec: pip install opencv-python pytesseract scikit-image")
    SCHEMA_LIBS_AVAILABLE = False


class SchemaAnalyzer(SpecializedProcessor):
    """
    Processeur spécialisé pour l'analyse des schémas techniques.
    
    Cette classe fournit des méthodes pour détecter, analyser et interpréter
    des schémas, diagrammes et plans techniques contenus dans des documents.
    Elle utilise des techniques de vision par ordinateur pour identifier
    les composants, connexions et annotations dans ces schémas.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'analyseur de schémas.
        
        Args:
            config: Configuration de l'analyseur
                - min_confidence: Seuil minimal de confiance pour les détections
                - extract_components: Extraire les composants individuels
                - extract_text: Extraire le texte des annotations
                - recognize_symbols: Reconnaître les symboles techniques standards
                - output_format: Format de sortie préféré ('json', 'xml', 'text')
                - detection_level: Niveau de détail ('basic', 'detailed', 'comprehensive')
        """
        super().__init__(config)
        
        # Paramètres de configuration avec valeurs par défaut
        self.min_confidence = self.config.get("min_confidence", 0.6)
        self.extract_components = self.config.get("extract_components", True)
        self.extract_text = self.config.get("extract_text", True)
        self.recognize_symbols = self.config.get("recognize_symbols", True)
        self.output_format = self.config.get("output_format", "json")
        self.detection_level = self.config.get("detection_level", "detailed")
        
        # État d'initialisation
        self.ocr_enabled = False
        self.contour_detection_enabled = False
        self.symbol_recognition_enabled = False
        
    async def initialize(self) -> bool:
        """
        Initialise l'analyseur de schémas en vérifiant la disponibilité des dépendances.
        
        Returns:
            True si au moins une méthode d'analyse est disponible, False sinon
        """
        if not SCHEMA_LIBS_AVAILABLE:
            logger.error("Les bibliothèques d'analyse de schémas ne sont pas disponibles")
            return False
        
        try:
            # Vérifier OpenCV
            import cv2
            self.contour_detection_enabled = True
            logger.info("OpenCV est disponible pour la détection de contours et l'analyse d'images")
            
            # Vérifier Tesseract OCR
            try:
                import pytesseract
                # Tester si Tesseract est correctement installé
                pytesseract.get_tesseract_version()
                self.ocr_enabled = True
                logger.info("Tesseract OCR est disponible pour l'extraction de texte")
            except Exception as e:
                logger.warning(f"Tesseract OCR n'est pas disponible ou mal configuré: {str(e)}")
            
            # Vérifier scikit-image
            try:
                from skimage import feature, measure
                self.symbol_recognition_enabled = True
                logger.info("scikit-image est disponible pour la reconnaissance de symboles")
            except Exception as e:
                logger.warning(f"scikit-image n'est pas disponible: {str(e)}")
            
            # L'analyseur est considéré comme initialisé si au moins une méthode est disponible
            self.initialized = self.contour_detection_enabled or self.ocr_enabled or self.symbol_recognition_enabled
            
            if not self.initialized:
                logger.error("Aucune méthode d'analyse de schémas n'est disponible")
                return False
                
            logger.info(f"Analyseur de schémas initialisé avec succès: "
                       f"Contours={self.contour_detection_enabled}, "
                       f"OCR={self.ocr_enabled}, "
                       f"Symboles={self.symbol_recognition_enabled}")
            return True
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'initialisation de l'analyseur de schémas: {str(e)}")
            return False
    
    async def process(self, 
                document_path: Union[str, Path],
                page_number: Optional[int] = None,
                content_region: Optional[Dict[str, Any]] = None,
                **kwargs) -> SpecializedProcessingResult:
        """
        Analyse un document pour en extraire des schémas techniques.
        
        Args:
            document_path: Chemin vers le document contenant des schémas
            page_number: Numéro de page à traiter (None pour toutes les pages)
            content_region: Région du document contenant le schéma (coordonnées)
            **kwargs: Options supplémentaires
                - detection_level: Niveau de détail pour cette requête
                - min_confidence: Seuil minimal de confiance
                - output_format: Format de sortie pour les résultats
                - save_visualizations: Générer des visualisations
                
        Returns:
            Résultat de l'analyse de schémas
        """
        if not self.is_initialized:
            logger.error("L'analyseur de schémas n'est pas initialisé")
            return SpecializedProcessingResult(
                success=False,
                processor_name="SchemaAnalyzer",
                content_type="schema",
                error_message="L'analyseur de schémas n'est pas initialisé",
                source_document=str(document_path),
                page_number=page_number
            )
        
        document_path = Path(document_path)
        
        if not document_path.exists():
            return SpecializedProcessingResult(
                success=False,
                processor_name="SchemaAnalyzer",
                content_type="schema",
                error_message=f"Le document n'existe pas: {document_path}",
                source_document=str(document_path),
                page_number=page_number
            )
        
        # Options spécifiques à cette requête
        detection_level = kwargs.get("detection_level", self.detection_level)
        min_confidence = kwargs.get("min_confidence", self.min_confidence)
        save_visualizations = kwargs.get("save_visualizations", False)
        
        try:
            # Déterminer le type de document
            document_type = document_path.suffix.lower()
            
            # Sélectionner la méthode de traitement selon le type de document
            if document_type in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']:
                # Traitement d'une image directement
                return await self._process_schema_image(
                    document_path,
                    content_region,
                    detection_level=detection_level,
                    min_confidence=min_confidence,
                    save_visualizations=save_visualizations,
                    **kwargs
                )
            elif document_type == '.pdf':
                # Pour les PDF, extraire les pages sous forme d'images
                return await self._process_schema_pdf(
                    document_path,
                    page_number,
                    content_region,
                    detection_level=detection_level,
                    min_confidence=min_confidence,
                    save_visualizations=save_visualizations,
                    **kwargs
                )
            else:
                # Type de document non pris en charge
                return SpecializedProcessingResult(
                    success=False,
                    processor_name="SchemaAnalyzer",
                    content_type="schema",
                    error_message=f"Type de document non pris en charge: {document_type}",
                    source_document=str(document_path),
                    page_number=page_number
                )
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'analyse de schémas: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="SchemaAnalyzer",
                content_type="schema",
                error_message=f"Erreur lors de l'analyse: {str(e)}",
                source_document=str(document_path),
                page_number=page_number
            )
    
    async def _process_schema_image(self,
                             image_path: Path,
                             content_region: Optional[Dict[str, Any]] = None,
                             detection_level: str = "detailed",
                             min_confidence: float = 0.6,
                             save_visualizations: bool = False,
                             **kwargs) -> SpecializedProcessingResult:
        """
        Analyse une image contenant un schéma technique.
        
        Args:
            image_path: Chemin vers l'image
            content_region: Région de l'image contenant le schéma
            detection_level: Niveau de détail de l'analyse
            min_confidence: Seuil minimal de confiance
            save_visualizations: Générer des visualisations
            **kwargs: Options supplémentaires
                
        Returns:
            Résultat de l'analyse du schéma
        """
        import cv2
        
        try:
            # Charger l'image
            image = cv2.imread(str(image_path))
            if image is None:
                return SpecializedProcessingResult(
                    success=False,
                    processor_name="SchemaAnalyzer",
                    content_type="schema",
                    error_message="Impossible de charger l'image",
                    source_document=str(image_path)
                )
            
            # Recadrer l'image si une région est spécifiée
            if content_region:
                x1 = int(content_region.get("x1", 0))
                y1 = int(content_region.get("y1", 0))
                x2 = int(content_region.get("x2", image.shape[1]))
                y2 = int(content_region.get("y2", image.shape[0]))
                
                image = image[y1:y2, x1:x2]
            
            # Prétraiter l'image
            preprocessed = await self._preprocess_image(image)
            
            # Détecter les contours et les composants
            components = await self._detect_components(preprocessed, detection_level, min_confidence)
            
            # Extraire le texte si l'OCR est activé
            text_annotations = []
            if self.extract_text and self.ocr_enabled:
                text_annotations = await self._extract_text_from_image(image)
            
            # Reconnaître les symboles techniques si activé
            symbols = []
            if self.recognize_symbols and self.symbol_recognition_enabled:
                symbols = await self._recognize_symbols(preprocessed, components, min_confidence)
            
            # Analyser la structure du schéma
            structure = await self._analyze_schema_structure(
                preprocessed, 
                components, 
                text_annotations, 
                symbols,
                detection_level
            )
            
            # Générer des visualisations si demandé
            visualizations = {}
            if save_visualizations:
                visualizations = await self._generate_visualizations(
                    image, 
                    preprocessed, 
                    components, 
                    text_annotations, 
                    symbols,
                    structure
                )
            
            # Préparer les résultats de l'analyse
            schema_data = {
                "components": components,
                "text_annotations": text_annotations,
                "symbols": symbols,
                "structure": structure,
                "visualizations": list(visualizations.keys()) if visualizations else []
            }
            
            # Préparer les métadonnées
            metadata = {
                "image_size": {"width": image.shape[1], "height": image.shape[0]},
                "components_count": len(components),
                "text_annotations_count": len(text_annotations),
                "symbols_count": len(symbols),
                "connections_count": len(structure.get("connections", [])),
                "confidence_avg": self._calculate_avg_confidence(components, symbols),
                "complexity": self._estimate_schema_complexity(components, text_annotations, symbols, structure)
            }
            
            # Préparer la représentation textuelle du schéma
            text_representation = self._generate_schema_description(
                components, 
                text_annotations, 
                symbols, 
                structure
            )
            
            # Retourner le résultat
            return SpecializedProcessingResult(
                success=True,
                processor_name="SchemaAnalyzer",
                content_type="schema",
                extracted_data=schema_data,
                source_document=str(image_path),
                metadata=metadata,
                text_representation=text_representation,
                additional_files=visualizations
            )
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'analyse de l'image: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="SchemaAnalyzer",
                content_type="schema",
                error_message=f"Erreur lors de l'analyse: {str(e)}",
                source_document=str(image_path)
            )
    
    async def _process_schema_pdf(self,
                           document_path: Path,
                           page_number: Optional[int] = None,
                           content_region: Optional[Dict[str, Any]] = None,
                           detection_level: str = "detailed",
                           min_confidence: float = 0.6,
                           save_visualizations: bool = False,
                           **kwargs) -> SpecializedProcessingResult:
        """
        Analyse un PDF pour en extraire des schémas techniques.
        
        Args:
            document_path: Chemin vers le document PDF
            page_number: Numéro de page à traiter
            content_region: Région du document contenant le schéma
            detection_level: Niveau de détail de l'analyse
            min_confidence: Seuil minimal de confiance
            save_visualizations: Générer des visualisations
            **kwargs: Options supplémentaires
                
        Returns:
            Résultat de l'analyse des schémas
        """
        try:
            # Convertir les pages du PDF en images
            from pdf2image import convert_from_path
            
            loop = asyncio.get_event_loop()
            
            # Déterminer les pages à convertir
            if page_number is not None:
                images = await loop.run_in_executor(
                    None,
                    lambda: convert_from_path(document_path, first_page=page_number+1, last_page=page_number+1)
                )
            else:
                images = await loop.run_in_executor(
                    None,
                    lambda: convert_from_path(document_path)
                )
            
            if not images:
                return SpecializedProcessingResult(
                    success=False,
                    processor_name="SchemaAnalyzer",
                    content_type="schema",
                    error_message="Impossible de convertir le PDF en images",
                    source_document=str(document_path),
                    page_number=page_number
                )
            
            # Traiter chaque image pour détecter des schémas
            all_schemas = []
            page_schemas = {}
            visualizations = {}
            
            for idx, pil_image in enumerate(images):
                current_page = page_number if page_number is not None else idx
                
                # Convertir l'image PIL en image OpenCV
                image_np = np.array(pil_image)
                image = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
                
                # Recadrer l'image si une région est spécifiée
                if content_region:
                    x1 = int(content_region.get("x1", 0))
                    y1 = int(content_region.get("y1", 0))
                    x2 = int(content_region.get("x2", image.shape[1]))
                    y2 = int(content_region.get("y2", image.shape[0]))
                    
                    image = image[y1:y2, x1:x2]
                
                # Prétraiter l'image
                preprocessed = await self._preprocess_image(image)
                
                # Détecter les contours et les composants
                components = await self._detect_components(preprocessed, detection_level, min_confidence)
                
                # Extraire le texte si l'OCR est activé
                text_annotations = []
                if self.extract_text and self.ocr_enabled:
                    text_annotations = await self._extract_text_from_image(image)
                
                # Reconnaître les symboles techniques si activé
                symbols = []
                if self.recognize_symbols and self.symbol_recognition_enabled:
                    symbols = await self._recognize_symbols(preprocessed, components, min_confidence)
                
                # Analyser la structure du schéma
                structure = await self._analyze_schema_structure(
                    preprocessed, 
                    components, 
                    text_annotations, 
                    symbols,
                    detection_level
                )
                
                # Vérifier si ce qui a été détecté ressemble à un schéma
                if not self._is_likely_schema(components, text_annotations, symbols, structure):
                    logger.info(f"Page {current_page+1}: Aucun schéma technique détecté")
                    continue
                
                # Générer des visualisations si demandé
                page_visualizations = {}
                if save_visualizations:
                    page_visualizations = await self._generate_visualizations(
                        image, 
                        preprocessed, 
                        components, 
                        text_annotations, 
                        symbols,
                        structure,
                        prefix=f"page_{current_page+1}_"
                    )
                    visualizations.update(page_visualizations)
                
                # Préparer les résultats de l'analyse pour cette page
                schema_data = {
                    "page": current_page,
                    "components": components,
                    "text_annotations": text_annotations,
                    "symbols": symbols,
                    "structure": structure,
                    "visualizations": list(page_visualizations.keys()) if page_visualizations else []
                }
                
                all_schemas.append(schema_data)
                page_schemas[current_page] = schema_data
            
            if not all_schemas:
                return SpecializedProcessingResult(
                    success=True,  # Succès technique même si aucun schéma n'est trouvé
                    processor_name="SchemaAnalyzer",
                    content_type="schema",
                    extracted_data={"schemas": []},
                    source_document=str(document_path),
                    page_number=page_number,
                    metadata={"schemas_count": 0},
                    text_representation="Aucun schéma technique détecté dans le document."
                )
            
            # Préparer les métadonnées
            metadata = {
                "schemas_count": len(all_schemas),
                "document_type": "pdf",
                "page_count": len(images),
                "pages_with_schemas": len(page_schemas)
            }
            
            # Préparer la représentation textuelle
            text_parts = []
            for page, schema in sorted(page_schemas.items()):
                text_parts.append(f"[PAGE {page+1}]")
                
                text_description = self._generate_schema_description(
                    schema["components"], 
                    schema["text_annotations"], 
                    schema["symbols"], 
                    schema["structure"]
                )
                
                text_parts.append(text_description)
                text_parts.append("")
            
            text_representation = "\n".join(text_parts)
            
            # Retourner le résultat
            return SpecializedProcessingResult(
                success=True,
                processor_name="SchemaAnalyzer",
                content_type="schema",
                extracted_data={"schemas": all_schemas},
                source_document=str(document_path),
                page_number=page_number if len(images) == 1 else None,
                metadata=metadata,
                text_representation=text_representation,
                additional_files=visualizations
            )
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'analyse du PDF: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="SchemaAnalyzer",
                content_type="schema",
                error_message=f"Erreur lors de l'analyse: {str(e)}",
                source_document=str(document_path),
                page_number=page_number
            )

    async def _preprocess_image(self, image):
        """
        Prétraite une image pour améliorer la détection des schémas.
        
        Args:
            image: Image OpenCV à prétraiter
            
        Returns:
            Image prétraitée
        """
        try:
            # Convertir en niveaux de gris
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Appliquer un filtre de réduction du bruit
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Détection des bords avec Canny
            edges = cv2.Canny(blurred, 50, 150)
            
            # Dilatation pour fermer les contours
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(edges, kernel, iterations=1)
            
            return {
                "original": image,
                "gray": gray,
                "blurred": blurred,
                "edges": edges,
                "dilated": dilated
            }
        except Exception as e:
            logger.exception(f"Erreur lors du prétraitement de l'image: {str(e)}")
            # Retourner au moins l'image originale en cas d'erreur
            return {
                "original": image,
                "gray": cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) > 2 else image
            }
    
    async def _detect_components(self, preprocessed, detection_level="detailed", min_confidence=0.6):
        """
        Détecte les composants d'un schéma technique.
        
        Args:
            preprocessed: Images prétraitées
            detection_level: Niveau de détail ('basic', 'detailed', 'comprehensive')
            min_confidence: Seuil minimal de confiance
            
        Returns:
            Liste des composants détectés
        """
        components = []
        
        try:
            # Utiliser l'image dilatée pour la détection de contours
            contours, hierarchy = cv2.findContours(
                preprocessed.get("dilated", preprocessed.get("edges")),
                cv2.RETR_CCOMP if detection_level in ["detailed", "comprehensive"] else cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Filtrer les contours trop petits ou trop grands
            min_area = 50  # Aire minimale en pixels
            max_area = preprocessed["original"].shape[0] * preprocessed["original"].shape[1] * 0.5  # 50% de l'image
            
            for i, contour in enumerate(contours):
                # Calculer l'aire du contour
                area = cv2.contourArea(contour)
                
                # Ignorer les contours trop petits ou trop grands
                if area < min_area or area > max_area:
                    continue
                
                # Obtenir un rectangle englobant
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculer un score de confiance basé sur la taille et la forme
                # Les composants techniques ont souvent des formes géométriques régulières
                confidence = self._calculate_component_confidence(contour, area, preprocessed["gray"])
                
                if confidence < min_confidence:
                    continue
                
                # Déterminer le type de composant basé sur la forme
                component_type = self._determine_component_type(contour, hierarchy[0][i] if hierarchy is not None else None)
                
                # Approximer la forme du contour pour une représentation simplifiée
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Créer un masque pour extraire la région du composant
                mask = np.zeros(preprocessed["gray"].shape, dtype=np.uint8)
                cv2.drawContours(mask, [contour], 0, 255, -1)
                component_region = cv2.bitwise_and(preprocessed["gray"], preprocessed["gray"], mask=mask)
                
                # Extraire des caractéristiques basées sur la forme
                features = self._extract_component_features(contour, component_region, approx)
                
                # Ajouter le composant détecté
                component = {
                    "id": len(components),
                    "type": component_type,
                    "confidence": float(confidence),
                    "bounding_box": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                    "centroid": {"x": int(x + w/2), "y": int(y + h/2)},
                    "area": float(area),
                    "features": features
                }
                
                if detection_level == "comprehensive":
                    # Ajouter le contour complet pour une analyse détaillée
                    # Convertir le contour numpy en liste pour la sérialisation JSON
                    component["contour"] = [[int(point[0][0]), int(point[0][1])] for point in contour]
                
                components.append(component)
            
            # Trier les composants par confiance décroissante
            components.sort(key=lambda x: x["confidence"], reverse=True)
            
            return components
            
        except Exception as e:
            logger.exception(f"Erreur lors de la détection des composants: {str(e)}")
            return []
    
    def _calculate_component_confidence(self, contour, area, gray_image):
        """
        Calcule un score de confiance pour un composant détecté.
        
        Args:
            contour: Contour du composant
            area: Aire du contour
            gray_image: Image en niveaux de gris
            
        Returns:
            Score de confiance (0.0 à 1.0)
        """
        try:
            # Obtenir un rectangle englobant
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculer les ratios d'aspect
            aspect_ratio = float(w) / h if h != 0 else 0
            
            # Les composants techniques ont souvent des ratios d'aspect proches de certaines valeurs
            # (carrés, rectangles dans certaines proportions, cercles)
            shape_score = 0.0
            
            # Vérifier si la forme est proche d'un carré
            if 0.8 < aspect_ratio < 1.2:
                shape_score = 0.8
            # Vérifier si la forme est un rectangle avec un ratio d'aspect raisonnable
            elif 0.2 < aspect_ratio < 5.0:
                shape_score = 0.6
            else:
                shape_score = 0.3
            
            # Calculer la compacité (rapport de l'aire au périmètre au carré)
            # Les formes géométriques régulières ont une compacité plus élevée
            perimeter = cv2.arcLength(contour, True)
            compactness = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            # Les cercles ont une compacité proche de 1, les formes régulières sont entre 0.5 et 1
            if compactness > 0.8:  # Proche d'un cercle
                shape_score = max(shape_score, 0.9)
            elif compactness > 0.6:  # Forme régulière
                shape_score = max(shape_score, 0.7)
            
            # Vérifier l'uniformité du contenu (variance faible pour les symboles techniques)
            roi = gray_image[y:y+h, x:x+w]
            if roi.size > 0:
                variance = np.var(roi)
                contrast_score = 1.0 - min(1.0, variance / 10000)  # Normaliser la variance
            else:
                contrast_score = 0.0
            
            # Combiner les scores
            final_score = 0.5 * shape_score + 0.3 * compactness + 0.2 * contrast_score
            
            return min(1.0, max(0.0, final_score))
            
        except Exception as e:
            logger.warning(f"Erreur lors du calcul de la confiance du composant: {str(e)}")
            return 0.0
    
    def _determine_component_type(self, contour, hierarchy):
        """
        Détermine le type probable d'un composant basé sur sa forme.
        
        Args:
            contour: Contour du composant
            hierarchy: Hiérarchie des contours
            
        Returns:
            Type de composant
        """
        try:
            # Obtenir un rectangle englobant
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculer des caractéristiques de forme
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            # Approximer la forme
            epsilon = 0.04 * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Calculer la compacité (valeur entre 0 et 1, 1 pour un cercle parfait)
            compactness = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            # Nombre de sommets après approximation
            num_vertices = len(approx)
            
            # Vérifier si c'est un cercle ou une ellipse
            if compactness > 0.8:
                return "circle" if abs(w - h) < 0.2 * max(w, h) else "ellipse"
            
            # Vérifier si c'est un rectangle
            if num_vertices == 4:
                return "rectangle"
            
            # Vérifier si c'est un triangle
            if num_vertices == 3:
                return "triangle"
            
            # Vérifier si c'est un polygone régulier
            if 5 <= num_vertices <= 10:
                return f"polygon_{num_vertices}"
            
            # Vérifier si c'est une ligne
            if area < 200 and (w > 5 * h or h > 5 * w):
                return "line"
            
            # Par défaut
            return "component"
            
        except Exception as e:
            logger.warning(f"Erreur lors de la détermination du type de composant: {str(e)}")
            return "unknown"
    
    def _extract_component_features(self, contour, region, approx):
        """
        Extrait des caractéristiques d'un composant.
        
        Args:
            contour: Contour du composant
            region: Région de l'image correspondant au composant
            approx: Approximation polygonale du contour
            
        Returns:
            Caractéristiques du composant
        """
        try:
            # Calculer des moments pour obtenir le centre de masse
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = 0, 0
            
            # Calculer l'orientation de l'ellipse englobante
            if len(contour) >= 5:  # Minimum 5 points pour fitEllipse
                ellipse = cv2.fitEllipse(contour)
                orientation = ellipse[2]  # Angle en degrés
            else:
                orientation = 0
            
            # Calculer les moments de Hu (invariants à l'échelle, la rotation et la translation)
            hu_moments = cv2.HuMoments(M).flatten()
            
            # Retourner les caractéristiques
            return {
                "center": {"x": cx, "y": cy},
                "orientation": float(orientation),
                "hu_moments": [float(m) for m in hu_moments],
                "vertices": len(approx),
                "convexity": float(cv2.isContourConvex(approx))
            }
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction des caractéristiques du composant: {str(e)}")
            return {}

    async def _extract_text_from_image(self, image):
        """
        Extrait le texte d'une image à l'aide d'OCR.
        
        Args:
            image: Image OpenCV
            
        Returns:
            Liste des annotations textuelles
        """
        if not self.ocr_enabled:
            return []
        
        try:
            # Convertir en niveau de gris si nécessaire
            if len(image.shape) > 2:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Améliorer le contraste pour l'OCR
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Appliquer un seuillage adaptatif
            thresh = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Sauvegarder l'image temporairement pour l'OCR
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                ocr_image_path = tmp.name
                cv2.imwrite(ocr_image_path, thresh)
            
            # Configurer Tesseract pour les documents techniques
            custom_config = '--oem 1 --psm 6 -l fra+eng'
            
            # Exécuter OCR
            loop = asyncio.get_event_loop()
            ocr_result = await loop.run_in_executor(
                None,
                lambda: pytesseract.image_to_data(
                    thresh, config=custom_config, output_type=pytesseract.Output.DICT
                )
            )
            
            # Supprimer le fichier temporaire
            try:
                os.unlink(ocr_image_path)
            except Exception:
                pass
            
            # Traiter les résultats OCR
            text_annotations = []
            n_boxes = len(ocr_result['text'])
            
            for i in range(n_boxes):
                # Ignorer les textes vides ou avec une confiance faible
                if int(ocr_result['conf'][i]) < 40 or not ocr_result['text'][i].strip():
                    continue
                
                # Obtenir les coordonnées du texte
                x = ocr_result['left'][i]
                y = ocr_result['top'][i]
                w = ocr_result['width'][i]
                h = ocr_result['height'][i]
                
                # Ajouter l'annotation
                annotation = {
                    "id": len(text_annotations),
                    "text": ocr_result['text'][i].strip(),
                    "confidence": float(ocr_result['conf'][i]) / 100,
                    "bounding_box": {"x": x, "y": y, "width": w, "height": h},
                    "language": ocr_result.get('lang', 'unknown')[i] if 'lang' in ocr_result else 'unknown',
                    "type": self._classify_text_annotation(ocr_result['text'][i].strip())
                }
                
                text_annotations.append(annotation)
            
            return text_annotations
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'extraction de texte: {str(e)}")
            return []
    
    def _classify_text_annotation(self, text):
        """
        Classifie une annotation textuelle.
        
        Args:
            text: Texte de l'annotation
            
        Returns:
            Type d'annotation
        """
        # Nettoyer le texte
        text = text.strip().lower()
        
        # Vérifier si c'est un nombre ou une valeur
        if re.match(r'^[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$', text):
            return "number"
        
        # Vérifier si c'est une unité de mesure
        if re.search(r'\b(mm|cm|m|kg|g|v|volt|amp|ohm|hz|db|°c|°f|psi|bar|mpa)\b', text):
            return "unit"
        
        # Vérifier si c'est un label ou une référence
        if re.match(r'^[a-z][0-9]+$|^[0-9]+[a-z]$', text) or re.match(r'^ref\.?\s*[0-9a-z\-_]+$', text):
            return "reference"
        
        # Vérifier si c'est une remarque ou une note
        if text.startswith("note") or text.startswith("remark") or text.startswith("nb"):
            return "note"
        
        # Par défaut
        return "label"
    
    async def _recognize_symbols(self, preprocessed, components, min_confidence=0.6):
        """
        Reconnaît les symboles techniques dans une image.
        
        Args:
            preprocessed: Images prétraitées
            components: Composants détectés
            min_confidence: Seuil minimal de confiance
            
        Returns:
            Liste des symboles reconnus
        """
        if not self.symbol_recognition_enabled:
            return []
        
        try:
            # Cette méthode utiliserait idéalement une base de données de symboles techniques
            # et un classificateur (comme SVM, CNN, etc.)
            # Pour cet exemple, nous utilisons une approche simplifiée basée sur les caractéristiques
            
            symbols = []
            
            for component in components:
                # Initialiser un score pour chaque catégorie de symbole
                symbol_scores = {
                    "resistor": 0.0,
                    "capacitor": 0.0,
                    "transistor": 0.0,
                    "diode": 0.0,
                    "battery": 0.0,
                    "switch": 0.0,
                    "led": 0.0,
                    "connector": 0.0,
                    "inductor": 0.0,
                    "motor": 0.0
                }
                
                # Obtenir les caractéristiques du composant
                bbox = component["bounding_box"]
                component_type = component["type"]
                aspect_ratio = bbox["width"] / bbox["height"] if bbox["height"] > 0 else 0
                area = component["area"]
                features = component.get("features", {})
                
                # Caractéristiques typiques de chaque symbole
                
                # Résistance: rectangulaire, souvent avec un ratio d'aspect élevé
                if component_type == "rectangle" and 2.5 < aspect_ratio < 5.0:
                    symbol_scores["resistor"] = 0.7
                
                # Condensateur: deux lignes parallèles proches
                elif component_type == "rectangle" and 0.2 < aspect_ratio < 0.5:
                    symbol_scores["capacitor"] = 0.6
                
                # Diode: triangle avec une ligne
                elif component_type == "triangle":
                    symbol_scores["diode"] = 0.6
                
                # Cercle: peut être LED, moteur, etc.
                elif component_type == "circle":
                    symbol_scores["led"] = 0.4
                    symbol_scores["motor"] = 0.4
                
                # Caractéristiques basées sur la convexité (par exemple, transistor)
                convexity = features.get("convexity", 0)
                if convexity > 0.8 and component_type == "polygon_6":
                    symbol_scores["transistor"] = 0.65
                
                # Caractéristiques basées sur les moments de Hu
                hu_moments = features.get("hu_moments", [])
                if hu_moments and len(hu_moments) >= 7:
                    # Certains moments de Hu sont caractéristiques de symboles spécifiques
                    # Ces valeurs seraient normalement déterminées par apprentissage
                    pass
                
                # Trouver le symbole le plus probable
                best_symbol = max(symbol_scores.items(), key=lambda x: x[1])
                
                # Si la confiance est suffisante, ajouter le symbole
                if best_symbol[1] >= min_confidence:
                    symbol = {
                        "id": len(symbols),
                        "component_id": component["id"],
                        "type": best_symbol[0],
                        "confidence": float(best_symbol[1]),
                        "bounding_box": component["bounding_box"],
                        "centroid": component["centroid"]
                    }
                    symbols.append(symbol)
            
            return symbols
            
        except Exception as e:
            logger.exception(f"Erreur lors de la reconnaissance de symboles: {str(e)}")
            return []
    
    async def _analyze_schema_structure(self, preprocessed, components, text_annotations, symbols, detection_level):
        """
        Analyse la structure d'un schéma technique.
        
        Args:
            preprocessed: Images prétraitées
            components: Composants détectés
            text_annotations: Annotations textuelles
            symbols: Symboles reconnus
            detection_level: Niveau de détail de l'analyse
            
        Returns:
            Structure du schéma
        """
        try:
            # Détection des lignes pour les connexions
            lines = []
            
            # Utiliser la transformée de Hough pour détecter les lignes
            if "edges" in preprocessed:
                loop = asyncio.get_event_loop()
                detected_lines = await loop.run_in_executor(
                    None,
                    lambda: cv2.HoughLinesP(
                        preprocessed["edges"],
                        1, np.pi/180, 
                        threshold=50, 
                        minLineLength=30, 
                        maxLineGap=10
                    )
                )
                
                if detected_lines is not None:
                    for i, line in enumerate(detected_lines):
                        x1, y1, x2, y2 = line[0]
                        lines.append({
                            "id": i,
                            "start": {"x": int(x1), "y": int(y1)},
                            "end": {"x": int(x2), "y": int(y2)},
                            "length": float(np.sqrt((x2 - x1)**2 + (y2 - y1)**2)),
                            "angle": float(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                        })
            
            # Détecter les connexions entre composants
            connections = []
            component_positions = {comp["id"]: (comp["centroid"]["x"], comp["centroid"]["y"]) for comp in components}
            
            # Associer les lignes aux composants
            for line in lines:
                start_point = (line["start"]["x"], line["start"]["y"])
                end_point = (line["end"]["x"], line["end"]["y"])
                
                # Trouver les composants les plus proches des extrémités de la ligne
                start_component = None
                end_component = None
                min_start_dist = float('inf')
                min_end_dist = float('inf')
                
                for comp_id, pos in component_positions.items():
                    start_dist = np.sqrt((pos[0] - start_point[0])**2 + (pos[1] - start_point[1])**2)
                    end_dist = np.sqrt((pos[0] - end_point[0])**2 + (pos[1] - end_point[1])**2)
                    
                    if start_dist < min_start_dist and start_dist < 30:  # Seuil de distance
                        min_start_dist = start_dist
                        start_component = comp_id
                    
                    if end_dist < min_end_dist and end_dist < 30:  # Seuil de distance
                        min_end_dist = end_dist
                        end_component = comp_id
                
                # Si une connexion est trouvée, l'ajouter
                if start_component is not None and end_component is not None and start_component != end_component:
                    connections.append({
                        "id": len(connections),
                        "component1_id": start_component,
                        "component2_id": end_component,
                        "line_id": line["id"]
                    })
            
            # Associer les annotations textuelles aux composants
            component_annotations = {}
            
            for anno in text_annotations:
                anno_center = (
                    anno["bounding_box"]["x"] + anno["bounding_box"]["width"] / 2,
                    anno["bounding_box"]["y"] + anno["bounding_box"]["height"] / 2
                )
                
                # Trouver le composant le plus proche
                closest_comp = None
                min_dist = float('inf')
                
                for comp in components:
                    comp_center = (comp["centroid"]["x"], comp["centroid"]["y"])
                    dist = np.sqrt((comp_center[0] - anno_center[0])**2 + (comp_center[1] - anno_center[1])**2)
                    
                    if dist < min_dist and dist < 100:  # Seuil de distance
                        min_dist = dist
                        closest_comp = comp["id"]
                
                if closest_comp is not None:
                    if closest_comp not in component_annotations:
                        component_annotations[closest_comp] = []
                    component_annotations[closest_comp].append(anno["id"])
            
            # Regrouper les composants en sous-systèmes (pour un niveau d'analyse détaillé)
            subsystems = []
            if detection_level in ["detailed", "comprehensive"] and len(components) > 3:
                # Utiliser un algorithme de clustering pour grouper les composants proches
                from sklearn.cluster import DBSCAN
                
                # Extraire les coordonnées des composants
                coords = np.array([
                    [comp["centroid"]["x"], comp["centroid"]["y"]]
                    for comp in components
                ])
                
                if len(coords) > 0:
                    # Appliquer DBSCAN
                    loop = asyncio.get_event_loop()
                    clustering = await loop.run_in_executor(
                        None,
                        lambda: DBSCAN(eps=150, min_samples=2).fit(coords)
                    )
                    
                    labels = clustering.labels_
                    
                    # Créer les sous-systèmes à partir des clusters
                    unique_labels = set(labels)
                    for label in unique_labels:
                        if label == -1:  # Ignorer les points de bruit
                            continue
                            
                        cluster_indices = [i for i, lbl in enumerate(labels) if lbl == label]
                        
                        if len(cluster_indices) >= 2:
                            subsystem = {
                                "id": len(subsystems),
                                "components": [components[i]["id"] for i in cluster_indices],
                                "centroid": {
                                    "x": int(np.mean([components[i]["centroid"]["x"] for i in cluster_indices])),
                                    "y": int(np.mean([components[i]["centroid"]["y"] for i in cluster_indices]))
                                },
                                "bounding_box": self._calculate_subsystem_bbox(
                                    [components[i]["bounding_box"] for i in cluster_indices]
                                )
                            }
                            subsystems.append(subsystem)
            
            # Retourner la structure complète
            return {
                "lines": lines,
                "connections": connections,
                "component_annotations": component_annotations,
                "subsystems": subsystems
            }
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'analyse de la structure: {str(e)}")
            return {
                "lines": [],
                "connections": [],
                "component_annotations": {},
                "subsystems": []
            }
    
    def _calculate_subsystem_bbox(self, bboxes):
        """
        Calcule la boîte englobante d'un sous-système.
        
        Args:
            bboxes: Liste des boîtes englobantes des composants
            
        Returns:
            Boîte englobante du sous-système
        """
        if not bboxes:
            return {"x": 0, "y": 0, "width": 0, "height": 0}
        
        min_x = min(bbox["x"] for bbox in bboxes)
        min_y = min(bbox["y"] for bbox in bboxes)
        max_x = max(bbox["x"] + bbox["width"] for bbox in bboxes)
        max_y = max(bbox["y"] + bbox["height"] for bbox in bboxes)
        
        return {
            "x": int(min_x),
            "y": int(min_y),
            "width": int(max_x - min_x),
            "height": int(max_y - min_y)
        }
    
    async def _generate_visualizations(self, image, preprocessed, components, text_annotations, symbols, structure, prefix=""):
        """
        Génère des visualisations pour l'analyse du schéma.
        
        Args:
            image: Image originale
            preprocessed: Images prétraitées
            components: Composants détectés
            text_annotations: Annotations textuelles
            symbols: Symboles reconnus
            structure: Structure du schéma
            prefix: Préfixe pour les noms de fichiers
            
        Returns:
            Dictionnaire des chemins des visualisations générées
        """
        visualizations = {}
        
        try:
            # Créer un répertoire temporaire pour les visualisations
            temp_dir = tempfile.mkdtemp()
            
            # Visualisation des composants
            if components:
                vis_components = image.copy()
                
                for comp in components:
                    bbox = comp["bounding_box"]
                    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                    
                    # Couleur selon le type
                    color = (0, 255, 0)  # Vert par défaut
                    if comp["type"] == "circle":
                        color = (255, 0, 0)  # Rouge
                    elif comp["type"] == "rectangle":
                        color = (0, 0, 255)  # Bleu
                    elif comp["type"] == "triangle":
                        color = (255, 255, 0)  # Jaune
                    
                    # Dessiner le rectangle
                    cv2.rectangle(vis_components, (x, y), (x + w, y + h), color, 2)
                    
                    # Ajouter l'ID et le type
                    label = f"{comp['id']}: {comp['type']}"
                    cv2.putText(vis_components, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # Sauvegarder l'image
                components_path = os.path.join(temp_dir, f"{prefix}components.png")
                cv2.imwrite(components_path, vis_components)
                visualizations[components_path] = "Components visualization"
            
            # Visualisation des annotations textuelles
            if text_annotations:
                vis_text = image.copy()
                
                for anno in text_annotations:
                    bbox = anno["bounding_box"]
                    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                    
                    # Dessiner le rectangle
                    cv2.rectangle(vis_text, (x, y), (x + w, y + h), (0, 255, 255), 1)  # Jaune
                    
                    # Ajouter le texte
                    cv2.putText(vis_text, anno["text"], (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Sauvegarder l'image
                text_path = os.path.join(temp_dir, f"{prefix}text_annotations.png")
                cv2.imwrite(text_path, vis_text)
                visualizations[text_path] = "Text annotations visualization"
            
            # Visualisation des connexions
            if structure and "connections" in structure and structure["connections"]:
                vis_connections = image.copy()
                
                # Dessiner les lignes
                for line in structure.get("lines", []):
                    cv2.line(
                        vis_connections,
                        (line["start"]["x"], line["start"]["y"]),
                        (line["end"]["x"], line["end"]["y"]),
                        (0, 255, 0),  # Vert
                        1
                    )
                
                # Dessiner les composants connectés
                for conn in structure["connections"]:
                    # Trouver les composants connectés
                    comp1_id = conn["component1_id"]
                    comp2_id = conn["component2_id"]
                    
                    comp1 = next((c for c in components if c["id"] == comp1_id), None)
                    comp2 = next((c for c in components if c["id"] == comp2_id), None)
                    
                    if comp1 and comp2:
                        # Dessiner les centroïdes des composants
                        cv2.circle(
                            vis_connections,
                            (comp1["centroid"]["x"], comp1["centroid"]["y"]),
                            5, (255, 0, 0), -1  # Rouge
                        )
                        cv2.circle(
                            vis_connections,
                            (comp2["centroid"]["x"], comp2["centroid"]["y"]),
                            5, (255, 0, 0), -1  # Rouge
                        )
                
                # Sauvegarder l'image
                connections_path = os.path.join(temp_dir, f"{prefix}connections.png")
                cv2.imwrite(connections_path, vis_connections)
                visualizations[connections_path] = "Connections visualization"
            
            # Visualisation complète
            vis_complete = image.copy()
            
            # Dessiner les composants
            for comp in components:
                bbox = comp["bounding_box"]
                x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                
                # Couleur selon le type
                color = (0, 255, 0)  # Vert par défaut
                
                # Si le composant est associé à un symbole, utiliser une couleur différente
                symbol = next((s for s in symbols if s["component_id"] == comp["id"]), None)
                if symbol:
                    color = (255, 0, 255)  # Magenta pour les symboles reconnus
                
                # Dessiner le rectangle
                cv2.rectangle(vis_complete, (x, y), (x + w, y + h), color, 2)
                
                # Ajouter l'ID et le type
                label = f"{comp['id']}"
                if symbol:
                    label += f": {symbol['type']}"
                cv2.putText(vis_complete, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Dessiner les lignes
            for line in structure.get("lines", []):
                cv2.line(
                    vis_complete,
                    (line["start"]["x"], line["start"]["y"]),
                    (line["end"]["x"], line["end"]["y"]),
                    (0, 255, 0),  # Vert
                    1
                )
            
            # Dessiner les annotations textuelles
            for anno in text_annotations:
                bbox = anno["bounding_box"]
                x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                
                # Dessiner le rectangle
                cv2.rectangle(vis_complete, (x, y), (x + w, y + h), (0, 255, 255), 1)  # Jaune
            
            # Dessiner les sous-systèmes
            for subsystem in structure.get("subsystems", []):
                bbox = subsystem["bounding_box"]
                x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                
                # Dessiner le rectangle avec une ligne pointillée
                pts = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(vis_complete, [pts], True, (255, 165, 0), 2, cv2.LINE_AA)  # Orange
                
                # Ajouter l'ID du sous-système
                cv2.putText(
                    vis_complete, 
                    f"Subsystem {subsystem['id']}", 
                    (x, y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.7, 
                    (255, 165, 0),  # Orange
                    2
                )
            
            # Sauvegarder l'image
            complete_path = os.path.join(temp_dir, f"{prefix}complete_analysis.png")
            cv2.imwrite(complete_path, vis_complete)
            visualizations[complete_path] = "Complete analysis visualization"
            
            return visualizations
            
        except Exception as e:
            logger.exception(f"Erreur lors de la génération des visualisations: {str(e)}")
            return {}

    def _is_likely_schema(self, components, text_annotations, symbols, structure):
        """
        Détermine si l'image analysée contient probablement un schéma technique.
        
        Args:
            components: Composants détectés
            text_annotations: Annotations textuelles
            symbols: Symboles reconnus
            structure: Structure du schéma
            
        Returns:
            True si l'image contient probablement un schéma technique
        """
        # Vérifier le nombre de composants
        if len(components) < 3:
            return False
        
        # Vérifier le nombre de connexions
        connections = structure.get("connections", [])
        if len(connections) < 1:
            return False
        
        # Vérifier si des symboles techniques ont été reconnus
        if symbols and len(symbols) > 0:
            return True
        
        # Vérifier les formes géométriques typiques des schémas techniques
        geometric_shapes = 0
        for comp in components:
            if comp["type"] in ["circle", "rectangle", "triangle", "polygon_5", "polygon_6"]:
                geometric_shapes += 1
        
        if geometric_shapes >= 3:
            return True
        
        # Vérifier si certains mots-clés techniques sont présents dans les annotations
        technical_terms = ["circuit", "schema", "diagram", "schéma", "électrique", "electronic", 
                          "composant", "component", "signal", "power", "puissance", "voltage", 
                          "courant", "current", "resistance", "capacité", "capacitance"]
        
        for anno in text_annotations:
            if any(term in anno["text"].lower() for term in technical_terms):
                return True
        
        # Si de nombreuses lignes droites sont présentes, c'est un bon indicateur
        lines = structure.get("lines", [])
        if len(lines) > 10:
            return True
        
        # Par défaut, être conservateur
        return False
    
    def _calculate_avg_confidence(self, components, symbols):
        """
        Calcule la confiance moyenne pour les éléments détectés.
        
        Args:
            components: Composants détectés
            symbols: Symboles reconnus
            
        Returns:
            Score de confiance moyen
        """
        if not components:
            return 0.0
        
        # Confiance des composants
        component_confidences = [comp.get("confidence", 0.0) for comp in components]
        avg_component_confidence = sum(component_confidences) / len(component_confidences) if component_confidences else 0.0
        
        # Confiance des symboles
        symbol_confidences = [symbol.get("confidence", 0.0) for symbol in symbols]
        avg_symbol_confidence = sum(symbol_confidences) / len(symbol_confidences) if symbol_confidences else 0.0
        
        # Pondérer la confiance globale
        if symbols:
            # Si des symboles ont été reconnus, leur donner plus de poids
            return 0.4 * avg_component_confidence + 0.6 * avg_symbol_confidence
        else:
            return avg_component_confidence
    
    def _estimate_schema_complexity(self, components, text_annotations, symbols, structure):
        """
        Estime la complexité d'un schéma technique.
        
        Args:
            components: Composants détectés
            text_annotations: Annotations textuelles
            symbols: Symboles reconnus
            structure: Structure du schéma
            
        Returns:
            Score de complexité (0-100)
        """
        score = 0
        
        # Facteur basé sur le nombre de composants
        component_factor = min(50, len(components)) / 50.0  # Normaliser jusqu'à 50 composants maximum
        score += 30 * component_factor
        
        # Facteur basé sur le nombre de connexions
        connections = structure.get("connections", [])
        connection_factor = min(100, len(connections)) / 100.0  # Normaliser jusqu'à 100 connexions maximum
        score += 25 * connection_factor
        
        # Facteur basé sur le nombre de symboles reconnus
        symbol_factor = min(20, len(symbols)) / 20.0  # Normaliser jusqu'à 20 symboles maximum
        score += 20 * symbol_factor
        
        # Facteur basé sur le nombre d'annotations textuelles
        text_factor = min(30, len(text_annotations)) / 30.0  # Normaliser jusqu'à 30 annotations maximum
        score += 15 * text_factor
        
        # Facteur basé sur le nombre de sous-systèmes
        subsystems = structure.get("subsystems", [])
        subsystem_factor = min(10, len(subsystems)) / 10.0  # Normaliser jusqu'à 10 sous-systèmes maximum
        score += 10 * subsystem_factor
        
        # Limiter entre 0 et 100
        return min(100, max(0, score))
    
    def _generate_schema_description(self, components, text_annotations, symbols, structure):
        """
        Génère une description textuelle du schéma analysé.
        
        Args:
            components: Composants détectés
            text_annotations: Annotations textuelles
            symbols: Symboles reconnus
            structure: Structure du schéma
            
        Returns:
            Description textuelle du schéma
        """
        # Cas où aucun composant n'est détecté
        if not components:
            return "Aucun composant de schéma technique détecté dans l'image."
        
        # Compter les différents types d'éléments
        component_types = {}
        for comp in components:
            component_type = comp["type"]
            component_types[component_type] = component_types.get(component_type, 0) + 1
        
        symbol_types = {}
        for symbol in symbols:
            symbol_type = symbol["type"]
            symbol_types[symbol_type] = symbol_types.get(symbol_type, 0) + 1
        
        # Compter les connexions
        connections = structure.get("connections", [])
        
        # Générer une description générale
        description_parts = []
        
        # Description du type de schéma
        if symbols:
            if any(s in symbol_types for s in ["resistor", "capacitor", "diode", "transistor"]):
                description_parts.append("Schéma électronique détecté.")
            elif any(s in symbol_types for s in ["motor", "battery", "switch"]):
                description_parts.append("Schéma électrique détecté.")
            else:
                description_parts.append("Schéma technique détecté.")
        else:
            description_parts.append("Diagramme technique détecté.")
        
        # Description des composants
        component_description = "Composants détectés : "
        component_parts = []
        
        for comp_type, count in component_types.items():
            comp_name = comp_type
            if comp_type == "circle":
                comp_name = "cercles"
            elif comp_type == "rectangle":
                comp_name = "rectangles"
            elif comp_type == "triangle":
                comp_name = "triangles"
            elif comp_type.startswith("polygon_"):
                vertices = comp_type.split("_")[1]
                comp_name = f"polygones à {vertices} sommets"
            
            component_parts.append(f"{count} {comp_name}")
        
        component_description += ", ".join(component_parts) + "."
        description_parts.append(component_description)
        
        # Description des symboles reconnus
        if symbols:
            symbol_description = "Symboles techniques identifiés : "
            symbol_parts = []
            
            symbol_names = {
                "resistor": "résistances",
                "capacitor": "condensateurs",
                "transistor": "transistors",
                "diode": "diodes",
                "battery": "batteries",
                "switch": "interrupteurs",
                "led": "LEDs",
                "connector": "connecteurs",
                "inductor": "inductances",
                "motor": "moteurs"
            }
            
            for sym_type, count in symbol_types.items():
                sym_name = symbol_names.get(sym_type, sym_type)
                symbol_parts.append(f"{count} {sym_name}")
            
            symbol_description += ", ".join(symbol_parts) + "."
            description_parts.append(symbol_description)
        
        # Description des connexions
        if connections:
            description_parts.append(f"{len(connections)} connexions entre composants identifiées.")
        
        # Description des annotations textuelles
        if text_annotations:
            # Regrouper les annotations par type
            annotation_types = {}
            for anno in text_annotations:
                anno_type = anno["type"]
                annotation_types[anno_type] = annotation_types.get(anno_type, 0) + 1
            
            anno_description = "Textes détectés : "
            anno_parts = []
            
            anno_names = {
                "label": "étiquettes",
                "reference": "références",
                "number": "valeurs numériques",
                "unit": "unités de mesure",
                "note": "notes"
            }
            
            for anno_type, count in annotation_types.items():
                anno_name = anno_names.get(anno_type, anno_type)
                anno_parts.append(f"{count} {anno_name}")
            
            anno_description += ", ".join(anno_parts) + "."
            description_parts.append(anno_description)
        
        # Description des sous-systèmes
        subsystems = structure.get("subsystems", [])
        if subsystems:
            description_parts.append(f"{len(subsystems)} sous-systèmes ou groupes fonctionnels identifiés.")
        
        # Joindre toutes les parties de la description
        return "\n".join(description_parts)
