"""
Implémentation avancée du service de chunking sémantique.
Utilise des techniques de NLP pour segmenter le texte de façon plus intelligente.
"""

import re
import nltk
from typing import List, Dict, Any, Optional, Set, Union, Tuple
import logging
import time
from pathlib import Path
import asyncio

from .base import TextChunker, ChunkingResult
from .simple import SimpleTextChunker

logger = logging.getLogger(__name__)

class SemanticTextChunker(TextChunker):
    """
    Service de chunking sémantique utilisant des techniques de NLP.
    Cette implémentation utilise une combinaison de heuristiques et d'analyse
    linguistique pour découper le texte en préservant la cohérence sémantique.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le chunker sémantique.
        
        Args:
            config: Configuration du chunker
                - default_max_chunk_size: Taille maximale par défaut (défaut: 1000)
                - default_overlap: Chevauchement par défaut (défaut: 100)
                - respect_semantic_boundaries: Respecter les frontières sémantiques (défaut: True)
                - fallback_to_simple: Utiliser le chunker simple en cas d'erreur (défaut: True)
                - nltk_data_path: Chemin vers les données NLTK (optionnel)
        """
        super().__init__(config)
        self.default_max_chunk_size = self.config.get('default_max_chunk_size', 1000)
        self.default_overlap = self.config.get('default_overlap', 100)
        self.respect_semantic_boundaries = self.config.get('respect_semantic_boundaries', True)
        self.fallback_to_simple = self.config.get('fallback_to_simple', True)
        
        # Initialiser NLTK si un chemin de données est fourni
        nltk_data_path = self.config.get('nltk_data_path')
        if nltk_data_path:
            nltk.data.path.append(nltk_data_path)
        
        # Chunker simple pour fallback
        self.simple_chunker = SimpleTextChunker(config)
        
        # Ressources NLTK nécessaires
        self._nltk_resources = {
            'punkt': 'tokenizers/punkt',
            'stopwords': 'corpora/stopwords',
            'averaged_perceptron_tagger': 'taggers/averaged_perceptron_tagger'
        }
        
        # État d'initialisation
        self._initialized = False
        self._missing_resources = set()
    
    @property
    def provider_name(self) -> str:
        """
        Nom du provider de chunking.
        
        Returns:
            "semantic"
        """
        return "semantic"
    
    async def _initialize(self) -> bool:
        """
        Initialise les ressources NLTK nécessaires.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if self._initialized:
            return True
        
        try:
            # Télécharger les ressources NLTK nécessaires de façon asynchrone
            for resource_name, resource_path in self._nltk_resources.items():
                try:
                    # Vérifier si la ressource est déjà disponible
                    nltk.data.find(resource_path)
                    logger.debug(f"Ressource NLTK '{resource_name}' déjà disponible")
                except LookupError:
                    # Télécharger la ressource manquante
                    logger.info(f"Téléchargement de la ressource NLTK '{resource_name}'")
                    
                    # Exécution dans un thread pour ne pas bloquer
                    await asyncio.to_thread(nltk.download, resource_name)
                    
                    # Vérifier si le téléchargement a réussi
                    try:
                        nltk.data.find(resource_path)
                        logger.info(f"Ressource NLTK '{resource_name}' téléchargée avec succès")
                    except LookupError:
                        logger.warning(f"Échec du téléchargement de la ressource NLTK '{resource_name}'")
                        self._missing_resources.add(resource_name)
            
            # Vérifier si toutes les ressources sont disponibles
            if not self._missing_resources:
                self._initialized = True
                logger.info("Chunker sémantique initialisé avec succès")
                return True
            else:
                logger.warning(f"Chunker sémantique initialisé avec ressources manquantes: {self._missing_resources}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du chunker sémantique: {str(e)}")
            return False
    
    async def chunk_text(self, 
                  text: str, 
                  max_chunk_size: Optional[int] = None,
                  overlap: Optional[int] = None,
                  **kwargs) -> ChunkingResult:
        """
        Découpe un texte en chunks en utilisant des techniques sémantiques.
        
        Args:
            text: Texte à découper
            max_chunk_size: Taille maximale d'un chunk (défaut: self.default_max_chunk_size)
            overlap: Chevauchement entre les chunks (défaut: self.default_overlap)
            **kwargs: Options additionnelles
                - respect_semantic_boundaries: Respecter les frontières sémantiques
                - detect_language: Détecter automatiquement la langue (défaut: True)
                - language: Code de langue (si detect_language=False)
                
        Returns:
            Résultat du chunking contenant les chunks générés
        """
        start_time = time.time()
        
        # Initialiser les ressources NLTK si nécessaire
        init_success = await self._initialize()
        
        # Si l'initialisation a échoué et qu'on veut fallback au chunker simple
        if not init_success and self.fallback_to_simple:
            logger.warning("Utilisation du chunker simple en fallback")
            return await self.simple_chunker.chunk_text(
                text=text,
                max_chunk_size=max_chunk_size,
                overlap=overlap,
                **kwargs
            )
        
        # Paramètres
        max_size = max_chunk_size or self.default_max_chunk_size
        overlap_size = overlap or self.default_overlap
        respect_semantic = kwargs.get('respect_semantic_boundaries', self.respect_semantic_boundaries)
        detect_language = kwargs.get('detect_language', True)
        
        if not text or max_size <= 0:
            return ChunkingResult(chunks=[], metadata={"empty_input": True})
        
        # Détecter la langue si demandé
        language = kwargs.get('language', 'french')
        if detect_language:
            try:
                from langdetect import detect
                detected_lang = detect(text[:min(len(text), 1000)])
                
                # Convertir le code langdetect en code compatible avec NLTK
                lang_mapping = {'fr': 'french', 'en': 'english', 'de': 'german', 'es': 'spanish', 'it': 'italian'}
                language = lang_mapping.get(detected_lang, 'french')
                
                logger.debug(f"Langue détectée: {detected_lang} -> {language}")
            except Exception as e:
                logger.warning(f"Erreur lors de la détection de langue: {str(e)}")
        
        try:
            # Si le texte est déjà assez petit, le retourner tel quel
            if len(text) <= max_size:
                return ChunkingResult(
                    chunks=[text],
                    metadata={
                        "processing_time": time.time() - start_time,
                        "provider": self.provider_name,
                        "language": language,
                        "strategy": "passthrough"
                    }
                )
            
            # Analyse sémantique et découpage
            if respect_semantic:
                chunks = await self._semantic_split(
                    text=text,
                    max_size=max_size,
                    overlap=overlap_size,
                    language=language,
                    **kwargs
                )
            else:
                # Si on ne veut pas respecter les frontières sémantiques,
                # utiliser le chunker simple avec les paramètres avancés
                return await self.simple_chunker.chunk_text(
                    text=text,
                    max_chunk_size=max_size,
                    overlap=overlap_size,
                    use_hierarchical_split=True,
                    **kwargs
                )
            
            processing_time = time.time() - start_time
            
            return ChunkingResult(
                chunks=chunks,
                metadata={
                    "processing_time": processing_time,
                    "provider": self.provider_name,
                    "max_chunk_size": max_size,
                    "overlap": overlap_size,
                    "language": language,
                    "semantic_boundaries": respect_semantic,
                    "original_text_length": len(text),
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du chunking sémantique: {str(e)}")
            
            # En cas d'erreur, fallback sur le chunker simple si configuré
            if self.fallback_to_simple:
                logger.warning("Fallback sur le chunker simple suite à une erreur")
                return await self.simple_chunker.chunk_text(
                    text=text,
                    max_chunk_size=max_size,
                    overlap=overlap_size,
                    **kwargs
                )
            else:
                # Sinon, propager l'erreur
                raise
    
    async def _semantic_split(self,
                      text: str, 
                      max_size: int, 
                      overlap: int,
                      language: str = 'french',
                      **kwargs) -> List[str]:
        """
        Découpage sémantique du texte.
        
        Args:
            text: Texte à découper
            max_size: Taille maximale d'un chunk
            overlap: Chevauchement entre les chunks
            language: Langue du texte
            **kwargs: Options additionnelles
            
        Returns:
            Liste des chunks générés
        """
        # Extraire des unités sémantiques (paragraphes, phrases)
        semantic_units = await self._extract_semantic_units(text, language)
        
        # Regrouper les unités sémantiques en chunks
        chunks = []
        current_chunk = ""
        current_overlap = ""
        overlap_buffer = []
        
        for unit in semantic_units:
            # Si l'unité seule est plus grande que la taille maximale
            if len(unit) > max_size:
                # Ajouter le chunk courant s'il existe
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # Découper cette grande unité avec le chunker simple
                large_unit_chunks = await self.simple_chunker._simple_split(unit, max_size, overlap)
                chunks.extend(large_unit_chunks)
                
                # Mettre à jour le buffer de chevauchement
                if large_unit_chunks and overlap > 0:
                    last_chunk = large_unit_chunks[-1]
                    overlap_buffer = self._create_overlap_buffer(last_chunk, overlap)
                
                continue
            
            # Vérifier si l'ajout de l'unité dépasse la taille maximale
            if len(current_chunk) + len(unit) + 1 > max_size:  # +1 pour l'espace ou saut de ligne
                # Ajouter le chunk courant aux résultats
                chunks.append(current_chunk)
                
                # Commencer un nouveau chunk avec le contenu du buffer de chevauchement
                if overlap_buffer:
                    current_chunk = " ".join(overlap_buffer)
                    overlap_buffer = []
                else:
                    current_chunk = ""
            
            # Ajouter l'unité au chunk courant
            if current_chunk:
                # Détecter si c'est un paragraphe ou une phrase pour choisir le bon séparateur
                if unit.strip().startswith(("- ", "* ", "•")) or re.match(r"^\d+\.\s", unit.strip()):
                    # Pour les listes, utiliser un saut de ligne
                    current_chunk += "\n" + unit
                elif len(unit) > 100 or unit.count(".") > 1:
                    # Pour les paragraphes, utiliser un double saut de ligne
                    current_chunk += "\n\n" + unit
                else:
                    # Pour les phrases simples, utiliser un espace
                    current_chunk += " " + unit
            else:
                current_chunk = unit
            
            # Mettre à jour le buffer de chevauchement
            if overlap > 0:
                overlap_buffer = self._update_overlap_buffer(overlap_buffer, unit, current_chunk, overlap)
        
        # Ajouter le dernier chunk s'il existe
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def _extract_semantic_units(self, text: str, language: str) -> List[str]:
        """
        Extrait les unités sémantiques du texte.
        
        Args:
            text: Texte à analyser
            language: Langue du texte
            
        Returns:
            Liste des unités sémantiques
        """
        # Diviser d'abord en paragraphes
        paragraphs = re.split(r"\n\s*\n", text)
        
        # Pour chaque paragraphe potentiellement long, le diviser en phrases
        units = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Conserver les paragraphes courts comme une seule unité
            if len(paragraph) < 300:
                units.append(paragraph)
                continue
            
            # Pour les paragraphes plus longs, diviser en phrases
            try:
                sentences = nltk.sent_tokenize(paragraph, language=language)
                units.extend(sentences)
            except Exception as e:
                logger.warning(f"Erreur lors de la tokenization des phrases: {str(e)}")
                # Fallback: découper aux points et aux sauts de ligne
                fallback_sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                units.extend(fallback_sentences)
        
        return units
    
    def _create_overlap_buffer(self, text: str, overlap_size: int) -> List[str]:
        """
        Crée un buffer de chevauchement à partir d'un texte.
        
        Args:
            text: Texte source
            overlap_size: Taille approximative du chevauchement
            
        Returns:
            Liste des tokens à inclure dans le buffer
        """
        if not text or overlap_size <= 0:
            return []
        
        # Extraire les derniers tokens jusqu'à atteindre la taille de chevauchement
        tokens = text.split()
        
        if not tokens:
            return []
        
        # Commencer par la fin et remonter jusqu'à atteindre la taille de chevauchement
        overlap_tokens = []
        current_size = 0
        
        for token in reversed(tokens):
            current_size += len(token) + 1  # +1 pour l'espace
            overlap_tokens.insert(0, token)
            
            if current_size >= overlap_size:
                break
        
        return overlap_tokens
    
    def _update_overlap_buffer(self, 
                              current_buffer: List[str], 
                              unit: str, 
                              current_chunk: str, 
                              overlap_size: int) -> List[str]:
        """
        Met à jour le buffer de chevauchement.
        
        Args:
            current_buffer: Buffer actuel
            unit: Unité ajoutée
            current_chunk: Chunk actuel
            overlap_size: Taille du chevauchement
            
        Returns:
            Buffer mis à jour
        """
        # Si le chunk actuel est plus petit que la taille de chevauchement,
        # utiliser tous ses tokens
        if len(current_chunk) <= overlap_size:
            return current_chunk.split()
        
        # Sinon, prendre les derniers tokens jusqu'à la taille de chevauchement
        return self._create_overlap_buffer(current_chunk, overlap_size)
    
    async def chunk_document(self,
                     document_text: str,
                     document_metadata: Optional[Dict[str, Any]] = None,
                     **kwargs) -> ChunkingResult:
        """
        Découpe un document entier en chunks en tenant compte de sa structure sémantique.
        
        Args:
            document_text: Texte du document à découper
            document_metadata: Métadonnées du document (titre, auteur, etc.)
            **kwargs: Options spécifiques au chunker
                - max_chunk_size: Taille maximale d'un chunk
                - overlap: Chevauchement entre les chunks
                - add_metadata_to_chunks: Ajouter les métadonnées à chaque chunk
                - respect_document_structure: Respecter la structure du document (défaut: True)
                
        Returns:
            Résultat du chunking contenant les chunks générés
        """
        # Paramètres
        max_size = kwargs.get('max_chunk_size', self.default_max_chunk_size)
        overlap = kwargs.get('overlap', self.default_overlap)
        add_metadata = kwargs.get('add_metadata_to_chunks', True)
        respect_structure = kwargs.get('respect_document_structure', True)
        
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
                
            if 'document_type' in document_metadata:
                metadata_items.append(f"Type: {document_metadata['document_type']}")
            
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
        
        # Si on respecte la structure du document, essayer d'identifier les sections
        if respect_structure and document_text:
            try:
                structured_chunks = await self._chunk_structured_document(
                    document_text, 
                    effective_max_size, 
                    overlap,
                    **kwargs
                )
                
                # Ajouter les métadonnées à chaque chunk si nécessaire
                if metadata_prefix:
                    structured_chunks = [metadata_prefix + chunk for chunk in structured_chunks]
                
                # Construire le résultat
                result = ChunkingResult(
                    chunks=structured_chunks,
                    metadata={
                        "document_metadata": document_metadata or {},
                        "provider": self.provider_name,
                        "strategy": "structured",
                        "max_chunk_size": max_size,
                        "overlap": overlap,
                    }
                )
                
                return result
            except Exception as e:
                logger.warning(f"Échec du chunking structuré: {str(e)}")
        
        # Chunker le texte normalement si la méthode structurée échoue
        result = await self.chunk_text(document_text, effective_max_size, overlap, **kwargs)
        
        # Ajouter les métadonnées à chaque chunk si nécessaire
        if metadata_prefix:
            result.chunks = [metadata_prefix + chunk for chunk in result.chunks]
        
        # Ajouter les métadonnées du document dans les métadonnées du résultat
        if document_metadata:
            result.metadata["document_metadata"] = document_metadata
        
        return result
    
    async def _chunk_structured_document(self,
                                 document_text: str,
                                 max_size: int,
                                 overlap: int,
                                 **kwargs) -> List[str]:
        """
        Découpe un document structuré en chunks en respectant la structure.
        
        Args:
            document_text: Texte du document
            max_size: Taille maximale d'un chunk
            overlap: Chevauchement entre les chunks
            **kwargs: Options additionnelles
            
        Returns:
            Liste des chunks générés
        """
        # Détecter les sections du document
        sections = await self._detect_document_sections(document_text)
        
        # Si aucune section n'est détectée, utiliser le chunking normal
        if not sections:
            chunks = await self.chunk_text(document_text, max_size, overlap, **kwargs)
            return chunks.chunks
        
        # Traiter chaque section indépendamment
        all_chunks = []
        
        for title, content in sections:
            # Déterminer si le titre doit être inclus avec le contenu
            if title and content:
                # Si le contenu est petit, le garder avec son titre
                if len(content) < max_size // 2:
                    section_text = f"{title}\n\n{content}"
                    
                    # Si la section entière est trop grande pour un chunk
                    if len(section_text) > max_size:
                        # Chunker le contenu et ajouter le titre à chaque chunk
                        content_chunks = await self.chunk_text(
                            content, 
                            max_size - len(title) - 4,  # 4 pour "\n\n"
                            overlap,
                            **kwargs
                        )
                        
                        # Ajouter le titre à chaque chunk
                        section_chunks = [f"{title}\n\n{chunk}" for chunk in content_chunks.chunks]
                        all_chunks.extend(section_chunks)
                    else:
                        # Ajouter la section entière
                        all_chunks.append(section_text)
                else:
                    # Pour les sections plus grandes, chunker le contenu
                    # et ajouter le titre à chaque chunk
                    content_chunks = await self.chunk_text(
                        content, 
                        max_size - len(title) - 4,  # 4 pour "\n\n"
                        overlap,
                        **kwargs
                    )
                    
                    # Ajouter le titre à chaque chunk
                    section_chunks = [f"{title}\n\n{chunk}" for chunk in content_chunks.chunks]
                    all_chunks.extend(section_chunks)
            elif title:
                # Juste un titre sans contenu
                all_chunks.append(title)
            elif content:
                # Juste du contenu sans titre
                content_chunks = await self.chunk_text(content, max_size, overlap, **kwargs)
                all_chunks.extend(content_chunks.chunks)
        
        return all_chunks
    
    async def _detect_document_sections(self, document_text: str) -> List[Tuple[str, str]]:
        """
        Détecte les sections d'un document.
        
        Args:
            document_text: Texte du document
            
        Returns:
            Liste de tuples (titre_section, contenu_section)
        """
        # Patterns pour détecter les titres de section
        title_patterns = [
            # Titres numérotés (1. Titre, 1.1 Titre, etc.)
            r"^(?:\d+\.)+\s+(.+)$",
            # Titres avec dièses (# Titre, ## Titre, etc.)
            r"^#{1,5}\s+(.+)$",
            # Titres en majuscules
            r"^([A-Z][A-Z\s]+[A-Z])$",
            # Titres avec deux-points
            r"^([^:]+:)\s*$"
        ]
        
        # Compiler les patterns
        compiled_patterns = [re.compile(pattern, re.MULTILINE) for pattern in title_patterns]
        
        # Découper le document en lignes
        lines = document_text.split("\n")
        
        # Identifier les lignes qui sont des titres
        title_indices = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Vérifier si cette ligne correspond à un pattern de titre
            for pattern in compiled_patterns:
                if pattern.match(line):
                    title_indices.append(i)
                    break
        
        # Si aucun titre n'est détecté, retourner le document entier
        if not title_indices:
            return []
        
        # Construire les sections
        sections = []
        
        for i in range(len(title_indices)):
            title_idx = title_indices[i]
            title = lines[title_idx].strip()
            
            # Déterminer la fin de cette section
            if i < len(title_indices) - 1:
                end_idx = title_indices[i + 1]
            else:
                end_idx = len(lines)
            
            # Extraire le contenu de la section
            content_lines = lines[title_idx + 1:end_idx]
            content = "\n".join(content_lines).strip()
            
            sections.append((title, content))
        
        return sections
