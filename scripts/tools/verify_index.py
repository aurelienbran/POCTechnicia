"""Script de vérification de l'état de l'index et de la qualité de l'indexation."""
import os
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance
import logging
import json
from datetime import datetime
import pandas as pd
from typing import Dict, List
import numpy as np
import tiktoken

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IndexVerifier:
    def __init__(self, host="localhost", port=6333):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "documents"
        self.encoding = tiktoken.get_encoding("cl100k_base")  # Encodage utilisé par Claude
        
    def check_qdrant_config(self) -> Dict:
        """Vérifie la configuration de Qdrant selon nos spécifications."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            config = collection_info.config
            
            # Vérification de la configuration
            checks = {
                "vector_size": {
                    "status": config.params.vectors.size == 1024,
                    "value": config.params.vectors.size,
                    "expected": 1024
                },
                "distance": {
                    "status": config.params.vectors.distance == Distance.COSINE,
                    "value": str(config.params.vectors.distance),
                    "expected": "Cosine"
                },
                "segments": {
                    "status": config.optimizer_config.default_segment_number >= 2,
                    "value": config.optimizer_config.default_segment_number,
                    "expected": "≥ 2"
                }
            }
            
            # Logging des résultats
            logger.info("\n=== Configuration Qdrant ===")
            for key, check in checks.items():
                status = "✅" if check["status"] else "❌"
                logger.info(f"{status} {key}: {check['value']} (attendu: {check['expected']})")
            
            return {
                "checks": checks,
                "status": all(check["status"] for check in checks.values()),
                "collection_info": collection_info.dict()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la configuration: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def analyze_chunks(self) -> Dict:
        """Analyse la qualité des chunks selon nos spécifications."""
        try:
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=True
            )
            points = scroll_result[0]
            
            chunk_analysis = []
            for point in points:
                text = point.payload.get("text", "")
                tokens = len(self.encoding.encode(text))
                
                # Analyse du chunk
                chunk_info = {
                    "id": point.id,
                    "tokens": tokens,
                    "in_target_range": 500 <= tokens <= 1000,
                    "metadata_complete": all(
                        field in point.payload 
                        for field in ["text", "page", "position", "source"]
                    ),
                    "has_section": "section" in point.payload,
                    "vector_norm": np.linalg.norm(point.vector)
                }
                chunk_analysis.append(chunk_info)
            
            # Statistiques globales
            stats = {
                "total_chunks": len(chunk_analysis),
                "tokens": {
                    "min": min(c["tokens"] for c in chunk_analysis),
                    "max": max(c["tokens"] for c in chunk_analysis),
                    "avg": sum(c["tokens"] for c in chunk_analysis) / len(chunk_analysis)
                },
                "chunks_in_range": sum(1 for c in chunk_analysis if c["in_target_range"]),
                "metadata_complete": sum(1 for c in chunk_analysis if c["metadata_complete"]),
                "has_section": sum(1 for c in chunk_analysis if c["has_section"]),
                "vector_norms": {
                    "min": min(c["vector_norm"] for c in chunk_analysis),
                    "max": max(c["vector_norm"] for c in chunk_analysis),
                    "avg": sum(c["vector_norm"] for c in chunk_analysis) / len(chunk_analysis)
                }
            }
            
            # Calcul des pourcentages
            stats["percent_in_range"] = (stats["chunks_in_range"] / stats["total_chunks"]) * 100
            stats["percent_metadata_complete"] = (stats["metadata_complete"] / stats["total_chunks"]) * 100
            stats["percent_has_section"] = (stats["has_section"] / stats["total_chunks"]) * 100
            
            # Logging des résultats
            logger.info("\n=== Analyse des Chunks ===")
            logger.info(f"Nombre total de chunks: {stats['total_chunks']}")
            logger.info(f"Tokens par chunk:")
            logger.info(f"- Min: {stats['tokens']['min']}")
            logger.info(f"- Max: {stats['tokens']['max']}")
            logger.info(f"- Moyenne: {stats['tokens']['avg']:.1f}")
            logger.info(f"Chunks dans la plage cible (500-1000): {stats['percent_in_range']:.1f}%")
            logger.info(f"Métadonnées complètes: {stats['percent_metadata_complete']:.1f}%")
            logger.info(f"Avec section/titre: {stats['percent_has_section']:.1f}%")
            
            return {
                "stats": stats,
                "chunk_analysis": chunk_analysis
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des chunks: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def verify_document_coverage(self, document_path: str) -> Dict:
        """Vérifie la couverture et la qualité de l'indexation d'un document."""
        try:
            filename = os.path.basename(document_path)
            
            # Rechercher tous les chunks pour ce document
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=True,
                filter={
                    "must": [
                        {
                            "key": "source",
                            "match": {
                                "value": filename
                            }
                        }
                    ]
                }
            )
            chunks = scroll_result[0]
            
            # Analyse détaillée
            pages_covered = set()
            tokens_by_page = {}
            overlap_analysis = []
            
            for i, chunk in enumerate(chunks):
                page = chunk.payload.get("page")
                text = chunk.payload.get("text", "")
                tokens = len(self.encoding.encode(text))
                
                if page is not None:
                    pages_covered.add(page)
                    tokens_by_page[page] = tokens_by_page.get(page, 0) + tokens
                
                # Analyse du chevauchement avec le chunk suivant
                if i < len(chunks) - 1:
                    next_chunk = chunks[i + 1]
                    if page == next_chunk.payload.get("page"):
                        text1 = set(text.split())
                        text2 = set(next_chunk.payload.get("text", "").split())
                        overlap = len(text1.intersection(text2))
                        overlap_analysis.append(overlap)
            
            verification = {
                "document": filename,
                "chunks_count": len(chunks),
                "pages": {
                    "covered": sorted(list(pages_covered)),
                    "total_covered": len(pages_covered)
                },
                "tokens": {
                    "by_page": tokens_by_page,
                    "total": sum(tokens_by_page.values())
                },
                "overlap": {
                    "avg": sum(overlap_analysis) / len(overlap_analysis) if overlap_analysis else 0,
                    "min": min(overlap_analysis) if overlap_analysis else 0,
                    "max": max(overlap_analysis) if overlap_analysis else 0
                }
            }
            
            # Logging des résultats
            logger.info(f"\n=== Vérification du document: {filename} ===")
            logger.info(f"Chunks indexés: {verification['chunks_count']}")
            logger.info(f"Pages couvertes: {verification['pages']['total_covered']}")
            logger.info(f"Tokens totaux: {verification['tokens']['total']}")
            logger.info(f"Chevauchement moyen: {verification['overlap']['avg']:.1f} mots")
            
            return verification
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du document: {str(e)}")
            return {"status": "error", "error": str(e)}

def main():
    """Fonction principale."""
    verifier = IndexVerifier()
    
    # 1. Vérifier la configuration
    config_check = verifier.check_qdrant_config()
    
    # 2. Analyser les chunks
    chunk_analysis = verifier.analyze_chunks()
    
    # 3. Vérifier les documents de test
    test_files = [
        "tests/performance/test_files/fe.pdf",
        "tests/performance/test_files/el.pdf",
        "tests/performance/test_files/LJ70_RJ70_chassis_body.pdf"
    ]
    
    document_verifications = []
    for file_path in test_files:
        if os.path.exists(file_path):
            verification = verifier.verify_document_coverage(file_path)
            document_verifications.append(verification)
    
    # 4. Générer un rapport
    report = {
        "timestamp": datetime.now().isoformat(),
        "config_check": config_check,
        "chunk_analysis": chunk_analysis,
        "document_verifications": document_verifications
    }
    
    # Sauvegarder le rapport
    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/index_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nRapport sauvegardé dans: {report_path}")

if __name__ == "__main__":
    main()
