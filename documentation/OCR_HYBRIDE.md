# Système Hybride d'OCR - Documentation Technique

> **ℹ️ Note ℹ️**  
> Ce document technique détaille l'implémentation interne du système hybride d'OCR.  
> Pour une vue complète du tableau de bord OCR et de ses fonctionnalités, consultez également : [OCR_DASHBOARD_COMPLET.md](./OCR_DASHBOARD_COMPLET.md)

## Vue d'ensemble

Le système hybride d'OCR est conçu pour optimiser le traitement des documents techniques en sélectionnant intelligemment la méthode d'OCR la plus appropriée en fonction des caractéristiques du document. Il intègre également un mécanisme robuste de gestion d'erreurs et un système de traitement par lots pour gérer efficacement les documents volumineux.

## Architecture

Le système se compose de quatre composants principaux :

1. **Sélecteur intelligent d'OCR** (`ocr_selector.py`)
2. **Métriques de qualité** (`quality_metrics.py`)
3. **Gestion d'erreurs** (`error_handling.py`)
4. **Traitement par lots** (`ocr_queue.py`)

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│   Sélecteur    │────▶│    Moteur      │────▶│   Métriques    │
│     d'OCR      │     │     OCR        │     │   de Qualité   │
└────────────────┘     └────────────────┘     └────────────────┘
         │                     │                      │
         │                     │                      │
         │                     ▼                      │
         │              ┌────────────────┐            │
         └─────────────▶│    Gestion     │◀───────────┘
                        │   d'Erreurs    │
                        └────────────────┘
                               │
                               ▼
                        ┌────────────────┐
                        │  Traitement    │
                        │   par Lots     │
                        └────────────────┘
```

## Composants

### 1. Sélecteur Intelligent d'OCR (`ocr_selector.py`)

Ce composant analyse les caractéristiques du document (taille, complexité, type) et sélectionne la méthode d'OCR la plus appropriée.

#### Caractéristiques principales :

- Analyse automatique de la complexité du document
- Support pour plusieurs moteurs OCR (Tesseract, Document AI, Vision AI)
- Prise de décision basée sur des métriques prédéfinies et l'apprentissage des performances passées
- Fallback automatique en cas d'échec de la méthode primaire

#### Utilisation :

```python
from app.core.file_processing.ocr.ocr_selector import OCRSelector

selector = OCRSelector()
await selector.initialize()

# Analyse et sélection du meilleur moteur OCR
best_provider, confidence = await selector.select_ocr_method("path/to/document.pdf")
print(f"Meilleur moteur OCR : {best_provider} (confiance: {confidence})")
```

### 2. Métriques de Qualité (`quality_metrics.py`)

Ce module fournit des outils pour évaluer la qualité des résultats OCR et comparer les performances des différents moteurs OCR.

#### Caractéristiques principales :

- Calcul de scores de confiance pour les résultats OCR
- Détection des erreurs courantes (caractères mal reconnus, mots manquants)
- Comparaison automatique des résultats de différents moteurs OCR
- Génération de rapports de performance

#### Utilisation :

```python
from app.core.file_processing.ocr.quality_metrics import OCRQualityEvaluator

evaluator = OCRQualityEvaluator()

# Évaluer la qualité d'un résultat OCR
score = await evaluator.evaluate_result(ocr_result)
print(f"Score de qualité : {score.overall_score}")

# Comparer deux résultats OCR
comparison = await evaluator.compare_results(result1, result2)
print(f"Meilleur résultat : {comparison.best_result}")
```

### 3. Gestion d'Erreurs (`error_handling.py`)

Ce composant fournit un système robuste pour la gestion des erreurs lors des tâches OCR, permettant la reprise des tâches interrompues et la gestion des timeouts.

#### Caractéristiques principales :

- Système de checkpoints pour sauvegarder l'état des tâches
- Mécanisme de reprise après erreur ou timeout
- Classification intelligente des erreurs
- Stratégies de retry adaptatives

#### Utilisation :

```python
from app.core.tasks.error_handling import TaskManager, with_error_handling

task_manager = TaskManager()

# Créer une nouvelle tâche
task_id = task_manager.register_task("ocr_processing", document_path="path/to/document.pdf")

# Utiliser le décorateur pour la gestion d'erreurs
@with_error_handling(max_retries=3, timeout=600)
async def process_document(document_path, task_id):
    # Traitement du document
    # ...
    
    # Créer un checkpoint
    task_manager.create_checkpoint(task_id, state={"page": current_page})
    
    # Mettre à jour la progression
    task_manager.update_task_progress(task_id, progress=0.5)
```

### 4. Traitement par Lots (`ocr_queue.py`)

Ce module permet de traiter efficacement les documents volumineux en les divisant en chunks et en les traitant en parallèle.

#### Caractéristiques principales :

- Division automatique des documents en chunks de taille configurable
- Traitement parallèle des chunks via Celery
- Fusion automatique des résultats
- Intégration avec le système de gestion d'erreurs pour une reprise fiable

#### Utilisation :

```python
from app.core.tasks.ocr_queue import OCRQueueManager, process_document_chunked

# Utilisation synchrone
queue_manager = OCRQueueManager({"chunk_size": 5})
result = await queue_manager.process_document_in_chunks(
    "path/to/large_document.pdf",
    ocr_provider="auto",
    language="fra"
)

# Utilisation asynchrone avec Celery
task_id = process_document_chunked(
    "path/to/large_document.pdf",
    chunk_size=5,
    ocr_provider="auto",
    language="fra"
)
print(f"Tâche Celery lancée avec ID: {task_id}")
```

## Flux de Traitement

1. **Réception d'un document**
   - Le document est reçu par le système
   - Les caractéristiques du document sont analysées

2. **Sélection de la méthode OCR**
   - Le sélecteur intelligent détermine la méthode OCR la plus appropriée
   - La confiance de la sélection est calculée

3. **Traitement OCR**
   - Si le document est volumineux, il est divisé en chunks
   - Chaque chunk est traité par la méthode OCR sélectionnée
   - Les checkpoints sont créés à intervalles réguliers

4. **Gestion des erreurs**
   - En cas d'erreur ou de timeout, le système tente de reprendre à partir du dernier checkpoint
   - Si nécessaire, une méthode OCR alternative est utilisée

5. **Évaluation de la qualité**
   - Les résultats OCR sont évalués pour déterminer leur qualité
   - Si la qualité est insuffisante, un traitement supplémentaire peut être appliqué

6. **Fusion des résultats**
   - Si le document a été traité par chunks, les résultats sont fusionnés
   - Le document final est renvoyé

## Configuration

La configuration du système se fait via les paramètres dans `app/config/settings.py`. Voici les principaux paramètres :

```python
# Paramètres OCR
OCR_PROVIDER_DEFAULT = "tesseract"  # Provider par défaut
OCR_TIMEOUT = 600  # Timeout en secondes
OCR_MAX_RETRIES = 3  # Nombre maximal de tentatives

# Paramètres de chunking
OCR_CHUNK_SIZE = 5  # Nombre de pages par chunk
OCR_CHUNK_TIMEOUT = 300  # Timeout par chunk en secondes

# Chemins des outils
TESSERACT_PATH = "/usr/bin/tesseract"  # Chemin vers Tesseract
POPPLER_PATH = "/usr/bin/pdftoppm"  # Chemin vers Poppler
GHOSTSCRIPT_PATH = "/usr/bin/gs"  # Chemin vers Ghostscript
```

## Dépendances

- **PyMuPDF** : Manipulation des fichiers PDF
- **Tesseract** : Moteur OCR principal
- **OCRmyPDF** : Traitement OCR avancé pour PDF
- **Pillow** : Traitement d'images
- **NumPy** : Calculs numériques
- **Celery** : Traitement asynchrone

## Exemples Concrets

### Exemple 1 : Traitement d'un document simple

```python
from app.core.file_processing.ocr.factory import get_ocr_processor

# Obtenir un processeur OCR automatiquement sélectionné
processor = await get_ocr_processor(provider_name="auto")

# Traiter le document
result = await processor.process_document("path/to/document.pdf", language="fra")

# Afficher le texte extrait
print(result.text_content)
```

### Exemple 2 : Traitement d'un document volumineux

```python
from app.core.tasks.ocr_queue import process_document_chunked

# Lancer le traitement par chunks
task_id = process_document_chunked(
    "path/to/large_document.pdf",
    chunk_size=10,
    ocr_provider="tesseract",
    language="fra"
)

# Le traitement continue en arrière-plan via Celery
```

## Bonnes Pratiques

1. **Utilisation du sélecteur automatique**
   - Pour la plupart des cas, utilisez `provider_name="auto"` pour permettre au système de choisir la meilleure méthode OCR.

2. **Adaptation de la taille des chunks**
   - Pour les documents très volumineux, augmentez la taille des chunks pour réduire les frais généraux.
   - Pour les documents complexes, réduisez la taille des chunks pour limiter le risque de timeout.

3. **Gestion des erreurs**
   - Utilisez toujours le décorateur `with_error_handling` pour les fonctions de traitement OCR.
   - Créez régulièrement des checkpoints pour permettre une reprise efficace en cas d'erreur.

4. **Surveillance des performances**
   - Surveillez régulièrement les métriques de qualité pour identifier les cas où l'OCR échoue ou produit des résultats de mauvaise qualité.

## Résolution des Problèmes Courants

| Problème | Cause Possible | Solution |
|----------|----------------|----------|
| Timeout lors du traitement | Document trop volumineux | Réduire la taille des chunks ou augmenter le timeout |
| Qualité OCR insuffisante | Mauvaise qualité d'image | Essayer un prétraitement d'image ou une méthode OCR alternative |
| Erreur "Out of memory" | Document trop grand pour la RAM disponible | Réduire la taille des chunks et le parallélisme |
| Échec de fusion des chunks | Corruption de fichiers temporaires | Vérifier l'espace disque et les permissions |

## Conclusion

Le système hybride d'OCR offre une solution robuste et flexible pour le traitement des documents techniques, en combinant la sélection intelligente des méthodes OCR, la gestion efficace des erreurs et le traitement par lots. Il est conçu pour gérer efficacement les documents de toutes tailles, avec une attention particulière pour les documents volumineux et complexes.
