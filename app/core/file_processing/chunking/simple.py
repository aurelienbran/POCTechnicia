"""
Implémentation simple du service de chunking de texte.
Utilise des délimiteurs de base pour découper le texte.
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Callable
import logging
import time

from .base import TextChunker, ChunkingResult

logger = logging.getLogger(__name__)

class SimpleTextChunker(TextChunker):
    """
    Service de chunking de texte utilisant des délimiteurs simples.
    Cette classe implémente une stratégie de découpage basée sur des délimiteurs
    hiérarchiques (titres, paragraphes, phrases) pour préserver au mieux
    la structure du document.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le chunker simple.
        
        Args:
            config: Configuration du chunker
                - default_max_chunk_size: Taille maximale par défaut (défaut: 1000)
                - default_overlap: Chevauchement par défaut (défaut: 50)
                - respect_paragraphs: Respecter les paragraphes si possible (défaut: True)
                - smart_split: Utiliser une heuristique intelligente (défaut: True)
        """
        super().__init__(config)
        self.default_max_chunk_size = self.config.get('default_max_chunk_size', 1000)
        self.default_overlap = self.config.get('default_overlap', 50)
        self.respect_paragraphs = self.config.get('respect_paragraphs', True)
        self.smart_split = self.config.get('smart_split', True)
        
        # Expressions régulières pour délimiteurs
        self._title_pattern = re.compile(r"^(?:#{1,5}|\*{1,3}|\d+\.|[A-Z\s]+:)\s+.+$", re.MULTILINE)
        self._paragraph_pattern = re.compile(r"\n\s*\n")
        self._sentence_pattern = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ö])")
    
    @property
    def provider_name(self) -> str:
        """
        Nom du provider de chunking.
        
        Returns:
            "simple"
        """
        return "simple"
    
    async def chunk_text(self, 
                  text: str, 
                  max_chunk_size: Optional[int] = None,
                  overlap: Optional[int] = None,
                  **kwargs) -> ChunkingResult:
        """
        Découpe un texte en chunks.
        
        Args:
            text: Texte à découper
            max_chunk_size: Taille maximale d'un chunk (défaut: self.default_max_chunk_size)
            overlap: Chevauchement entre les chunks (défaut: self.default_overlap)
            **kwargs: Options additionnelles
                - respect_paragraphs: Respecter les paragraphes si possible
                - use_hierarchical_split: Utiliser un découpage hiérarchique
                - delimiter_patterns: Patterns regex supplémentaires pour les délimiteurs
                
        Returns:
            Résultat du chunking contenant les chunks générés
        """
        start_time = time.time()
        
        # Paramètres
        max_size = max_chunk_size or self.default_max_chunk_size
        overlap_size = overlap or self.default_overlap
        respect_paragraphs = kwargs.get('respect_paragraphs', self.respect_paragraphs)
        use_hierarchical = kwargs.get('use_hierarchical_split', self.smart_split)
        
        # Délimiteurs supplémentaires fournis par l'appelant
        extra_patterns = kwargs.get('delimiter_patterns', [])
        
        if not text or max_size <= 0:
            return ChunkingResult(chunks=[], metadata={"empty_input": True})
        
        chunks = []
        
        # Si le texte est déjà assez petit, le retourner tel quel
        if len(text) <= max_size:
            chunks = [text]
        else:
            if use_hierarchical:
                # Utiliser une stratégie hiérarchique pour préserver la structure
                chunks = self._hierarchical_split(
                    text, 
                    max_size=max_size, 
                    overlap=overlap_size, 
                    respect_paragraphs=respect_paragraphs,
                    extra_patterns=extra_patterns
                )
            else:
                # Découpage simple avec chevauchement
                chunks = self._simple_split(
                    text, 
                    max_size=max_size, 
                    overlap=overlap_size
                )
        
        processing_time = time.time() - start_time
        
        return ChunkingResult(
            chunks=chunks,
            metadata={
                "processing_time": processing_time,
                "provider": self.provider_name,
                "max_chunk_size": max_size,
                "overlap": overlap_size,
                "strategy": "hierarchical" if use_hierarchical else "simple",
                "original_text_length": len(text),
            }
        )
    
    def _simple_split(self, 
                     text: str, 
                     max_size: int, 
                     overlap: int) -> List[str]:
        """
        Découpage simple avec chevauchement.
        
        Args:
            text: Texte à découper
            max_size: Taille maximale d'un chunk
            overlap: Chevauchement entre les chunks
            
        Returns:
            Liste des chunks générés
        """
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            # Calculer la fin du chunk
            end = start + max_size
            
            # Ajuster si on dépasse la fin du texte
            if end > text_len:
                end = text_len
            
            # Extraire le chunk
            chunk = text[start:end]
            chunks.append(chunk)
            
            # Calculer le début du prochain chunk avec chevauchement
            start = end - overlap
            
            # S'assurer qu'on avance au moins d'un caractère
            if start >= end:
                start = end
            
            # Si on atteint la fin du texte, sortir
            if start >= text_len:
                break
        
        return chunks
    
    def _hierarchical_split(self, 
                           text: str, 
                           max_size: int, 
                           overlap: int,
                           respect_paragraphs: bool = True,
                           extra_patterns: List[str] = None) -> List[str]:
        """
        Découpage hiérarchique respectant la structure du document.
        
        Args:
            text: Texte à découper
            max_size: Taille maximale d'un chunk
            overlap: Chevauchement entre les chunks
            respect_paragraphs: Respecter les paragraphes si possible
            extra_patterns: Patterns regex supplémentaires pour les délimiteurs
            
        Returns:
            Liste des chunks générés
        """
        # Préparer les délimiteurs hiérarchiques
        delimiters = self._get_hierarchical_delimiters(extra_patterns)
        chunks = []
        
        # Essayer de découper avec chaque délimiteur dans l'ordre
        for delimiter_pattern, description in delimiters:
            # Si le texte est déjà court, ne pas continuer
            if len(text) <= max_size:
                chunks = [text]
                break
            
            # Découper le texte avec le délimiteur actuel
            segments = re.split(delimiter_pattern, text)
            
            # Si le découpage donne des segments trop gros, essayer le prochain délimiteur
            if all(len(segment) <= max_size for segment in segments):
                logger.debug(f"Découpage réussi avec délimiteur: {description}")
                
                # Recombiner les segments en chunks de taille maximale
                current_chunk = ""
                last_added_segment = ""
                
                for segment in segments:
                    # Si le segment est vide, passer au suivant
                    if not segment.strip():
                        continue
                    
                    # Si le segment seul est trop grand, le découper en plus petits chunks
                    if len(segment) > max_size:
                        # D'abord ajouter le chunk courant s'il existe
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = ""
                        
                        # Puis découper ce segment trop grand avec le prochain délimiteur
                        # ou en dernier recours avec un découpage simple
                        continue
                    
                    # Vérifier si l'ajout du segment dépasse la taille maximale
                    if len(current_chunk) + len(segment) > max_size:
                        # Ajouter le chunk courant aux résultats
                        chunks.append(current_chunk)
                        
                        # Commencer un nouveau chunk avec chevauchement si configuré
                        if overlap > 0 and last_added_segment:
                            current_chunk = last_added_segment
                        else:
                            current_chunk = ""
                    
                    # Ajouter le segment au chunk courant
                    if current_chunk and respect_paragraphs:
                        current_chunk += "\n\n" + segment
                    else:
                        current_chunk += segment
                    
                    last_added_segment = segment
                
                # Ajouter le dernier chunk s'il existe
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Si on a réussi à découper, sortir de la boucle
                if chunks:
                    break
        
        # Si aucun découpage hiérarchique n'a réussi, utiliser le découpage simple
        if not chunks:
            logger.debug("Découpage hiérarchique échoué, utilisation du découpage simple")
            chunks = self._simple_split(text, max_size, overlap)
        
        return chunks
    
    def _get_hierarchical_delimiters(self, extra_patterns: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        """
        Prépare une liste de délimiteurs hiérarchiques pour le découpage.
        
        Args:
            extra_patterns: Patterns regex supplémentaires pour les délimiteurs
            
        Returns:
            Liste de tuples (pattern_regex, description)
        """
        # Délimiteurs de base, du plus structurant au moins structurant
        delimiters = [
            (self._title_pattern, "titres"),
            (self._paragraph_pattern, "paragraphes"),
            (self._sentence_pattern, "phrases"),
        ]
        
        # Ajouter les délimiteurs supplémentaires
        if extra_patterns:
            for pattern in extra_patterns:
                delimiters.insert(0, (re.compile(pattern, re.MULTILINE), "custom"))
        
        return delimiters
    
    async def chunk_document(self,
                     document_text: str,
                     document_metadata: Optional[Dict[str, Any]] = None,
                     **kwargs) -> ChunkingResult:
        """
        Découpe un document entier en chunks en tenant compte de sa structure.
        
        Args:
            document_text: Texte du document à découper
            document_metadata: Métadonnées du document (titre, auteur, etc.)
            **kwargs: Options spécifiques au chunker
                - max_chunk_size: Taille maximale d'un chunk
                - overlap: Chevauchement entre les chunks
                - add_metadata_to_chunks: Ajouter les métadonnées à chaque chunk
                
        Returns:
            Résultat du chunking contenant les chunks générés
        """
        # Paramètres
        max_size = kwargs.get('max_chunk_size', self.default_max_chunk_size)
        overlap = kwargs.get('overlap', self.default_overlap)
        add_metadata = kwargs.get('add_metadata_to_chunks', True)
        
        # Métadonnées formatées pour préfixage
        metadata_prefix = ""
        if add_metadata and document_metadata:
            metadata_items = []
            
            # Ajouter les métadonnées pertinentes
            if 'title' in document_metadata:
                metadata_items.append(f"Titre: {document_metadata['title']}")
            
            if 'author' in document_metadata:
                metadata_items.append(f"Auteur: {document_metadata['author']}")
                
            if 'date' in document_metadata:
                metadata_items.append(f"Date: {document_metadata['date']}")
                
            if 'source' in document_metadata:
                metadata_items.append(f"Source: {document_metadata['source']}")
            
            if metadata_items:
                metadata_prefix = "--- Métadonnées ---\n"
                metadata_prefix += "\n".join(metadata_items)
                metadata_prefix += "\n\n--- Contenu ---\n"
        
        # Si les métadonnées sont ajoutées, on doit ajuster la taille maximale
        effective_max_size = max_size
        if metadata_prefix:
            # Réduire la taille maximale pour tenir compte des métadonnées
            metadata_length = len(metadata_prefix)
            effective_max_size = max(max_size - metadata_length, max_size // 2)
        
        # Chunker le texte
        result = await self.chunk_text(document_text, effective_max_size, overlap, **kwargs)
        
        # Ajouter les métadonnées à chaque chunk si nécessaire
        if metadata_prefix:
            result.chunks = [metadata_prefix + chunk for chunk in result.chunks]
        
        # Ajouter les métadonnées du document dans les métadonnées du résultat
        if document_metadata:
            result.metadata["document_metadata"] = document_metadata
        
        return result
