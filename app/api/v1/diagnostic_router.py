"""Router pour les endpoints de diagnostic."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from pathlib import Path

from ...core.rag_engine import RAGEngine
from ...diagnostics.pdf_analyzer import PDFAnalyzer
from ...diagnostics.search_analyzer import SearchAnalyzer
from ...diagnostics.response_analyzer import ResponseAnalyzer
from ...dependencies import get_rag_engine
from ...core.models import DiagnosticRequest

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])

@router.post("/pdf")
async def analyze_pdf(
    request: DiagnosticRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine)
) -> Dict[str, Any]:
    """Analyse un fichier PDF."""
    try:
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Fichier non trouvé")

        analyzer = PDFAnalyzer(rag_engine.pdf_processor)
        
        # Analyser les sections et les chunks
        section_stats = await analyzer.analyze_sections(file_path)
        chunk_stats = await analyzer.analyze_chunk_distribution(file_path)
        
        return {
            "file": str(file_path),
            "section_analysis": section_stats,
            "chunk_analysis": chunk_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def analyze_search(
    request: DiagnosticRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine)
) -> Dict[str, Any]:
    """Analyse une recherche."""
    try:
        if not request.query:
            raise HTTPException(status_code=400, detail="Query requise")
            
        analyzer = SearchAnalyzer(rag_engine.vector_store, rag_engine)
        
        # Analyser la recherche et les patterns
        search_stats = await analyzer.analyze_search_results(request.query)
        pattern_stats = await analyzer.analyze_query_patterns(request.query)
        
        return {
            "query": request.query,
            "search_analysis": search_stats,
            "pattern_analysis": pattern_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/response")
async def analyze_response(
    request: DiagnosticRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine)
) -> Dict[str, Any]:
    """Analyse une réponse générée."""
    try:
        if not request.response:
            raise HTTPException(status_code=400, detail="Response requise")
            
        analyzer = ResponseAnalyzer(rag_engine.llm_interface)
        
        # Analyser la structure et le contenu
        structure_stats = analyzer.analyze_response_structure(request.response)
        technical_stats = analyzer.analyze_technical_content(request.response)
        source_stats = analyzer.analyze_source_usage(request.response)
        
        return {
            "structure_analysis": structure_stats,
            "technical_analysis": technical_stats,
            "source_analysis": source_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/full")
async def full_diagnostic(
    request: DiagnosticRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine)
) -> Dict[str, Any]:
    """Effectue un diagnostic complet."""
    try:
        results = {}
        
        # Analyse du PDF si spécifié
        if request.file_path:
            file_path = Path(request.file_path)
            if file_path.exists():
                pdf_analyzer = PDFAnalyzer(rag_engine.pdf_processor)
                results["pdf_analysis"] = {
                    "section_stats": await pdf_analyzer.analyze_sections(file_path),
                    "chunk_stats": await pdf_analyzer.analyze_chunk_distribution(file_path)
                }
        
        # Analyse de la recherche si query spécifiée
        if request.query:
            search_analyzer = SearchAnalyzer(rag_engine.vector_store, rag_engine)
            results["search_analysis"] = {
                "search_stats": await search_analyzer.analyze_search_results(request.query),
                "pattern_stats": await search_analyzer.analyze_query_patterns(request.query)
            }
        
        # Analyse de la réponse si spécifiée
        if request.response:
            response_analyzer = ResponseAnalyzer(rag_engine.llm_interface)
            results["response_analysis"] = {
                "structure_stats": response_analyzer.analyze_response_structure(request.response),
                "technical_stats": response_analyzer.analyze_technical_content(request.response),
                "source_stats": response_analyzer.analyze_source_usage(request.response)
            }
        
        if not results:
            raise HTTPException(
                status_code=400,
                detail="Au moins un paramètre (file_path, query, ou response) doit être spécifié"
            )
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
