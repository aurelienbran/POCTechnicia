#!/usr/bin/env python
"""
Script de test pour le système de traitement de documents.
Permet de tester les fonctionnalités de conversion, OCR et chunking sur différents types de documents.
"""

import asyncio
import argparse
import logging
import time
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import json

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Ajouter le répertoire racine au path Python
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

# Importer les modules de l'application
from app.core.file_processing.document_processor import get_document_processor, DocumentProcessingResult
from app.core.file_processing.conversion import get_document_converter
from app.core.file_processing.chunking import get_text_chunker
from app.core.file_processing.ocr import get_ocr_processor

async def test_document_conversion(file_path: Path, output_dir: Path = None) -> None:
    """
    Teste la conversion d'un document en texte.
    
    Args:
        file_path: Chemin vers le document à tester
        output_dir: Répertoire de sortie pour les fichiers convertis
    """
    logger.info(f"Test de conversion pour le document: {file_path}")
    
    # Créer un répertoire de sortie si nécessaire
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Obtenir le convertisseur
        converter = await get_document_converter(provider_name="standard")
        
        # Convertir le document
        start_time = time.time()
        result = await converter.convert_file(file_path)
        
        # Afficher les résultats
        logger.info(f"Résultat de la conversion:")
        logger.info(f"  Succès: {result.success}")
        logger.info(f"  Temps de traitement: {time.time() - start_time:.2f} secondes")
        
        if result.success:
            logger.info(f"  Taille du texte extrait: {len(result.text_content)} caractères")
            logger.info(f"  Nombre de mots: {len(result.text_content.split())} mots")
            logger.info(f"  Pages traitées: {result.pages_processed} / {result.total_pages}")
            
            # Enregistrer le texte dans un fichier si un répertoire de sortie est spécifié
            if output_dir:
                output_file = output_dir / f"{file_path.stem}_converted.txt"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result.text_content)
                logger.info(f"  Texte enregistré dans: {output_file}")
                
                # Enregistrer les métadonnées
                metadata_file = output_dir / f"{file_path.stem}_metadata.json"
                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(result.metadata, f, indent=2, default=str)
                logger.info(f"  Métadonnées enregistrées dans: {metadata_file}")
        else:
            logger.error(f"  Erreur: {result.error_message}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Erreur lors du test de conversion: {str(e)}")
        return None

async def test_document_ocr(file_path: Path, output_dir: Path = None) -> None:
    """
    Teste l'OCR sur un document.
    
    Args:
        file_path: Chemin vers le document à tester
        output_dir: Répertoire de sortie pour les fichiers OCR
    """
    logger.info(f"Test d'OCR pour le document: {file_path}")
    
    # Créer un répertoire de sortie si nécessaire
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Obtenir le processeur OCR
        ocr_processor = await get_ocr_processor()
        
        # Vérifier si le document nécessite OCR
        needs_ocr = await ocr_processor.needs_ocr(file_path)
        logger.info(f"  Nécessite OCR: {needs_ocr}")
        
        # Si OCR nécessaire, traiter le document
        if needs_ocr:
            # Traiter le document
            start_time = time.time()
            result = await ocr_processor.process_document(
                input_path=file_path,
                output_dir=output_dir
            )
            
            # Afficher les résultats
            logger.info(f"Résultat de l'OCR:")
            logger.info(f"  Succès: {result.success}")
            logger.info(f"  Temps de traitement: {time.time() - start_time:.2f} secondes")
            
            if result.success:
                logger.info(f"  Fichier de sortie: {result.output_path}")
                logger.info(f"  Pages traitées: {result.pages_processed}")
                
                # Conversion du fichier OCR en texte pour vérification
                converter = await get_document_converter(provider_name="standard")
                text_result = await converter.convert_file(result.output_path)
                
                if text_result.success:
                    logger.info(f"  Taille du texte extrait après OCR: {len(text_result.text_content)} caractères")
                    logger.info(f"  Nombre de mots après OCR: {len(text_result.text_content.split())} mots")
                    
                    # Enregistrer le texte dans un fichier
                    if output_dir:
                        output_file = output_dir / f"{file_path.stem}_ocr.txt"
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(text_result.text_content)
                        logger.info(f"  Texte OCR enregistré dans: {output_file}")
            else:
                logger.error(f"  Erreur: {result.error_message}")
                
            return result
        else:
            logger.info("  OCR non nécessaire pour ce document.")
            return None
    
    except Exception as e:
        logger.exception(f"Erreur lors du test d'OCR: {str(e)}")
        return None

async def test_document_chunking(text_content: str, output_dir: Path = None, 
                          chunk_sizes: List[int] = None, overlaps: List[int] = None) -> None:
    """
    Teste le chunking d'un texte avec différentes tailles et chevauchements.
    
    Args:
        text_content: Texte à découper en chunks
        output_dir: Répertoire de sortie pour les fichiers de chunks
        chunk_sizes: Liste des tailles de chunks à tester
        overlaps: Liste des chevauchements à tester
    """
    if not text_content:
        logger.error("Aucun texte fourni pour le test de chunking")
        return None
    
    logger.info(f"Test de chunking pour un texte de {len(text_content)} caractères")
    
    # Valeurs par défaut
    if not chunk_sizes:
        chunk_sizes = [500, 1000, 2000]
    
    if not overlaps:
        overlaps = [0, 100, 200]
    
    # Créer un répertoire de sortie si nécessaire
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
    
    results = {}
    
    try:
        # Tester différents types de chunkers
        chunker_types = ["simple", "semantic"]
        
        for chunker_type in chunker_types:
            logger.info(f"Test du chunker: {chunker_type}")
            
            try:
                # Obtenir le chunker
                chunker = await get_text_chunker(provider_name=chunker_type)
                
                for chunk_size in chunk_sizes:
                    for overlap in overlaps:
                        logger.info(f"  Test avec: taille={chunk_size}, chevauchement={overlap}")
                        
                        # Découper le texte
                        start_time = time.time()
                        result = await chunker.chunk_text(
                            text=text_content,
                            max_chunk_size=chunk_size,
                            overlap=overlap
                        )
                        
                        # Afficher les résultats
                        processing_time = time.time() - start_time
                        logger.info(f"  Résultat du chunking:")
                        logger.info(f"    Nombre de chunks: {len(result.chunks)}")
                        logger.info(f"    Temps de traitement: {processing_time:.2f} secondes")
                        
                        # Calculer des statistiques sur les chunks
                        if result.chunks:
                            chunk_lengths = [len(chunk) for chunk in result.chunks]
                            avg_length = sum(chunk_lengths) / len(chunk_lengths)
                            max_length = max(chunk_lengths)
                            min_length = min(chunk_lengths)
                            
                            logger.info(f"    Taille moyenne des chunks: {avg_length:.2f} caractères")
                            logger.info(f"    Taille min/max: {min_length}/{max_length} caractères")
                            
                            # Enregistrer les chunks dans un fichier
                            if output_dir:
                                output_file = output_dir / f"chunks_{chunker_type}_{chunk_size}_{overlap}.txt"
                                with open(output_file, "w", encoding="utf-8") as f:
                                    for i, chunk in enumerate(result.chunks):
                                        f.write(f"--- CHUNK {i+1} ({len(chunk)} caractères) ---\n")
                                        f.write(chunk)
                                        f.write("\n\n")
                                logger.info(f"    Chunks enregistrés dans: {output_file}")
                        
                        # Stocker les résultats pour comparaison
                        key = f"{chunker_type}_{chunk_size}_{overlap}"
                        results[key] = {
                            "chunker_type": chunker_type,
                            "chunk_size": chunk_size,
                            "overlap": overlap,
                            "chunks_count": len(result.chunks),
                            "processing_time": processing_time,
                            "metadata": result.metadata
                        }
            
            except Exception as e:
                logger.warning(f"Chunker '{chunker_type}' non disponible ou erreur: {str(e)}")
                continue
        
        # Comparer les résultats
        if results and len(results) > 1:
            logger.info("Comparaison des résultats de chunking:")
            
            # Trier par nombre de chunks
            sorted_by_chunks = sorted(results.items(), key=lambda x: x[1]["chunks_count"])
            logger.info(f"  Plus petit nombre de chunks: {sorted_by_chunks[0][0]} ({sorted_by_chunks[0][1]['chunks_count']} chunks)")
            logger.info(f"  Plus grand nombre de chunks: {sorted_by_chunks[-1][0]} ({sorted_by_chunks[-1][1]['chunks_count']} chunks)")
            
            # Trier par temps de traitement
            sorted_by_time = sorted(results.items(), key=lambda x: x[1]["processing_time"])
            logger.info(f"  Plus rapide: {sorted_by_time[0][0]} ({sorted_by_time[0][1]['processing_time']:.2f} secondes)")
            logger.info(f"  Plus lent: {sorted_by_time[-1][0]} ({sorted_by_time[-1][1]['processing_time']:.2f} secondes)")
        
        return results
    
    except Exception as e:
        logger.exception(f"Erreur lors du test de chunking: {str(e)}")
        return None

async def test_full_processing(file_path: Path, output_dir: Path = None,
                       chunk_size: int = 1000, chunk_overlap: int = 100,
                       enable_ocr: bool = True) -> None:
    """
    Teste le traitement complet d'un document (conversion + OCR si nécessaire + chunking).
    
    Args:
        file_path: Chemin vers le document à tester
        output_dir: Répertoire de sortie pour les fichiers de résultats
        chunk_size: Taille des chunks
        chunk_overlap: Chevauchement des chunks
        enable_ocr: Activer l'OCR si nécessaire
    """
    logger.info(f"Test de traitement complet pour le document: {file_path}")
    logger.info(f"  Taille des chunks: {chunk_size}")
    logger.info(f"  Chevauchement: {chunk_overlap}")
    logger.info(f"  OCR activé: {enable_ocr}")
    
    # Créer un répertoire de sortie si nécessaire
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Obtenir le processeur de documents
        processor = await get_document_processor()
        
        # Traiter le document
        start_time = time.time()
        result = await processor.process_document(
            file_path=file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            enable_ocr=enable_ocr
        )
        processing_time = time.time() - start_time
        
        # Afficher les résultats
        logger.info(f"Résultat du traitement complet:")
        logger.info(f"  Succès: {result.success}")
        logger.info(f"  Temps de traitement: {processing_time:.2f} secondes")
        
        if result.success:
            logger.info(f"  Taille du texte extrait: {len(result.text_content)} caractères")
            logger.info(f"  Nombre de chunks: {len(result.chunks)}")
            
            # Vérifier si OCR a été appliqué
            ocr_processed = result.metadata.get("ocr_processed", False)
            logger.info(f"  OCR appliqué: {ocr_processed}")
            
            # Enregistrer les résultats dans des fichiers
            if output_dir:
                # Enregistrer le texte complet
                text_file = output_dir / f"{file_path.stem}_full.txt"
                with open(text_file, "w", encoding="utf-8") as f:
                    f.write(result.text_content)
                logger.info(f"  Texte complet enregistré dans: {text_file}")
                
                # Enregistrer les chunks
                chunks_file = output_dir / f"{file_path.stem}_chunks.txt"
                with open(chunks_file, "w", encoding="utf-8") as f:
                    for i, chunk in enumerate(result.chunks):
                        f.write(f"--- CHUNK {i+1} ({len(chunk)} caractères) ---\n")
                        f.write(chunk)
                        f.write("\n\n")
                logger.info(f"  Chunks enregistrés dans: {chunks_file}")
                
                # Enregistrer les métadonnées
                metadata_file = output_dir / f"{file_path.stem}_full_metadata.json"
                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(result.metadata, f, indent=2, default=str)
                logger.info(f"  Métadonnées enregistrées dans: {metadata_file}")
        else:
            logger.error(f"  Erreur: {result.error_message}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Erreur lors du test de traitement complet: {str(e)}")
        return None

async def test_large_file_processing(file_path: Path, output_dir: Path = None,
                             chunk_size: int = 500, batch_size: int = 10) -> None:
    """
    Teste le traitement d'un fichier volumineux avec une approche par batches.
    Particulièrement utile pour les fichiers PDF volumineux nécessitant OCR.
    
    Args:
        file_path: Chemin vers le document à tester
        output_dir: Répertoire de sortie pour les fichiers de résultats
        chunk_size: Taille des chunks
        batch_size: Nombre de chunks par batch
    """
    logger.info(f"Test de traitement pour fichier volumineux: {file_path}")
    logger.info(f"  Taille des chunks: {chunk_size}")
    logger.info(f"  Taille de batch: {batch_size}")
    
    # Créer un répertoire de sortie si nécessaire
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Obtenir le processeur de documents
        processor = await get_document_processor()
        
        # Étape 1: Conversion en texte avec OCR si nécessaire
        logger.info("Étape 1: Conversion en texte")
        start_time = time.time()
        
        # Traiter le document sans chunking d'abord
        conversion_result = await processor.process_document(
            file_path=file_path,
            enable_ocr=True,
            skip_chunking=True  # On va faire le chunking manuellement
        )
        
        conversion_time = time.time() - start_time
        logger.info(f"  Conversion terminée en {conversion_time:.2f} secondes")
        
        if not conversion_result.success:
            logger.error(f"  Erreur lors de la conversion: {conversion_result.error_message}")
            return None
        
        logger.info(f"  Taille du texte extrait: {len(conversion_result.text_content)} caractères")
        
        # Étape 2: Chunking du texte
        logger.info("Étape 2: Chunking du texte")
        chunker = await get_text_chunker(provider_name="simple")
        
        start_time = time.time()
        chunking_result = await chunker.chunk_text(
            text=conversion_result.text_content,
            max_chunk_size=chunk_size,
            overlap=chunk_size // 10  # 10% de chevauchement
        )
        
        chunking_time = time.time() - start_time
        logger.info(f"  Chunking terminé en {chunking_time:.2f} secondes")
        logger.info(f"  Nombre de chunks: {len(chunking_result.chunks)}")
        
        # Étape 3: Traitement par batches (simulation)
        logger.info("Étape 3: Traitement par batches")
        chunks = chunking_result.chunks
        batches = [chunks[i:i+batch_size] for i in range(0, len(chunks), batch_size)]
        
        logger.info(f"  Nombre de batches: {len(batches)}")
        
        # Simuler le traitement de chaque batch
        total_batches_time = 0
        for i, batch in enumerate(batches):
            logger.info(f"  Traitement du batch {i+1}/{len(batches)} ({len(batch)} chunks)")
            
            start_time = time.time()
            # Simulation du traitement (par exemple, calcul d'embeddings)
            # Dans la vie réelle, ce serait l'appel au service d'embeddings
            await asyncio.sleep(0.5)  # Simulation d'un délai de traitement
            
            batch_time = time.time() - start_time
            total_batches_time += batch_time
            
            logger.info(f"    Batch {i+1} traité en {batch_time:.2f} secondes")
            
            # Simulation de reprise sur erreur
            if i == len(batches) // 2:  # Au milieu du traitement
                logger.info("    Simulation d'une erreur de timeout")
                logger.info("    Reprise du traitement...")
        
        logger.info(f"  Traitement par batches terminé en {total_batches_time:.2f} secondes")
        
        # Enregistrer les résultats
        if output_dir:
            # Enregistrer un échantillon de chunks
            sample_file = output_dir / f"{file_path.stem}_large_sample.txt"
            with open(sample_file, "w", encoding="utf-8") as f:
                for i, chunk in enumerate(chunks[:min(10, len(chunks))]):
                    f.write(f"--- CHUNK {i+1} ({len(chunk)} caractères) ---\n")
                    f.write(chunk)
                    f.write("\n\n")
            logger.info(f"  Échantillon de chunks enregistré dans: {sample_file}")
            
            # Enregistrer les métadonnées
            metadata = {
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "text_size": len(conversion_result.text_content),
                "chunks_count": len(chunks),
                "batches_count": len(batches),
                "chunk_size": chunk_size,
                "batch_size": batch_size,
                "conversion_time": conversion_time,
                "chunking_time": chunking_time,
                "batches_time": total_batches_time,
                "total_time": conversion_time + chunking_time + total_batches_time,
                "original_metadata": conversion_result.metadata
            }
            
            metadata_file = output_dir / f"{file_path.stem}_large_metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)
            logger.info(f"  Métadonnées enregistrées dans: {metadata_file}")
        
        return {
            "success": True,
            "chunks_count": len(chunks),
            "batches_count": len(batches),
            "conversion_time": conversion_time,
            "chunking_time": chunking_time,
            "batches_time": total_batches_time,
            "total_time": conversion_time + chunking_time + total_batches_time
        }
    
    except Exception as e:
        logger.exception(f"Erreur lors du test de traitement pour fichier volumineux: {str(e)}")
        return None

async def main():
    """Fonction principale du script."""
    # Parser les arguments
    parser = argparse.ArgumentParser(description="Test du système de traitement de documents")
    parser.add_argument("--file", "-f", type=str, help="Chemin vers le document à tester")
    parser.add_argument("--output", "-o", type=str, help="Répertoire de sortie pour les résultats", default="output")
    parser.add_argument("--test", "-t", type=str, choices=["conversion", "ocr", "chunking", "full", "large"], 
                        help="Type de test à exécuter", default="full")
    parser.add_argument("--chunk-size", type=int, help="Taille des chunks pour le test", default=1000)
    parser.add_argument("--overlap", type=int, help="Chevauchement des chunks pour le test", default=100)
    parser.add_argument("--batch-size", type=int, help="Taille des batches pour le test de fichiers volumineux", default=10)
    parser.add_argument("--enable-ocr", action="store_true", help="Activer l'OCR pour les tests")
    
    args = parser.parse_args()
    
    # Vérifier les arguments
    if not args.file:
        logger.error("Aucun fichier spécifié")
        parser.print_help()
        return
    
    file_path = Path(args.file)
    if not file_path.exists():
        logger.error(f"Le fichier {file_path} n'existe pas")
        return
    
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Exécuter le test demandé
    if args.test == "conversion":
        await test_document_conversion(file_path, output_dir)
    
    elif args.test == "ocr":
        await test_document_ocr(file_path, output_dir)
    
    elif args.test == "chunking":
        # D'abord convertir le document en texte
        conversion_result = await test_document_conversion(file_path, output_dir)
        
        if conversion_result and conversion_result.success:
            # Puis tester le chunking sur le texte extrait
            await test_document_chunking(conversion_result.text_content, output_dir)
    
    elif args.test == "full":
        await test_full_processing(file_path, output_dir, args.chunk_size, args.overlap, args.enable_ocr)
    
    elif args.test == "large":
        await test_large_file_processing(file_path, output_dir, args.chunk_size, args.batch_size)

if __name__ == "__main__":
    asyncio.run(main())
