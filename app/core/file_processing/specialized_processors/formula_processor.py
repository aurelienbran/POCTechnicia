"""
Module de traitement des formules mathématiques et techniques.

Ce module fournit des fonctionnalités pour détecter et traiter des formules
mathématiques et techniques à partir de différents formats de documents.
Il permet d'extraire, de formater et d'interpréter des équations et des notations
scientifiques.
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

from .base import SpecializedProcessor, SpecializedProcessingResult

logger = logging.getLogger(__name__)

# Tentative d'importation des bibliothèques de traitement de formules
try:
    import sympy
    import latex2sympy2
    import pix2tex
    from PIL import Image
    FORMULA_LIBS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Certaines bibliothèques de traitement de formules ne sont pas disponibles: {str(e)}. "
                  "Installez-les avec: pip install sympy latex2sympy2 pix2tex pillow")
    FORMULA_LIBS_AVAILABLE = False


class FormulaProcessor(SpecializedProcessor):
    """
    Processeur spécialisé pour l'extraction et le traitement de formules mathématiques.
    
    Cette classe fournit des méthodes pour détecter, extraire et interpréter des
    formules mathématiques et techniques à partir de documents ou d'images.
    Elle utilise une combinaison de techniques OCR spécialisées et d'analyse
    symbolique pour traiter les notations scientifiques.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le processeur de formules.
        
        Args:
            config: Configuration du processeur
                - recognition_mode: Mode de reconnaissance ('text', 'image', 'auto')
                - confidence_threshold: Seuil de confiance pour la détection
                - format_preference: Format préféré pour les résultats ('tex', 'ascii', 'mathml')
                - simplify_expressions: Tenter de simplifier les expressions mathématiques
                - translate_to_text: Générer une description textuelle des formules
        """
        super().__init__(config)
        
        # Paramètres de configuration avec valeurs par défaut
        self.recognition_mode = self.config.get("recognition_mode", "auto")
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        self.format_preference = self.config.get("format_preference", "tex")
        self.simplify_expressions = self.config.get("simplify_expressions", True)
        self.translate_to_text = self.config.get("translate_to_text", True)
        
        # État d'initialisation des bibliothèques
        self.sympy_available = False
        self.latex2sympy_available = False
        self.pix2tex_available = False
        self.pix2tex_model = None
    
    async def initialize(self) -> bool:
        """
        Initialise le processeur de formules en vérifiant la disponibilité des dépendances.
        
        Returns:
            True si au moins une méthode de traitement est disponible, False sinon
        """
        if not FORMULA_LIBS_AVAILABLE:
            logger.error("Les bibliothèques de traitement de formules ne sont pas disponibles")
            return False
        
        try:
            # Vérifier SymPy
            import sympy
            self.sympy_available = True
            logger.info("SymPy est disponible pour le traitement symbolique")
            
            # Vérifier latex2sympy2
            try:
                import latex2sympy2
                self.latex2sympy_available = True
                logger.info("latex2sympy2 est disponible pour la conversion LaTeX->SymPy")
            except ImportError as e:
                logger.warning(f"latex2sympy2 n'est pas disponible: {str(e)}")
            
            # Vérifier pix2tex
            try:
                import pix2tex
                
                # Initialiser le modèle pix2tex (peut prendre un peu de temps)
                loop = asyncio.get_event_loop()
                self.pix2tex_model = await loop.run_in_executor(
                    None, 
                    lambda: pix2tex.cli.LatexOCR()
                )
                
                self.pix2tex_available = True
                logger.info("pix2tex est disponible pour la reconnaissance de formules dans les images")
            except Exception as e:
                logger.warning(f"pix2tex n'a pas pu être initialisé: {str(e)}")
                self.pix2tex_available = False
            
            # L'extracteur est considéré comme initialisé si au moins une méthode est disponible
            self.initialized = self.sympy_available or self.latex2sympy_available or self.pix2tex_available
            
            if not self.initialized:
                logger.error("Aucune méthode de traitement de formules n'est disponible")
                return False
                
            logger.info(f"Processeur de formules initialisé avec succès: "
                       f"SymPy={self.sympy_available}, "
                       f"latex2sympy={self.latex2sympy_available}, "
                       f"pix2tex={self.pix2tex_available}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du processeur de formules: {str(e)}")
            return False
    
    async def process(self, 
                document_path: Union[str, Path],
                page_number: Optional[int] = None,
                content_region: Optional[Dict[str, Any]] = None,
                **kwargs) -> SpecializedProcessingResult:
        """
        Traite un document pour en extraire des formules mathématiques.
        
        Args:
            document_path: Chemin vers le document contenant des formules
            page_number: Numéro de page à traiter (None pour toutes les pages)
            content_region: Région du document contenant la formule (coordonnées)
            **kwargs: Options supplémentaires
                - formula_text: Texte de formule déjà extrait (évite l'OCR)
                - recognition_mode: Mode de reconnaissance pour cette requête
                - output_format: Format de sortie pour les résultats
                - save_to_file: Sauvegarder les résultats dans un fichier
                - output_path: Chemin de sortie pour les fichiers sauvegardés
                
        Returns:
            Résultat du traitement de formules
        """
        if not self.is_initialized:
            logger.error("Le processeur de formules n'est pas initialisé")
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message="Le processeur de formules n'est pas initialisé",
                source_document=str(document_path),
                page_number=page_number
            )
        
        document_path = Path(document_path)
        
        # Vérifier si un texte de formule a été fourni directement
        formula_text = kwargs.get("formula_text")
        if formula_text:
            # Si un texte de formule est fourni, l'utiliser directement
            return await self._process_formula_text(
                formula_text, 
                str(document_path),
                page_number,
                **kwargs
            )
        
        if not document_path.exists():
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message=f"Le document n'existe pas: {document_path}",
                source_document=str(document_path),
                page_number=page_number
            )
        
        # Options spécifiques à cette requête
        recognition_mode = kwargs.get("recognition_mode", self.recognition_mode)
        
        try:
            # Déterminer le type de document
            document_type = document_path.suffix.lower()
            
            # Sélectionner la méthode de traitement selon le type de document
            if document_type in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']:
                # Traitement d'une image directement
                return await self._process_formula_image(
                    document_path,
                    content_region,
                    **kwargs
                )
            elif document_type == '.tex' or document_type == '.latex':
                # Traitement d'un fichier LaTeX directement
                return await self._process_latex_file(
                    document_path,
                    **kwargs
                )
            elif document_type == '.pdf':
                # Pour les PDF, la méthode dépend du mode de reconnaissance
                if recognition_mode == "text" or recognition_mode == "auto":
                    # Essayer d'abord l'extraction basée sur le texte
                    result = await self._extract_formulas_from_pdf_text(
                        document_path,
                        page_number,
                        content_region,
                        **kwargs
                    )
                    
                    # Si le mode est auto et que l'extraction de texte n'a pas donné de formules,
                    # essayer l'extraction basée sur l'image
                    if recognition_mode == "auto" and (not result.success or not result.extracted_data):
                        result = await self._extract_formulas_from_pdf_image(
                            document_path,
                            page_number,
                            content_region,
                            **kwargs
                        )
                    
                    return result
                else:  # Mode image
                    return await self._extract_formulas_from_pdf_image(
                        document_path,
                        page_number,
                        content_region,
                        **kwargs
                    )
            else:
                # Type de document non pris en charge
                return SpecializedProcessingResult(
                    success=False,
                    processor_name="FormulaProcessor",
                    content_type="formula",
                    error_message=f"Type de document non pris en charge: {document_type}",
                    source_document=str(document_path),
                    page_number=page_number
                )
            
        except Exception as e:
            logger.exception(f"Erreur lors du traitement de formules: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message=f"Erreur lors du traitement: {str(e)}",
                source_document=str(document_path),
                page_number=page_number
            )
    
    async def _process_formula_text(self,
                             formula_text: str,
                             source_document: str,
                             page_number: Optional[int] = None,
                             **kwargs) -> SpecializedProcessingResult:
        """
        Traite un texte de formule déjà extrait.
        
        Args:
            formula_text: Texte de la formule (LaTeX, ASCII, etc.)
            source_document: Document source
            page_number: Numéro de page
            **kwargs: Options supplémentaires
                
        Returns:
            Résultat du traitement de la formule
        """
        try:
            # Déterminer si le texte est du LaTeX, de l'ASCII, ou autre
            formula_type = self._detect_formula_type(formula_text)
            
            # Convertir au format souhaité et générer les métadonnées
            processed_formula = await self._convert_formula(
                formula_text, 
                formula_type,
                **kwargs
            )
            
            # Si la conversion a échoué
            if not processed_formula:
                return SpecializedProcessingResult(
                    success=False,
                    processor_name="FormulaProcessor",
                    content_type="formula",
                    error_message=f"Impossible de traiter la formule: {formula_text}",
                    source_document=source_document,
                    page_number=page_number
                )
            
            # Créer la description textuelle si demandé
            text_description = None
            if self.translate_to_text:
                text_description = await self._generate_formula_description(
                    formula_text,
                    processed_formula,
                    formula_type
                )
            
            # Préparer les métadonnées
            metadata = {
                "formula_type": formula_type,
                "has_variables": self._has_variables(processed_formula),
                "complexity": self._estimate_complexity(processed_formula)
            }
            
            # Retourner le résultat
            return SpecializedProcessingResult(
                success=True,
                processor_name="FormulaProcessor",
                content_type="formula",
                extracted_data=processed_formula,
                source_document=source_document,
                page_number=page_number,
                metadata=metadata,
                text_representation=text_description or formula_text
            )
            
        except Exception as e:
            logger.exception(f"Erreur lors du traitement du texte de formule: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message=f"Erreur lors du traitement du texte: {str(e)}",
                source_document=source_document,
                page_number=page_number,
                text_representation=formula_text
            )

    async def _process_formula_image(self,
                              image_path: Path,
                              content_region: Optional[Dict[str, Any]] = None,
                              **kwargs) -> SpecializedProcessingResult:
        """
        Traite une image contenant une formule mathématique.
        
        Args:
            image_path: Chemin vers l'image
            content_region: Région de l'image contenant la formule
            **kwargs: Options supplémentaires
                
        Returns:
            Résultat du traitement de la formule
        """
        if not self.pix2tex_available:
            logger.error("pix2tex n'est pas disponible pour la reconnaissance d'images")
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message="pix2tex n'est pas disponible pour la reconnaissance d'images",
                source_document=str(image_path)
            )
        
        try:
            loop = asyncio.get_event_loop()
            
            # Charger l'image
            image = await loop.run_in_executor(
                None,
                lambda: Image.open(image_path)
            )
            
            # Recadrer l'image si une région est spécifiée
            if content_region:
                x1 = content_region.get("x1", 0)
                y1 = content_region.get("y1", 0)
                x2 = content_region.get("x2", image.width)
                y2 = content_region.get("y2", image.height)
                
                image = image.crop((x1, y1, x2, y2))
            
            # Utiliser pix2tex pour reconnaître la formule
            latex_formula = await loop.run_in_executor(
                None,
                lambda: self.pix2tex_model(image)
            )
            
            # Si la reconnaissance a échoué
            if not latex_formula:
                return SpecializedProcessingResult(
                    success=False,
                    processor_name="FormulaProcessor",
                    content_type="formula",
                    error_message="Impossible de reconnaître une formule dans l'image",
                    source_document=str(image_path)
                )
            
            # Traiter la formule LaTeX extraite
            return await self._process_formula_text(
                latex_formula,
                str(image_path),
                None,
                **kwargs
            )
            
        except Exception as e:
            logger.exception(f"Erreur lors du traitement de l'image: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message=f"Erreur lors du traitement de l'image: {str(e)}",
                source_document=str(image_path)
            )
    
    async def _process_latex_file(self,
                           latex_file: Path,
                           **kwargs) -> SpecializedProcessingResult:
        """
        Traite un fichier LaTeX pour en extraire des formules.
        
        Args:
            latex_file: Chemin vers le fichier LaTeX
            **kwargs: Options supplémentaires
                
        Returns:
            Résultat du traitement des formules
        """
        try:
            # Lire le contenu du fichier
            with open(latex_file, 'r', encoding='utf-8') as f:
                latex_content = f.read()
            
            # Extraire les formules du texte LaTeX
            formulas = self._extract_latex_formulas(latex_content)
            
            if not formulas:
                return SpecializedProcessingResult(
                    success=True,  # Succès technique même si aucune formule n'est trouvée
                    processor_name="FormulaProcessor",
                    content_type="formula",
                    extracted_data={"formulas": []},
                    source_document=str(latex_file),
                    metadata={"formulas_count": 0},
                    text_representation="Aucune formule détectée dans le document."
                )
            
            # Traiter chaque formule
            processed_formulas = []
            for formula in formulas:
                processed = await self._convert_formula(
                    formula,
                    "latex",
                    **kwargs
                )
                
                if processed:
                    # Générer une description textuelle si demandé
                    text_description = None
                    if self.translate_to_text:
                        text_description = await self._generate_formula_description(
                            formula,
                            processed,
                            "latex"
                        )
                    
                    processed["original"] = formula
                    processed["text_description"] = text_description
                    processed_formulas.append(processed)
            
            # Préparer la représentation textuelle
            text_representation = "\n\n".join([
                f"[FORMULE {i+1}]\n{f.get('original', '')}\n{f.get('text_description', '')}"
                for i, f in enumerate(processed_formulas)
            ])
            
            # Préparer les métadonnées
            metadata = {
                "formulas_count": len(processed_formulas),
                "document_type": "latex",
                "complexity_avg": sum(self._estimate_complexity(f) for f in processed_formulas) / len(processed_formulas) if processed_formulas else 0
            }
            
            # Retourner le résultat
            return SpecializedProcessingResult(
                success=True,
                processor_name="FormulaProcessor",
                content_type="formula",
                extracted_data={"formulas": processed_formulas},
                source_document=str(latex_file),
                metadata=metadata,
                text_representation=text_representation
            )
            
        except Exception as e:
            logger.exception(f"Erreur lors du traitement du fichier LaTeX: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message=f"Erreur lors du traitement du fichier LaTeX: {str(e)}",
                source_document=str(latex_file)
            )
    
    async def _extract_formulas_from_pdf_text(self,
                                       document_path: Path,
                                       page_number: Optional[int] = None,
                                       content_region: Optional[Dict[str, Any]] = None,
                                       **kwargs) -> SpecializedProcessingResult:
        """
        Extrait des formules à partir du texte d'un PDF.
        
        Args:
            document_path: Chemin vers le document PDF
            page_number: Numéro de page à traiter
            content_region: Région du document contenant les formules
            **kwargs: Options supplémentaires
                
        Returns:
            Résultat de l'extraction de formules
        """
        try:
            # Extraire le texte du PDF
            import PyPDF2
            
            with open(document_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Déterminer les pages à traiter
                if page_number is not None:
                    pages = [min(page_number, len(pdf_reader.pages) - 1)]
                else:
                    pages = range(len(pdf_reader.pages))
                
                # Extraire le texte de chaque page
                text_content = ""
                for page_idx in pages:
                    text_content += pdf_reader.pages[page_idx].extract_text() + "\n\n"
            
            # Si aucun texte n'a été extrait
            if not text_content.strip():
                return SpecializedProcessingResult(
                    success=False,
                    processor_name="FormulaProcessor",
                    content_type="formula",
                    error_message="Aucun texte n'a pu être extrait du PDF",
                    source_document=str(document_path),
                    page_number=page_number
                )
            
            # Chercher des formules dans le texte
            potential_formulas = self._extract_potential_formulas(text_content)
            
            if not potential_formulas:
                return SpecializedProcessingResult(
                    success=True,  # Succès technique même si aucune formule n'est trouvée
                    processor_name="FormulaProcessor",
                    content_type="formula",
                    extracted_data={"formulas": []},
                    source_document=str(document_path),
                    page_number=page_number,
                    metadata={"formulas_count": 0},
                    text_representation="Aucune formule détectée dans le document."
                )
            
            # Traiter chaque formule potentielle
            processed_formulas = []
            for formula in potential_formulas:
                formula_type = self._detect_formula_type(formula)
                
                processed = await self._convert_formula(
                    formula,
                    formula_type,
                    **kwargs
                )
                
                if processed:
                    # Générer une description textuelle si demandé
                    text_description = None
                    if self.translate_to_text:
                        text_description = await self._generate_formula_description(
                            formula,
                            processed,
                            formula_type
                        )
                    
                    processed["original"] = formula
                    processed["formula_type"] = formula_type
                    processed["text_description"] = text_description
                    processed_formulas.append(processed)
            
            # Préparer la représentation textuelle
            text_representation = "\n\n".join([
                f"[FORMULE {i+1}]\n{f.get('original', '')}\n{f.get('text_description', '')}"
                for i, f in enumerate(processed_formulas)
            ])
            
            # Préparer les métadonnées
            metadata = {
                "formulas_count": len(processed_formulas),
                "document_type": "pdf",
                "extraction_method": "text",
                "page_count": len(pages),
                "complexity_avg": sum(self._estimate_complexity(f) for f in processed_formulas) / len(processed_formulas) if processed_formulas else 0
            }
            
            # Retourner le résultat
            return SpecializedProcessingResult(
                success=True,
                processor_name="FormulaProcessor",
                content_type="formula",
                extracted_data={"formulas": processed_formulas},
                source_document=str(document_path),
                page_number=page_number if len(pages) == 1 else None,
                metadata=metadata,
                text_representation=text_representation
            )
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'extraction de formules du PDF: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message=f"Erreur lors de l'extraction: {str(e)}",
                source_document=str(document_path),
                page_number=page_number
            )
    
    async def _extract_formulas_from_pdf_image(self,
                                        document_path: Path,
                                        page_number: Optional[int] = None,
                                        content_region: Optional[Dict[str, Any]] = None,
                                        **kwargs) -> SpecializedProcessingResult:
        """
        Extrait des formules à partir des images d'un PDF.
        
        Args:
            document_path: Chemin vers le document PDF
            page_number: Numéro de page à traiter
            content_region: Région du document contenant les formules
            **kwargs: Options supplémentaires
                
        Returns:
            Résultat de l'extraction de formules
        """
        if not self.pix2tex_available:
            logger.error("pix2tex n'est pas disponible pour la reconnaissance d'images")
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message="pix2tex n'est pas disponible pour la reconnaissance d'images",
                source_document=str(document_path),
                page_number=page_number
            )
        
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
                    processor_name="FormulaProcessor",
                    content_type="formula",
                    error_message="Impossible de convertir le PDF en images",
                    source_document=str(document_path),
                    page_number=page_number
                )
            
            # Traiter chaque image pour en extraire des formules
            processed_formulas = []
            page_formulas = {}
            
            for idx, image in enumerate(images):
                current_page = page_number if page_number is not None else idx
                
                # Recadrer l'image si une région est spécifiée
                if content_region:
                    x1 = content_region.get("x1", 0)
                    y1 = content_region.get("y1", 0)
                    x2 = content_region.get("x2", image.width)
                    y2 = content_region.get("y2", image.height)
                    
                    image = image.crop((x1, y1, x2, y2))
                
                # Sauvegarder l'image temporairement pour la traiter
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    image_path = tmp.name
                    image.save(image_path, "PNG")
                
                # Utiliser pix2tex pour reconnaître des formules
                try:
                    latex_formula = await loop.run_in_executor(
                        None,
                        lambda: self.pix2tex_model(image)
                    )
                    
                    if latex_formula:
                        # Traiter la formule LaTeX reconnue
                        processed = await self._convert_formula(
                            latex_formula,
                            "latex",
                            **kwargs
                        )
                        
                        if processed:
                            # Générer une description textuelle si demandé
                            text_description = None
                            if self.translate_to_text:
                                text_description = await self._generate_formula_description(
                                    latex_formula,
                                    processed,
                                    "latex"
                                )
                            
                            processed["original"] = latex_formula
                            processed["page"] = current_page
                            processed["text_description"] = text_description
                            processed_formulas.append(processed)
                            
                            # Associer la formule à sa page
                            if current_page not in page_formulas:
                                page_formulas[current_page] = []
                            page_formulas[current_page].append(processed)
                except Exception as e:
                    logger.warning(f"Erreur lors de la reconnaissance de formule sur la page {current_page}: {str(e)}")
                
                # Supprimer le fichier temporaire
                try:
                    os.unlink(image_path)
                except Exception:
                    pass
            
            if not processed_formulas:
                return SpecializedProcessingResult(
                    success=True,  # Succès technique même si aucune formule n'est trouvée
                    processor_name="FormulaProcessor",
                    content_type="formula",
                    extracted_data={"formulas": []},
                    source_document=str(document_path),
                    page_number=page_number,
                    metadata={"formulas_count": 0},
                    text_representation="Aucune formule détectée dans le document."
                )
            
            # Préparer la représentation textuelle
            text_parts = []
            for page, formulas in sorted(page_formulas.items()):
                text_parts.append(f"[PAGE {page+1}]")
                for i, formula in enumerate(formulas):
                    text_parts.append(f"[FORMULE {i+1}]\n{formula.get('original', '')}")
                    if formula.get('text_description'):
                        text_parts.append(formula['text_description'])
                    text_parts.append("")
            
            text_representation = "\n".join(text_parts)
            
            # Préparer les métadonnées
            metadata = {
                "formulas_count": len(processed_formulas),
                "document_type": "pdf",
                "extraction_method": "image",
                "page_count": len(images),
                "pages_with_formulas": len(page_formulas),
                "complexity_avg": sum(self._estimate_complexity(f) for f in processed_formulas) / len(processed_formulas) if processed_formulas else 0
            }
            
            # Retourner le résultat
            return SpecializedProcessingResult(
                success=True,
                processor_name="FormulaProcessor",
                content_type="formula",
                extracted_data={"formulas": processed_formulas},
                source_document=str(document_path),
                page_number=page_number if len(images) == 1 else None,
                metadata=metadata,
                text_representation=text_representation
            )
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'extraction de formules du PDF: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="FormulaProcessor",
                content_type="formula",
                error_message=f"Erreur lors de l'extraction: {str(e)}",
                source_document=str(document_path),
                page_number=page_number
            )

    def _detect_formula_type(self, text: str) -> str:
        """
        Détecte le type de formule (LaTeX, ASCII, etc.).
        
        Args:
            text: Texte de la formule
            
        Returns:
            Type de formule détecté ('latex', 'ascii', 'mathml', 'unknown')
        """
        # Nettoyer le texte
        text = text.strip()
        
        # Caractéristiques LaTeX
        if text.startswith('\\') or '\\frac' in text or '\\sum' in text or '\\int' in text or \
           '\\alpha' in text or '\\beta' in text or '\\gamma' in text or \
           '\\begin{equation}' in text or '\\end{equation}' in text or \
           '\\begin{align}' in text or '\\end{align}' in text or \
           '$' in text or '\\[' in text or '\\]' in text:
            return 'latex'
        
        # Caractéristiques MathML
        if text.startswith('<math') or '<mi>' in text or '<mo>' in text or '<mn>' in text:
            return 'mathml'
        
        # Caractéristiques ASCII - vérifier la présence d'opérateurs mathématiques ASCII courants
        ascii_operators = ['+', '-', '*', '/', '=', '^', '_', 'sqrt', 'sum', 'sin', 'cos', 'tan', 'log']
        if any(op in text for op in ascii_operators) and not any(c in text for c in ['<', '>']):
            return 'ascii'
        
        # Par défaut, supposer un format inconnu
        return 'unknown'
    
    def _extract_latex_formulas(self, latex_content: str) -> List[str]:
        """
        Extrait les formules d'un document LaTeX.
        
        Args:
            latex_content: Contenu LaTeX
            
        Returns:
            Liste des formules extraites
        """
        formulas = []
        
        # Rechercher des environnements d'équation
        env_patterns = [
            (r'\\begin\{equation\}(.*?)\\end\{equation\}', r'\1'),
            (r'\\begin\{equation\*\}(.*?)\\end\{equation\*\}', r'\1'),
            (r'\\begin\{align\}(.*?)\\end\{align\}', r'\1'),
            (r'\\begin\{align\*\}(.*?)\\end\{align\*\}', r'\1'),
            (r'\\begin\{eqnarray\}(.*?)\\end\{eqnarray\}', r'\1'),
            (r'\\begin\{eqnarray\*\}(.*?)\\end\{eqnarray\*\}', r'\1'),
            (r'\\begin\{gather\}(.*?)\\end\{gather\}', r'\1'),
            (r'\\begin\{gather\*\}(.*?)\\end\{gather\*\}', r'\1'),
            (r'\\begin\{multline\}(.*?)\\end\{multline\}', r'\1'),
            (r'\\begin\{multline\*\}(.*?)\\end\{multline\*\}', r'\1')
        ]
        
        for pattern, replacement in env_patterns:
            matches = re.finditer(pattern, latex_content, re.DOTALL)
            for match in matches:
                formula = match.group(0)
                formulas.append(formula)
        
        # Rechercher des formules inline delimitées par $...$
        dollar_pattern = r'\$(.*?)\$'
        matches = re.finditer(dollar_pattern, latex_content)
        for match in matches:
            # Éviter les cas où $ est utilisé pour des devises, etc.
            formula = match.group(0)
            if len(formula) > 2 and any(op in formula for op in ['\\', '{', '}', '^', '_']):
                formulas.append(formula)
        
        # Rechercher des formules delimitées par \[...\]
        bracket_pattern = r'\\\[(.*?)\\\]'
        matches = re.finditer(bracket_pattern, latex_content, re.DOTALL)
        for match in matches:
            formula = match.group(0)
            formulas.append(formula)
        
        # Rechercher des formules delimitées par \(...\)
        paren_pattern = r'\\\((.*?)\\\)'
        matches = re.finditer(paren_pattern, latex_content)
        for match in matches:
            formula = match.group(0)
            formulas.append(formula)
        
        return formulas
    
    def _extract_potential_formulas(self, text: str) -> List[str]:
        """
        Extrait des formules potentielles d'un texte brut.
        
        Args:
            text: Texte source
            
        Returns:
            Liste des formules potentielles
        """
        # Motifs pour différents types de formules
        patterns = [
            # LaTeX inline et bloc
            r'\$(.*?)\$',
            r'\$\$(.*?)\$\$',
            r'\\\[(.*?)\\\]',
            r'\\\((.*?)\\\)',
            
            # Équations LaTeX
            r'\\begin\{equation\}(.*?)\\end\{equation\}',
            r'\\begin\{equation\*\}(.*?)\\end\{equation\*\}',
            r'\\begin\{align\}(.*?)\\end\{align\}',
            r'\\begin\{align\*\}(.*?)\\end\{align\*\}',
            
            # MathML simplifié
            r'<math.*?>(.*?)</math>',
            
            # Formules ASCII potentielles
            r'([a-zA-Z0-9]+[\+\-\*/\^\=]+[a-zA-Z0-9\(\)]+)'
        ]
        
        potential_formulas = []
        
        for pattern in patterns:
            # Utiliser re.DOTALL pour que le point capture également les sauts de ligne
            flag = re.DOTALL if '{' in pattern or '}' in pattern or '\\[' in pattern else 0
            matches = re.finditer(pattern, text, flag)
            
            for match in matches:
                formula = match.group(0)
                
                # Filtrer les faux positifs évidents
                if formula.startswith('$') and formula.endswith('$'):
                    # Éviter les références à des montants (ex: $10)
                    if len(formula) > 2 and not formula[1:].strip().isdigit():
                        potential_formulas.append(formula)
                else:
                    potential_formulas.append(formula)
        
        return potential_formulas
        
    async def _convert_formula(self,
                        formula: str,
                        formula_type: str,
                        **kwargs) -> Optional[Dict[str, Any]]:
        """
        Convertit une formule dans le format souhaité.
        
        Args:
            formula: Texte de la formule
            formula_type: Type de formule ('latex', 'ascii', 'mathml', 'unknown')
            **kwargs: Options supplémentaires
                - output_format: Format de sortie souhaité
                - simplify: Simplifier la formule si possible
                
        Returns:
            Formule convertie avec des métadonnées ou None si la conversion a échoué
        """
        output_format = kwargs.get("output_format", self.format_preference)
        simplify = kwargs.get("simplify", self.simplify_expressions)
        
        loop = asyncio.get_event_loop()
        
        result = {
            "original_type": formula_type,
            "output_type": output_format,
            "original": formula
        }
        
        try:
            # Si la formule est du LaTeX et que nous avons SymPy disponible
            if formula_type == 'latex' and self.latex2sympy_available and self.sympy_available:
                # Nettoyer la formule pour la conversion
                clean_formula = self._clean_latex_formula(formula)
                
                if clean_formula:
                    try:
                        # Convertir de LaTeX à expression SymPy
                        sympy_expr = await loop.run_in_executor(
                            None,
                            lambda: latex2sympy2.latex2sympy(clean_formula)
                        )
                        
                        # Simplifier si demandé
                        if simplify:
                            sympy_expr = await loop.run_in_executor(
                                None,
                                lambda: sympy.simplify(sympy_expr)
                            )
                        
                        # Reconvertir dans les formats demandés
                        ascii_repr = str(sympy_expr)
                        result["sympy"] = ascii_repr
                        
                        # Générer des représentations supplémentaires
                        if output_format == 'tex' or output_format == 'latex':
                            latex_repr = await loop.run_in_executor(
                                None,
                                lambda: sympy.latex(sympy_expr)
                            )
                            result["latex"] = latex_repr
                        
                        if output_format == 'mathml':
                            mathml_repr = await loop.run_in_executor(
                                None,
                                lambda: sympy.printing.mathml(sympy_expr)
                            )
                            result["mathml"] = mathml_repr
                        
                        result["variables"] = self._extract_variables(sympy_expr)
                        result["converted"] = True
                        
                    except Exception as e:
                        logger.warning(f"Erreur lors de la conversion LaTeX->SymPy: {str(e)}")
                        result["converted"] = False
                        result[output_format] = clean_formula
            
            # Si conversion SymPy a échoué ou n'est pas disponible
            if formula_type == 'latex' and not result.get("converted", False):
                # Assurer que nous avons au moins une représentation LaTeX
                clean_formula = self._clean_latex_formula(formula)
                result["latex"] = clean_formula or formula
                result["converted"] = False
            
            if formula_type == 'ascii':
                result["ascii"] = formula
                
                # Essayer de convertir en LaTeX si demandé
                if output_format == 'tex' or output_format == 'latex':
                    # Conversion très basique d'ASCII à LaTeX
                    latex_repr = formula.replace('^', '^{').replace('_', '_{')
                    if '^{' in latex_repr:
                        latex_repr = latex_repr.replace('^{', '^{') + '}'
                    if '_{' in latex_repr:
                        latex_repr = latex_repr.replace('_{', '_{') + '}'
                    
                    result["latex"] = latex_repr
            
            if formula_type == 'mathml':
                result["mathml"] = formula
                
                # Si nous avons SymPy, essayer de convertir MathML en LaTeX
                if self.sympy_available and output_format in ['tex', 'latex']:
                    try:
                        # TODO: Conversion MathML->LaTeX (nécessite une bibliothèque supplémentaire)
                        # Pour l'instant, retourner le MathML tel quel
                        result["latex"] = formula
                    except Exception:
                        result["latex"] = formula
            
            return result
            
        except Exception as e:
            logger.exception(f"Erreur lors de la conversion de formule: {str(e)}")
            return None

    def _clean_latex_formula(self, formula: str) -> Optional[str]:
        """
        Nettoie une formule LaTeX pour la conversion.
        
        Args:
            formula: Formule LaTeX brute
            
        Returns:
            Formule nettoyée ou None si la formule n'est pas valide
        """
        # Supprimer les environnements LaTeX
        formula = re.sub(r'\\begin\{equation\*?\}|\\end\{equation\*?\}', '', formula)
        formula = re.sub(r'\\begin\{align\*?\}|\\end\{align\*?\}', '', formula)
        formula = re.sub(r'\\begin\{eqnarray\*?\}|\\end\{eqnarray\*?\}', '', formula)
        formula = re.sub(r'\\begin\{gather\*?\}|\\end\{gather\*?\}', '', formula)
        formula = re.sub(r'\\begin\{multline\*?\}|\\end\{multline\*?\}', '', formula)
        
        # Supprimer les dollars et les crochets LaTeX
        formula = re.sub(r'^\$|\$$', '', formula)
        formula = re.sub(r'^\$\$|\$\$$', '', formula)
        formula = re.sub(r'^\\[|\\]$', '', formula)
        formula = re.sub(r'^\\(|\\)$', '', formula)
        
        # Supprimer les numéros d'équation
        formula = re.sub(r'\\tag\{.*?\}', '', formula)
        
        # Supprimer les espaces excessifs
        formula = re.sub(r'\s+', ' ', formula).strip()
        
        if not formula.strip():
            return None
            
        return formula
    
    async def _generate_formula_description(self,
                                     original_formula: str,
                                     processed_formula: Dict[str, Any],
                                     formula_type: str) -> Optional[str]:
        """
        Génère une description textuelle d'une formule.
        
        Args:
            original_formula: Formule originale
            processed_formula: Formule traitée
            formula_type: Type de formule
            
        Returns:
            Description textuelle ou None si impossible
        """
        try:
            # Si nous avons SymPy, utiliser ses capacités
            if self.sympy_available and "sympy" in processed_formula:
                sympy_expr = processed_formula["sympy"]
                
                # Extraire les variables
                variables = processed_formula.get("variables", [])
                
                if formula_type == 'latex':
                    # Nettoyer la formule pour la description
                    clean_formula = self._clean_latex_formula(original_formula) or original_formula
                    
                    # Descriptions basiques selon le type de formule
                    if "\\int" in clean_formula:
                        return f"Intégrale comprenant les variables {', '.join(variables) if variables else 'aucune variable'}"
                    elif "\\sum" in clean_formula:
                        return f"Somme comprenant les variables {', '.join(variables) if variables else 'aucune variable'}"
                    elif "\\frac" in clean_formula:
                        return f"Fraction comprenant les variables {', '.join(variables) if variables else 'aucune variable'}"
                    elif "=" in clean_formula:
                        return f"Équation comprenant les variables {', '.join(variables) if variables else 'aucune variable'}"
                    else:
                        return f"Expression mathématique comprenant les variables {', '.join(variables) if variables else 'aucune variable'}"
                
                # Description par défaut basée sur le type et les variables
                if "=" in sympy_expr:
                    return f"Équation comportant les variables {', '.join(variables) if variables else 'aucune variable'}"
                else:
                    return f"Expression mathématique comportant les variables {', '.join(variables) if variables else 'aucune variable'}"
            
            # Si la conversion SymPy n'est pas disponible, description générique
            if formula_type == 'latex':
                if "\\int" in original_formula:
                    return "Intégrale"
                elif "\\sum" in original_formula:
                    return "Somme"
                elif "\\frac" in original_formula:
                    return "Fraction"
                elif "=" in original_formula:
                    return "Équation"
                else:
                    return "Expression mathématique"
            
            return "Expression mathématique"
            
        except Exception as e:
            logger.warning(f"Erreur lors de la génération de description: {str(e)}")
            return None
    
    def _extract_variables(self, sympy_expr) -> List[str]:
        """
        Extrait les variables d'une expression SymPy.
        
        Args:
            sympy_expr: Expression SymPy
            
        Returns:
            Liste des variables
        """
        if not self.sympy_available:
            return []
            
        try:
            import sympy
            
            # Obtenir les symboles
            symbols = list(sympy.symbols(sympy_expr.free_symbols))
            
            # Extraire les noms des symboles
            variable_names = [str(symbol) for symbol in symbols]
            
            return variable_names
        except Exception:
            return []
    
    def _has_variables(self, processed_formula: Dict[str, Any]) -> bool:
        """
        Vérifie si une formule contient des variables.
        
        Args:
            processed_formula: Formule traitée
            
        Returns:
            True si la formule contient des variables
        """
        variables = processed_formula.get("variables", [])
        return len(variables) > 0
    
    def _estimate_complexity(self, processed_formula: Dict[str, Any]) -> float:
        """
        Estime la complexité d'une formule.
        
        Args:
            processed_formula: Formule traitée
            
        Returns:
            Score de complexité (0-100)
        """
        # Si nous avons une représentation SymPy, l'utiliser
        if "sympy" in processed_formula:
            expr_str = processed_formula["sympy"]
            
            # Critères de complexité
            operators = ['+', '-', '*', '/', '^', 'sqrt', 'log', 'sin', 'cos', 'tan', 'exp']
            special_funcs = ['sin', 'cos', 'tan', 'exp', 'log', 'sqrt', 'lim', 'diff', 'integrate']
            
            # Compter les opérateurs et fonctions
            op_count = sum(expr_str.count(op) for op in operators)
            func_count = sum(expr_str.count(func) for func in special_funcs)
            
            # Variables
            var_count = len(processed_formula.get("variables", []))
            
            # Calculer le score de complexité
            length_factor = min(len(expr_str) / 50, 1.0)  # Longueur normalisée
            complexity = (op_count * 2 + func_count * 5 + var_count * 3) * length_factor
            
            # Limiter entre 0 et 100
            return min(100, max(0, complexity))
        
        # Si nous avons LaTeX, utiliser sa structure
        elif "latex" in processed_formula:
            latex_str = processed_formula["latex"]
            
            # Critères de complexité
            environments = ['\\begin', '\\end', 'array', 'matrix']
            commands = ['\\frac', '\\int', '\\sum', '\\prod', '\\lim', '\\to', '\\infty', 
                       '\\alpha', '\\beta', '\\gamma', '\\Delta', '\\partial']
            
            # Compter les structures complexes
            env_count = sum(latex_str.count(env) for env in environments)
            cmd_count = sum(latex_str.count(cmd) for cmd in commands)
            
            # Compter les accolades et les indices/exposants
            brace_count = latex_str.count('{') + latex_str.count('}')
            index_exp_count = latex_str.count('^') + latex_str.count('_')
            
            # Calculer le score de complexité
            length_factor = min(len(latex_str) / 100, 1.0)  # Longueur normalisée
            complexity = (env_count * 10 + cmd_count * 5 + brace_count + index_exp_count * 2) * length_factor
            
            # Limiter entre 0 et 100
            return min(100, max(0, complexity))
        
        # Par défaut, complexité basée sur la longueur
        else:
            original = processed_formula.get("original", "")
            return min(100, len(original) / 5)

    def _is_likely_formula(self, text: str) -> Tuple[bool, float]:
        """
        Détermine si un texte contient probablement une formule mathématique.
        
        Args:
            text: Texte à analyser
            
        Returns:
            Tuple (est_une_formule, score_de_confiance)
        """
        if not text or len(text.strip()) < 3:
            return False, 0.0
        
        text = text.strip()
        
        # Indicateurs LaTeX
        latex_indicators = [
            # Environnements mathématiques
            r'\begin{equation}', r'\end{equation}',
            r'\begin{align}', r'\end{align}',
            r'\begin{math}', r'\end{math}',
            r'\begin{eqnarray}', r'\end{eqnarray}',
            # Délimiteurs inline
            r'\(', r'\)', r'$$', r'$',
            # Commandes fréquentes
            r'\frac{', r'\sqrt{', r'\sum_', r'\int_',
            r'\alpha', r'\beta', r'\gamma', r'\delta', r'\theta', r'\lambda',
            r'\partial', r'\nabla', r'\infty'
        ]
        
        # Symboles mathématiques courants
        math_symbols = [
            # Opérateurs
            '±', '×', '÷', '∑', '∏', '∫', '√',
            # Symboles de comparaison
            '≤', '≥', '≠', '≈', '∝',
            # Symboles grecs courants
            'α', 'β', 'γ', 'δ', 'θ', 'λ', 'π',
            # Symboles divers
            '∞', '∂', '∇', '∆', '∈', '∉', '∩', '∪'
        ]
        
        # Patterns pour les formules en format ASCII
        ascii_patterns = [
            r'[a-zA-Z0-9]+\^[0-9]+',  # exposants: x^2
            r'[a-zA-Z0-9]+\_[0-9]+',  # indices: x_1
            r'sqrt\([^)]+\)',  # racines: sqrt(x)
            r'[a-zA-Z]+/[a-zA-Z0-9]+',  # fractions: a/b
            r'[a-zA-Z]+\*\*[0-9]+',  # puissances: x**2
            r'sum\([^)]+\)',  # sommes: sum(i=1..n)
            r'int\([^)]+\)'   # intégrales: int(f(x)dx)
        ]
        
        # Vérifier les indicateurs LaTeX
        for indicator in latex_indicators:
            if indicator in text:
                confidence = min(0.9, 0.5 + 0.1 * text.count(indicator))
                return True, confidence
        
        # Vérifier les symboles mathématiques
        symbol_count = sum(1 for symbol in math_symbols if symbol in text)
        if symbol_count >= 2:
            confidence = min(0.8, 0.4 + 0.1 * symbol_count)
            return True, confidence
        
        # Vérifier les patterns ASCII
        for pattern in ascii_patterns:
            if re.search(pattern, text):
                return True, 0.7
        
        # Vérifier la densité de symboles mathématiques
        # Si le texte contient un ratio élevé de symboles spéciaux typiques des formules
        special_chars = set("+-*/=()[]{}^_<>")
        special_char_count = sum(1 for char in text if char in special_chars)
        
        if len(text) > 0:
            special_char_ratio = special_char_count / len(text)
            if special_char_ratio > 0.25:
                confidence = min(0.6, 0.3 + special_char_ratio)
                return True, confidence
        
        # Vérifier si le texte contient un nombre équilibré de parenthèses,
        # ce qui est courant dans les formules
        if '(' in text and ')' in text and text.count('(') == text.count(')'):
            parenthesis_pairs = text.count('(')
            if parenthesis_pairs >= 2:
                confidence = min(0.7, 0.4 + 0.1 * parenthesis_pairs)
                return True, confidence
        
        # Pas de preuve suffisante que c'est une formule
        return False, 0.0
    
    def _generate_formula_visualization(self, formula: str, formula_type: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Génère une visualisation de la formule.
        
        Args:
            formula: Texte de la formule
            formula_type: Type de formule ('latex', 'ascii', 'mathml', 'unknown')
            output_dir: Répertoire de sortie pour les fichiers générés
            
        Returns:
            Informations sur la visualisation générée
        """
        if not self.sympy_available:
            logger.warning("Impossible de générer une visualisation - SymPy n'est pas disponible")
            return {}
        
        try:
            visualization_info = {}
            
            # Créer un répertoire temporaire si aucun répertoire de sortie n'est spécifié
            temp_dir = None
            if not output_dir:
                temp_dir = tempfile.mkdtemp(prefix="formula_viz_")
                output_dir = temp_dir
            else:
                output_dir = Path(output_dir)
                os.makedirs(output_dir, exist_ok=True)
            
            # Préparer la formule pour la visualisation
            clean_formula = formula
            
            if formula_type == 'latex':
                clean_formula = self._clean_latex_formula(formula)
                if not clean_formula:
                    return {}
                
                try:
                    # Convertir en expression SymPy
                    expr = latex2sympy2.latex2sympy(clean_formula)
                    
                    # Générer une image PNG de la formule
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    png_path = Path(output_dir) / f"formula_{timestamp}.png"
                    
                    import matplotlib.pyplot as plt
                    from sympy import preview
                    
                    preview(expr, viewer='file', filename=str(png_path), euler=False, 
                            packages=('amsmath', 'amsfonts', 'amssymb'))
                    
                    visualization_info['png_path'] = str(png_path)
                    visualization_info['format'] = 'png'
                    
                    # Générer également une version SVG pour une meilleure qualité
                    svg_path = Path(output_dir) / f"formula_{timestamp}.svg"
                    try:
                        preview(expr, viewer='file', filename=str(svg_path), 
                                euler=False, format='svg', 
                                packages=('amsmath', 'amsfonts', 'amssymb'))
                        visualization_info['svg_path'] = str(svg_path)
                    except Exception as e:
                        logger.warning(f"Impossible de générer SVG: {str(e)}")
                    
                except Exception as e:
                    logger.warning(f"Impossible de générer une visualisation via SymPy: {str(e)}")
                    
                    # Fallback: utiliser un service web ou une bibliothèque plus simple
                    try:
                        from matplotlib import mathtext
                        import matplotlib.pyplot as plt
                        import numpy as np
                        
                        # Nettoyer davantage la formule si nécessaire
                        display_formula = clean_formula
                        if not display_formula.startswith('$') and not display_formula.endswith('$'):
                            display_formula = f"${display_formula}$"
                        
                        fig = plt.figure(figsize=(6, 1))
                        plt.axis('off')
                        plt.text(0.5, 0.5, display_formula, fontsize=14, 
                                verticalalignment='center', horizontalalignment='center')
                        
                        png_path = Path(output_dir) / f"formula_simple_{timestamp}.png"
                        plt.savefig(str(png_path), bbox_inches='tight', pad_inches=0.1, dpi=150)
                        plt.close(fig)
                        
                        visualization_info['png_path'] = str(png_path)
                        visualization_info['format'] = 'png'
                        visualization_info['fallback'] = True
                    except Exception as e2:
                        logger.warning(f"Fallback de visualisation échoué: {str(e2)}")
            
            elif formula_type == 'ascii':
                # Pour l'ASCII math, convertir d'abord en LaTeX puis visualiser
                try:
                    # Conversion ASCII -> LaTeX simplifiée
                    latex_formula = formula
                    
                    # Remplacements de base pour les opérations courantes
                    replacements = {
                        "**": "^",
                        "sqrt": "\\sqrt",
                        "alpha": "\\alpha",
                        "beta": "\\beta",
                        "gamma": "\\gamma",
                        "delta": "\\delta",
                        "theta": "\\theta",
                        "lambda": "\\lambda",
                        "pi": "\\pi",
                        "inf": "\\infty"
                    }
                    
                    for orig, repl in replacements.items():
                        latex_formula = latex_formula.replace(orig, repl)
                    
                    # Envelopper dans des délimiteurs LaTeX
                    if not latex_formula.startswith("$"):
                        latex_formula = f"${latex_formula}$"
                    
                    # Utiliser matplotlib pour rendre la formule
                    from matplotlib import mathtext
                    import matplotlib.pyplot as plt
                    
                    fig = plt.figure(figsize=(6, 1))
                    plt.axis('off')
                    plt.text(0.5, 0.5, latex_formula, fontsize=14, 
                            verticalalignment='center', horizontalalignment='center')
                    
                    png_path = Path(output_dir) / f"formula_ascii_{timestamp}.png"
                    plt.savefig(str(png_path), bbox_inches='tight', pad_inches=0.1, dpi=150)
                    plt.close(fig)
                    
                    visualization_info['png_path'] = str(png_path)
                    visualization_info['format'] = 'png'
                    
                except Exception as e:
                    logger.warning(f"Impossible de visualiser la formule ASCII: {str(e)}")
            
            # Ajouter des métadonnées à la visualisation
            visualization_info['timestamp'] = timestamp
            visualization_info['original_formula'] = formula
            visualization_info['formula_type'] = formula_type
            
            return visualization_info
            
        except Exception as e:
            logger.exception(f"Erreur lors de la génération de visualisation: {str(e)}")
            return {}
        finally:
            # Nettoyer le répertoire temporaire si nous en avons créé un
            if temp_dir:
                try:
                    import shutil
                    # Ne pas supprimer pour permettre l'accès aux fichiers générés
                    # shutil.rmtree(temp_dir)
                    pass
                except Exception:
                    pass
    
    def _improve_formula_description(self, original_formula: str, variables: List[str], complexity: int) -> str:
        """
        Améliore la description textuelle d'une formule en fournissant plus de contexte.
        
        Args:
            original_formula: Formule originale
            variables: Variables identifiées dans la formule
            complexity: Score de complexité de la formule
            
        Returns:
            Description améliorée de la formule
        """
        # Base de descriptions pour différents types de formules
        common_formulas = {
            r'e\^(-t/RC)': "Cette formule représente une décharge exponentielle, typique des circuits RC (résistance-condensateur). Elle montre comment la tension diminue exponentiellement au cours du temps.",
            r'F = m.?a': "Il s'agit de la deuxième loi de Newton qui relie la force, la masse et l'accélération. Elle indique que la force appliquée à un objet est égale au produit de sa masse par son accélération.",
            r'E = m.?c\^2': "C'est la célèbre équation d'équivalence masse-énergie d'Einstein. Elle montre que l'énergie (E) équivaut à la masse (m) multipliée par le carré de la vitesse de la lumière (c²).",
            r'PV = n.?RT': "Cette formule est l'équation des gaz parfaits qui relie la pression, le volume, la quantité de matière et la température d'un gaz.",
            r'I = V/R': "C'est la loi d'Ohm qui définit la relation entre la tension, le courant et la résistance dans un circuit électrique.",
            r'P = I.?\^2.?R': "Cette formule permet de calculer la puissance dissipée par effet Joule dans un conducteur.",
            r'a\^2 \+ b\^2 = c\^2': "Il s'agit du théorème de Pythagore, applicable aux triangles rectangles.",
            r'\\frac{dx}{dt}': "Cette expression représente une dérivée par rapport au temps, souvent utilisée pour décrire un taux de variation instantané.",
            r'\\int_a\^b': "Cette expression représente une intégrale définie, utilisée pour calculer l'aire sous une courbe ou l'accumulation d'une quantité."
        }
        
        # Essayer de reconnaître des formules connues
        clean_formula = re.sub(r'\s+', '', original_formula)
        for pattern, description in common_formulas.items():
            if re.search(pattern, clean_formula):
                return description
        
        # Si aucune formule connue n'est détectée, générer une description plus générique
        
        # Caractériser la formule en fonction des opérations qu'elle contient
        operations = []
        if '=' in original_formula:
            operations.append("une équation")
        if '+' in original_formula or '-' in original_formula:
            operations.append("des additions/soustractions")
        if '*' in original_formula or '×' in original_formula or re.search(r'[a-zA-Z]\d', original_formula):
            operations.append("des multiplications")
        if '/' in original_formula or '÷' in original_formula or '\\frac' in original_formula:
            operations.append("des divisions")
        if '^' in original_formula or '**' in original_formula or re.search(r'\^\d+', original_formula):
            operations.append("des élévations à puissance")
        if 'sqrt' in original_formula or '\\sqrt' in original_formula or '√' in original_formula:
            operations.append("des racines carrées")
        if '\\int' in original_formula or '∫' in original_formula:
            operations.append("des intégrales")
        if '\\sum' in original_formula or '∑' in original_formula:
            operations.append("des sommes")
        if '\\prod' in original_formula or '∏' in original_formula:
            operations.append("des produits")
        if '\\frac{d' in original_formula or '\\partial' in original_formula or '∂' in original_formula:
            operations.append("des dérivées")
        
        # Générer une description basée sur les caractéristiques détectées
        description_parts = []
        
        if operations:
            ops_text = ", ".join(operations[:-1])
            if len(operations) > 1:
                ops_text += f" et {operations[-1]}"
            else:
                ops_text = operations[0]
            
            description_parts.append(f"Cette expression mathématique contient {ops_text}.")
        
        # Ajouter des informations sur les variables
        if variables:
            if len(variables) == 1:
                description_parts.append(f"Elle utilise la variable {variables[0]}.")
            elif len(variables) <= 3:
                vars_text = ", ".join(variables[:-1]) + f" et {variables[-1]}"
                description_parts.append(f"Elle utilise les variables {vars_text}.")
            else:
                description_parts.append(f"Elle utilise {len(variables)} variables différentes.")
        
        # Ajouter une indication sur la complexité
        if complexity < 30:
            description_parts.append("Il s'agit d'une formule relativement simple.")
        elif complexity < 60:
            description_parts.append("Il s'agit d'une formule de complexité modérée.")
        else:
            description_parts.append("Il s'agit d'une formule complexe.")
        
        return " ".join(description_parts)
