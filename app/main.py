"""Point d'entrée de l'application."""
from fastapi import FastAPI, Request
from datetime import datetime
import time
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from app.api.v1.router import router as api_router
from app.schemas import ErrorResponse
from app.config import settings
from qdrant_client import QdrantClient
from app.core.llm_interface import LLMInterface
from app.core.vector_store import VectorStore
from app.core.rag_engine import RAGEngine

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG API",
    description="API pour le système de Retrieval Augmented Generation",
    version="1.0.0"
)

# Configuration de la taille maximale des fichiers
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > settings.MAX_UPLOAD_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Fichier trop volumineux. Maximum autorisé: {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"}
                )
        return await call_next(request)

app.add_middleware(MaxBodySizeMiddleware)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les origines exactes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware pour le logging et le temps de traitement
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Gestionnaire d'erreurs global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).model_dump()
    )

# Configuration des templates et fichiers statiques
templates_path = Path("app/templates")
if not templates_path.exists():
    templates_path.mkdir(parents=True)
templates = Jinja2Templates(directory=str(templates_path))

static_path = Path("app/static")
if not static_path.exists():
    static_path.mkdir(parents=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Inclusion du routeur API
app.include_router(api_router, prefix="/api/v1", tags=["api"])

# État global de l'application
app.state.startup_complete = False
app.state.startup_error = None

@app.on_event("startup")
async def startup_event():
    """Initialisation de l'application."""
    try:
        # Initialiser l'interface LLM
        llm_interface = LLMInterface()
        
        # Initialiser le VectorStore
        vector_store = VectorStore(llm_interface=llm_interface)
        await vector_store.ensure_initialized()
        
        # Initialiser le RAG Engine
        rag_engine = RAGEngine(vector_store=vector_store, llm_interface=llm_interface)
        await rag_engine.initialize()
        
        # Stocker les instances dans l'état de l'application
        app.state.rag_engine = rag_engine
        app.state.vector_store = vector_store
        app.state.startup_complete = True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'application: {str(e)}")
        app.state.startup_error = str(e)
        raise e

# Route de santé
@app.get("/health")
async def health_check():
    """Vérifie l'état du système et de ses composants."""
    if not getattr(app.state, "startup_complete", False):
        return JSONResponse(
            status_code=503,
            content={
                "status": "initializing",
                "detail": getattr(app.state, "startup_error", "Système en cours d'initialisation"),
                "timestamp": datetime.now().isoformat()
            }
        )

    try:
        # Vérifier la connexion à Qdrant
        try:
            collection_info = await app.state.vector_store.get_collection_info()
            if not collection_info:
                raise Exception("Impossible d'accéder à la collection Qdrant")
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "detail": f"Erreur Qdrant: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": app.version,
            "components": {
                "rag_engine": "initialized",
                "vector_store": "connected",
                "qdrant": "connected"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "detail": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# Route principale
@app.get("/")
async def root(request: Request):
    """Page d'accueil."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
