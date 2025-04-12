# Index de la documentation technique Technicia

> **ℹ️ Note importante ℹ️**  
> Ce document sert d'index central pour toute la documentation technique du projet Technicia.
> Il a été créé suite à la réorganisation de la documentation le 1er avril 2025.
>
> Dernière mise à jour : 1 avril 2025

## 1. Documentation principale

### Guide d'utilisation
- [README.md](./README.md) - Vue d'ensemble du projet et guide de démarrage rapide
- [GUIDE_MISE_EN_ROUTE.md](./GUIDE_MISE_EN_ROUTE.md) - Guide détaillé pour démarrer avec Technicia
- [INSTALLATION_OCR.md](./INSTALLATION_OCR.md) - Guide d'installation des composants OCR

### Plan d'implémentation et suivi
- [Plan d'implémentation](./MVP/PLAN_IMPLEMENTATION.md) - Plan détaillé d'implémentation du MVP
- [Suivi d'implémentation](./MVP/SUIVI_IMPLEMENTATION.md) - État actuel de l'implémentation

## 2. Documentation technique

### Architecture et conception
- [Architecture globale](./architecture/ARCHITECTURE_GLOBALE.md) - Vue d'ensemble de l'architecture
- [Diagramme des classes RAG-OCR](./architecture/DIAGRAMME_CLASSES_RAG_OCR.md) - Relations entre les composants RAG et OCR

### Traitement de documents
- [Système de traitement de documents](./technique/TRAITEMENT_DOCUMENTS.md) - Architecture complète du système de traitement de documents et extraction de haute qualité
- [Système de traitement et queues](./technique/SYSTEME_TRAITEMENT_QUEUE.md) - Pipelines et file d'attente pour le traitement des documents

### Interface utilisateur
- [Tableau de bord OCR](./technique/TABLEAU_BORD_OCR.md) - Documentation complète du tableau de bord OCR
- [Intégration OCR-RAG](./technique/OCR_RAG_INTEGRATION.md) - Détails sur l'intégration entre OCR et RAG

## 3. Documentation API

- [API de traitement de documents](./api/API_DOCUMENT_PROCESSING.md) - Endpoints pour le traitement de documents
- [API du tableau de bord OCR](./api/API_DASHBOARD_OCR.md) - Endpoints pour l'interface de gestion OCR

## 4. Maintenance et support

- [Changelog](./CHANGELOG.md) - Historique des modifications
- [Bugfixes](./BUGFIXES.md) - Corrections de bugs
- [Diagnostics](./DIAGNOSTICS.md) - Outils et procédures de diagnostic
- [Résolution de problèmes](./TROUBLESHOOTING/README.md) - Guides de dépannage

## 5. Documents archivés

*Les documents suivants ont été remplacés par des versions plus récentes et sont conservés uniquement pour référence historique :*

- [~~OCR_DASHBOARD_COMPLET.md~~](./OCR_DASHBOARD_COMPLET.md) → Remplacé par [TABLEAU_BORD_OCR.md](./technique/TABLEAU_BORD_OCR.md)
- [~~DOCUMENT_PROCESSING.md~~](./DOCUMENT_PROCESSING.md) → Remplacé par [TRAITEMENT_DOCUMENTS.md](./technique/TRAITEMENT_DOCUMENTS.md)
- [~~PIPELINE.md~~](./PIPELINE.md) → Remplacé par [SYSTEME_TRAITEMENT_QUEUE.md](./technique/SYSTEME_TRAITEMENT_QUEUE.md)
- [~~OCR_HYBRIDE.md~~](./OCR_HYBRIDE.md) → Intégré dans [TRAITEMENT_DOCUMENTS.md](./technique/TRAITEMENT_DOCUMENTS.md)
- [~~PLAN_PHASE3.md~~](./MVP/PLAN_PHASE3.md) → Intégré dans [PLAN_IMPLEMENTATION.md](./MVP/PLAN_IMPLEMENTATION.md)
