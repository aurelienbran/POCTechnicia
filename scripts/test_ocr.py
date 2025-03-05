"""
Script de test pour vérifier la fonctionnalité OCR de l'application.
"""
import requests
import sys
import os
import time
import json
from pathlib import Path

# Ajouter le chemin parent au PATH pour pouvoir importer les modules de l'application
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importer la configuration depuis dotenv
from dotenv import load_dotenv
load_dotenv()

# URL de l'API (peut être configurée via variable d'environnement)
API_URL = os.environ.get("API_URL", "http://localhost:8000/api/v1/documents")

# Vérifier si les chemins OCR sont configurés
TESSERACT_PATH = os.environ.get("TESSERACT_PATH")
POPPLER_PATH = os.environ.get("POPPLER_PATH")
GHOSTSCRIPT_PATH = os.environ.get("GHOSTSCRIPT_PATH")

def print_ocr_config():
    """Affiche la configuration OCR actuelle."""
    print("\n=== Configuration OCR ===")
    if TESSERACT_PATH:
        print(f" TESSERACT_PATH configuré: {TESSERACT_PATH}")
    else:
        print(" TESSERACT_PATH non configuré dans .env (utilise le PATH système)")
        
    if POPPLER_PATH:
        print(f" POPPLER_PATH configuré: {POPPLER_PATH}")
    else:
        print(" POPPLER_PATH non configuré dans .env (utilise le PATH système)")
        
    if GHOSTSCRIPT_PATH:
        print(f" GHOSTSCRIPT_PATH configuré: {GHOSTSCRIPT_PATH}")
    else:
        print(" GHOSTSCRIPT_PATH non configuré dans .env (utilise le PATH système)")
    print("")

def upload_file(file_path, enable_ocr=True):
    """
    Télécharge un fichier PDF à l'API et active l'OCR.
    
    Args:
        file_path (str): Chemin vers le fichier PDF à télécharger
        enable_ocr (bool): Active ou désactive la détection et application automatique de l'OCR
        
    Returns:
        dict: Réponse de l'API
    """
    if not Path(file_path).exists():
        print(f"Erreur: Le fichier {file_path} n'existe pas")
        return None
        
    print(f"Téléchargement du fichier: {file_path}")
    print(f"OCR automatique: {'Activé' if enable_ocr else 'Désactivé'}")
    
    # Préparation des données pour la requête
    with open(file_path, "rb") as file:
        files = {"file": (Path(file_path).name, file, "application/pdf")}
        data = {"enable_ocr": "true" if enable_ocr else "false"}
        
        # Envoi de la requête
        print("Envoi de la requête...")
        response = requests.post(API_URL, files=files, data=data)
        
        if response.status_code == 202:
            print(f"Succès! Status: {response.status_code}")
            try:
                result = response.json()
                print("Réponse:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            except:
                print("Réponse non-JSON:", response.text)
                return {"status": "success", "raw_response": response.text}
        else:
            print(f"Erreur! Status: {response.status_code}")
            print("Réponse:", response.text)
            return None

def main():
    """Fonction principale du script de test."""
    # Vérifier les arguments
    if len(sys.argv) < 2:
        print(f"Usage: python {Path(__file__).name} chemin/vers/fichier.pdf [true|false]")
        print("Le second argument optionnel active ou désactive l'OCR (true par défaut)")
        return
    
    # Récupérer le chemin du fichier
    file_path = sys.argv[1]
    
    # Récupérer l'option OCR
    enable_ocr = True  # Par défaut
    if len(sys.argv) > 2:
        enable_ocr = sys.argv[2].lower() in ["true", "1", "yes", "y", "oui", "o"]
    
    # Afficher la configuration OCR
    print_ocr_config()
    
    # Télécharger le fichier
    upload_file(file_path, enable_ocr)

if __name__ == "__main__":
    main()
