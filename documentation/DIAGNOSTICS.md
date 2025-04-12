# Guide des Outils de Diagnostic

> **ℹ️ Note ℹ️**  
> Pour les diagnostics spécifiques au tableau de bord OCR, consultez également : [OCR_DASHBOARD_COMPLET.md](./OCR_DASHBOARD_COMPLET.md)

## Vue d'ensemble

Les outils de diagnostic permettent d'analyser et d'améliorer la qualité des réponses du système RAG en examinant trois composants principaux :
1. Le traitement des PDFs
2. La qualité des recherches
3. La structure des réponses

## Composants

### 1. PDF Analyzer
Analyse le traitement des documents PDF :
- Structure des sections
- Distribution des chunks
- Problèmes potentiels

```python
stats = await pdf_analyzer.analyze_sections(file_path)
# Retourne :
{
    "total_sections": 10,
    "sections_with_content": 8,
    "avg_section_length": 450,
    "sections_details": [...]
}
```

### 2. Search Analyzer
Évalue la qualité des recherches :
- Scores de similarité
- Couverture des sections
- Patterns de requête

```python
stats = await search_analyzer.analyze_search_results("EL-37 problèmes")
# Retourne :
{
    "total_results": 6,
    "avg_score": 0.75,
    "section_coverage": {...},
    "potential_issues": [...]
}
```

### 3. Response Analyzer
Analyse la structure et le contenu des réponses :
- Présence des sections requises
- Contenu technique
- Utilisation des sources

```python
stats = response_analyzer.analyze_response_structure(response)
# Retourne :
{
    "sections_present": {...},
    "content_stats": {...},
    "potential_issues": [...]
}
```

## Diagnostics OCR

Les outils de diagnostic OCR permettent d'analyser et d'optimiser la qualité de reconnaissance de texte dans les documents PDF.

### 1. OCR Quality Analyzer
Évalue la qualité de la reconnaissance de texte :
- Score de confiance par page
- Détection des zones problématiques
- Analyse comparative entre fournisseurs OCR

```python
ocr_metrics = await ocr_analyzer.analyze_quality(file_path)
# Retourne :
{
    "confidence_score": 0.87,
    "problematic_areas": [
        {"page": 2, "zone": "table", "confidence": 0.65},
        {"page": 5, "zone": "image_caption", "confidence": 0.72}
    ],
    "recommended_provider": "google_document_ai"
}
```

### 2. OCR Performance Analyzer
Évalue les performances des différents fournisseurs OCR :
- Temps de traitement par page
- Consommation de ressources
- Comparaison des résultats entre fournisseurs

```python
performance = await ocr_analyzer.benchmark_providers(file_path)
# Retourne :
{
    "providers": {
        "tesseract": {"time": 1.2, "quality": 0.81},
        "azure": {"time": 0.8, "quality": 0.88},
        "google": {"time": 0.9, "quality": 0.92}
    },
    "optimal_provider": "google"
}
```

### 3. Interface de Diagnostic dans le Tableau de Bord
Le tableau de bord OCR intègre une interface de diagnostic accessible via :
```
http://localhost:8000/dashboard/diagnostics
```

Cette interface permet de :
- Exécuter des analyses de qualité sur demande
- Visualiser les zones problématiques sur les documents
- Comparer visuellement les résultats entre différents fournisseurs
- Générer des rapports détaillés pour l'optimisation

### 4. Tests Automatisés
Les scripts de test automatisés pour l'OCR se trouvent dans :
```
scripts/tests/ocr_quality_tests.py
```

Exécution des tests automatisés :
```bash
python scripts/tests/ocr_quality_tests.py --doc-type=technical --provider=all
```

## API Endpoints

### PDF Analysis
```bash
POST /api/v1/diagnostic/pdf
{
    "file_path": "path/to/file.pdf"
}
```

### Search Analysis
```bash
POST /api/v1/diagnostic/search
{
    "query": "EL-37 problèmes"
}
```

### Response Analysis
```bash
POST /api/v1/diagnostic/response
{
    "response": "DESCRIPTION\n..."
}
```

### Full Diagnostic
```bash
POST /api/v1/diagnostic/full
{
    "file_path": "path/to/file.pdf",
    "query": "EL-37 problèmes",
    "response": "DESCRIPTION\n..."
}
```

## Script Utilitaire

Un script utilitaire `diagnostic_tool.py` est disponible pour faciliter l'utilisation des outils de diagnostic. Voir la section "Utilisation du Script Utilitaire" pour plus de détails.

## Interprétation des Résultats

### Scores de Similarité
- > 0.8 : Excellente correspondance
- 0.6-0.8 : Bonne correspondance
- 0.4-0.6 : Correspondance moyenne
- < 0.4 : Faible correspondance

### Problèmes Courants

1. **PDF Processing**
   - Sections non détectées
   - Chunks trop grands/petits
   - Contenu mal structuré

2. **Recherche**
   - Scores de similarité faibles
   - Couverture limitée des sections
   - Résultats non pertinents

3. **Réponses**
   - Sections manquantes
   - Contenu technique insuffisant
   - Sources mal citées

## Bonnes Pratiques

1. **Analyse des PDFs**
   - Vérifier la structure des sections avant l'indexation
   - Optimiser la taille des chunks
   - Valider la couverture du contenu

2. **Optimisation des Recherches**
   - Utiliser des références de section précises
   - Inclure des mots-clés techniques
   - Vérifier la distribution des scores

3. **Amélioration des Réponses**
   - Assurer la présence de toutes les sections
   - Inclure des détails techniques pertinents
   - Citer les sources avec leurs scores

## Maintenance

1. **Monitoring Régulier**
   - Analyser les tendances des scores
   - Identifier les patterns problématiques
   - Suivre la qualité des réponses

2. **Ajustements**
   - Paramètres de chunking
   - Seuils de similarité
   - Structure des prompts

3. **Documentation**
   - Mettre à jour les guides
   - Noter les problèmes récurrents
   - Documenter les solutions
