"""Tests de performance pour le POC RAG."""
import os
import time
import psutil
import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict
import logging
from app.core.pdf_processor import PDFProcessor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.process = psutil.Process()
        self.test_files_dir = Path(__file__).parent / "test_files"
        self.pdf_processor = PDFProcessor(temp_dir=Path("temp"))
        
    def find_pdf_files(self, test_dir="tests/performance/test_files"):
        """Trouve tous les fichiers PDF dans le dossier de test."""
        pdf_files = []
        
        if not os.path.exists(test_dir):
            logger.error(f"❌ Le dossier {test_dir} n'existe pas!")
            return []
        
        for file in os.listdir(test_dir):
            if file.lower().endswith('.pdf'):
                file_path = os.path.join(test_dir, file)
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                pdf_files.append({
                    "path": file_path,
                    "name": file,
                    "size": size_mb
                })
        
        # Trier par taille croissante
        pdf_files.sort(key=lambda x: x["size"])
        
        if pdf_files:
            logger.info(f"Trouvé {len(pdf_files)} fichiers PDF:")
            for pdf in pdf_files:
                logger.info(f"  - {pdf['name']} ({pdf['size']:.2f} MB)")
            logger.info("")
        else:
            logger.error("❌ Aucun fichier PDF trouvé!")
            
        return pdf_files
        
    async def measure_upload_performance(self, pdf_path: str):
        """Mesure les performances d'upload d'un fichier PDF."""
        filename = os.path.basename(pdf_path)
        size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        
        logger.info(f"\n📄 Test du fichier: {filename} ({size_mb:.2f} MB)")
        
        try:
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            # Upload du fichier
            async with aiohttp.ClientSession() as session:
                with open(pdf_path, 'rb') as f:
                    form = aiohttp.FormData()
                    form.add_field('file', f, filename=filename)
                    
                    async with session.post(f"{self.base_url}/api/v1/documents", data=form) as response:
                        if response.status != 200:
                            error_msg = await response.text()
                            logger.error(f"❌ Erreur lors de l'upload: {error_msg}")
                            return None
                        
                        result = await response.json()
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            processing_time = end_time - start_time
            memory_used = end_memory - start_memory
            speed = size_mb / processing_time if processing_time > 0 else 0
            
            logger.info(f"  ⏱️  Temps de traitement: {processing_time:.2f}s")
            logger.info(f"  💾 Mémoire utilisée: {memory_used:.2f}MB")
            logger.info(f"  📈 Vitesse: {speed:.2f} MB/s")
            if result:
                logger.info(f"  📊 Chunks traités: {result.get('chunks_processed', 0)}")
                logger.info(f"  📊 Chunks indexés: {result.get('chunks_indexed', 0)}")
            
            test_result = {
                "filename": filename,
                "size_mb": size_mb,
                "processing_time": processing_time,
                "memory_used": memory_used,
                "speed": speed,
                "chunks_processed": result.get("chunks_processed", 0) if result else 0,
                "chunks_indexed": result.get("chunks_indexed", 0) if result else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            # Ajouter le résultat à la liste des résultats
            self.results.append(test_result)
            
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du test: {str(e)}")
            return None
    
    async def measure_query_performance(self, question: str, num_queries: int = 10):
        """Mesure les performances des requêtes."""
        logger.info(f"\n🔍 Test des performances des requêtes ({num_queries} requêtes)...")
        
        query_times = []
        memory_usage = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_queries):
                start_memory = self.process.memory_info().rss / (1024 * 1024)
                start_time = time.time()
                
                try:
                    async with session.post(
                        f"{self.base_url}/api/v1/query",
                        json={"question": question, "k": 4}
                    ) as response:
                        if response.status != 200:
                            raise Exception(f"Erreur HTTP {response.status}")
                        await response.json()
                    
                    end_time = time.time()
                    end_memory = self.process.memory_info().rss / (1024 * 1024)
                    
                    query_time = end_time - start_time
                    memory_used = end_memory - start_memory
                    
                    query_times.append(query_time)
                    memory_usage.append(memory_used)
                    
                    logger.info(f"  Requête {i+1}/{num_queries}: {query_time:.2f}s")
                    
                except Exception as e:
                    logger.error(f"❌ Erreur lors de la requête {i+1}: {str(e)}")
                    continue
        
        if not query_times:
            logger.error("❌ Aucune requête n'a réussi!")
            return None
            
        result = {
            'timestamp': datetime.now().isoformat(),
            'avg_query_time_s': sum(query_times) / len(query_times),
            'min_query_time_s': min(query_times),
            'max_query_time_s': max(query_times),
            'avg_memory_mb': sum(memory_usage) / len(memory_usage),
            'num_queries': len(query_times),
            'successful_queries': len(query_times),
            'failed_queries': num_queries - len(query_times)
        }
        
        logger.info(f"  ⏱️  Temps moyen: {result['avg_query_time_s']:.2f}s")
        logger.info(f"  ⚡ Temps min/max: {result['min_query_time_s']:.2f}s / {result['max_query_time_s']:.2f}s")
        logger.info(f"  💾 Mémoire moyenne: {result['avg_memory_mb']:.2f}MB")
        
        return result
    
    async def wait_for_indexing(self, max_retries=60, delay=10):
        """Attend que l'indexation soit terminée."""
        logger.info("\n⏳ Attente de la fin de l'indexation...")
        
        connection_errors = 0
        max_connection_errors = 3
        previous_stats = None
        stable_count = 0
        required_stable_checks = 3
        
        for i in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base_url}/api/v1/stats") as response:
                        if response.status == 200:
                            connection_errors = 0
                            stats = await response.json()
                            
                            # Vérifier si une erreur s'est produite pendant l'indexation
                            if stats.get("error_occurred", False):
                                logger.error(f"❌ Erreur détectée pendant l'indexation: {stats.get('error_message', 'Erreur inconnue')}")
                                return False
                            
                            # Vérifier la progression
                            current_stats = {
                                "processed_files": stats.get("processed_files", 0),
                                "indexed_chunks": stats.get("indexed_chunks", 0),
                                "vectors_count": stats.get("vectors_count", 0)
                            }
                            
                            # L'indexation est considérée comme terminée si :
                            # 1. Le statut indique que ce n'est plus en cours ET
                            # 2. Les statistiques sont stables pendant plusieurs vérifications ET
                            # 3. Le nombre de fichiers traités correspond au total attendu
                            if previous_stats == current_stats:
                                stable_count += 1
                            else:
                                stable_count = 0
                                previous_stats = current_stats
                            
                            if (not stats.get("indexing_in_progress", True) and 
                                stable_count >= required_stable_checks and
                                stats.get("processed_files", 0) == stats.get("total_files", 0)):
                                
                                logger.info("✅ Indexation terminée")
                                logger.info(f"  - Fichiers traités: {stats.get('processed_files', 0)}/{stats.get('total_files', 0)}")
                                logger.info(f"  - Chunks indexés: {stats.get('indexed_chunks', 0)}/{stats.get('total_chunks', 0)}")
                                logger.info(f"  - Vecteurs dans Qdrant: {stats.get('vectors_count', 0)}")
                                return True
                            
                            # Afficher la progression
                            logger.info(f"⏳ En attente... ({i+1}/{max_retries})")
                            logger.info(f"  - Fichiers traités: {stats.get('processed_files', 0)}/{stats.get('total_files', 0)}")
                            logger.info(f"  - Chunks indexés: {stats.get('indexed_chunks', 0)}/{stats.get('total_chunks', 0)}")
                            logger.info(f"  - Stabilité: {stable_count}/{required_stable_checks}")
                            
                        else:
                            logger.error(f"❌ Erreur HTTP {response.status}")
                            connection_errors += 1
                
                if connection_errors >= max_connection_errors:
                    logger.error(f"❌ Trop d'erreurs de connexion consécutives ({connection_errors})")
                    return False
                    
                await asyncio.sleep(delay)
                
            except Exception as e:
                connection_errors += 1
                logger.error(f"❌ Erreur inattendue: {str(e)}")
                if connection_errors >= max_connection_errors:
                    return False
                await asyncio.sleep(delay)
        
        logger.error(f"❌ Délai d'attente dépassé après {max_retries} tentatives")
        return False

    async def process_pdf_directly(self, pdf_path: str):
        """Traite directement un fichier PDF avec PDFProcessor."""
        filename = os.path.basename(pdf_path)
        size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        
        logger.info(f"\n📄 Test du fichier: {filename} ({size_mb:.2f} MB)")
        
        try:
            start_time = time.time()
            start_memory = self.process.memory_info().rss / (1024 * 1024)
            
            # Traitement du PDF
            chunks = []
            async for chunk in self.pdf_processor.process_pdf(Path(pdf_path)):
                chunks.append(chunk)
            
            end_time = time.time()
            end_memory = self.process.memory_info().rss / (1024 * 1024)
            
            processing_time = end_time - start_time
            memory_used = end_memory - start_memory
            speed = size_mb / processing_time if processing_time > 0 else 0
            
            logger.info(f"  ⏱️  Temps de traitement: {processing_time:.2f}s")
            logger.info(f"  💾 Mémoire utilisée: {memory_used:.2f}MB")
            logger.info(f"  📈 Vitesse: {speed:.2f} MB/s")
            logger.info(f"  📊 Chunks générés: {len(chunks)}")
            
            # Afficher un aperçu des chunks
            logger.info("\n📝 Aperçu des chunks générés:")
            for i, chunk in enumerate(chunks[:3], 1):
                preview = chunk[:200] + "..." if len(chunk) > 200 else chunk
                logger.info(f"\nChunk {i}:\n{preview}")
            
            if len(chunks) > 3:
                logger.info(f"\n... et {len(chunks) - 3} autres chunks")
            
            return {
                "filename": filename,
                "size_mb": size_mb,
                "processing_time": processing_time,
                "memory_used": memory_used,
                "speed_mbs": speed,
                "chunks_count": len(chunks),
                "avg_chunk_size": sum(len(c) for c in chunks) / len(chunks) if chunks else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement: {str(e)}")
            return None
    
    def generate_report(self, output_dir="performance_reports"):
        """Génère un rapport de performance avec graphiques."""
        if not self.results:
            logger.error("❌ Aucun résultat à analyser!")
            return
            
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        logger.info("\n📊 Génération du rapport...")
        
        # Convertir les résultats en DataFrame
        df = pd.DataFrame(self.results)
        
        # Graphique 1: Taille vs Temps de traitement
        plt.figure(figsize=(10, 6))
        plt.scatter(df['size_mb'], df['processing_time'])
        plt.xlabel('Taille du fichier (MB)')
        plt.ylabel('Temps de traitement (s)')
        plt.title('Taille du fichier vs Temps de traitement')
        plt.grid(True)
        plt.savefig(output_dir / 'size_vs_time.png')
        plt.close()
        
        # Graphique 2: Taille vs Mémoire utilisée
        plt.figure(figsize=(10, 6))
        plt.scatter(df['size_mb'], df['memory_used'])
        plt.xlabel('Taille du fichier (MB)')
        plt.ylabel('Mémoire utilisée (MB)')
        plt.title('Taille du fichier vs Mémoire utilisée')
        plt.grid(True)
        plt.savefig(output_dir / 'size_vs_memory.png')
        plt.close()
        
        # Graphique 3: Vitesse de traitement
        plt.figure(figsize=(10, 6))
        plt.plot(df['size_mb'], df['speed_mbs'], marker='o')
        plt.xlabel('Taille du fichier (MB)')
        plt.ylabel('Vitesse de traitement (MB/s)')
        plt.title('Vitesse de traitement selon la taille')
        plt.grid(True)
        plt.savefig(output_dir / 'processing_speed.png')
        plt.close()
        
        # Sauvegarder les résultats bruts
        df.to_csv(output_dir / 'performance_results.csv', index=False)
        
        # Générer un rapport HTML
        html_report = f"""
        <html>
        <head>
            <title>Rapport de Performance - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                img {{ max-width: 100%; height: auto; margin: 20px 0; }}
                .success {{ color: green; }}
                .warning {{ color: orange; }}
                .error {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>Rapport de Performance</h1>
            
            <h2>Résumé</h2>
            <table>
                <tr>
                    <th>Métrique</th>
                    <th>Valeur</th>
                    <th>Statut</th>
                </tr>
                <tr>
                    <td>Nombre de fichiers testés</td>
                    <td>{len(df)}</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td>Temps de traitement moyen</td>
                    <td>{df['processing_time'].mean():.2f} s</td>
                    <td class="{self._get_status_class(df['processing_time'].mean(), 5)}">
                        {self._get_status_text(df['processing_time'].mean(), 5, "< 5s")}
                    </td>
                </tr>
                <tr>
                    <td>Mémoire moyenne utilisée</td>
                    <td>{df['memory_used'].mean():.2f} MB</td>
                    <td class="{self._get_status_class(df['memory_used'].mean(), 1024)}">
                        {self._get_status_text(df['memory_used'].mean(), 1024, "< 1GB")}
                    </td>
                </tr>
                <tr>
                    <td>Plus grand fichier traité</td>
                    <td>{df['size_mb'].max():.2f} MB</td>
                    <td class="{self._get_status_class(df['size_mb'].max(), 150)}">
                        {self._get_status_text(df['size_mb'].max(), 150, "< 150MB")}
                    </td>
                </tr>
                <tr>
                    <td>Vitesse moyenne de traitement</td>
                    <td>{df['speed_mbs'].mean():.2f} MB/s</td>
                    <td>-</td>
                </tr>
            </table>
            
            <h2>Graphiques</h2>
            <img src="size_vs_time.png" alt="Taille vs Temps">
            <img src="size_vs_memory.png" alt="Taille vs Mémoire">
            <img src="processing_speed.png" alt="Vitesse de traitement">
            
            <h2>Détails par fichier</h2>
            {df.to_html()}
        </body>
        </html>
        """
        
        with open(output_dir / 'report.html', 'w', encoding='utf-8') as f:
            f.write(html_report)
            
        logger.info(f"✅ Rapport généré dans le dossier {output_dir}")
    
    def _get_status_class(self, value, threshold):
        """Retourne la classe CSS selon le statut."""
        if value <= threshold * 0.7:  # < 70% du seuil
            return "success"
        elif value <= threshold:  # < 100% du seuil
            return "warning"
        else:  # > seuil
            return "error"
    
    def _get_status_text(self, value, threshold, criteria):
        """Retourne le texte de statut."""
        if value <= threshold * 0.7:
            return f"✅ OK ({criteria})"
        elif value <= threshold:
            return f"⚠️ Limite ({criteria})"
        else:
            return f"❌ Dépassé ({criteria})"

async def main():
    """Fonction principale pour exécuter les tests de performance."""
    try:
        test = PerformanceTest()
        
        # Liste des fichiers à tester
        pdf_files = [
            "D:/Projets/POC TECHNICIA/tests/performance/test_files/fe.pdf",
            "D:/Projets/POC TECHNICIA/tests/performance/test_files/el.pdf",
            "D:/Projets/POC TECHNICIA/tests/performance/test_files/LJ70_RJ70_chassis_body.pdf"
        ]
        
        logger.info("🚀 Démarrage des tests de performance...")
        
        # Tester chaque fichier
        for pdf_path in pdf_files:
            if not os.path.exists(pdf_path):
                logger.error(f"❌ Le fichier {pdf_path} n'existe pas!")
                continue
                
            # Test de traitement direct
            result = await test.process_pdf_directly(pdf_path)
            if result:
                # Sauvegarder les résultats
                test.results.append(result)
        
        # Générer les graphiques avec tous les résultats
        if test.results:
            test.generate_report()
            
        logger.info("✅ Tests terminés!")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors des tests: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️ Tests interrompus par l'utilisateur")
    except Exception as e:
        logger.error(f"\n❌ Erreur lors des tests: {str(e)}")
