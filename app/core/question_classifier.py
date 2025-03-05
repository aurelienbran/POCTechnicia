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

class QuestionClassifier:
    def __init__(self):
        """Initialise le classificateur avec le client Anthropic."""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
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

            # Appeler Claude
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=10,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extraire et valider la réponse
            answer = response.content[0].text.strip().upper()
            if answer not in ["SIMPLE", "TECHNIQUE"]:
                logger.warning(f"Réponse inattendue de Claude: {answer}, utilisation de TECHNIQUE par défaut")
                return QuestionType.TECHNIQUE
                
            # Mapper la réponse au type
            return QuestionType.SIMPLE if answer == "SIMPLE" else QuestionType.TECHNIQUE

        except Exception as e:
            logger.error(f"Erreur lors de la classification: {str(e)}")
            # En cas d'erreur, considérer comme TECHNIQUE par sécurité
            return QuestionType.TECHNIQUE
