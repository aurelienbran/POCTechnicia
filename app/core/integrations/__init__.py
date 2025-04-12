"""
Intégrations entre les différents composants du système Technicia

Ce package contient les modules d'intégration entre les différents
composants de l'application, permettant leur interaction cohérente.

Principales intégrations:
- OCR-RAG: Permet l'indexation automatique des documents OCR dans le système RAG
- Document Processing-OCR: Coordination du traitement des documents avec OCR

Auteur: Équipe Technicia
Date: Avril 2025
"""

# Pour faciliter l'importation directe
from app.core.integrations.ocr_rag_integration import (
    index_ocr_document,
    register_ocr_rag_integration,
    unregister_ocr_rag_integration
)
