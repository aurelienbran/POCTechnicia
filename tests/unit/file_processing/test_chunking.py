"""
Tests unitaires pour les composants de chunking.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.core.file_processing.chunking.base import TextChunker, ChunkingResult
from app.core.file_processing.chunking.simple import SimpleTextChunker
from app.core.file_processing.chunking.semantic import SemanticTextChunker
from app.core.file_processing.chunking.factory import get_text_chunker

# Données de test
SAMPLE_TEXT = """
Ceci est un exemple de texte à découper en chunks pour les tests unitaires.
Il contient plusieurs paragraphes.

Ce paragraphe est séparé du précédent par une ligne vide.
Ceci est une phrase supplémentaire dans le même paragraphe.

Voici un troisième paragraphe avec suffisamment de contenu 
pour tester divers scénarios de chunking.
Nous incluons quelques phrases supplémentaires pour s'assurer 
que le texte est assez long pour être découpé en plusieurs chunks.

Ce dernier paragraphe contient des informations additionnelles
qui permettront de tester les différentes stratégies de chunking,
notamment avec différentes tailles de chunks et de chevauchement.
"""

@pytest.fixture
def sample_text():
    """Fixture pour un exemple de texte."""
    return SAMPLE_TEXT

@pytest.mark.asyncio
async def test_simple_chunker_basic(sample_text):
    """Teste le chunker simple avec des paramètres de base."""
    # Créer un chunker simple
    chunker = SimpleTextChunker()
    
    # Paramètres de chunking
    chunk_size = 100
    overlap = 0
    
    # Découper le texte
    result = await chunker.chunk_text(sample_text, max_chunk_size=chunk_size, overlap=overlap)
    
    # Vérifier le résultat
    assert result.success is True
    assert len(result.chunks) > 1  # Le texte devrait être découpé en plusieurs chunks
    assert "chunk_count" in result.metadata
    assert result.metadata["chunk_count"] == len(result.chunks)
    
    # Vérifier que chaque chunk respecte la taille maximale
    for chunk in result.chunks:
        assert len(chunk) <= chunk_size

@pytest.mark.asyncio
async def test_simple_chunker_with_overlap(sample_text):
    """Teste le chunker simple avec chevauchement."""
    # Créer un chunker simple
    chunker = SimpleTextChunker()
    
    # Paramètres de chunking
    chunk_size = 100
    overlap = 30
    
    # Découper le texte
    result = await chunker.chunk_text(sample_text, max_chunk_size=chunk_size, overlap=overlap)
    
    # Vérifier le résultat
    assert result.success is True
    assert len(result.chunks) > 1
    
    # Vérifier que les chunks se chevauchent
    # Prenons les deux premiers chunks et vérifions qu'ils partagent du contenu
    if len(result.chunks) >= 2:
        chunk1 = result.chunks[0]
        chunk2 = result.chunks[1]
        
        # Le début du second chunk devrait être présent à la fin du premier
        end_of_first = chunk1[-overlap:] if len(chunk1) > overlap else chunk1
        start_of_second = chunk2[:len(end_of_first)]
        
        # Il devrait y avoir un certain chevauchement, même s'il n'est pas exact à cause des limites de mots
        assert len(set(end_of_first.split()) & set(start_of_second.split())) > 0

@pytest.mark.asyncio
async def test_simple_chunker_empty_text():
    """Teste le chunker simple avec un texte vide."""
    # Créer un chunker simple
    chunker = SimpleTextChunker()
    
    # Paramètres de chunking
    chunk_size = 100
    overlap = 0
    
    # Découper un texte vide
    result = await chunker.chunk_text("", max_chunk_size=chunk_size, overlap=overlap)
    
    # Vérifier le résultat
    assert result.success is True
    assert len(result.chunks) == 0  # Pas de chunks pour un texte vide
    assert result.metadata["chunk_count"] == 0

@pytest.mark.asyncio
async def test_simple_chunker_single_chunk(sample_text):
    """Teste le chunker simple avec une taille de chunk plus grande que le texte."""
    # Créer un chunker simple
    chunker = SimpleTextChunker()
    
    # Paramètres de chunking (taille suffisamment grande pour tout le texte)
    chunk_size = len(sample_text) * 2
    overlap = 0
    
    # Découper le texte
    result = await chunker.chunk_text(sample_text, max_chunk_size=chunk_size, overlap=overlap)
    
    # Vérifier le résultat
    assert result.success is True
    assert len(result.chunks) == 1  # Un seul chunk
    assert result.metadata["chunk_count"] == 1
    assert result.chunks[0] == sample_text  # Le chunk devrait être le texte complet

@pytest.mark.asyncio
async def test_semantic_chunker_basic(sample_text):
    """Teste le chunker sémantique avec des paramètres de base."""
    # Skip si spaCy n'est pas disponible
    try:
        import spacy
        # Skip si le modèle français n'est pas disponible
        try:
            nlp = spacy.load("fr_core_news_sm")
        except:
            pytest.skip("Modèle spaCy français non disponible")
    except ImportError:
        pytest.skip("spaCy non disponible")
    
    # Créer un chunker sémantique
    chunker = SemanticTextChunker()
    
    # Paramètres de chunking
    chunk_size = 100
    overlap = 0
    
    # Découper le texte
    result = await chunker.chunk_text(sample_text, max_chunk_size=chunk_size, overlap=overlap)
    
    # Vérifier le résultat
    assert result.success is True
    assert len(result.chunks) > 0
    assert "chunk_count" in result.metadata
    assert result.metadata["chunk_count"] == len(result.chunks)
    
    # Vérifier que chaque chunk respecte la taille maximale (avec une certaine tolérance)
    for chunk in result.chunks:
        # Les chunks sémantiques peuvent parfois dépasser légèrement la taille max
        # pour préserver l'intégrité des phrases/paragraphes
        assert len(chunk) <= chunk_size * 1.2

@pytest.mark.asyncio
async def test_semantic_chunker_paragraph_mode(sample_text):
    """Teste le chunker sémantique en mode paragraphe."""
    # Skip si spaCy n'est pas disponible
    try:
        import spacy
        try:
            nlp = spacy.load("fr_core_news_sm")
        except:
            pytest.skip("Modèle spaCy français non disponible")
    except ImportError:
        pytest.skip("spaCy non disponible")
    
    # Créer un chunker sémantique
    chunker = SemanticTextChunker()
    
    # Paramètres de chunking
    chunk_size = 200
    overlap = 0
    chunk_strategy = "paragraph"
    
    # Découper le texte
    result = await chunker.chunk_text(
        sample_text, 
        max_chunk_size=chunk_size, 
        overlap=overlap,
        chunk_strategy=chunk_strategy
    )
    
    # Vérifier le résultat
    assert result.success is True
    
    # Vérifier que les chunks respectent les limites de paragraphes
    # Compter les paragraphes dans le texte original (séparés par des lignes vides)
    original_paragraphs = [p for p in sample_text.split("\n\n") if p.strip()]
    
    # Le nombre de chunks devrait être au moins égal au nombre de paragraphes 
    # ou plus petit si certains paragraphes sont combinés 
    # (car certains paragraphes peuvent être trop petits pour former un chunk)
    assert len(result.chunks) <= len(original_paragraphs)

@pytest.mark.asyncio
async def test_chunker_factory():
    """Teste la factory de chunkers."""
    # Tester l'obtention d'un chunker simple
    simple_chunker = await get_text_chunker("simple")
    assert isinstance(simple_chunker, SimpleTextChunker)
    
    # Tester l'obtention d'un chunker sémantique (si disponible)
    try:
        import spacy
        try:
            nlp = spacy.load("fr_core_news_sm")
            semantic_chunker = await get_text_chunker("semantic")
            assert isinstance(semantic_chunker, SemanticTextChunker)
        except:
            # Si le modèle français n'est pas disponible, la factory devrait retourner un SimpleTextChunker
            semantic_chunker = await get_text_chunker("semantic")
            assert isinstance(semantic_chunker, SimpleTextChunker)
    except ImportError:
        # Si spaCy n'est pas disponible, la factory devrait retourner un SimpleTextChunker
        semantic_chunker = await get_text_chunker("semantic")
        assert isinstance(semantic_chunker, SimpleTextChunker)
    
    # Tester avec un type inconnu (devrait retourner le chunker par défaut)
    default_chunker = await get_text_chunker("unknown_type")
    assert isinstance(default_chunker, SimpleTextChunker)

@pytest.mark.asyncio
async def test_chunker_custom_separator(sample_text):
    """Teste le chunker avec des séparateurs personnalisés."""
    # Créer un chunker simple
    chunker = SimpleTextChunker()
    
    # Paramètres de chunking avec séparateur personnalisé
    chunk_size = 100
    overlap = 0
    separators = ["\n\n", ".", ","]  # Priorité: paragraphe, phrase, virgule
    
    # Découper le texte
    result = await chunker.chunk_text(
        sample_text, 
        max_chunk_size=chunk_size, 
        overlap=overlap,
        separators=separators
    )
    
    # Vérifier le résultat
    assert result.success is True
    assert len(result.chunks) > 0
    
    # Vérifier que les chunks se terminent par un des séparateurs (ou sont la fin du texte)
    for i, chunk in enumerate(result.chunks):
        if i < len(result.chunks) - 1:  # Tous sauf le dernier chunk
            # Le chunk devrait se terminer par un des séparateurs
            assert any(chunk.endswith(sep) for sep in separators) or len(chunk) >= chunk_size

@pytest.mark.asyncio
async def test_chunking_very_long_text():
    """Teste le comportement des chunkers avec un texte très long."""
    # Créer un texte long en répétant le texte d'exemple
    very_long_text = SAMPLE_TEXT * 10  # 10 fois le texte d'exemple
    
    # Créer un chunker simple
    chunker = SimpleTextChunker()
    
    # Paramètres de chunking
    chunk_size = 200
    overlap = 50
    
    # Mesurer le temps de traitement
    start_time = asyncio.get_event_loop().time()
    
    # Découper le texte
    result = await chunker.chunk_text(very_long_text, max_chunk_size=chunk_size, overlap=overlap)
    
    end_time = asyncio.get_event_loop().time()
    processing_time = end_time - start_time
    
    # Vérifier le résultat
    assert result.success is True
    assert len(result.chunks) > 10  # Devrait produire de nombreux chunks
    
    # Vérifier que le temps de traitement est raisonnable (moins de 1 seconde pour ce volume)
    assert processing_time < 1.0
    
    # Vérifier que la taille totale de tous les chunks (avec chevauchement) est supérieure 
    # à la taille du texte original
    total_chunks_size = sum(len(chunk) for chunk in result.chunks)
    assert total_chunks_size > len(very_long_text)
    
    # Vérifier la métrique de chevauchement
    overlap_size = total_chunks_size - len(very_long_text)
    expected_overlap_size = (len(result.chunks) - 1) * overlap  # Approximation
    assert abs(overlap_size - expected_overlap_size) < len(very_long_text) * 0.1  # Tolérance de 10%

@pytest.mark.asyncio
async def test_comparison_chunkers(sample_text):
    """Compare les résultats des différents chunkers."""
    # Créer les chunkers
    simple_chunker = SimpleTextChunker()
    
    # Paramètres de chunking identiques pour les deux chunkers
    chunk_size = 100
    overlap = 20
    
    # Découper le texte avec le chunker simple
    simple_result = await simple_chunker.chunk_text(
        sample_text, 
        max_chunk_size=chunk_size, 
        overlap=overlap
    )
    
    # Tester le chunker sémantique si disponible
    try:
        import spacy
        try:
            nlp = spacy.load("fr_core_news_sm")
            semantic_chunker = SemanticTextChunker()
            
            # Découper le texte avec le chunker sémantique
            semantic_result = await semantic_chunker.chunk_text(
                sample_text, 
                max_chunk_size=chunk_size, 
                overlap=overlap
            )
            
            # Comparer les résultats
            assert simple_result.success and semantic_result.success
            
            # Le nombre de chunks peut être différent
            # En général, le chunker sémantique devrait créer moins de chunks
            # car il essaie de préserver la cohérence sémantique
            print(f"Chunks simples: {len(simple_result.chunks)}")
            print(f"Chunks sémantiques: {len(semantic_result.chunks)}")
            
            # Vérifier que tous les chunks respectent la taille maximale (avec une certaine tolérance pour le sémantique)
            for chunk in simple_result.chunks:
                assert len(chunk) <= chunk_size
            
            for chunk in semantic_result.chunks:
                assert len(chunk) <= chunk_size * 1.2
                
        except:
            pytest.skip("Modèle spaCy français non disponible")
    except ImportError:
        pytest.skip("spaCy non disponible")
