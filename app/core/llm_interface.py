from typing import List, Dict, Any, Optional
import os
from app.config import settings
import logging
import time
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
from .question_classifier import QuestionClassifier, QuestionType
from app.core.formatters import TechnicalResponseFormatter

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

logger.info("Module anthropic importé avec succès")
logger.info("Module json importé avec succès")

class LLMInterface:
    SYSTEM_PROMPT = """Tu es CFF IA, l'assistant technique officiel des CFF (Chemins de fer fédéraux suisses).

        Pour les questions SIMPLES (salutations, présentations) :
        - Présente-toi comme CFF IA, l'assistant technique des CFF
        - Adopte un ton professionnel mais conversationnel, comme un collègue expert
        - Propose ton aide sur la documentation et les aspects techniques du projet

        Pour les questions TECHNIQUES :
        - Réponds comme un expert ferroviaire s'adressant à un collègue technicien
        - Utilise un langage technique précis mais accessible
        - Intègre naturellement les informations techniques dans une conversation fluide
        - Évite les sections rigides et les formulations trop formelles
        - Organise ta réponse de façon logique mais conversationnelle
        - Présente les informations de manière fluide et naturelle
        - NE CITE JAMAIS les sources dans le corps du texte
        - N'utilise PAS de références comme (Document 1), [1], ou "selon le document X"
        - Présente l'information comme si elle faisait partie de tes connaissances
        - Les sources seront automatiquement ajoutées à la fin de ta réponse
        """
        
    def __init__(self, api_key: Optional[str] = None):
        """Initialise l'interface avec le client Anthropic et Voyage."""
        # Anthropic (Claude)
        # Utiliser le client MinimalAnthropicClient défini dans question_classifier.py
        from .question_classifier import MinimalAnthropicClient
        
        # Utiliser notre client minimaliste au lieu du SDK officiel
        api_key = api_key or settings.ANTHROPIC_API_KEY
        self.client = MinimalAnthropicClient(api_key)
        self.model = "claude-3-sonnet-20240229"
        self.classifier = QuestionClassifier()
        
        # Voyage AI
        self._voyage_initialized = False
        self._voyage_client = None
        self._voyage_model = "voyage-2"
        
        # Initialisation de Voyage AI avec retry
        self._initialize_voyage()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _initialize_voyage(self):
        """Initialise Voyage AI avec retry pattern."""
        try:
            if not settings.VOYAGE_API_KEY:
                logger.error("VOYAGE_API_KEY non définie dans les settings")
                return
                
            os.environ["VOYAGE_API_KEY"] = settings.VOYAGE_API_KEY
            self._voyage_client = voyageai.Client()
            
            # Test de connexion avec retry
            test_text = "Test de connexion"
            response = self._voyage_client.embed(test_text, model=self._voyage_model)
            test_embedding = response.embeddings[0]
            
            if not isinstance(test_embedding, list) or len(test_embedding) != 1024:
                raise ValueError(f"Embedding invalide: attendu 1024 dimensions, reçu {len(test_embedding) if isinstance(test_embedding, list) else 'non-liste'}")
                
            self._voyage_initialized = True
            logger.info("Voyage AI initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Voyage AI: {str(e)}")
            self._voyage_initialized = False
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_embeddings(self, texts: List[str], batch_size: int = 10, max_retries: int = 3, timeout: int = 120) -> List[List[float]]:
        """
        Génère des embeddings pour une liste de textes en traitant par lots.
        
        Args:
            texts: Liste des textes à encoder
            batch_size: Taille de chaque lot (nombre de textes traités par requête)
            max_retries: Nombre maximal de tentatives en cas d'échec
            timeout: Timeout en secondes pour chaque requête API
        
        Returns:
            Liste des embeddings générés
        """
        if not self._voyage_initialized or not self._voyage_client:
            raise RuntimeError("Voyage AI n'est pas initialisé correctement")
        
        if not texts:
            return []
        
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        processed_batches = 0
        
        logger.info(f"Traitement de {len(texts)} textes en {total_batches} lots de maximum {batch_size} textes")
        
        # Diviser les textes en lots
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = processed_batches + 1
            
            # Début du traitement du lot avec mécanisme de retry avancé
            retry_count = 0
            batch_success = False
            current_timeout = timeout
            
            while not batch_success and retry_count < max_retries:
                try:
                    logger.info(f"Traitement du lot {batch_num}/{total_batches} ({len(batch)} textes)")
                    start_time = time.time()
                    
                    # Configuration du timeout
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._voyage_client.embed,
                            batch,
                            model=self._voyage_model
                        ),
                        timeout=current_timeout
                    )
                    
                    # Validation du résultat
                    batch_embeddings = response.embeddings
                    if len(batch_embeddings) != len(batch):
                        raise ValueError(f"Nombre d'embeddings ({len(batch_embeddings)}) différent du nombre de textes ({len(batch)})")
                    
                    # Ajout des embeddings du lot aux résultats
                    all_embeddings.extend(batch_embeddings)
                    processing_time = time.time() - start_time
                    logger.info(f"Lot {batch_num}/{total_batches} traité en {processing_time:.2f}s")
                    
                    batch_success = True
                    processed_batches += 1
                    
                except asyncio.TimeoutError:
                    retry_count += 1
                    logger.warning(f"Timeout lors du traitement du lot {batch_num}/{total_batches}. Tentative {retry_count}/{max_retries}")
                    # Augmenter le timeout progressivement à chaque retry
                    current_timeout = min(current_timeout * 1.5, 600)  # Maximum 10 minutes
                    
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Erreur lors du traitement du lot {batch_num}/{total_batches}: {str(e)}. Tentative {retry_count}/{max_retries}")
                    await asyncio.sleep(2 ** retry_count)  # Backoff exponentiel
                    
            # Si le lot a échoué après toutes les tentatives
            if not batch_success:
                logger.error(f"Échec du traitement du lot {batch_num}/{total_batches} après {max_retries} tentatives")
                raise RuntimeError(f"Impossible de générer les embeddings pour le lot {batch_num}")
        
        logger.info(f"Génération des embeddings terminée: {processed_batches}/{total_batches} lots traités")
        return all_embeddings

    async def _call_claude_simple(self, query: str):
        """Génère une réponse pour une question simple."""
        try:
            # Utiliser notre client personnalisé avec le system prompt
            response = await asyncio.to_thread(
                self.client.messages_create,
                model=self.model,
                max_tokens=1000,
                temperature=0.7,  # Plus de personnalité pour les réponses simples
                system=self.SYSTEM_PROMPT,  # Ajouter le system prompt
                messages=[{"role": "user", "content": query}]
            )
            
            # Extraire le texte avec le format JSON de notre client personnalisé
            response_text = response["content"][0]["text"] if response and "content" in response else ""
            
            return response_text
            
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Claude (simple): {str(e)}")
            raise

    async def _call_claude_technical(self, query: str, context_docs: List[Dict]):
        """Génère une réponse technique basée sur le contexte."""
        try:
            formatted_context = self._format_technical_context(context_docs)
            # Utiliser notre client personnalisé avec le system prompt
            response = await asyncio.to_thread(
                self.client.messages_create,
                model=self.model,
                max_tokens=2000,
                temperature=0.6,  # Augmenté de 0.5 à 0.6 pour un ton plus naturel
                system=self.SYSTEM_PROMPT,  # Ajouter le system prompt
                messages=[{
                    "role": "user",
                    "content": f"Contexte :\n{formatted_context}\n\nQuestion : {query}"
                }]
            )
            
            # Extraire le texte avec le format JSON de notre client personnalisé
            response_text = response["content"][0]["text"] if response and "content" in response else ""
            
            # Formater la réponse avec notre formateur technique
            formatter = TechnicalResponseFormatter()
            formatted_response = formatter.format_response(
                query=query,
                context_docs=context_docs,
                llm_response=response_text
            )
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Claude (technique): {str(e)}")
            raise

    def _format_technical_context(self, context_docs: List[Dict]) -> str:
        """Formate le contexte technique pour les questions techniques."""
        if not context_docs:
            return "Aucun document pertinent trouvé dans la base de données."
            
        formatted_docs = []
        
        for i, doc in enumerate(context_docs, 1):
            content = doc.get("content", "").strip()
            metadata = doc.get("metadata", {})
            source = metadata.get("source", "").strip()
            page = metadata.get("page", "")
            section = metadata.get("section", "")
            score = doc.get("score", 0)
            relevance = int(score * 100)
            
            if content:
                # Amélioration: Inclure les informations de page et de section dans l'en-tête
                doc_header = f"Document {i} (pertinence: {relevance}%)"
                if source:
                    doc_header += f" - Source: {source}"
                if page:
                    doc_header += f" - Page: {page}"
                if section:
                    doc_header += f" - Section: {section}"
                
                # Essayer d'identifier les sections dans le contenu
                sections = []
                current_section = []
                
                for line in content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Détecter les titres de section potentiels
                    if line.isupper() or line.endswith(':'):
                        if current_section:
                            sections.append('\n'.join(current_section))
                            current_section = []
                    current_section.append(line)
                
                if current_section:
                    sections.append('\n'.join(current_section))
                
                # Formater le document
                formatted_content = '\n\n'.join(sections)
                formatted_docs.append(f"{doc_header}\n{'-' * len(doc_header)}\n{formatted_content}")
        
        context = '\n\n'.join(formatted_docs)
        
        return f"""Voici les documents pertinents trouvés dans la base de données.
Pour chaque document, j'ai indiqué sa pertinence par rapport à la question, ainsi que sa source, page et section quand disponibles.
Utilise ces informations pour structurer ta réponse de façon conversationnelle et fluide.

IMPORTANT:
- NE CITE PAS les sources dans le corps du texte. N'utilise pas de références comme (Document 1), [1], ou toute autre forme de citation.
- N'utilise pas de formulations comme "selon le document X" ou "d'après la source Y".
- Présente l'information comme si elle faisait partie de tes connaissances, de façon naturelle et fluide.
- Les sources seront automatiquement ajoutées à la fin de ta réponse, tu n'as pas besoin de les mentionner.

Documents :
{context}"""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(
        self,
        query: str,
        context_docs: List[Dict[str, Any]] = None,
        question_type: Optional[QuestionType] = None
    ) -> str:
        """
        Génère une réponse adaptée au type de question.
        
        Args:
            query: La question de l'utilisateur
            context_docs: Documents de contexte (optionnel)
            question_type: Type de question (si déjà classifié)
            
        Returns:
            str: La réponse générée
        """
        try:
            # Classifier la question si le type n'est pas fourni
            if question_type is None:
                try:
                    question_type = await self.classifier.classify(query)
                    logger.info(f"Question classifiée comme: {question_type}")
                except Exception as e:
                    logger.error(f"Erreur lors de la classification: {str(e)}")
                    # Par défaut, traiter comme une question technique si la classification échoue
                    question_type = QuestionType.TECHNIQUE
                    logger.info("Utilisation du type TECHNIQUE par défaut")

            # Générer la réponse selon le type de question
            try:
                if question_type == QuestionType.SIMPLE:
                    message = await self._call_claude_simple(query)
                else:
                    message = await self._call_claude_technical(query, context_docs or [])
                
                if not message:
                    raise ValueError("Réponse vide reçue de Claude")
                
                return message

            except Exception as e:
                logger.error(f"Erreur lors de l'appel à Claude: {str(e)}")
                raise RuntimeError(f"Erreur lors de la génération de la réponse: {str(e)}")

        except Exception as e:
            logger.error(f"Erreur lors de la génération de réponse: {str(e)}")
            raise RuntimeError("Une erreur est survenue lors de la génération de la réponse. Veuillez réessayer.")

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

            # Appeler Claude avec notre client personnalisé et le system prompt
            message = await asyncio.to_thread(
                self.client.messages_create,
                model=self.model,
                max_tokens=max_length,
                temperature=0.7,
                system=self.SYSTEM_PROMPT,  # Ajouter le system prompt
                messages=[
                    {
                        "role": "user",
                        "content": user_content
                    }
                ]
            )

            # Extraire le texte du ContentBlock avec le format JSON de notre client personnalisé
            summary = message["content"][0]["text"] if message and "content" in message else ""
            logger.info(f"Résumé généré avec succès: {summary[:100]}...")
            return summary

        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé: {str(e)}")
            raise

    async def generate_follow_up_questions(
        self,
        query: str,
        initial_response: str,
    ) -> List[str]:
        """Génère des questions de suivi basées sur la réponse initiale."""
        try:
            # Construire le prompt pour les questions de suivi
            user_content = f"""En fonction de la question initiale et de la réponse fournie, génère exactement 3 questions de suivi pertinentes.
            
            Question initiale : {query}
            
            Réponse : {initial_response}
            
            Format attendu : uniquement les 3 questions, une par ligne, sans numérotation ni préfixe."""

            # Appeler Claude avec notre client personnalisé et le system prompt
            message = await asyncio.to_thread(
                self.client.messages_create,
                model=self.model,
                max_tokens=500,
                temperature=0.7,
                system=self.SYSTEM_PROMPT,  # Ajouter le system prompt
                messages=[
                    {
                        "role": "user",
                        "content": user_content
                    }
                ]
            )

            # Extraire et traiter les questions avec le format JSON de notre client personnalisé
            questions_text = message["content"][0]["text"] if message and "content" in message else ""
            questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
            
            # S'assurer qu'on a exactement 3 questions
            questions = questions[:3]
            while len(questions) < 3:
                questions.append("Avez-vous d'autres questions ?")

            return questions

        except Exception as e:
            logger.error(f"Erreur lors de la génération des questions de suivi: {str(e)}")
            return []
