"""
Chunker relationnel préservant les liens entre éléments
======================================================================

Ce module implémente un système de chunking qui préserve les relations
structurelles et sémantiques entre les différents éléments du document,
permettant une meilleure contextualisation et une recherche plus précise.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import re
import asyncio
from typing import List, Dict, Any, Optional, Set, Union, Tuple
import logging
import time
from pathlib import Path
import json
from datetime import datetime

from .base import TextChunker, ChunkingResult
from .semantic import SemanticTextChunker
from .metadata_enricher import MetadataEnricher

logger = logging.getLogger(__name__)


class RelationalChunker(TextChunker):
    """
    Chunker relationnel préservant les liens entre éléments.
    
    Cette classe étend le chunker sémantique en ajoutant la préservation
    des relations entre les différents éléments du document (tableaux,
    figures, références, etc.) et enrichit les chunks avec des métadonnées
    sur ces relations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le chunker relationnel.
        
        Args:
            config: Configuration du chunker
                - semantic_chunker_config: Configuration pour le chunker sémantique sous-jacent
                - metadata_enricher_config: Configuration pour l'enrichisseur de métadonnées
                - preserve_structural_elements: Préserver les éléments structurels (défaut: True)
                - link_references: Établir des liens pour les références (défaut: True)
                - detect_element_types: Détecter les types d'éléments (défaut: True)
                - relationship_types: Types de relations à détecter
        """
        super().__init__(config)
        self.preserve_structural_elements = self.config.get('preserve_structural_elements', True)
        self.link_references = self.config.get('link_references', True)
        self.detect_element_types = self.config.get('detect_element_types', True)
        
        # Types de relations à détecter
        self.relationship_types = self.config.get('relationship_types', [
            'reference', 'continuation', 'parent-child', 'figure-text',
            'table-text', 'definition', 'example'
        ])
        
        # Initialiser le chunker sémantique sous-jacent
        semantic_config = self.config.get('semantic_chunker_config', {})
        self.semantic_chunker = SemanticTextChunker(semantic_config)
        
        # Initialiser l'enrichisseur de métadonnées
        enricher_config = self.config.get('metadata_enricher_config', {})
        self.metadata_enricher = MetadataEnricher(enricher_config)
        
        # Patterns pour la détection d'éléments structurels
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """
        Initialise les patterns de détection d'éléments structurels.
        """
        # Patterns pour les figures
        self.figure_pattern = re.compile(
            r'(figure|fig\.?|schéma|diagramme)\s+(\d+[a-z]?)', 
            re.IGNORECASE
        )
        
        # Patterns pour les tableaux
        self.table_pattern = re.compile(
            r'(tableau|table)\s+(\d+[a-z]?)', 
            re.IGNORECASE
        )
        
        # Patterns pour les références
        self.reference_pattern = re.compile(
            r'(voir|cf\.?|référence|ref\.?)\s+((section|chapitre|partie)\s+)?(\d+(\.\d+)*)', 
            re.IGNORECASE
        )
        
        # Patterns pour les équations
        self.equation_pattern = re.compile(
            r'(équation|formule|eq\.?)\s+(\d+[a-z]?)', 
            re.IGNORECASE
        )
    
    @property
    def provider_name(self) -> str:
        """
        Nom du provider de chunking.
        
        Returns:
            "relational"
        """
        return "relational"
    
    async def chunk_text(self, 
                      text: str, 
                      max_chunk_size: Optional[int] = None,
                      overlap: Optional[int] = None,
                      **kwargs) -> ChunkingResult:
        """
        Découpe un texte en chunks en préservant les relations.
        
        Args:
            text: Texte à découper
            max_chunk_size: Taille maximale d'un chunk
            overlap: Chevauchement entre les chunks
            **kwargs: Options additionnelles
                
        Returns:
            Résultat du chunking contenant les chunks générés et leurs relations
        """
        start_time = time.time()
        
        # Détecter les éléments structurels avant le chunking
        structural_elements = self._detect_structural_elements(text)
        
        # Utiliser le chunker sémantique pour le découpage initial
        chunking_result = await self.semantic_chunker.chunk_text(
            text=text,
            max_chunk_size=max_chunk_size,
            overlap=overlap,
            **kwargs
        )
        
        # Si aucun chunk n'a été généré, retourner le résultat tel quel
        if not chunking_result.chunks:
            logger.warning("Aucun chunk généré par le chunker sémantique")
            return chunking_result
        
        # Enrichir les chunks avec les éléments structurels
        enriched_chunks = self._enrich_chunks_with_structural_elements(
            chunking_result.chunks, 
            structural_elements
        )
        
        # Mettre à jour les chunks dans le résultat
        chunking_result.chunks = enriched_chunks
        
        # Ajouter des métadonnées sur les éléments structurels
        chunking_result.metadata.update({
            "has_structural_elements": bool(structural_elements),
            "structural_element_count": len(structural_elements),
            "element_types": list(set(e["type"] for e in structural_elements)),
            "chunking_method": "relational",
            "preprocessing_time": time.time() - start_time
        })
        
        # Enrichir davantage avec l'enrichisseur de métadonnées
        enriched_result = self.metadata_enricher.enrich_chunks(chunking_result)
        
        # Établir des liens entre les chunks en fonction des éléments structurels
        if self.link_references and structural_elements:
            final_result = self._establish_element_relationships(enriched_result, structural_elements)
        else:
            final_result = enriched_result
        
        logger.info(f"Chunking relationnel terminé en {time.time() - start_time:.2f} secondes")
        
        return final_result
    
    def _detect_structural_elements(self, text: str) -> List[Dict[str, Any]]:
        """
        Détecte les éléments structurels dans le texte.
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste des éléments structurels trouvés
        """
        if not self.detect_element_types:
            return []
        
        structural_elements = []
        
        # Détecter les figures
        for match in self.figure_pattern.finditer(text):
            element = {
                "type": "figure",
                "id": match.group(2),
                "reference": match.group(0),
                "start": match.start(),
                "end": match.end(),
                "context": text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
            }
            structural_elements.append(element)
        
        # Détecter les tableaux
        for match in self.table_pattern.finditer(text):
            element = {
                "type": "table",
                "id": match.group(2),
                "reference": match.group(0),
                "start": match.start(),
                "end": match.end(),
                "context": text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
            }
            structural_elements.append(element)
        
        # Détecter les références
        for match in self.reference_pattern.finditer(text):
            element = {
                "type": "reference",
                "id": match.group(4),
                "reference": match.group(0),
                "start": match.start(),
                "end": match.end(),
                "context": text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
            }
            structural_elements.append(element)
        
        # Détecter les équations
        for match in self.equation_pattern.finditer(text):
            element = {
                "type": "equation",
                "id": match.group(2),
                "reference": match.group(0),
                "start": match.start(),
                "end": match.end(),
                "context": text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
            }
            structural_elements.append(element)
        
        logger.info(f"Détecté {len(structural_elements)} éléments structurels dans le texte")
        
        return structural_elements
    
    def _enrich_chunks_with_structural_elements(self, 
                                            chunks: List[Dict[str, Any]],
                                            structural_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrichit les chunks avec les informations sur les éléments structurels.
        
        Args:
            chunks: Liste des chunks à enrichir
            structural_elements: Liste des éléments structurels détectés
            
        Returns:
            Liste des chunks enrichis
        """
        if not structural_elements:
            return chunks
        
        # Pour chaque chunk, trouver les éléments structurels qu'il contient
        for chunk in chunks:
            chunk_text = chunk.get('text', '')
            chunk_start = chunk.get('metadata', {}).get('position_in_document', 0)
            chunk_end = chunk_start + len(chunk_text)
            
            # Initialiser la liste des éléments dans ce chunk
            if 'metadata' not in chunk:
                chunk['metadata'] = {}
            
            chunk['metadata']['structural_elements'] = []
            
            # Trouver les éléments qui sont dans ce chunk
            for element in structural_elements:
                element_start = element['start']
                element_end = element['end']
                
                # Vérifier si l'élément est dans ce chunk
                if (chunk_start <= element_start < chunk_end or
                        chunk_start < element_end <= chunk_end or
                        element_start <= chunk_start < element_end):
                    
                    # Ajouter l'élément aux métadonnées du chunk
                    chunk['metadata']['structural_elements'].append({
                        "type": element['type'],
                        "id": element['id'],
                        "reference": element['reference']
                    })
            
            # Ajouter un résumé des éléments structurels
            if chunk['metadata']['structural_elements']:
                element_types = [e['type'] for e in chunk['metadata']['structural_elements']]
                element_summary = {t: element_types.count(t) for t in set(element_types)}
                chunk['metadata']['element_summary'] = element_summary
        
        return chunks
    
    def _establish_element_relationships(self, 
                                      chunking_result: ChunkingResult,
                                      structural_elements: List[Dict[str, Any]]) -> ChunkingResult:
        """
        Établit des relations entre les chunks en fonction des éléments structurels.
        
        Args:
            chunking_result: Résultat du chunking à enrichir
            structural_elements: Liste des éléments structurels détectés
            
        Returns:
            Résultat du chunking avec relations établies
        """
        chunks = chunking_result.chunks
        
        # Créer un index des éléments par type et ID
        element_index = {}
        for element in structural_elements:
            key = f"{element['type']}_{element['id']}"
            element_index[key] = element
        
        # Créer un index des chunks par élément
        chunks_by_element = {}
        for i, chunk in enumerate(chunks):
            for element in chunk.get('metadata', {}).get('structural_elements', []):
                key = f"{element['type']}_{element['id']}"
                if key not in chunks_by_element:
                    chunks_by_element[key] = []
                chunks_by_element[key].append(i)
        
        # Établir des relations entre les chunks contenant les mêmes éléments
        for element_key, chunk_indices in chunks_by_element.items():
            if len(chunk_indices) <= 1:
                continue
            
            # Créer des relations entre tous les chunks contenant cet élément
            element_type = element_key.split('_')[0]
            for i in range(len(chunk_indices)):
                chunk_idx = chunk_indices[i]
                
                # S'assurer que le chunk a des métadonnées et une liste de relations
                if 'metadata' not in chunks[chunk_idx]:
                    chunks[chunk_idx]['metadata'] = {}
                
                if 'relations' not in chunks[chunk_idx]['metadata']:
                    chunks[chunk_idx]['metadata']['relations'] = []
                
                # Ajouter des relations avec les autres chunks contenant cet élément
                for j in range(len(chunk_indices)):
                    if i == j:
                        continue
                    
                    related_idx = chunk_indices[j]
                    
                    # Ajouter la relation
                    chunks[chunk_idx]['metadata']['relations'].append({
                        'chunk_id': chunks[related_idx].get('id', f"chunk_{related_idx}"),
                        'type': f"shared_{element_type}",
                        'element_id': element_key,
                        'strength': 0.8
                    })
        
        # Mettre à jour les chunks dans le résultat
        chunking_result.chunks = chunks
        
        # Ajouter des métadonnées sur les relations
        chunking_result.metadata.update({
            "has_element_relationships": True,
            "relationship_count": sum(len(chunk.get('metadata', {}).get('relations', [])) for chunk in chunks),
            "elements_with_relationships": len(chunks_by_element)
        })
        
        return chunking_result
    
    async def chunk_document(self,
                         document_text: str,
                         document_metadata: Optional[Dict[str, Any]] = None,
                         **kwargs) -> ChunkingResult:
        """
        Découpe un document entier en préservant sa structure et ses relations.
        
        Args:
            document_text: Texte du document à découper
            document_metadata: Métadonnées du document
            **kwargs: Options additionnelles
                
        Returns:
            Résultat du chunking
        """
        # Prétraitement spécifique aux documents
        if self.preserve_structural_elements:
            # Détecter la structure du document (sections, titres, etc.)
            document_structure = self._detect_document_structure(document_text)
            kwargs['document_structure'] = document_structure
        
        # Utiliser le chunker de base avec les options enrichies
        chunking_result = await self.chunk_text(
            text=document_text,
            **kwargs
        )
        
        # Enrichir avec les métadonnées du document
        if document_metadata:
            for chunk in chunking_result.chunks:
                # Ajouter les métadonnées du document à chaque chunk
                if 'metadata' not in chunk:
                    chunk['metadata'] = {}
                
                # Préfixer les métadonnées du document pour éviter les conflits
                document_meta = {
                    f"document_{key}": value 
                    for key, value in document_metadata.items()
                }
                
                chunk['metadata'].update(document_meta)
        
        return chunking_result
    
    def _detect_document_structure(self, document_text: str) -> Dict[str, Any]:
        """
        Détecte la structure d'un document (sections, titres, etc.).
        
        Args:
            document_text: Texte du document
            
        Returns:
            Dictionnaire décrivant la structure du document
        """
        # Patterns pour détecter les titres et sections
        section_pattern = re.compile(
            r'^(?P<level>#{1,6})\s+(?P<title>.+?)$', 
            re.MULTILINE
        )
        
        numbered_section_pattern = re.compile(
            r'^(?P<number>\d+(\.\d+)*)\s+(?P<title>.+?)$',
            re.MULTILINE
        )
        
        # Trouver toutes les sections
        sections = []
        
        # Rechercher les sections markdown
        for match in section_pattern.finditer(document_text):
            level = len(match.group('level'))
            title = match.group('title').strip()
            start = match.start()
            
            sections.append({
                'type': 'section',
                'level': level,
                'title': title,
                'start': start,
                'end': -1,  # Sera rempli plus tard
                'format': 'markdown'
            })
        
        # Rechercher les sections numérotées
        for match in numbered_section_pattern.finditer(document_text):
            number = match.group('number')
            title = match.group('title').strip()
            start = match.start()
            
            # Estimer le niveau en fonction du nombre de points
            level = number.count('.') + 1
            
            sections.append({
                'type': 'section',
                'level': level,
                'number': number,
                'title': title,
                'start': start,
                'end': -1,  # Sera rempli plus tard
                'format': 'numbered'
            })
        
        # Trier les sections par position
        sections.sort(key=lambda s: s['start'])
        
        # Déterminer la fin de chaque section
        for i in range(len(sections) - 1):
            sections[i]['end'] = sections[i + 1]['start']
        
        # La dernière section se termine à la fin du document
        if sections:
            sections[-1]['end'] = len(document_text)
        
        # Construire la hiérarchie des sections
        hierarchy = []
        section_stack = []
        
        for section in sections:
            level = section['level']
            
            # Retirer du stack les sections de niveau supérieur ou égal
            while section_stack and section_stack[-1]['level'] >= level:
                section_stack.pop()
            
            # Ajouter cette section au parent approprié
            if section_stack:
                parent = section_stack[-1]
                if 'children' not in parent:
                    parent['children'] = []
                parent['children'].append(section)
            else:
                hierarchy.append(section)
            
            # Ajouter cette section au stack
            section_stack.append(section)
        
        return {
            'sections': sections,
            'hierarchy': hierarchy,
            'section_count': len(sections)
        }
