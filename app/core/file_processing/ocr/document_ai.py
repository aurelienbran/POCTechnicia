"""
Module d'intégration avec Google Cloud Document AI.
Ce processeur OCR utilise l'API Document AI de Google Cloud pour l'extraction de texte
et la reconnaissance de documents.
"""

import os
import asyncio
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging
import tempfile
import time
from datetime import datetime

from .base import OCRProcessor, OCRResult

logger = logging.getLogger(__name__)

# Tentative d'importation des bibliothèques Document AI
try:
    from google.cloud import documentai_v1 as documentai
    from google.cloud.documentai_v1.types import Document
    from google.api_core.client_options import ClientOptions
    from google.api_core.exceptions import GoogleAPIError
    DOCUMENTAI_AVAILABLE = True
except ImportError:
    logger.warning("Google Cloud Document AI n'est pas disponible. "
                   "Installez-le avec: pip install google-cloud-documentai")
    DOCUMENTAI_AVAILABLE = False


class DocumentAIProcessor(OCRProcessor):
    """
    Processeur OCR utilisant Google Cloud Document AI.
    
    Cette classe fournit une interface pour traiter des documents avec l'API Document AI
    de Google Cloud Platform. Elle permet d'extraire du texte, des entités et des informations
    structurées à partir de documents, y compris des schémas techniques.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le processeur Document AI.
        
        Args:
            config: Configuration du processeur
                - project_id: ID du projet GCP (obligatoire)
                - location: Région GCP (défaut: 'eu')
                - processor_id: ID du processeur Document AI (obligatoire)
                - api_endpoint: Point de terminaison API (facultatif)
                - timeout: Timeout pour les requêtes API en secondes (défaut: 300)
        """
        super().__init__(config)
        self.client = None
        self.project_id = self.config.get("project_id")
        self.location = self.config.get("location", "eu")
        self.processor_id = self.config.get("processor_id")
        self.api_endpoint = self.config.get("api_endpoint")
        self.timeout = self.config.get("timeout", 300)
        
        # Valider la configuration minimale requise
        if not self.project_id:
            logger.warning("Project ID non spécifié pour Document AI")
        
        if not self.processor_id:
            logger.warning("Processor ID non spécifié pour Document AI")
    
    async def initialize(self) -> bool:
        """
        Initialise le client Document AI et vérifie la disponibilité du service.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if not DOCUMENTAI_AVAILABLE:
            logger.error("Google Cloud Document AI n'est pas disponible")
            return False
            
        try:
            # Vérifier que les variables d'environnement nécessaires sont définies
            if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                logger.error("La variable d'environnement GOOGLE_APPLICATION_CREDENTIALS n'est pas définie")
                return False
                
            if not self.project_id or not self.processor_id:
                logger.error("Configuration incomplète: project_id et processor_id sont requis")
                return False
            
            # Initialiser le client Document AI
            opts = ClientOptions(api_endpoint=self.api_endpoint) if self.api_endpoint else None
            
            # Exécuter dans un thread pour éviter de bloquer l'event loop
            loop = asyncio.get_event_loop()
            self.client = await loop.run_in_executor(
                None, 
                lambda: documentai.DocumentProcessorServiceClient(client_options=opts)
            )
            
            # Construire le nom complet du processeur
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            
            logger.info(f"Client Document AI initialisé avec succès. "
                        f"Processeur: {self.processor_name}")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Document AI: {str(e)}")
            return False
    
    async def process_document(self, 
                        input_file: Union[str, Path], 
                        output_file: Optional[Union[str, Path]] = None,
                        language: str = "fra",
                        **kwargs) -> OCRResult:
        """
        Traite un document avec Document AI.
        
        Args:
            input_file: Chemin vers le fichier d'entrée
            output_file: Chemin vers le fichier de sortie (optionnel)
            language: Code de langue pour l'OCR
            **kwargs: Options supplémentaires
                - mime_type: Type MIME du document (auto-détecté si non spécifié)
                - extract_tables: Extraire les tableaux (défaut: True)
                - extract_entities: Extraire les entités (défaut: False)
                - process_options: Options de traitement spécifiques à Document AI
                
        Returns:
            Résultat de l'opération OCR
        """
        if not self.is_initialized:
            logger.error("Document AI n'est pas initialisé")
            return OCRResult(
                success=False,
                error_message="Document AI n'est pas initialisé"
            )
        
        start_time = time.time()
        input_path = Path(input_file)
        
        if not input_path.exists():
            return OCRResult(
                success=False,
                error_message=f"Le fichier d'entrée n'existe pas: {input_path}"
            )
        
        # Définir le fichier de sortie si non spécifié
        if not output_file:
            output_file = input_path.with_suffix(".ai.pdf")
        output_path = Path(output_file)
        
        try:
            # Déterminer le type MIME si non spécifié
            mime_type = kwargs.get("mime_type")
            if not mime_type:
                if input_path.suffix.lower() == ".pdf":
                    mime_type = "application/pdf"
                elif input_path.suffix.lower() in [".jpg", ".jpeg"]:
                    mime_type = "image/jpeg"
                elif input_path.suffix.lower() == ".png":
                    mime_type = "image/png"
                elif input_path.suffix.lower() in [".tiff", ".tif"]:
                    mime_type = "image/tiff"
                else:
                    mime_type = "application/pdf"  # Valeur par défaut
            
            # Lire le contenu du fichier
            with open(input_path, "rb") as f:
                content = f.read()
            
            # Configurer la requête
            document = {"content": content, "mime_type": mime_type}
            
            # Récupérer les options de traitement
            process_options = kwargs.get("process_options", {})
            
            # Créer la requête
            request = {
                "name": self.processor_name,
                "raw_document": document,
                "process_options": process_options
            }
            
            # Exécuter l'appel API dans un thread pour éviter de bloquer
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.process_document(request=request, timeout=self.timeout)
            )
            
            # Extraire les données de la réponse
            document = response.document
            text_content = document.text
            
            # Créer des métadonnées riches
            metadata = {
                "mime_type": document.mime_type,
                "page_count": len(document.pages),
                "language_codes": document.pages[0].detected_languages[0].language_code if document.pages and document.pages[0].detected_languages else language,
                "processed_at": datetime.now().isoformat(),
                "processor_version": response.human_review_operation if hasattr(response, "human_review_operation") else "N/A"
            }
            
            # Extraire et ajouter les entités si demandé
            if kwargs.get("extract_entities", False) and document.entities:
                entities = []
                for entity in document.entities:
                    entities.append({
                        "type": entity.type_,
                        "mention_text": entity.mention_text,
                        "confidence": entity.confidence
                    })
                metadata["entities"] = entities
            
            # Extraire et ajouter les tableaux si demandé
            if kwargs.get("extract_tables", True):
                tables = []
                for page in document.pages:
                    for table in page.tables:
                        table_data = []
                        # Parcourir les lignes et colonnes
                        for row_idx in range(len(table.body_rows)):
                            row = []
                            for col_idx in range(len(table.header_rows[0].cells) if table.header_rows else 0):
                                if row_idx < len(table.body_rows) and col_idx < len(table.body_rows[row_idx].cells):
                                    cell = table.body_rows[row_idx].cells[col_idx]
                                    row.append(document.text[cell.layout.text_anchor.text_segments[0].start_index:
                                                            cell.layout.text_anchor.text_segments[0].end_index])
                                else:
                                    row.append("")
                            table_data.append(row)
                        tables.append(table_data)
                if tables:
                    metadata["tables"] = tables
            
            # Si un fichier de sortie a été spécifié, écrire le texte extrait
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
            
            # Calculer le temps de traitement
            processing_time = time.time() - start_time
            
            return OCRResult(
                success=True,
                output_path=output_path,
                text_content=text_content,
                pages_processed=len(document.pages),
                total_pages=len(document.pages),
                processing_time=processing_time,
                metadata=metadata
            )
            
        except GoogleAPIError as api_error:
            error_message = f"Erreur API Google Document AI: {str(api_error)}"
            logger.error(error_message)
            return OCRResult(
                success=False,
                error_message=error_message
            )
        except Exception as e:
            error_message = f"Erreur lors du traitement avec Document AI: {str(e)}"
            logger.error(error_message)
            return OCRResult(
                success=False,
                error_message=error_message
            )
    
    async def extract_text(self, 
                    document_path: Union[str, Path],
                    page_numbers: Optional[List[int]] = None) -> str:
        """
        Extrait le texte d'un document en utilisant Document AI.
        
        Args:
            document_path: Chemin vers le document
            page_numbers: Liste des numéros de page à extraire (None = toutes)
            
        Returns:
            Texte extrait du document
        """
        # Cette méthode peut réutiliser process_document et extraire le texte du résultat
        document_path = Path(document_path)
        
        # Si le fichier est déjà un fichier texte généré par Document AI
        if document_path.suffix.lower() == ".ai.pdf" or document_path.name.endswith(".txt"):
            try:
                return document_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Erreur lors de la lecture du fichier texte: {str(e)}")
                return ""
        
        # Sinon, traiter le document avec Document AI
        result = await self.process_document(document_path)
        
        if not result.success or not result.text_content:
            logger.error(f"Échec de l'extraction de texte: {result.error_message}")
            return ""
        
        # Filtrer par numéros de page si spécifiés
        if page_numbers and result.metadata and "page_count" in result.metadata:
            # Cette implémentation simplifie l'extraction par page
            # Une implémentation complète nécessiterait de connaître les limites de chaque page
            # dans le texte extrait, ce qui dépend de l'API Document AI
            logger.warning("L'extraction par numéro de page n'est pas entièrement supportée "
                           "avec Document AI dans cette version")
        
        return result.text_content or ""
    
    async def needs_ocr(self, document_path: Union[str, Path]) -> bool:
        """
        Détermine si un document nécessite un traitement OCR.
        Document AI traite tous les documents, mais cette méthode peut être utilisée
        pour déterminer si un traitement supplémentaire est nécessaire.
        
        Args:
            document_path: Chemin vers le document
            
        Returns:
            True si le document nécessite un OCR spécifique, False sinon
        """
        document_path = Path(document_path)
        
        # Si ce n'est pas un PDF, on considère qu'il nécessite un OCR
        if document_path.suffix.lower() != ".pdf":
            return True
            
        # Heuristique pour les PDF : Document AI peut traiter tous les types de PDF,
        # mais pour l'optimisation, on peut vérifier s'il contient déjà du texte
        # Cette logique peut être affinée selon les besoins
        try:
            # Réutiliser la logique existante dans d'autres processeurs OCR si disponible
            from .ocrmypdf import check_pdf_needs_ocr
            return await check_pdf_needs_ocr(document_path)
        except ImportError:
            # Implémentation simplifiée si check_pdf_needs_ocr n'est pas disponible
            try:
                import PyPDF2
                with open(document_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    # Vérifier la première page
                    if reader.pages and len(reader.pages) > 0:
                        text = reader.pages[0].extract_text().strip()
                        # Si la page contient du texte, on considère que l'OCR n'est pas nécessaire
                        return len(text) == 0
                    return True  # En cas de doute, on considère qu'il nécessite un OCR
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du PDF: {str(e)}")
                return True  # En cas d'erreur, on considère qu'il nécessite un OCR
    
    @property
    def provider_name(self) -> str:
        """
        Nom du provider OCR.
        
        Returns:
            "document_ai"
        """
        return "document_ai"
