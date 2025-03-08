from enum import Enum
import logging
from anthropic import Anthropic
from app.config import settings
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class QuestionType(Enum):
    SIMPLE = 1      # salutations, présentations, remerciements
    TECHNIQUE = 2  # questions spécifiques au projet

class MinimalAnthropicClient:
    def __init__(self, api_key):
        self.api_key = api_key
        import httpx
        # Création d'un client HTTP sans les options problématiques
        self.http = httpx.Client(timeout=60.0)
        
    def messages_create(self, model, messages, max_tokens=1000, temperature=0, system=None):
        """Version minimale de l'API de messages avec support pour system prompt."""
        import json
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Construire le corps de la requête
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Ajouter le system prompt s'il est fourni
        if system:
            data["system"] = system
            
        # Envoyer la requête à l'API
        response = self.http.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            logger.error(f"Erreur API Anthropic: {response.status_code} - {response.text}")
            raise Exception(f"Erreur API Anthropic: {response.status_code}")
            
        return response.json()

class QuestionClassifier:
    def __init__(self):
        """Initialise le classificateur avec le client Anthropic."""
        # Utiliser notre client minimaliste au lieu du SDK officiel
        self.client = MinimalAnthropicClient(settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-sonnet-20240229"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def classify(self, question: str) -> QuestionType:
        """Classifie une question comme SIMPLE ou TECHNIQUE."""
        try:
            # Vérifier que la question n'est pas vide
            if not question or not question.strip():
                logger.warning("Question vide reçue, classifiée comme SIMPLE par défaut")
                return QuestionType.SIMPLE

            # Construire le prompt
            prompt = f"""Détermine si cette question est SIMPLE ou TECHNIQUE.

SIMPLE = Une des catégories suivantes :
- Salutations (bonjour, au revoir, etc.)
- Présentations (qui es-tu, que fais-tu, etc.)
- Remerciements
- Questions générales sur ton rôle

TECHNIQUE = Une des catégories suivantes :
- Questions sur la documentation technique
- Questions sur le code ou l'implémentation
- Questions sur l'architecture ou le design
- Questions nécessitant des informations spécifiques du contexte

Question : {question}

Réponds uniquement par un mot : SIMPLE ou TECHNIQUE"""

            # Appeler Claude avec notre client personnalisé
            response = await asyncio.to_thread(
                self.client.messages_create,
                model=self.model,
                max_tokens=10,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extraire et valider la réponse - format personnalisé
            answer = response["content"][0]["text"].strip().upper()
            if answer not in ["SIMPLE", "TECHNIQUE"]:
                logger.warning(f"Réponse inattendue de Claude: {answer}, utilisation de TECHNIQUE par défaut")
                return QuestionType.TECHNIQUE
                
            # Mapper la réponse au type
            return QuestionType.SIMPLE if answer == "SIMPLE" else QuestionType.TECHNIQUE

        except Exception as e:
            logger.error(f"Erreur lors de la classification: {str(e)}")
            # En cas d'erreur, considérer comme TECHNIQUE par sécurité
            return QuestionType.TECHNIQUE
