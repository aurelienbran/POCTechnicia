"""Module de traitement des fichiers PDF optimisé pour le POC TechnicIA."""
from pathlib import Path
import fitz  # PyMuPDF
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional
import logging
import tempfile
import tiktoken
import re
import os
from datetime import datetime
import subprocess
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Classe pour traiter les fichiers PDF avec optimisations pour RAG."""
    
    def __init__(self, 
                 chunk_size: int = 768, 
                 overlap: int = 200, 
                 temp_dir: Optional[Path] = None, 
                 extract_images: bool = False):  # Désactivé par défaut
        """
        Initialise le processeur PDF.
        
        Args:
            chunk_size: Taille des chunks en tokens
            overlap: Nombre de tokens de chevauchement entre chunks
            temp_dir: Répertoire temporaire pour stocker les extractions
            extract_images: Extraire les images des PDF ou non
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "technicia"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.extract_images = extract_images
        
        logger.info(f"PDFProcessor initialisé avec chunk_size={chunk_size}, "
                   f"overlap={overlap}, extract_images={extract_images}")
    
    async def close(self):
        """Nettoie les ressources temporaires."""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("**/*"):
                    if file.is_file():
                        file.unlink()
                for dir in self.temp_dir.glob("**/"):
                    if dir.is_dir() and dir != self.temp_dir:
                        dir.rmdir()
            logger.debug("Nettoyage des ressources temporaires effectué")
        except Exception as e:
            logger.warning(f"Erreur lors du nettoyage des ressources: {e}")
    
    async def get_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extrait les métadonnées du PDF."""
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata or {}
            metadata.update({
                "page_count": len(doc),
                "file_size": file_path.stat().st_size,
                "has_toc": len(doc.get_toc()) > 0,
                "processed_at": datetime.now().isoformat(),
                "filename": file_path.name
            })
            
            # Extraire la table des matières si elle existe
            if metadata["has_toc"]:
                metadata["toc"] = doc.get_toc()
                
            doc.close()
            logger.debug(f"Métadonnées extraites pour {file_path.name}")
            return metadata
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des métadonnées de {file_path}: {str(e)}")
            return {
                "error": str(e),
                "filename": file_path.name,
                "processed_at": datetime.now().isoformat()
            }
    
    async def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Méthode de compatibilité pour maintenir la rétrocompatibilité avec le code existant.
        Appelle simplement get_metadata.
        """
        logger.debug(f"extract_metadata appelé pour {file_path.name}, redirection vers get_metadata")
        return await self.get_metadata(file_path)
            
    def _extract_section_title(self, content: str) -> str:
        """Extrait un titre de section du contenu."""
        # Rechercher les motifs de titre courants
        patterns = [
            r'^(?:\d+\.)+\s+(.+?)$',  # Format: "1.2.3. Titre"
            r'^(Introduction|Contexte|Solution|Fonctionnalités|Architecture|Données|Développement|Conclusion)[\s:]+',
            r'^(?:Chapitre|Section|Partie)\s+\d+[\s:]+(.+?)$'  # Format: "Chapitre 1: Titre"
        ]
        
        lines = content.strip().split('\n')
        for line in lines[:5]:  # Chercher uniquement dans les premières lignes
            line = line.strip()
            if not line:
                continue
                
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    if match.groups():
                        return match.group(1)
                    return line
        
        # En dernier recours, prendre la première ligne non vide
        for line in lines:
            if line.strip():
                # Limiter la longueur du titre extrait
                return line.strip()[:80] + ('...' if len(line) > 80 else '')
                
        return "Section sans titre"
    
    async def _extract_images(self, doc: fitz.Document, page_idx: int) -> List[Dict[str, Any]]:
        """
        Extrait les images d'une page PDF.
        
        Args:
            doc: Document PDF ouvert
            page_idx: Index de la page
            
        Returns:
            Liste d'informations sur les images extraites
        """
        if not self.extract_images:
            return []
            
        page = doc[page_idx]
        image_list = page.get_images(full=True)
        
        result = []
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                
                # Filtrer les petites images (probablement des icônes ou décorations)
                if base_image["width"] * base_image["height"] < 10000:
                    continue
                
                # Créer un chemin pour l'image
                img_dir = self.temp_dir / f"page_{page_idx+1}"
                img_dir.mkdir(exist_ok=True)
                img_path = img_dir / f"img_{img_idx+1}.{base_image['ext']}"
                
                # Sauvegarder l'image
                with open(img_path, "wb") as f:
                    f.write(base_image["image"])
                
                # Type d'image (simplification pour le POC)
                image_type = "schéma" if base_image["width"] * base_image["height"] > 100000 else "image"
                
                result.append({
                    "path": str(img_path),
                    "type": image_type,
                    "page": page_idx + 1,
                    "size": f"{base_image['width']}x{base_image['height']}"
                })
                
                logger.debug(f"Image extraite: page {page_idx+1}, type {image_type}")
            except Exception as e:
                logger.warning(f"Erreur extraction image page {page_idx+1}, image {img_idx}: {e}")
        
        return result
    
    def _split_into_chunks_with_overlap(self, content: str) -> List[Dict[str, Any]]:
        """
        Découpe le texte en chunks avec chevauchement en respectant la structure.
        Préserve les titres en majuscules avec leur contenu associé.
        
        Args:
            content: Texte à découper
            
        Returns:
            Liste de chunks avec leur nombre de tokens
        """
        # Détection des titres techniques (en majuscules ou se terminant par ":")
        title_pattern = r'^([A-Z][A-Z\s]+(?:\s*:\s*|\n|$))'
        
        # Prétraitement pour préserver la relation entre titres et contenu
        marked_paragraphs = []
        current_title = None
        
        # Traiter le contenu ligne par ligne
        for line in content.split('\n'):
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            # Vérifier si la ligne est un titre technique
            title_match = re.match(title_pattern, line_stripped)
            if title_match:
                current_title = line_stripped
                # Marquer cette ligne comme un titre
                marked_paragraphs.append({"text": line_stripped, "is_title": True, "title": current_title})
            else:
                # C'est du contenu normal
                marked_paragraphs.append({"text": line_stripped, "is_title": False, "title": current_title})
        
        # Regrouper les paragraphes avec leurs titres
        structured_paragraphs = []
        current_group = []
        current_group_title = None
        
        for item in marked_paragraphs:
            if item["is_title"]:
                # Si on a un groupe en cours, l'ajouter à la liste
                if current_group:
                    structured_paragraphs.append({"title": current_group_title, "content": current_group})
                
                # Commencer un nouveau groupe
                current_group_title = item["text"]
                current_group = [item["text"]]
            else:
                # Ajouter au groupe courant
                if current_group_title:
                    current_group.append(item["text"])
                else:
                    # Pas de titre pour ce contenu
                    structured_paragraphs.append({"title": None, "content": [item["text"]]})
        
        # Ajouter le dernier groupe si nécessaire
        if current_group:
            structured_paragraphs.append({"title": current_group_title, "content": current_group})
        
        # Maintenant on crée les chunks en gardant les titres avec leur contenu
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for para in structured_paragraphs:
            title = para["title"]
            content_lines = para["content"]
            
            # Reconstruire le paragraphe complet
            if title:
                paragraph = title + "\n" + "\n".join(content_lines[1:]) if len(content_lines) > 1 else title
            else:
                paragraph = "\n".join(content_lines)
                
            paragraph = paragraph.strip()
            para_tokens = len(self.encoding.encode(paragraph))
            
            # Si le paragraphe est trop long à lui seul
            if para_tokens > self.chunk_size:
                # Ajouter le chunk courant s'il existe
                if current_chunk:
                    chunks.append({
                        "content": current_chunk,
                        "tokens": current_tokens
                    })
                    current_chunk = ""
                    current_tokens = 0
                
                # Cas spécial: titre avec contenu
                if title:
                    title_tokens = len(self.encoding.encode(title))
                    
                    # Commencer avec le titre
                    temp_chunk = title
                    temp_tokens = title_tokens
                    
                    # Ajouter autant de contenu que possible
                    for line in content_lines[1:] if len(content_lines) > 1 else []:
                        line_tokens = len(self.encoding.encode(line))
                        
                        if temp_tokens + line_tokens + 1 <= self.chunk_size:  # +1 pour le \n
                            temp_chunk += "\n" + line
                            temp_tokens += line_tokens + 1
                        else:
                            # Ce chunk est plein, l'ajouter
                            chunks.append({
                                "content": temp_chunk,
                                "tokens": temp_tokens
                            })
                            
                            # Commencer un nouveau chunk avec le titre répété pour le contexte
                            temp_chunk = f"{title}\n(suite) {line}"
                            temp_tokens = len(self.encoding.encode(temp_chunk))
                    
                    # Ajouter le dernier morceau s'il existe
                    if temp_chunk:
                        chunks.append({
                            "content": temp_chunk,
                            "tokens": temp_tokens
                        })
                else:
                    # Paragraphe normal trop long, le découper en phrases
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    temp_chunk = ""
                    temp_tokens = 0
                    
                    for sentence in sentences:
                        sentence_tokens = len(self.encoding.encode(sentence))
                        
                        if temp_tokens + sentence_tokens <= self.chunk_size:
                            temp_chunk += " " + sentence if temp_chunk else sentence
                            temp_tokens += sentence_tokens
                        else:
                            # Ajouter le chunk accumulé
                            if temp_chunk:
                                chunks.append({
                                    "content": temp_chunk,
                                    "tokens": temp_tokens
                                })
                            
                            # Démarrer un nouveau chunk avec cette phrase
                            temp_chunk = sentence
                            temp_tokens = sentence_tokens
                    
                    # Ajouter le dernier morceau
                    if temp_chunk:
                        chunks.append({
                            "content": temp_chunk,
                            "tokens": temp_tokens
                        })
            
            # Si ajouter ce paragraphe dépasserait la limite
            elif current_tokens + para_tokens > self.chunk_size:
                # Finir le chunk courant
                chunks.append({
                    "content": current_chunk,
                    "tokens": current_tokens
                })
                
                # Démarrer un nouveau chunk avec ce paragraphe
                current_chunk = paragraph
                current_tokens = para_tokens
            else:
                # Ajouter ce paragraphe au chunk courant
                separator = "\n\n" if current_chunk else ""
                current_chunk += separator + paragraph
                current_tokens += para_tokens + (2 if separator else 0)  # +2 pour le \n\n
        
        # Ajouter le dernier chunk s'il reste du contenu
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "tokens": current_tokens
            })
        
        # Ajouter le chevauchement entre chunks
        if len(chunks) <= 1 or self.overlap <= 0:
            return chunks
        
        chunks_with_overlap = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                # Le premier chunk reste inchangé
                chunks_with_overlap.append(chunk)
            else:
                # Pour les chunks suivants, ajouter un chevauchement avec le chunk précédent
                prev_content = chunks[i-1]["content"]
                prev_tokens = self.encoding.encode(prev_content)
                
                # Prendre les derniers tokens du chunk précédent
                overlap_size = min(self.overlap, len(prev_tokens))
                overlap_tokens = prev_tokens[-overlap_size:]
                overlap_text = self.encoding.decode(overlap_tokens)
                
                # Créer le nouveau contenu avec chevauchement
                new_content = overlap_text + "\n\n" + chunk["content"]
                new_tokens = len(self.encoding.encode(new_content))
                
                chunks_with_overlap.append({
                    "content": new_content,
                    "tokens": new_tokens
                })
        
        return chunks_with_overlap
    
    def _extract_basic_metadata(self, doc) -> Dict[str, Any]:
        """
        Extrait les métadonnées de base d'un document PDF.
        
        Args:
            doc: Objet document PyMuPDF
            
        Returns:
            Dictionnaire des métadonnées
        """
        metadata = {}
        try:
            if doc:
                # Extraire les métadonnées standard
                metadata_dict = doc.metadata
                if metadata_dict:
                    # Convertir les clés pour assurer la compatibilité
                    for key, value in metadata_dict.items():
                        if value and key.lower() in ["title", "author", "subject", "keywords", "creator", "producer", "creationdate", "moddate"]:
                            # Nettoyer les valeurs
                            if isinstance(value, str):
                                value = value.strip()
                            metadata[key.lower()] = value
                
                # Ajouter le nombre de pages
                metadata["page_count"] = doc.page_count
                
                # Vérifier si le document est encrypted
                metadata["encrypted"] = doc.is_encrypted
                
                # Récupérer la taille
                if hasattr(doc, "file_size") and doc.file_size:
                    metadata["file_size"] = doc.file_size
                
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des métadonnées de base: {str(e)}")
        
        return metadata
    
    async def process_pdf(self, file_path: Path) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Traite un fichier PDF, extrait son contenu et les métadonnées,
        et génère des chunks indexés.
        
        Args:
            file_path: Chemin vers le fichier PDF à traiter
            
        Yields:
            Chunks indexés contenant le texte et les métadonnées
        """
        try:
            # 1. Déterminer si c'est un document OCR (par nom ou métadonnées)
            is_ocr_document = False
            
            # Vérification par nom de fichier (conservative)
            if file_path.name.lower().startswith("ocr_") or "_ocr_" in file_path.name.lower():
                is_ocr_document = True
                logger.info(f"Document détecté comme OCR par son nom: {file_path.name}")
            
            # Vérification par métadonnées
            try:
                doc_metadata = fitz.open(str(file_path))
                basic_metadata = self._extract_basic_metadata(doc_metadata)
                doc_metadata.close()
                
                if basic_metadata:
                    producer = basic_metadata.get("producer", "").lower()
                    creator = basic_metadata.get("creator", "").lower()
                    
                    # Vérifier les signatures de logiciels d'OCR courants
                    ocr_signatures = ["ocrmypdf", "abbyy", "tesseract", "readiris", "omnipage", "adobe scan"]
                    
                    for sig in ocr_signatures:
                        if sig in producer or sig in creator:
                            is_ocr_document = True
                            logger.info(f"Document détecté comme OCR par ses métadonnées (signature: {sig})")
                            break
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction des métadonnées pour la détection OCR: {str(e)}")
            
            # 2. Extraire le texte et les métadonnées
            doc = fitz.open(str(file_path))
            
            # Détecter également si le document a besoin d'OCR en vérifiant si les premières pages ont du texte
            text_content = ""
            sample_size = min(3, doc.page_count)  # Vérifier jusqu'à 3 pages
            
            for i in range(sample_size):
                page_text = doc[i].get_text().strip()
                text_content += page_text
            
            needs_ocr = len(text_content) < 100  # Seuil arbitraire pour décider si le document a besoin d'OCR
            
            if needs_ocr and not is_ocr_document:
                logger.info(f"Document détecté comme nécessitant OCR (peu ou pas de texte): {file_path.name}")
            
            # Fermer le document pour éviter les problèmes de mémoire
            doc.close()
                
            # Extraire le texte page par page
            doc = fitz.open(str(file_path))
            all_text = []
            
            for i in range(doc.page_count):
                page = doc[i]
                # Utiliser notre méthode spécialisée qui sélectionne la meilleure approche
                page_text = await self._extract_text_from_page(file_path, page, i + 1, is_ocr_document)
                
                if not page_text.strip():
                    logger.warning(f"Aucun texte extrait de la page {i+1} de {file_path.name}")
                
                all_text.append(page_text)
            
            # Assembler le texte complet et créer des chunks
            full_text = "\n\n".join(all_text)
            
            # Si le document est vide ou presque vide, loguer un avertissement
            if len(full_text.strip()) < 100:
                logger.warning(f"Texte extrait très court pour {file_path.name}, OCR pourrait être nécessaire")
            
            # Générer des chunks à partir du texte
            chunks = self._split_into_chunks_with_overlap(full_text)
            
            # Extraire les métadonnées PDF
            metadata = await self.get_metadata(file_path)
            
            # Fermer le document
            doc.close()
            
            # Générer des chunks indexés avec métadonnées
            for i, chunk in enumerate(chunks):
                yield {
                    "id": f"{file_path.stem}_chunk_{i}",
                    "text": chunk["content"],
                    "metadata": {
                        **metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "is_ocr_document": is_ocr_document,
                        "filename": file_path.name,
                        "start_page": None,
                        "end_page": None
                    }
                }
                
        except Exception as e:
            logger.error(f"Erreur lors du traitement du PDF {file_path.name}: {str(e)}")
            logger.error(f"Détails: {e}")
            
            # En cas d'erreur majeure, renvoyer un chunk unique avec une description de l'erreur
            yield {
                "id": f"{file_path.stem}_error",
                "text": f"Erreur lors du traitement du document {file_path.name}. Veuillez vérifier le format du fichier.",
                "metadata": {
                    "filename": file_path.name,
                    "error": str(e),
                    "chunk_index": 0,
                    "total_chunks": 1
                }
            }
    
    async def _extract_text_from_page(self, file_path: Path, page, page_number: int, is_ocr_document: bool) -> str:
        """
        Extrait le texte d'une page en utilisant la méthode appropriée selon le type de document.
        
        Args:
            file_path: Chemin du fichier PDF
            page: Objet page PyMuPDF
            page_number: Numéro de la page (1-indexed)
            is_ocr_document: True si le document a subi OCR
            
        Returns:
            Texte extrait de la page
        """
        # Toujours essayer PyMuPDF d'abord
        page_text = page.get_text()
        
        # Si aucun texte n'est trouvé ou si on sait que c'est un document OCR,
        # utiliser pdftotext (plus robuste pour les PDFs avec OCR)
        if not page_text.strip() or is_ocr_document:
            try:
                # Utiliser subprocess.run au lieu d'asyncio
                import subprocess
                
                # Créer un répertoire temporaire pour extraire le texte
                temp_dir = Path(tempfile.gettempdir()) / "technicia_textextract"
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                # Extraire la page spécifique vers un fichier temporaire
                temp_page_pdf = temp_dir / f"page_{page_number}_{file_path.stem}.pdf"
                
                # Utiliser PyMuPDF pour extraire la page
                doc_subset = fitz.open()
                doc_subset.insert_pdf(fitz.open(str(file_path)), from_page=page_number-1, to_page=page_number-1)
                doc_subset.save(str(temp_page_pdf))
                doc_subset.close()
                
                # Utiliser pdftotext pour extraire le texte
                pdftotext_path = Path(os.environ.get("POPPLER_PATH", "")) / "pdftotext.exe"
                if not pdftotext_path.exists():
                    # Chercher dans le PATH actuel
                    paths = os.environ.get("PATH", "").split(os.pathsep)
                    for path in paths:
                        candidate = Path(path) / "pdftotext.exe"
                        if candidate.exists():
                            pdftotext_path = candidate
                            break
                        candidate = Path(path) / "pdftotext"
                        if candidate.exists():
                            pdftotext_path = candidate
                            break
                
                temp_text_file = temp_dir / f"page_{page_number}_{file_path.stem}.txt"
                
                if pdftotext_path.exists():
                    # Exécuter pdftotext de façon synchrone
                    result = subprocess.run([
                        str(pdftotext_path),
                        "-layout",  # Préserver la mise en page
                        str(temp_page_pdf),
                        str(temp_text_file)
                    ], capture_output=True, text=True)
                    
                    # Lire le fichier texte si disponible
                    if temp_text_file.exists():
                        with open(temp_text_file, 'r', encoding='utf-8', errors='ignore') as f:
                            extracted_text = f.read()
                        
                        if extracted_text.strip():
                            logger.debug(f"Page {page_number}: Texte extrait via pdftotext")
                            page_text = extracted_text
                else:
                    logger.warning(f"pdftotext non trouvé, impossible d'utiliser la méthode alternative d'extraction")
                
                # Nettoyage
                try:
                    temp_page_pdf.unlink(missing_ok=True)
                    temp_text_file.unlink(missing_ok=True)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Erreur lors de l'extraction de texte alternative: {str(e)}")
                # En cas d'erreur, revenir au texte original (potentiellement vide)
        
        return page_text
