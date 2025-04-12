"""Point d'entrée de l'application."""
from fastapi import FastAPI, Request
from datetime import datetime
import time
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from app.api.v1.router import router as api_router
from app.api.websocket.ocr_socket import router as ws_router
from app.api.router import router as dashboard_api_router
from app.schemas import ErrorResponse
from app.config import settings
from qdrant_client import QdrantClient
from app.core.llm_interface import LLMInterface
from app.core.vector_store import VectorStore
from app.core.rag_engine import RAGEngine
from app.core.proxy_middleware import ReverseProxyMiddleware
from app.api.register_routes import register_routes

# Configuration du logging pour réduire les messages watchfiles
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG API",
    description="API pour le système de Retrieval Augmented Generation",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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

# Inclusion des routeurs dans l'ordre correct (WebSocket d'abord)
app.include_router(ws_router, tags=["websocket"])
app.include_router(api_router, prefix="/api/v1", tags=["api"])
app.include_router(dashboard_api_router, prefix="/api", tags=["dashboard"])

# Enregistrement des routes de l'API de traitement de documents
register_routes(app)

# État global de l'application
app.state.startup_complete = False
app.state.startup_error = None
app.state.llm_interface = None
app.state.vector_store = None
app.state.rag_engine = None

# Ajouter le middleware de proxy pour le nouveau frontend
# Ce middleware redirigera les requêtes /new/* vers le frontend React sur le port 3001
app.add_middleware(
    ReverseProxyMiddleware,
    target_url="http://localhost:3001",
    prefix_path="/new",
)

async def get_llm_interface():
    """Dépendance pour obtenir l'instance LLMInterface."""
    if not app.state.llm_interface:
        app.state.llm_interface = LLMInterface()
        logger.info("LLMInterface créé et stocké dans l'état de l'application")
    return app.state.llm_interface

async def get_vector_store():
    """Dépendance pour obtenir l'instance VectorStore."""
    if not app.state.vector_store:
        llm_interface = await get_llm_interface()
        app.state.vector_store = VectorStore(llm_interface=llm_interface)
        await app.state.vector_store.ensure_initialized()
        logger.info("VectorStore créé et stocké dans l'état de l'application")
    return app.state.vector_store

async def get_rag_engine():
    """Dépendance pour obtenir l'instance RAGEngine."""
    if not app.state.rag_engine:
        vector_store = await get_vector_store()
        llm_interface = await get_llm_interface()
        app.state.rag_engine = RAGEngine(
            vector_store=vector_store,
            llm_interface=llm_interface
        )
        await app.state.rag_engine.initialize()
        logger.info("RAGEngine créé et stocké dans l'état de l'application")
    return app.state.rag_engine

@app.on_event("startup")
async def startup_event():
    """Initialisation de l'application."""
    try:
        # Initialiser les composants une seule fois au démarrage
        await get_rag_engine()  # Cela initialisera aussi LLMInterface et VectorStore
        
        # Initialiser l'intégration OCR-RAG
        from app.core.integrations import register_ocr_rag_integration
        await register_ocr_rag_integration()
        logger.info("Intégration OCR-RAG initialisée avec succès")
        
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
    """Redirige vers le nouveau frontend React."""
    return RedirectResponse(url="/new")

# Route pour basculer entre les frontends
@app.get("/switch")
async def switch_frontend(request: Request, target: str = "new"):
    """
    Redirige vers le frontend spécifié.
    
    Args:
        target: Le frontend cible ('new' ou 'original')
    """
    if target == "original":
        # Conserver le code de redirection vers l'ancien frontend, mais ajouter un log
        logger.warning("Tentative d'accès à l'ancien frontend. Redirection vers le nouveau frontend.")
        return RedirectResponse(url="/new")
    else:
        # Rediriger vers le nouveau frontend React
        return RedirectResponse(url="/new")

@app.get("/new")
@app.get("/new/{path:path}")
async def new_frontend(request: Request, path: str = ""):
    """
    Point d'entrée pour le nouveau frontend React.
    Cette route est nécessaire pour que FastAPI puisse traiter les requêtes pour /new
    avant que le middleware de proxy ne les intercepte.
    """
    # Cette route ne sera jamais réellement appelée car le middleware interceptera la requête avant,
    # mais elle est nécessaire pour que FastAPI enregistre le chemin
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
