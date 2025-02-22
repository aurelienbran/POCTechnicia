"""Configuration de l'application."""
from pydantic import BaseModel
from typing import List
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Charger les variables d'environnement seulement si on n'est pas en test
if os.getenv("TESTING") != "true":
    env_path = Path(__file__).parent.parent / '.env'
    print(f"DEBUG: Loading .env from: {env_path}")
    # Forcer le rechargement des variables d'environnement
    load_dotenv(dotenv_path=env_path, override=True)

# Créer le répertoire logs s'il n'existe pas
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / "app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class Settings(BaseModel):
    """Configuration de l'application."""
    
    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    VOYAGE_API_KEY: str = os.getenv("VOYAGE_API_KEY", "")
    
    # Qdrant Configuration
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "documents")
    
    # App Configuration
    print(f"DEBUG: Raw MAX_UPLOAD_SIZE value: {os.getenv('MAX_UPLOAD_SIZE')}")
    # Utiliser directement la valeur par défaut si la variable n'est pas définie
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE") or "157286400")  # 150 MB
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    MAX_MEMORY_MB: int = int(os.getenv("MAX_MEMORY_MB", "1024"))
    
    # Security
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8000"]
    
    # Paths
    UPLOAD_DIR: Path = Path("uploads").absolute()
    STORAGE_DIR: Path = Path("storage").absolute()

# Create required directories
os.makedirs(Settings().UPLOAD_DIR, exist_ok=True)
os.makedirs(Settings().STORAGE_DIR, exist_ok=True)

# Instance singleton des paramètres
settings = Settings()
