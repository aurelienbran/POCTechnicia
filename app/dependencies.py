"""Dépendances pour l'application FastAPI."""
from fastapi import Depends
from typing import AsyncGenerator

from .core.rag_engine import RAGEngine
from .core.pdf_processor import PDFProcessor
from .core.vector_store import VectorStore
from .core.llm_interface import LLMInterface

async def get_vector_store() -> AsyncGenerator[VectorStore, None]:
    """Dépendance pour obtenir une instance de VectorStore."""
    vector_store = VectorStore()
    try:
        yield vector_store
    finally:
        await vector_store.close()

async def get_llm_interface() -> AsyncGenerator[LLMInterface, None]:
    """Dépendance pour obtenir une instance de LLMInterface."""
    llm = LLMInterface()
    try:
        yield llm
    finally:
        await llm.close()

async def get_pdf_processor() -> AsyncGenerator[PDFProcessor, None]:
    """Dépendance pour obtenir une instance de PDFProcessor."""
    processor = PDFProcessor()
    try:
        yield processor
    finally:
        await processor.close()

async def get_rag_engine(
    vector_store: VectorStore = Depends(get_vector_store),
    llm_interface: LLMInterface = Depends(get_llm_interface),
    pdf_processor: PDFProcessor = Depends(get_pdf_processor)
) -> AsyncGenerator[RAGEngine, None]:
    """Dépendance pour obtenir une instance de RAGEngine."""
    engine = RAGEngine(
        vector_store=vector_store,
        llm_interface=llm_interface,
        pdf_processor=pdf_processor
    )
    try:
        yield engine
    finally:
        await engine.close()
