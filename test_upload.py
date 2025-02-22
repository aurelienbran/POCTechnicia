import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_upload():
    url = "http://localhost:8000/api/v1/documents"
    file_path = "D:/Projets/POC TECHNICIA/fe.pdf"
    
    logger.info(f"Test d'upload du fichier: {file_path}")
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": ("fe.pdf", f, "application/pdf")}
            logger.info("Envoi de la requête...")
            response = requests.post(url, files=files)
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            if response.status_code == 200:
                logger.info("Upload réussi!")
            else:
                logger.error(f"Erreur lors de l'upload: {response.text}")
    
    except Exception as e:
        logger.error(f"Exception: {str(e)}")
        logger.error(f"Type d'erreur: {type(e).__name__}")

if __name__ == "__main__":
    test_upload()
