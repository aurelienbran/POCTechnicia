"""
Système de métadonnées enrichies pour les chunks de texte
======================================================================

Ce module améliore les chunks de texte avec des métadonnées sémantiques
et établit les relations entre les différents chunks pour une meilleure
contextualisation et recherche.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import re
import nltk
from typing import List, Dict, Any, Optional, Set, Union, Tuple
import logging
import time
from pathlib import Path
import numpy as np
import json
from datetime import datetime
import hashlib

from .base import ChunkingResult

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """
    Enrichisseur de métadonnées pour les chunks de texte.
    
    Cette classe ajoute des informations sémantiques et structurelles
    aux chunks et établit des relations entre eux pour améliorer
    la recherche et la contextualisation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'enrichisseur de métadonnées.
        
        Args:
            config: Configuration de l'enrichisseur
                - extract_entities: Extraire les entités nommées (défaut: True)
                - detect_key_terms: Détecter les termes clés (défaut: True)
                - compute_embeddings: Calculer des embeddings pour les chunks (défaut: True)
                - entity_types: Types d'entités à extraire (défaut: ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT'])
                - embedding_model: Modèle pour calculer les embeddings (défaut: 'paraphrase-multilingual-MiniLM-L12-v2')
                - max_distance_threshold: Seuil maximal de distance pour considérer des chunks comme liés (défaut: 0.7)
        """
        self.config = config or {}
        self.extract_entities = self.config.get('extract_entities', True)
        self.detect_key_terms = self.config.get('detect_key_terms', True)
        self.compute_embeddings = self.config.get('compute_embeddings', True)
        
        self.entity_types = self.config.get('entity_types', ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT'])
        self.embedding_model = self.config.get('embedding_model', 'paraphrase-multilingual-MiniLM-L12-v2')
        self.max_distance_threshold = self.config.get('max_distance_threshold', 0.7)
        
        # Cache pour éviter de recalculer les métadonnées
        self._metadata_cache = {}
        self._embedding_cache = {}
        
        # Pour les liens entre chunks
        self._chunk_links = {}
        
        # Initialiser les modèles NLP si nécessaire
        self._initialize_nlp_models()
    
    def _initialize_nlp_models(self):
        """
        Initialise les modèles NLP nécessaires pour l'enrichissement.
        """
        # Note: Dans une implémentation réelle, on chargerait ici les modèles NLP
        # Pour cette démonstration, nous simulons simplement l'initialisation
        self.nlp_initialized = True
        logger.info("Modèles NLP initialisés pour l'enrichissement de métadonnées")
    
    def enrich_chunks(self, chunking_result: ChunkingResult) -> ChunkingResult:
        """
        Enrichit les chunks avec des métadonnées et établit des relations.
        
        Args:
            chunking_result: Résultat du chunking à enrichir
            
        Returns:
            Résultat du chunking enrichi
        """
        start_time = time.time()
        
        # Collecter les chunks et leurs métadonnées existantes
        chunks = chunking_result.chunks
        if not chunks:
            logger.warning("Aucun chunk à enrichir")
            return chunking_result
        
        logger.info(f"Enrichissement de {len(chunks)} chunks avec des métadonnées")
        
        # Enrichir chaque chunk individuellement
        enriched_chunks = []
        for chunk in chunks:
            try:
                enriched_chunk = self._enrich_single_chunk(chunk)
                enriched_chunks.append(enriched_chunk)
            except Exception as e:
                logger.error(f"Erreur lors de l'enrichissement d'un chunk: {str(e)}")
                enriched_chunks.append(chunk)  # Garder le chunk original en cas d'erreur
        
        # Établir les relations entre les chunks
        linked_chunks = self._establish_chunk_relationships(enriched_chunks)
        
        # Mettre à jour le résultat de chunking
        chunking_result.chunks = linked_chunks
        
        # Ajouter des métadonnées globales
        chunking_result.metadata.update({
            "enriched": True,
            "enrichment_time": time.time() - start_time,
            "has_relationships": True,
            "enrichment_method": "semantic_metadata_enricher",
            "entities_extracted": self.extract_entities,
            "key_terms_detected": self.detect_key_terms,
            "embeddings_computed": self.compute_embeddings
        })
        
        logger.info(f"Enrichissement terminé en {time.time() - start_time:.2f} secondes")
        
        return chunking_result
    
    def _enrich_single_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrichit un seul chunk avec des métadonnées.
        
        Args:
            chunk: Chunk à enrichir
            
        Returns:
            Chunk enrichi
        """
        # Générer un ID unique pour le chunk s'il n'en a pas
        if 'id' not in chunk:
            chunk_text = chunk.get('text', '')
            chunk['id'] = self._generate_chunk_id(chunk_text)
        
        # Vérifier si ce chunk est déjà dans le cache
        if chunk['id'] in self._metadata_cache:
            # Mettre à jour les métadonnées depuis le cache
            chunk['metadata'] = {**chunk.get('metadata', {}), **self._metadata_cache[chunk['id']]}
            return chunk
        
        # Initialiser ou récupérer les métadonnées existantes
        chunk['metadata'] = chunk.get('metadata', {})
        
        # Extraire les entités nommées si configuré
        if self.extract_entities:
            entities = self._extract_entities(chunk['text'])
            chunk['metadata']['entities'] = entities
        
        # Détecter les termes clés si configuré
        if self.detect_key_terms:
            key_terms = self._detect_key_terms(chunk['text'])
            chunk['metadata']['key_terms'] = key_terms
        
        # Calculer l'embedding pour le chunk si configuré
        if self.compute_embeddings:
            chunk_embedding = self._compute_embedding(chunk['text'])
            # Stocker l'embedding dans le cache (pas dans les métadonnées directement car trop volumineux)
            self._embedding_cache[chunk['id']] = chunk_embedding
            
            # Ajouter une référence à l'embedding dans les métadonnées
            chunk['metadata']['has_embedding'] = True
            chunk['metadata']['embedding_model'] = self.embedding_model
        
        # Calculer des statistiques sur le contenu
        stats = self._compute_text_statistics(chunk['text'])
        chunk['metadata'].update(stats)
        
        # Ajouter un timestamp d'enrichissement
        chunk['metadata']['enriched_at'] = datetime.now().isoformat()
        
        # Sauvegarder dans le cache
        self._metadata_cache[chunk['id']] = chunk['metadata']
        
        return chunk
    
    def _generate_chunk_id(self, text: str) -> str:
        """
        Génère un ID unique pour un chunk basé sur son contenu.
        
        Args:
            text: Texte du chunk
            
        Returns:
            ID unique
        """
        # Utiliser un hash du texte pour générer un ID stable
        hash_object = hashlib.md5(text.encode())
        return f"chunk_{hash_object.hexdigest()[:12]}"
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extrait les entités nommées du texte.
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste des entités trouvées avec leur type et position
        """
        # Note: Dans une implémentation réelle, on utiliserait spaCy ou une autre librairie NER
        # Pour cette démonstration, nous simulons l'extraction d'entités
        
        # Simuler quelques entités
        entities = []
        common_entities = {
            'PERSON': ['Jean Dupont', 'Marie Martin'],
            'ORG': ['Technicia', 'Entreprise ABC'],
            'LOC': ['Paris', 'Lyon'],
            'PRODUCT': ['Modèle X-2000', 'Système Alpha']
        }
        
        for entity_type, entity_values in common_entities.items():
            for entity in entity_values:
                if entity.lower() in text.lower():
                    start = text.lower().find(entity.lower())
                    entities.append({
                        'text': entity,
                        'type': entity_type,
                        'start': start,
                        'end': start + len(entity)
                    })
        
        return entities
    
    def _detect_key_terms(self, text: str) -> List[str]:
        """
        Détecte les termes clés dans le texte.
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste des termes clés
        """
        # Note: Dans une implémentation réelle, on utiliserait des techniques comme TF-IDF ou KeyBERT
        # Pour cette démonstration, nous simulons la détection
        
        # Tokenization simple
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filtrer les mots courants (stopwords)
        stopwords = ['le', 'la', 'les', 'un', 'une', 'des', 'et', 'ou', 'est', 'sont']
        filtered_words = [w for w in words if w not in stopwords and len(w) > 3]
        
        # Compter les occurrences
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sélectionner les termes les plus fréquents
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        key_terms = [word for word, count in sorted_words[:10]]
        
        return key_terms
    
    def _compute_embedding(self, text: str) -> List[float]:
        """
        Calcule l'embedding d'un texte.
        
        Args:
            text: Texte à encoder
            
        Returns:
            Vecteur d'embedding
        """
        # Note: Dans une implémentation réelle, on utiliserait un modèle comme Sentence-BERT
        # Pour cette démonstration, nous simulons un embedding
        
        # Simuler un vecteur d'embedding de dimension 384 (typique pour MiniLM)
        np.random.seed(hash(text) % 2**32)
        embedding = np.random.normal(0, 1, 384)
        
        # Normaliser le vecteur
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.tolist()
    
    def _compute_text_statistics(self, text: str) -> Dict[str, Any]:
        """
        Calcule des statistiques sur le texte.
        
        Args:
            text: Texte à analyser
            
        Returns:
            Dictionnaire de statistiques
        """
        # Nombre de caractères
        char_count = len(text)
        
        # Nombre de mots
        words = re.findall(r'\b\w+\b', text)
        word_count = len(words)
        
        # Nombre de phrases (approximatif)
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Longueur moyenne des mots
        avg_word_length = sum(len(word) for word in words) / max(1, word_count)
        
        # Complexité lexicale (approximative)
        unique_words = len(set(word.lower() for word in words))
        lexical_diversity = unique_words / max(1, word_count)
        
        return {
            'char_count': char_count,
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_word_length': round(avg_word_length, 2),
            'unique_words': unique_words,
            'lexical_diversity': round(lexical_diversity, 2)
        }
    
    def _establish_chunk_relationships(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Établit des relations entre les chunks.
        
        Args:
            chunks: Liste des chunks à lier
            
        Returns:
            Liste des chunks avec leurs relations
        """
        if len(chunks) <= 1:
            return chunks
        
        logger.info(f"Établissement des relations entre {len(chunks)} chunks")
        
        # Calculer les similarités entre tous les chunks
        chunk_similarities = self._compute_chunk_similarities(chunks)
        
        # Créer les liens entre chunks
        for i, chunk in enumerate(chunks):
            chunk_id = chunk['id']
            
            # Initialiser le tableau de relations s'il n'existe pas
            if 'relations' not in chunk['metadata']:
                chunk['metadata']['relations'] = []
            
            # Trouver les chunks les plus similaires
            similar_chunks = sorted(
                [(j, sim) for j, sim in enumerate(chunk_similarities[i]) if j != i],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Sélectionner les chunks au-dessus du seuil de similarité
            for j, similarity in similar_chunks:
                if similarity >= self.max_distance_threshold:
                    related_chunk_id = chunks[j]['id']
                    
                    # Ajouter la relation
                    chunk['metadata']['relations'].append({
                        'chunk_id': related_chunk_id,
                        'similarity': round(similarity, 3),
                        'type': 'semantic_similarity'
                    })
        
        # Ajouter des relations de séquence (ordre des chunks)
        self._add_sequence_relations(chunks)
        
        return chunks
    
    def _compute_chunk_similarities(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """
        Calcule les similarités entre tous les chunks.
        
        Args:
            chunks: Liste des chunks
            
        Returns:
            Matrice de similarités
        """
        n_chunks = len(chunks)
        similarities = [[0.0 for _ in range(n_chunks)] for _ in range(n_chunks)]
        
        # Si les embeddings ne sont pas disponibles, retourner une matrice vide
        if not self.compute_embeddings:
            return similarities
        
        # Récupérer tous les embeddings
        embeddings = []
        for chunk in chunks:
            chunk_id = chunk['id']
            if chunk_id in self._embedding_cache:
                embedding = np.array(self._embedding_cache[chunk_id])
                embeddings.append(embedding)
            else:
                # Si l'embedding n'est pas dans le cache, en calculer un à la volée
                embedding = np.array(self._compute_embedding(chunk['text']))
                embeddings.append(embedding)
        
        # Calculer les similarités cosinus entre tous les embeddings
        for i in range(n_chunks):
            for j in range(n_chunks):
                if i == j:
                    similarities[i][j] = 1.0  # Similarité maximale avec soi-même
                else:
                    # Similarité cosinus
                    dot_product = np.dot(embeddings[i], embeddings[j])
                    similarities[i][j] = dot_product
        
        return similarities
    
    def _add_sequence_relations(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Ajoute des relations de séquence entre les chunks.
        
        Args:
            chunks: Liste des chunks à lier
        """
        for i, chunk in enumerate(chunks):
            # Établir des liens avec les chunks précédent et suivant
            if i > 0:
                prev_chunk_id = chunks[i-1]['id']
                self._add_relation(chunk, prev_chunk_id, 'previous', 1.0)
            
            if i < len(chunks) - 1:
                next_chunk_id = chunks[i+1]['id']
                self._add_relation(chunk, next_chunk_id, 'next', 1.0)
    
    def _add_relation(self, 
                     chunk: Dict[str, Any], 
                     related_id: str, 
                     relation_type: str, 
                     strength: float) -> None:
        """
        Ajoute une relation à un chunk.
        
        Args:
            chunk: Chunk à modifier
            related_id: ID du chunk lié
            relation_type: Type de relation (previous, next, semantic, etc.)
            strength: Force de la relation (entre 0 et 1)
        """
        # S'assurer que le tableau de relations existe
        if 'relations' not in chunk['metadata']:
            chunk['metadata']['relations'] = []
        
        # Vérifier si la relation existe déjà
        for relation in chunk['metadata']['relations']:
            if relation['chunk_id'] == related_id and relation['type'] == relation_type:
                # La relation existe déjà, ne pas la dupliquer
                return
        
        # Ajouter la nouvelle relation
        chunk['metadata']['relations'].append({
            'chunk_id': related_id,
            'type': relation_type,
            'strength': round(strength, 3)
        })
