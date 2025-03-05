from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from app.core.vector_store import VectorStore
from app.core.llm_interface import LLMInterface
from app.core.pdf_processor import PDFProcessor
from app.core.question_classifier import QuestionType
import logging
from pathlib import Path
import asyncio
import time
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        llm_interface: Optional[LLMInterface] = None,
        collection_name: str = "documents"
    ):
        """
        Initialise le moteur RAG avec ses composants.
        
        Args:
            vector_store: Instance de VectorStore à utiliser
            llm_interface: Instance de LLMInterface à utiliser
            collection_name: Nom de la collection Qdrant à utiliser si vector_store n'est pas fourni
        """
        # Créer d'abord le LLMInterface s'il n'existe pas
        self.llm_interface = llm_interface or LLMInterface()
        
        # Ensuite créer le VectorStore en lui passant le LLMInterface
        self.vector_store = vector_store or VectorStore(
            collection_name=collection_name,
            llm_interface=self.llm_interface
        )
        
        self.pdf_processor = PDFProcessor()

    async def initialize(self) -> None:
        """
        Initialise le RAGEngine.
        Cette méthode doit être appelée avant d'utiliser la classe.
        """
        try:
            await self.vector_store.ensure_initialized()
            logger.info("RAGEngine initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du RAGEngine: {str(e)}")
            raise

    async def _process_document(self, file_path: Path, collection_name: str, apply_ocr: bool = False) -> Dict[str, Any]:
        """
        Traite un document (PDF, texte, Word, etc.) et l'ajoute à la collection spécifiée.
        
        Args:
            file_path: Chemin vers le fichier à traiter
            collection_name: Nom de la collection où ajouter le document
            apply_ocr: Indique si l'OCR doit être appliqué aux documents qui en ont besoin
            
        Returns:
            Informations sur le document traité
        """
        file_extension = file_path.suffix.lower()
        document_info = {
            "id": file_path.stem,
            "filename": file_path.name,
            "file_extension": file_extension,
            "path": str(file_path),
            "size": file_path.stat().st_size,
            "chunks": 0,
            "needs_ocr": False,
            "applied_ocr": False
        }
        
        try:
            # Vérifier si le document a besoin d'OCR (uniquement pour les PDFs pour l'instant)
            needs_ocr = False
            if file_extension == ".pdf":
                # Utiliser PyMuPDF pour vérifier rapidement si le document contient du texte
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(str(file_path))
                    
                    # Vérifier les premières pages (jusqu'à 3) pour voir si elles contiennent du texte
                    text_content = ""
                    pages_to_check = min(3, doc.page_count)
                    
                    for i in range(pages_to_check):
                        page_text = doc[i].get_text().strip()
                        text_content += page_text
                    
                    # Si moins de 100 caractères pour les 3 premières pages, c'est probablement un scan
                    needs_ocr = len(text_content) < 100
                    doc.close()
                    
                    logger.info(f"Détection OCR pour {file_path.name}: {'Nécessaire' if needs_ocr else 'Non nécessaire'}")
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification OCR: {str(e)}")
            
            document_info["needs_ocr"] = needs_ocr
            
            # Appliquer l'OCR si nécessaire et demandé
            if needs_ocr and apply_ocr and file_extension == ".pdf":
                try:
                    logger.info(f"Application de l'OCR au fichier {file_path.name}")
                    
                    # Vérifier si les dépendances OCR sont disponibles
                    if OCRHelper.verify_dependencies():
                        # Appliquer l'OCR
                        ocr_file_path = await OCRHelper.apply_ocr(file_path)
                        
                        if ocr_file_path != file_path:
                            logger.info(f"OCR appliqué avec succès: {ocr_file_path}")
                            document_info["applied_ocr"] = True
                            document_info["original_path"] = str(file_path)
                            document_info["path"] = str(ocr_file_path)
                            # Utiliser le fichier OCR pour le traitement ultérieur
                            file_path = ocr_file_path
                        else:
                            logger.warning(f"OCR demandé mais non appliqué pour {file_path.name}")
                    else:
                        logger.error("Dépendances OCR manquantes. L'OCR ne sera pas appliqué.")
                except Exception as e:
                    logger.error(f"Erreur lors de l'application de l'OCR: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # Traiter le document selon son type
            count = 0
            
            if file_extension == ".pdf":
                processor = PDFProcessor(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
                async for chunk in processor.process_pdf(file_path):
                    # Ajouter les métadonnées communes à tous les chunks
                    chunk["metadata"]["collection_name"] = collection_name
                    chunk["metadata"]["applied_ocr"] = document_info.get("applied_ocr", False)
                    
                    # Ajouter le chunk à l'index
                    await self.vector_store.add_text(
                        collection_name=collection_name,
                        document_id=chunk["id"],
                        text=chunk["text"],
                        metadata=chunk["metadata"]
                    )
                    count += 1
            else:
                logger.warning(f"Type de fichier non supporté: {file_extension}")
            
            document_info["chunks"] = count
            logger.info(f"{count} chunks ajoutés pour {file_path.name}")
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du document {file_path.name}: {str(e)}")
            logger.error(traceback.format_exc())
            document_info["error"] = str(e)
        
        return document_info

    async def process_document(self, file_path: Path, enable_ocr: bool = True) -> Dict[str, Any]:
        """
        Traite un nouveau document PDF et l'indexe dans le vector store.
        
        Args:
            file_path: Chemin vers le fichier PDF à traiter
            enable_ocr: Si True, détecte et applique automatiquement l'OCR si nécessaire
        
        Returns:
            Dict contenant les statistiques du traitement
        """
        try:
            processed_file = file_path
            ocr_applied = False
            
            # Vérifier et appliquer l'OCR si activé
            if enable_ocr:
                try:
                    from app.core.ocr_helper import OCRHelper
                    
                    # Vérifier si le PDF nécessite OCR
                    logger.info(f"Vérification du besoin d'OCR pour {file_path.name}")
                    needs_ocr = await OCRHelper.needs_ocr(file_path)
                    
                    if needs_ocr:
                        # Appliquer l'OCR
                        logger.info(f"Application de l'OCR à {file_path.name}")
                        processed_file = await OCRHelper.apply_ocr(file_path)
                        ocr_applied = processed_file != file_path
                        if ocr_applied:
                            logger.info(f"OCR appliqué: {file_path.name} -> {processed_file.name}")
                    else:
                        logger.info(f"OCR non nécessaire pour {file_path.name}")
                except Exception as e:
                    logger.error(f"Erreur lors du traitement OCR: {str(e)}")
                    # Continuer avec le fichier original
            
            # Extraire les métadonnées du PDF
            metadata = await self.pdf_processor.extract_metadata(processed_file)
            logger.info(f"Métadonnées extraites pour {processed_file}")
            
            # Traiter le PDF en une seule fois
            chunks = []
            async for chunk in self._process_pdf_chunks(processed_file):
                chunks.append(chunk)
            
            if not chunks:
                logger.warning("Aucun chunk extrait du PDF")
                return {
                    'document': str(file_path),
                    'chunks_processed': 0,
                    'chunks_indexed': 0,
                    'success_rate': 0,
                    'metadata': metadata,
                    'ocr_applied': ocr_applied if enable_ocr else False
                }
            
            # Préparer les données pour l'indexation
            texts = []
            chunk_metadata = []
            
            for i, chunk in enumerate(chunks):
                texts.append(chunk['text'])  # Utiliser 'text' au lieu de 'content'
                metadata_entry = {
                    **metadata,
                    'chunk_number': i + 1,
                    'total_chunks': len(chunks),
                }
                # Ajouter les informations OCR aux métadonnées si pertinent
                if enable_ocr:
                    metadata_entry['ocr_checked'] = True
                    metadata_entry['ocr_applied'] = ocr_applied
                
                chunk_metadata.append({**metadata_entry, **chunk})
            
            # Indexer tous les chunks
            logger.info(f"Indexation de {len(texts)} chunks")
            point_ids = await self.vector_store.add_texts(texts, chunk_metadata)
            
            # Calculer les statistiques
            total_chunks = len(chunks)
            total_indexed = len(point_ids)
            success_rate = total_indexed / total_chunks if total_chunks > 0 else 0
            
            logger.info(f"Document traité : {total_indexed}/{total_chunks} chunks indexés ({success_rate*100:.1f}%)")
            
            return {
                'document': str(file_path),
                'chunks_processed': total_chunks,
                'chunks_indexed': total_indexed,
                'success_rate': success_rate,
                'metadata': metadata,
                'ocr_applied': ocr_applied if enable_ocr else False
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du document : {str(e)}", exc_info=True)
            raise

    async def index_document(self, file_path: Path, filename: str, progress_callback=None) -> Dict[str, Any]:
        """
        Indexe un document PDF dans le vector store.
        Cette méthode est un alias pour process_document, ajoutée pour compatibilité avec router.py.
        
        Args:
            file_path (Path): Chemin vers le fichier PDF à traiter
            filename (str): Nom original du fichier (utilisé pour les métadonnées)
            progress_callback (callable, optional): Fonction de callback pour suivre la progression
            
        Returns:
            dict: Statistiques sur le traitement du document
        """
        start_time = time.time()
        logger.info(f"Indexation du document: {filename}")
        
        # Étape initiale du callback si disponible
        if progress_callback:
            await progress_callback(
                in_progress=True,
                indexed_chunks=0,
                total_chunks=0,
                current_file=filename,
                current_step="initializing"
            )
        
        try:
            # Étape 1: Traitement OCR et extraction des chunks via process_document
            logger.info(f"Étape 1/3: Traitement OCR et extraction du texte pour {filename}")
            if progress_callback:
                await progress_callback(
                    in_progress=True,
                    indexed_chunks=0, 
                    total_chunks=0,
                    current_file=filename,
                    current_step="preprocessing"
                )
            
            result = await self.process_document(
                file_path=file_path,
                enable_ocr=True  # On active l'OCR par défaut comme dans router.py
            )
            
            # Vérification des résultats du traitement
            chunks_processed = result.get("chunks_processed", 0)
            chunks_indexed = result.get("chunks_indexed", 0)
            ocr_applied = result.get("ocr_applied", False)
            
            # Si aucun chunk n'a été extrait, on termine rapidement
            if chunks_processed == 0:
                logger.warning(f"Aucun chunk extrait du document {filename}")
                if progress_callback:
                    await progress_callback(
                        in_progress=False,
                        indexed_chunks=0,
                        total_chunks=0,
                        current_file=filename,
                        current_step="completed",
                        error=f"Aucun contenu extractible dans {filename}"
                    )
                return {
                    "chunks_indexed": 0,
                    "total_chunks": 0,
                    "processing_time": time.time() - start_time,
                    "filename": filename,
                    "ocr_applied": ocr_applied
                }
            
            # Étape 2: Mise à jour de progression pour montrer que process_document est terminé
            logger.info(f"Étape 2/3: Traitement terminé, {chunks_processed} chunks extraits")
            if progress_callback:
                await progress_callback(
                    in_progress=True,
                    indexed_chunks=chunks_indexed,
                    total_chunks=chunks_processed,
                    current_file=filename,
                    current_step="processing",
                    processing_stats={
                        "chunks_processed": chunks_processed,
                        "chunks_indexed": chunks_indexed,
                        "ocr_applied": ocr_applied
                    }
                )
            
            # Étape 3: Notification finale - simule une progression même si process_document a déjà indexé
            processing_time = time.time() - start_time
            logger.info(f"Étape 3/3: Indexation terminée pour {filename} en {processing_time:.2f} secondes")
            
            # Construire les statistiques à retourner (format attendu par router.py)
            stats = {
                "chunks_indexed": chunks_indexed,
                "total_chunks": chunks_processed,
                "processing_time": processing_time,
                "filename": filename,
                "ocr_applied": ocr_applied
            }
            
            # Appeler le callback de progression final si fourni
            if progress_callback:
                await progress_callback(
                    in_progress=False,
                    indexed_chunks=chunks_indexed,
                    total_chunks=chunks_processed,
                    current_file=filename,
                    current_step="completed",
                    processing_stats=stats
                )
            
            logger.info(f"Indexation terminée avec succès: {chunks_indexed}/{chunks_processed} chunks pour {filename}")
            return stats
            
        except Exception as e:
            # Gestion des erreurs et notification via callback
            error_msg = f"Erreur lors de l'indexation de {filename}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            if progress_callback:
                await progress_callback(
                    in_progress=False,
                    indexed_chunks=0,
                    total_chunks=0,
                    current_file=filename,
                    current_step="error",
                    error=error_msg
                )
            
            # Propager l'erreur avec plus de détails
            raise RuntimeError(error_msg)

    async def _process_pdf_chunks(self, file_path: Path) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Wrapper autour de process_pdf pour gérer correctement le générateur asynchrone.
        """
        processor = self.pdf_processor.process_pdf(file_path)
        async for chunk in processor:
            yield chunk

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def query(self, query: str, k: int = 10, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Traite une requête utilisateur.
        
        Args:
            query: La question de l'utilisateur
            k: Nombre de documents similaires à récupérer
            filter: Filtres optionnels pour la recherche
            
        Returns:
            Dict contenant la réponse et les métadonnées
        """
        start_time = time.time()
        logger.info(f"Début du traitement de la requête: {query}")
        
        try:
            # Classifier la question
            try:
                question_type = await self.llm_interface.classifier.classify(query)
                logger.info(f"Question classifiée comme: {question_type}")
            except Exception as e:
                logger.error(f"Erreur lors de la classification: {str(e)}")
                question_type = QuestionType.TECHNIQUE
            
            # Récupérer le contexte uniquement pour les questions techniques
            context_docs = None
            if question_type == QuestionType.TECHNIQUE:
                try:
                    context_docs = await self.vector_store.similarity_search(query, k=k, filter=filter)
                    logger.info(f"Contexte récupéré: {len(context_docs)} documents")
                    # Ajout de logs détaillés sur les scores de similarité
                    if context_docs and len(context_docs) > 0:
                        similarity_scores = [f'{doc.get("score", 0):.2f}' for doc in context_docs[:5]]
                        logger.info(f"Scores de similarité (top 5): {similarity_scores}")
                except Exception as e:
                    logger.error(f"Erreur lors de la recherche de contexte: {str(e)}")
                    context_docs = []
            
            # Générer la réponse
            try:
                response = await self.llm_interface.generate_response(query, context_docs, question_type)
            except Exception as e:
                logger.error(f"Erreur lors de la génération de réponse: {str(e)}")
                raise RuntimeError("Une erreur est survenue lors de la génération de la réponse. Veuillez réessayer.")
            
            # Préparer la réponse
            result = {
                "query": query,
                "answer": response,
                "sources": self._extract_sources(context_docs) if context_docs else [],
                "processing_time": round(time.time() - start_time, 2)
            }
            
            logger.info(f"Requête traitée en {result['processing_time']} secondes")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la requête: {str(e)}")
            raise RuntimeError("Une erreur est survenue lors du traitement de votre requête. Veuillez réessayer.")

    def _extract_sources(self, context_docs: List[Dict]) -> List[Dict]:
        """Extrait les sources pertinentes des documents de contexte."""
        sources = []
        seen_sources = set()
        
        for doc in context_docs:
            metadata = doc.get("metadata", {})
            source = metadata.get("source", "")
            score = doc.get("score", 0)
            page = metadata.get("page", "")
            section = metadata.get("section", "")
            
            if source and source not in seen_sources and score >= 0.4:  
                source_info = {
                    "file": source,
                    "score": score,
                }
                
                # Ajouter les informations contextuelles si disponibles
                if page:
                    source_info["page"] = page
                if section:
                    source_info["section"] = section
                    
                sources.append(source_info)
                seen_sources.add(source)
        
        # Trier les sources par score
        return sorted(sources, key=lambda x: x["score"], reverse=True)

    async def get_document_summary(self, file_path: Path) -> str:
        """
        Génère un résumé d'un document.
        
        Args:
            file_path: Chemin vers le document à résumer
        
        Returns:
            str: Le résumé du document
        """
        try:
            # Extraire le texte du document
            text = ""
            async for chunk in self.pdf_processor.process_pdf(file_path):
                text += chunk + "\n"
            
            # Générer le résumé
            summary = await self.llm_interface.summarize_document(text)
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé pour {file_path}: {str(e)}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques de la collection.
        
        Returns:
            Dict contenant les statistiques
        """
        try:
            return self.vector_store.get_collection_info()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
            raise
