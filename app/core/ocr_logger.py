"""
Module pour améliorer le logging et le suivi du processus OCR.
"""
import logging
import asyncio
import time
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Union

try:
    import fitz  # PyMuPDF
except ImportError:
    pass  # Gestion de l'absence de PyMuPDF

logger = logging.getLogger(__name__)

class OCRProgressTracker:
    """Classe pour suivre la progression de l'OCR."""
    
    def __init__(self, websocket_manager=None, update_status_func=None):
        """
        Initialisation du tracker de progression OCR.
        
        Args:
            websocket_manager: Gestionnaire WebSocket pour diffuser les mises à jour
            update_status_func: Fonction pour mettre à jour le statut d'indexation
        """
        self.websocket_manager = websocket_manager
        self.update_status_func = update_status_func
        self.current_file = None
        self.file_stats = {
            "current_page": 0,
            "total_pages": 0,
            "progress": 0,
            "start_time": None,
            "logs": []
        }
    
    async def log_ocr_event(self, message: str, level: str = "INFO") -> None:
        """
        Enregistre un événement OCR et le diffuse via WebSocket si disponible.
        
        Args:
            message: Message à enregistrer
            level: Niveau de log (INFO, WARNING, ERROR, DEBUG)
        """
        # Ajouter le préfixe OCR
        full_message = f"[OCR] {message}"
        
        # Logger avec le niveau approprié
        if level == "INFO":
            logger.info(full_message)
        elif level == "WARNING":
            logger.warning(full_message)
        elif level == "ERROR":
            logger.error(full_message)
        elif level == "DEBUG":
            logger.debug(full_message)
        
        # Ajouter au buffer de logs
        self.file_stats["logs"].append({
            "message": full_message,
            "level": level,
            "timestamp": time.time()
        })
        
        # Limiter la taille du buffer
        if len(self.file_stats["logs"]) > 50:
            self.file_stats["logs"] = self.file_stats["logs"][-50:]
        
        # Diffuser via WebSocket si disponible
        if self.websocket_manager:
            log_entry = {
                "type": "log",
                "level": level,
                "message": full_message,
                "timestamp": time.time(),
                "source": "OCR"
            }
            
            # Ajouter informations de progression si disponibles
            if self.file_stats["current_page"] > 0:
                log_entry.update({
                    "current_page": self.file_stats["current_page"],
                    "total_pages": self.file_stats["total_pages"],
                    "progress": self.file_stats["progress"],
                    "step": "ocr"
                })
            
            await self.websocket_manager.broadcast(log_entry)
        
        # Mettre à jour le statut d'indexation si la fonction est disponible
        if self.update_status_func and self.file_stats["current_page"] > 0:
            await self.update_status_func(status_data={
                "current_step": "ocr",
                "ocr_in_progress": True,
                "ocr_progress": self.file_stats["progress"],
                "ocr_current_page": self.file_stats["current_page"],
                "ocr_total_pages": self.file_stats["total_pages"],
                "ocr_logs": [full_message]
            })
    
    async def start_ocr_tracking(self, file_path: Union[str, Path]) -> None:
        """
        Commence à suivre le processus OCR pour un fichier.
        
        Args:
            file_path: Chemin vers le fichier en cours de traitement
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        self.current_file = file_path
        self.file_stats["start_time"] = time.time()
        self.file_stats["current_page"] = 0
        self.file_stats["progress"] = 0
        
        # Estimer le nombre total de pages
        try:
            import fitz
            doc = fitz.open(str(file_path))
            self.file_stats["total_pages"] = len(doc)
            doc.close()
        except Exception as e:
            await self.log_ocr_event(f"Impossible d'estimer le nombre de pages: {e}", "WARNING")
            self.file_stats["total_pages"] = 0
        
        await self.log_ocr_event(
            f"Démarrage du processus OCR pour {file_path.name} "
            f"({self.file_stats['total_pages']} pages)"
        )
        
        # Mettre à jour le statut d'indexation
        if self.update_status_func:
            await self.update_status_func(status_data={
                "current_step": "ocr",
                "ocr_in_progress": True,
                "ocr_progress": 0,
                "ocr_current_page": 0,
                "ocr_total_pages": self.file_stats["total_pages"],
                "ocr_start_time": self.file_stats["start_time"],
                "ocr_logs": [f"Démarrage OCR pour {file_path.name}"]
            })
    
    async def update_ocr_progress(self, current_page: int, message: str = None) -> None:
        """
        Met à jour la progression OCR.
        
        Args:
            current_page: Page actuelle en cours de traitement
            message: Message optionnel à logger
        """
        self.file_stats["current_page"] = current_page
        
        # Calculer le pourcentage de progression
        if self.file_stats["total_pages"] > 0:
            raw_progress = (current_page / self.file_stats["total_pages"]) * 90
            self.file_stats["progress"] = min(int(raw_progress), 99)
        else:
            # Si nous ne connaissons pas le nombre total de pages, estimons une progression
            self.file_stats["progress"] = min(current_page * 5, 99)
        
        log_message = message or f"OCR: traitement de la page {current_page}"
        if self.file_stats["total_pages"] > 0:
            log_message += f"/{self.file_stats['total_pages']} ({self.file_stats['progress']}%)"
        
        await self.log_ocr_event(log_message)
    
    async def complete_ocr_tracking(self, success: bool = True, error_message: str = None) -> None:
        """
        Termine le suivi OCR pour le fichier courant.
        
        Args:
            success: Si l'OCR s'est terminé avec succès
            error_message: Message d'erreur si échec
        """
        if not self.current_file:
            return
        
        end_time = time.time()
        duration = end_time - (self.file_stats["start_time"] or end_time)
        
        if success:
            self.file_stats["progress"] = 100
            await self.log_ocr_event(
                f"OCR terminé avec succès pour {self.current_file.name} "
                f"en {duration:.2f} secondes"
            )
        else:
            await self.log_ocr_event(
                f"OCR échoué pour {self.current_file.name}: {error_message}", "ERROR"
            )
        
        # Mettre à jour le statut d'indexation
        if self.update_status_func:
            await self.update_status_func(status_data={
                "current_step": "indexing" if success else "error",
                "ocr_in_progress": False,
                "ocr_progress": 100 if success else self.file_stats["progress"],
                "ocr_logs": [f"OCR {'terminé avec succès' if success else 'échoué'} pour {self.current_file.name}"]
            })
        
        # Réinitialiser le suivi
        self.current_file = None

class OCROutputCapture:
    """Classe pour capturer et analyser la sortie d'OCRmyPDF."""
    
    def __init__(self, tracker: OCRProgressTracker = None):
        """
        Initialise le capteur de sortie OCR.
        
        Args:
            tracker: Tracker de progression OCR
        """
        self.tracker = tracker
        self.buffer = []
        self.original_stdout = sys.stdout
    
    def __enter__(self):
        """Commence à capturer la sortie."""
        sys.stdout = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Arrête la capture et restaure stdout."""
        sys.stdout = self.original_stdout
    
    def write(self, data):
        """
        Écrit les données dans le buffer et analyse pour la progression.
        
        Args:
            data: Données à écrire
        """
        # Écrire dans stdout original et buffer
        self.original_stdout.write(data)
        self.buffer.append(data)
        
        # Analyser la sortie pour la progression
        if self.tracker:
            self.parse_ocr_output(data)
    
    def flush(self):
        """Flush le buffer."""
        self.original_stdout.flush()
    
    def parse_ocr_output(self, line: str):
        """
        Analyse la sortie OCRmyPDF pour extraire les informations de progression.
        
        Args:
            line: Ligne de sortie à analyser
        """
        if not self.tracker:
            return
        
        # Format typique: "Processing page 5 of 42..."
        page_match = re.search(r'[Pp]rocessing page (\d+) of (\d+)', line)
        if page_match:
            try:
                current_page = int(page_match.group(1))
                total_pages = int(page_match.group(2))
                
                # Mettre à jour le tracker asynchronely
                asyncio.create_task(self.tracker.update_ocr_progress(current_page))
            except (ValueError, IndexError):
                pass


# Singleton global pour le tracker
ocr_tracker = None

def get_ocr_tracker(websocket_manager=None, update_status_func=None):
    """
    Retourne l'instance singleton du tracker OCR.
    
    Args:
        websocket_manager: Gestionnaire WebSocket pour diffuser les mises à jour
        update_status_func: Fonction pour mettre à jour le statut d'indexation
        
    Returns:
        OCRProgressTracker: L'instance du tracker
    """
    global ocr_tracker
    
    if ocr_tracker is None:
        ocr_tracker = OCRProgressTracker(websocket_manager, update_status_func)
    
    return ocr_tracker
