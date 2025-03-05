"""Middleware de proxy inverse pour FastAPI."""
import httpx
from fastapi import Request
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
import logging
import sys
from starlette.types import ASGIApp, Receive, Scope, Send

# Configurer le logging pour afficher les messages dans la console
logger = logging.getLogger(__name__)
# Vérifier si le logger a déjà des handlers pour éviter les doublons
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # Désactiver la propagation pour éviter les logs en double
    logger.propagate = False

class ReverseProxyMiddleware:
    """
    Middleware de proxy inverse pour FastAPI.
    Permet de rediriger certaines routes vers un autre serveur.
    """
    
    def __init__(self, app: ASGIApp, target_url: str, prefix_path: str):
        """
        Initialise le middleware.
        
        Args:
            app: L'application ASGI
            target_url: URL du serveur cible (ex: http://localhost:3001)
            prefix_path: Préfixe de chemin à rediriger (ex: /new)
        """
        self.app = app
        self.target_url = target_url.rstrip('/')
        self.prefix_path = prefix_path
        self.client = httpx.AsyncClient()
        logger.info(f"ReverseProxyMiddleware initialisé avec target_url={target_url}, prefix_path={prefix_path}")
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """
        Traite la requête.
        
        Si le chemin commence par le préfixe, redirige vers le serveur cible.
        Sinon, passe la requête au middleware suivant.
        """
        # Un seul log pour le type de scope
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
            
        path = scope["path"]
        
        # Si le chemin ne commence pas par le préfixe, passe au middleware suivant
        if not path.startswith(self.prefix_path):
            # Un seul log au lieu de trois logs séparés
            logger.debug(f"Path {path} does not start with {self.prefix_path}, skipping proxy")
            return await self.app(scope, receive, send)
        
        # Construire l'URL cible
        # Supprimer le préfixe du chemin pour obtenir le chemin relatif
        relative_path = path[len(self.prefix_path):] if path != self.prefix_path else "/"
        target_url = f"{self.target_url}{relative_path}"
        
        # Ajouter les paramètres de requête s'il y en a
        query_string = scope.get("query_string", b"").decode("latin1")
        if query_string:
            target_url = f"{target_url}?{query_string}"
        
        logger.info(f"Proxying request: {path} -> {target_url}")
        
        # Récupérer les headers de la requête
        headers = dict([(k.decode('latin1'), v.decode('latin1')) for k, v in scope["headers"]])
        # Un seul log pour les headers
        logger.debug(f"Request headers: {headers}")
        
        # Mettre à jour l'hôte
        headers["host"] = self.target_url.split("://")[1]
        
        # Récupérer le corps de la requête
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            # Un seul log pour le message reçu
            logger.debug(f"Message reçu du client: {message.get('type')}")
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
        
        # Un seul log pour la méthode de requête
        logger.debug(f"Request method: {scope['method']}")
        
        try:
            # Envoyer la requête au serveur cible
            logger.debug(f"Sending request to {target_url}")
            response = await self.client.request(
                method=scope["method"],
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=True
            )
            
            # Un seul log pour le statut de la réponse
            logger.debug(f"Response status: {response.status_code}")
            # Un seul log pour les headers de la réponse
            logger.debug(f"Response headers: {response.headers}")
            # Un seul log pour l'aperçu du contenu de la réponse
            logger.debug(f"Response content preview: {response.content[:100] if response.content else 'No content'}")
            
            # Envoyer la réponse au client
            logger.debug("Envoi de la réponse au client (http.response.start)")
            await send({
                "type": "http.response.start",
                "status": response.status_code,
                "headers": [(k.encode('latin1'), v.encode('latin1')) for k, v in response.headers.items()]
            })
            
            # Envoyer le corps de la réponse
            logger.debug("Envoi du corps de la réponse au client (http.response.body)")
            await send({
                "type": "http.response.body",
                "body": response.content
            })
            
            # Fermer la réponse
            await response.aclose()
            logger.info(f"Proxy request completed: {path} -> {target_url} ({response.status_code})")
            
        except Exception as e:
            logger.error(f"Error proxying request: {e}", exc_info=True)
            return await self.app(scope, receive, send)
