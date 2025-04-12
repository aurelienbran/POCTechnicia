"""
Module d'intégration pour le traitement complet des documents.
Coordonne les différents services (conversion, OCR, chunking) dans un flux de travail unifié.
"""

import logging
import time
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, BinaryIO, Tuple

from app.config import settings
from app.core.file_processing.conversion import get_document_converter, ConversionResult
from app.core.file_processing.chunking import get_text_chunker, ChunkingResult
from app.core.file_processing.ocr import get_ocr_processor

logger = logging.getLogger(__name__)

class DocumentProcessingResult:
    """Résultat du traitement complet d'un document."""
    
    def __init__(self, 
                success: bool,
                chunks: List[str] = None,
                text_content: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None,
                error_message: Optional[str] = None):
        """
        Initialise le résultat du traitement.
        
        Args:
            success: Succès de l'opération
            chunks: Liste des chunks générés
            text_content: Contenu textuel extrait
            metadata: Métadonnées du traitement
            error_message: Message d'erreur le cas échéant
        """
        self.success = success
        self.chunks = chunks or []
        self.text_content = text_content
        self.metadata = metadata or {}
        self.error_message = error_message
        
        # Ajouter des métriques utiles
        if self.text_content:
            self.metadata["text_length"] = len(self.text_content)
            self.metadata["words_count"] = len(self.text_content.split())
        
        if self.chunks:
            self.metadata["chunks_count"] = len(self.chunks)
            self.metadata["avg_chunk_size"] = sum(len(chunk) for chunk in self.chunks) / len(self.chunks) if self.chunks else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le résultat en dictionnaire.
        
        Returns:
            Dictionnaire du résultat
        """
        result = {
            "success": self.success,
            "chunks_count": len(self.chunks),
            "metadata": self.metadata,
        }
        
        if self.text_content:
            result["text_content_preview"] = self.text_content[:500] + "..." if len(self.text_content) > 500 else self.text_content
            result["text_length"] = len(self.text_content)
        
        if self.error_message:
            result["error_message"] = self.error_message
            
        return result
    
    def __str__(self) -> str:
        """
        Représentation sous forme de chaîne.
        
        Returns:
            Description du résultat
        """
        if not self.success:
            return f"Échec du traitement: {self.error_message}"
            
        chunks_info = f"{len(self.chunks)} chunks générés" if self.chunks else "Aucun chunk"
        text_info = f"{len(self.text_content)} caractères extraits" if self.text_content else "Pas de texte"
        
        return f"Traitement réussi: {text_info}, {chunks_info}"

class DocumentProcessor:
    """
    Processeur de documents qui coordonne les différentes étapes de traitement.
    Gère le flux complet: conversion de document → extraction de texte → OCR si nécessaire → chunking.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le processeur de documents.
        
        Args:
            config: Configuration du processeur
                - converter_provider: Provider pour la conversion (défaut: 'standard')
                - chunker_provider: Provider pour le chunking (défaut: 'simple')
                - ocr_provider: Provider pour l'OCR (défaut: 'ocrmypdf')
                - enable_ocr: Activer l'OCR pour les documents numérisés (défaut: True)
                - default_chunk_size: Taille par défaut des chunks (défaut: 1000)
                - default_chunk_overlap: Chevauchement par défaut des chunks (défaut: 100)
                - extract_metadata: Extraire les métadonnées des documents (défaut: True)
        """
        self.config = config or {}
        
        # Configuration par défaut
        self.converter_provider = self.config.get('converter_provider', 
                                                 getattr(settings, 'DOCUMENT_CONVERTER_PROVIDER', 'standard'))
        self.chunker_provider = self.config.get('chunker_provider', 
                                               getattr(settings, 'TEXT_CHUNKER_PROVIDER', 'simple'))
        self.ocr_provider = self.config.get('ocr_provider', 
                                           getattr(settings, 'OCR_PROCESSOR_PROVIDER', 'ocrmypdf'))
        
        # Options de traitement
        self.enable_ocr = self.config.get('enable_ocr', True)
        self.default_chunk_size = self.config.get('default_chunk_size', 
                                                 getattr(settings, 'DEFAULT_CHUNK_SIZE', 1000))
        self.default_chunk_overlap = self.config.get('default_chunk_overlap', 
                                                    getattr(settings, 'DEFAULT_CHUNK_OVERLAP', 100))
        self.extract_metadata = self.config.get('extract_metadata', True)
        
        # Services
        self.converter = None
        self.chunker = None
        self.ocr_processor = None
        
        # État d'initialisation
        self.initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialise les services nécessaires.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if self.initialized:
            return True
        
        try:
            # Initialiser le convertisseur de documents
            self.converter = await get_document_converter(
                provider_name=self.converter_provider,
                config=self.config,
                fallback=True
            )
            
            # Initialiser le chunker de texte
            self.chunker = await get_text_chunker(
                provider_name=self.chunker_provider,
                config=self.config,
                fallback=True
            )
            
            # Initialiser le processeur OCR si activé
            if self.enable_ocr:
                try:
                    self.ocr_processor = await get_ocr_processor(
                        provider_name=self.ocr_provider,
                        config=self.config
                    )
                except Exception as e:
                    logger.warning(f"Erreur lors de l'initialisation du processeur OCR: {str(e)}")
            
            # Journaliser la configuration
            logger.info(f"Document Processor initialisé avec:")
            logger.info(f"- Convertisseur: {self.converter.provider_name}")
            logger.info(f"- Chunker: {self.chunker.provider_name}")
            logger.info(f"- OCR: {'activé' if self.ocr_processor else 'désactivé'}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du Document Processor: {str(e)}")
            return False
    
    async def process_document(self, 
                        file_path: Union[str, Path],
                        chunk_size: Optional[int] = None,
                        chunk_overlap: Optional[int] = None,
                        enable_ocr: Optional[bool] = None,
                        **kwargs) -> DocumentProcessingResult:
        """
        Traite un document en extrayant le texte et en le découpant en chunks.
        
        Args:
            file_path: Chemin vers le document
            chunk_size: Taille des chunks (défaut: self.default_chunk_size)
            chunk_overlap: Chevauchement des chunks (défaut: self.default_chunk_overlap)
            enable_ocr: Activer l'OCR pour ce document (défaut: self.enable_ocr)
            **kwargs: Options additionnelles pour les étapes de traitement
                - conversion_options: Options pour le convertisseur
                - chunking_options: Options pour le chunker
                - ocr_options: Options pour l'OCR
                - skip_chunking: Ignorer l'étape de chunking (défaut: False)
                - extract_tables: Extraire les tableaux (défaut: True)
                
        Returns:
            Résultat du traitement
        """
        start_time = time.time()
        
        # S'assurer que le processeur est initialisé
        if not self.initialized and not await self.initialize():
            return DocumentProcessingResult(
                success=False,
                error_message="Le processeur n'a pas pu être initialisé"
            )
        
        # Paramètres
        file_path = Path(file_path)
        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap
        enable_ocr_for_doc = enable_ocr if enable_ocr is not None else self.enable_ocr
        skip_chunking = kwargs.get('skip_chunking', False)
        
        # Options spécifiques
        conversion_options = kwargs.get('conversion_options', {})
        chunking_options = kwargs.get('chunking_options', {})
        ocr_options = kwargs.get('ocr_options', {})
        
        # Métadonnées du document
        metadata = {
            "filename": file_path.name,
            "extension": file_path.suffix.lower(),
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "processing_start_time": start_time,
            "steps": [],
        }
        
        try:
            # Étape 1: Conversion du document en texte
            logger.info(f"Conversion du document: {file_path}")
            metadata["steps"].append({"name": "conversion", "start_time": time.time()})
            
            conversion_result = await self.converter.convert_file(
                file_path=file_path,
                output_format="text",
                extract_metadata=self.extract_metadata,
                **conversion_options
            )
            
            metadata["steps"][-1]["end_time"] = time.time()
            metadata["steps"][-1]["duration"] = metadata["steps"][-1]["end_time"] - metadata["steps"][-1]["start_time"]
            
            if not conversion_result.success:
                return DocumentProcessingResult(
                    success=False,
                    error_message=f"Échec de la conversion: {conversion_result.error_message}",
                    metadata=metadata
                )
            
            # Ajouter les métadonnées de conversion
            metadata.update(conversion_result.metadata or {})
            metadata["text_length"] = len(conversion_result.text_content)
            
            # Étape 2: OCR si nécessaire et disponible
            text_content = conversion_result.text_content
            needs_ocr = getattr(conversion_result.metadata, "needs_ocr", False)
            
            if enable_ocr_for_doc and needs_ocr and self.ocr_processor and not getattr(conversion_result.metadata, "ocr_processed", False):
                logger.info(f"Traitement OCR du document: {file_path}")
                metadata["steps"].append({"name": "ocr", "start_time": time.time()})
                
                # Créer un fichier temporaire pour les résultats OCR
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    ocr_result = await self.ocr_processor.process_document(
                        input_path=file_path,
                        output_dir=temp_dir,
                        **ocr_options
                    )
                    
                    if ocr_result.success:
                        # Re-convertir le document traité par OCR
                        ocr_conversion = await self.converter.convert_file(
                            file_path=ocr_result.output_path,
                            output_format="text",
                            **conversion_options
                        )
                        
                        if ocr_conversion.success:
                            text_content = ocr_conversion.text_content
                            metadata["ocr_processed"] = True
                            
                            # Ajouter les métadonnées OCR
                            if ocr_result.metadata:
                                metadata["ocr"] = ocr_result.metadata
                    
                metadata["steps"][-1]["end_time"] = time.time()
                metadata["steps"][-1]["duration"] = metadata["steps"][-1]["end_time"] - metadata["steps"][-1]["start_time"]
            
            # Étape 3: Chunking du texte
            chunks = []
            
            if not skip_chunking and text_content:
                logger.info(f"Chunking du texte extrait ({len(text_content)} caractères)")
                metadata["steps"].append({"name": "chunking", "start_time": time.time()})
                
                chunking_result = await self.chunker.chunk_text(
                    text=text_content,
                    max_chunk_size=chunk_size,
                    overlap=chunk_overlap,
                    **chunking_options
                )
                
                if chunking_result.success:
                    chunks = chunking_result.chunks
                    
                    # Ajouter les métadonnées de chunking
                    metadata["chunking"] = chunking_result.metadata or {}
                    metadata["chunks_count"] = len(chunks)
                
                metadata["steps"][-1]["end_time"] = time.time()
                metadata["steps"][-1]["duration"] = metadata["steps"][-1]["end_time"] - metadata["steps"][-1]["start_time"]
            
            # Finaliser le traitement
            processing_time = time.time() - start_time
            metadata["processing_time"] = processing_time
            
            return DocumentProcessingResult(
                success=True,
                chunks=chunks,
                text_content=text_content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du document {file_path}: {str(e)}")
            
            # Ajouter les détails de l'erreur
            metadata["error"] = {
                "message": str(e),
                "type": type(e).__name__,
                "processing_time": time.time() - start_time
            }
            
            return DocumentProcessingResult(
                success=False,
                error_message=str(e),
                metadata=metadata
            )
    
    async def process_file_content(self,
                            content: Union[bytes, BinaryIO],
                            file_type: str,
                            chunk_size: Optional[int] = None,
                            chunk_overlap: Optional[int] = None,
                            **kwargs) -> DocumentProcessingResult:
        """
        Traite un contenu binaire de document.
        
        Args:
            content: Contenu binaire à traiter
            file_type: Type du fichier (extension ou MIME type)
            chunk_size: Taille des chunks (défaut: self.default_chunk_size)
            chunk_overlap: Chevauchement des chunks (défaut: self.default_chunk_overlap)
            **kwargs: Options additionnelles pour les étapes de traitement
                
        Returns:
            Résultat du traitement
        """
        start_time = time.time()
        
        # S'assurer que le processeur est initialisé
        if not self.initialized and not await self.initialize():
            return DocumentProcessingResult(
                success=False,
                error_message="Le processeur n'a pas pu être initialisé"
            )
        
        # Paramètres
        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap
        
        # Métadonnées
        metadata = {
            "file_type": file_type,
            "processing_start_time": start_time,
            "steps": [],
        }
        
        try:
            # Étape 1: Conversion du contenu binaire en texte
            logger.info(f"Conversion du contenu binaire de type {file_type}")
            metadata["steps"].append({"name": "conversion", "start_time": time.time()})
            
            conversion_result = await self.converter.convert_bytes(
                content=content,
                file_type=file_type,
                output_format="text",
                **kwargs.get('conversion_options', {})
            )
            
            metadata["steps"][-1]["end_time"] = time.time()
            metadata["steps"][-1]["duration"] = metadata["steps"][-1]["end_time"] - metadata["steps"][-1]["start_time"]
            
            if not conversion_result.success:
                return DocumentProcessingResult(
                    success=False,
                    error_message=f"Échec de la conversion: {conversion_result.error_message}",
                    metadata=metadata
                )
            
            # Ajouter les métadonnées de conversion
            metadata.update(conversion_result.metadata or {})
            
            # Étape 2: Chunking du texte
            chunks = []
            text_content = conversion_result.text_content
            
            if not kwargs.get('skip_chunking', False) and text_content:
                logger.info(f"Chunking du texte extrait ({len(text_content)} caractères)")
                metadata["steps"].append({"name": "chunking", "start_time": time.time()})
                
                chunking_result = await self.chunker.chunk_text(
                    text=text_content,
                    max_chunk_size=chunk_size,
                    overlap=chunk_overlap,
                    **kwargs.get('chunking_options', {})
                )
                
                if chunking_result.success:
                    chunks = chunking_result.chunks
                    
                    # Ajouter les métadonnées de chunking
                    metadata["chunking"] = chunking_result.metadata or {}
                    metadata["chunks_count"] = len(chunks)
                
                metadata["steps"][-1]["end_time"] = time.time()
                metadata["steps"][-1]["duration"] = metadata["steps"][-1]["end_time"] - metadata["steps"][-1]["start_time"]
            
            # Finaliser le traitement
            processing_time = time.time() - start_time
            metadata["processing_time"] = processing_time
            
            return DocumentProcessingResult(
                success=True,
                chunks=chunks,
                text_content=text_content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du contenu binaire de type {file_type}: {str(e)}")
            
            # Ajouter les détails de l'erreur
            metadata["error"] = {
                "message": str(e),
                "type": type(e).__name__,
                "processing_time": time.time() - start_time
            }
            
            return DocumentProcessingResult(
                success=False,
                error_message=str(e),
                metadata=metadata
            )

# Instance partagée du processeur de documents
_shared_processor = None

async def get_document_processor(config: Optional[Dict[str, Any]] = None) -> DocumentProcessor:
    """
    Obtient une instance partagée du processeur de documents.
    
    Args:
        config: Configuration du processeur
        
    Returns:
        Instance du processeur de documents
    """
    global _shared_processor
    
    if _shared_processor is None:
        _shared_processor = DocumentProcessor(config)
        await _shared_processor.initialize()
    
    return _shared_processor
