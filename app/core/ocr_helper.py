"""Module d'assistance pour l'OCR des PDFs."""
import subprocess
import logging
import traceback
from pathlib import Path
import fitz  # PyMuPDF
import tempfile
import asyncio
import os
import shutil
import sys
from dotenv import load_dotenv
from .ocr_logger import OCROutputCapture, get_ocr_tracker

# Charger les variables d'environnement
load_dotenv()

logger = logging.getLogger(__name__)

class OCRHelper:
    """Classe pour appliquer l'OCR à des PDFs scannés."""
    
    # Chemins des dépendances (chargés depuis les variables d'environnement ou valeurs par défaut)
    TESSERACT_PATH = os.environ.get("TESSERACT_PATH", r"C:\Users\aurel\AppData\Local\Programs\Tesseract-OCR")
    POPPLER_PATH = os.environ.get("POPPLER_PATH", r"C:\ProgramData\chocolatey\lib\poppler\tools\Library\bin")
    GS_PATH = os.environ.get("GHOSTSCRIPT_PATH", r"C:\ProgramData\chocolatey\lib-bad\Ghostscript.app\10.4.0\tools")
    
    @staticmethod
    async def needs_ocr(file_path: Path, sample_pages: int = 3, min_text_length: int = 100) -> bool:
        """
        Détermine si un PDF a besoin d'OCR en vérifiant le contenu textuel.
        
        Args:
            file_path: Chemin vers le fichier PDF
            sample_pages: Nombre de pages à échantillonner
            min_text_length: Longueur minimale de texte attendue
            
        Returns:
            True si le PDF nécessite OCR, False sinon
        """
        if not file_path.exists():
            logger.error(f"Fichier non trouvé: {file_path}")
            return False
            
        try:
            # Obtenir le tracker pour les logs OCR
            tracker = get_ocr_tracker()
            if tracker:
                await tracker.log_ocr_event(f"Vérification du besoin d'OCR pour {file_path.name}")
                
            doc = fitz.open(str(file_path))
            
            # Échantillonnage des premières pages
            pages_to_check = min(sample_pages, len(doc))
            total_text = ""
            
            for i in range(pages_to_check):
                page_text = doc[i].get_text().strip()
                total_text += page_text
                
                # Log pour débogage
                if not page_text:
                    logger.info(f"Page {i+1}: Aucun texte détecté")
                else:
                    sample = page_text[:50].replace('\n', ' ')
                    logger.debug(f"Page {i+1}: Échantillon de texte: '{sample}...'")
            
            doc.close()
            
            # Décision basée sur la quantité de texte
            needs_ocr = len(total_text) < min_text_length
            result_message = f"PDF {file_path.name}: {'Nécessite OCR' if needs_ocr else 'Contient déjà du texte'} " \
                             f"({len(total_text)} caractères dans {pages_to_check} pages)"
            
            logger.info(result_message)
            
            # Loguer la décision via le tracker
            if tracker:
                await tracker.log_ocr_event(result_message)
                
            return needs_ocr
            
        except Exception as e:
            error_message = f"Erreur lors de l'analyse du besoin d'OCR: {str(e)}"
            logger.error(error_message)
            
            # Loguer l'erreur via le tracker
            tracker = get_ocr_tracker()
            if tracker:
                await tracker.log_ocr_event(error_message, "ERROR")
                
            return False
    
    @staticmethod
    def _verify_dependencies():
        """
        Vérifie que les dépendances requises pour l'OCR sont disponibles.
        
        Returns:
            bool: True si toutes les dépendances sont trouvées, False sinon
        """
        issues = []
        
        # Vérifier Tesseract
        tesseract_exe = Path(OCRHelper.TESSERACT_PATH) / "tesseract.exe"
        if not tesseract_exe.exists():
            issues.append(f"Tesseract.exe non trouvé à {tesseract_exe}")
            
        # Vérifier Poppler (pdfinfo)
        pdfinfo_exe = Path(OCRHelper.POPPLER_PATH) / "pdfinfo.exe"
        if not pdfinfo_exe.exists():
            issues.append(f"pdfinfo.exe non trouvé à {pdfinfo_exe}")
            
        # Vérifier Ghostscript
        gs_found = False
        gs_path = OCRHelper.GS_PATH
        try:
            gs_exes = list(Path(gs_path).glob("gs*.exe"))
            if gs_exes:
                gs_found = True
        except:
            pass
            
        if not gs_found:
            issues.append(f"Aucun exécutable Ghostscript trouvé dans {gs_path}")
        
        # Signaler les problèmes
        if issues:
            for issue in issues:
                logger.error(issue)
            logger.error("Des dépendances OCR sont manquantes. Voir INSTALLATION_OCR.md pour les instructions.")
            return False
            
        return True
    
    @staticmethod
    async def apply_ocr(file_path: Path) -> Path:
        """
        Applique l'OCR au PDF et retourne le chemin du nouveau fichier.
        
        Args:
            file_path: Chemin vers le fichier PDF original
            
        Returns:
            Chemin vers le PDF avec OCR appliqué
        """
        # Obtenir le tracker OCR
        tracker = get_ocr_tracker()
        
        # Vérifier que le fichier existe
        if not file_path.exists():
            error_message = f"Fichier non trouvé pour OCR: {file_path}"
            logger.error(error_message)
            if tracker:
                await tracker.log_ocr_event(error_message, "ERROR")
            return file_path
        
        # Démarrer le suivi OCR
        if tracker:
            await tracker.start_ocr_tracking(file_path)
            await tracker.log_ocr_event(f"Démarrage du processus OCR pour {file_path.name}")
        
        # Vérifier les dépendances
        if tracker:
            await tracker.log_ocr_event("Vérification des dépendances OCR...")
            
        if not OCRHelper._verify_dependencies():
            error_message = "Impossible d'appliquer l'OCR: dépendances manquantes ou mal configurées"
            logger.error(error_message)
            if tracker:
                await tracker.log_ocr_event(error_message, "ERROR")
                await tracker.complete_ocr_tracking(False, error_message)
            return file_path
        
        # Créer un répertoire temporaire pour l'OCR
        temp_dir = Path(tempfile.gettempdir()) / "technicia_ocr"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        if tracker:
            await tracker.log_ocr_event(f"Répertoire temporaire créé: {temp_dir}")
        
        # Chemin pour le fichier de sortie
        output_path = temp_dir / f"ocr_{file_path.name}"
        
        # Ajouter les chemins au PATH temporairement
        env = os.environ.copy()
        env_paths = env.get("PATH", "").split(os.pathsep)
        
        # Vérifier si les chemins sont déjà dans le PATH
        paths_to_add = [
            OCRHelper.TESSERACT_PATH,
            OCRHelper.POPPLER_PATH,
            OCRHelper.GS_PATH
        ]
        
        for path in paths_to_add:
            if path and Path(path).exists() and path not in env_paths:
                env["PATH"] = f"{path}{os.pathsep}{env['PATH']}"
                logger.debug(f"Ajout au PATH pour OCR: {path}")
        
        try:
            if tracker:
                await tracker.log_ocr_event(f"Lancement de la commande OCRmyPDF avec les paramètres: lang=fra, skip-text=True")
            
            # Utiliser subprocess.run au lieu de asyncio.create_subprocess_exec pour Windows
            import subprocess
            
            # Capturer la sortie pour l'analyse de progression
            with OCROutputCapture(tracker) as output_capture:
                # Utiliser la version simplifiée de la commande pour plus de fiabilité
                result = subprocess.run([
                    "ocrmypdf",
                    "--skip-text",  # Ne pas réappliquer l'OCR aux pages avec du texte
                    "--language", "fra",  # Langue française
                    str(file_path),
                    str(output_path)
                ], env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                success_message = f"OCR terminé avec succès pour {file_path.name}"
                logger.info(success_message)
                
                if tracker:
                    await tracker.log_ocr_event(success_message)
                    
                if output_path.exists() and output_path.stat().st_size > 0:
                    file_size = output_path.stat().st_size / (1024*1024)
                    if tracker:
                        await tracker.log_ocr_event(f"Fichier OCR généré: {output_path.name}, taille: {file_size:.2f} MB")
                        await tracker.complete_ocr_tracking(True)
                    return output_path
                else:
                    error_message = "Fichier de sortie non trouvé ou vide malgré le succès de la commande"
                    logger.error(error_message)
                    if tracker:
                        await tracker.log_ocr_event(error_message, "ERROR")
                        await tracker.complete_ocr_tracking(False, error_message)
                    return file_path
            else:
                error_message = f"Erreur OCR (code {result.returncode}): {result.stderr}"
                logger.error(error_message)
                if tracker:
                    await tracker.log_ocr_event(error_message, "ERROR")
                
                # Essayer une version encore plus simplifiée avec moins d'options
                retry_message = "Nouvelle tentative avec options minimales..."
                logger.info(retry_message)
                if tracker:
                    await tracker.log_ocr_event(retry_message)
                
                with OCROutputCapture(tracker) as output_capture:
                    retry_result = subprocess.run([
                        "ocrmypdf",
                        "--skip-text",  # Ne pas réappliquer l'OCR aux pages avec du texte
                        str(file_path),
                        str(output_path)
                    ], env=env, capture_output=True, text=True)
                
                if retry_result.returncode == 0:
                    success_message = f"OCR réussi lors de la deuxième tentative pour {file_path.name}"
                    logger.info(success_message)
                    if tracker:
                        await tracker.log_ocr_event(success_message)
                        await tracker.complete_ocr_tracking(True)
                    
                    if output_path.exists() and output_path.stat().st_size > 0:
                        return output_path
                
                # En cas d'échec, vérifier si le fichier existe quand même
                if output_path.exists() and output_path.stat().st_size > 0:
                    warning_message = "Malgré l'erreur, le fichier de sortie existe. Utilisation du résultat partiel."
                    logger.warning(warning_message)
                    if tracker:
                        await tracker.log_ocr_event(warning_message, "WARNING")
                        await tracker.complete_ocr_tracking(True)
                    return output_path
                
                if tracker:
                    await tracker.complete_ocr_tracking(False, "Échec de l'OCR après plusieurs tentatives")
                return file_path
            
        except Exception as e:
            error_message = f"Exception lors de l'OCR: {str(e)}"
            details = f"Détails de l'exception: {traceback.format_exc()}"
            
            logger.error(error_message)
            logger.error(details)
            
            if tracker:
                await tracker.log_ocr_event(error_message, "ERROR")
                await tracker.log_ocr_event(details, "ERROR")
                await tracker.complete_ocr_tracking(False, error_message)
                
            return file_path
    
    @staticmethod
    async def cleanup_temp_files():
        """Nettoie les fichiers temporaires créés par l'OCR."""
        try:
            temp_dir = Path(tempfile.gettempdir()) / "technicia_ocr"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.debug("Répertoire temporaire OCR nettoyé")
        except Exception as e:
            logger.warning(f"Erreur lors du nettoyage des fichiers OCR temporaires: {str(e)}")
