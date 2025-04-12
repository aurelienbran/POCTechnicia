# Architecture Frontend Technicia

> **📋 Documentation Technique 📋**  
> Ce document décrit l'architecture complète du frontend pour le système Technicia.  
> Il présente les concepts techniques, l'organisation du code, et les principes d'implémentation.
>
> Dernière mise à jour : 7 avril 2025  
> État : Document initial

## 1. Vue d'ensemble

L'interface utilisateur de Technicia est conçue comme une application web moderne et responsive capable de s'adapter aux différents appareils (ordinateurs, tablettes, smartphones). Elle met en œuvre un système complet de gestion des utilisateurs avec différents rôles (administrateur, utilisateur standard) et propose des fonctionnalités spécifiques à chaque type d'utilisateur.

### 1.1 Objectifs principaux

- Fournir une interface intuitive pour exploiter les capacités avancées du système OCR
- Permettre l'accès depuis différents appareils grâce à une conception responsive
- Offrir des expériences différenciées selon le rôle de l'utilisateur
- Intégrer des fonctionnalités d'édition et de correction des résultats OCR
- Assurer la sécurité des données et l'authentification des utilisateurs

### 1.2 Structure globale

L'architecture frontend de Technicia suit une approche modulaire orientée composants avec les couches suivantes :

```
┌─────────────────────────────────────────────────────────────┐
│ Interface utilisateur (Composants Vue.js/React)             │
├─────────────────────────────────────────────────────────────┤
│ Gestionnaire d'état (Vuex/Redux)                            │
├─────────────────────────────────────────────────────────────┤
│ Services et API                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Service REST │  │ WebSockets   │  │ Stockage local   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│ Utilitaires et bibliothèques partagées                      │
└─────────────────────────────────────────────────────────────┘
```

## 2. Choix technologiques

### 2.1 Framework et bibliothèques

- **Framework principal:** Vue.js 3 avec composition API
  - Motivations: Performance, écosystème mature, courbe d'apprentissage douce
  - Alternative évaluée: React, qui pourrait être également adapté

- **Framework CSS:** Tailwind CSS
  - Motivations: Approche utility-first, facilité de personnalisation, performances
  - Configuration avec design tokens pour assurer la cohérence visuelle

- **Gestion d'état:** Pinia (évolution de Vuex pour Vue 3)
  - Motivations: Typage TypeScript, composition API, meilleure ergonomie

- **Routage:** Vue Router
  - Gestion des routes et du contrôle d'accès basé sur les permissions

- **HTTP Client:** Axios
  - Motivations: Support des intercepteurs, gestion avancée des requêtes/réponses

### 2.2 Outils de développement

- **Langage:** TypeScript
  - Motivations: Typage statique, meilleure maintenabilité, autocomplétion IDE

- **Bundler:** Vite
  - Motivations: Performances de développement, Hot Module Replacement (HMR)

- **Linting:** ESLint avec configuration Vue.js/TypeScript
  - Assure la cohérence du code et les bonnes pratiques

- **Testing:** Vitest + Vue Testing Library
  - Tests unitaires et d'intégration
  - Cypress pour les tests end-to-end

- **Documentation:** VuePress
  - Documentation technique et guides utilisateurs

## 3. Structure du projet

```
frontend/
├── public/                  # Ressources statiques
│   ├── fonts/              # Polices de caractères
│   ├── icons/              # Icônes et favicons
│   └── images/             # Images statiques
├── src/
│   ├── assets/             # Ressources importées par le code
│   ├── components/         # Composants réutilisables
│   │   ├── common/         # Composants génériques (boutons, inputs, etc.)
│   │   ├── admin/          # Composants spécifiques à l'interface admin
│   │   ├── user/           # Composants spécifiques à l'interface utilisateur
│   │   ├── auth/           # Composants d'authentification
│   │   ├── dashboard/      # Composants du tableau de bord
│   │   ├── document-viewer/ # Visualisation des documents
│   │   ├── editor/         # Outils d'édition et correction
│   │   ├── export/         # Module d'exportation
│   │   └── upload/         # Interface d'upload
│   ├── composables/        # Fonctions composables (hooks) Vue.js
│   ├── config/             # Configuration de l'application
│   ├── directives/         # Directives Vue personnalisées
│   ├── layouts/            # Mises en page
│   │   ├── AdminLayout.vue # Layout pour l'interface administrateur
│   │   ├── UserLayout.vue  # Layout pour l'interface utilisateur standard
│   │   └── AuthLayout.vue  # Layout pour les pages d'authentification
│   ├── pages/              # Pages de l'application
│   │   ├── admin/          # Pages d'administration
│   │   ├── user/           # Pages utilisateur
│   │   └── auth/           # Pages d'authentification
│   ├── router/             # Configuration des routes
│   ├── services/           # Services API et WebSocket
│   │   ├── api/            # Services d'API REST
│   │   ├── websocket/      # Services WebSocket
│   │   └── auth/           # Services d'authentification
│   ├── stores/             # État global (Pinia)
│   ├── styles/             # Styles et design system
│   │   ├── tailwind/       # Configuration Tailwind CSS
│   │   ├── variables.css   # Variables CSS globales
│   │   └── main.css        # Styles principaux
│   ├── types/              # Définitions TypeScript
│   ├── utils/              # Fonctions utilitaires
│   ├── App.vue             # Composant racine
│   ├── main.ts             # Point d'entrée de l'application
│   └── shims-vue.d.ts      # Déclarations de types pour Vue
├── tests/                  # Tests automatisés
│   ├── unit/               # Tests unitaires
│   ├── integration/        # Tests d'intégration
│   └── e2e/                # Tests end-to-end
├── .eslintrc.js            # Configuration ESLint
├── .gitignore              # Fichiers ignorés par Git
├── index.html              # Page HTML principale
├── package.json            # Dépendances et scripts
├── README.md               # Documentation du frontend
├── tailwind.config.js      # Configuration Tailwind CSS
├── tsconfig.json           # Configuration TypeScript
└── vite.config.ts          # Configuration Vite
```

## 4. Authentification et gestion des utilisateurs

### 4.1 Système d'authentification

L'authentification repose sur un système de tokens JWT (JSON Web Tokens) avec le workflow suivant :

1. **Login:** L'utilisateur fournit ses identifiants (email/mot de passe)
2. **Validation:** Le serveur valide les identifiants et génère deux tokens :
   - Access token (courte durée, utilisé pour les requêtes API)
   - Refresh token (longue durée, stocké en cookie HTTP-only)
3. **Stockage:** L'access token est stocké en mémoire (non persistant)
4. **Utilisation:** Chaque requête API inclut l'access token dans l'en-tête Authorization
5. **Refresh:** Lorsque l'access token expire, le refresh token est utilisé pour obtenir un nouveau token
6. **Logout:** Suppression des tokens côté client et invalidation côté serveur

### 4.2 Système de rôles et permissions

Le système de rôles distingue deux catégories d'utilisateurs principales :

#### Administrateur
- Accès complet au système
- Gestion des utilisateurs et des permissions
- Configuration du système OCR
- Gestion complète des documents et bases de connaissances

#### Utilisateur standard
- Accès au chatbot et à l'upload d'images
- Consultation des documents partagés
- Fonctionnalités de base d'OCR pour les images uploadées

La vérification des permissions est effectuée à plusieurs niveaux :
- **Backend:** Middleware de vérification des rôles pour chaque endpoint API
- **Frontend - Router:** Guards empêchant l'accès aux routes non autorisées
- **Frontend - Composants:** Rendu conditionnel basé sur les permissions de l'utilisateur

### 4.3 Stockage des données utilisateur

Les informations de session sont gérées ainsi :
- Access token stocké en mémoire (non persistant entre les sessions)
- Refresh token stocké dans un cookie HTTP-only (sécurité)
- Données utilisateur de base (nom, email, rôle) stockées dans le store Pinia
- Préférences utilisateur stockées dans localStorage pour persistance

## 5. Interfaces utilisateur par rôle

### 5.1 Interface administrateur

L'interface administrateur est organisée en sections principales :

#### Dashboard administrateur
- Vue d'ensemble des statistiques système
- Graphiques d'activité et d'utilisation
- Alertes et notifications

#### Gestion documentaire
- Upload et organisation des documents
- Configuration des paramètres OCR
- Visualisation et édition des résultats OCR
- Création et gestion des bases de connaissances

#### Administration système
- Gestion des utilisateurs et des rôles
- Configuration du système et des intégrations
- Monitoring des performances et journaux

#### Paramètres avancés
- Configuration des processeurs OCR
- Gestion des fournisseurs OCR externes
- Paramètres de sauvegarde et restauration

### 5.2 Interface utilisateur standard

L'interface utilisateur standard se concentre sur les fonctionnalités essentielles :

#### Interface chatbot
- Zone de conversation principale
- Historique des conversations
- Indicateurs de statut et de traitement

#### Upload d'images
- Interface d'upload simplifiée
- Prévisualisation des images
- Résultats d'analyse OCR basique

#### Documents partagés
- Liste des documents accessibles
- Visualisation des documents
- Recherche et filtrage

#### Profil et préférences
- Informations personnelles
- Paramètres d'interface et de notifications
- Gestion des préférences et des favoris

## 6. Responsive design et optimisation mobile

### 6.1 Approche mobile-first

L'interface est développée selon une approche mobile-first avec :
- Styles de base optimisés pour les petits écrans
- Media queries pour adapter l'interface aux écrans plus grands
- Composants adaptatifs qui changent de comportement selon la taille d'écran

### 6.2 Adaptations spécifiques par taille d'écran

#### Mobile (< 640px)
- Navigation par menu hamburger
- Interface simplifiée en plein écran
- Interactions optimisées pour le toucher
- Utilisation de l'appareil photo natif

#### Tablette (640px - 1024px)
- Navigation mixte (menu latéral compact + menu supérieur)
- Mises en page adaptatives avec grilles flexibles
- Visualisation de document optimisée pour l'orientation

#### Desktop (> 1024px)
- Interface complète avec sidebar permanente
- Multiples panneaux et vues côte à côte
- Raccourcis clavier avancés
- Visualisation avancée des documents

### 6.3 Progressive Web App (PWA)

L'application est configurée comme une PWA avec :
- Manifest pour installation sur l'écran d'accueil
- Service Worker pour mise en cache et fonctionnalités hors-ligne
- Stratégie de cache pour les ressources statiques et les données
- Synchronisation différée pour les actions effectuées hors-ligne

## 7. Composants d'interface critiques

### 7.1 Visualisateur de documents OCR

Le visualisateur de documents est un composant central permettant :
- Affichage côte à côte du document original et du texte extrait
- Surlignage synchronisé entre l'image et le texte
- Zoom et navigation dans les documents
- Mise en évidence des zones par type de contenu (texte, formules, tableaux)
- Interaction avec les éléments détectés

```typescript
// Exemple simplifié de la structure du composant
export interface DocumentViewerProps {
  documentId: string;          // ID du document à visualiser
  showOriginal: boolean;       // Affichage de l'image originale
  showExtractedText: boolean;  // Affichage du texte extrait
  highlightElements: boolean;  // Surlignage des éléments détectés
  currentPage: number;         // Page actuelle
}

// Types d'éléments détectés
export enum ElementType {
  TEXT = 'text',
  FORMULA = 'formula',
  TABLE = 'table',
  CHART = 'chart',
  DIAGRAM = 'diagram',
  LOW_CONFIDENCE = 'low_confidence'
}
```

### 7.2 Module d'upload et de traitement

Le module d'upload comprend :
- Zone de glisser-déposer pour les fichiers
- Prévisualisation des documents
- Options de configuration OCR
- Barre de progression avec estimation du temps restant
- Feedback en temps réel pendant le traitement

### 7.3 Interface du chatbot

L'interface du chatbot intègre :
- Zone de conversation avec historique
- Support pour les messages texte et multimédia
- Affichage des sources documentaires
- Possibilité d'upload d'images contextuelles
- Exportation des conversations

### 7.4 Éditeur de correction OCR

L'éditeur permet :
- Edition du texte extrait avec préservation de la mise en forme
- Visualisation côte à côte avec le document original
- Correction assistée des zones à faible confiance
- Validation des modifications et historique des changements

## 8. Communication avec le backend

### 8.1 Architecture des services API

Les services API sont organisés par domaine fonctionnel :

```typescript
// Structure simplifiée des services API
export const apiServices = {
  // Services d'authentification
  auth: {
    login: (credentials: Credentials) => axios.post('/api/auth/login', credentials),
    logout: () => axios.post('/api/auth/logout'),
    refreshToken: () => axios.post('/api/auth/refresh-token'),
    getProfile: () => axios.get('/api/auth/profile')
  },
  
  // Services de gestion documentaire
  documents: {
    upload: (file: File, options: OcrOptions) => { /* ... */ },
    getList: (filters: DocumentFilters) => { /* ... */ },
    getDocument: (id: string) => { /* ... */ },
    updateDocument: (id: string, data: DocumentData) => { /* ... */ },
    deleteDocument: (id: string) => { /* ... */ }
  },
  
  // Services OCR
  ocr: {
    processImage: (image: File, options: OcrOptions) => { /* ... */ },
    getTaskStatus: (taskId: string) => { /* ... */ },
    cancelTask: (taskId: string) => { /* ... */ }
  },
  
  // Services du chatbot
  chat: {
    sendMessage: (message: ChatMessage) => { /* ... */ },
    getHistory: (conversationId: string) => { /* ... */ },
    uploadAttachment: (file: File, conversationId: string) => { /* ... */ }
  },
  
  // Services d'administration (admin uniquement)
  admin: {
    getUsers: (filters: UserFilters) => { /* ... */ },
    createUser: (userData: UserData) => { /* ... */ },
    updateUser: (id: string, userData: UserData) => { /* ... */ },
    deleteUser: (id: string) => { /* ... */ },
    getSystemStats: () => { /* ... */ }
  }
};
```

### 8.2 Intégration WebSockets

Les WebSockets sont utilisés pour les communications en temps réel :

```typescript
// Service WebSocket pour les notifications et mises à jour
export class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private eventHandlers: Map<string, Function[]> = new Map();
  
  // Connexion au serveur WebSocket
  connect() {
    const token = authService.getToken();
    this.socket = new WebSocket(`${WS_URL}?token=${token}`);
    
    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.dispatchEvent('connected', {});
    };
    
    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.dispatchEvent(data.type, data.payload);
    };
    
    this.socket.onclose = () => {
      if (this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        setTimeout(() => this.connect(), RECONNECT_INTERVAL);
        this.reconnectAttempts++;
      }
    };
  }
  
  // Enregistrement d'un gestionnaire d'événements
  on(event: string, callback: Function) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)?.push(callback);
  }
  
  // Déclenchement d'un événement
  private dispatchEvent(event: string, data: any) {
    const handlers = this.eventHandlers.get(event) || [];
    handlers.forEach(handler => handler(data));
  }
  
  // Envoi d'un message au serveur
  send(type: string, payload: any) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type, payload }));
    }
  }
  
  // Déconnexion
  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}
```

### 8.3 Gestion de l'état global

L'état global de l'application est géré avec Pinia :

```typescript
// Store utilisateur
export const useUserStore = defineStore('user', {
  state: () => ({
    user: null as User | null,
    isAuthenticated: false,
    permissions: [] as string[],
    preferences: {} as UserPreferences
  }),
  
  getters: {
    isAdmin: (state) => state.user?.role === 'admin',
    hasPermission: (state) => (permission: string) => state.permissions.includes(permission)
  },
  
  actions: {
    async login(credentials: Credentials) {
      try {
        const { data } = await apiServices.auth.login(credentials);
        this.user = data.user;
        this.isAuthenticated = true;
        this.permissions = data.permissions;
        this.loadPreferences();
      } catch (error) {
        throw error;
      }
    },
    
    async logout() {
      try {
        await apiServices.auth.logout();
      } finally {
        this.user = null;
        this.isAuthenticated = false;
        this.permissions = [];
        this.preferences = {};
      }
    },
    
    loadPreferences() {
      const storedPrefs = localStorage.getItem('user_preferences');
      if (storedPrefs) {
        this.preferences = JSON.parse(storedPrefs);
      }
    },
    
    savePreferences(prefs: Partial<UserPreferences>) {
      this.preferences = { ...this.preferences, ...prefs };
      localStorage.setItem('user_preferences', JSON.stringify(this.preferences));
    }
  }
});

// Store documents
export const useDocumentStore = defineStore('documents', {
  state: () => ({
    documents: [] as Document[],
    currentDocument: null as Document | null,
    isLoading: false,
    filters: {} as DocumentFilters
  }),
  
  actions: {
    async fetchDocuments() {
      this.isLoading = true;
      try {
        const { data } = await apiServices.documents.getList(this.filters);
        this.documents = data.documents;
      } catch (error) {
        console.error('Error fetching documents:', error);
      } finally {
        this.isLoading = false;
      }
    },
    
    async fetchDocument(id: string) {
      this.isLoading = true;
      try {
        const { data } = await apiServices.documents.getDocument(id);
        this.currentDocument = data;
      } catch (error) {
        console.error(`Error fetching document ${id}:`, error);
      } finally {
        this.isLoading = false;
      }
    },
    
    setFilters(filters: Partial<DocumentFilters>) {
      this.filters = { ...this.filters, ...filters };
    },
    
    clearFilters() {
      this.filters = {};
    }
  }
});
```

## 9. Sécurité

### 9.1 Protection contre les vulnérabilités courantes

- **XSS (Cross-Site Scripting):**
  - Échappement systématique des données utilisateur avec v-bind
  - Utilisation des fonctionnalités de sécurité intégrées à Vue.js
  - Content Security Policy (CSP) configuré

- **CSRF (Cross-Site Request Forgery):**
  - Tokens CSRF pour les requêtes importantes
  - SameSite cookies configurés comme Strict

- **Injection de dépendances:**
  - Validation stricte des données utilisateur côté client et serveur
  - Utilisation de bibliothèques validées pour la manipulation de données

### 9.2 Gestion des tokens et sessions

- Tokens JWT stockés de manière sécurisée (access token en mémoire, refresh token en cookie HTTP-only)
- Rotation des tokens pour limiter les risques de compromission
- Expiration automatique des sessions inactives
- Possibilité de révoquer les sessions actives

### 9.3 Validation des permissions

```typescript
// Guard de route pour vérifier les permissions
export function permissionGuard(permission: string) {
  return (to: RouteLocationNormalized) => {
    const userStore = useUserStore();
    
    if (!userStore.isAuthenticated) {
      return { name: 'login', query: { redirect: to.fullPath } };
    }
    
    if (!userStore.hasPermission(permission)) {
      return { name: 'forbidden' };
    }
    
    return true;
  };
}

// Configuration des routes avec guards
const routes = [
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAuth: true },
    beforeEnter: permissionGuard('admin.access'),
    children: [
      // Routes admin protégées...
    ]
  },
  {
    path: '/documents',
    component: DocumentsView,
    meta: { requiresAuth: true },
    beforeEnter: permissionGuard('documents.read')
  }
];
```

## 10. Tests et qualité du code

### 10.1 Stratégie de tests

- **Tests unitaires:** Composants individuels et fonctions utilitaires
- **Tests d'intégration:** Interaction entre composants et services
- **Tests e2e:** Flux utilisateur complets
- **Tests de performance:** Temps de chargement et réactivité

### 10.2 Outils de qualité de code

- ESLint pour l'analyse statique du code
- Prettier pour le formatage
- Husky pour les hooks pre-commit
- TypeScript pour la vérification de types

### 10.3 Couverture de tests cible

- Composants critiques: 90%+ de couverture
- Utilitaires et services: 85%+ de couverture
- Flux principaux: 100% de couverture en e2e

## 11. Déploiement et CI/CD

### 11.1 Construction de l'application

- Build de production avec Vite
- Optimisations pour la taille des bundles
- Extraction de CSS et minification
- Génération des assets pour PWA

### 11.2 Intégration avec le backend

- Build frontend généré dans le dossier `/dist`
- Servi par le backend FastAPI via un middleware statique
- Configuration pour le routage SPA (redirection vers index.html)

### 11.3 Pipeline CI/CD

- Tests automatisés à chaque pull request
- Build et déploiement automatiques sur les environnements de test
- Déploiement manuel en production après validation

## 12. Roadmap et évolutions futures

### 12.1 Phase 1: Architecture de base et authentification
- Mise en place du framework et des outils
- Système d'authentification et de rôles
- Layouts adaptatifs pour desktop et mobile

### 12.2 Phase 2: Interfaces principales
- Interface administrateur
- Interface utilisateur standard
- Gestion documentaire et visualisateur OCR
- Interface chatbot

### 12.3 Phase 3: Optimisations et fonctionnalités avancées
- Transformation en PWA
- Optimisations mobiles avancées
- Fonctionnalités d'exportation et de partage
- Intégrations WebSockets

### 12.4 Évolutions futures potentielles
- Mode hors-ligne complet
- Application mobile native (React Native/Flutter)
- Éditeur collaboratif en temps réel
- Intégrations avec des outils externes

## 13. Références

### 13.1 Documentation technique associée
- [ARCHITECTURE_TECHNIQUE_COMPLETE.md](./ARCHITECTURE_TECHNIQUE_COMPLETE.md)
- [OCR_DASHBOARD.md](./OCR_DASHBOARD.md)
- [OCR_RAG_INTEGRATION.md](./OCR_RAG_INTEGRATION.md)

### 13.2 Ressources externes
- [Vue.js Documentation](https://vuejs.org/guide/introduction.html)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Pinia Documentation](https://pinia.vuejs.org/)
- [Vite Documentation](https://vitejs.dev/guide/)
