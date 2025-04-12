"""
Implémentation avancée du service de conversion de documents.
Offre des fonctionnalités supplémentaires comme le prétraitement des images et l'OCR avancé.
"""

import logging
import time
import os
import tempfile
import asyncio
import shutil
from typing import List, Dict, Any, Optional, Union, BinaryIO
from pathlib import Path

from .base import DocumentConverter, ConversionResult, ConversionError
from .standard import StandardDocumentConverter
from app.core.file_processing.ocr.factory import get_ocr_processor

logger = logging.getLogger(__name__)

class AdvancedDocumentConverter(DocumentConverter):
    """
    Implémentation avancée du service de conversion de documents.
    Ajoute des fonctionnalités comme le prétraitement des images, la reconnaissance de tableaux,
    et l'intégration avec différents services d'OCR.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le convertisseur avancé.
        
        Args:
            config: Configuration du convertisseur
                - temp_dir: Répertoire temporaire (défaut: tempfile.gettempdir())
                - enable_ocr: Activer l'OCR pour les PDFs (défaut: True)
                - ocr_provider: Provider OCR à utiliser (défaut: "ocrmypdf")
                - fallback_to_standard: Utiliser le convertisseur standard en fallback (défaut: True)
                - cleanup_temp_files: Nettoyer les fichiers temporaires après usage (défaut: True)
                - use_threading: Utiliser le multithreading pour les conversions parallèles (défaut: True)
        """
        super().__init__(config)
        
        # Configuration
        self.temp_dir = self.config.get('temp_dir', tempfile.gettempdir())
        self.enable_ocr = self.config.get('enable_ocr', True)
        self.ocr_provider = self.config.get('ocr_provider', 'ocrmypdf')
        self.fallback_to_standard = self.config.get('fallback_to_standard', True)
        self.cleanup_temp_files = self.config.get('cleanup_temp_files', True)
        self.use_threading = self.config.get('use_threading', True)
        
        # Convertisseur standard comme fallback
        self.standard_converter = None
        
        # Processeur OCR
        self.ocr_processor = None
        
        # Dépendances externes
        self._dependencies = {
            'ocr': False,
            'image_processing': False,
            'table_extraction': False
        }
    
    @property
    def provider_name(self) -> str:
        """
        Nom du provider de conversion.
        
        Returns:
            "advanced"
        """
        return "advanced"
    
    async def initialize(self) -> bool:
        """
        Initialise le convertisseur et vérifie les dépendances.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if self.initialized:
            return True
        
        try:
            # Initialiser le convertisseur standard en fallback
            if self.fallback_to_standard:
                self.standard_converter = StandardDocumentConverter(self.config)
                await self.standard_converter.initialize()
            
            # Initialiser le processeur OCR si activé
            if self.enable_ocr:
                try:
                    self.ocr_processor = await get_ocr_processor(
                        provider_name=self.ocr_provider, 
                        config=self.config
                    )
                    self._dependencies['ocr'] = True
                except Exception as e:
                    logger.warning(f"Erreur lors de l'initialisation du processeur OCR: {str(e)}")
            
            # Vérifier les dépendances d'image processing
            try:
                import cv2
                self._dependencies['image_processing'] = True
            except ImportError:
                logger.warning("OpenCV (cv2) n'est pas installé pour le traitement d'images avancé")
            
            # Vérifier les dépendances d'extraction de tableaux
            try:
                import camelot
                self._dependencies['table_extraction'] = True
            except ImportError:
                logger.warning("camelot-py n'est pas installé pour l'extraction de tableaux")
            
            # Journaliser le statut d'initialisation
            logger.info(f"Statut d'initialisation du convertisseur avancé:")
            logger.info(f"  OCR: {self._dependencies['ocr']}")
            logger.info(f"  Traitement d'images: {self._dependencies['image_processing']}")
            logger.info(f"  Extraction de tableaux: {self._dependencies['table_extraction']}")
            
            # Considérer comme réussi si l'OCR est disponible, ou si le fallback standard est initialisé
            self.initialized = self._dependencies['ocr'] or (self.fallback_to_standard and self.standard_converter.is_initialized)
            return self.initialized
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du convertisseur avancé: {str(e)}")
            return False
    
    async def convert_file(self, 
                    file_path: Union[str, Path],
                    output_format: str = "text",
                    **kwargs) -> ConversionResult:
        """
        Convertit un fichier en texte avec des fonctionnalités avancées.
        
        Args:
            file_path: Chemin vers le fichier à convertir
            output_format: Format de sortie (défaut: "text")
            **kwargs: Options spécifiques au convertisseur
                - detect_tables: Détecter et extraire les tableaux (défaut: True)
                - preprocess_images: Prétraiter les images pour améliorer l'OCR (défaut: True)
                - detect_languages: Détecter automatiquement les langues (défaut: True)
                - extract_metadata: Extraire les métadonnées (défaut: True)
                
        Returns:
            Résultat de la conversion
        """
        start_time = time.time()
        
        # S'assurer que le convertisseur est initialisé
        if not self.initialized and not await self.initialize():
            return ConversionResult(
                success=False,
                error_message="Le convertisseur n'a pas pu être initialisé"
            )
        
        # Convertir en Path
        file_path = Path(file_path)
        
        # Vérifier l'existence du fichier
        if not file_path.exists():
            return ConversionResult(
                success=False,
                error_message=f"Le fichier {file_path} n'existe pas"
            )
        
        # Détecter le type de fichier
        mime_type = await self.detect_file_type(file_path)
        extension = file_path.suffix.lower()
        
        # Extraire les métadonnées si demandé
        metadata = {}
        if kwargs.get('extract_metadata', True):
            try:
                metadata = await self.extract_metadata(file_path)
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction des métadonnées: {str(e)}")
        
        # Vérifier si OCR potentiellement nécessaire pour les PDFs
        needs_ocr = False
        if extension == '.pdf' and self.enable_ocr:
            needs_ocr = await self._check_if_pdf_needs_ocr(file_path)
        
        try:
            # Conversion selon le type de fichier
            if extension == '.pdf':
                if needs_ocr and self._dependencies['ocr']:
                    result = await self._convert_pdf_with_ocr(file_path, **kwargs)
                else:
                    # Utiliser le convertisseur standard ou le fallback pour les PDFs sans OCR
                    if self.standard_converter:
                        result = await self.standard_converter.convert_file(file_path, output_format, **kwargs)
                    else:
                        result = await self._convert_pdf_standard(file_path, **kwargs)
                
                # Post-traitement spécifique au PDF (extraction de tableaux, etc.)
                result = await self._post_process_pdf(file_path, result, **kwargs)
            
            elif extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']:
                # Conversion d'image avec OCR
                if self._dependencies['ocr']:
                    result = await self._convert_image_with_ocr(file_path, **kwargs)
                elif self.standard_converter:
                    result = await self.standard_converter.convert_file(file_path, output_format, **kwargs)
                else:
                    return ConversionResult(
                        success=False,
                        error_message="Aucun processeur OCR disponible pour la conversion d'image"
                    )
            
            elif extension in ['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.odt']:
                # Utiliser le convertisseur standard pour les documents Office
                if self.standard_converter:
                    result = await self.standard_converter.convert_file(file_path, output_format, **kwargs)
                else:
                    return ConversionResult(
                        success=False,
                        error_message="Aucun convertisseur disponible pour les documents Office"
                    )
            
            else:
                # Fallback sur le convertisseur standard pour les autres formats
                if self.standard_converter:
                    result = await self.standard_converter.convert_file(file_path, output_format, **kwargs)
                else:
                    return ConversionResult(
                        success=False,
                        error_message=f"Type de fichier non supporté: {extension}"
                    )
            
            # Ajouter les métadonnées et le temps de traitement
            if result.success:
                if result.metadata is None:
                    result.metadata = {}
                result.metadata.update(metadata)
                result.metadata["needs_ocr"] = needs_ocr
                result.processing_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion avancée du fichier {file_path}: {str(e)}")
            
            # Fallback sur le convertisseur standard en cas d'erreur
            if self.fallback_to_standard and self.standard_converter:
                logger.info(f"Fallback sur le convertisseur standard suite à une erreur")
                
                try:
                    result = await self.standard_converter.convert_file(file_path, output_format, **kwargs)
                    result.metadata = result.metadata or {}
                    result.metadata["fallback_used"] = True
                    result.processing_time = time.time() - start_time
                    return result
                except Exception as fallback_error:
                    logger.error(f"Erreur lors du fallback sur convertisseur standard: {str(fallback_error)}")
            
            return ConversionResult(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    async def convert_bytes(self,
                     content: Union[bytes, BinaryIO],
                     file_type: str,
                     output_format: str = "text",
                     **kwargs) -> ConversionResult:
        """
        Convertit un contenu binaire en texte.
        
        Args:
            content: Contenu binaire à convertir
            file_type: Type du fichier (extension ou MIME type)
            output_format: Format de sortie (défaut: "text")
            **kwargs: Options spécifiques au convertisseur
            
        Returns:
            Résultat de la conversion
        """
        # Créer un fichier temporaire
        temp_dir = Path(self.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Déterminer l'extension
        if file_type.startswith('.'):
            extension = file_type
        elif '/' in file_type:  # MIME type
            # Mapper le MIME type à une extension
            mime_to_ext = {
                'application/pdf': '.pdf',
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/tiff': '.tiff',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                'text/plain': '.txt',
                'text/html': '.html',
            }
            extension = mime_to_ext.get(file_type, '.bin')
        else:
            extension = f".{file_type}"
        
        # Écrire le contenu dans un fichier temporaire
        try:
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False, dir=temp_dir) as temp_file:
                temp_path = temp_file.name
                
                if isinstance(content, bytes):
                    temp_file.write(content)
                else:
                    temp_file.write(content.read())
            
            # Convertir le fichier temporaire
            result = await self.convert_file(temp_path, output_format, **kwargs)
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion du contenu binaire: {str(e)}")
            return ConversionResult(
                success=False,
                error_message=str(e)
            )
        finally:
            # Supprimer le fichier temporaire si demandé
            if self.cleanup_temp_files and 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Erreur lors de la suppression du fichier temporaire: {str(e)}")
    
    async def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extrait les métadonnées d'un fichier.
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            Dictionnaire des métadonnées
        """
        # Utiliser le convertisseur standard pour l'extraction de métadonnées
        if self.standard_converter:
            try:
                return await self.standard_converter.extract_metadata(file_path)
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction des métadonnées via convertisseur standard: {str(e)}")
        
        # Métadonnées de base (fallback)
        file_path = Path(file_path)
        
        return {
            "filename": file_path.name,
            "extension": file_path.suffix.lower(),
            "size_bytes": file_path.stat().st_size,
            "modified_time": file_path.stat().st_mtime,
        }
    
    async def supported_file_types(self) -> List[str]:
        """
        Retourne la liste des types de fichiers supportés.
        
        Returns:
            Liste des extensions de fichiers supportées
        """
        # Combiner les types supportés par le convertisseur standard et l'OCR
        supported = []
        
        # Types supportés par l'OCR
        if self._dependencies['ocr']:
            supported.extend(['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'])
        
        # Types supportés par le convertisseur standard
        if self.standard_converter:
            supported.extend(await self.standard_converter.supported_file_types())
        
        # Éliminer les doublons
        return list(set(supported))
    
    # Méthodes d'aide
    
    async def _check_if_pdf_needs_ocr(self, file_path: Path) -> bool:
        """
        Vérifie si un PDF a besoin d'OCR.
        
        Args:
            file_path: Chemin vers le fichier PDF
            
        Returns:
            True si le PDF a besoin d'OCR, False sinon
        """
        if not self.ocr_processor:
            return False
        
        try:
            return await self.ocr_processor.needs_ocr(file_path)
        except Exception as e:
            logger.warning(f"Erreur lors de la vérification OCR du PDF: {str(e)}")
            return False
    
    async def _convert_pdf_with_ocr(self, file_path: Path, **kwargs) -> ConversionResult:
        """
        Convertit un PDF en texte en utilisant l'OCR.
        
        Args:
            file_path: Chemin vers le fichier PDF
            **kwargs: Options spécifiques
                
        Returns:
            Résultat de la conversion
        """
        if not self.ocr_processor:
            raise ConversionError("Aucun processeur OCR disponible")
        
        # Créer un répertoire temporaire pour les fichiers de sortie
        temp_dir = Path(self.temp_dir) / f"ocr_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Traiter le document avec OCR
            ocr_result = await self.ocr_processor.process_document(
                input_path=file_path,
                output_dir=temp_dir,
                **kwargs
            )
            
            if not ocr_result.success:
                raise ConversionError(f"Échec de l'OCR: {ocr_result.error_message}")
            
            # Extraire le texte du PDF traité par OCR
            output_file = ocr_result.output_path
            
            # Utiliser le convertisseur standard pour l'extraction de texte
            if self.standard_converter:
                result = await self.standard_converter.convert_file(output_file, "text", **kwargs)
            else:
                result = await self._convert_pdf_standard(output_file, **kwargs)
            
            # Ajouter les métadonnées OCR
            if result.success:
                if result.metadata is None:
                    result.metadata = {}
                result.metadata.update({
                    "ocr_processed": True,
                    "ocr_provider": self.ocr_provider,
                    "ocr_processing_time": ocr_result.processing_time,
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion PDF avec OCR: {str(e)}")
            raise
        finally:
            # Nettoyer les fichiers temporaires si demandé
            if self.cleanup_temp_files and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Erreur lors du nettoyage du répertoire temporaire: {str(e)}")
    
    async def _convert_pdf_standard(self, file_path: Path, **kwargs) -> ConversionResult:
        """
        Convertit un PDF en texte sans OCR.
        
        Args:
            file_path: Chemin vers le fichier PDF
            **kwargs: Options spécifiques
                
        Returns:
            Résultat de la conversion
        """
        try:
            # Utiliser PyMuPDF si disponible
            import fitz
            doc = fitz.open(str(file_path))
            
            text_content = ""
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                text_content += page.get_text()
            
            doc.close()
            
            return ConversionResult(
                success=True,
                text_content=text_content,
                pages_processed=doc.page_count,
                total_pages=doc.page_count,
                metadata={"parser": "fitz"}
            )
            
        except ImportError:
            # Fallback sur PyPDF2
            try:
                import pypdf
                with open(file_path, 'rb') as f:
                    reader = pypdf.PdfReader(f)
                    
                    text_content = ""
                    for page in reader.pages:
                        text_content += page.extract_text() or ""
                    
                    return ConversionResult(
                        success=True,
                        text_content=text_content,
                        pages_processed=len(reader.pages),
                        total_pages=len(reader.pages),
                        metadata={"parser": "pypdf"}
                    )
            except ImportError:
                raise ConversionError("Aucune bibliothèque PDF n'est disponible")
    
    async def _convert_image_with_ocr(self, file_path: Path, **kwargs) -> ConversionResult:
        """
        Convertit une image en texte en utilisant l'OCR.
        
        Args:
            file_path: Chemin vers l'image
            **kwargs: Options spécifiques
                - lang: Langue pour l'OCR (défaut: 'fra')
                - dpi: Résolution pour l'OCR (défaut: 300)
                - preprocess_image: Prétraiter l'image pour améliorer l'OCR (défaut: True)
                
        Returns:
            Résultat de la conversion
        """
        if not self._dependencies['ocr']:
            raise ConversionError("OCR non disponible pour la conversion d'images")
        
        # Prétraiter l'image si demandé et si OpenCV est disponible
        preprocess = kwargs.get('preprocess_image', True) and self._dependencies['image_processing']
        
        if preprocess:
            try:
                # Prétraiter l'image pour améliorer l'OCR
                import cv2
                import numpy as np
                from PIL import Image
                
                # Créer un répertoire temporaire pour les fichiers de sortie
                temp_dir = Path(self.temp_dir) / f"img_preprocessing_{int(time.time())}"
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                # Charger l'image
                img = cv2.imread(str(file_path))
                
                # Convertir en niveaux de gris
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Appliquer un filtre gaussien pour réduire le bruit
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                
                # Binarisation adaptative
                thresh = cv2.adaptiveThreshold(
                    blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
                )
                
                # Inverser pour avoir du texte noir sur fond blanc
                thresh = cv2.bitwise_not(thresh)
                
                # Enregistrer l'image prétraitée
                preprocessed_path = temp_dir / f"preprocessed_{file_path.name}"
                cv2.imwrite(str(preprocessed_path), thresh)
                
                # Utiliser l'image prétraitée pour l'OCR
                file_path = preprocessed_path
                
            except Exception as e:
                logger.warning(f"Erreur lors du prétraitement de l'image: {str(e)}")
        
        try:
            # Utiliser pytesseract pour l'OCR
            import pytesseract
            from PIL import Image
            
            # Options OCR
            lang = kwargs.get('lang', 'fra')  # fra pour français
            dpi = kwargs.get('dpi', 300)
            
            # Ouvrir l'image
            img = Image.open(file_path)
            
            # Effectuer l'OCR
            text_content = pytesseract.image_to_string(img, lang=lang)
            
            return ConversionResult(
                success=True,
                text_content=text_content,
                pages_processed=1,
                total_pages=1,
                metadata={
                    "format": file_path.suffix[1:],
                    "ocr_lang": lang,
                    "ocr_processed": True,
                    "image_size": {"width": img.width, "height": img.height},
                    "preprocessed": preprocess
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'OCR de l'image: {str(e)}")
            raise ConversionError(f"Impossible d'extraire le texte de l'image: {str(e)}")
    
    async def _post_process_pdf(self, file_path: Path, result: ConversionResult, **kwargs) -> ConversionResult:
        """
        Post-traitement d'un PDF pour extraction de tableaux, etc.
        
        Args:
            file_path: Chemin vers le fichier PDF
            result: Résultat de la conversion
            **kwargs: Options spécifiques
                - detect_tables: Détecter et extraire les tableaux (défaut: True)
                
        Returns:
            Résultat de la conversion mis à jour
        """
        if not result.success or not result.text_content:
            return result
        
        # Extraire les tableaux si demandé et si camelot est disponible
        detect_tables = kwargs.get('detect_tables', True) and self._dependencies['table_extraction']
        
        if detect_tables:
            try:
                import camelot
                
                # Extraire les tableaux
                tables = camelot.read_pdf(str(file_path), pages='all')
                
                if len(tables) > 0:
                    # Ajouter les tableaux au métadonnées
                    if result.metadata is None:
                        result.metadata = {}
                    
                    result.metadata["tables_count"] = len(tables)
                    result.metadata["tables"] = []
                    
                    # Convertir les tableaux en format texte structuré
                    for i, table in enumerate(tables):
                        try:
                            # Convertir le tableau en texte structuré (format CSV)
                            table_text = table.df.to_csv(index=False)
                            
                            # Remplacer le tableau dans le texte original
                            table_marker = f"\n\n--- TABLE {i+1} ---\n{table_text}\n--- END TABLE {i+1} ---\n\n"
                            
                            # Ajouter à la fin du texte pour ne pas perturber le contenu original
                            if not result.text_content.endswith('\n'):
                                result.text_content += '\n'
                            result.text_content += table_marker
                            
                            # Ajouter les détails du tableau aux métadonnées
                            result.metadata["tables"].append({
                                "index": i,
                                "rows": table.shape[0],
                                "cols": table.shape[1],
                                "accuracy": table.accuracy,
                                "whitespace": table.whitespace,
                            })
                        
                        except Exception as table_error:
                            logger.warning(f"Erreur lors du traitement du tableau {i}: {str(table_error)}")
                
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction des tableaux: {str(e)}")
        
        return result
