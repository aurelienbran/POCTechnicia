"""
Script de diagnostic complet pour tester toutes les étapes du traitement OCR d'un document PDF.
Ce script vérifie :
1. Les dépendances OCR (Tesseract, Poppler, Ghostscript)
2. L'application OCR sur un fichier PDF
3. L'extraction de texte après OCR
4. Le traitement des chunks
"""
import asyncio
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import traceback
from pathlib import Path
import time

# Ajouter le répertoire parent au PYTHONPATH pour importer les modules de l'application
script_dir = Path(__file__).parent
root_dir = script_dir.parent
sys.path.insert(0, str(root_dir))

# Configuration du logging
# Créer un dossier logs s'il n'existe pas
log_dir = root_dir / "logs"
log_dir.mkdir(exist_ok=True)

# Configuration du fichier de log pour le diagnostic
log_file = log_dir / "ocr_diagnostic.log"

# Configuration du logging
logger = logging.getLogger("diagnose_complete_process")
logger.setLevel(logging.INFO)

# Gestionnaire pour la console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# Gestionnaire pour le fichier
file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# Ajouter les gestionnaires au logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Supprimer la propagation pour éviter les messages en double
logger.propagate = False

# Import des composants nécessaires
async def run_diagnostics(pdf_path: Path, enable_ocr: bool = True):
    """
    Exécute un diagnostic complet du traitement OCR et de l'extraction de texte.
    
    Args:
        pdf_path: Chemin vers le fichier PDF à analyser
        enable_ocr: Activer ou non la détection et application OCR
    """
    try:
        from app.core.ocr_helper import OCRHelper
        from app.core.pdf_processor import PDFProcessor
        
        if not pdf_path.exists():
            logger.error(f"Le fichier {pdf_path} n'existe pas")
            return
            
        logger.info("=" * 80)
        logger.info(f"Diagnostic pour {pdf_path.name}")
        logger.info("-" * 80)
        
        # 1. Vérifier les dépendances OCR
        logger.info("1. Vérification des dépendances OCR")
        
        # Vérification des dépendances (méthode non-async)
        ocr_deps_ok = OCRHelper._verify_dependencies()
        
        # Vérifier les chemins individuels pour plus de détails
        tesseract_path = Path(OCRHelper.TESSERACT_PATH) / "tesseract.exe"
        poppler_path = Path(OCRHelper.POPPLER_PATH) / "pdfinfo.exe"
        gs_path = Path(OCRHelper.GS_PATH)
        
        logger.info(f"Tesseract disponible: {tesseract_path.exists()} ({tesseract_path})")
        logger.info(f"Poppler disponible: {poppler_path.exists()} ({poppler_path})")
        logger.info(f"Ghostscript path exists: {gs_path.exists()} ({gs_path})")
        
        # Vérifier si ocrmypdf est installé
        try:
            subprocess.run(["ocrmypdf", "--version"], capture_output=True, text=True)
            ocrmypdf_ok = True
            logger.info("OCRmyPDF disponible: Oui")
        except:
            ocrmypdf_ok = False
            logger.info("OCRmyPDF disponible: Non")
        
        logger.info(f"Toutes les dépendances disponibles: {ocr_deps_ok and ocrmypdf_ok}")
        
        # Afficher les variables d'environnement PATH pour aider au diagnostic
        logger.info("Valeur de PATH: " + os.environ.get("PATH", "Non défini"))

        # 2. Vérifier si le PDF a besoin d'OCR
        logger.info("\n2. Vérification du besoin d'OCR")
        needs_ocr = await OCRHelper.needs_ocr(pdf_path)
        logger.info(f"Le document nécessite OCR: {needs_ocr}")
        
        # 3. Appliquer l'OCR si nécessaire et activé
        ocr_applied = False
        processed_file = pdf_path
        
        if enable_ocr and needs_ocr:
            logger.info("\n3. Application de l'OCR")
            try:
                start_time = time.time()
                processed_file = await OCRHelper.apply_ocr(pdf_path)
                ocr_time = time.time() - start_time
                ocr_applied = processed_file != pdf_path
                logger.info(f"OCR appliqué: {ocr_applied} (en {ocr_time:.2f} secondes)")
                logger.info(f"Fichier traité: {processed_file}")
            except Exception as e:
                logger.error(f"Erreur lors de l'application OCR: {e}")
                logger.error(traceback.format_exc())
                processed_file = pdf_path  # Continuer avec le fichier original
        else:
            logger.info("\n3. Étape OCR ignorée - non nécessaire ou désactivée")
        
        # 4. Extraire et tester le contenu textuel
        logger.info("\n4. Test d'extraction de texte")
        # Initialiser le PDF processor
        pdf_processor = PDFProcessor(extract_images=False)
        
        # Extraire les métadonnées
        metadata = await pdf_processor.extract_metadata(processed_file)
        logger.info(f"Métadonnées extraites: {metadata}")
        
        # Traiter le PDF et compter les chunks
        logger.info("\n5. Traitement des chunks")
        chunks = []
        pages_with_content = set()
        empty_pages = set()
        
        try:
            async for chunk in pdf_processor.process_pdf(processed_file):
                chunks.append(chunk)
                pages_with_content.add(chunk.get('page', 0))
                
            # Identifier les pages sans contenu
            if metadata.get('page_count'):
                all_pages = set(range(1, metadata.get('page_count') + 1))
                empty_pages = all_pages - pages_with_content
            
            logger.info(f"Nombre de chunks extraits: {len(chunks)}")
            logger.info(f"Pages avec contenu: {sorted(list(pages_with_content))}")
            logger.info(f"Pages sans contenu: {sorted(list(empty_pages))}")
        except Exception as e:
            logger.error(f"Erreur pendant l'extraction des chunks: {e}")
            logger.error(traceback.format_exc())
        
        # Échantillon de texte (premier chunk)
        if chunks:
            first_chunk = chunks[0]
            text_sample = first_chunk['content'][:300].replace('\n', ' ')
            logger.info(f"Échantillon de texte (premier chunk): {text_sample}...")
            logger.info(f"Taille en tokens du premier chunk: {first_chunk['tokens']}")
            
            # Afficher aussi un échantillon du dernier chunk
            if len(chunks) > 1:
                last_chunk = chunks[-1]
                text_sample = last_chunk['content'][:300].replace('\n', ' ')
                logger.info(f"Échantillon de texte (dernier chunk): {text_sample}...")
                logger.info(f"Taille en tokens du dernier chunk: {last_chunk['tokens']}")
        else:
            logger.warning("Aucun chunk n'a été extrait!")
            
        # Résultats du diagnostic
        logger.info("\n" + "=" * 80)
        logger.info("RÉSUMÉ DU DIAGNOSTIC")
        logger.info("-" * 80)
        logger.info(f"Fichier: {pdf_path.name}")
        logger.info(f"Nombre de pages: {metadata.get('page_count', 'Inconnu')}")
        logger.info(f"OCR nécessaire: {needs_ocr}")
        logger.info(f"OCR appliqué: {ocr_applied}")
        logger.info(f"Extraction de texte: {'Réussie' if chunks else 'Échouée'}")
        logger.info(f"Nombre de chunks: {len(chunks)}")
        logger.info(f"Nombre de pages avec contenu: {len(pages_with_content)}")
        logger.info(f"Nombre de pages sans contenu: {len(empty_pages)}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Erreur lors du diagnostic: {e}")
        logger.error(traceback.format_exc())

async def main():
    """Point d'entrée principal du script."""
    # Vérifier les arguments
    if len(sys.argv) < 2:
        print(f"Usage: python {Path(__file__).name} chemin/vers/fichier.pdf [true|false]")
        print("Le second argument optionnel active ou désactive l'OCR (true par défaut)")
        return
    
    # Récupérer le chemin du fichier
    file_path = Path(sys.argv[1])
    
    # Récupérer l'option OCR
    enable_ocr = True  # Par défaut
    if len(sys.argv) > 2:
        enable_ocr = sys.argv[2].lower() in ["true", "1", "yes", "y", "oui", "o"]
    
    # Exécuter le diagnostic
    await run_diagnostics(file_path, enable_ocr)
    
    # Afficher le chemin du fichier de log
    print(f"\nRésultats du diagnostic enregistrés dans: {log_dir / 'ocr_diagnostic.log'}")

if __name__ == "__main__":
    asyncio.run(main())
