from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

class DocumentMetadata(BaseModel):
    """Métadonnées d'un document."""
    title: str
    page_count: int
    author: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None

class ProcessingStats(BaseModel):
    """Statistiques de traitement d'un document."""
    document: str
    chunks_processed: int
    chunks_indexed: int
    processing_time: float

class Source(BaseModel):
    """Source d'une réponse."""
    file: str
    score: float = Field(..., ge=0.0, le=1.0)

class QueryRequest(BaseModel):
    """Requête de recherche."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="La requête de recherche",
        examples=["Quelles sont les procédures de maintenance ?"]
    )
    k: Optional[int] = Field(
        default=4,
        ge=1,
        le=10,
        description="Nombre de documents à retourner"
    )
    filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filtre optionnel pour la recherche"
    )

    @property
    def get_query(self) -> str:
        """Retourne la requête nettoyée."""
        return self.query.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Quelle est la procédure pour X ?",
                "k": 4,
                "filter": {"type": "document"}
            }
        }

class QueryResponse(BaseModel):
    """Réponse à une question."""
    query: str
    answer: str
    sources: List[Source]
    processing_time: float
    follow_up_questions: Optional[List[str]] = Field(default_factory=list)

class CollectionStats(BaseModel):
    """Statistiques de la collection."""
    name: str
    vectors_count: int
    dimension: int
    distance: str

class DocumentsStatistics(BaseModel):
    """Statistiques détaillées sur les documents indexés."""
    collection_name: str
    documents_count: int
    vectors_count: int
    indexed_vectors_count: int
    indexing_percentage: float
    points_count: int
    avg_vectors_per_document: float
    is_empty: bool
    is_fully_indexed: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ErrorResponse(BaseModel):
    """Réponse d'erreur."""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class IndexingProgressEvent(BaseModel):
    """Événement de progression d'indexation."""
    in_progress: bool
    current_file: Optional[str] = None
    indexed_chunks: Optional[int] = None
    total_chunks: Optional[int] = None
    error: Optional[bool] = None
    error_message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class OCRProgressEvent(BaseModel):
    """Événement de progression OCR."""
    progress: Optional[int] = None  # Pourcentage 0-100
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class OCRResult(BaseModel):
    """Résultat d'une opération OCR sur un document."""
    output_path: Path
    success: bool
    original_path: Path
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
