from typing import List, Dict, Any, Optional
import os
from app.config import settings
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Démarrage de l'initialisation de LLMInterface")
logger.info(f"VOYAGE_API_KEY dans settings: {settings.VOYAGE_API_KEY[:10]}...")

# Initialiser Voyage AI avant d'importer le client
os.environ["VOYAGE_API_KEY"] = settings.VOYAGE_API_KEY
logger.info(f"VOYAGE_API_KEY dans os.environ: {os.environ.get('VOYAGE_API_KEY', 'Non définie')[:10]}...")

try:
    import voyageai
    logger.info("Module voyageai importé avec succès")
except Exception as e:
    logger.error(f"Erreur lors de l'import de voyageai: {str(e)}")
    raise

import anthropic
import json
from tenacity import retry, stop_after_attempt, wait_exponential
import numpy as np
import asyncio

logger.info("Module anthropic importé avec succès")
logger.info("Module json importé avec succès")
logger.info("Module tenacity importé avec succès")
logger.info("Module numpy importé avec succès")
logger.info("Module asyncio importé avec succès")

class LLMInterface:
    def __init__(self):
        """Initialise la connexion avec Claude et Voyage."""
        logger.info("Initialisation de LLMInterface")
        self._initialized = False
        self._voyage_initialized = False
        
        try:
            # Initialiser Anthropic (Claude)
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = "claude-3-sonnet-20240229"
            self.system_prompt = """Tu es un assistant technique expert qui aide à répondre aux questions
            en te basant sur la documentation technique fournie. Utilise uniquement les informations
            présentes dans le contexte fourni pour répondre. Si tu ne trouves pas l'information dans
            le contexte, dis-le clairement. Sois précis et concis dans tes réponses."""
            
            # Initialiser Voyage AI
            if not settings.VOYAGE_API_KEY:
                raise ValueError("VOYAGE_API_KEY non définie")
                
            os.environ["VOYAGE_API_KEY"] = settings.VOYAGE_API_KEY
            self.voyage_client = voyageai.Client()
            self.voyage_model = "voyage-2"  # Utiliser voyage-2 qui a une limite de 4000 tokens
            
            # Tester la connexion avec un retry
            max_retries = 3
            retry_delay = 1
            
            for attempt in range(max_retries):
                try:
                    test_text = "Test de connexion"
                    response = self.voyage_client.embed(test_text, model=self.voyage_model)
                    test_embedding = response.embeddings[0]  # Accéder à la propriété embeddings
                    
                    if not isinstance(test_embedding, list) or len(test_embedding) != 1024:
                        raise ValueError(f"Embedding invalide: attendu 1024 dimensions, reçu {len(test_embedding) if isinstance(test_embedding, list) else 'non-liste'}")
                        
                    self._voyage_initialized = True
                    logger.info("Voyage AI initialisé avec succès")
                    break
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Tentative {attempt + 1} échouée: {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Backoff exponentiel
                    else:
                        raise ValueError(f"Échec de l'initialisation de Voyage AI après {max_retries} tentatives: {str(e)}")
            
            self._initialized = True
            logger.info("LLMInterface initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur critique lors de l'initialisation de LLMInterface: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Génère une réponse à la question en utilisant le contexte fourni.
        
        Args:
            query: La question de l'utilisateur
            context_docs: Liste de documents pertinents avec leurs scores
            max_tokens: Nombre maximum de tokens pour la réponse
            temperature: Contrôle la créativité de la réponse (0.0 = déterministe, 1.0 = créatif)
        
        Returns:
            str: La réponse générée
        """
        try:
            logger.info(f"Génération de réponse pour la question: {query}")
            # Préparer le contexte
            formatted_context = []
            for doc in context_docs:
                text = doc.get("text", "")
                score = doc.get("score", 0)
                if score >= 0.5:  # Seuil abaissé pour être plus permissif
                    formatted_context.append(f"[Score: {score:.2f}] {text}")

            if not formatted_context:
                return "Je n'ai pas trouvé de documents pertinents pour répondre à votre question. Veuillez reformuler ou poser une autre question."

            context_text = "\n\n".join(formatted_context)
            
            # Construire le prompt
            user_content = f"""Contexte :
            {context_text}
            
            Question : {query}
            
            Réponds à la question en te basant uniquement sur le contexte fourni."""

            # Appeler Claude avec le nouveau format
            message = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_content
                    }
                ]
            )

            # Extraire le texte du ContentBlock
            response_text = message.content[0].text if message.content else ""
            logger.info(f"Réponse générée avec succès: {response_text}")
            return response_text

        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_follow_up_questions(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
        previous_response: str,
        num_questions: int = 3
    ) -> List[str]:
        """
        Génère des questions de suivi pertinentes basées sur le contexte et la réponse précédente.
        
        Args:
            query: La question originale de l'utilisateur
            context_docs: Liste de documents pertinents avec leurs scores
            previous_response: La réponse précédente générée
            num_questions: Nombre de questions de suivi à générer
        
        Returns:
            List[str]: Liste des questions de suivi générées
        """
        try:
            logger.info(f"Génération de questions de suivi pour la question: {query}")
            # Préparer le contexte
            formatted_context = []
            for doc in context_docs:
                text = doc.get("text", "")
                score = doc.get("score", 0)
                if score >= 0.5:  # Seuil abaissé pour être plus permissif
                    formatted_context.append(f"[Score: {score:.2f}] {text}")

            if not formatted_context:
                return "Je n'ai pas trouvé de documents pertinents pour répondre à votre question. Veuillez reformuler ou poser une autre question."

            context_text = "\n\n".join(formatted_context)
            
            # Construire le prompt pour les questions de suivi
            user_content = f"""Contexte :
            {context_text}
            
            Question initiale : {query}
            
            Réponse précédente : {previous_response}
            
            Génère {num_questions} questions de suivi pertinentes basées sur le contexte et la réponse. Retourne une question par ligne."""

            # Appeler Claude avec le nouveau format
            message = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_content
                    }
                ]
            )

            # Extraire et formater les questions
            response_text = message.content[0].text if message.content else ""
            questions = [q.strip() for q in response_text.split("\n") if q.strip()]
            logger.info(f"Questions de suivi générées avec succès: {questions[:num_questions]}")
            return questions[:num_questions]

        except Exception as e:
            logger.error(f"Erreur lors de la génération des questions de suivi: {str(e)}")
            raise

    async def summarize_document(
        self,
        document_text: str,
        max_length: int = 1000
    ) -> str:
        """
        Génère un résumé concis d'un document.
        
        Args:
            document_text: Le texte du document à résumer
            max_length: Longueur maximale du résumé en tokens
        
        Returns:
            str: Le résumé généré
        """
        try:
            logger.info(f"Génération de résumé pour le document: {document_text[:100]}...")
            
            # Construire le prompt
            user_content = f"""Document à résumer :
            {document_text}
            
            Génère un résumé concis et informatif de ce document."""

            # Appeler Claude avec le nouveau format
            message = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=max_length,
                temperature=0.7,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_content
                    }
                ]
            )

            # Extraire le texte du ContentBlock
            summary = message.content[0].text if message.content else ""
            logger.info(f"Résumé généré avec succès: {summary[:100]}...")
            return summary

        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Génère un embedding pour le texte donné.
        Utilise un retry pattern pour la résilience.
        
        Args:
            text: Texte à encoder
            
        Returns:
            np.ndarray: Vecteur d'embedding ou None si erreur
        """
        if not self._voyage_initialized:
            logger.error("Voyage AI n'est pas initialisé")
            return None
            
        try:
            # Limiter la taille du texte si nécessaire
            max_text_length = 8192
            if len(text) > max_text_length:
                logger.warning(f"Texte tronqué de {len(text)} à {max_text_length} caractères")
                text = text[:max_text_length]
            
            # Générer l'embedding avec timeout
            async with asyncio.timeout(30):  # 30 secondes timeout
                response = await asyncio.to_thread(
                    self.voyage_client.embed,
                    text,
                    model=self.voyage_model
                )
                test_embedding = response.embeddings[0]  # Accéder à la propriété embeddings
                
                if not isinstance(test_embedding, list):
                    logger.error(f"Format d'embedding invalide: {type(test_embedding)}")
                    return None
                    
                return np.array(test_embedding)
                
        except asyncio.TimeoutError:
            logger.error("Timeout lors de la génération de l'embedding")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'embedding: {str(e)}")
            return None

    async def get_embeddings(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        """Génère des embeddings pour une liste de textes."""
        if not self._voyage_initialized:
            raise RuntimeError("Voyage AI n'est pas initialisé")
            
        try:
            response = self.voyage_client.embed(texts, model=self.voyage_model)
            if not response or not hasattr(response, 'embeddings'):
                raise ValueError("Réponse invalide de Voyage AI")
                
            embeddings = response.embeddings
            if not embeddings or not isinstance(embeddings, list):
                raise ValueError("Échec de la génération des embeddings")
                
            return [np.array(emb) for emb in embeddings]
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des embeddings: {str(e)}")
            raise
