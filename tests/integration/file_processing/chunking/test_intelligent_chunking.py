"""
Tests d'intégration pour le chunking intelligent et les métadonnées enrichies
============================================================================

Ce module contient les tests d'intégration qui vérifient le bon fonctionnement
du système de chunking intelligent, incluant la préservation des relations 
entre éléments et l'enrichissement des métadonnées.

Ces tests assurent que le système complet de chunking fonctionne correctement
dans des scénarios réels, avec différents types de documents techniques.

Auteur: Équipe Technicia
Date: Avril 2025
"""

import os
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
import logging
from typing import List, Dict, Any, Optional
import json

from app.core.file_processing.chunking.semantic import SemanticTextChunker
from app.core.file_processing.chunking.relational_chunker import RelationalChunker
from app.core.file_processing.chunking.metadata_enricher import MetadataEnricher
from app.core.file_processing.chunking.base import ChunkingResult

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Répertoire de test pour les fichiers d'exemple
TEST_FILES_DIR = Path(__file__).parent.parent.parent.parent / "test_files"
if not TEST_FILES_DIR.exists():
    TEST_FILES_DIR.mkdir(parents=True)


@pytest.fixture
async def semantic_chunker():
    """
    Fixture qui crée un chunker sémantique pour les tests.
    
    Returns:
        Une instance configurée de SemanticTextChunker
    """
    # Configuration de base pour les tests
    config = {
        'default_max_chunk_size': 500,
        'default_overlap': 50,
        'respect_semantic_boundaries': True,
        'fallback_to_simple': True
    }
    
    # Créer et initialiser le chunker
    chunker = SemanticTextChunker(config)
    await chunker._initialize()
    
    yield chunker


@pytest.fixture
async def relational_chunker():
    """
    Fixture qui crée un chunker relationnel pour les tests.
    
    Returns:
        Une instance configurée de RelationalChunker
    """
    # Configuration de base pour les tests
    config = {
        'semantic_chunker_config': {
            'default_max_chunk_size': 500,
            'default_overlap': 50
        },
        'metadata_enricher_config': {
            'extract_entities': True,
            'detect_key_terms': True,
            'compute_embeddings': True
        },
        'preserve_structural_elements': True,
        'link_references': True,
        'detect_element_types': True
    }
    
    # Créer et initialiser le chunker
    chunker = RelationalChunker(config)
    
    yield chunker


@pytest.fixture
def metadata_enricher():
    """
    Fixture qui crée un enrichisseur de métadonnées pour les tests.
    
    Returns:
        Une instance configurée de MetadataEnricher
    """
    # Configuration de base pour les tests
    config = {
        'extract_entities': True,
        'detect_key_terms': True,
        'compute_embeddings': True,
        'entity_types': ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT']
    }
    
    # Créer l'enrichisseur
    enricher = MetadataEnricher(config)
    
    yield enricher


@pytest.fixture
def technical_document():
    """
    Fixture qui crée un document technique de test.
    
    Returns:
        Chemin vers le document technique de test
    """
    # Créer un fichier temporaire pour les tests
    temp_dir = tempfile.mkdtemp()
    test_doc_path = Path(temp_dir) / "technical_document.txt"
    
    # Écrire un contenu technique pour les tests
    with open(test_doc_path, "w", encoding="utf-8") as f:
        f.write("""# Manuel de maintenance du système de refroidissement

## 1. Introduction
Ce manuel explique les procédures de maintenance du système de refroidissement Technicia X-2000.

## 2. Composants principaux
Le système comprend les éléments suivants:
* Pompe principale (réf. P-3421)
* Échangeur thermique (réf. ET-789)
* Capteurs de température (x4)
* Circuit de fluide caloporteur

### 2.1 Schéma du système
Voir Figure 1 pour le schéma complet du circuit.

## 3. Procédures de maintenance

### 3.1 Vérification des niveaux
1. Assurez-vous que le système est hors tension
2. Consultez le manomètre sur le panneau avant
3. Le niveau doit se situer entre 2.3 et 2.7 bars

### 3.2 Remplacement du fluide
Comme indiqué dans le Tableau 1, le fluide doit être remplacé tous les 12 mois.

#### Formule de calcul de la viscosité
La viscosité du fluide peut être calculée avec l'équation suivante:
η = η₀ * e^(-αT)

où:
* η est la viscosité dynamique
* η₀ est la viscosité à température de référence
* α est le coefficient de température
* T est la température en Celsius

## 4. Diagnostic des pannes
En cas de surchauffe, référez-vous à la Section 5.2 du manuel principal.

Jean Dupont, Ingénieur Technicia
        """)
    
    yield test_doc_path
    
    # Nettoyer
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_semantic_chunking(semantic_chunker, technical_document):
    """
    Vérifie que le chunking sémantique fonctionne correctement.
    
    Args:
        semantic_chunker: Fixture du chunker sémantique
        technical_document: Fixture du document technique
    """
    # Lire le contenu du document
    with open(technical_document, "r", encoding="utf-8") as f:
        document_text = f.read()
    
    # Appliquer le chunking sémantique
    chunking_result = await semantic_chunker.chunk_text(
        text=document_text,
        max_chunk_size=300,
        overlap=50
    )
    
    # Vérifier que des chunks ont été générés
    assert chunking_result.chunks is not None
    assert len(chunking_result.chunks) > 0
    
    # Vérifier que les chunks ont une taille raisonnable
    for chunk in chunking_result.chunks:
        assert len(chunk['text']) <= 350  # Max size + tolerance
    
    # Vérifier que les chunks contiennent du texte significatif
    for chunk in chunking_result.chunks:
        assert len(chunk['text'].strip()) > 0
        assert 'metadata' in chunk
    
    # Vérifier qu'il y a un chevauchement entre chunks consécutifs
    overlaps_found = 0
    for i in range(len(chunking_result.chunks) - 1):
        chunk1 = chunking_result.chunks[i]['text']
        chunk2 = chunking_result.chunks[i + 1]['text']
        
        # Rechercher les derniers 40 caractères du chunk précédent 
        # dans les 100 premiers caractères du chunk suivant
        overlap = any(chunk1[-40:].find(s) >= 0 for s in [chunk2[:100]])
        if overlap:
            overlaps_found += 1
    
    # Au moins 50% des chunks devraient avoir un chevauchement
    assert overlaps_found >= (len(chunking_result.chunks) - 1) / 2
    
    # Vérifier les métadonnées de base
    assert 'total_chunks' in chunking_result.metadata
    assert chunking_result.metadata['total_chunks'] == len(chunking_result.chunks)
    assert 'chunking_method' in chunking_result.metadata
    assert chunking_result.metadata['chunking_method'] == "semantic"


@pytest.mark.asyncio
async def test_relational_chunking(relational_chunker, technical_document):
    """
    Vérifie que le chunking relationnel fonctionne correctement.
    
    Args:
        relational_chunker: Fixture du chunker relationnel
        technical_document: Fixture du document technique
    """
    # Lire le contenu du document
    with open(technical_document, "r", encoding="utf-8") as f:
        document_text = f.read()
    
    # Appliquer le chunking relationnel
    chunking_result = await relational_chunker.chunk_text(
        text=document_text,
        max_chunk_size=300,
        overlap=50
    )
    
    # Vérifier que des chunks ont été générés
    assert chunking_result.chunks is not None
    assert len(chunking_result.chunks) > 0
    
    # Vérifier que les métadonnées contiennent des informations sur les éléments structurels
    assert 'has_structural_elements' in chunking_result.metadata
    
    # Vérifier que des éléments structurels ont été détectés
    has_structural_elements = False
    for chunk in chunking_result.chunks:
        structural_elements = chunk.get('metadata', {}).get('structural_elements', [])
        if structural_elements:
            has_structural_elements = True
            break
    
    assert has_structural_elements, "Aucun élément structurel détecté dans les chunks"
    
    # Vérifier que des relations ont été établies entre les chunks
    has_relations = False
    for chunk in chunking_result.chunks:
        relations = chunk.get('metadata', {}).get('relations', [])
        if relations:
            has_relations = True
            break
    
    assert has_relations, "Aucune relation établie entre les chunks"
    
    # Vérifier les IDs des chunks
    for chunk in chunking_result.chunks:
        assert 'id' in chunk
        assert isinstance(chunk['id'], str)
        assert len(chunk['id']) > 0
    
    # Vérifier que le type de chunking est correct
    assert chunking_result.metadata.get('chunking_method') == "relational"


@pytest.mark.asyncio
async def test_metadata_enrichment(metadata_enricher, semantic_chunker, technical_document):
    """
    Vérifie que l'enrichissement des métadonnées fonctionne correctement.
    
    Args:
        metadata_enricher: Fixture de l'enrichisseur de métadonnées
        semantic_chunker: Fixture du chunker sémantique
        technical_document: Fixture du document technique
    """
    # Lire le contenu du document
    with open(technical_document, "r", encoding="utf-8") as f:
        document_text = f.read()
    
    # Générer des chunks avec le chunker sémantique
    chunking_result = await semantic_chunker.chunk_text(
        text=document_text,
        max_chunk_size=300,
        overlap=50
    )
    
    # Enrichir les métadonnées
    enriched_result = metadata_enricher.enrich_chunks(chunking_result)
    
    # Vérifier que l'enrichissement a été effectué
    assert enriched_result.metadata.get('enriched') is True
    
    # Vérifier que les chunks ont des métadonnées enrichies
    for chunk in enriched_result.chunks:
        # Vérifier les entités
        if metadata_enricher.extract_entities:
            assert 'entities' in chunk['metadata']
        
        # Vérifier les termes clés
        if metadata_enricher.detect_key_terms:
            assert 'key_terms' in chunk['metadata']
            assert isinstance(chunk['metadata']['key_terms'], list)
            
        # Vérifier les statistiques de texte
        assert 'char_count' in chunk['metadata']
        assert 'word_count' in chunk['metadata']
        assert 'sentence_count' in chunk['metadata']
        
        # Vérifier les embeddings ou leur référence
        if metadata_enricher.compute_embeddings:
            assert 'has_embedding' in chunk['metadata']
            assert chunk['metadata']['has_embedding'] is True
    
    # Vérifier que des relations ont été établies
    for chunk in enriched_result.chunks:
        # Au moins certains chunks devraient avoir des relations
        if 'relations' in chunk['metadata']:
            # Vérifier la structure des relations
            for relation in chunk['metadata']['relations']:
                assert 'chunk_id' in relation
                assert 'type' in relation
                # Les relations peuvent être de similarité ou de séquence
                assert relation['type'] in ['semantic_similarity', 'previous', 'next']


@pytest.mark.asyncio
async def test_complete_chunking_pipeline(relational_chunker, technical_document):
    """
    Teste le pipeline complet de chunking, de l'entrée à la sortie.
    
    Args:
        relational_chunker: Fixture du chunker relationnel
        technical_document: Fixture du document technique
    """
    # Lire le contenu du document
    with open(technical_document, "r", encoding="utf-8") as f:
        document_text = f.read()
    
    # Métadonnées du document
    document_metadata = {
        "title": "Manuel de maintenance du système de refroidissement",
        "author": "Jean Dupont",
        "type": "technical_manual",
        "creation_date": "2025-04-02"
    }
    
    # Appliquer le chunking relationnel au niveau document
    chunking_result = await relational_chunker.chunk_document(
        document_text=document_text,
        document_metadata=document_metadata,
        max_chunk_size=300,
        overlap=50
    )
    
    # Vérifier que des chunks ont été générés
    assert chunking_result.chunks is not None
    assert len(chunking_result.chunks) > 0
    
    # Vérifier que les métadonnées du document ont été ajoutées aux chunks
    for chunk in chunking_result.chunks:
        assert 'document_title' in chunk['metadata']
        assert chunk['metadata']['document_title'] == document_metadata['title']
        assert 'document_author' in chunk['metadata']
        assert chunk['metadata']['document_author'] == document_metadata['author']
    
    # Vérifier la détection de la structure du document
    assert 'document_structure' in chunking_result.metadata
    
    # Écrire le résultat dans un fichier JSON pour inspection
    output_dir = Path(tempfile.mkdtemp())
    try:
        output_file = output_dir / "chunking_result.json"
        
        # Convertir le résultat en dictionnaire sérialisable
        result_dict = {
            "metadata": chunking_result.metadata,
            "chunks": chunking_result.chunks,
            "stats": {
                "chunk_count": len(chunking_result.chunks),
                "avg_chunk_size": sum(len(c['text']) for c in chunking_result.chunks) / len(chunking_result.chunks),
                "total_relations": sum(len(c.get('metadata', {}).get('relations', [])) for c in chunking_result.chunks)
            }
        }
        
        # Écrire dans le fichier JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        
        # Vérifier que le fichier a été créé
        assert output_file.exists()
        
    finally:
        # Nettoyer
        shutil.rmtree(output_dir)


if __name__ == "__main__":
    # Pour exécution manuelle des tests
    pytest.main(["-xvs", __file__])
