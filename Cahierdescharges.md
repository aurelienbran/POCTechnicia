Cahier des Charges - POC RAG (Retrieval Augmented Generation)
1. Objectif du POC
Développer un système de questions-réponses capable de :

Traiter des PDF techniques volumineux (jusqu'à 150 Mo)
Extraire et indexer l'information pertinente
Fournir des réponses contextuelles précises

2. Composants Requis
Backend

FastAPI pour l'API REST
Gestion optimisée des PDF volumineux
Base vectorielle Qdrant (installation binaire locale)
Claude 3.5 Sonnet pour la génération de réponses
VoyageAI pour les embeddings

Frontend

Interface utilisateur minimaliste
Upload de PDF
Zone de chat pour les questions/réponses
Indication de progression pour les longs traitements

3. Contraintes Techniques
Gestion des PDF

Taille maximale : 150 Mo
Extraction page par page pour optimiser la mémoire
Découpage en chunks pertinents
Nettoyage des fichiers temporaires

Base Vectorielle

Installation locale de Qdrant (pas de Docker)
Stockage optimisé des embeddings
Recherche sémantique efficace

Performance

Traitement asynchrone des gros fichiers
Gestion de la mémoire (max 1GB par process)
Temps de réponse aux questions < 5s

4. Fonctionnalités Clés
Upload et Traitement

Validation des fichiers PDF
Extraction progressive du texte
Génération et stockage des embeddings
Suivi de la progression

Recherche et Réponses

Recherche sémantique dans Qdrant
Contextualisation pour Claude 3.5
Réponses basées uniquement sur le contenu extrait

5. Points d'Attention
Sécurité

Validation des types de fichiers
Nettoyage des données temporaires
Gestion sécurisée des API keys

Robustesse

Gestion des erreurs d'extraction
Reprise sur erreur
Validation des données extraites

Maintenabilité

Structure de projet claire
Tests essentiels
Documentation du code

6. Critères de Validation
Fonctionnel

Upload de PDF réussi
Extraction correcte du texte
Recherche pertinente
Réponses contextuelles

Technique

Gestion mémoire maîtrisée
Performance acceptable
Installation simple
Interface réactive

7. État d'Avancement (13/02/2025)

Backend ( Complété)
- API REST avec FastAPI
- Gestion des PDF volumineux (jusqu'à 150 Mo)
- Intégration Qdrant
- Intégration Claude 3.5 Sonnet
- Intégration VoyageAI
- Gestion asynchrone
- Gestion des erreurs
- Validation des données

Gestion des PDF ( Complété)
- Validation des fichiers
- Extraction page par page
- Chunking optimisé
- Nettoyage des fichiers temporaires
- Gestion de la mémoire

Base Vectorielle ( Complété)
- Installation locale Qdrant
- Configuration optimisée
- Gestion des collections
- Validation des données

Performance ( En cours)
- Traitement asynchrone
- Gestion mémoire < 1GB
- Optimisation des lots Qdrant
- Tests de performance complets

Frontend ( Non commencé)
- Interface utilisateur
- Upload de fichiers
- Zone de chat
- Indicateurs de progression

Sécurité ( Complété)
- Validation des fichiers
- Nettoyage des données
- Gestion des API keys
- Validation des données

Documentation ( En cours)
- README.md
- PROJECT.md
- Documentation API
- Documentation utilisateur

Tests ( En cours)
- Tests unitaires
- Tests d'intégration
- Tests de performance
- Tests frontend

Prochaines étapes prioritaires :
1. Développement du frontend
2. Tests de performance
3. Documentation complète
4. Tests d'intégration