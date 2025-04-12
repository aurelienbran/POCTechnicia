# API de Traitement de Documents

> **ℹ️ Note ℹ️**  
> Ce document décrit l'API de traitement de documents et ses fonctionnalités OCR.  
> Pour les APIs liées au tableau de bord OCR, consultez : [OCR_DASHBOARD_COMPLET.md](../OCR_DASHBOARD_COMPLET.md)

Ce document décrit l'API RESTful pour le traitement de documents implémentée dans le cadre du MVP Technicia. Cette API permet d'extraire le texte des documents, d'appliquer l'OCR si nécessaire, et de découper le contenu en chunks pour l'indexation vectorielle.

## Base URL

```
/api/documents
```

## Authentification

Toutes les routes de l'API nécessitent une authentification. Utilisez le token JWT dans l'en-tête Authorization :

```
Authorization: Bearer <token>
```

## Endpoints

### 1. Traiter un Document

Traite un document en l'extrayant et le découpant en chunks.

**URL** : `/documents/process`

**Méthode** : `POST`

**Content-Type** : `multipart/form-data`

**Paramètres** :

| Nom | Type | Requis | Description |
|-----|------|--------|-------------|
| file | File | Oui | Le fichier à traiter |
| options | JSON string | Non | Options de traitement au format JSON |
| synchronous | Boolean | Non | Si true, le traitement est synchrone (défaut: false) |

**Options disponibles** :

```json
{
  "chunk_size": 1000,          // Taille maximale d'un chunk (caractères)
  "chunk_overlap": 100,        // Chevauchement entre chunks consécutifs
  "enable_ocr": true,          // Activer l'OCR pour les documents numérisés
  "extract_tables": false,     // Extraire les tableaux des documents
  "include_text_content": false, // Inclure le contenu textuel complet dans la réponse
  "skip_chunking": false       // Ignorer l'étape de chunking
}
```

**Exemple de requête** :

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf" \
  -F "options={\"chunk_size\":1000,\"enable_ocr\":true}" \
  -F "synchronous=true" \
  http://localhost:8000/api/documents/process
```

**Réponse (traitement synchrone)** :

```json
{
  "success": true,
  "metadata": {
    "title": "Exemple de document",
    "author": "Technicia",
    "pages": 5,
    "ocr_processed": true
  },
  "processing_time": 2.34,
  "chunks_count": 12,
  "chunks": [
    "Contenu du premier chunk...",
    "Contenu du deuxième chunk...",
    "..."
  ]
}
```

**Réponse (traitement asynchrone)** :

```json
{
  "success": true,
  "task_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "filename": "document.pdf",
  "status": "processing"
}
```

### 2. Traiter un Lot de Documents

Traite plusieurs documents en parallèle.

**URL** : `/documents/batch-process`

**Méthode** : `POST`

**Content-Type** : `multipart/form-data`

**Paramètres** :

| Nom | Type | Requis | Description |
|-----|------|--------|-------------|
| files | File[] | Oui | Liste des fichiers à traiter |
| options | JSON string | Non | Options de traitement au format JSON |

**Exemple de requête** :

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "files=@document1.pdf" \
  -F "files=@document2.docx" \
  -F "options={\"chunk_size\":1000,\"enable_ocr\":true}" \
  http://localhost:8000/api/documents/batch-process
```

**Réponse** :

```json
{
  "success": true,
  "task_id": "b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7",
  "files_count": 2,
  "status": "processing"
}
```

### 3. Traiter et Indexer un Document

Traite un document et indexe ses chunks dans la base vectorielle.

**URL** : `/documents/process-and-index`

**Méthode** : `POST`

**Content-Type** : `multipart/form-data`

**Paramètres** :

| Nom | Type | Requis | Description |
|-----|------|--------|-------------|
| file | File | Oui | Le fichier à traiter et indexer |
| processing_options | JSON string | Non | Options de traitement au format JSON |
| indexing_options | JSON string | Non | Options d'indexation au format JSON |

**Options d'indexation disponibles** :

```json
{
  "collection_name": "documents",  // Nom de la collection où indexer le document
  "embedding_provider": "voyageai", // Provider d'embeddings à utiliser
  "metadata_fields": ["title", "author", "date"] // Champs de métadonnées à inclure
}
```

**Exemple de requête** :

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf" \
  -F "processing_options={\"chunk_size\":800,\"enable_ocr\":true}" \
  -F "indexing_options={\"collection_name\":\"documents\",\"embedding_provider\":\"voyageai\"}" \
  http://localhost:8000/api/documents/process-and-index
```

**Réponse** :

```json
{
  "success": true,
  "task_id": "c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8",
  "filename": "document.pdf",
  "status": "processing_and_indexing"
}
```

### 4. Vérifier le Statut d'une Tâche

Récupère le statut et le résultat d'une tâche de traitement.

**URL** : `/documents/task/{task_id}`

**Méthode** : `GET`

**Exemple de requête** :

```bash
curl -X GET \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/documents/task/a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

**Réponse (tâche terminée)** :

```json
{
  "task_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "status": "completed",
  "result": {
    "success": true,
    "metadata": {
      "title": "Exemple de document",
      "pages": 5
    },
    "chunks_count": 12,
    "processing_time": 3.45
  }
}
```

**Réponse (tâche en cours)** :

```json
{
  "task_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "status": "processing"
}
```

**Réponse (tâche échouée)** :

```json
{
  "task_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "status": "failed",
  "error": "Le format du fichier n'est pas supporté"
}
```

### 5. Formats de Fichiers Supportés

Liste les formats de fichiers supportés par le système.

**URL** : `/documents/supported-formats`

**Méthode** : `GET`

**Exemple de requête** :

```bash
curl -X GET \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/documents/supported-formats
```

**Réponse** :

```json
{
  "success": true,
  "supported_formats": [
    ".pdf",
    ".docx",
    ".doc",
    ".txt",
    ".rtf",
    ".odt",
    ".pptx",
    ".xlsx"
  ]
}
```

### 6. Analyser un Document

Analyse un document pour déterminer ses caractéristiques sans le traiter complètement.

**URL** : `/documents/analyze`

**Méthode** : `POST`

**Content-Type** : `multipart/form-data`

**Paramètres** :

| Nom | Type | Requis | Description |
|-----|------|--------|-------------|
| file | File | Oui | Le fichier à analyser |

**Exemple de requête** :

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf" \
  http://localhost:8000/api/documents/analyze
```

**Réponse** :

```json
{
  "success": true,
  "filename": "document.pdf",
  "metadata": {
    "title": "Exemple de document",
    "author": "Technicia",
    "pages": 15,
    "creation_date": "2025-03-15T10:30:00Z"
  },
  "needs_ocr": true,
  "mime_type": "application/pdf"
}
```

## Gestion des Erreurs

L'API utilise les codes de statut HTTP standard pour indiquer le succès ou l'échec d'une requête :

* **200 OK** : La requête a réussi
* **400 Bad Request** : La requête est incorrecte (fichier manquant, options invalides, etc.)
* **401 Unauthorized** : Authentification requise
* **404 Not Found** : Ressource non trouvée
* **500 Internal Server Error** : Erreur interne du serveur

En cas d'erreur, le corps de la réponse contient un message descriptif :

```json
{
  "detail": "Description de l'erreur"
}
```

## Traitement des Fichiers Volumineux

Pour les fichiers PDF volumineux (>28 Mo) nécessitant un OCR, l'API implémente une approche par batches pour éviter les timeouts :

1. **Conversion initiale** : Le document est d'abord converti en texte (avec OCR si nécessaire)
2. **Découpage en chunks** : Le texte est découpé en chunks de taille appropriée
3. **Traitement par batches** : Les chunks sont traités par lots plus petits
4. **Reprise sur erreur** : En cas d'échec d'un batch, le traitement peut reprendre à partir du dernier batch réussi

Pour activer ce mode, utilisez le paramètre `batch_size` dans les options de traitement :

```json
{
  "enable_ocr": true,
  "chunk_size": 500,
  "batch_size": 10  // Traiter 10 chunks par batch
}
```

## Exemple d'Intégration

### Traitement Asynchrone avec Vérification du Statut

```javascript
// Envoyer le document pour traitement
async function processDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('options', JSON.stringify({
    chunk_size: 1000,
    enable_ocr: true
  }));
  
  const response = await fetch('/api/documents/process', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  const data = await response.json();
  if (data.success) {
    pollTaskStatus(data.task_id);
  }
}

// Vérifier périodiquement le statut de la tâche
function pollTaskStatus(taskId) {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/documents/task/${taskId}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    const data = await response.json();
    if (data.status === 'completed') {
      clearInterval(interval);
      displayResults(data.result);
    } else if (data.status === 'failed') {
      clearInterval(interval);
      displayError(data.error);
    }
  }, 1000);
}
```

### Traitement Synchrone Simple

```javascript
async function processSynchronously(file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('synchronous', 'true');
  
  try {
    const response = await fetch('/api/documents/process', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    
    const data = await response.json();
    if (data.success) {
      displayResults(data);
    } else {
      displayError(data.error_message);
    }
  } catch (error) {
    displayError('Erreur de connexion au serveur');
  }
}
