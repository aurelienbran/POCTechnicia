import requests
import os
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_server():
    """Vérifie si le serveur est disponible."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def upload_file(file_path):
    """Upload un fichier PDF au serveur."""
    if not os.path.exists(file_path):
        logger.error(f"Le fichier {file_path} n'existe pas")
        return False
        
    if not check_server():
        logger.error("Le serveur FastAPI n'est pas accessible")
        return False

    url = "http://localhost:8000/api/v1/documents"
    
    try:
        logger.info(f"Envoi du fichier {file_path}")
        with open(file_path, 'rb') as f:
            response = requests.post(
                url,
                files={'file': (os.path.basename(file_path), f, 'application/pdf')},
                timeout=5  # 5 secondes max
            )

        if response.status_code == 409:
            logger.error("Un document est déjà en cours de traitement")
            return False
            
        if response.status_code == 202:
            logger.info("Document accepté pour traitement")
            logger.info(f"Réponse: {response.json()}")
            return True
            
        logger.error(f"Erreur {response.status_code}: {response.text}")
        return False
        
    except requests.Timeout:
        logger.error("Le serveur ne répond pas (timeout)")
        return False
    except requests.ConnectionError:
        logger.error("Impossible de se connecter au serveur")
        return False
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== Début de l'upload ===")
    success = upload_file(r"D:\Projets\POC TECHNICIA\tests\performance\test_files\el.pdf")
    logger.info("=== Fin de l'upload ===")
    exit(0 if success else 1)
