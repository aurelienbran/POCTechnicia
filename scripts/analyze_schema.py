#!/usr/bin/env python
"""
Script d'analyse de schémas techniques avec Google Cloud Vision AI.
Ce script permet d'analyser des schémas techniques pour en extraire du texte,
identifier des symboles, et comprendre la structure du schéma.

Utilisation:
    python analyze_schema.py --input chemin/vers/schema.png [--output chemin/vers/résultats]

Options:
    --input (-i): Chemin vers l'image du schéma technique
    --output (-o): Chemin pour sauvegarder les résultats d'analyse (facultatif)
    --format (-f): Format de sortie (json, txt, html)
    --visualize (-v): Génère une visualisation des résultats d'analyse
"""

import argparse
import asyncio
import os
import sys
import logging
import json
from pathlib import Path
import time

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au chemin pour importer les modules du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.core.image_processing.vision_ai import VisionAIService, VisionAnalysisResult
    VISION_AI_AVAILABLE = True
except ImportError:
    logger.warning("Module Vision AI non disponible. Veuillez installer les dépendances nécessaires.")
    VISION_AI_AVAILABLE = False

def get_args():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Analyse des schémas techniques avec Vision AI")
    parser.add_argument("-i", "--input", required=True, help="Chemin vers l'image du schéma technique")
    parser.add_argument("-o", "--output", help="Chemin pour sauvegarder les résultats d'analyse")
    parser.add_argument("-f", "--format", choices=["json", "txt", "html"], default="json", 
                        help="Format de sortie des résultats")
    parser.add_argument("-v", "--visualize", action="store_true", 
                        help="Génère une visualisation des résultats")
    parser.add_argument("--features", nargs="+", 
                        choices=["text", "label", "object", "symbol", "technical_drawing"],
                        default=["text", "object", "symbol", "technical_drawing"],
                        help="Fonctionnalités d'analyse à utiliser")
    return parser.parse_args()

async def analyze_schema(input_path, features=None):
    """
    Analyse un schéma technique avec Vision AI.
    
    Args:
        input_path: Chemin vers l'image du schéma
        features: Liste des fonctionnalités à analyser
        
    Returns:
        Résultat de l'analyse ou None en cas d'erreur
    """
    if not VISION_AI_AVAILABLE:
        logger.error("Vision AI n'est pas disponible. Veuillez installer les dépendances nécessaires.")
        return None
    
    input_path = Path(input_path)
    
    # Vérifier que le fichier existe
    if not input_path.exists():
        logger.error(f"Le fichier {input_path} n'existe pas")
        return None
    
    # Vérifier que c'est une image
    valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    if input_path.suffix.lower() not in valid_extensions:
        logger.error(f"Le fichier {input_path} n'est pas une image supportée. "
                     f"Extensions supportées: {', '.join(valid_extensions)}")
        return None
    
    # Initialiser le service Vision AI
    logger.info("Initialisation du service Vision AI...")
    vision_service = VisionAIService()
    initialized = await vision_service.initialize()
    
    if not initialized:
        logger.error("Impossible d'initialiser le service Vision AI")
        logger.error("Vérifiez que les variables d'environnement sont correctement configurées:")
        logger.error("  - GOOGLE_APPLICATION_CREDENTIALS: Chemin vers le fichier de credentials GCP")
        return None
    
    # Analyser l'image
    logger.info(f"Analyse de {input_path.name} avec Vision AI...")
    start_time = time.time()
    
    if not features:
        features = ["text", "object", "symbol", "technical_drawing"]
    
    result = await vision_service.analyze_image(input_path, features=features)
    
    duration = time.time() - start_time
    
    if result.success:
        logger.info(f"Analyse réussie en {duration:.2f} secondes")
        return result
    else:
        logger.error(f"Erreur lors de l'analyse: {result.error_message}")
        return None

def generate_report_txt(result, output_path):
    """Génère un rapport en format texte."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"RAPPORT D'ANALYSE DE SCHÉMA TECHNIQUE\n")
        f.write(f"====================================\n\n")
        
        # Texte détecté
        f.write(f"TEXTE DÉTECTÉ:\n")
        f.write(f"--------------\n")
        if result.text_annotations:
            # Le premier élément contient tout le texte
            f.write(f"{result.text_annotations[0]['description']}\n\n")
        else:
            f.write(f"Aucun texte détecté.\n\n")
        
        # Symboles techniques
        f.write(f"SYMBOLES TECHNIQUES:\n")
        f.write(f"-------------------\n")
        if result.symbol_annotations:
            for i, symbol in enumerate(result.symbol_annotations):
                f.write(f"{i+1}. {symbol['description']} (confiance: {symbol['score']:.2f})\n")
            f.write("\n")
        else:
            f.write(f"Aucun symbole technique identifié.\n\n")
        
        # Objets détectés
        f.write(f"OBJETS DÉTECTÉS:\n")
        f.write(f"---------------\n")
        if result.object_annotations:
            for i, obj in enumerate(result.object_annotations):
                f.write(f"{i+1}. {obj['name']} (confiance: {obj['score']:.2f})\n")
            f.write("\n")
        else:
            f.write(f"Aucun objet détecté.\n\n")
        
        # Éléments techniques
        f.write(f"ÉLÉMENTS TECHNIQUES:\n")
        f.write(f"-------------------\n")
        if result.technical_drawing_annotations:
            for i, elem in enumerate(result.technical_drawing_annotations):
                f.write(f"{i+1}. {elem['text']} (confiance: {elem['confidence']:.2f})\n")
            f.write("\n")
        else:
            f.write(f"Aucun élément technique identifié.\n\n")

def generate_report_html(result, output_path, input_path):
    """Génère un rapport en format HTML avec visualisation."""
    try:
        import cv2
        import numpy as np
        import base64
        from PIL import Image
    except ImportError:
        logger.error("Dépendances manquantes pour la génération HTML. "
                    "Installez-les avec: pip install opencv-python pillow")
        return
    
    # Charger l'image
    img = cv2.imread(str(input_path))
    if img is None:
        logger.error(f"Impossible de charger l'image: {input_path}")
        return
    
    # Créer une copie pour la visualisation
    img_viz = img.copy()
    
    # Dessiner les annotations
    # Texte
    for text in result.text_annotations[1:]:  # Ignorer le premier qui contient tout le texte
        if 'bounds' in text and text['bounds']:
            points = np.array([[pt['x'], pt['y']] for pt in text['bounds']], np.int32)
            cv2.polylines(img_viz, [points], True, (0, 255, 0), 2)
            
            # Ajouter une étiquette
            x, y = points[0]
            cv2.putText(img_viz, text['description'], (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Symboles
    for symbol in result.symbol_annotations:
        if 'bounds' in symbol and symbol['bounds']:
            points = np.array([[pt['x'], pt['y']] for pt in symbol['bounds']], np.int32)
            cv2.polylines(img_viz, [points], True, (255, 0, 0), 2)
            
            # Ajouter une étiquette
            x, y = points[0]
            cv2.putText(img_viz, symbol['description'], (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    
    # Objets
    for obj in result.object_annotations:
        if 'bounds' in obj and obj['bounds']:
            points = np.array([[int(pt['x'] * img.shape[1]), int(pt['y'] * img.shape[0])] 
                              for pt in obj['bounds']], np.int32)
            cv2.polylines(img_viz, [points], True, (0, 0, 255), 2)
            
            # Ajouter une étiquette
            x, y = points[0]
            cv2.putText(img_viz, obj['name'], (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    # Sauvegarder l'image annotée
    annotated_img_path = output_path.with_suffix('.annotated.png')
    cv2.imwrite(str(annotated_img_path), img_viz)
    
    # Convertir l'image en base64 pour inclusion dans le HTML
    img_pil = Image.fromarray(cv2.cvtColor(img_viz, cv2.COLOR_BGR2RGB))
    img_byte_arr = io.BytesIO()
    img_pil.save(img_byte_arr, format='PNG')
    img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    
    # Générer le HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Analyse de schéma technique</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .container {{ display: flex; }}
            .image-container {{ flex: 1; }}
            .results-container {{ flex: 1; padding-left: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .highlight {{ background-color: yellow; }}
            img {{ max-width: 100%; border: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <h1>Analyse de schéma technique</h1>
        <p>Fichier: {input_path.name}</p>
        
        <div class="container">
            <div class="image-container">
                <h2>Image annotée</h2>
                <img src="data:image/png;base64,{img_base64}" alt="Schéma annoté" />
            </div>
            
            <div class="results-container">
                <h2>Texte détecté</h2>
                <div class="text-box">
                    {result.text_annotations[0]['description'] if result.text_annotations else "Aucun texte détecté."}
                </div>
                
                <h2>Symboles techniques</h2>
                <table>
                    <tr>
                        <th>Description</th>
                        <th>Confiance</th>
                    </tr>
    """
    
    # Ajouter les symboles
    if result.symbol_annotations:
        for symbol in result.symbol_annotations:
            html += f"""
                    <tr>
                        <td>{symbol['description']}</td>
                        <td>{symbol['score']:.2f}</td>
                    </tr>
            """
    else:
        html += f"""
                    <tr>
                        <td colspan="2">Aucun symbole détecté</td>
                    </tr>
        """
    
    html += """
                </table>
                
                <h2>Objets détectés</h2>
                <table>
                    <tr>
                        <th>Nom</th>
                        <th>Confiance</th>
                    </tr>
    """
    
    # Ajouter les objets
    if result.object_annotations:
        for obj in result.object_annotations:
            html += f"""
                    <tr>
                        <td>{obj['name']}</td>
                        <td>{obj['score']:.2f}</td>
                    </tr>
            """
    else:
        html += f"""
                    <tr>
                        <td colspan="2">Aucun objet détecté</td>
                    </tr>
        """
    
    html += """
                </table>
                
                <h2>Éléments techniques</h2>
                <table>
                    <tr>
                        <th>Texte</th>
                        <th>Confiance</th>
                    </tr>
    """
    
    # Ajouter les éléments techniques
    if result.technical_drawing_annotations:
        for elem in result.technical_drawing_annotations:
            html += f"""
                    <tr>
                        <td>{elem['text']}</td>
                        <td>{elem['confidence']:.2f}</td>
                    </tr>
            """
    else:
        html += f"""
                    <tr>
                        <td colspan="2">Aucun élément technique identifié</td>
                    </tr>
        """
    
    html += """
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info(f"Rapport HTML généré: {output_path}")
    logger.info(f"Image annotée générée: {annotated_img_path}")

async def main():
    """Fonction principale."""
    args = get_args()
    
    # Analyser le schéma
    result = await analyze_schema(args.input, features=args.features)
    
    if not result:
        return
    
    # Déterminer le chemin de sortie
    if args.output:
        output_path = Path(args.output)
    else:
        input_path = Path(args.input)
        output_path = input_path.with_suffix(f'.analysis.{args.format}')
    
    # Générer le rapport selon le format demandé
    if args.format == 'json':
        # Sauvegarder les résultats en JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Résultats d'analyse sauvegardés dans {output_path}")
    
    elif args.format == 'txt':
        # Générer un rapport en texte
        generate_report_txt(result, output_path)
        logger.info(f"Rapport textuel généré: {output_path}")
    
    elif args.format == 'html':
        # Générer un rapport HTML avec visualisation
        try:
            import io
            generate_report_html(result, output_path, args.input)
        except ImportError as e:
            logger.error(f"Erreur lors de la génération du rapport HTML: {e}")
            logger.error("Utilisez 'pip install pillow opencv-python' pour installer les dépendances nécessaires")
    
    # Résumé des résultats
    logger.info("\nRésumé de l'analyse:")
    
    if result.text_annotations:
        text_count = len(result.text_annotations) - 1  # Le premier élément contient tout le texte
        logger.info(f"  - {text_count} éléments de texte détectés")
    else:
        logger.info("  - Aucun texte détecté")
    
    if result.symbol_annotations:
        logger.info(f"  - {len(result.symbol_annotations)} symboles techniques identifiés")
    else:
        logger.info("  - Aucun symbole technique identifié")
    
    if result.object_annotations:
        logger.info(f"  - {len(result.object_annotations)} objets détectés")
    else:
        logger.info("  - Aucun objet détecté")
    
    if result.technical_drawing_annotations:
        logger.info(f"  - {len(result.technical_drawing_annotations)} éléments techniques identifiés")
    else:
        logger.info("  - Aucun élément technique identifié")

if __name__ == "__main__":
    asyncio.run(main())
