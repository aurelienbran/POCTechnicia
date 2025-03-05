# POC RAG - Assistant Documentation Technique

## Description
POC de Retrieval Augmented Generation (RAG) pour le traitement de documents techniques PDF volumineux. Le système utilise Claude 3 Sonnet pour la génération de réponses et VoyageAI pour les embeddings, avec une interface utilisateur moderne et intuitive basée sur React.

## Fonctionnalités
- Upload et traitement de PDF jusqu'à 150 Mo
- Traitement asynchrone des documents avec suivi de progression
- Extraction et indexation intelligente du contenu avec PyMuPDF
- OCR automatique pour les documents scannés (via OCRmyPDF)
- Recherche sémantique optimisée via Qdrant
- Génération de réponses contextuelles avec Claude 3 Sonnet :
  - Réponses directes sans préfixe de mode
  - Génération parallèle des questions de suivi
  - Gestion optimisée des composants
- Interface utilisateur moderne et réactive (React + Vite) :
  - Design Tailwind CSS + TypeScript
  - État géré avec React Hooks
  - Sidebar compacte pour l'upload
  - Modal de progression interactif
  - Chat avec historique scrollable
  - Affichage des sources avec scores
  - Design responsive
  - Gestion des erreurs côté client

## Prérequis
- Python 3.11+
- Environnement virtuel Python (.venv)
- Node.js et npm (pour le frontend React)
- Qdrant (version binaire)
- Clés API :
  - VoyageAI pour les embeddings (v0.3.2)
  - Claude 3 Sonnet (Anthropic v0.18.0)
- Pour la fonctionnalité OCR (optionnelle) :
  - Tesseract OCR
  - Poppler
  - Ghostscript
  - OCRmyPDF (installé via pip)
  - Voir [INSTALLATION_OCR.md](./INSTALLATION_OCR.md) pour les instructions détaillées

## Installation

1. Cloner le dépôt :
```bash
git clone <repository_url>
cd POC-TECHNICIA
```

2. Créer et activer l'environnement virtuel :
```bash
python -m venv .venv
.\.venv\Scripts\activate 
source .venv/bin/activate 
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Installer les dépendances OCR (optionnel) :
Voir [INSTALLATION_OCR.md](./INSTALLATION_OCR.md) pour les instructions détaillées d'installation de Tesseract, Poppler et Ghostscript.

```bash
# Pour vérifier l'installation OCR
python .\scripts\diagnose_ocr.py

# Pour tester l'OCR sur un fichier PDF
python .\scripts\test_ocr.py chemin/vers/fichier.pdf

# Configuration automatique du PATH Windows (PowerShell administrateur)
.\scripts\tools\update_ocr_path.ps1
```

Après avoir installé les dépendances OCR, vous pouvez démarrer l'application avec les scripts de démarrage qui prendront automatiquement en compte la configuration OCR :

```bash
# Démarrage complet de l'application (après installation des dépendances OCR)
cd scripts/startup
start-all-components.bat
```

5. Copier le fichier `.env.example` vers `.env` et configurer les variables :
```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-...  # Clé API Claude 3 Sonnet
VOYAGE_API_KEY=pa-...         # Clé API VoyageAI

# Configuration
MAX_UPLOAD_SIZE=157286400     # Taille maximale des fichiers (150 Mo)
QDRANT_HOST=localhost         # Hôte Qdrant
QDRANT_PORT=6333             # Port Qdrant
QDRANT_PATH=./qdrant_storage # Stockage local Qdrant
COLLECTION_NAME=documents     # Nom de la collection
```

## Fonctionnalité OCR

L'application intègre une couche OCR puissante pour le traitement des documents PDF numérisés ou sans texte sélectionnable :

### Caractéristiques principales

- **Détection automatique** des documents nécessitant OCR par :
  - Analyse du contenu textuel des premières pages
  - Analyse des métadonnées du document
  - Reconnaissance des marqueurs OCR dans les noms de fichiers

- **Intégration avec OCRmyPDF** qui utilise :
  - Tesseract OCR pour la reconnaissance de texte
  - Ghostscript pour le traitement PDF
  - Poppler pour l'extraction de texte améliorée

- **Extraction de texte hybride** adaptative :
  - Utilisation de PyMuPDF comme méthode principale
  - Recours à pdftotext pour les documents OCR ou peu structurés
  - Stratégie optimisée selon le type de document

### Outils de diagnostic et test

Plusieurs scripts utilitaires facilitent l'installation et le test de l'OCR :

```bash
# Diagnostic complet des dépendances OCR
python .\scripts\diagnose_ocr.py

# Test OCR sur un fichier PDF
python .\scripts\test_ocr.py chemin/vers/fichier.pdf

# Configuration automatique du PATH Windows (PowerShell administrateur)
.\scripts\tools\update_ocr_path.ps1
```

### Configuration

Deux méthodes de configuration sont disponibles :
1. **Variables d'environnement** dans le fichier `.env` :
   ```
   TESSERACT_PATH=C:\chemin\vers\Tesseract-OCR
   POPPLER_PATH=C:\chemin\vers\poppler\bin
   GHOSTSCRIPT_PATH=C:\chemin\vers\ghostscript
   ```

2. **PATH système** : Ajout des chemins des outils dans la variable PATH de Windows

Pour plus de détails, consultez [INSTALLATION_OCR.md](./INSTALLATION_OCR.md).

## Architecture

Le projet utilise :
- FastAPI pour l'API REST
- PyMuPDF pour le traitement des PDFs
- VoyageAI pour les embeddings
- Qdrant (mode local) pour le stockage vectoriel
- Claude 3 Sonnet pour la génération de réponses
- Tailwind CSS pour l'interface utilisateur

### Stockage Vectoriel

Nous utilisons Qdrant en mode local (fichier) plutôt qu'en mode serveur pour :
- Simplifier le déploiement
- Éviter les dépendances externes
- Faciliter les tests et le développement
- Permettre une portabilité maximale

Les vecteurs et métadonnées sont stockés dans le dossier `qdrant_storage/`.

## Structure du Projet

```
POC-TECHNICIA/
├── app/
│   ├── api/            # Endpoints FastAPI
│   ├── core/           # Logique métier
│   │   ├── pdf_processor.py    # Traitement PDF
│   │   ├── vector_store.py     # Interface Qdrant
│   │   ├── llm_interface.py    # Interface Claude
│   │   ├── ocr_helper.py       # Fonctionnalités OCR
│   │   └── rag_engine.py       # Orchestration RAG
│   ├── static/         # Assets static
├── documentation/      # Documentation du projet
│   ├── MONITORING.md   # Configuration monitoring
│   ├── NEXT.md        # Prochaines étapes
│   ├── PIPELINE.md    # Description pipelines
│   ├── PORTABLE.md    # Installation portable
│   ├── README.md      # Documentation principale
│   └── WEBSOCKET.md   # Implémentation WebSocket
├── frontend/          # Frontend React (Vite)
│   ├── public/        # Assets statiques
│   ├── src/           # Code source React
│   ├── index.html     # Template HTML principal
│   └── package.json   # Dépendances NPM
├── logs/              # Logs applicatifs
│   ├── app.log
│   ├── error.log
│   └── websocket.log
├── performance_reports/# Rapports de performance
├── scripts/           # Scripts utilitaires
│   ├── startup/       # Scripts de démarrage
│   │   ├── 1-start-qdrant.bat       # Démarrage de Qdrant
│   │   ├── 2-start-backend.bat      # Démarrage du backend
│   │   ├── 3-start-frontend.bat     # Démarrage du frontend
│   │   └── start-all-components.bat # Démarrage complet
│   ├── maintenance/   # Scripts de maintenance
│   │   ├── clean_qdrant.bat         # Nettoyage de Qdrant
│   │   ├── cleanup_project.bat      # Nettoyage du projet
│   │   ├── portable_installer.bat   # Création d'installateur portable
│   │   └── setup_project.bat        # Configuration du projet
│   ├── python/        # Scripts Python utilitaires
│   │   ├── check_qdrant.py          # Vérification de l'état de Qdrant
│   │   ├── clean_all_collections.py # Suppression des collections
│   │   ├── clean_documents.py       # Nettoyage de la collection documents
│   │   ├── create_snapshot.py       # Création de snapshots Qdrant
│   │   ├── initialize_qdrant.py     # Initialisation de Qdrant
│   │   └── restore_snapshot.py      # Restauration de snapshots
│   ├── tools/         # Outils de diagnostic et de test
│   │   ├── diagnostic_tool.py       # Outil de diagnostic
│   │   ├── test_query.py            # Test de requête
│   │   ├── upload_file.py           # Upload de fichier
│   │   └── verify_index.py          # Vérification d'index
│   └── deprecated/    # Scripts obsolètes (conservés pour référence)
├── snapshots/         # Sauvegardes Qdrant
├── storage/           # Stockage persistant
├── temp/              # Fichiers temporaires
├── tests/             # Tests unitaires et E2E
│   └── performance/   # Tests de performance
└── uploads/           # Upload temporaire PDF
```

## Utilisation

### Installation et configuration du projet

1. **Configuration complète du projet**
```bash
cd scripts/maintenance
setup_project.bat
```
Ce script effectue automatiquement:
- La création d'un environnement virtuel Python
- L'installation des dépendances Python du backend
- L'installation des dépendances NPM du frontend React
- La configuration de Qdrant

### Démarrage du projet

1. **Démarrage de tous les serveurs**
```bash
cd scripts/startup
start-all-components.bat
```
Ce script lance automatiquement:
- Le serveur Qdrant
- Le backend FastAPI
- Le frontend React

2. **Accès à l'application**
```
http://localhost:8000  # Redirection automatique vers le frontend React
http://localhost:3001  # Accès direct au frontend React
```

3. **Documentation API (Swagger)**
```
http://localhost:8000/api/docs
```

### Maintenance

1. **Nettoyage de la base vectorielle Qdrant**
```bash
cd scripts/maintenance
clean_qdrant.bat
```
Ce script offre plusieurs options:
- Suppression de la collection 'documents'
- Suppression de toutes les collections
- Création de snapshots de sauvegarde
- Restauration de snapshots

2. **Nettoyage du projet**
```bash
cd scripts/maintenance
cleanup_project.bat
```
Ce script permet de nettoyer le projet en supprimant :
- Les fichiers temporaires
- Les caches et répertoires de compilation
- Les fichiers de tests inutilisés
- Les environnements virtuels (optionnel)

### Installation Portable

1. **Création d'un installateur portable**
```bash
cd scripts/maintenance
portable_installer.bat
```
Ce script crée un installateur auto-extractible qui permet de:
- Déployer le projet sur n'importe quel PC sans installation
- Inclure toutes les dépendances portables (Python, Node.js, Qdrant)
- Configurer automatiquement l'environnement de travail
- Exécuter l'application depuis une clé USB ou un dossier partagé

> **Note**: Les scripts `setup_portable.bat`, `start_portable.bat` et `clean_qdrant_portable.bat` ne sont pas présents initialement dans le dossier scripts, mais sont générés lors de l'exécution de l'installateur portable.

2. **Utilisation de la version portable**
```bash
# Une fois installé via l'exécutable auto-extractible
cd scripts/maintenance
setup_portable.bat  # Configuration initiale
cd ../startup
start_portable.bat  # Démarrage de tous les services
```

Pour des instructions détaillées, consultez le document [PORTABLE.md](./documentation/PORTABLE.md).

## Démarrage Rapide

1. **Installation des dépendances**
   ```
   # Dépendances Python (backend)
   pip install -r requirements.txt
   
   # Installation des dépendances OCR (optionnel mais recommandé)
   # Voir INSTALLATION_OCR.md pour les instructions détaillées
   
   # Vérification de l'installation OCR
   python .\scripts\diagnose_ocr.py
   
   # Dépendances JavaScript (frontend)
   cd scripts/maintenance
   setup_frontend.bat
   ```

2. **Démarrage des serveurs**
   ```
   cd scripts/startup
   start-all-components.bat
   ```

3. **Accès à l'application**
   - Ouvrez votre navigateur et accédez à `http://localhost:8000`
   - Vous serez automatiquement redirigé vers le frontend React moderne

## Problèmes Connus

1. **Erreur 503 au Démarrage**
   - Normal pendant l'initialisation du système
   - Attendre quelques secondes
   - Vérifier les logs dans `logs/app.log`

2. **Problèmes d'Upload**
   - Vérifier que le fichier est un PDF
   - Taille maximale : 150 MB
   - Rafraîchir si le système vient de démarrer

## Limitations Actuelles

- Taille maximale des fichiers : 150 MB
- Format supporté : PDF uniquement
- Base de données vectorielle locale (pas de clustering)
- Traitement séquentiel des documents

## État Actuel du Projet

### Composants Principaux
- Upload et traitement de PDF avec PyMuPDF
- Extraction de texte et chunking optimisé
- OCR intégré pour les documents scannés (avec OCRmyPDF)
- Génération d'embeddings avec VoyageAI
- Stockage vectoriel optimisé avec Qdrant
- Interface LLM avec Claude
- Interface utilisateur (en développement)

### Optimisations Réalisées
1. **Migration vers PyMuPDF** :
   - Meilleure performance pour les gros PDFs
   - Extraction de texte plus précise
   - Gestion optimisée de la mémoire

2. **Intégration OCR** :
   - Détection automatique des documents nécessitant OCR
   - Traitement hybride (PyMuPDF + pdftotext)
   - Compatible Windows et Linux
   - Optimisé pour les documents techniques

3. **Configuration Qdrant Optimisée** :
   - Collection configurée pour RAG
   - Stockage sur disque pour les gros volumes
   - Paramètres optimisés pour la recherche sémantique
   - Gestion mémoire contrôlée (max 1GB)

## Tests

Exécuter les tests :
```bash
pytest
```

Tests avec couverture :
```bash
pytest --cov=app tests/
```

Tests de performance :
```bash
python tests/performance/test_performance.py
```

## Logs

Les logs sont stockés dans :
- `logs/app.log` : Logs principaux
- `logs/uvicorn.log` : Logs du serveur

## Documentation Complémentaire

- [PROJECT.md](PROJECT.md) : État détaillé du projet
- [PIPELINE.md](PIPELINE.md) : Description des pipelines de traitement
- [INSTALLATION_OCR.md](INSTALLATION_OCR.md) : Configuration OCR
- [NEXT.md](NEXT.md) : Prochaines étapes et instructions

## Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## Licence

Distribué sous la licence MIT. Voir `LICENSE` pour plus d'informations.

## Gestion des Erreurs

### Niveaux d'Erreur
1. **Validation** : Erreurs de format ou de données
2. **Fonctionnel** : Erreurs métier
3. **Système** : Erreurs infrastructure
4. **Fatal** : Erreurs bloquantes

### Format des Erreurs
```json
{
    "error": "ERROR_CODE",
    "detail": "Description détaillée",
    "timestamp": "2024-02-24T10:30:00Z"
}
```

### Logging
- Logs structurés JSON
- Rotation quotidienne
- Rétention 30 jours
- Monitoring des erreurs

## Monitoring

### Métriques Clés
1. **Performance**
   - Temps de réponse
   - Utilisation ressources
   - Taux de succès

2. **Qualité**
   - Score similarité
   - Pertinence réponses
   - Satisfaction utilisateur

### Outils
- Grafana : Visualisation
- Prometheus : Collecte
- Alertmanager : Notifications

## WebSocket

Le système utilise WebSocket pour :
- Communication temps réel
- Questions de suivi
- Notifications d'état
- Mises à jour progressives

Voir `WEBSOCKET.md` pour plus de détails.
