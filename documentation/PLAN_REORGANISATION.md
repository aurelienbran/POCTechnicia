# Plan de réorganisation de la documentation

Ce document résume le plan de réorganisation de la documentation pour l'aligner avec le nouveau plan d'implémentation réorganisé.

Date : 1 avril 2025

## 1. Documents principaux du projet

### Documents à conserver et mettre à jour
- `README.md` - Mise à jour pour refléter la nouvelle structure 
- `GUIDE_MISE_EN_ROUTE.md` - Conserver et mettre à jour
- `INSTALLATION_OCR.md` - Conserver et mettre à jour les dépendances OCR

### Documents obsolètes à remplacer
- `MVP/PLAN_IMPLEMENTATION.md` → Remplacer par `MVP/PLAN_IMPLEMENTATION_REORGANISE.md` et renommer
- `MVP/SUIVI_IMPLEMENTATION.md` → Remplacer par `MVP/SUIVI_IMPLEMENTATION_REORGANISE.md` et renommer
- `MVP/PLAN_PHASE3.md` → Intégrer dans le nouveau plan d'implémentation

## 2. Documentation technique

### Documents à fusionner
- `DOCUMENT_PROCESSING.md` + `technique/EXTRACTION_HAUTE_QUALITE.md` → Nouveau `technique/TRAITEMENT_DOCUMENTS.md`
- `OCR_DASHBOARD_COMPLET.md` + `technique/OCR_DASHBOARD.md` + `technique/DASHBOARD_OCR.md` → Nouveau `technique/TABLEAU_BORD_OCR.md`
- `technique/OCR_QUEUE_SYSTEM.md` + `PIPELINE.md` → Nouveau `technique/SYSTEME_TRAITEMENT_QUEUE.md`

### Documents à conserver avec mise à jour
- `architecture/ARCHITECTURE_GLOBALE.md` - Mise à jour avec la nouvelle organisation
- `architecture/DIAGRAMME_CLASSES_RAG_OCR.md` - Mise à jour avec les nouvelles interactions

### Documents potentiellement obsolètes à évaluer
- `OCR_HYBRIDE.md` - Vérifier la pertinence et fusionner si nécessaire
- `DUAL_FRONTEND.md` - Vérifier la pertinence et fusionner si nécessaire
- `NEXT.md` - Remplacer par les informations du nouveau plan

## 3. Documentation API

### Documents à conserver
- `api/API_DOCUMENT_PROCESSING.md` - Mise à jour avec les nouveaux endpoints
- `api/API_DASHBOARD_OCR.md` - Mise à jour avec les nouvelles fonctionnalités

## 4. Documents de support et maintenance

### Documents à conserver
- `BUGFIXES.md` - Conserver et mettre à jour
- `CHANGELOG.md` - Conserver et mettre à jour
- `DIAGNOSTICS.md` - Conserver et mettre à jour
- `TROUBLESHOOTING/*.md` - Conserver et mettre à jour

## Plan d'action
1. Sauvegarder tous les documents existants
2. Effectuer les fusions nécessaires
3. Mettre à jour les documents conservés
4. Remplacer les documents obsolètes
5. Créer un index de documentation pour faciliter la navigation
