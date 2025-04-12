"""
Définition des classes de base pour les processeurs spécialisés.

Ce module fournit les interfaces communes que tous les processeurs spécialisés
doivent implémenter, assurant une cohérence et une interopérabilité
au sein du système de traitement de documents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class SpecializedProcessingResult:
    """
    Résultat d'un traitement par un processeur spécialisé.
    
    Cette classe encapsule les résultats d'une extraction ou analyse spécialisée,
    incluant les données extraites, les métadonnées et les informations d'état.
    """
    
    success: bool
    processor_name: str
    content_type: str  # 'table', 'formula', 'schema', etc.
    
    # Données extraites spécifiques au type de contenu
    extracted_data: Any = None
    
    # Informations sur le document source
    source_document: Optional[str] = None
    page_number: Optional[int] = None
    
    # Métadonnées techniques
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Informations d'erreur
    error_message: Optional[str] = None
    
    # Texte alternatif/description pour l'élément extrait
    text_representation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "success": self.success,
            "processor_name": self.processor_name,
            "content_type": self.content_type,
            "extracted_data": self.extracted_data,
            "source_document": self.source_document,
            "page_number": self.page_number,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "text_representation": self.text_representation
        }
    
    def get_text_content(self) -> str:
        """
        Retourne une représentation textuelle du contenu extrait.
        
        Cette méthode est utile pour les cas où le contenu extrait
        doit être intégré dans un texte, comme pour le RAG.
        
        Returns:
            Représentation textuelle du contenu
        """
        if self.text_representation:
            return self.text_representation
        
        # Si aucune représentation textuelle n'est fournie mais que l'extraction a réussi,
        # essayons de créer une représentation de base à partir des données
        if self.success and self.extracted_data:
            content_type = self.content_type.lower()
            
            if content_type == 'table':
                return f"[TABLE EXTRAITE]\n{self._format_table_data()}"
            
            if content_type == 'formula':
                return f"[FORMULE]\n{self._format_formula_data()}"
                
            if content_type == 'schema':
                return f"[SCHÉMA TECHNIQUE]\n{self._format_schema_data()}"
                
            # Générique pour tout autre type
            return f"[ÉLÉMENT TECHNIQUE: {self.content_type}]\n{str(self.extracted_data)}"
        
        # Si l'extraction a échoué
        if self.error_message:
            return f"[ÉCHEC D'EXTRACTION DE {self.content_type}]: {self.error_message}"
            
        # Cas par défaut
        return f"[CONTENU TECHNIQUE NON EXTRAIT: {self.content_type}]"
    
    def _format_table_data(self) -> str:
        """Formate les données de table en texte lisible."""
        try:
            if isinstance(self.extracted_data, dict) and 'rows' in self.extracted_data:
                rows = self.extracted_data['rows']
                if not rows:
                    return "Table vide"
                
                # Construire la représentation textuelle de la table
                result = []
                
                # Si nous avons un en-tête (première ligne)
                if rows:
                    # Ajouter les en-têtes
                    result.append(" | ".join([str(cell) for cell in rows[0]]))
                    result.append("-" * len(result[0]))
                    
                    # Ajouter les données
                    for row in rows[1:]:
                        result.append(" | ".join([str(cell) for cell in row]))
                
                return "\n".join(result)
            
            # Si le format est différent, retourner une représentation par défaut
            return str(self.extracted_data)
            
        except Exception as e:
            logger.warning(f"Erreur lors du formatage des données de table: {str(e)}")
            return str(self.extracted_data)
    
    def _format_formula_data(self) -> str:
        """Formate les données de formule en texte lisible."""
        try:
            if isinstance(self.extracted_data, dict):
                # Si nous avons des données structurées pour la formule
                tex_repr = self.extracted_data.get('tex', '')
                ascii_repr = self.extracted_data.get('ascii', '')
                description = self.extracted_data.get('description', '')
                
                result = []
                if description:
                    result.append(description)
                    
                if tex_repr:
                    result.append(f"LaTeX: {tex_repr}")
                    
                if ascii_repr:
                    result.append(f"ASCII: {ascii_repr}")
                
                return "\n".join(result) if result else str(self.extracted_data)
            
            # Si le format est simple
            return str(self.extracted_data)
            
        except Exception as e:
            logger.warning(f"Erreur lors du formatage des données de formule: {str(e)}")
            return str(self.extracted_data)
    
    def _format_schema_data(self) -> str:
        """Formate les données de schéma en texte lisible."""
        try:
            if isinstance(self.extracted_data, dict):
                # Si nous avons des données structurées pour le schéma
                description = self.extracted_data.get('description', '')
                elements = self.extracted_data.get('elements', [])
                relations = self.extracted_data.get('relations', [])
                
                result = []
                if description:
                    result.append(description)
                
                if elements:
                    result.append("\nÉléments identifiés:")
                    for elem in elements:
                        elem_desc = elem.get('description', 'Élément sans description')
                        elem_type = elem.get('type', 'inconnu')
                        result.append(f"- {elem_desc} (type: {elem_type})")
                
                if relations:
                    result.append("\nRelations identifiées:")
                    for rel in relations:
                        rel_desc = rel.get('description', 'Relation sans description')
                        result.append(f"- {rel_desc}")
                
                return "\n".join(result) if result else str(self.extracted_data)
            
            # Si le format est simple
            return str(self.extracted_data)
            
        except Exception as e:
            logger.warning(f"Erreur lors du formatage des données de schéma: {str(e)}")
            return str(self.extracted_data)


class SpecializedProcessor(ABC):
    """
    Interface de base pour tous les processeurs spécialisés.
    
    Cette classe définit les méthodes communes que tous les processeurs spécialisés
    doivent implémenter pour s'intégrer au pipeline de traitement des documents.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le processeur spécialisé.
        
        Args:
            config: Configuration du processeur
        """
        self.config = config or {}
        self.initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Indique si le processeur est initialisé."""
        return self.initialized
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialise le processeur.
        
        Cette méthode doit être implémentée par chaque processeur spécialisé
        pour préparer les ressources nécessaires à son fonctionnement.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abstractmethod
    async def process(self, 
                document_path: Union[str, Path],
                page_number: Optional[int] = None,
                content_region: Optional[Dict[str, Any]] = None,
                **kwargs) -> SpecializedProcessingResult:
        """
        Traite un document ou une partie de document pour en extraire du contenu spécialisé.
        
        Args:
            document_path: Chemin vers le document à traiter
            page_number: Numéro de page à traiter (pour les documents multi-pages)
            content_region: Région du document contenant le contenu (coordonnées)
            **kwargs: Arguments supplémentaires spécifiques au processeur
            
        Returns:
            Résultat du traitement spécialisé
        """
        pass
    
    @abstractmethod
    def supports_content_type(self, content_type: str) -> bool:
        """
        Vérifie si le processeur prend en charge un type de contenu spécifique.
        
        Args:
            content_type: Type de contenu ('table', 'formula', 'schema', etc.)
            
        Returns:
            True si le processeur prend en charge ce type de contenu, False sinon
        """
        pass
    
    @abstractmethod
    def get_supported_content_types(self) -> List[str]:
        """
        Retourne la liste des types de contenu pris en charge par ce processeur.
        
        Returns:
            Liste des types de contenu pris en charge
        """
        pass
    
    def __str__(self) -> str:
        """Représentation du processeur sous forme de chaîne."""
        return f"{self.__class__.__name__}(initialized={self.initialized})"
