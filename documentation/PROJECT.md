# Projet POC TECHNICIA - État d'avancement

## Vue d'ensemble
Ce projet est une plateforme complète combinant un système de Retrieval Augmented Generation (RAG) utilisant Claude 3 Sonnet et un tableau de bord OCR avancé. Le système est conçu pour traiter de grands documents techniques PDF, les indexer dans une base de données vectorielle Qdrant, générer des réponses contextuelles, et offrir une gestion complète des tâches OCR via un tableau de bord dédié.

## Architecture du Projet

L'architecture globale du projet s'articule autour de deux composants principaux :

1. **Module RAG** : Extraction, indexation et génération de réponses contextuelles
2. **Tableau de bord OCR** : Gestion et monitoring des tâches OCR en temps réel

### Backend (FastAPI)
- API REST avec FastAPI
- Endpoints principaux :
  - `/api/v1/documents` : Upload et gestion des documents
  - `/api/v1/chat` : Interface de chat avec contexte
  - `/api/v1/health` : Vérification de l'état du service
  - `/api/v1/indexing-status` : Statut du traitement des documents
  - `/api/v1/stats` : Statistiques sur les documents indexés
  - `/api/dashboard` : API du tableau de bord OCR
  - `/api/export` : Exportation des données OCR

### Composants Principaux du Module RAG
1. **PDFProcessor** : Extraction et chunking de texte (utilisant PyMuPDF)
2. **VectorStore** : Interface avec Qdrant pour le stockage et la recherche vectorielle
3. **LLMInterface** : Interface avec Claude 3 Sonnet pour la génération de réponses
4. **RAGEngine** : Orchestration du processus RAG complet

### Composants Principaux du Tableau de Bord OCR
1. **OCRTaskManager** : Gestion des tâches OCR (création, pause, reprise, annulation)
2. **OCRMetricsCollector** : Collecte et analyse des métriques de performance OCR
3. **ExportService** : Génération de rapports et exportation de données
4. **WebSocketManager** : Communication en temps réel pour les mises à jour du tableau de bord

### Frontends
- **Frontend RAG** :
  - Interface utilisateur moderne avec Tailwind CSS
  - Upload de fichiers via sidebar compact
  - Modal de progression interactif
  - Chat avec historique scrollable
  - Affichage des sources avec scores de pertinence
  - Gestion des erreurs côté client

- **Frontend Dashboard OCR** :
  - Interface de gestion et monitoring des tâches OCR
  - Visualisations et graphiques de performance en temps réel
  - Formulaires de création et gestion des tâches
  - Interface d'exportation de données et rapports
  - Communication WebSocket pour mises à jour en direct

### Dépendances Externes
- Claude 3 Sonnet (Anthropic v0.18.0)
- VoyageAI pour les embeddings (v0.3.2)
- Qdrant pour le stockage vectoriel
- PyMuPDF pour le traitement PDF

## État Actuel du Projet

### Backend
1. **Traitement des Documents**
   - Pipeline d'extraction robuste
   - Chunking optimisé avec distribution adaptative
   - Embeddings de haute qualité via Voyage AI
   - Gestion asynchrone des traitements

2. **Base de Connaissances**
   - Qdrant opérationnel et optimisé
   - 335 vecteurs indexés avec succès
   - Scores de similarité >0.75 pour requêtes pertinentes
   - Payload on_disk activé pour performance

3. **API FastAPI**
   - Endpoints stables et documentés
   - Gestion asynchrone efficace
   - Validation des données entrantes
   - Monitoring de l'état du système

### Frontend
1. **Interface Utilisateur**
   - Design moderne avec Tailwind CSS
   - Upload via sidebar compact
   - Modal de progression détaillé
   - Chat responsive et intuitif

2. **Problèmes en Cours**
   - Upload de fichiers à stabiliser
   - Gestion des erreurs à améliorer
   - Feedback utilisateur à enrichir

### Performance
1. **Qualité des Réponses**
   - Réponses structurées et précises
   - Bonne gestion du contexte
   - Admission appropriée des limites
   - Sources avec scores de pertinence

2. **Métriques**
   - Temps de réponse moyen : ~12-14s
   - Taille moyenne des chunks : 571 caractères
   - Distribution optimale des chunks
   - 335 vecteurs indexés dans Qdrant

### Prochaines Étapes

1. **Frontend**
   - Correction des problèmes d'upload
   - Amélioration du feedback utilisateur
   - Ajout de prévisualisation PDF
   - Gestion du drag & drop

2. **Optimisations**
   - Mise en cache des embeddings
   - Amélioration des temps de réponse
   - Enrichissement des métadonnées
   - Optimisation du chunking

3. **Documentation**
   - Guide d'utilisation détaillé
   - Documentation API complète
   - Exemples d'intégration
   - Guides de dépannage

## Déploiement

### Configuration Qdrant (Production)
1. **Installation Binaire**
   - Scripts d'installation et de configuration dans `scripts/`
   - Collection optimisée pour RAG :
     - Taille des vecteurs : 1024 (VoyageAI)
     - Distance : Cosine
     - Stockage sur disque activé
     - 5 segments pour distribution optimale
     - Gestion mémoire limitée à 1GB
     - Optimisation pour PDFs volumineux

## Tests de Performance

### Résultats (18/02/2025)

#### Fichiers Testés
1. `fe.pdf` (0.14 MB)
   - Temps : 0.15s
   - Mémoire : 2.79 MB
   - Vitesse : 0.90 MB/s
   - Chunks : 4

2. `LJ70_RJ70_chassis_body.pdf` (111.33 MB)
   - Temps : 9.93s
   - Mémoire : ~0.01 MB*
   - Vitesse : 11.22 MB/s
   - Chunks : 1048

*Note : La mesure mémoire semble sous-estimée pour les gros fichiers

#### Métriques Globales
- Temps de traitement moyen : 5.43s
- Mémoire moyenne utilisée : 1.83 MB
- Plus grand fichier traité : 111.33 MB

#### Points Forts
- ✅ Gestion efficace de la mémoire (< 1GB)
- ✅ Support de fichiers volumineux (> 100MB)
- ✅ Vitesse de traitement adaptative (0.90-11.22 MB/s)

#### Points d'Amélioration
- ⚠️ Temps de traitement moyen à optimiser (objectif < 5s)
- ⚠️ Monitoring mémoire à affiner pour les gros fichiers
- ⚠️ Qualité des chunks à évaluer

### Configuration Optimisée
```python
{
    "vectors": {
        "size": 1024,
        "distance": "Cosine"
    },
    "optimizers_config": {
        "default_segment_number": 2,
        "memmap_threshold": 1000,
        "indexing_threshold": 20000
    },
    "hnsw_config": {
        "m": 16,
        "ef_construct": 100,
        "full_scan_threshold": 10000
    }
}
```

## Structure du Projet
```
POC-TECHNICIA/
├── app/
│   ├── api/            # Endpoints FastAPI
│   ├── core/           # Logique métier
│   │   ├── pdf_processor.py    # Traitement PDF
│   │   ├── vector_store.py     # Interface Qdrant
│   │   ├── llm_interface.py    # Interface Claude
│   │   └── rag_engine.py       # Orchestration RAG
│   ├── static/         # Assets frontend
│   │   ├── css/
│   │   └── js/
│   ├── templates/      # Templates HTML
│   └── config.py       # Configuration
├── tests/              # Tests
│   ├── unit/
│   └── performance/
├── qdrant_storage/     # Stockage vectoriel local
├── uploads/            # Fichiers PDF temporaires
├── logs/              # Logs applicatifs
└── storage/           # Autres données persistantes
```

## Notes Techniques
- Traitement asynchrone des documents avec suivi d'état
- Tests automatisés avec pytest
- Monitoring des performances dans `performance_reports/`
- Scripts utilitaires dans `scripts/`
- Logs détaillés dans `logs/`
- Configuration via variables d'environnement

## Prochaine Revue
- Tests de performance avec la nouvelle configuration
- Validation de l'interface utilisateur
- Revue de la documentation
- Optimisation du chunking des documents
- Résolution des problèmes d'upload
