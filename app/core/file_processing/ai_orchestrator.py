"""
Module d'orchestration combinant Document AI et Vision AI.
Ce module coordonne l'utilisation des processeurs Document AI et Vision AI
pour optimiser l'extraction et l'analyse des documents techniques.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import logging
import tempfile
import shutil
from datetime import datetime
import json

from .ocr.base import OCRProcessor, OCRResult
from .ocr.document_ai import DocumentAIProcessor
from ..image_processing.vision_ai import VisionAIService, VisionAnalysisResult

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Orchestrateur qui combine Document AI et Vision AI pour une analyse complète des documents.
    
    Cette classe coordonne l'utilisation de Google Cloud Document AI et Vision AI
    pour optimiser l'extraction de texte et l'analyse d'images dans les documents techniques.
    Elle détermine intelligemment quand utiliser chaque service et fusionne les résultats.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'orchestrateur AI.
        
        Args:
            config: Configuration de l'orchestrateur
                - document_ai_config: Configuration pour Document AI
                - vision_ai_config: Configuration pour Vision AI
                - extract_images: Extraire les images des documents pour analyse (défaut: True)
                - image_min_size: Taille minimale des images à extraire en pixels (défaut: 200x200)
                - confidence_threshold: Seuil de confiance pour les résultats (défaut: 0.7)
        """
        self.config = config or {}
        self.document_ai = DocumentAIProcessor(self.config.get("document_ai_config", {}))
        self.vision_ai = VisionAIService(self.config.get("vision_ai_config", {}))
        
        self.extract_images = self.config.get("extract_images", True)
        self.image_min_size = self.config.get("image_min_size", (200, 200))
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        
        self.initialized = False
        
    async def initialize(self) -> bool:
        """
        Initialise les processeurs Document AI et Vision AI.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        try:
            # Initialiser Document AI
            doc_ai_init = await self.document_ai.initialize()
            
            # Initialiser Vision AI
            vision_ai_init = await self.vision_ai.initialize()
            
            # L'orchestrateur est considéré comme initialisé si au moins un des services est disponible
            self.initialized = doc_ai_init or vision_ai_init
            
            if not self.initialized:
                logger.error("Échec d'initialisation des services AI")
                return False
                
            logger.info(f"Orchestrateur AI initialisé. Document AI: {doc_ai_init}, Vision AI: {vision_ai_init}")
            return self.initialized
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'orchestrateur AI: {str(e)}")
            return False
    
    async def process_document(self, 
                        input_file: Union[str, Path],
                        output_dir: Optional[Union[str, Path]] = None,
                        language: str = "fra",
                        **kwargs) -> Dict[str, Any]:
        """
        Traite un document en orchestrant Document AI et Vision AI.
        
        Args:
            input_file: Chemin vers le fichier d'entrée
            output_dir: Répertoire de sortie pour les fichiers générés (optionnel)
            language: Code de langue pour l'OCR
            **kwargs: Options supplémentaires
                - force_extract_images: Forcer l'extraction d'images même pour les documents textuels
                - skip_vision_ai: Ne pas utiliser Vision AI, même pour les images
                - document_type: Type de document pour orienter l'analyse ('technical', 'text', 'mixed')
                
        Returns:
            Résultats combinés de l'analyse Document AI et Vision AI
        """
        if not self.initialized:
            logger.error("L'orchestrateur AI n'est pas initialisé")
            return {
                "success": False,
                "error_message": "L'orchestrateur AI n'est pas initialisé"
            }
        
        input_path = Path(input_file)
        
        if not input_path.exists():
            return {
                "success": False,
                "error_message": f"Le fichier d'entrée n'existe pas: {input_path}"
            }
        
        # Créer un répertoire temporaire de travail si output_dir n'est pas spécifié
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True, parents=True)
        else:
            temp_output_dir = tempfile.mkdtemp(prefix="ai_orchestrator_")
            output_path = Path(temp_output_dir)
        
        combined_results = {
            "success": False,
            "input_file": str(input_path),
            "output_dir": str(output_path),
            "document_ai_result": None,
            "vision_ai_results": [],
            "combined_text": "",
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "language": language,
                "has_images": False,
                "document_type": kwargs.get("document_type", "mixed")
            }
        }
        
        try:
            # Étape 1: Traiter avec Document AI pour extraire le texte
            if self.document_ai.is_initialized:
                document_ai_output = output_path / f"{input_path.stem}_document_ai{input_path.suffix}"
                
                document_ai_result = await self.document_ai.process_document(
                    input_file=input_path,
                    output_file=document_ai_output,
                    language=language,
                    **kwargs
                )
                
                combined_results["document_ai_result"] = document_ai_result.to_dict()
                combined_results["success"] = document_ai_result.success
                
                if document_ai_result.success:
                    combined_results["combined_text"] = document_ai_result.text_content
                    
                    # Évaluer si le document contient des images à analyser
                    has_images = document_ai_result.metadata.get("has_images", False)
                    combined_results["metadata"]["has_images"] = has_images
                    
                    # Extraire les images si nécessaire
                    extracted_images = []
                    if (self.extract_images and has_images) or kwargs.get("force_extract_images", False):
                        extracted_images = await self._extract_images_from_document(
                            input_path, 
                            document_ai_result, 
                            output_path
                        )
                        
                    # Étape 2: Analyser les images avec Vision AI si disponible
                    if self.vision_ai.initialized and extracted_images and not kwargs.get("skip_vision_ai", False):
                        vision_results = await self._process_images_with_vision_ai(
                            extracted_images, language
                        )
                        
                        combined_results["vision_ai_results"] = vision_results
                        
                        # Fusionner les résultats Vision AI avec le texte principal
                        for vision_result in vision_results:
                            if vision_result.get("success", False):
                                technical_text = self._extract_technical_text_from_vision(vision_result)
                                if technical_text:
                                    combined_results["combined_text"] += f"\n\n[IMAGE ANALYSIS]\n{technical_text}"
            
            # Si Document AI n'est pas disponible ou a échoué, mais que le fichier est une image
            elif self.vision_ai.initialized and input_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
                # Traiter directement avec Vision AI
                vision_result = await self.vision_ai.analyze_image(
                    image_path=input_path,
                    features=['text', 'label', 'object', 'symbol', 'technical_drawing']
                )
                
                combined_results["vision_ai_results"] = [vision_result.to_dict()]
                combined_results["success"] = vision_result.success
                
                if vision_result.success:
                    technical_text = self._extract_technical_text_from_vision(vision_result.to_dict())
                    combined_results["combined_text"] = technical_text
            
            # Sauvegarder le texte combiné dans un fichier texte
            text_output_path = output_path / f"{input_path.stem}_combined_text.txt"
            with open(text_output_path, "w", encoding="utf-8") as f:
                f.write(combined_results["combined_text"])
            
            # Sauvegarder les métadonnées complètes
            metadata_output_path = output_path / f"{input_path.stem}_metadata.json"
            with open(metadata_output_path, "w", encoding="utf-8") as f:
                json.dump(combined_results["metadata"], f, indent=2)
                
            logger.info(f"Traitement orchestré terminé pour {input_path}")
            return combined_results
            
        except Exception as e:
            logger.error(f"Erreur lors de l'orchestration AI: {str(e)}")
            combined_results["error_message"] = str(e)
            return combined_results
    
    async def _extract_images_from_document(self, 
                                    document_path: Path, 
                                    document_result: OCRResult,
                                    output_dir: Path) -> List[Path]:
        """
        Extrait les images d'un document.
        
        Args:
            document_path: Chemin vers le document
            document_result: Résultat de l'OCR
            output_dir: Répertoire de sortie pour les images
            
        Returns:
            Liste des chemins vers les images extraites
        """
        image_paths = []
        
        # Si Document AI a déjà extrait les images
        if document_result.metadata.get("images"):
            for idx, image_info in enumerate(document_result.metadata["images"]):
                if "content" in image_info:
                    # Décoder le contenu base64
                    try:
                        image_data = image_info["content"]
                        if isinstance(image_data, str):
                            import base64
                            image_data = base64.b64decode(image_data)
                            
                        image_path = output_dir / f"image_{idx}.png"
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                        
                        # Vérifier les dimensions minimales
                        from PIL import Image
                        with Image.open(image_path) as img:
                            width, height = img.size
                            if width >= self.image_min_size[0] and height >= self.image_min_size[1]:
                                image_paths.append(image_path)
                            else:
                                # Supprimer l'image trop petite
                                os.remove(image_path)
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'extraction d'une image: {str(e)}")
        
        # Si nous n'avons pas d'images et que le document est un PDF, essayer d'en extraire
        if not image_paths and document_path.suffix.lower() == ".pdf":
            try:
                from pdf2image import convert_from_path
                
                # Extraire les images du PDF
                images = convert_from_path(document_path)
                for idx, image in enumerate(images):
                    image_path = output_dir / f"page_{idx}.png"
                    image.save(image_path, "PNG")
                    
                    # Vérifier les dimensions minimales
                    width, height = image.size
                    if width >= self.image_min_size[0] and height >= self.image_min_size[1]:
                        image_paths.append(image_path)
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction d'images du PDF: {str(e)}")
        
        logger.info(f"Extraction d'images: {len(image_paths)} images extraites")
        return image_paths
    
    async def _process_images_with_vision_ai(self, 
                                     image_paths: List[Path],
                                     language: str) -> List[Dict[str, Any]]:
        """
        Traite une liste d'images avec Vision AI.
        
        Args:
            image_paths: Liste des chemins vers les images à analyser
            language: Code de langue pour l'analyse
            
        Returns:
            Liste des résultats d'analyse Vision AI
        """
        results = []
        
        for image_path in image_paths:
            try:
                # Analyser l'image avec Vision AI
                vision_result = await self.vision_ai.analyze_image(
                    image_path=image_path,
                    features=['text', 'label', 'object', 'symbol', 'technical_drawing']
                )
                
                results.append(vision_result.to_dict())
                
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse de l'image {image_path}: {str(e)}")
                results.append({
                    "success": False,
                    "image_path": str(image_path),
                    "error_message": str(e)
                })
        
        return results
    
    def _extract_technical_text_from_vision(self, vision_result: Dict[str, Any]) -> str:
        """
        Extrait le texte technique des résultats Vision AI.
        
        Args:
            vision_result: Résultat de l'analyse Vision AI
            
        Returns:
            Texte technique extrait
        """
        extracted_text = ""
        
        # Extraire le texte des annotations textuelles
        if vision_result.get("text_annotations") and len(vision_result["text_annotations"]) > 0:
            # Le premier élément contient généralement tout le texte trouvé dans l'image
            extracted_text += vision_result["text_annotations"][0].get("description", "")
        
        # Ajouter les informations sur les symboles techniques
        if vision_result.get("symbol_annotations"):
            symbol_info = "\n\n[SYMBOLES TECHNIQUES DÉTECTÉS]\n"
            for symbol in vision_result["symbol_annotations"]:
                symbol_info += f"- {symbol.get('description', 'Symbole inconnu')}\n"
            extracted_text += symbol_info
        
        # Ajouter les informations sur les objets techniques
        if vision_result.get("object_annotations"):
            object_info = "\n\n[OBJETS TECHNIQUES DÉTECTÉS]\n"
            for obj in vision_result["object_annotations"]:
                object_info += f"- {obj.get('name', 'Objet inconnu')} ({obj.get('score', 0):.2f})\n"
            extracted_text += object_info
        
        return extracted_text
