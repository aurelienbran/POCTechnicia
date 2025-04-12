"""
Module d'extraction de tableaux à partir de documents techniques.

Ce module fournit des fonctionnalités pour détecter et extraire des tableaux
à partir de différents formats de documents (PDF, images, etc.).
Il utilise une combinaison de techniques OCR et d'analyse d'image pour
assurer une extraction précise des structures tabulaires.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import logging
import tempfile
import json
import csv
import pandas as pd
import numpy as np
from datetime import datetime

from .base import SpecializedProcessor, SpecializedProcessingResult

logger = logging.getLogger(__name__)

# Tentative d'importation des bibliothèques d'extraction de tableaux
try:
    import tabula
    import camelot
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    EXTRACTION_LIBS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Certaines bibliothèques d'extraction de tableaux ne sont pas disponibles: {str(e)}. "
                  "Installez-les avec: pip install tabula-py camelot-py pytesseract pdf2image pillow pandas")
    EXTRACTION_LIBS_AVAILABLE = False


class TableExtractor(SpecializedProcessor):
    """
    Processeur spécialisé pour l'extraction de tableaux depuis des documents.
    
    Cette classe fournit des méthodes pour détecter et extraire des tables à partir de
    différents formats de documents (PDF, images). Elle utilise plusieurs bibliothèques
    spécialisées et sélectionne la meilleure méthode selon le type de document.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'extracteur de tableaux.
        
        Args:
            config: Configuration de l'extracteur
                - extraction_mode: Mode d'extraction ('lattice', 'stream', 'auto')
                - confidence_threshold: Seuil de confiance pour la détection
                - max_tables: Nombre maximum de tables à extraire par page
                - format_preference: Format préféré pour les données ('dataframe', 'dict', 'list')
                - extract_text: Extraire également le texte des cellules
        """
        super().__init__(config)
        
        # Paramètres de configuration avec valeurs par défaut
        self.extraction_mode = self.config.get("extraction_mode", "auto")
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        self.max_tables = self.config.get("max_tables", 10)
        self.format_preference = self.config.get("format_preference", "list")
        self.extract_text = self.config.get("extract_text", True)
        
        # État d'initialisation des bibliothèques
        self.camelot_available = False
        self.tabula_available = False
        self.tesseract_available = False
    
    async def initialize(self) -> bool:
        """
        Initialise l'extracteur de tableaux en vérifiant la disponibilité des dépendances.
        
        Returns:
            True si au moins une méthode d'extraction est disponible, False sinon
        """
        if not EXTRACTION_LIBS_AVAILABLE:
            logger.error("Les bibliothèques d'extraction de tableaux ne sont pas disponibles")
            return False
        
        try:
            # Vérifier Camelot
            import camelot
            self.camelot_available = True
            logger.info("Camelot est disponible pour l'extraction de tableaux")
            
            # Vérifier Tabula
            import tabula
            self.tabula_available = True
            logger.info("Tabula est disponible pour l'extraction de tableaux")
            
            # Vérifier Tesseract (pour les images)
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                self.tesseract_available = True
                logger.info("Tesseract est disponible pour l'extraction de tableaux depuis des images")
            except Exception as e:
                logger.warning(f"Tesseract n'est pas disponible: {str(e)}")
                self.tesseract_available = False
            
            # L'extracteur est considéré comme initialisé si au moins une méthode est disponible
            self.initialized = self.camelot_available or self.tabula_available or self.tesseract_available
            
            if not self.initialized:
                logger.error("Aucune méthode d'extraction de tableaux n'est disponible")
                return False
                
            logger.info(f"Extracteur de tableaux initialisé avec succès: "
                       f"Camelot={self.camelot_available}, "
                       f"Tabula={self.tabula_available}, "
                       f"Tesseract={self.tesseract_available}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'extracteur de tableaux: {str(e)}")
            return False
    
    async def process(self, 
                document_path: Union[str, Path],
                page_number: Optional[int] = None,
                content_region: Optional[Dict[str, Any]] = None,
                **kwargs) -> SpecializedProcessingResult:
        """
        Extrait des tableaux à partir d'un document.
        
        Args:
            document_path: Chemin vers le document contenant les tableaux
            page_number: Numéro de page à traiter (None pour toutes les pages)
            content_region: Région du document contenant le tableau (coordonnées)
            **kwargs: Options supplémentaires
                - extraction_mode: Mode d'extraction spécifique pour cette requête
                - output_format: Format de sortie pour les données ('pandas', 'dict', 'list', 'csv', 'html')
                - save_to_file: Sauvegarder également les résultats dans un fichier
                - output_path: Chemin de sortie pour les fichiers sauvegardés
                
        Returns:
            Résultat de l'extraction de tableaux
        """
        if not self.is_initialized:
            logger.error("L'extracteur de tableaux n'est pas initialisé")
            return SpecializedProcessingResult(
                success=False,
                processor_name="TableExtractor",
                content_type="table",
                error_message="L'extracteur de tableaux n'est pas initialisé",
                source_document=str(document_path),
                page_number=page_number
            )
        
        document_path = Path(document_path)
        
        if not document_path.exists():
            return SpecializedProcessingResult(
                success=False,
                processor_name="TableExtractor",
                content_type="table",
                error_message=f"Le document n'existe pas: {document_path}",
                source_document=str(document_path),
                page_number=page_number
            )
        
        # Options spécifiques à cette requête
        extraction_mode = kwargs.get("extraction_mode", self.extraction_mode)
        output_format = kwargs.get("output_format", self.format_preference)
        save_to_file = kwargs.get("save_to_file", False)
        output_path = kwargs.get("output_path")
        
        try:
            # Déterminer le type de document
            document_type = document_path.suffix.lower()
            
            # Sélectionner la méthode d'extraction selon le type de document
            if document_type == '.pdf':
                tables_data = await self._extract_from_pdf(
                    document_path, 
                    page_number,
                    content_region,
                    extraction_mode
                )
            elif document_type in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
                tables_data = await self._extract_from_image(
                    document_path,
                    content_region
                )
            else:
                return SpecializedProcessingResult(
                    success=False,
                    processor_name="TableExtractor",
                    content_type="table",
                    error_message=f"Type de document non pris en charge: {document_type}",
                    source_document=str(document_path),
                    page_number=page_number
                )
            
            # Si aucun tableau n'a été trouvé
            if not tables_data:
                return SpecializedProcessingResult(
                    success=True,  # C'est un succès technique même si aucun tableau n'est trouvé
                    processor_name="TableExtractor",
                    content_type="table",
                    extracted_data={"tables": []},
                    source_document=str(document_path),
                    page_number=page_number,
                    metadata={"tables_count": 0},
                    text_representation="Aucun tableau détecté dans le document."
                )
            
            # Convertir les tableaux au format de sortie demandé
            formatted_tables = []
            for idx, table_data in enumerate(tables_data):
                formatted_table = self._format_table(table_data, output_format)
                formatted_tables.append(formatted_table)
                
                # Sauvegarder dans un fichier si demandé
                if save_to_file and output_path:
                    output_dir = Path(output_path)
                    output_dir.mkdir(exist_ok=True, parents=True)
                    
                    base_name = f"{document_path.stem}_table_{idx+1}"
                    
                    if output_format == 'csv':
                        output_file = output_dir / f"{base_name}.csv"
                        if isinstance(table_data, pd.DataFrame):
                            table_data.to_csv(output_file, index=False)
                    elif output_format == 'html':
                        output_file = output_dir / f"{base_name}.html"
                        if isinstance(table_data, pd.DataFrame):
                            table_data.to_html(output_file, index=False)
                    elif output_format == 'json':
                        output_file = output_dir / f"{base_name}.json"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            if isinstance(table_data, pd.DataFrame):
                                json.dump(table_data.to_dict(orient='records'), f, ensure_ascii=False, indent=2)
                            else:
                                json.dump(formatted_table, f, ensure_ascii=False, indent=2)
            
            # Créer la représentation textuelle des tableaux
            text_representation = self._create_text_representation(formatted_tables)
            
            # Préparer les métadonnées
            metadata = {
                "tables_count": len(formatted_tables),
                "extraction_mode": extraction_mode,
                "document_type": document_type,
                "output_format": output_format
            }
            
            if page_number is not None:
                metadata["page_number"] = page_number
            
            # Retourner le résultat final
            return SpecializedProcessingResult(
                success=True,
                processor_name="TableExtractor",
                content_type="table",
                extracted_data={"tables": formatted_tables},
                source_document=str(document_path),
                page_number=page_number,
                metadata=metadata,
                text_representation=text_representation
            )
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'extraction de tableaux: {str(e)}")
            return SpecializedProcessingResult(
                success=False,
                processor_name="TableExtractor",
                content_type="table",
                error_message=f"Erreur lors de l'extraction: {str(e)}",
                source_document=str(document_path),
                page_number=page_number
            )
    
    async def _extract_from_pdf(self,
                        document_path: Path,
                        page_number: Optional[int] = None,
                        content_region: Optional[Dict[str, Any]] = None,
                        extraction_mode: str = "auto") -> List[pd.DataFrame]:
        """
        Extrait des tableaux à partir d'un document PDF.
        
        Args:
            document_path: Chemin vers le document PDF
            page_number: Numéro de page à traiter
            content_region: Région contenant le tableau
            extraction_mode: Mode d'extraction ('lattice', 'stream', 'auto')
            
        Returns:
            Liste des tableaux extraits sous forme de DataFrames Pandas
        """
        tables = []
        
        # Préparer les pages à traiter
        pages = str(page_number) if page_number is not None else "all"
        
        # Préparer la région si spécifiée
        area = None
        if content_region:
            # Format attendu par Camelot et Tabula: [y1, x1, y2, x2]
            area = [
                content_region.get("y1", 0),
                content_region.get("x1", 0),
                content_region.get("y2", 0),
                content_region.get("x2", 0)
            ]
        
        # Déterminer si le document est basé sur un treillis (lattice) ou un flux (stream)
        if extraction_mode == "auto":
            # Essayer d'abord avec lattice (souvent meilleur pour les tableaux avec bordures)
            camelot_mode = "lattice"
            
            # Essayer également avec stream si disponible
            alternative_mode = "stream"
        else:
            camelot_mode = extraction_mode
            alternative_mode = None
        
        # Utiliser Camelot si disponible (généralement donne de meilleurs résultats)
        if self.camelot_available:
            try:
                loop = asyncio.get_event_loop()
                
                # Extraire avec le mode principal
                camelot_tables = await loop.run_in_executor(
                    None,
                    lambda: camelot.read_pdf(
                        str(document_path),
                        pages=pages,
                        flavor=camelot_mode,
                        suppress_stdout=True
                    )
                )
                
                # Si aucune table n'a été trouvée et que nous sommes en mode auto, essayer le mode alternatif
                if len(camelot_tables) == 0 and alternative_mode:
                    camelot_tables = await loop.run_in_executor(
                        None,
                        lambda: camelot.read_pdf(
                            str(document_path),
                            pages=pages,
                            flavor=alternative_mode,
                            suppress_stdout=True
                        )
                    )
                
                # Convertir les tableaux Camelot en DataFrames Pandas
                for table in camelot_tables:
                    if table.parsing_report['accuracy'] >= self.confidence_threshold * 100:
                        tables.append(table.df)
                
                # Si nous avons trouvé des tableaux avec Camelot, retourner ces résultats
                if tables:
                    return tables
                
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction avec Camelot: {str(e)}")
        
        # Si Camelot a échoué ou n'est pas disponible, essayer Tabula
        if self.tabula_available:
            try:
                loop = asyncio.get_event_loop()
                
                # Extraire les tableaux avec Tabula
                tabula_tables = await loop.run_in_executor(
                    None,
                    lambda: tabula.read_pdf(
                        str(document_path),
                        pages=pages,
                        area=area,
                        multiple_tables=True
                    )
                )
                
                # Ajouter les tableaux Tabula à la liste
                for table in tabula_tables:
                    if not table.empty:
                        tables.append(table)
                
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction avec Tabula: {str(e)}")
        
        # Si aucune méthode n'a fonctionné ou n'est disponible, essayer de convertir en image puis utiliser Tesseract
        if not tables and self.tesseract_available:
            try:
                # Convertir la page PDF en image
                images = await loop.run_in_executor(
                    None,
                    lambda: convert_from_path(document_path, first_page=page_number, last_page=page_number) 
                    if page_number else convert_from_path(document_path)
                )
                
                # Traiter chaque image
                for img in images:
                    # Extraire les tableaux de l'image avec pytesseract
                    image_tables = await self._extract_from_image_object(img, content_region)
                    tables.extend(image_tables)
                
            except Exception as e:
                logger.warning(f"Erreur lors de la conversion PDF en image: {str(e)}")
        
        return tables
    
    async def _extract_from_image(self,
                          image_path: Path,
                          content_region: Optional[Dict[str, Any]] = None) -> List[pd.DataFrame]:
        """
        Extrait des tableaux à partir d'une image.
        
        Args:
            image_path: Chemin vers l'image
            content_region: Région contenant le tableau
            
        Returns:
            Liste des tableaux extraits sous forme de DataFrames Pandas
        """
        if not self.tesseract_available:
            logger.error("Tesseract n'est pas disponible pour l'extraction depuis des images")
            return []
        
        try:
            loop = asyncio.get_event_loop()
            
            # Charger l'image
            image = await loop.run_in_executor(
                None,
                lambda: Image.open(image_path)
            )
            
            # Appeler la méthode d'extraction commune
            return await self._extract_from_image_object(image, content_region)
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'extraction depuis l'image: {str(e)}")
            return []
    
    async def _extract_from_image_object(self,
                                image: Image.Image,
                                content_region: Optional[Dict[str, Any]] = None) -> List[pd.DataFrame]:
        """
        Extrait des tableaux à partir d'un objet Image PIL.
        
        Args:
            image: Image PIL
            content_region: Région contenant le tableau
            
        Returns:
            Liste des tableaux extraits sous forme de DataFrames Pandas
        """
        tables = []
        
        try:
            loop = asyncio.get_event_loop()
            
            # Recadrer l'image si une région est spécifiée
            if content_region:
                x1 = content_region.get("x1", 0)
                y1 = content_region.get("y1", 0)
                x2 = content_region.get("x2", image.width)
                y2 = content_region.get("y2", image.height)
                
                image = image.crop((x1, y1, x2, y2))
            
            # Utiliser pytesseract pour extraire les données de tableau
            table_data = await loop.run_in_executor(
                None,
                lambda: pytesseract.image_to_data(image, output_type=pytesseract.Output.DATAFRAME)
            )
            
            # Filtrer les lignes vides et les textes de faible confiance
            table_data = table_data[
                (table_data['conf'] >= self.confidence_threshold * 100) & 
                (table_data['text'].str.strip() != '')
            ]
            
            if not table_data.empty:
                # Essayer de reconstruire la structure du tableau
                structured_table = self._reconstruct_table_from_ocr(table_data)
                
                if structured_table is not None and not structured_table.empty:
                    tables.append(structured_table)
                else:
                    # Fallback: utiliser directement les données OCR comme tableau simple
                    simple_table = table_data[['block_num', 'line_num', 'text']].pivot_table(
                        index='line_num', columns='block_num', values='text', aggfunc=lambda x: ' '.join(x)
                    )
                    tables.append(simple_table.reset_index(drop=True))
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction depuis l'objet image: {str(e)}")
        
        return tables
    
    def _reconstruct_table_from_ocr(self, ocr_data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Reconstruit une structure de tableau à partir des données OCR brutes.
        
        Args:
            ocr_data: DataFrame Pandas contenant les données OCR de pytesseract
            
        Returns:
            DataFrame représentant la structure tabulaire reconstruite, ou None en cas d'échec
        """
        try:
            # Regrouper par bloc et ligne pour former des cellules
            ocr_data['cell_id'] = ocr_data['block_num'].astype(str) + '_' + ocr_data['line_num'].astype(str)
            
            # Agréger le texte par cellule
            cells = ocr_data.groupby('cell_id').agg({
                'text': lambda x: ' '.join(x),
                'left': 'min',
                'top': 'min',
                'block_num': 'first',
                'line_num': 'first'
            }).reset_index()
            
            # Trier par position verticale (lignes) puis horizontale (colonnes)
            cells = cells.sort_values(['top', 'left'])
            
            # Identifier les lignes du tableau
            row_thresholds = []
            tops = cells['top'].values
            for i in range(1, len(tops)):
                if tops[i] - tops[i-1] > 10:  # Seuil pour considérer une nouvelle ligne
                    row_thresholds.append((tops[i] + tops[i-1]) / 2)
            
            # Assigner chaque cellule à une ligne
            row_assignments = np.zeros(len(cells), dtype=int)
            for i, threshold in enumerate(row_thresholds):
                row_assignments[cells['top'] > threshold] = i + 1
            
            cells['row'] = row_assignments
            
            # Identifier les colonnes du tableau
            # Trier les cellules par ligne puis position horizontale
            cells = cells.sort_values(['row', 'left'])
            
            # Pour chaque ligne, attribuer un numéro de colonne
            column_assignments = []
            for row, group in cells.groupby('row'):
                col_positions = list(range(len(group)))
                column_assignments.extend(col_positions)
            
            cells['column'] = column_assignments
            
            # Créer un DataFrame pivot avec les lignes et colonnes
            table = cells.pivot(index='row', columns='column', values='text')
            
            # Nettoyer le tableau (supprimer les colonnes/lignes vides, etc.)
            table = table.dropna(how='all').fillna('')
            
            return table
            
        except Exception as e:
            logger.warning(f"Erreur lors de la reconstruction du tableau: {str(e)}")
            return None
    
    def _format_table(self, table_data: pd.DataFrame, output_format: str) -> Any:
        """
        Convertit un tableau au format demandé.
        
        Args:
            table_data: DataFrame contenant les données du tableau
            output_format: Format de sortie ('pandas', 'dict', 'list', 'csv', 'html')
            
        Returns:
            Données du tableau au format demandé
        """
        # Si le format demandé est pandas, retourner directement
        if output_format == 'pandas':
            return table_data
        
        # Pour les autres formats, convertir depuis pandas
        if output_format == 'dict':
            return table_data.to_dict(orient='records')
        
        elif output_format == 'list':
            # Convertir en liste de listes (incluant les en-têtes)
            rows = [table_data.columns.tolist()]
            rows.extend(table_data.values.tolist())
            return rows
        
        elif output_format == 'csv':
            # Retourner sous forme de chaîne CSV
            return table_data.to_csv(index=False)
        
        elif output_format == 'html':
            # Retourner sous forme de table HTML
            return table_data.to_html(index=False)
        
        # Par défaut, utiliser le format liste
        return table_data.values.tolist()
    
    def _create_text_representation(self, tables: List[Any]) -> str:
        """
        Crée une représentation textuelle des tableaux extraits.
        
        Args:
            tables: Liste des tableaux extraits
            
        Returns:
            Représentation textuelle des tableaux
        """
        if not tables:
            return "Aucun tableau détecté."
        
        text_parts = []
        
        for idx, table in enumerate(tables):
            text_parts.append(f"[TABLEAU {idx+1}]")
            
            # Déterminer le type de données pour le formatage
            if isinstance(table, list):
                # Format liste de listes
                for row in table:
                    text_parts.append(" | ".join([str(cell) for cell in row]))
                    
            elif isinstance(table, dict) or (isinstance(table, list) and isinstance(table[0], dict)):
                # Format dictionnaire ou liste de dictionnaires
                if isinstance(table, dict):
                    items = [table]
                else:
                    items = table
                
                # Extraire les clés (en-têtes)
                headers = set()
                for item in items:
                    headers.update(item.keys())
                
                headers = sorted(headers)
                
                # Ajouter l'en-tête
                text_parts.append(" | ".join(headers))
                text_parts.append("-" * (sum(len(h) for h in headers) + 3 * (len(headers) - 1)))
                
                # Ajouter les lignes
                for item in items:
                    row = []
                    for header in headers:
                        row.append(str(item.get(header, "")))
                    text_parts.append(" | ".join(row))
            
            elif isinstance(table, str):
                # Déjà sous forme de texte (CSV ou HTML)
                text_parts.append(table)
            
            # Séparateur entre les tableaux
            text_parts.append("\n")
        
        return "\n".join(text_parts)
    
    def supports_content_type(self, content_type: str) -> bool:
        """
        Vérifie si le processeur prend en charge un type de contenu spécifique.
        
        Args:
            content_type: Type de contenu ('table')
            
        Returns:
            True si le processeur prend en charge ce type de contenu, False sinon
        """
        return content_type.lower() == 'table'
    
    def get_supported_content_types(self) -> List[str]:
        """
        Retourne la liste des types de contenu pris en charge par ce processeur.
        
        Returns:
            Liste des types de contenu pris en charge
        """
        return ['table']
