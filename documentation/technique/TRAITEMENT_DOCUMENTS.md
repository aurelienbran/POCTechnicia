# Système de traitement de documents et extraction de haute qualité

> **ℹ️ Note importante ℹ️**  
> Ce document technique unifié décrit l'architecture complète du système de traitement de documents dans le projet Technicia, y compris les composants actuels et les améliorations planifiées pour l'extraction de haute qualité.
>
> Dernière mise à jour : 1 avril 2025

## 1. Introduction et objectifs

### 1.1 Objectif du système

Le système de traitement de documents Technicia vise à fournir une extraction de données de haute qualité à partir de documents techniques pour alimenter le moteur de RAG (Retrieval-Augmented Generation) utilisé par les techniciens sur le terrain. Il doit traiter efficacement différents types de documents, notamment :

- Documents numérisés de qualité variable
- Schémas techniques et diagrammes
- Documents contenant des tableaux complexes
- Documents avec formules et symboles techniques
- Documents multilingues

### 1.2 Critères de succès

Les critères de qualité pour ce système sont :
- Taux de reconnaissance de texte > 98% pour les documents de qualité standard
- Taux de reconnaissance de symboles techniques > 95%
- Précision dans l'extraction de tableaux > 97%
- Préservation de la structure logique des documents > 90%

## 2. Architecture du système

### 2.1 Vue d'ensemble

Le système de traitement de documents est conçu de manière modulaire avec les composants suivants :

```
┌─────────────────┐     ┌───────────────────────┐     ┌─────────────────┐
│  Document brut  │────▶│ OCRQueueManager       │────▶│ Texte extrait   │
└─────────────────┘     │ Document Analyzer      │     └─────────────────┘
                        │ Processeurs OCR        │              │
                        │ (+ Processeurs         │              ▼
                        │  spécialisés)          │     ┌─────────────────┐
                        └───────────────────────┘     │    Chunker       │
                                                      └─────────────────┘
                                                               │
                        ┌─────────────────┐                    ▼
                        │  Indexation     │◀───────┌─────────────────┐
                        │  vectorielle    │        │     Chunks      │
                        └─────────────────┘        └─────────────────┘
```

### 2.2 Composants principaux

1. **File d'attente OCR** : Gestion des tâches avec priorité et reprise
2. **Analyseur de documents** : Détection du type, de la qualité et de la complexité
3. **Processeurs OCR et spécialisés** :
   - OCRmyPDF pour les documents PDF simples
   - Tesseract Direct pour les conversions d'images
   - Document AI pour les documents complexes
   - Vision AI pour l'analyse d'images et schémas
   - Processeurs spécialisés pour tableaux, formules, etc.
4. **Chunkers** : Découpage intelligent du texte pour l'indexation
5. **Orchestrateur** : Coordination des différents processeurs et fusion des résultats
6. **Système de validation** : Vérification de la qualité et boucle de rétroaction

## 3. État actuel du système

### 3.1 Architecture implémentée

Le système actuel repose sur une architecture hybride qui utilise plusieurs processeurs OCR :

```
Document → OCRQueueManager → OCR Selector → OCR Processor (OCRmyPDF/Tesseract/Document AI) → Chunker → RAG Indexation
```

Les principaux composants implémentés sont :
- **OCRQueueManager** : Gestion des tâches OCR avec priorité
- **OCR Selector** : Sélection du processeur OCR approprié selon le type de document
- **OCR Processors** : 
  - OCRmyPDF pour les documents PDF simples
  - Tesseract Direct pour les conversions d'images
  - Document AI pour les documents complexes
- **Vision AI Service** : Analyse complémentaire des images et schémas (service distinct)
- **Chunker de base** : Découpage des documents en chunks pour indexation

### 3.2 Limitations identifiées

1. **Intégration limitée de Vision AI**
   - Vision AI est actuellement un service isolé, non intégré dans le pipeline principal
   - Sous-utilisation du potentiel de Vision AI pour les schémas techniques

2. **Absence de mécanisme d'amélioration itérative**
   - Aucun processus pour retraiter automatiquement les documents mal reconnus
   - Pas de feedback sur la qualité de l'extraction

3. **Traitement générique des documents**
   - Pas de processeurs spécialisés pour les contenus techniques spécifiques
   - Traitement uniforme des tableaux, textes et schémas

4. **Chunking basé sur la taille**
   - Découpage principalement basé sur la longueur du texte
   - Risque de perte de contexte pour les informations techniques

## 4. Architecture cible pour l'extraction de haute qualité

L'architecture cible propose une approche plus sophistiquée :

```
Document 
  ↓
OCRQueueManager 
  ↓
Document Analyzer ── ┬── Type Document ──┬─→ OCRmyPDF/Tesseract → Extraction texte standard
                     ├── Qualité         ├─→ Document AI       → Extraction structurée
                     ├── Complexité      ├─→ Vision AI         → Analyse d'images
                     └── Contenu         └─→ Processeurs spécialisés (tableaux, équations)
                       ↓
                  Orchestrateur d'extraction
                       ↓
                  Validation qualité et feedback
                       ↓
                  Chunking intelligent contextuel
                       ↓
                  RAG Indexation enrichie
```

### 4.1 Nouveaux composants planifiés

1. **Orchestrateur d'extraction**
   - Coordonne l'utilisation de plusieurs processeurs sur un même document
   - Fusionne les résultats des différents processeurs
   - Applique des règles de priorité selon la fiabilité des extractions

2. **Système de validation qualité**
   - Évalue la qualité des extractions selon des métriques multicritères
   - Identifie les segments à faible confiance
   - Déclenche des retraitements ciblés si nécessaire

3. **Processeurs spécialisés**
   - Extracteur de tableaux et données structurées
   - Processeur d'équations et formules techniques
   - Analyseur de schémas avec reconnaissance de symboles

4. **Chunking intelligent**
   - Adapte le chunking selon le type de contenu
   - Préserve les relations entre les éléments connexes
   - Maintient le contexte des informations techniques

## 5. Prérequis techniques

### 5.1 Outils OCR

Le système utilise les outils suivants pour le traitement OCR des documents numérisés :

1. **OCRmyPDF** : Installé via pip (`pip install ocrmypdf`)
2. **Tesseract OCR** : Doit être installé séparément
3. **Ghostscript** : Nécessaire pour OCRmyPDF
4. **Poppler** : Nécessaire pour OCRmyPDF

### 5.2 Services cloud

Pour les fonctionnalités avancées, le système s'appuie sur deux services Google Cloud :

1. **Google Cloud Document AI** : Service de traitement et d'extraction de documents
2. **Google Cloud Vision AI** : Service d'analyse et de reconnaissance d'images

### 5.3 Configuration des chemins

Les chemins vers ces outils sont configurés via des variables d'environnement :

```
TESSERACT_PATH=C:\Programs\Tesseract-OCR
POPPLER_PATH=C:\Programs\poppler\bin
GHOSTSCRIPT_PATH=C:\Programs\gs\bin
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

## 6. Utilisation du système

### 6.1 Via l'API REST

L'API de traitement de documents est disponible aux endpoints suivants :

- `/api/documents/process` : Traitement d'un document
- `/api/documents/batch-process` : Traitement d'un lot de documents
- `/api/documents/process-and-index` : Traitement et indexation d'un document

Consultez la [documentation complète de l'API](../api/API_DOCUMENT_PROCESSING.md) pour plus de détails.

### 6.2 Via le processeur de documents directement

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

## 7. Plan d'implémentation pour l'extraction de haute qualité

### 7.1 Phase 1 : Intégration complète de Vision AI

1. **Développement d'un processeur OCR basé sur Vision AI**
   - Implémentation dans `app/core/file_processing/ocr/vision_ai_processor.py`
   - Intégration dans la factory OCR existante
   - Ajout des règles de sélection dans l'OCR Selector

2. **Système d'orchestration Document AI + Vision AI**
   - Nouveau module `app/core/file_processing/orchestration/hybrid_processor.py`
   - Gestion parallèle des traitements Document AI et Vision AI
   - Fusion intelligente des résultats

3. **Détection automatique améliorée**
   - Amélioration de `app/core/file_processing/ocr/ocr_selector.py`
   - Ajout de critères de détection plus fins (densité d'images, complexité visuelle)
   - Benchmarking pour optimiser les règles de sélection

### 7.2 Phase 2 : Système de validation et d'amélioration

1. **Mécanisme de détection des extractions à faible confiance**
   - Nouveau module `app/core/validation/extraction_validator.py`
   - Implémentation des métriques de confiance par type de contenu
   - Seuils adaptatifs selon le type de document

2. **Boucle de rétroaction**
   - Système de logging des résultats de qualité dans `app/core/metrics/extraction_quality.py`
   - Interface d'analyse pour identifier les tendances et problèmes récurrents
   - Mise à jour automatique des paramètres de sélection OCR

3. **Workflow de retraitement**
   - Nouvelle tâche Celery `app/core/tasks/reprocessing_tasks.py`
   - Intégration avec la file d'attente OCR pour le retraitement prioritaire
   - Options de retraitement ciblé (pages spécifiques, zones)

### 7.3 Phase 3 : Processeurs spécialisés

1. **Extracteur de tableaux**
   - Module `app/core/file_processing/extraction/table_extractor.py`
   - Intégration avec Tabula et d'autres outils spécialisés
   - Préservation de la structure des tableaux dans le format d'indexation

2. **Processeur de formules techniques**
   - Module `app/core/file_processing/extraction/formula_processor.py`
   - Reconnaissance de formules mathématiques et techniques
   - Conversion en format lisible et indexable

3. **Analyseur de schémas techniques**
   - Intégration avec Vision AI pour la détection de composants
   - Reconnaissance de symboles industriels standardisés
   - Génération de descriptions textuelles des schémas

### 7.4 Phase 4 : Chunking intelligent

1. **Stratégies de chunking adaptatives**
   - Extension du module `app/core/file_processing/chunking/semantic.py`
   - Développement de nouveaux algorithmes spécifiques aux documents techniques
   - Préservation des liens entre texte, tableaux et images

2. **Métadonnées structurelles**
   - Enrichissement des métadonnées de chunks avec la structure du document
   - Conservation des références aux éléments visuels et sections
   - Système de navigation entre chunks liés

## 8. Traitement des fichiers volumineux

Pour les fichiers PDF volumineux (>28 Mo) nécessitant un OCR, le système utilise une approche par batches pour éviter les timeouts :

1. **Conversion initiale** : Le document est d'abord converti en texte (avec OCR si nécessaire)
2. **Découpage en chunks** : Le texte est découpé en chunks de taille appropriée
3. **Traitement par batches** : Les chunks sont traités par lots plus petits
4. **Reprise sur erreur** : En cas d'échec d'un batch, le traitement peut reprendre à partir du dernier batch réussi

Cette approche est particulièrement utile lors de la génération d'embeddings pour de grands documents, où le temps de traitement peut dépasser les limites de timeout des services externes.

## 9. Métriques et évaluation

Pour mesurer l'amélioration de la qualité, nous utiliserons les métriques suivantes :

### 9.1 Métriques de base
- **Character Error Rate (CER)** : Taux d'erreur au niveau des caractères
- **Word Error Rate (WER)** : Taux d'erreur au niveau des mots
- **Accuracy** : Précision globale de l'extraction

### 9.2 Métriques avancées
- **Structure Preservation Score** : Mesure de préservation de la structure du document
- **Table Extraction Accuracy** : Précision de l'extraction des tableaux
- **Symbol Recognition Rate** : Taux de reconnaissance des symboles techniques
- **Contextual Relevance** : Pertinence contextuelle des chunks générés

### 9.3 Benchmarking
Un ensemble de documents tests de référence sera créé pour évaluer systématiquement les améliorations :
- 20 documents techniques de complexité variable
- 10 schémas techniques avec symboles standardisés
- 15 documents avec tableaux complexes
- 5 documents multilingues avec contenu technique

## 10. Tests et diagnostics

### 10.1 Scripts de diagnostic

Le script `scripts/diagnose_ocr.py` permet de vérifier la configuration des outils OCR :

```bash
python scripts/diagnose_ocr.py
```

Ce script vérifie :
- La présence des outils nécessaires (Tesseract, Ghostscript, Poppler)
- Le bon fonctionnement de OCRmyPDF
- La reconnaissance de texte avec un exemple simple

### 10.2 Script de test pour le traitement de documents

Le script `scripts/test_document_processing.py` permet de tester différentes fonctionnalités du système :

```bash
# Test complet
python scripts/test_document_processing.py --file chemin/vers/document.pdf --test full --enable-ocr

# Test de conversion seulement
python scripts/test_document_processing.py --file chemin/vers/document.pdf --test conversion

# Test OCR seulement
python scripts/test_document_processing.py --file chemin/vers/document.pdf --test ocr

# Test chunks
python scripts/test_document_processing.py --file chemin/vers/document.pdf --test chunking
```

### 10.3 Tests unitaires

Les tests unitaires sont disponibles dans les dossiers suivants :

- `tests/unit/file_processing/test_document_processor.py`
- `tests/unit/file_processing/test_chunking.py`
- `tests/unit/file_processing/test_conversion.py`

Pour exécuter les tests :

```bash
pytest tests/unit/file_processing/
```

## 11. Notes d'implémentation

### 11.1 Extensibilité du système

Le système est conçu pour être facilement extensible :

1. **Nouveaux formats** : Ajoutez de nouveaux convertisseurs dans `app/core/file_processing/conversion/`
2. **Stratégies de chunking** : Implémentez de nouvelles stratégies dans `app/core/file_processing/chunking/`
3. **Méthodes OCR** : Étendez les capacités OCR dans `app/core/file_processing/ocr/`
4. **Processeurs spécialisés** : Ajoutez de nouveaux extracteurs dans `app/core/file_processing/extraction/`

### 11.2 Performance

- Les opérations coûteuses sont exécutées de manière asynchrone via Celery
- Le traitement par batches permet de gérer efficacement les grands documents
- La mise en cache des résultats intermédiaires évite les calculs redondants

### 11.3 Sécurité et confidentialité

- Gestion sécurisée des clés API pour les services cloud
- Chiffrement des documents durant le transfert vers les services externes
- Contrôle des quotas et coûts pour les services payants

## 12. Planification du développement

Le développement des fonctionnalités d'extraction de haute qualité est prévu selon le plan d'implémentation réorganisé (voir [PLAN_IMPLEMENTATION_REORGANISE.md](../MVP/PLAN_IMPLEMENTATION_REORGANISE.md)), principalement dans les phases 2 et 3 :

- **Phase 2** : Architecture fondamentale du système de traitement de documents
  - Étape 5 : Intégration de Google Cloud Document AI et Vision AI
  - Étape 6 : Processeurs spécialisés pour contenus techniques

- **Phase 3** : Optimisation de la qualité d'extraction
  - Étape 7 : Système de validation et d'amélioration itérative
  - Étape 8 : Orchestration intelligente des processeurs
  - Étape 9 : Chunking intelligent et métadonnées enrichies
