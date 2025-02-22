from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from app.core.vector_store import VectorStore
from app.core.llm_interface import LLMInterface
from app.core.pdf_processor import PDFProcessor
import logging
from pathlib import Path
import asyncio

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

    async def process_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Traite un nouveau document PDF et l'indexe dans le vector store.
        
        Args:
            file_path: Chemin vers le fichier PDF à traiter
        
        Returns:
            Dict contenant les statistiques du traitement
        """
        try:
            # Extraire les métadonnées du PDF
            metadata = await self.pdf_processor.extract_metadata(file_path)
            logger.info(f"Métadonnées extraites pour {file_path}")
            
            # Traiter le PDF en une seule fois
            chunks = []
            async for chunk in self._process_pdf_chunks(file_path):
                chunks.append(chunk)
            
            if not chunks:
                logger.warning("Aucun chunk extrait du PDF")
                return {
                    'document': str(file_path),
                    'chunks_processed': 0,
                    'chunks_indexed': 0,
                    'success_rate': 0,
                    'metadata': metadata
                }
            
            # Préparer les données pour l'indexation
            texts = []
            chunk_metadata = []
            
            for i, chunk in enumerate(chunks):
                texts.append(chunk['text'])
                chunk_metadata.append({
                    **metadata,
                    'chunk_number': i + 1,
                    'total_chunks': len(chunks),
                    **chunk
                })
            
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
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du document : {str(e)}", exc_info=True)
            raise

    async def _process_pdf_chunks(self, file_path: Path) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Wrapper autour de process_pdf pour gérer correctement le générateur asynchrone.
        """
        processor = self.pdf_processor.process_pdf(file_path)
        async for chunk in processor:
            yield chunk

    async def query(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Traite une requête et génère une réponse basée sur le contexte.
        
        Args:
            query: La requête de l'utilisateur
            k: Nombre de documents à récupérer
            filter: Filtre optionnel pour la recherche
        
        Returns:
            Dict contenant la réponse et les questions de suivi
        """
        try:
            # Rechercher les documents pertinents
            context_docs = await self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter
            )

            # Générer la réponse
            response = await self.llm_interface.generate_response(
                query=query,
                context_docs=context_docs
            )

            # Générer des questions de suivi
            follow_up_questions = await self.llm_interface.generate_follow_up_questions(
                query=query,
                context_docs=context_docs,
                previous_response=response
            )

            # Préparer les sources utilisées
            sources = []
            seen_sources = set()
            for doc in context_docs:
                source = doc["metadata"].get("source", "")
                if source and source not in seen_sources and doc["score"] >= 0.7:
                    sources.append({
                        "file": source,
                        "score": doc["score"]
                    })
                    seen_sources.add(source)

            return {
                "query": query,
                "answer": response,
                "follow_up_questions": follow_up_questions,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Erreur lors du traitement de la requête: {str(e)}")
            raise

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
