#!/usr/bin/env python
"""
Script d'extraction de schémas techniques depuis des documents PDF.
Ce script permet d'identifier et d'extraire automatiquement les zones 
qui contiennent potentiellement des schémas techniques.

Utilisation:
    python extract_schemas.py --input chemin/vers/document.pdf --output chemin/vers/dossier_sortie

Options:
    --input (-i): Chemin vers le document PDF à analyser
    --output (-o): Dossier de sortie pour les schémas extraits
    --min-area (-m): Surface minimale (en pixels) pour qu'une région soit considérée comme un schéma
    --format (-f): Format de sortie des images (png, jpg)
    --dpi (-d): Résolution des images extraites
"""

import argparse
import asyncio
import os
import sys
import logging
from pathlib import Path
import time
import numpy as np

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au chemin pour importer les modules du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.core.image_processing.vision_ai import VisionAIService
    VISION_AI_AVAILABLE = True
except ImportError:
    logger.warning("Module Vision AI non disponible. L'analyse avancée des schémas ne sera pas possible.")
    VISION_AI_AVAILABLE = False

def get_args():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Extrait les schémas techniques des documents PDF")
    parser.add_argument("-i", "--input", required=True, help="Chemin vers le document PDF")
    parser.add_argument("-o", "--output", help="Dossier de sortie pour les schémas extraits")
    parser.add_argument("-m", "--min-area", type=int, default=10000, help="Surface minimale (pixels) pour qu'une région soit considérée comme un schéma")
    parser.add_argument("-f", "--format", choices=["png", "jpg"], default="png", help="Format de sortie des images")
    parser.add_argument("-d", "--dpi", type=int, default=300, help="Résolution des images extraites")
    parser.add_argument("--analyze", action="store_true", help="Analyser les schémas extraits avec Vision AI")
    return parser.parse_args()

async def extract_schemas(input_path, output_dir, min_area=10000, img_format="png", dpi=300, analyze=False):
    """
    Extrait les schémas techniques d'un document PDF.
    
    Args:
        input_path: Chemin vers le document PDF
        output_dir: Répertoire de sortie pour les images extraites
        min_area: Surface minimale pour qu'une région soit considérée comme un schéma
        img_format: Format de sortie des images
        dpi: Résolution des images extraites
        analyze: Si True, analyse les schémas extraits avec Vision AI
        
    Returns:
        Liste des chemins vers les images extraites
    """
    logger.info(f"Extraction des schémas de {input_path}")
    
    start_time = time.time()
    input_path = Path(input_path)
    
    # Vérifier que le fichier existe
    if not input_path.exists():
        logger.error(f"Le fichier {input_path} n'existe pas")
        return []
    
    # Vérifier que c'est un PDF
    if input_path.suffix.lower() != ".pdf":
        logger.error(f"Le fichier {input_path} n'est pas un PDF")
        return []
    
    # Créer le répertoire de sortie
    if output_dir:
        output_dir = Path(output_dir)
    else:
        output_dir = input_path.parent / f"{input_path.stem}_schemas"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Import des dépendances requises
        try:
            from pdf2image import convert_from_path
            import cv2
        except ImportError as e:
            logger.error(f"Dépendances manquantes: {e}")
            logger.error("Installez les dépendances avec: pip install pdf2image opencv-python")
            return []
        
        # Vérifier la disponibilité de Poppler
        poppler_path = os.environ.get("POPPLER_PATH")
        poppler_args = {"poppler_path": poppler_path} if poppler_path else {}
        
        # Convertir le PDF en images
        logger.info(f"Conversion du PDF en images (DPI: {dpi})...")
        images = convert_from_path(
            input_path, 
            dpi=dpi,
            fmt=img_format,
            **poppler_args
        )
        
        logger.info(f"PDF converti en {len(images)} pages")
        
        # Liste pour stocker les chemins des schémas extraits
        extracted_schemas = []
        
        # Traiter chaque page
        for i, image in enumerate(images):
            logger.info(f"Traitement de la page {i+1}/{len(images)}")
            
            # Convertir l'image PIL en tableau numpy pour OpenCV
            image_np = np.array(image)
            image_cv = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            
            # Recherche de schémas potentiels
            # 1. Conversion en niveaux de gris
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
            
            # 2. Binarisation
            _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # 3. Recherche des contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 4. Filtrage des contours par taille
            filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
            
            # Extraire chaque région d'intérêt
            regions_found = 0
            for j, contour in enumerate(filtered_contours):
                x, y, w, h = cv2.boundingRect(contour)
                
                # Ignorer les régions trop petites ou trop grandes
                if w < 100 or h < 100 or w * h > image_cv.shape[0] * image_cv.shape[1] * 0.9:
                    continue
                
                # Extraire la région
                roi = image_cv[y:y+h, x:x+w]
                
                # Chemin de sortie
                output_path = output_dir / f"schema_page{i+1}_region{j+1}.{img_format}"
                
                # Sauvegarder l'image
                cv2.imwrite(str(output_path), roi)
                extracted_schemas.append(output_path)
                regions_found += 1
            
            logger.info(f"  {regions_found} régions extraites de la page {i+1}")
            
            # Si aucun schéma n'est trouvé, sauvegarder la page entière comme fallback
            if regions_found == 0:
                output_path = output_dir / f"page{i+1}.{img_format}"
                cv2.imwrite(str(output_path), image_cv)
                extracted_schemas.append(output_path)
                logger.info(f"  Sauvegarde de la page entière comme schéma potentiel")
        
        # Analyse des schémas avec Vision AI si demandé
        if analyze and VISION_AI_AVAILABLE and extracted_schemas:
            logger.info("Analyse des schémas extraits avec Vision AI...")
            
            # Initialiser le service Vision AI
            vision_service = VisionAIService()
            initialized = await vision_service.initialize()
            
            if not initialized:
                logger.error("Impossible d'initialiser le service Vision AI")
            else:
                # Analyser chaque schéma
                for schema_path in extracted_schemas:
                    logger.info(f"Analyse de {schema_path.name}...")
                    
                    result = await vision_service.analyze_image(
                        schema_path,
                        features=['text', 'object', 'label', 'technical_drawing']
                    )
                    
                    if result.success:
                        # Sauvegarder les résultats d'analyse
                        analysis_path = schema_path.with_suffix('.analysis.json')
                        import json
                        with open(analysis_path, 'w', encoding='utf-8') as f:
                            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
                        
                        logger.info(f"  Résultats d'analyse sauvegardés dans {analysis_path.name}")
                    else:
                        logger.error(f"  Erreur lors de l'analyse: {result.error_message}")
        
        duration = time.time() - start_time
        logger.info(f"Extraction terminée en {duration:.2f} secondes")
        logger.info(f"{len(extracted_schemas)} schémas extraits dans {output_dir}")
        
        return extracted_schemas
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des schémas: {e}", exc_info=True)
        return []

async def main():
    """Fonction principale."""
    args = get_args()
    
    # Extraction des schémas
    schemas = await extract_schemas(
        args.input,
        args.output,
        min_area=args.min_area,
        img_format=args.format,
        dpi=args.dpi,
        analyze=args.analyze
    )
    
    # Résumé
    if schemas:
        logger.info(f"\nSchémas extraits ({len(schemas)}):")
        for schema in schemas:
            logger.info(f"  - {schema}")
    else:
        logger.warning("Aucun schéma extrait.")

if __name__ == "__main__":
    asyncio.run(main())
