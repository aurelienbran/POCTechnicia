# Système de traitement de documents

> **ℹ️ Note ℹ️**  
> Ce document décrit le système de traitement de documents et les composants OCR.  
> Pour une documentation complète sur le tableau de bord OCR et ses fonctionnalités, consultez : [OCR_DASHBOARD_COMPLET.md](./OCR_DASHBOARD_COMPLET.md)

Ce document décrit le système de traitement de documents implémenté dans le cadre du MVP Technicia. Il inclut les composants de conversion, OCR, chunking, ainsi que l'API associée.

## Architecture du système

Le système de traitement de documents est conçu de manière modulaire avec les composants suivants :

1. **Convertisseurs de documents** : Extraction de texte à partir de différents formats
2. **Processeur OCR** : Traitement des documents numérisés
3. **Chunkers de texte** : Découpage intelligent du texte pour l'indexation
4. **Processeur de documents** : Coordination des différentes étapes
5. **API RESTful** : Exposition des fonctionnalités via des endpoints HTTP
6. **Tâches Celery** : Traitement asynchrone des documents

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Document brut  │────▶│  Convertisseur  │────▶│ Texte extrait   │
└─────────────────┘     │  (+ OCR si      │     └─────────────────┘
                        │   nécessaire)   │              │
                        └─────────────────┘              ▼
                                                ┌─────────────────┐
                                                │    Chunker      │
                                                └─────────────────┘
                                                         │
                  ┌─────────────────┐                    ▼
                  │  Indexation     │◀───────┌─────────────────┐
                  │  vectorielle    │        │     Chunks      │
                  └─────────────────┘        └─────────────────┘
```

## Prérequis techniques

### Outils OCR

Le système utilise les outils suivants pour le traitement OCR des documents numérisés :

1. **OCRmyPDF** : Installé via pip (`pip install ocrmypdf`)
2. **Tesseract OCR** : Doit être installé séparément
3. **Ghostscript** : Nécessaire pour OCRmyPDF
4. **Poppler** : Nécessaire pour OCRmyPDF

### Configuration des chemins

Les chemins vers ces outils sont configurés via des variables d'environnement :

```
TESSERACT_PATH=C:\Programs\Tesseract-OCR
POPPLER_PATH=C:\Programs\poppler\bin
GHOSTSCRIPT_PATH=C:\Programs\gs\bin
```

## Utilisation du système

### Via l'API REST

L'API de traitement de documents est disponible aux endpoints suivants :

- `/api/documents/process` : Traitement d'un document
- `/api/documents/batch-process` : Traitement d'un lot de documents
- `/api/documents/process-and-index` : Traitement et indexation d'un document

Consultez la [documentation complète de l'API](api/API_DOCUMENT_PROCESSING.md) pour plus de détails.

### Via le processeur de documents directement

```python
from app.core.file_processing.document_processor import get_document_processor

# Obtenir une instance du processeur
processor = await get_document_processor()

# Traiter un document
result = await processor.process_document(
    file_path="chemin/vers/document.pdf",
    chunk_size=1000,
    chunk_overlap=100,
    enable_ocr=True
)

# Accéder aux résultats
if result.success:
    print(f"Texte extrait: {result.text_content[:100]}...")
    print(f"Nombre de chunks: {len(result.chunks)}")
    print(f"Métadonnées: {result.metadata}")
else:
    print(f"Erreur: {result.error_message}")
```

## Traitement des fichiers volumineux

Pour les fichiers PDF volumineux (>28 Mo) nécessitant un OCR, le système utilise une approche par batches pour éviter les timeouts :

1. **Conversion initiale** : Le document est d'abord converti en texte (avec OCR si nécessaire)
2. **Découpage en chunks** : Le texte est découpé en chunks de taille appropriée
3. **Traitement par batches** : Les chunks sont traités par lots plus petits
4. **Reprise sur erreur** : En cas d'échec d'un batch, le traitement peut reprendre à partir du dernier batch réussi

Cette approche est particulièrement utile lors de la génération d'embeddings pour de grands documents, où le temps de traitement peut dépasser les limites de timeout des services externes.

## Tests et diagnostic

### Scripts de diagnostic

Le script `scripts/diagnose_ocr.py` permet de vérifier la configuration des outils OCR :

```bash
python scripts/diagnose_ocr.py
```

Ce script vérifie :
- La présence des outils nécessaires (Tesseract, Ghostscript, Poppler)
- Le bon fonctionnement de OCRmyPDF
- La reconnaissance de texte avec un exemple simple

### Script de test pour le traitement de documents

Le script `scripts/test_document_processing.py` permet de tester différentes fonctionnalités du système :

```bash
# Test complet
python scripts/test_document_processing.py --file chemin/vers/document.pdf --test full --enable-ocr

# Test de conversion seulement
python scripts/test_document_processing.py --file chemin/vers/document.pdf --test conversion

# Test OCR seulement
python scripts/test_document_processing.py --file chemin/vers/document.pdf --test ocr

# Test chunking seulement
python scripts/test_document_processing.py --file chemin/vers/document.pdf --test chunking

# Test pour fichiers volumineux avec approche par batches
python scripts/test_document_processing.py --file chemin/vers/document_volumineux.pdf --test large --chunk-size 500 --batch-size 10
```

## Tests unitaires

Les tests unitaires pour le système de traitement de documents sont disponibles dans les dossiers suivants :

- `tests/unit/file_processing/test_document_processor.py`
- `tests/unit/file_processing/test_chunking.py`
- `tests/unit/file_processing/test_conversion.py`

Pour exécuter les tests :

```bash
pytest tests/unit/file_processing/
```

## Exemple d'intégration frontend

Un exemple d'interface utilisateur pour le traitement de documents est disponible dans :

- `examples/document_processing_client.html`

Cette interface permet de télécharger des documents, configurer les options de traitement, et visualiser les résultats.

## Notes d'implémentation

### Extensibilité du système

Le système est conçu pour être facilement extensible :

1. **Nouveaux formats** : Ajoutez de nouveaux convertisseurs dans `app/core/file_processing/conversion/`
2. **Stratégies de chunking** : Implémentez de nouvelles stratégies dans `app/core/file_processing/chunking/`
3. **Méthodes OCR** : Étendez les capacités OCR dans `app/core/file_processing/ocr/`

### Performance

- Les opérations coûteuses sont exécutées de manière asynchrone via Celery
- Le traitement par batches permet de gérer efficacement les grands documents
- La mise en cache des résultats intermédiaires évite les calculs redondants
