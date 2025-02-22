# Prochaines Étapes et Instructions de Démarrage

## État Actuel du Projet

Nous sommes actuellement en train de :
1. Optimiser le traitement des embeddings avec VoyageAI
2. Améliorer la gestion des erreurs et le logging
3. Résoudre les problèmes d'indexation dans Qdrant
4. Corriger les problèmes d'upload de fichiers dans le frontend

## Démarrage du Projet

### 1. Prérequis
- Python 3.11+ installé
- Qdrant.exe téléchargé depuis [le site officiel](https://qdrant.tech/documentation/quick-start/)
- Clés API configurées dans `.env` :
  - `VOYAGE_API_KEY` pour VoyageAI
  - `ANTHROPIC_API_KEY` pour Claude 3 Sonnet

### 2. Lancement des Services

#### Démarrer Qdrant
1. Ouvrir un terminal
2. Naviguer vers le dossier contenant Qdrant.exe
3. Lancer la commande :
```bash
./qdrant.exe
```
Le serveur Qdrant sera accessible sur `http://localhost:6333`

#### Démarrer l'API
1. Ouvrir un nouveau terminal
2. Naviguer vers le dossier du projet
3. Activer l'environnement virtuel :
```bash
.\.venv\Scripts\activate
```
4. Lancer l'API :
```bash
uvicorn app.main:app --reload --port 8000
```
L'API sera accessible sur `http://localhost:8000`

### 3. Vérification du Fonctionnement

#### Vérifier Qdrant
```bash
curl http://localhost:6333/collections/documents
```
Devrait retourner les informations sur la collection.

#### Vérifier l'API
```bash
curl http://localhost:8000/api/v1/health
```
Devrait retourner `{"status": "ok"}` une fois le système initialisé.

## Commandes Utiles

### Gestion de l'Environnement
```bash
# Créer un nouvel environnement virtuel
python -m venv .venv

# Activer l'environnement
.\.venv\Scripts\activate  # Windows

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

### 1. Interface Utilisateur
- Correction des problèmes d'upload de fichiers
- Amélioration du feedback visuel pendant le traitement
- Ajout d'une prévisualisation des PDF
- Gestion du drag & drop

### 2. Performance
- Optimisation du chunking des documents
- Amélioration des temps de réponse
- Mise en cache des embeddings fréquents

### 3. Fonctionnalités
- Export des conversations
- Historique des documents traités
- Filtrage par source de document
- Mode hors ligne pour certaines fonctionnalités

### 4. Sécurité
- Validation plus stricte des fichiers
- Rate limiting sur les endpoints
- Gestion des sessions utilisateur
- Chiffrement des données sensibles
