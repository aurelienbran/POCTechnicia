# Intégration OCR-RAG - Documentation technique

## Vue d'ensemble

L'intégration OCR-RAG établit une connexion automatique entre le système de reconnaissance optique de caractères (OCR) et le système de Retrieval-Augmented Generation (RAG). Cette intégration permet d'indexer automatiquement les documents traités par OCR dans la base de connaissances vectorielle, rendant leur contenu immédiatement disponible pour les requêtes sémantiques.

Date de création : Avril 2025  
Statut : Opérationnel  
Auteur : Équipe Technicia

## Architecture

L'intégration OCR-RAG utilise une architecture basée sur les événements, où les notifications de tâches OCR déclenchent automatiquement l'indexation des documents. Le flux de travail est composé des étapes suivantes :

1. **Traitement OCR** - Le document est traité par le système OCR
2. **Notification d'achèvement** - Une fois l'OCR terminé, une notification est émise
3. **Déclenchement de l'indexation** - La notification active le processus d'indexation RAG
4. **Extraction et chunking** - Le document est analysé et segmenté
5. **Génération d'embeddings** - Des embeddings vectoriels sont créés pour chaque chunk
6. **Indexation** - Les embeddings sont stockés dans la base vectorielle

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ OCR Queue   │────▶│ Notification │────▶│ RAG Indexing │
│ Manager     │     │ System       │     │ Process      │
└─────────────┘     └──────────────┘     └──────────────┘
       │                                         │
       ▼                                         ▼
┌─────────────┐                           ┌──────────────┐
│ Document    │                           │ Vector       │
│ Processing  │                           │ Database     │
└─────────────┘                           └──────────────┘
```

## Composants principaux

### Module d'intégration OCR-RAG (`app/core/integrations/ocr_rag_integration.py`)

- **Responsabilité** : Fournir les fonctions d'indexation et gérer les notifications de tâches OCR
- **Fonctions clés** :
  - `index_ocr_document()` : Indexe un document traité par OCR
  - `register_ocr_rag_integration()` : Enregistre les callbacks d'intégration
  - `ocr_completed_callback()` : Callback appelé après achèvement d'une tâche OCR

### Initialisation (`app/main.py`)

- **Responsabilité** : Configurer l'intégration au démarrage de l'application
- **Fonctionnalités** :
  - Enregistrement des callbacks automatiques
  - Gestion des erreurs d'initialisation

## Flux de données détaillé

1. **Soumission de document**
   - L'utilisateur soumet un document pour OCR via le tableau de bord
   - Le document est ajouté à la file d'attente OCR

2. **Traitement OCR**
   - Le gestionnaire de file d'attente OCR traite le document
   - Le document est traité page par page avec OCR (si nécessaire)
   - Le résultat du traitement OCR est enregistré

3. **Notification d'achèvement**
   - Lorsque la tâche OCR est terminée, le gestionnaire de file d'attente émet une notification
   - Le callback `ocr_completed_callback` est appelé avec les détails de la tâche

4. **Préparation pour l'indexation**
   - Les métadonnées OCR sont collectées (qualité, confiance, fournisseur, etc.)
   - Le chemin du document traité est déterminé

5. **Lancement de l'indexation**
   - La fonction `index_ocr_document` est appelée
   - Une tâche asynchrone `process_and_index_document_task` est lancée

6. **Indexation RAG**
   - Le document est traité (extraction de texte, chunking)
   - Des embeddings sont générés pour chaque chunk
   - Les chunks avec leurs embeddings sont stockés dans la base vectorielle

7. **Finalisation**
   - Le document est maintenant disponible pour les requêtes RAG
   - Les métadonnées OCR sont stockées avec les chunks pour référence future

## Configuration et paramètres

Le module d'intégration OCR-RAG utilise les paramètres suivants, configurables via le fichier `.env` ou les variables d'environnement :

| Paramètre | Description | Valeur par défaut |
|-----------|-------------|-------------------|
| `DEFAULT_RAG_COLLECTION` | Collection pour l'indexation RAG | `"documents"` |
| `DEFAULT_EMBEDDING_PROVIDER` | Fournisseur d'embeddings | `"voyage"` |
| `EMBEDDING_BATCH_SIZE` | Taille de lot pour la génération d'embeddings | `10` |

## Métadonnées d'intégration

Les métadonnées suivantes sont transmises du système OCR au système RAG :

| Métadonnée | Description |
|------------|-------------|
| `ocr_processed` | Booléen indiquant si le document a été traité par OCR |
| `ocr_task_id` | Identifiant unique de la tâche OCR |
| `ocr_quality` | Score de qualité globale OCR (0-100) |
| `ocr_confidence` | Score de confiance OCR moyen (0-100) |
| `ocr_provider` | Fournisseur OCR utilisé (ocrmypdf, tesseract, document_ai) |
| `ocr_language` | Langue(s) OCR utilisée(s) |
| `processing_time` | Temps de traitement OCR en secondes |
| `pages_count` | Nombre de pages du document |

## Cas d'utilisation

### Exemple 1: Traitement d'un document scanné

1. Un utilisateur téléverse un document PDF scanné sans texte intégré
2. Le système OCR détecte l'absence de texte et applique l'OCR
3. Une fois l'OCR terminé, l'intégration OCR-RAG est automatiquement déclenchée
4. Le document est indexé dans la base de connaissances

### Exemple 2: Traitement par lots

1. Un utilisateur téléverse plusieurs documents via l'interface par lots
2. Chaque document est traité par OCR selon sa priorité
3. À l'achèvement de chaque document, son contenu est automatiquement indexé
4. L'utilisateur peut immédiatement effectuer des recherches sur les documents traités

## Gestion des erreurs

Le système OCR-RAG gère les erreurs selon les principes suivants :

1. **Isolation** - Une erreur dans l'indexation n'affecte pas le résultat du traitement OCR
2. **Journalisation** - Toutes les erreurs sont enregistrées dans les logs avec la trace complète
3. **Reprise** - En cas d'échec d'indexation, le système conserve le document traité pour une reprise manuelle
4. **Notification** - Les erreurs d'indexation sont signalées via les canaux de notification existants

## Tests et validation

L'intégration OCR-RAG doit être testée selon les scénarios suivants :

1. **Test fonctionnel** - Vérifier que l'indexation est déclenchée après un traitement OCR réussi
2. **Test de robustesse** - Vérifier la gestion des erreurs en cas de problème d'indexation
3. **Test de performances** - Mesurer l'impact sur les performances du système global
4. **Test de qualité** - Vérifier que les métadonnées OCR sont correctement transférées

## Évolutions futures

- **Recherche ciblée OCR** - Permettre la recherche spécifiquement dans les documents OCR avec filtrage par qualité
- **Amélioration itérative** - Réindexation automatique des documents lorsqu'un meilleur OCR devient disponible
- **Filtrage intelligent** - Ignorer automatiquement les parties du document ayant une faible confiance OCR
- **Métadonnées enrichies** - Ajouter des métadonnées supplémentaires comme le taux d'erreur de caractères

## Références

- [Documentation OCR Queue Manager](./OCR_QUEUE_SYSTEM.md)
- [Documentation Tableau de bord OCR](./OCR_DASHBOARD.md)
- [Documentation RAG](./RAG_SYSTEM.md)
