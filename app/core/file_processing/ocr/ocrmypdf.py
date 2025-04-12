"""
Implémentation du service OCR utilisant OCRmyPDF.
"""

import os
import time
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
import logging
import shutil

import fitz  # PyMuPDF
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from .base import OCRProcessor, OCRResult

logger = logging.getLogger(__name__)

class OCRmyPDFProcessor(OCRProcessor):
    """Service OCR utilisant OCRmyPDF avec Tesseract."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le processeur OCR avec OCRmyPDF.
        
        Args:
            config: Configuration additionnelle
                - tesseract_path: Chemin vers l'exécutable Tesseract
                - poppler_path: Chemin vers les binaires Poppler
                - ghostscript_path: Chemin vers l'exécutable Ghostscript
                - timeout: Timeout pour les opérations OCR en secondes
                - dpi: Résolution pour l'OCR (défaut: 300)
        """
        super().__init__(config)
        self.tesseract_path = self.config.get('tesseract_path') or settings.TESSERACT_PATH
        self.poppler_path = self.config.get('poppler_path') or settings.POPPLER_PATH
        self.ghostscript_path = self.config.get('ghostscript_path') or settings.GHOSTSCRIPT_PATH
        self.timeout = self.config.get('timeout', 600)  # 10 minutes par défaut
        self.dpi = self.config.get('dpi', 300)
        
        # Environnement pour les sous-processus
        self.env = os.environ.copy()
        
        # Ajouter les chemins aux variables d'environnement si définis
        if self.tesseract_path:
            self.env["PATH"] = f"{self.tesseract_path}{os.pathsep}{self.env.get('PATH', '')}"
        if self.poppler_path:
            self.env["PATH"] = f"{self.poppler_path}{os.pathsep}{self.env.get('PATH', '')}"
        if self.ghostscript_path:
            self.env["PATH"] = f"{self.ghostscript_path}{os.pathsep}{self.env.get('PATH', '')}"
    
    @property
    def provider_name(self) -> str:
        """
        Nom du provider OCR.
        
        Returns:
            "ocrmypdf"
        """
        return "ocrmypdf"
    
    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def initialize(self) -> bool:
        """
        Vérifie que OCRmyPDF et ses dépendances sont correctement installés.
        
        Returns:
            True si tous les composants sont disponibles, False sinon
        """
        try:
            # Vérifier OCRmyPDF
            ocrmypdf_version = await self._run_command(["ocrmypdf", "--version"])
            logger.info(f"OCRmyPDF version: {ocrmypdf_version.strip()}")
            
            # Vérifier Tesseract
            tesseract_version = await self._run_command(["tesseract", "--version"])
            logger.info(f"Tesseract version: {tesseract_version.split(chr(10))[0].strip()}")
            
            # Vérifier les langues disponibles
            tesseract_langs = await self._run_command(["tesseract", "--list-langs"])
            logger.info(f"Langues Tesseract disponibles: {tesseract_langs.strip()}")
            
            # Vérifier Ghostscript si possible
            try:
                gs_version = await self._run_command(["gs", "--version"])
                logger.info(f"Ghostscript version: {gs_version.strip()}")
            except Exception:
                logger.warning("Impossible de détecter Ghostscript, il pourrait ne pas être dans le PATH")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de OCRmyPDF: {str(e)}")
            self.initialized = False
            return False
    
    async def _run_command(self, cmd: List[str], timeout: Optional[int] = None) -> str:
        """
        Exécute une commande système et retourne sa sortie.
        
        Args:
            cmd: Liste des éléments de la commande
            timeout: Timeout en secondes pour l'exécution
            
        Returns:
            Sortie de la commande (stdout)
            
        Raises:
            Exception: Si la commande échoue
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout or self.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace')
                logger.error(f"Commande échouée: {' '.join(cmd)}")
                logger.error(f"Erreur: {error_msg}")
                raise Exception(f"Commande échouée avec code {process.returncode}: {error_msg}")
                
            return stdout.decode('utf-8', errors='replace')
            
        except asyncio.TimeoutError:
            process.kill()
            logger.error(f"Timeout lors de l'exécution de la commande: {' '.join(cmd)}")
            raise TimeoutError(f"Timeout après {timeout or self.timeout}s")
    
    async def process_document(self, 
                        input_file: Union[str, Path], 
                        output_file: Optional[Union[str, Path]] = None,
                        language: str = "fra",
                        **kwargs) -> OCRResult:
        """
        Traite un document avec OCRmyPDF.
        
        Args:
            input_file: Chemin vers le fichier d'entrée
            output_file: Chemin vers le fichier de sortie (optionnel)
            language: Code de langue pour l'OCR
            **kwargs: Options additionnelles pour OCRmyPDF
                - force_ocr: Forcer l'OCR même si le document contient du texte
                - dpi: Résolution pour l'OCR
                - optimize: Niveau d'optimisation (0-3)
                
        Returns:
            Résultat de l'opération OCR
        """
        start_time = time.time()
        
        # Convertir les chemins en objets Path
        input_path = Path(input_file)
        
        if not input_path.exists():
            return OCRResult(
                success=False,
                error_message=f"Le fichier d'entrée n'existe pas: {input_path}",
                processing_time=time.time() - start_time
            )
        
        # Si pas de fichier de sortie spécifié, créer un fichier temporaire
        if output_file:
            output_path = Path(output_file)
        else:
            temp_dir = Path(tempfile.gettempdir())
            output_path = temp_dir / f"ocr_{input_path.stem}_{int(time.time())}.pdf"
        
        try:
            # Compter le nombre de pages dans le document d'entrée
            doc = fitz.open(input_path)
            total_pages = len(doc)
            doc.close()
            
            # Construction de la commande OCRmyPDF
            cmd = ["ocrmypdf"]
            
            # Ajouter les options
            cmd.extend(["--language", language])
            cmd.extend(["--dpi", str(kwargs.get("dpi", self.dpi))])
            
            if kwargs.get("force_ocr", False):
                cmd.append("--force-ocr")
            else:
                cmd.append("--skip-text")
            
            optimize_level = kwargs.get("optimize", 1)
            if optimize_level > 0:
                cmd.extend([f"--optimize", str(min(optimize_level, 3))])
            
            # Ajouter d'autres options passées en kwargs
            for key, value in kwargs.items():
                if key not in ["force_ocr", "dpi", "optimize"]:
                    if isinstance(value, bool):
                        if value:
                            cmd.append(f"--{key.replace('_', '-')}")
                    else:
                        cmd.extend([f"--{key.replace('_', '-')}", str(value)])
            
            # Ajouter les chemins d'entrée et de sortie
            cmd.extend([str(input_path), str(output_path)])
            
            logger.info(f"Exécution OCR: {' '.join(cmd)}")
            result = await self._run_command(cmd)
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                success=True,
                output_path=output_path,
                pages_processed=total_pages,
                total_pages=total_pages,
                processing_time=processing_time,
                metadata={
                    "provider": self.provider_name,
                    "language": language,
                    "command": " ".join(cmd),
                    "options": kwargs
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement OCR: {str(e)}")
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                success=False,
                error_message=str(e),
                processing_time=processing_time,
                metadata={
                    "provider": self.provider_name,
                    "language": language,
                    "options": kwargs
                }
            )
    
    async def extract_text(self, 
                    document_path: Union[str, Path],
                    page_numbers: Optional[List[int]] = None) -> str:
        """
        Extrait le texte d'un document PDF.
        
        Args:
            document_path: Chemin vers le document PDF
            page_numbers: Liste des numéros de page à extraire (None = toutes)
            
        Returns:
            Texte extrait du document
        """
        path = Path(document_path)
        if not path.exists():
            raise FileNotFoundError(f"Document introuvable: {path}")
        
        try:
            doc = fitz.open(path)
            
            # Déterminer les pages à extraire
            if page_numbers:
                # Ajuster pour l'indexation à partir de 0
                pages_to_extract = [p-1 for p in page_numbers if 0 <= p-1 < len(doc)]
            else:
                pages_to_extract = range(len(doc))
            
            # Extraire le texte de chaque page
            text = []
            for page_num in pages_to_extract:
                page = doc[page_num]
                text.append(page.get_text())
            
            doc.close()
            return "\n\n".join(text)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de texte: {str(e)}")
            raise
    
    async def needs_ocr(self, document_path: Union[str, Path]) -> bool:
        """
        Détermine si un document nécessite un traitement OCR en vérifiant
        la présence de texte sélectionnable.
        
        Args:
            document_path: Chemin vers le document
            
        Returns:
            True si le document nécessite un OCR, False sinon
        """
        path = Path(document_path)
        if not path.exists():
            raise FileNotFoundError(f"Document introuvable: {path}")
        
        # Vérifier si c'est un PDF
        if path.suffix.lower() != '.pdf':
            # Pour les non-PDF, supposer que l'OCR est nécessaire
            return True
        
        try:
            doc = fitz.open(path)
            
            # Vérifier un échantillon de pages (première, milieu, dernière)
            sample_pages = [0]
            if len(doc) > 2:
                sample_pages.append(len(doc) // 2)
            if len(doc) > 1:
                sample_pages.append(len(doc) - 1)
            
            # Un document a besoin d'OCR si au moins une page échantillonnée
            # contient très peu de texte sélectionnable
            needs_ocr = False
            
            for page_num in sample_pages:
                page = doc[page_num]
                text = page.get_text()
                
                # Si la page contient très peu de texte, elle a probablement besoin d'OCR
                # Seuil minimal de caractères (ajustable)
                if len(text.strip()) < 50:
                    needs_ocr = True
                    break
            
            doc.close()
            return needs_ocr
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification OCR: {str(e)}")
            # En cas d'erreur, mieux vaut appliquer l'OCR
            return True
