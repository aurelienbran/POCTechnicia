# Architecture Globale du Système Technicia

Ce document présente l'architecture globale du système Technicia, en détaillant les principaux composants et leurs interactions.

## Vue d'ensemble

L'application Technicia est basée sur une architecture moderne qui combine plusieurs technologies clés:

- **Backend**: FastAPI (Python) avec une architecture RESTful
- **Frontend**: React/TypeScript avec TailwindCSS
- **Base de données vectorielle**: Qdrant pour le stockage des embeddings
- **Traitement LLM**: Intégration avec Anthropic Claude et VoyageAI
- **Traitement de documents**: Système OCR hybride utilisant OCRmyPDF, Tesseract, Poppler et Ghostscript
- **Tableau de bord OCR**: Surveillance et gestion complètes des tâches OCR en temps réel

## Diagramme des composants principaux

```
+-----------------------+       +------------------------+
|                       |       |                        |
|  Frontend (React/TS)  +<----->+  Backend (FastAPI)     |
|                       |       |                        |
+-----------+-----------+       +------+----------+------+
            ^                          |          |
            |                          |          |
            |                          v          v
            |                  +-------+--+    +--+-------+    +----------------+
            |                  |          |    |          |    |                |
            |                  |  LLM     |    |  RAG     |    | Tableau de     |
            |                  |Interface |    |  Engine  |    | bord OCR       |
            |                  |          |    |          |    |                |
            |                  +----+-----+    +----+-----+    +-------+--------+
            |                       |               |                  |
            |                       v               v                  v
            |                  +----+---------------+--+        +------+-------+
            |                  |                       |        |              |
            +------------------+  WebSocket Manager    +<-------+ Task Manager |
                               |                       |        |              |
                               +-----------------------+        +--------------+
```

## Architecture de communication

L'application utilise une architecture hybride pour la communication entre le frontend et le backend:

### WebSockets
- Utilisé pour les communications en temps réel (streaming des réponses du LLM)
- Implémente un mécanisme de throttling pour optimiser les performances
- Permet la diffusion des mises à jour de statut d'indexation en temps réel

### REST API
- Utilisé pour les opérations CRUD standard
- Sert de mécanisme de fallback quand les WebSockets ne sont pas disponibles
- Utilisé pour l'upload de documents et les requêtes non-streaming

## Traitement des documents et OCR

```
+------------------------+     +---------------------------+
|                        |     |                           |
|  Document Upload API   +---->+  PDF Processor            |
|                        |     |                           |
+------------------------+     +--------+------------------+
                                        |
                                        v
                              +---------+------------------+
                              |                            |
                              |  Détection automatique    |
                              |  de besoin d'OCR          |
                              |                            |
                              +-+-------------------+------+
                                |                   |
                                v                   v
              +------------------+     +------------+-------+
              |                  |     |                    |
              |  Extraction      |     |  OCRmyPDF         |
              |  directe du texte|     |  (Tesseract)      |
              |                  |     |                    |
              +------------------+     +--------------------+
                                              |
                                              v
                                      +-------+---------+
                                      |                 |
                                      | Tableau de bord |
                                      | OCR             |
                                      |                 |
                                      +-----------------+
```

## Tableau de bord OCR

```
+-------------------+     +------------------------+
|                   |     |                        |
| Interface         +---->+ API Tableau de bord    |
| utilisateur       |     |                        |
+-------------------+     +-----------+------------+
                                      |
                                      v
                           +----------+------------+
                           |                       |
                           |  OCRTaskManager       |
                           |                       |
                           +-----------+-----------+
                                       |
                                       v
              +---------------------+  |  +----------------------+
              |                     |  |  |                      |
              | ExportService       |<-+->| MetricsCollector    |
              |                     |     |                      |
              +---------------------+     +----------------------+
                                              |
                                              v
                                      +-------+---------+
                                      |                 |
                                      | WebSocket       |
                                      | Notifications   |
                                      |                 |
                                      +-----------------+
```

## Système RAG (Retrieval Augmented Generation)

```
+-------------------+     +------------------------+
|                   |     |                        |
|  Question User    +---->+  Question Classifier   |
|                   |     |                        |
+-------------------+     +-----------+------------+
                                      |
                                      v
                           +----------+------------+
                           |                       |
                           |  Vectorisation        |
                           |  (VoyageAI)           |
                           |                       |
                           +-----------+-----------+
                                       |
                                       v
                           +-----------+-----------+
                           |                       |
                           |  Recherche similitude |
                           |  (Qdrant)             |
                           |                       |
                           +-----------+-----------+
                                       |
                                       v
                           +-----------+-----------+
                           |                       |
                           |  Augmentation Prompt  |
                           |  avec contexte        |
                           |                       |
                           +-----------+-----------+
                                       |
                                       v
                           +-----------+-----------+
                           |                       |
                           |  LLM Generation       |
                           |  (Anthropic Claude)   |
                           |                       |
                           +-----------+-----------+
```

## Gestion des timeouts et traitement par lots

Pour gérer les problèmes de timeout lors du traitement de gros documents PDF (>28Mo), le système utilise:

- Un mécanisme de traitement par lots (chunk de texte) pour les grands documents
- Une gestion de timeout configurable (actuellement 600 secondes)
- Un système de reprise sur erreur permettant de continuer le traitement là où il s'est arrêté

## Patterns de conception utilisés

L'application implémente plusieurs patterns de conception notables:

- **Singleton**: Utilisé pour le PollingManager afin d'éviter les appels API redondants
- **Factory**: Implémenté pour la création des différents types de processeurs de documents
- **Strategy**: Utilisé pour sélectionner la méthode d'OCR appropriée selon le type de document
- **Observer**: Implémenté via WebSockets pour notifier les clients des changements d'état

## Points d'extension futurs

L'architecture actuelle prévoit plusieurs points d'extension pour les fonctionnalités futures:

1. Intégration avec Google Cloud Document AI pour l'OCR avancé
2. Support de Vision AI pour les schémas techniques
3. Système de mémoire à court et long terme
4. Authentification et autorisation utilisateur
5. Personnalisation des prompts et templates via interface admin
