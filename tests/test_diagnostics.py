"""Tests pour les outils de diagnostic."""
import pytest
from pathlib import Path
from app.diagnostics.pdf_analyzer import PDFAnalyzer
from app.diagnostics.search_analyzer import SearchAnalyzer
from app.diagnostics.response_analyzer import ResponseAnalyzer
from app.core.pdf_processor import PDFProcessor
from app.core.vector_store import VectorStore
from app.core.llm_interface import LLMInterface
from app.core.rag_engine import RAGEngine

# Fixtures
@pytest.fixture
def pdf_analyzer():
    return PDFAnalyzer(PDFProcessor())

@pytest.fixture
def search_analyzer(vector_store):
    return SearchAnalyzer(vector_store)

@pytest.fixture
def response_analyzer(llm_interface):
    return ResponseAnalyzer(llm_interface)

# Tests PDF Analyzer
@pytest.mark.asyncio
async def test_section_analysis(pdf_analyzer, test_pdf):
    """Test l'analyse des sections d'un PDF."""
    stats = await pdf_analyzer.analyze_sections(test_pdf)
    assert "total_sections" in stats
    assert "sections_with_content" in stats
    assert "avg_section_length" in stats
    assert "sections_details" in stats

@pytest.mark.asyncio
async def test_chunk_distribution(pdf_analyzer, test_pdf):
    """Test l'analyse de la distribution des chunks."""
    stats = await pdf_analyzer.analyze_chunk_distribution(test_pdf)
    assert "total_chunks" in stats
    assert "avg_chunk_size" in stats
    assert "size_distribution" in stats
    assert "page_distribution" in stats
    assert "potential_issues" in stats

# Tests Search Analyzer
@pytest.mark.asyncio
async def test_search_analysis(search_analyzer):
    """Test l'analyse des résultats de recherche."""
    query = "EL-37 problèmes"
    stats = await search_analyzer.analyze_search_results(query)
    assert "total_results" in stats
    assert "avg_score" in stats
    assert "score_distribution" in stats
    assert "section_coverage" in stats

@pytest.mark.asyncio
async def test_query_pattern_analysis(search_analyzer):
    """Test l'analyse des patterns de requête."""
    query = "EL-37 problèmes maintenance"
    stats = await search_analyzer.analyze_query_patterns(query)
    assert "identified_patterns" in stats
    assert "suggestions" in stats
    assert any(p["type"] == "section_reference" for p in stats["identified_patterns"])
    assert any(p["type"] == "technical_keywords" for p in stats["identified_patterns"])

# Tests Response Analyzer
def test_response_structure_analysis(response_analyzer):
    """Test l'analyse de la structure des réponses."""
    response = """
    DESCRIPTION
    Description du problème
    
    INFORMATIONS TECHNIQUES
    Détails techniques
    
    INSTRUCTIONS ET PRÉCAUTIONS
    Instructions à suivre
    
    SOURCES
    - doc1.pdf (pertinence: 85%)
    """
    stats = response_analyzer.analyze_response_structure(response)
    assert all(stats["sections_present"].values())
    assert "content_stats" in stats
    assert "formatting" in stats

def test_technical_content_analysis(response_analyzer):
    """Test l'analyse du contenu technique."""
    response = """
    DESCRIPTION
    Problème sur EL-37 nécessitant une maintenance.
    
    INFORMATIONS TECHNIQUES
    Système en panne, erreur détectée.
    """
    stats = response_analyzer.analyze_technical_content(response)
    assert "EL-37" in stats["section_references"]
    assert len(stats["technical_terms"]) > 0

def test_source_usage_analysis(response_analyzer):
    """Test l'analyse de l'utilisation des sources."""
    response = """
    DESCRIPTION
    Problème identifié
    
    SOURCES
    - manual.pdf (pertinence: 85%)
    - guide.pdf (pertinence: 70%)
    """
    stats = response_analyzer.analyze_source_usage(response)
    assert len(stats["sources_cited"]) == 2
    assert all(s["score"] >= 70 for s in stats["sources_cited"])

# Tests d'intégration
@pytest.mark.asyncio
async def test_full_diagnostic_workflow(pdf_analyzer, search_analyzer, response_analyzer, test_pdf):
    """Test le workflow complet de diagnostic."""
    # 1. Analyser le PDF
    pdf_stats = await pdf_analyzer.analyze_sections(test_pdf)
    assert pdf_stats["total_sections"] > 0
    
    # 2. Analyser la recherche
    search_stats = await search_analyzer.analyze_search_results("EL-37 problèmes")
    assert search_stats["total_results"] > 0
    
    # 3. Analyser la réponse
    response = """
    DESCRIPTION
    Problème sur EL-37
    
    INFORMATIONS TECHNIQUES
    Détails du problème
    
    SOURCES
    - doc.pdf (pertinence: 80%)
    """
    response_stats = response_analyzer.analyze_response_structure(response)
    assert response_stats["sections_present"]["DESCRIPTION"]
    
    # Vérifier la cohérence
    assert any(s["section_id"] == "EL-37" for s in pdf_stats["sections_details"])
    assert "EL-37" in response_stats["sections_present"]
