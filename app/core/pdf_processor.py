"""Module de traitement des fichiers PDF."""
from pathlib import Path
import fitz  # PyMuPDF
import asyncio
from typing import List, Dict, Any, AsyncGenerator
import logging
import tempfile
import tiktoken
import re

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Classe pour traiter les fichiers PDF."""
    
    def __init__(self, chunk_size: int = 1024, overlap: int = 100, temp_dir: Path = None):
        """Initialise le processeur PDF avec des paramètres de chunk."""
        self.chunk_size = chunk_size  # Taille maximale pour Voyage AI
        self.overlap = overlap
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "pdf_processor"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    async def process_pdf(self, file_path: Path) -> AsyncGenerator[Dict[str, Any], None]:
        """Traite un fichier PDF avec gestion de la mémoire."""
        try:
            # Ouvrir le PDF
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            # Pour chaque page
            for page_num in range(total_pages):
                # Extraire le texte de la page
                page = doc[page_num]
                text = page.get_text()
                
                if not text.strip():
                    continue
                
                # Découper le texte en chunks
                chunks = self._split_text_into_chunks(text)
                
                # Enrichir chaque chunk avec les métadonnées
                for i, chunk in enumerate(chunks):
                    yield {
                        'text': chunk['text'],
                        'tokens': chunk['tokens'],
                        'page': page_num + 1,
                        'total_pages': total_pages,
                        'chunk_number': i + 1,
                        'total_chunks': len(chunks),
                        'source': file_path.name
                    }
            
            # Fermer le document
            doc.close()
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du PDF {file_path}: {str(e)}")
            raise
    
    def _split_text_into_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Découpe le texte en chunks basés sur le nombre de tokens."""
        chunks = []
        
        # Nettoyer le texte
        text = text.strip()
        if not text:
            return []
            
        # Convertir en tokens une seule fois
        tokens = self.encoding.encode(text)
        
        # Si le texte est plus petit que la taille maximale
        if len(tokens) <= self.chunk_size:
            return [{
                'text': text,
                'tokens': len(tokens)
            }]
        
        # Diviser en phrases pour un meilleur découpage
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = []
        current_tokens = []
        
        for sentence in sentences:
            # Encoder la phrase
            sentence_tokens = self.encoding.encode(sentence)
            
            # Si la phrase seule est trop longue, la découper en mots
            if len(sentence_tokens) > self.chunk_size:
                # Ajouter le chunk en cours s'il existe
                if current_chunk:
                    chunks.append({
                        'text': ' '.join(current_chunk),
                        'tokens': len(current_tokens)
                    })
                    current_chunk = []
                    current_tokens = []
                
                # Découper la phrase en mots
                words = sentence.split()
                temp_chunk = []
                temp_tokens = []
                
                for word in words:
                    word_tokens = self.encoding.encode(word + ' ')
                    if len(temp_tokens) + len(word_tokens) > self.chunk_size:
                        if temp_chunk:
                            chunks.append({
                                'text': ' '.join(temp_chunk),
                                'tokens': len(temp_tokens)
                            })
                        temp_chunk = [word]
                        temp_tokens = word_tokens
                    else:
                        temp_chunk.append(word)
                        temp_tokens.extend(word_tokens)
                
                if temp_chunk:
                    chunks.append({
                        'text': ' '.join(temp_chunk),
                        'tokens': len(temp_tokens)
                    })
                continue
            
            # Si ajouter cette phrase dépasserait la limite
            if current_tokens and len(current_tokens) + len(sentence_tokens) > self.chunk_size:
                chunks.append({
                    'text': ' '.join(current_chunk),
                    'tokens': len(current_tokens)
                })
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens.extend(sentence_tokens)
        
        # Ajouter le dernier chunk s'il existe
        if current_chunk:
            chunks.append({
                'text': ' '.join(current_chunk),
                'tokens': len(current_tokens)
            })
        
        return chunks
    
    async def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extrait les métadonnées du PDF."""
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata
            doc.close()
            return metadata
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des métadonnées de {file_path}: {str(e)}")
            return {}
