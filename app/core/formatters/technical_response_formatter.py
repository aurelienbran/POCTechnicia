from typing import List, Dict, Any, Optional
import re
import logging

logger = logging.getLogger(__name__)

class TechnicalResponseFormatter:
    """Formateur pour les réponses techniques."""
    
    def __init__(self):
        """Initialise le formateur technique."""
        self.component_patterns = [
            r"système\s+d['']([^\s]+)",  # système d'échappement
            r"système\s+de\s+([^\s]+)",  # système de freinage
            r"([^\s]+)\s+system",        # exhaust system
            r"le\s+([^\s]+)",           # le moteur, le frein
            r"l['']([^\s]+)",           # l'échappement
            r"du\s+([^\s]+)",           # du moteur
            r"des\s+([^\s]+)s?"         # des freins
        ]

    def format_response(self, query: str, context_docs: List[Dict], llm_response: str) -> str:
        """
        Formate la réponse technique selon le template standard.
        
        Args:
            query: La question de l'utilisateur
            context_docs: Les documents de contexte
            llm_response: La réponse brute du LLM
            
        Returns:
            str: La réponse formatée
        """
        try:
            # Extraire le composant principal
            component = self._extract_component(query.lower())
            if not component:
                component = "Non spécifié"
            
            # Extraire les sections de la réponse
            sections = self._extract_sections(llm_response)
            
            # Nettoyer les références dans chaque section
            for section_key in sections:
                if sections[section_key]:
                    sections[section_key] = self._clean_references_from_text(sections[section_key])
            
            # Formater les sources
            sources = self._format_sources(context_docs)
            
            # Appliquer le template
            return self._apply_template(component, sections, sources)
            
        except Exception as e:
            logger.error(f"Erreur lors du formatage de la réponse technique: {str(e)}")
            return llm_response  # Fallback sur la réponse brute en cas d'erreur

    def _extract_component(self, query: str) -> Optional[str]:
        """Extrait le composant/système principal de la question."""
        for pattern in self.component_patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1).strip()
        return None

    def _extract_sections(self, response: str) -> Dict[str, str]:
        """
        Extrait les différentes sections de la réponse avec une approche robuste.
        Utilise des expressions régulières pour capturer les sections complètes.
        """
        if not isinstance(response, str):
            logger.warning(f"Réponse non textuelle reçue: {type(response)}")
            return {
                "description": "Erreur: Format de réponse invalide",
                "specifications": "",
                "instructions_precautions": "",
                "verification": ""
            }
            
        # Initialiser les sections avec des valeurs vides
        sections = {
            "description": "",
            "specifications": "",
            "instructions_precautions": "",
            "verification": ""
        }
        
        try:
            # Nettoyer la réponse
            response = re.sub(r'\[Sources[^\]]*\]', '', response)
            
            # Approche 1: Utiliser des regex pour extraire les sections complètes
            section_patterns = {
                "description": r'(?:^|\n)DESCRIPTION\s*\n(.*?)(?=\n\s*(?:INFORMATIONS TECHNIQUES|INSTRUCTIONS ET PRÉCAUTIONS|VÉRIFICATION|SOURCES)|$)',
                "specifications": r'(?:^|\n)INFORMATIONS TECHNIQUES\s*\n(.*?)(?=\n\s*(?:INSTRUCTIONS ET PRÉCAUTIONS|VÉRIFICATION|SOURCES)|$)',
                "instructions_precautions": r'(?:^|\n)INSTRUCTIONS ET PRÉCAUTIONS\s*\n(.*?)(?=\n\s*(?:VÉRIFICATION|SOURCES)|$)',
                "verification": r'(?:^|\n)VÉRIFICATION\s*\n(.*?)(?=\n\s*(?:SOURCES)|$)'
            }
            
            for section_key, pattern in section_patterns.items():
                match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
                if match:
                    sections[section_key] = match.group(1).strip()
            
            # Approche 2 (fallback): Si les regex ne trouvent rien, utiliser une approche ligne par ligne
            if not any(sections.values()):
                logger.info("Utilisation de la méthode de fallback pour l'extraction des sections")
                current_section = "description"  # Section par défaut
                section_content = {
                    "description": [],
                    "specifications": [],
                    "instructions_precautions": [],
                    "verification": []
                }
                
                for line in response.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    lower_line = line.lower()
                    
                    # Détecter les changements de section
                    if re.match(r'^DESCRIPTION\s*:?$', line, re.IGNORECASE):
                        current_section = "description"
                        continue
                    elif re.match(r'^INFORMATIONS\s+TECHNIQUES\s*:?$', line, re.IGNORECASE) or "informations techniques" in lower_line:
                        current_section = "specifications"
                        continue
                    elif re.match(r'^INSTRUCTIONS\s+ET\s+PRÉCAUTIONS\s*:?$', line, re.IGNORECASE) or "instructions et précautions" in lower_line:
                        current_section = "instructions_precautions"
                        continue
                    elif re.match(r'^VÉRIFICATION\s*:?$', line, re.IGNORECASE) or "vérification" in lower_line:
                        current_section = "verification"
                        continue
                    elif re.match(r'^SOURCES\s*:?$', line, re.IGNORECASE) or "sources" in lower_line:
                        # Ignorer la section sources, elle est gérée séparément
                        continue
                    
                    # Ajouter la ligne à la section courante
                    section_content[current_section].append(line)
                
                # Convertir les listes en texte
                for section in section_content:
                    if section_content[section]:
                        sections[section] = "\n".join(section_content[section])
            
            # Vérifier si nous avons au moins une section avec du contenu
            if not any(sections.values()):
                # Si aucune section n'a été identifiée, mettre tout le contenu dans la description
                logger.warning("Aucune section identifiée, utilisation du contenu brut comme description")
                sections["description"] = response.strip()
                
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des sections: {str(e)}")
            sections["description"] = "Erreur lors du traitement de la réponse"
            
        return sections

    def _clean_references_from_text(self, text: str) -> str:
        """
        Supprime les références au milieu du texte.
        Exemples de références à supprimer: (Manuel EL, p.158), (Document 1), [1], etc.
        """
        # Nettoyer les références entre parenthèses
        cleaned_text = re.sub(r'\([^)]*(?:document|doc|manuel|source|référence|page|p\.)[^)]*\)', '', text, flags=re.IGNORECASE)
        
        # Nettoyer les références entre parenthèses avec des numéros
        cleaned_text = re.sub(r'\(\s*(?:doc(?:ument)?\s*)?(?:\d+|[ivxlcdm]+)(?:\s*,\s*p(?:age|p)?\.\s*\d+)?\s*\)', '', cleaned_text, flags=re.IGNORECASE)
        
        # Nettoyer les références entre crochets
        cleaned_text = re.sub(r'\[\s*\d+\s*\]', '', cleaned_text)
        cleaned_text = re.sub(r'\[\s*(?:doc(?:ument)?\s*)?(?:\d+|[ivxlcdm]+)(?:\s*,\s*p(?:age|p)?\.\s*\d+)?\s*\]', '', cleaned_text, flags=re.IGNORECASE)
        
        # Nettoyer les références de type "selon le document X" ou "d'après le document X"
        cleaned_text = re.sub(r'(?:selon|d\'après|comme mentionné dans|comme indiqué dans|d\'après|tel que décrit dans)\s+(?:le\s+)?(?:document|doc|manuel|source|référence)\s+(?:\d+|[ivxlcdm]+)', '', cleaned_text, flags=re.IGNORECASE)
        
        # Nettoyer les doubles espaces qui pourraient résulter des suppressions
        cleaned_text = re.sub(r'\s{2,}', ' ', cleaned_text)
        
        # Nettoyer les espaces avant la ponctuation
        cleaned_text = re.sub(r'\s+([.,;:!?])', r'\1', cleaned_text)
        
        # Nettoyer les phrases qui commencent par une ponctuation (résultat possible de suppressions)
        cleaned_text = re.sub(r'(?<=\.\s+)([.,;:!?])', '', cleaned_text)
        
        return cleaned_text

    def _format_sources(self, context_docs: List[Dict]) -> str:
        """Formate les sources des documents avec leur pertinence."""
        if not context_docs:
            return "Aucune source disponible"
            
        sources = []
        seen_sources = set()
        
        for doc in context_docs:
            source = doc.get("metadata", {}).get("source", "")
            score = doc.get("score", 0)
            
            if source and source not in seen_sources:
                relevance = int(score * 100)
                sources.append(f"- {source} (pertinence: {relevance}%)")
                seen_sources.add(source)
        
        return "\n".join(sources)

    def _apply_template(self, component: str, sections: Dict[str, str], sources: str) -> str:
        """
        Applique un template conversationnel à la réponse.
        Élimine la structure rigide tout en conservant les informations importantes.
        """
        # Construire une réponse plus naturelle
        response_parts = []
        
        # Ajouter le composant/système comme contexte initial
        response_parts.append(f"À propos de {component}:")
        
        # Fusionner les sections en un texte cohérent avec des transitions naturelles
        if sections.get('description'):
            response_parts.append(sections['description'])
        
        if sections.get('specifications'):
            # Ajouter une transition naturelle vers les spécifications
            specs_transition = "\n\nVoici les détails techniques importants à connaître : "
            response_parts.append(f"{specs_transition}{sections['specifications']}")
        
        if sections.get('instructions_precautions'):
            # Ajouter une transition naturelle vers les instructions
            instructions_transition = "\n\nPour intervenir sur ce système, voici ce que je te recommande : "
            response_parts.append(f"{instructions_transition}{sections['instructions_precautions']}")
        
        if sections.get('verification'):
            # Ajouter une transition naturelle vers les vérifications
            verification_transition = "\n\nPour confirmer que tout fonctionne correctement : "
            response_parts.append(f"{verification_transition}{sections['verification']}")
        
        # Fusionner toutes les parties en un texte cohérent
        main_content = "\n".join(response_parts)
        
        # Ne plus ajouter les sources - elles seront gérées par l'API
        return main_content
