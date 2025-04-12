# Prochaines Étapes et Instructions de Démarrage

## État Actuel du Projet

### Développements achevés :
1. **Tableau de bord OCR complet** (01/04/2025) :
   - Interface utilisateur complète pour la surveillance des tâches OCR
   - Système WebSocket pour les mises à jour en temps réel
   - API d'exportation (CSV, PDF, JSON) et génération de rapports
   - Métriques de performance par fournisseur OCR
   - Documentation consolidée dans [OCR_DASHBOARD_COMPLET.md](./OCR_DASHBOARD_COMPLET.md)

2. **Système OCR hybride optimisé** :
   - Sélection intelligente du fournisseur OCR selon le type de document
   - Mécanisme de file d'attente et reprise en cas d'erreur
   - Évaluation de la qualité OCR avec métriques détaillées

### Travaux en cours :
1. Développement d'outils de diagnostic avancés pour l'OCR
2. Adaptation des interfaces pour les appareils mobiles
3. Support pour formats de documents additionnels
4. Amélioration de la documentation technique

## Corrections Récentes

### Gestion des Réponses API (24/02/2025)
Nous avons corrigé plusieurs problèmes liés au traitement des réponses de l'API Claude :
1. Correction du traitement des ContentBlocks dans les réponses :
   - Gestion correcte des réponses sous forme de liste
   - Extraction du texte de chaque ContentBlock
   - Support unifié pour les questions simples et techniques
2. Amélioration du formatage des réponses techniques :
   - Suppression des titres de sections répétés
   - Meilleure extraction des sections pertinentes
   - Nettoyage des mentions de sources dans le texte

### Améliorations de l'Interface (24/02/2025)
1. Ajout d'une bulle de réflexion pendant le traitement des requêtes :
   - Animation de points pour indiquer l'activité
   - Affichage et masquage automatique
   - Style cohérent avec l'interface
2. Correction du formatage des messages :
   - Meilleure détection du contenu HTML
   - Conservation des retours à la ligne
   - Support des crochets dans le texte

### Format des Documents (24/02/2025)
Nous avons standardisé le format des documents dans toute l'application :
1. Standardisation des clés pour l'accès au contenu des chunks :
   - Utilisation cohérente de la clé `text` dans :
   - PDFProcessor : génération des chunks de documents
   - RAGEngine : indexation des documents dans Qdrant
   - Méthode similarity_search : récupération des documents
2. Cette standardisation assure que :
   - Les documents sont correctement stockés et récupérés
   - Le LLM (Claude) peut accéder au contenu des documents
   - Les réponses sont générées avec le bon contexte

### Améliorations OCR - Mise à jour du 03/03/2025

#### Modifications Récentes

##### 1. Compatibilité Windows pour OCR
- Remplacement de `asyncio.create_subprocess_exec` par `subprocess.run` dans `ocr_helper.py`
- Correction des problèmes de chemin et de dépendances sous Windows
- Impact : Fonctionnalité OCR pleinement opérationnelle sur environnements Windows

##### 2. Amélioration de la Détection des Documents OCR
- Mise en place d'une détection plus précise des documents nécessitant OCR
- Vérification des métadonnées et analyse du contenu textuel
- Impact : Meilleure identification automatique des documents scannés

##### 3. Correction de Bugs dans le Traitement OCR
- Correction d'une erreur KeyError liée à l'accès à la clé 'content' dans `rag_engine.py`
- Mise à jour pour utiliser la clé 'text' en cohérence avec la structure des chunks
- Impact : Traitement fluide des documents OCR sans erreurs d'indexation

##### 4. Optimisation de l'Extraction de Texte
- Implémentation d'une méthode d'extraction hybride dans `pdf_processor.py`
- Choix intelligent entre PyMuPDF et pdftotext selon le type de document
- Impact : Meilleure qualité d'extraction de texte pour tous types de documents

#### Prochaines Étapes OCR

1. Amélioration des performances OCR
   - Tests sur divers types de documents scannés
   - Optimisation des paramètres OCRmyPDF pour les documents techniques
   - Évaluation de méthodes alternatives pour les cas difficiles

2. Support multilangue amélioré
   - Configuration des packs de langues supplémentaires
   - Détection automatique de la langue du document

### Améliorations OCR (02/03/2025)

Nous avons considérablement amélioré la fonctionnalité OCR de l'application :

1. **Meilleure compatibilité Windows** :
   - Remplacement d'`asyncio.create_subprocess_exec` par `subprocess.run`
   - Gestion améliorée des chemins d'exécutables

2. **Détection automatique de besoin d'OCR** :
   - Par nom de fichier (préfixe "ocr_" ou contient "_ocr_")
   - Par analyse des métadonnées du PDF
   - Par détection de l'absence de texte dans les pages

3. **Gestion des erreurs et robustesse** :
   - Ajout d'un mécanisme de tentatives multiples
   - Journalisation détaillée des erreurs
   - Capture et traitement approprié des exceptions

4. **Outils de diagnostic et de test** :
   - Script `diagnose_ocr.py` pour vérifier l'installation des dépendances
   - Script `test_ocr.py` pour tester l'OCR sur un fichier spécifique
   - Script PowerShell `update_ocr_path.ps1` pour configurer automatiquement le PATH

5. **Documentation complète** :
   - Instructions détaillées dans `INSTALLATION_OCR.md`
   - Description technique des algorithmes d'extraction de texte
   - Guides de dépannage et de résolution des problèmes

**Prochaines étapes OCR** :
- Développement d'une interface utilisateur pour configurer les options OCR
- Ajout de langues supplémentaires et de configurations personnalisées
- Optimisation des performances pour les documents volumineux

### Améliorations RAG - Mise à jour du 25/02/2025

#### Modifications Récentes

##### 1. Amélioration de la Recherche de Documents
- Augmentation du nombre de documents retournés (k=6)
- Réduction du seuil de similarité à 0.5 pour inclure plus de résultats pertinents
- Impact : Meilleure couverture des informations disponibles

##### 2. Optimisation de la Génération de Réponses
- Ajustement de la température à 0.5 (précédemment 0.3)
- Équilibre amélioré entre précision et naturel des réponses
- Impact : Réponses plus fluides tout en maintenant la précision technique

##### 3. Amélioration des Sources
- Réduction du seuil de score pour les sources à 0.6
- Ajout d'informations contextuelles (pages, sections)
- Tri des sources par pertinence
- Impact : Sources plus détaillées et mieux contextualisées

#### Prochaines Étapes

##### Court Terme
1. Amélioration du formatage du contexte
   - Préservation de la structure des documents
   - Meilleure gestion des sections
   - Implémentation d'un système de formatage robuste

##### Moyen Terme
1. Optimisation des embeddings
   - Évaluation de différents modèles d'embedding
   - Tests de performance sur la recherche sémantique

2. Amélioration de la classification des questions
   - Raffinement des catégories
   - Meilleure gestion des cas limites

##### Long Terme
1. Système de feedback utilisateur
   - Collecte des retours sur la qualité des réponses
   - Amélioration continue basée sur les retours

2. Optimisation des performances
   - Mise en cache intelligente
   - Parallélisation des recherches

### Installation Portable - Mise à jour du 03/03/2025

#### Fonctionnalités Ajoutées
1. **Installateur Portable**
   - Création d'un installateur auto-extractible
   - Support pour les dépendances portables
   - Configuration automatique de l'environnement

2. **Scripts Portables**
   - `portable_installer.bat` : Génération de la structure d'installation
   - `setup_portable.bat` : Configuration des dépendances portables
   - `start_portable.bat` : Démarrage avec les versions portables
   - `clean_qdrant_portable.bat` : Nettoyage de Qdrant portable

#### Documentation
- Ajout de `PORTABLE.md` avec les instructions détaillées
- Mise à jour du README.md avec la section sur l'installation portable

#### Prochaines Étapes
- Test de l'installateur sur différentes machines
- Optimisation de la taille de l'installateur
- Ajout d'une interface graphique pour l'installation

#### Utilisation
Pour créer un installateur portable :
```bash
cd scripts
portable_installer.bat
```

Pour les instructions détaillées, consultez `documentation/PORTABLE.md`.

### Prochaines Améliorations
- Ajouter des tests pour valider le format des documents
- Optimiser la taille des chunks pour de meilleures performances
- Améliorer la pertinence des réponses avec un meilleur formatage du contexte

## Instructions de Démarrage (MISE À JOUR MARS 2025)

Nous avons simplifié l'architecture du projet. Le frontend React est maintenant:
- Intégré au projet principal dans le dossier `D:\Projets\POC TECHNICIA\frontend\`
- Automatiquement servi par FastAPI via la redirection depuis la racine `/`
- Accessible directement à l'adresse `http://localhost:3001/` en développement

### Organisation des Scripts

Nous avons réorganisé les scripts pour une meilleure lisibilité et maintenance :

#### Structure des Dossiers
1. **startup/** : Scripts de démarrage des composants
   - `1-start-qdrant.bat` : Démarrage de Qdrant
   - `2-start-backend.bat` : Démarrage du backend FastAPI
   - `3-start-frontend.bat` : Démarrage du frontend React
   - `start-all-components.bat` : Démarrage de tous les composants

2. **maintenance/** : Scripts de maintenance du système
   - `clean_qdrant.bat` : Nettoyage des collections Qdrant
   - `cleanup_project.bat` : Nettoyage des fichiers temporaires
   - `portable_installer.bat` : Création d'installateur portable
   - `setup_project.bat` : Configuration initiale du projet

3. **python/** : Scripts Python pour la gestion de Qdrant
   - `check_qdrant.py` : Vérification de l'état de Qdrant
   - `clean_all_collections.py` : Suppression des collections
   - `clean_documents.py` : Nettoyage de la collection documents
   - `create_snapshot.py` : Création de snapshots Qdrant
   - `initialize_qdrant.py` : Initialisation de Qdrant
   - `restore_snapshot.py` : Restauration de snapshots

4. **tools/** : Outils de diagnostic et de test
   - `diagnostic_tool.py` : Outil de diagnostic complet
   - `test_query.py` : Test de requêtes Qdrant
   - `upload_file.py` : Utilitaire d'upload de fichiers
   - `verify_index.py` : Vérification d'index vectoriel

5. **deprecated/** : Scripts obsolètes (conservés pour référence)
   - Note : Ces scripts sont conservés uniquement pour référence et ne doivent pas être utilisés

### Démarrage du Projet

#### 1. Préparation du Frontend
```bash
cd scripts/maintenance
setup_project.bat
```
Ce script va installer toutes les dépendances npm nécessaires dans le dossier frontend.

#### 2. Démarrage des Serveurs
```bash
cd scripts/startup
start-all-components.bat
```
Ce script va démarrer:
- Le backend FastAPI sur le port 8000 
- Le frontend React sur le port 3001

#### 3. Accès à l'Application
- Accédez à `http://localhost:8000` pour être redirigé automatiquement vers le frontend React
- Ou accédez directement à `http://localhost:3001`

### Maintenance du Système

#### 1. Nettoyage de Qdrant
Pour nettoyer ou gérer les collections Qdrant :
```bash
cd scripts/maintenance
clean_qdrant.bat
```
Ce script offre plusieurs options:
- Suppression de la collection 'documents'
- Suppression de toutes les collections
- Création et restauration de snapshots

#### 2. Nettoyage du Projet
Pour nettoyer les fichiers temporaires :
```bash
cd scripts/maintenance
cleanup_project.bat
```

## Commandes Utiles

### Gestion de l'Environnement
```bash
# Créer un nouvel environnement virtuel
python -m venv .venv

# Activer l'environnement
.\.venv\Scripts\activate 

# Installer les dépendances
pip install -r requirements.txt

# Mettre à jour les dépendances
pip install --upgrade -r requirements.txt
```

### Tests
```bash
# Lancer tous les tests
pytest

# Lancer les tests avec couverture
pytest --cov=app tests/
```

### Logs
Les logs sont maintenant stockés dans le dossier `logs/` :
- `logs/app.log` : Logs principaux de l'application
- `logs/uvicorn.log` : Logs du serveur web

## Problèmes Connus et Solutions

### 1. Erreur 503 au Démarrage
Si vous obtenez une erreur 503 sur `/api/v1/health` :
- C'est normal pendant l'initialisation du système
- Attendre quelques secondes que l'initialisation soit terminée
- Vérifier les logs dans `logs/app.log` pour suivre la progression

### 2. Problèmes d'Upload de Fichiers
Si l'upload de fichiers ne fonctionne pas :
1. Vérifier que le fichier est bien un PDF
2. Vérifier que la taille est inférieure à 150 MB
3. Vérifier les erreurs dans la console du navigateur
4. Essayer de rafraîchir la page si le système vient de démarrer

### 3. Erreur d'Indexation Qdrant
Si les documents ne sont pas indexés correctement :
1. Vérifier que Qdrant est bien lancé
2. Vérifier les logs dans `logs/app.log`
3. Essayer de recréer la collection :
```bash
curl -X DELETE http://localhost:6333/collections/documents
```
Puis redémarrer l'API.

### 4. Problèmes d'Embeddings
Si les embeddings ne sont pas générés correctement :
1. Vérifier la clé API VoyageAI dans `.env`
2. Vérifier la connexion internet
3. Vérifier les quotas d'utilisation de l'API

## Prochaines Améliorations

### 1. Monitoring et Performance
- Implémentation des métriques de performance
  - Temps de réponse par composant
  - Utilisation des ressources
  - Qualité des réponses
- Mise en place du système de monitoring
  - Dashboard Grafana
  - Collecte avec Prometheus
  - Alerting automatique
- Optimisation du stockage des logs
  - Rotation et compression
  - Analyse automatique
  - Nettoyage intelligent

### 2. Gestion des Sauvegardes
- Système de snapshots Qdrant
  - Sauvegarde quotidienne
  - Restauration rapide
  - Vérification d'intégrité
- Backup des configurations
  - Variables d'environnement
  - Prompts optimisés
  - Paramètres système

### 3. Tests et Qualité
- Tests de performance
  - Benchmarks automatisés
  - Rapports de régression
  - Profiling détaillé
- Tests de charge
  - Simulation multi-utilisateurs
  - Stress testing WebSocket
  - Limites de scalabilité

### 4. Interface Utilisateur
- Correction des problèmes d'upload de fichiers
- Amélioration du feedback visuel pendant le traitement
- Ajout d'une prévisualisation des PDF
- Gestion du drag & drop

### 5. Architecture Double Frontend (Mise à jour du 27/02/2025)

#### Configuration Actuelle

Nous avons mis en place une architecture double frontend permettant d'utiliser simultanément :

1. **Frontend original (FastAPI + Jinja2)**
   - URL d'accès : `http://localhost:8000`
   - Technologies : FastAPI, Jinja2, Bootstrap
   - Serveur : Uvicorn sur le port 8000

2. **Nouveau frontend (React + Vite)**
   - URL d'accès : `http://localhost:3001`
   - Technologies : React, TypeScript, Tailwind CSS, Vite
   - Serveur de développement : Vite sur le port 3001

Les deux frontends partagent le même backend FastAPI et peuvent être utilisés simultanément.

#### Installation et Configuration

1. **Configuration du Frontend React**
   ```bash
   # Dans le dossier frontend POC
   npm install
   ```

2. **Configuration des Ports**
   - Le frontend React est configuré pour utiliser le port 3001 (vite.config.ts)
   - Le backend FastAPI utilise le port 8000
   - Les proxys sont configurés pour les appels API vers `/api` et `/static`

3. **Configuration CORS**
   - Les origines autorisées dans `app/config.py` incluent :
     - `http://localhost:8000`
     - `http://localhost:3001`

#### Démarrage des deux Frontends

1. **Utiliser le script de démarrage automatique**
   ```bash
   # À la racine du projet
   scripts\startup\start-all-components.bat
   ```
   Ce script lance à la fois le backend FastAPI et le frontend React.

2. **Démarrage Manuel**
   ```bash
   # Terminal 1 - Backend FastAPI
   cd "chemin\vers\POC TECHNICIA"
   .\.venv\Scripts\activate
   uvicorn app.main:app --reload --port 8000

   # Terminal 2 - Frontend React
   cd "chemin\vers\frontend POC"
   npm run dev
   ```

#### Accès aux Frontends

- **Frontend Original** : [http://localhost:8000](http://localhost:8000)
- **Nouveau Frontend** : [http://localhost:3001](http://localhost:3001)

#### API Partagée

Les deux frontends utilisent les mêmes API REST :
- Les endpoints API sont accessibles via `/api/v1/...`
- Le frontend React est configuré avec un proxy pour rediriger les appels API automatiquement

#### Dépannage

1. **Page blanche sur le Frontend React**
   - Vérifier que le serveur Vite est bien démarré sur le port 3001
   - Désactiver le mode "useMockApi" dans `src/App.tsx` pour utiliser l'API réelle
   - Vérifier les erreurs dans la console du navigateur

2. **Statistiques incorrectes**
   - Les statistiques affichées peuvent montrer 0 documents indexés même si des chunks vectorisés sont présents
   - C'est dû à une désynchronisation entre les compteurs en mémoire et la base vectorielle
   - L'indicateur "Documents disponibles" permet de voir si la base contient des données

3. **Problèmes d'API**
   - Vérifier que les deux serveurs (FastAPI et Vite) sont bien lancés
   - S'assurer que la configuration CORS autorise les origines correctes
   - Vérifier les logs du backend pour d'éventuelles erreurs

### 6. Performance
- Optimisation du chunking des documents
- Amélioration des temps de réponse
- Mise en cache des embeddings fréquents

### 7. Fonctionnalités
- Export des conversations
- Historique des documents traités
- Filtrage par source de document
- Mode hors ligne pour certaines fonctionnalités

### 8. Sécurité
- Validation plus stricte des fichiers
- Rate limiting sur les endpoints
- Gestion des sessions utilisateur
- Chiffrement des données sensibles
