"""Module d'analyse des PDF et de leur traitement."""
from pathlib import Path
from typing import Dict, List, Any
import logging
from ..core.pdf_processor import PDFProcessor
from ..core.vector_store import VectorStore

logger = logging.getLogger(__name__)

class PDFAnalyzer:
    """Classe pour analyser le traitement des PDF."""
    
    def __init__(self, pdf_processor: PDFProcessor = None):
        """Initialise l'analyseur avec un processeur PDF."""
        self.pdf_processor = pdf_processor or PDFProcessor()
        
    async def analyze_sections(self, file_path: Path) -> Dict[str, Any]:
        """Analyse les sections d'un PDF."""
        sections = {}
        section_stats = {
            "total_sections": 0,
            "sections_with_content": 0,
            "avg_section_length": 0,
            "sections_details": []
        }
        
        try:
            async for chunk in self.pdf_processor.process_pdf(file_path):
                section = chunk.get("section", "")
                if section:
                    if section not in sections:
                        sections[section] = {
                            "content": [],
                            "page_range": [chunk["page"], chunk["page"]],
                            "total_tokens": 0
                        }
                    
                    sections[section]["content"].append(chunk["content"])
                    sections[section]["total_tokens"] += chunk["tokens"]
                    sections[section]["page_range"][1] = chunk["page"]
            
            # Calculer les statistiques
            section_stats["total_sections"] = len(sections)
            section_stats["sections_with_content"] = len([s for s in sections.values() if s["content"]])
            
            total_tokens = sum(s["total_tokens"] for s in sections.values())
            if sections:
                section_stats["avg_section_length"] = total_tokens / len(sections)
            
            # Détails des sections
            for section_id, data in sections.items():
                section_stats["sections_details"].append({
                    "section_id": section_id,
                    "page_range": f"{data['page_range'][0]}-{data['page_range'][1]}",
                    "total_tokens": data["total_tokens"],
                    "content_samples": data["content"][:2]  # Premiers chunks pour exemple
                })
            
            return section_stats
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des sections: {str(e)}")
            raise

    async def analyze_chunk_distribution(self, file_path: Path) -> Dict[str, Any]:
        """Analyse la distribution des chunks."""
        chunk_stats = {
            "total_chunks": 0,
            "avg_chunk_size": 0,
            "size_distribution": {},
            "page_distribution": {},
            "potential_issues": []
        }
        
        try:
            total_tokens = 0
            async for chunk in self.pdf_processor.process_pdf(file_path):
                chunk_stats["total_chunks"] += 1
                total_tokens += chunk["tokens"]
                
                # Distribution par taille
                size_range = f"{(chunk['tokens'] // 100) * 100}-{((chunk['tokens'] // 100) + 1) * 100}"
                chunk_stats["size_distribution"][size_range] = chunk_stats["size_distribution"].get(size_range, 0) + 1
                
                # Distribution par page
                page = str(chunk["page"])
                chunk_stats["page_distribution"][page] = chunk_stats["page_distribution"].get(page, 0) + 1
                
                # Détecter les problèmes potentiels
                if chunk["tokens"] < 50:
                    chunk_stats["potential_issues"].append({
                        "type": "small_chunk",
                        "page": chunk["page"],
                        "tokens": chunk["tokens"],
                        "content": chunk["content"][:100]
                    })
                elif chunk["tokens"] > self.pdf_processor.chunk_size * 0.9:
                    chunk_stats["potential_issues"].append({
                        "type": "large_chunk",
                        "page": chunk["page"],
                        "tokens": chunk["tokens"],
                        "content": chunk["content"][:100]
                    })
            
            if chunk_stats["total_chunks"] > 0:
                chunk_stats["avg_chunk_size"] = total_tokens / chunk_stats["total_chunks"]
            
            return chunk_stats
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des chunks: {str(e)}")
            raise
