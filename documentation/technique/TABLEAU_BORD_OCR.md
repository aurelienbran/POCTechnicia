# Tableau de bord OCR - Documentation technique unifiée

> **ℹ️ Note importante ℹ️**  
> Ce document technique unifié décrit l'architecture, le fonctionnement et l'utilisation du tableau de bord OCR dans le projet Technicia.
>
> Dernière mise à jour : 1 avril 2025

## 1. Vue d'ensemble

Le tableau de bord OCR est une interface complète pour la surveillance, la gestion et l'optimisation des tâches de reconnaissance optique de caractères (OCR) dans la plateforme Technicia. Il permet un suivi en temps réel des performances, l'analyse des métriques et l'exportation de rapports détaillés.

### 1.1 Fonctionnalités principales

- **Vue d'ensemble des tâches OCR** ✅
  - Affichage des tâches en cours, en attente, terminées et en erreur
  - Statistiques globales sur le traitement des documents
  - Indicateurs de performance clés (KPI)

- **Gestion des tâches OCR** ✅
  - Création de nouvelles tâches OCR
  - Priorisation des tâches dans la file d'attente
  - Pause, reprise et annulation des tâches
  - Retraitement des documents avec différentes options

- **Surveillance en temps réel** ✅
  - Mise à jour en direct via WebSockets
  - Visualisation de la progression des tâches
  - Notifications pour les changements d'état importants

- **Métrique et rapports** ✅
  - Graphiques de performance OCR
  - Statistiques sur les types de documents traités
  - Rapports sur les taux d'erreur et les temps de traitement
  - Exportation des données en formats CSV et PDF

- **Validation des extractions** 🔄
  - Affichage côte à côte du document original et du texte extrait
  - Identification des zones de faible confiance
  - Interface de correction manuelle
  - Feedback pour amélioration continue

- **Configuration du système OCR** ✅
  - Paramétrage des options OCR par défaut
  - Configuration des priorités pour différents types de documents
  - Gestion des seuils de confiance pour la validation

## 2. Architecture du système

### 2.1 Vue d'ensemble de l'architecture

Le tableau de bord OCR repose sur une architecture à plusieurs couches :

```
┌───────────────────────────────┐
│           Frontend            │
│    (HTML/CSS/JS, Handlebars)  │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│      API REST & WebSockets    │
│      (FastAPI, SocketIO)      │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│      OCRQueueManager          │
│   (Gestionnaire de tâches)    │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│     Moteurs OCR & Processeurs │
│  (OCRmyPDF, Tesseract, etc.)  │
└───────────────────────────────┘
```

### 2.2 Composants principaux

1. **Backend**
   - **OCRQueueManager** : Gestion de la file d'attente des tâches OCR
   - **API RESTful** : Endpoints pour les opérations CRUD
   - **Système WebSocket** : Communication en temps réel
   - **Services de traitement** : Exécution des tâches OCR

2. **Frontend**
   - **Interface utilisateur HTML/CSS/JS** : Tableaux, graphiques et formulaires
   - **Client WebSocket** : Mise à jour en temps réel des données
   - **Composants interactifs** : Gestion des actions utilisateur
   - **Visualisations** : Graphiques et tableaux de bord

## 3. Implémentation technique

### 3.1 Backend

#### 3.1.1 OCRQueueManager

Le gestionnaire de file d'attente OCR (`OCRQueueManager`) est implémenté dans le module `app/core/file_processing/ocr/ocr_queue_manager.py`. Ses principales fonctionnalités sont :

- Gestion des priorités des tâches OCR
- Contrôle d'exécution (pause, reprise, annulation)
- Suivi de la progression et gestion d'état
- Stockage persistant des tâches
- Reprise après redémarrage du serveur

```python
# Exemple d'utilisation du OCRQueueManager
from app.core.file_processing.ocr.ocr_queue_manager import OCRQueueManager

# Obtenir l'instance singleton
queue_manager = OCRQueueManager()

# Ajouter une tâche à la file d'attente
task_id = await queue_manager.add_task(
    file_path='/chemin/vers/document.pdf',
    priority=5,
    user_id='user123',
    ocr_options={'enable_vision_ai': True}
)

# Obtenir des informations sur une tâche
task_info = await queue_manager.get_task(task_id)

# Contrôler l'exécution d'une tâche
await queue_manager.pause_task(task_id)
await queue_manager.resume_task(task_id)
await queue_manager.cancel_task(task_id)
```

#### 3.1.2 API REST

L'API REST du tableau de bord OCR est implémentée dans `app/api/endpoints/ocr_dashboard.py` et expose les endpoints suivants :

- `GET /api/ocr/tasks` - Récupération de la liste des tâches
- `GET /api/ocr/tasks/{task_id}` - Récupération d'une tâche spécifique
- `POST /api/ocr/tasks` - Création d'une nouvelle tâche
- `PATCH /api/ocr/tasks/{task_id}` - Mise à jour d'une tâche existante
- `DELETE /api/ocr/tasks/{task_id}` - Suppression d'une tâche
- `POST /api/ocr/tasks/{task_id}/action` - Exécution d'actions sur une tâche (pause, reprise, etc.)
- `GET /api/ocr/metrics` - Récupération des métriques OCR
- `GET /api/ocr/export` - Exportation des données OCR
- `GET /api/ocr/download/{export_id}` - Téléchargement d'un export

Consultez la [documentation complète de l'API](../api/API_DASHBOARD_OCR.md) pour plus de détails.

#### 3.1.3 Système WebSocket

L'architecture des WebSockets du tableau de bord OCR est implémentée dans `app/api/websockets/ocr_dashboard.py`. Elle comprend les éléments suivants :

##### Gestionnaire de connexions (`DashboardConnectionManager`)

Cette classe centrale gère toutes les connexions WebSocket et assure les fonctionnalités suivantes :
- Gestion des connexions pour différentes vues (tableau de bord, tâches actives, détail de tâche, métriques)
- Diffusion des mises à jour aux clients connectés
- Gestion des abonnements aux événements spécifiques
- Authentification et autorisation

```python
# Exemple de code serveur WebSocket
@router.websocket("/ws/ocr/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await manager.connect(websocket, "dashboard")
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

##### Types de messages WebSocket

Le système prend en charge les types de messages suivants :
- `task_update` : Mises à jour sur l'état d'une tâche OCR
- `queue_update` : Changements dans la file d'attente des tâches
- `metrics_update` : Mises à jour des métriques de performance
- `system_notification` : Notifications système importantes
- `error_alert` : Alertes d'erreurs critiques

### 3.2 Frontend

#### 3.2.1 Interface utilisateur

L'interface utilisateur du tableau de bord OCR est implémentée avec les technologies suivantes :
- HTML/CSS pour la structure et le style
- JavaScript pour l'interactivité
- Chart.js pour les visualisations graphiques
- Bootstrap pour les composants UI

#### 3.2.2 Structure de l'interface

Le tableau de bord est structuré en plusieurs sections :

1. **Vue d'ensemble**
   - Résumé des tâches par statut
   - KPIs principaux (taux de réussite, temps moyen, etc.)
   - Graphique d'activité récente

2. **Liste des tâches**
   - Table interactive avec filtres et tri
   - Indicateurs visuels d'état et de progression
   - Actions rapides (pause, reprise, annulation)

3. **Détails de tâche**
   - Informations complètes sur une tâche sélectionnée
   - Logs d'exécution
   - Visualisation du document original et du texte extrait

4. **Métriques et rapports**
   - Graphiques de performance
   - Statistiques détaillées
   - Options d'exportation de données

5. **Configuration**
   - Paramètres OCR
   - Gestion des priorités
   - Configuration des notifications

#### 3.2.3 Client WebSocket

Le client WebSocket est implémenté en JavaScript et gère la connexion en temps réel avec le serveur :

```javascript
// Exemple de code client WebSocket
const socket = new WebSocket(`ws://${window.location.host}/ws/ocr/dashboard`);

socket.onopen = () => {
    console.log('Connexion WebSocket établie');
};

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'task_update':
            updateTaskUI(data.payload);
            break;
        case 'queue_update':
            updateQueueStats(data.payload);
            break;
        case 'metrics_update':
            updateMetricsCharts(data.payload);
            break;
        // ...
    }
};

function subscribeToTask(taskId) {
    socket.send(JSON.stringify({
        action: 'subscribe',
        target: 'task',
        task_id: taskId
    }));
}
```

## 4. Fonctionnalités détaillées

### 4.1 Gestion des tâches OCR

#### 4.1.1 Création de tâche

L'utilisateur peut créer une nouvelle tâche OCR de plusieurs façons :
- Via le formulaire d'upload de fichier
- Par glisser-déposer de documents
- En utilisant l'API programmatiquement

Options configurables lors de la création :
- Priorité de la tâche (1-10)
- Options OCR spécifiques
- Notification par email à la fin du traitement
- Tags pour catégorisation

#### 4.1.2 Priorisation des tâches

Le système de priorisation permet de :
- Attribuer une priorité initiale (1-10)
- Modifier la priorité d'une tâche en attente
- Définir des règles de priorité automatique par type de document
- Appliquer une escalade de priorité pour les tâches en attente depuis longtemps

#### 4.1.3 Contrôle d'exécution

L'interface permet différentes actions sur les tâches :
- **Pause** : Interrompre temporairement l'exécution
- **Reprise** : Continuer une tâche en pause
- **Annulation** : Arrêter définitivement une tâche
- **Retraitement** : Relancer une tâche avec des options différentes
- **Archivage** : Déplacer une tâche terminée vers les archives

### 4.2 Visualisation et analyse

#### 4.2.1 Métriques disponibles

Le tableau de bord affiche diverses métriques :
- **Performance OCR** : Précision estimée, taux d'erreur
- **Efficacité du processus** : Temps de traitement, utilisation des ressources
- **Volume** : Nombre de documents, pages et caractères traités
- **Qualité** : Niveau de confiance, taux de retraitement

#### 4.2.2 Visualisations

Différents types de visualisations sont disponibles :
- Graphiques temporels pour l'évolution des métriques
- Diagrammes à barres pour la comparaison des performances
- Cartes thermiques pour l'identification des goulets d'étranglement
- Indicateurs visuels pour les statuts et alertes

#### 4.2.3 Exportation

Les données peuvent être exportées dans plusieurs formats :
- CSV pour l'analyse dans des outils externes
- PDF pour des rapports formels
- JSON pour l'intégration programmatique

La fonctionnalité d'exportation permet de :
- Sélectionner les métriques à inclure
- Définir la période couverte
- Personnaliser la mise en page du rapport
- Planifier des exports récurrents

### 4.3 Validation et amélioration

#### 4.3.1 Interface de validation

L'interface de validation permet de :
- Afficher côte à côte le document original et le texte extrait
- Surligner les zones de faible confiance
- Comparer les résultats de différents moteurs OCR
- Effectuer des corrections manuelles

#### 4.3.2 Boucle de feedback

Le système intègre une boucle de feedback pour l'amélioration continue :
- Collecte des corrections manuelles
- Analyse des erreurs récurrentes
- Ajustement automatique des paramètres OCR
- Amélioration des règles de sélection des processeurs

## 5. Exemples d'utilisation

### 5.1 Utilisation de l'interface web

1. **Accès au tableau de bord**
   - Naviguez vers `/ocr/dashboard` dans l'application
   - Authentifiez-vous si nécessaire

2. **Création d'une tâche OCR**
   - Cliquez sur "Nouvelle tâche OCR"
   - Téléchargez un document ou spécifiez une URL
   - Configurez les options OCR selon vos besoins
   - Soumettez la tâche

3. **Analyse des résultats**
   - Accédez aux détails d'une tâche en cliquant sur son identifiant
   - Consultez les métriques de performance et les logs d'exécution
   - Téléchargez les résultats OCR une fois le traitement terminé

### 5.2 Utilisation de l'API

```python
# Exemple de code pour l'utilisation de l'API du tableau de bord OCR
import requests
import json

base_url = "http://localhost:8000/api/ocr"

# Authentification
auth_response = requests.post(
    "http://localhost:8000/api/auth/token",
    data={"username": "user", "password": "password"}
)
token = auth_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Création d'une tâche OCR
with open("document.pdf", "rb") as f:
    files = {"file": f}
    data = {
        "priority": 5,
        "ocr_options": json.dumps({
            "enable_vision_ai": True,
            "extract_tables": True
        })
    }
    response = requests.post(f"{base_url}/tasks", headers=headers, data=data, files=files)
    task_id = response.json()["task_id"]

# Suivi de l'état d'une tâche
task_info = requests.get(f"{base_url}/tasks/{task_id}", headers=headers).json()
print(f"État de la tâche: {task_info['status']}")

# Récupération des résultats
if task_info["status"] == "completed":
    results = requests.get(f"{base_url}/tasks/{task_id}/results", headers=headers).json()
    print(f"Texte extrait: {results['text'][:100]}...")
```

## 6. Considérations techniques

### 6.1 Performance et scalabilité

Le tableau de bord OCR est conçu pour gérer efficacement un grand nombre de tâches :
- Pagination côté serveur pour les listes de tâches
- Chargement différé des détails et métriques
- Traitement asynchrone pour les opérations longues
- Mise en cache des données fréquemment consultées

Pour améliorer les performances en production :
- Configurez un nombre approprié de workers Celery
- Ajustez les délais d'expiration en fonction de la taille des documents
- Utilisez un système de cache distribué (Redis)
- Mettez en place une stratégie d'archivage pour les anciennes tâches

### 6.2 Sécurité

Le tableau de bord implémente plusieurs mesures de sécurité :
- Authentification et autorisation pour toutes les opérations
- Validation des entrées utilisateur
- Protection contre les attaques CSRF
- Limitation du débit pour prévenir les abus

### 6.3 Intégration avec les autres systèmes

Le tableau de bord OCR s'intègre avec d'autres composants de Technicia :
- Système RAG pour l'indexation des documents traités
- Système de notifications pour les alertes
- Module d'analyse pour les rapports approfondis

## 7. Résolution des problèmes courants

### 7.1 Problèmes de connexion WebSocket

Si les mises à jour en temps réel ne fonctionnent pas :
1. Vérifiez que le serveur WebSocket est actif
2. Assurez-vous que le navigateur prend en charge WebSocket
3. Vérifiez les règles de pare-feu ou proxy qui pourraient bloquer les connexions
4. Consultez les logs du serveur pour les erreurs de connexion

### 7.2 Tâches bloquées

Si une tâche reste bloquée en état "en cours" :
1. Vérifiez les logs Celery pour des erreurs ou timeouts
2. Redémarrez le worker Celery si nécessaire
3. Utilisez l'action "Reset" pour forcer la réinitialisation de l'état
4. Vérifiez la disponibilité des services externes (Vision AI, Document AI)

### 7.3 Problèmes de performance

Si le tableau de bord devient lent :
1. Réduisez le nombre de tâches affichées simultanément
2. Désactivez les mises à jour en temps réel pour les périphériques à faible puissance
3. Archivez les tâches anciennes ou terminées
4. Vérifiez l'utilisation des ressources serveur (CPU, mémoire, I/O)

## 8. Développement futur

Les améliorations planifiées pour le tableau de bord OCR comprennent :

- **Interface de validation avancée** 🔄
  - Éditeur visuel pour la correction du texte extrait
  - Apprentissage des corrections fréquentes
  - Visualisation des zones de faible confiance

- **Analyse prédictive** ⏳
  - Prédiction des temps de traitement
  - Détection des anomalies
  - Recommandations d'optimisation

- **Mode multiutilisateur avancé** ⏳
  - Affectation de tâches à des utilisateurs spécifiques
  - Workflows d'approbation
  - Notifications personnalisées

- **Intégration avec l'IA générative** ⏳
  - Résumé automatique des documents traités
  - Extraction d'informations clés
  - Classification automatique des documents
