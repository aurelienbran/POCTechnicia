document.addEventListener('DOMContentLoaded', () => {
    // Éléments du DOM
    const uploadForm = document.getElementById('uploadForm');
    const pdfFile = document.getElementById('pdfFile');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadModal = document.getElementById('uploadModal');
    const uploadStatus = document.getElementById('uploadStatus');
    const documentInfo = document.getElementById('uploadDetails');
    const documentName = document.getElementById('documentName');
    const documentSize = document.getElementById('documentSize');
    const documentPages = document.getElementById('documentPages');
    const indexingStatus = document.getElementById('indexingStatus');
    const queryInput = document.getElementById('query');
    const sendButton = document.getElementById('sendButton');
    const chatMessages = document.getElementById('chatMessages');
    const queryForm = document.getElementById('questionForm');

    // Charger les données initiales
    async function initialize() {
        try {
            // Nettoyer toutes les connexions et pollings existants
            cleanupWebSockets();
            stopExistingPolling();
            
            // Initialiser les WebSockets dès le début (priorité WebSockets)
            initializeWebSockets();
            
            // Vérifier si une indexation est en cours
            const statusResponse = await fetch('/api/v1/indexing-status');
            const status = await statusResponse.json();
            
            if (status.in_progress) {
                // Afficher le statut d'indexation
                indexingStatus.classList.remove('hidden');
                indexingStatus.querySelector('div').textContent = 'En cours...';
                
                // Attendre un petit moment pour voir si les WebSockets se connectent
                setTimeout(() => {
                    // Ne démarrer le polling que si nécessaire
                    // Si WebSockets connectés et récentes mises à jour, ne pas faire de polling
                    if (!webSocketConnected || !window.lastIndexingStatusTime || 
                        (Date.now() - window.lastIndexingStatusTime > 5000)) {
                        console.log('Démarrage du polling comme fallback (WebSockets non disponibles)');
                        window.PollingManager.startPolling();
                    } else {
                        console.log('WebSockets connectés, polling évité');
                    }
                }, 1000);
            }
            
            // Récupérer les statistiques détaillées
            try {
                const statsResponse = await fetch('/api/v1/documents/statistics');
                if (statsResponse.ok) {
                    const statistics = await statsResponse.json();
                    
                    // Ajouter une information sur les documents indexés
                    if (statistics.is_empty) {
                        addMessage('system', 'Bienvenue ! Aucun document n\'est indexé actuellement. Veuillez télécharger un PDF pour commencer.');
                    } else {
                        addMessage('system', `Bienvenue ! ${statistics.documents_count} document(s) indexé(s) contenant ${statistics.vectors_count} passages de texte sont disponibles pour vos questions.`);
                    }
                }
            } catch (error) {
                console.error('Erreur lors de la récupération des statistiques détaillées:', error);
                // En cas d'erreur, utiliser l'endpoint classique comme fallback
                const simpleStatsResponse = await fetch('/api/v1/stats');
                if (simpleStatsResponse.ok) {
                    const stats = await simpleStatsResponse.json();
                    addMessage('system', `Bienvenue ! ${stats.vectors_count} passages de texte sont disponibles pour vos questions.`);
                }
            }
        } catch (error) {
            console.error('Erreur lors de l\'initialisation:', error);
        }
    }

    // Initialiser l'application
    initialize();

    // Vérifier l'état du système et des documents indexés au démarrage
    async function checkSystemStatus() {
        try {
            const response = await fetch('/api/v1/health');
            if (response.ok) {
                queryInput.disabled = false;
                sendButton.disabled = false;
                addMessage('assistant', 'Bienvenue ! Je suis prêt à répondre à vos questions sur vos documents techniques.');
                
                // Vérifier les documents indexés
                const responseIndexed = await fetch('/api/v1/stats');
                if (responseIndexed.ok) {
                    const stats = await responseIndexed.json();
                    if (stats.points_count > 0) {
                        addMessage('assistant', `${stats.points_count} passages de documents sont indexés et prêts à être consultés.`);
                    }
                }
            } else {
                throw new Error('Système non disponible');
            }
        } catch (error) {
            addMessage('system', 'Le système est actuellement indisponible. Veuillez réessayer plus tard.');
        }
    }

    // Empêcher la soumission du formulaire d'upload
    uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
    });

    // Gestion de l'upload de fichier
    // Désactiver les écouteurs multiples en utilisant AbortController
    window.fileUploadController = window.fileUploadController || new AbortController();
    window.fileUploadController.abort(); // Arrêter les écouteurs précédents
    window.fileUploadController = new AbortController();
    
    pdfFile.addEventListener('change', async (e) => {
        // Désactiver l'input temporairement pour éviter les uploads multiples
        pdfFile.disabled = true;
        
        // Réinitialiser tout traitement d'indexation précédent
        if (window.fileUploadController) {
            window.fileUploadController.abort();
        }
        window.fileUploadController = new AbortController();
        
        // Réinitialiser le compteur d'appels API
        window.indexingApiCallCount = 0;
        window.indexingStartTime = Date.now();
        
        // Marquer explicitement que nous sommes en train de traiter un document
        processingInProgress = true;
        
        // Afficher la fenêtre modale
        uploadModal.classList.remove('hidden');
        uploadProgress.classList.remove('hidden');
        
        const file = e.target.files[0];
        if (!file) {
            pdfFile.disabled = false;
            return;
        }
        
        if (file.type !== 'application/pdf') {
            showError('Veuillez sélectionner un fichier PDF');
            pdfFile.disabled = false;
            return;
        }

        if (file.size > 157286400) { // 150 MB
            showError('Le fichier ne doit pas dépasser 150 MB');
            pdfFile.disabled = false;
            return;
        }

        // Afficher les informations du document
        documentName.textContent = `Fichier : ${file.name}`;
        documentSize.textContent = `Taille : ${formatFileSize(file.size)}`;
        uploadStatus.textContent = 'Envoi du fichier...';
        
        const formData = new FormData(uploadForm);
        
        // Arrêter tout polling existant avant d'en démarrer un nouveau
        stopExistingPolling();
        
        try {
            const response = await fetch('/api/v1/documents', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Erreur lors de l\'upload');
            }
            
            // Enregistrer le timestamp de cet upload
            window.lastUploadTime = Date.now();
            console.log('[Upload] Upload réussi enregistré à:', new Date(window.lastUploadTime).toISOString());
            
            // S'assurer explicitement que le modal reste visible et que processingInProgress reste à true
            processingInProgress = true;
            uploadModal.classList.remove('hidden');
            
            // Ajouter un message explicite pour l'utilisateur
            uploadStatus.textContent = 'Initialisation du traitement...';
            
            // Démarrer le polling via le PollingManager
            window.PollingManager.startPolling();
            
        } catch (error) {
            showError(error.message);
            uploadStatus.textContent = 'Erreur : ' + error.message;
            setTimeout(() => {
                uploadModal.classList.add('hidden');
                uploadProgress.classList.add('hidden');
            }, 3000);
        } finally {
            // Réactiver l'input après le traitement
            setTimeout(() => {
                pdfFile.disabled = false;
            }, 1000);
        }
    }, { signal: window.fileUploadController.signal });

    // PollingManager: Gestionnaire de polling centralisé avec support WebSocket
    window.PollingManager = {
        _polling: false,
        _timer: null,
        _lastCheckTime: 0,
        _minCheckIntervalMs: 4000, // 4 secondes minimum entre les checks
        _adaptiveIntervalMs: 4000, // Intervalle qui s'adapte en fonction des réponses
        _backoffFactor: 1, // Facteur multiplicateur pour le backoff
        _maxBackoffFactor: 10, // Facteur maximum de backoff
        _maxPollTime: 5 * 60 * 1000, // 5 minutes maximum de polling
        _pollStartTime: 0,
        _checkOnceWithWebSocket: false, // Flag pour vérifier une fois même avec WebSocket
        _sessionId: null, // Identifiant unique de la session de polling
        _consecutiveErrors: 0, // Nombre d'erreurs consécutives
        
        // Récupérer le semaphore
        _getSemaphore: function() {
            const semaphore = localStorage.getItem('pollingInProgress');
            if (!semaphore) return null;
            
            try {
                return JSON.parse(semaphore);
            } catch (e) {
                console.error('[PollingManager] Erreur dans le parsing du semaphore:', e);
                return null;
            }
        },
        
        // Définir le semaphore
        _setSemaphore: function(value) {
            try {
                localStorage.setItem('pollingInProgress', JSON.stringify(value));
            } catch (e) {
                console.error('[PollingManager] Erreur dans la définition du semaphore:', e);
            }
        },
        
        // Vérifier si un polling est actif dans un autre onglet
        _isPollingActiveInAnotherTab: function() {
            const semaphore = this._getSemaphore();
            if (!semaphore) return false;
            
            // Vérifier l'horodatage pour détecter les semaphores périmés (> 30 secondes)
            const now = Date.now();
            const isExpired = (now - semaphore.timestamp) > 30000;
            
            // Si le semaphore est périmé, le nettoyer
            if (isExpired) {
                console.log('[PollingManager] Semaphore périmé détecté, nettoyage');
                this._setSemaphore(null);
                return false;
            }
            
            // Si le semaphore existe et est valide, mais avec un ID différent
            return semaphore.id !== this._sessionId;
        },
        
        // Démarrer une nouvelle session de polling
        startPolling: function() {
            // Générer un identifiant de session unique s'il n'existe pas
            if (!this._sessionId) {
                this._sessionId = `poll_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            }
            
            // Évaluer si le WebSocket est actuellement fiable
            const wsIsFunctional = window.webSocketConnected && window.lastIndexingStatusTime && 
                                  (Date.now() - window.lastIndexingStatusTime < 5000);
            
            // Si WebSocket est fonctionnel, vérifier une fois seulement puis s'appuyer sur WebSocket
            if (wsIsFunctional) {
                console.log('[WebSocket] WebSocket fonctionnel détecté, mode check unique activé');
                this._checkOnceWithWebSocket = true;
            }
            
            // Vérifier si un polling est déjà en cours dans cet onglet
            if (this._polling) {
                console.log('[PollingManager] Polling déjà en cours dans cet onglet');
                return;
            }
            
            // Vérifier si un polling est en cours dans un autre onglet
            if (this._isPollingActiveInAnotherTab()) {
                console.log('[PollingManager] Polling déjà actif dans un autre onglet');
                
                // S'assurer que processingInProgress reste à true même si on ne démarre pas de nouveau polling
                console.log('[PollingManager] État de processingInProgress (autre onglet actif):', processingInProgress);
                processingInProgress = true;
                
                // Si les WebSockets ne sont pas disponibles, on force quand même une vérification unique
                if (!window.webSocketConnected) {
                    console.log('[PollingManager] WebSocket non disponible, vérification unique forcée malgré le polling dans un autre onglet');
                    this._checkStatus();
                }
                return;
            }
            
            // Acquérir le semaphore
            this._setSemaphore({
                id: this._sessionId,
                timestamp: Date.now(),
                wsConnected: window.webSocketConnected
            });
            
            // Initialiser les variables de polling
            this._polling = true;
            this._pollStartTime = Date.now();
            this._consecutiveErrors = 0;
            this._backoffFactor = 1;
            
            console.log('[PollingManager] Démarrage du polling (ID:', this._sessionId, ', WebSocket:', window.webSocketConnected ? 'actif' : 'inactif', ')');
            
            // S'assurer que processingInProgress reste à true pendant le démarrage du polling
            console.log('[PollingManager] État de processingInProgress avant démarrage polling:', processingInProgress);
            processingInProgress = true;
            
            // Attendre un court délai pour laisser le temps aux WebSockets de se connecter
            // et éviter les requêtes inutiles si les WebSockets se connectent rapidement
            if (!wsIsFunctional && window.socket && window.socket.readyState === 0) {
                console.log('[PollingManager] Attente de 800ms pour laisser le WebSocket se connecter...');
                setTimeout(() => this._checkStatus(), 800);
            } else {
                // Vérifier immédiatement le statut
                this._checkStatus();
            }
        },
        
        // Arrêter le polling en cours
        stopPolling: function() {
            if (this._timer) {
                clearTimeout(this._timer);
                this._timer = null;
            }
            
            // Si ce n'est pas notre semaphore, ne pas le supprimer
            const semaphore = this._getSemaphore();
            if (semaphore && semaphore.id === this._sessionId) {
                // Libérer explicitement le semaphore
                localStorage.removeItem('pollingInProgress');
                console.log('[PollingManager] Semaphore libéré');
            }
            
            // Conserver une trace du dernier état pour les autres onglets via localStorage
            if (this._polling) {
                try {
                    localStorage.setItem('polling_last_stopped', JSON.stringify({
                        timestamp: Date.now(),
                        sessionId: this._sessionId,
                        reason: 'completed_or_stopped'
                    }));
                } catch (e) {
                    console.warn('[PollingManager] Erreur lors de la sauvegarde de l\'état d\'arrêt:', e);
                }
            }
            
            this._polling = false;
            this._checkOnceWithWebSocket = false;
            console.log('[PollingManager] Polling arrêté');
        },
        
        // Mettre à jour le semaphore pour indiquer une activité récente
        _refreshSemaphore: function() {
            try {
                const semaphore = this._getSemaphore();
                if (semaphore && semaphore.id === this._sessionId) {
                    // Mettre à jour le timestamp et l'état WebSocket
                    semaphore.timestamp = Date.now();
                    semaphore.wsConnected = window.webSocketConnected || false;
                    this._setSemaphore(semaphore);
                }
            } catch (e) {
                console.warn('[PollingManager] Erreur lors du rafraîchissement du semaphore:', e);
                // En cas d'erreur, tenter de réinitialiser le semaphore
                try {
                    if (this._polling) {
                        this._setSemaphore({
                            id: this._sessionId,
                            timestamp: Date.now(),
                            wsConnected: window.webSocketConnected || false
                        });
                    }
                } catch (err) {
                    console.error('[PollingManager] Impossible de récupérer ou mettre à jour le semaphore:', err);
                }
            }
        },
        
        // Vérifier le statut d'indexation
        _checkStatus: async function() {
            // S'assurer que processingInProgress reste true pendant la vérification
            console.log('[PollingManager] État de processingInProgress dans _checkStatus:', processingInProgress);
            processingInProgress = true;
            
            // Vérifier si le temps maximum de polling est dépassé
            const pollDuration = Date.now() - this._pollStartTime;
            if (pollDuration > this._maxPollTime) {
                console.log('[PollingManager] Temps maximum de polling atteint, arrêt');
                this.stopPolling();
                return;
            }
            
            // Rafraîchir le semaphore pour signaler l'activité
            this._refreshSemaphore();
            
            // Si WebSocket est connecté et que nous n'avons pas besoin de vérifier
            // ET que la dernière mise à jour WebSocket est récente (moins de 10 secondes)
            const wsRecentUpdate = window.lastIndexingStatusTime && (Date.now() - window.lastIndexingStatusTime < 10000);
            
            // Vérification plus intelligente du WebSocket fonctionnel
            const wsIsReliable = window.webSocketConnected && wsRecentUpdate && window.socket && 
                               window.socket.readyState === WebSocket.OPEN;
                               
            if (wsIsReliable && !this._checkOnceWithWebSocket) {
                console.log('[WebSocket] WebSocket actif avec mises à jour récentes, pause du polling');
                // Vérifier toutes les 20 secondes quand même comme filet de sécurité
                this._timer = setTimeout(() => this._checkStatus(), 20000);
                return;
            }
            
            // Réinitialiser le flag pour ne pas vérifier systématiquement
            this._checkOnceWithWebSocket = false;
            
            // Vérifier le temps écoulé depuis la dernière vérification
            const now = Date.now();
            const timeSinceLastCheck = now - this._lastCheckTime;
            
            // Attendre au moins l'intervalle minimum entre les vérifications
            const currentInterval = this._adaptiveIntervalMs * this._backoffFactor;
            if (timeSinceLastCheck < currentInterval) {
                const waitTime = currentInterval - timeSinceLastCheck;
                console.log(`[PollingManager] Attente de ${Math.round(waitTime/1000)}s avant prochaine vérification (backoff: ${this._backoffFactor.toFixed(2)}x)`);
                this._timer = setTimeout(() => this._checkStatus(), waitTime);
                return;
            }
            
            // Marquer l'heure de cette vérification
            this._lastCheckTime = now;
            
            try {
                console.log('[PollingManager] Vérification du statut d\'indexation via API');
                
                // Ajouter un timeout pour éviter les requêtes qui traînent
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 8000); // Augmenter le timeout à 8 secondes
                
                // Utiliser un cache buster spécifique à chaque requête
                const cacheBuster = `${this._sessionId}-${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;
                
                const response = await fetch(`/api/v1/indexing-status?cb=${cacheBuster}`, {
                    signal: controller.signal,
                    // Ajouter des paramètres uniques pour éviter le cache
                    headers: {
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0',
                        'X-Request-ID': `${this._sessionId}-${Date.now()}`
                    }
                }).finally(() => clearTimeout(timeoutId));
                
                // Si la requête échoue avec un 429, attendre plus longtemps avant de réessayer
                if (response.status === 429) {
                    this._consecutiveErrors++;
                    console.warn(`[PollingManager] Rate limit atteint (429), erreur #${this._consecutiveErrors}`);
                    
                    // Augmenter le facteur de backoff de manière exponentielle
                    this._backoffFactor = Math.min(this._maxBackoffFactor, this._backoffFactor * 2);
                    
                    // Tenter de récupérer le Retry-After de l'en-tête
                    let retryAfter = 5;
                    try {
                        const headerRetryAfter = response.headers.get('Retry-After');
                        if (headerRetryAfter) {
                            retryAfter = parseInt(headerRetryAfter);
                            console.log(`[PollingManager] En-tête Retry-After reçu: ${retryAfter}s`);
                        }
                    } catch (e) {
                        console.warn('[PollingManager] Erreur lors de la lecture de Retry-After:', e);
                    }
                    
                    // Délai de base + backoff progressif
                    const delayMs = Math.max(5000, (retryAfter * 1000) + (this._consecutiveErrors * 1000));
                    
                    console.log(`[PollingManager] Attente de ${Math.round(delayMs/1000)}s avant nouvelle tentative (backoff: ${this._backoffFactor.toFixed(2)}x)`);
                    this._timer = setTimeout(() => this._checkStatus(), delayMs);
                    
                    // Si WebSocket est connecté, s'en remettre principalement à lui
                    const wsIsReliable = window.webSocketConnected && window.socket && 
                                      window.socket.readyState === WebSocket.OPEN;
                    
                    if (wsIsReliable) {
                        console.log('[PollingManager] WebSocket fiable disponible, backoff plus agressif');
                        this._backoffFactor = Math.min(this._maxBackoffFactor, this._backoffFactor + 2);
                        
                        // Enregistrer la dernière erreur 429 dans localStorage pour informer les autres onglets
                        try {
                            localStorage.setItem('polling_rate_limited', JSON.stringify({
                                timestamp: Date.now(),
                                sessionId: this._sessionId,
                                retryAfter: retryAfter
                            }));
                        } catch (e) {
                            console.warn('[PollingManager] Erreur lors du partage de l\'état de rate limit:', e);
                        }
                    }
                    
                    return;
                }
                
                // Si la requête échoue pour une autre raison
                if (!response.ok) {
                    this._consecutiveErrors++;
                    console.warn(`[PollingManager] Échec de la récupération du statut: ${response.status}, erreur #${this._consecutiveErrors}`);
                    
                    // Augmenter le délai en fonction du nombre d'erreurs consécutives
                    const delayMs = 3000 + (this._consecutiveErrors * 1500);
                    this._timer = setTimeout(() => this._checkStatus(), delayMs);
                    return;
                }
                
                // Réinitialiser les compteurs d'erreur après une requête réussie
                this._consecutiveErrors = 0;
                
                const status = await response.json();
                console.log('[PollingManager] Statut reçu via polling:', status);
                
                // Vérifier si l'upload est récent avant de traiter un statut completed=true
                if (status.completed === true) {
                    const timeSinceUpload = Date.now() - window.lastUploadTime;
                    if (timeSinceUpload < window.UPLOAD_GRACE_PERIOD) {
                        console.log(`[PollingManager] Ignorer le statut completed=true (upload récent il y a ${Math.round(timeSinceUpload/1000)}s)`);
                        
                        // Planifier la prochaine vérification rapidement
                        const nextCheckDelay = 1000;
                        console.log(`[PollingManager] Revérification rapide dans ${nextCheckDelay/1000}s`);
                        this._timer = setTimeout(() => this._checkStatus(), nextCheckDelay);
                        return;
                    }
                }
                
                // Marquer le moment de la dernière mise à jour
                window.lastIndexingStatusTime = Date.now();
                
                // Sauvegarder le statut dans localStorage pour la synchronisation entre onglets
                try {
                    localStorage.setItem('latest_indexing_status', JSON.stringify({
                        status: status,
                        timestamp: Date.now(),
                        sessionId: this._sessionId,
                        source: 'polling'
                    }));
                } catch (e) {
                    console.warn('[PollingManager] Erreur lors de la sauvegarde du statut dans localStorage:', e);
                }
                
                // Utiliser la même fonction de traitement que les WebSockets
                handleIndexingStatusUpdate(status);
                
                // Si le traitement est terminé, arrêter le polling
                if (status.completed === true) {
                    const timeSinceUpload = Date.now() - window.lastUploadTime;
                    if (timeSinceUpload >= window.UPLOAD_GRACE_PERIOD) {
                        console.log('[PollingManager] Traitement terminé, arrêt du polling');
                        this.stopPolling();
                        return;
                    } else {
                        // Si l'upload est récent, continuer le polling malgré completed=true
                        console.log(`[PollingManager] Continuer le polling malgré completed=true (upload récent)`);
                    }
                }
                
                // Adapter l'intervalle en fonction de l'avancement
                if (status.progress !== undefined) {
                    // Moins fréquent si > 70% terminé, plus fréquent au début
                    if (status.progress > 70) {
                        this._adaptiveIntervalMs = 6000; // 6 secondes
                    } else if (status.progress > 30) {
                        this._adaptiveIntervalMs = 4500; // 4.5 secondes
                    } else {
                        this._adaptiveIntervalMs = 3500; // 3.5 secondes
                    }
                }
                
                // Réduire légèrement le facteur de backoff après une requête réussie
                if (this._backoffFactor > 1) {
                    this._backoffFactor = Math.max(1, this._backoffFactor * 0.7);
                }
                
                // Planifier la prochaine vérification avec un intervalle plus long si WebSocket est actif
                const wsIsActive = window.webSocketConnected && window.socket && 
                                 window.socket.readyState === WebSocket.OPEN;
                const wsMultiplier = wsIsActive ? 3 : 1;
                const nextCheckDelay = this._adaptiveIntervalMs * this._backoffFactor * wsMultiplier;
                
                console.log(`[PollingManager] Prochaine vérification dans ${Math.round(nextCheckDelay/1000)}s (backoff: ${this._backoffFactor.toFixed(2)}x, ws: ${wsMultiplier}x)`);
                this._timer = setTimeout(() => this._checkStatus(), nextCheckDelay);
                
            } catch (error) {
                // En cas d'erreur réseau ou autre
                this._consecutiveErrors++;
                console.error('[PollingManager] Erreur lors de la vérification:', error);
                
                // Détection d'une erreur d'annulation contrôlée
                const isAbortError = error.name === 'AbortError';
                
                // Augmenter le délai en fonction du nombre d'erreurs consécutives
                // Erreur d'annulation = temps d'attente plus court car c'était intentionnel
                const baseDelayMs = isAbortError ? 2000 : 3000;
                const delayMs = baseDelayMs + (this._consecutiveErrors * (isAbortError ? 1000 : 1500));
                
                console.log(`[PollingManager] Nouvelle tentative dans ${Math.round(delayMs/1000)}s (erreur #${this._consecutiveErrors}, ${isAbortError ? 'timeout' : 'réseau'})`);
                this._timer = setTimeout(() => this._checkStatus(), delayMs);
            }
        }
    };

    // Fonction pour arrêter proprement un polling existant
    function stopExistingPolling() {
        window.PollingManager.stopPolling();
        
        // Maintenir la compatibilité avec l'ancien système
        if (window.indexingTimer) {
            console.log('Arrêt du polling existant (legacy)');
            clearTimeout(window.indexingTimer);
            window.indexingTimer = null;
        }
        // Créer un nouvel ID pour la prochaine session de polling
        window.activePollingId = Date.now().toString();
        console.log(`Nouvelle session de polling créée (ID: ${window.activePollingId})`);
        
        // Réinitialiser les variables de polling
        window.indexingStartTime = Date.now();
        window.indexingApiCallCount = 0;
    }

    async function checkIndexingStatus() {
        // Démarrer le polling via le PollingManager
        window.PollingManager.startPolling();
        
        // Le reste de cette fonction ne sera pas exécuté
        // Code maintenu pour des raisons de compatibilité
        return;
        
        // Capturer l'ID de polling actif au moment de l'appel
        const currentPollingId = window.activePollingId;
        
        try {
            // Vérifier si cette session est toujours l'active
            if (currentPollingId !== window.activePollingId) {
                console.log(`Session de polling abandonnée (ID: ${currentPollingId})`);
                return;
            }
            
            // Incrémenter le compteur d'appels API
            window.indexingApiCallCount = (window.indexingApiCallCount || 0) + 1;
            
            const response = await fetch('/api/v1/indexing-status');
            const status = await response.json();
            
            // Revérifier si cette session est toujours l'active après l'appel réseau
            if (currentPollingId !== window.activePollingId) {
                console.log(`Session de polling abandonnée après la requête (ID: ${currentPollingId})`);
                return;
            }
            
            // Vérifier explicitement le champ 'completed' qui indique si le traitement est terminé
            if (status.completed === true) {
                console.log('Traitement terminé, arrêt du polling');
                completeIndexing(status);
                return;
            }
            
            // Si le traitement est toujours en cours
            if (status.in_progress) {
                // Mettre à jour le modal
                uploadStatus.textContent = `Traitement en cours : ${status.processed_files}/${status.total_files} fichiers`;
                if (status.total_chunks) {
                    documentPages.textContent = `Pages traitées : ${status.total_chunks}`;
                }
                
                // Mettre à jour le badge dans la sidebar
                indexingStatus.classList.remove('hidden');
                indexingStatus.querySelector('div').textContent = `${Math.round((status.processed_files / status.total_files) * 100)}%`;
                
                // Calcul du temps écoulé depuis le début du traitement
                const elapsedTime = (Date.now() - window.indexingStartTime) / 1000; // en secondes
                
                // Utiliser un délai constant de 2 secondes pour tous les appels
                const nextDelay = 2000; // Délai fixe de 2 secondes
                
                // Forcer l'arrêt après 5 minutes ou après MAX_API_CALLS appels pour éviter les boucles infinies
                const MAX_API_CALLS = 150; // Maximum d'appels à l'API (augmenté pour compenser le délai constant)
                if (elapsedTime > 300 || window.indexingApiCallCount >= MAX_API_CALLS) {
                    const reason = elapsedTime > 300 ? 'Timeout de 5 minutes' : `Limite de ${MAX_API_CALLS} appels API`;
                    console.log(`${reason} atteint, arrêt du polling`);
                    completeIndexing({...status, timeout: true, reason: reason});
                    return;
                }
                
                console.log(`Prochain appel dans ${nextDelay/1000} secondes (appel #${window.indexingApiCallCount}, ID: ${currentPollingId})`);
                
                // Stocker la référence du timer pour pouvoir l'annuler si nécessaire
                clearTimeout(window.indexingTimer);
                // Vérifie une dernière fois que l'ID est toujours valide
                if (currentPollingId === window.activePollingId) {
                    window.indexingTimer = setTimeout(checkIndexingStatus, nextDelay);
                } else {
                    console.log(`Session abandonnée avant prochain appel (ID: ${currentPollingId})`);
                }
            } else {
                // Traitement terminé ou erreur
                completeIndexing(status);
            }
        } catch (error) {
            console.error('Erreur lors du polling:', error);
            // En cas d'erreur, arrêter le polling après un délai
            clearTimeout(window.indexingTimer);
            // Vérifie que l'ID est toujours valide
            if (currentPollingId === window.activePollingId) {
                window.indexingTimer = setTimeout(checkIndexingStatus, 2000);
            }
        }
    }
    
    // Fonction pour terminer proprement l'indexation
    function completeIndexing(status) {
        // Vérifier s'il y a eu un upload récent (moins de 5 secondes)
        const timeSinceUpload = Date.now() - (window.lastUploadTime || 0);
        if (timeSinceUpload < 5000) {
            console.log(`[completeIndexing] Upload récent détecté (${Math.round(timeSinceUpload/1000)}s), attendre avant de terminer`);
            // Ne pas terminer le traitement maintenant, mais réessayer plus tard
            setTimeout(() => completeIndexing(status), 2000);
            return;
        }
        
        // Marquer explicitement que le traitement est terminé, mais pas tout de suite
        // pour permettre l'affichage du message de succès
        
        if (status.error_occurred) {
            uploadStatus.textContent = `Erreur : ${status.error_message || "Erreur inconnue"}`;
        } else if (status.timeout) {
            uploadStatus.textContent = `Traitement terminé (${status.reason || "timeout"})`;
        } else {
            uploadStatus.textContent = 'Traitement terminé avec succès';
        }
        
        // Afficher des statistiques d'appels API si disponibles
        if (window.indexingApiCallCount) {
            console.log(`Indexation terminée après ${window.indexingApiCallCount} appels à l'API`);
        }
        
        // Nettoyer l'interface après un délai
        setTimeout(() => {
            // Désactiver explicitement le drapeau de traitement
            processingInProgress = false;
            
            uploadModal.classList.add('hidden');
            uploadProgress.classList.add('hidden');
            indexingStatus.classList.add('hidden');
            
            // Rafraîchir les stats UNE SEULE FOIS
            refreshStats();
        }, 2000);
    }
    
    // Fonction pour rafraîchir les statistiques affichées
    let lastStatsRefreshTime = 0;
    const STATS_REFRESH_COOLDOWN = 2000; // 2 secondes de cooldown minimum
    
    async function refreshStats() {
        // Appliquer un throttling pour les rafraîchissements fréquents
        const now = Date.now();
        if (now - lastStatsRefreshTime < STATS_REFRESH_COOLDOWN) {
            console.log(`Rafraîchissement des statistiques ignoré (throttling, prochain rafraîchissement dans ${Math.ceil((lastStatsRefreshTime + STATS_REFRESH_COOLDOWN - now)/1000)}s)`);
            return;
        }
        
        lastStatsRefreshTime = now;
        console.log('Rafraîchissement des statistiques');
        let statsData;

        try {
            // Essayer d'utiliser le nouvel endpoint qui fournit des statistiques plus détaillées
            const response = await fetch('/api/v1/documents/statistics');
            if (response.ok) {
                statsData = await response.json();
                
                // Afficher les informations détaillées
                statsDisplay.querySelector('.documents-count').textContent = statsData.documents_count;
                
                // Afficher des informations sur les vecteurs
                const vectorsInfo = document.querySelector('.vectors-info');
                if (vectorsInfo) {
                    // Mettre à jour les infos existantes
                    vectorsInfo.querySelector('.vectors-count').textContent = statsData.vectors_count;
                    vectorsInfo.querySelector('.indexed-vectors').textContent = statsData.indexed_vectors_count;
                    vectorsInfo.querySelector('.indexing-percentage').textContent = `${statsData.indexing_percentage}%`;
                    
                    // Mettre à jour la couleur en fonction du statut d'indexation
                    const statusIndicator = vectorsInfo.querySelector('.indexing-status');
                    if (statusIndicator) {
                        if (statsData.is_fully_indexed) {
                            statusIndicator.className = 'indexing-status text-green-500';
                            statusIndicator.textContent = 'Complètement indexé';
                        } else if (statsData.indexing_percentage > 0) {
                            statusIndicator.className = 'indexing-status text-yellow-500';
                            statusIndicator.textContent = 'Indexation partielle';
                        } else {
                            statusIndicator.className = 'indexing-status text-gray-500';
                            statusIndicator.textContent = 'Non indexé';
                        }
                    }
                } else {
                    // Créer un nouvel élément d'information s'il n'existe pas
                    const vectorsInfoHtml = `
                        <div class="vectors-info mt-4 p-4 bg-gray-100 rounded-lg">
                            <h3 class="text-lg font-semibold mb-2">Informations sur les vecteurs</h3>
                            <p>Total: <span class="vectors-count font-medium">${statsData.vectors_count}</span></p>
                            <p>Indexés: <span class="indexed-vectors font-medium">${statsData.indexed_vectors_count}</span> 
                               (<span class="indexing-percentage">${statsData.indexing_percentage}%</span>)</p>
                            <p>Statut: <span class="indexing-status ${statsData.is_fully_indexed ? 'text-green-500' : 'text-yellow-500'}">
                                ${statsData.is_fully_indexed ? 'Complètement indexé' : 'Indexation partielle'}</span></p>
                        </div>
                    `;
                    statsDisplay.insertAdjacentHTML('beforeend', vectorsInfoHtml);
                }
                
                console.log('Statistiques rafraîchies avec succès (endpoint détaillé)');
                return;
            }
        } catch (error) {
            console.warn('Erreur avec le nouvel endpoint de statistiques, utilisation du fallback:', error);
        }

        // Fallback: utiliser l'ancien endpoint si le nouveau n'est pas disponible
        try {
            const response = await fetch('/api/v1/stats');
            if (response.ok) {
                statsData = await response.json();
                statsDisplay.querySelector('.documents-count').textContent = statsData.documents_count || 0;
                console.log('Statistiques rafraîchies avec succès (endpoint simple)');
            } else {
                console.error('Erreur lors de la récupération des statistiques:', response.statusText);
            }
        } catch (error) {
            console.error('Erreur lors de la récupération des statistiques:', error);
        }
    }

    // Fonction pour mettre à jour l'interface d'indexation
    function updateIndexingUI(status) {
        if (!status) return;
        
        console.log('Mise à jour de l\'interface avec le statut:', status);
        
        // Récupérer les éléments DOM nécessaires
        const indexingStatus = document.getElementById('indexingStatus');
        const uploadModal = document.getElementById('uploadModal');
        const uploadStatus = document.getElementById('uploadStatus');
        
        if (!indexingStatus) return;
        
        // Mettre à jour l'état de traitement global
        processingInProgress = status.in_progress || status.ocr_in_progress;
        
        // Afficher l'état d'avancement global
        let statusHtml = '';
        
        if (status.error_occurred) {
            statusHtml = `
                <div class="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
                    <p class="font-bold">Erreur lors de l'indexation</p>
                    <p>${status.error_message || "Erreur inconnue"}</p>
                </div>
            `;
            processingInProgress = false;
        } else if (status.in_progress) {
            // Calcul des pourcentages
            const filesProgress = status.total_files ? Math.round((status.processed_files / status.total_files) * 100) : 0;
            const chunksProgress = status.total_chunks ? Math.round((status.indexed_chunks / status.total_chunks) * 100) : 0;
            
            statusHtml = `
                <div class="mb-2">
                    <p>Traitement en cours, veuillez patienter...</p>
                    <p class="text-sm text-gray-600">Fichier en cours: ${status.current_file || 'Initialisation...'}</p>
                </div>
                <div class="mb-4">
                    <div class="flex justify-between mb-1">
                        <span>Fichiers traités: ${status.processed_files}/${status.total_files} fichiers</span>
                        <span>${filesProgress}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-blue-600 h-2 rounded-full" style="width: ${filesProgress}%"></div>
                    </div>
                </div>
                <div>
                    <div class="flex justify-between mb-1">
                        <span>Fragments indexés: ${status.indexed_chunks}/${status.total_chunks} fragments</span>
                        <span>${chunksProgress}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-green-600 h-2 rounded-full" style="width: ${chunksProgress}%"></div>
                    </div>
                </div>
            `;
        } else if (status.ocr_in_progress) {
            // Afficher le statut OCR
            const ocrProgress = status.ocr_progress || 0;
            
            statusHtml = `
                <div class="mb-2">
                    <p>Reconnaissance de texte (OCR) en cours...</p>
                    <p class="text-sm text-gray-600">Page: ${status.ocr_current_page || 0}/${status.ocr_total_pages || '?'}</p>
                </div>
                <div>
                    <div class="flex justify-between mb-1">
                        <span>Progression OCR</span>
                        <span>${ocrProgress}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-purple-600 h-2 rounded-full" style="width: ${ocrProgress}%"></div>
                    </div>
                </div>
            `;
        } else if (status.completed) {
            // Indexation terminée
            statusHtml = `
                <div class="bg-green-100 border-l-4 border-green-500 text-green-700 p-4" role="alert">
                    <p class="font-bold">Document traité avec succès!</p>
                    <p>Le document a été complètement indexé et est prêt à être interrogé.</p>
                </div>
            `;
            // Ne pas désactiver processingInProgress ici pour éviter la fermeture prématurée
            // Laisser finishProcessing gérer cela
        }
        
        // Mettre à jour l'interface
        indexingStatus.innerHTML = statusHtml;
        
        // Afficher/masquer la modal d'upload en fonction de l'état
        if (uploadModal && uploadStatus) {
            // Vérifier s'il y a eu un upload récent (moins de 5 secondes)
            const timeSinceUpload = Date.now() - (window.lastUploadTime || 0);
            const isRecentUpload = timeSinceUpload < 5000;
            
            // Garder la modal visible pour tous les états de processing (upload, OCR, indexation)
            // OU si l'upload est récent, même si le statut est "completed"
            if (status.in_progress || status.ocr_in_progress || isRecentUpload) {
                uploadModal.classList.remove('hidden');
                if (status.in_progress) {
                    uploadStatus.innerHTML = 'Traitement du document en cours...';
                } else if (status.ocr_in_progress) {
                    uploadStatus.innerHTML = 'Reconnaissance de texte (OCR) en cours...';
                } else if (isRecentUpload && !status.in_progress && !status.ocr_in_progress) {
                    // Message pour la phase d'initialisation
                    uploadStatus.innerHTML = 'Initialisation du traitement en cours...';
                    console.log('[updateIndexingUI] Upload récent, garder le modal visible malgré completed:', timeSinceUpload);
                }
            } else if (status.completed) {
                // Ne pas masquer tout de suite pour que l'utilisateur puisse voir que c'est terminé
                uploadStatus.innerHTML = 'Traitement terminé!';
                // Ne pas masquer la modal ici, laisser finishProcessing s'en charger
            }
        }
    }
{{ ... }}
    // Fonction appelée quand l'indexation est terminée
    function finishProcessing() {
        console.log('Finalisation du traitement d\'indexation');
        
        // Arrêter le polling s'il est actif
        window.PollingManager.stopPolling();
        
        // Pour la compatibilité avec le code existant
        if (window.indexingTimer) {
            clearTimeout(window.indexingTimer);
            window.indexingTimer = null;
        }
        
        // Mettre à jour l'interface
        const uploadModal = document.getElementById('uploadModal');
        if (uploadModal) {
            // Augmenter le délai pour permettre à l'utilisateur de voir le message de succès
            setTimeout(() => {
                // Désactiver le drapeau de traitement APRÈS l'affichage du message de succès
                processingInProgress = false;
                uploadModal.classList.add('hidden');
            }, 3500); // Augmenté de 2000 à 3500 ms
        } else {
            // Désactiver le drapeau même si le modal n'est pas trouvé
            processingInProgress = false;
        }
        
        // Préparer l'interface pour les questions
        const queryForm = document.getElementById('questionForm');
        const queryInput = document.getElementById('query');
        
        if (queryForm && queryInput) {
            queryForm.classList.remove('opacity-50', 'pointer-events-none');
            queryInput.disabled = false;
            queryInput.placeholder = "Posez une question sur votre document...";
            queryInput.focus();
        }
        
        // Nettoyer les variables globales de suivi
        window.lastIndexingStatus = null;
        window.lastIndexingStatusTime = null;
        
        console.log('Traitement terminé, interface mise à jour');
    }
{{ ... }}
    // Variable globale pour suivre l'état de connexion WebSocket
    window.webSocketConnected = false;
    window.lastIndexingStatusTime = 0;
    window.socket = null;
    window.reconnectAttempts = 0;
    window.maxReconnectAttempts = 5;
    
    // Variables globales pour les statuts d'indexation
    let currentIndexingStatus = null;
    let indexingStatus = null;
    let uploadInProgress = false;
    let processingInProgress = false;

    // Variables pour le suivi des uploads récents
    window.lastUploadTime = 0;
    window.UPLOAD_GRACE_PERIOD = 10000; // 10 secondes de délai de sécurité

    function cleanupWebSockets() {
        // Nettoyer les sockets existants
        if (window.socket) {
            console.log('[WebSocket] Fermeture d\'une connexion existante');
            try {
                window.socket.close();
            } catch (e) {
                console.error('[WebSocket] Erreur lors de la fermeture:', e);
            }
            window.socket = null;
            window.webSocketConnected = false;
        }
    }
    
    function stopExistingPolling() {
        // Arrêter le polling s'il est en cours
        if (window.PollingManager && window.PollingManager._timer) {
            console.log('[PollingManager] Arrêt d\'un polling existant');
            window.PollingManager.stopPolling();
        }
    }
    
    // Initialiser la connexion WebSocket
    function initializeWebSockets() {
        // Nettoyer les connexions existantes
        cleanupWebSockets();
        
        // Définir les variables globales de WebSocket si elles n'existent pas
        window.webSocketConnected = false;
        window.reconnectAttempts = 0;
        window.maxReconnectAttempts = 5;
        window.pingInterval = null;
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/v1/ws`;
        
        console.log('[WebSocket] Tentative de connexion à:', wsUrl);
        
        try {
            window.socket = new WebSocket(wsUrl);
            
            socket.addEventListener('open', function() {
                console.log('[WebSocket] Connexion établie avec succès');
                window.webSocketConnected = true;
                window.reconnectAttempts = 0;
                
                // Mettre à jour le statut WebSocket dans le semaphore s'il existe
                if (window.PollingManager) {
                    try {
                        const semaphore = window.PollingManager._getSemaphore();
                        if (semaphore) {
                            semaphore.wsConnected = true;
                            window.PollingManager._setSemaphore(semaphore);
                        }
                    } catch (e) {
                        console.warn('[WebSocket] Erreur lors de la mise à jour du semaphore:', e);
                    }
                }
                
                // Ajouter un ping périodique pour maintenir la connexion
                window.pingInterval = setInterval(function() {
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        try {
                            socket.send(JSON.stringify({ 
                                type: 'ping', 
                                data: { timestamp: Date.now() } 
                            }));
                            console.log('[WebSocket] Ping périodique envoyé');
                        } catch (e) {
                            console.error('[WebSocket] Erreur lors de l\'envoi du ping périodique:', e);
                            
                            // Si erreur lors du ping, vérifier l'état de la connexion
                            if (socket.readyState !== WebSocket.OPEN) {
                                console.warn('[WebSocket] Connexion interrompue détectée pendant le ping');
                                window.webSocketConnected = false;
                                
                                // Nettoyer l'intervalle de ping si la connexion est rompue
                                if (window.pingInterval) {
                                    clearInterval(window.pingInterval);
                                    window.pingInterval = null;
                                }
                                
                                // Tenter de reconnecter
                                setTimeout(initializeWebSockets, 2000);
                            }
                        }
                    }
                }, 30000); // Ping toutes les 30 secondes
                
                // Envoyer un message de test initial
                try {
                    socket.send(JSON.stringify({ type: 'ping', data: { timestamp: Date.now() } }));
                    console.log('[WebSocket] Message ping initial envoyé');
                } catch (e) {
                    console.error('[WebSocket] Erreur lors de l\'envoi du ping initial:', e);
                }
            });
            
            socket.addEventListener('error', function(event) {
                console.error('[WebSocket] Erreur de connexion:', event);
                window.webSocketConnected = false;
                
                // Si le WebSocket échoue, basculer sur le polling
                if (window.PollingManager && !window.PollingManager._polling) {
                    console.log('[WebSocket] Échec, basculement vers le polling');
                    window.PollingManager.startPolling();
                }
            });
            
            socket.addEventListener('close', function(event) {
                console.log('[WebSocket] Connexion fermée:', event);
                window.webSocketConnected = false;
                
                // Mettre à jour le semaphore pour indiquer que WebSocket n'est plus disponible
                if (window.PollingManager) {
                    try {
                        const semaphore = window.PollingManager._getSemaphore();
                        if (semaphore) {
                            semaphore.wsConnected = false;
                            window.PollingManager._setSemaphore(semaphore);
                        }
                    } catch (e) {
                        console.warn('[WebSocket] Erreur lors de la mise à jour du semaphore:', e);
                    }
                }
                
                // Nettoyer l'intervalle de ping
                if (window.pingInterval) {
                    clearInterval(window.pingInterval);
                    window.pingInterval = null;
                }
                
                // Tenter de se reconnecter automatiquement (max 5 fois)
                if (window.reconnectAttempts < window.maxReconnectAttempts) {
                    window.reconnectAttempts++;
                    const delay = Math.min(3000 * window.reconnectAttempts, 10000);
                    console.log(`[WebSocket] Tentative de reconnexion ${window.reconnectAttempts}/${window.maxReconnectAttempts} dans ${delay/1000}s`);
                    setTimeout(initializeWebSockets, delay);
                } else {
                    console.log('[WebSocket] Nombre maximum de tentatives atteint, basculement vers le polling');
                    if (window.PollingManager && !window.PollingManager._polling) {
                        window.PollingManager.startPolling();
                    }
                }
            });
            
            socket.addEventListener('message', function(event) {
                console.log('[WebSocket] Message reçu');
                try {
                    const data = JSON.parse(event.data);
                    console.log('[WebSocket] Type de message:', data.type);
                    
                    // Gérer différents types de messages
                    switch(data.type) {
                        case 'indexing_status':
                            // Traiter les mises à jour d'indexation
                            console.log('[WebSocket] Statut d\'indexation reçu:', data.data);
                            
                            // S'assurer que la fenêtre de statut est visible si nécessaire
                            if (data.data.in_progress || data.data.ocr_in_progress) {
                                const uploadModal = document.getElementById('uploadModal');
                                if (uploadModal) {
                                    uploadModal.classList.remove('hidden');
                                    // Marquer explicitement qu'un traitement est en cours
                                    processingInProgress = true;
                                }
                            }
                            
                            // Gérer la mise à jour du statut
                            handleIndexingStatusUpdate(data.data);
                            
                            // Marquer explicitement le moment de la dernière mise à jour
                            window.lastIndexingStatusTime = Date.now();
                            
                            // Stopper temporairement le check unique avec WebSocket actif
                            if (window.PollingManager) {
                                window.PollingManager._checkOnceWithWebSocket = false;
                                
                                // Si le polling est en cours et que les WebSockets fonctionnent bien, arrêter le polling
                                if (window.PollingManager._polling && window.webSocketConnected) {
                                    console.log('[WebSocket] WebSocket fonctionnel, arrêt du polling');
                                    window.PollingManager.stopPolling();
                                }
                            }
                            break;
{{ ... }}
                        case 'ocr_status':
                            // Traiter les mises à jour OCR
                            console.log('[WebSocket] Statut OCR reçu:', data.data);
                            
                            // S'assurer que la fenêtre de statut est visible pour les mises à jour OCR
                            const ocr_uploadModal = document.getElementById('uploadModal');
                            if (ocr_uploadModal) {
                                ocr_uploadModal.classList.remove('hidden');
                                // Marquer explicitement qu'un traitement est en cours
                                processingInProgress = true;
                                // Mettre à jour le statut d'OCR dans l'interface
                                const uploadStatus = document.getElementById('uploadStatus');
                                if (uploadStatus) {
                                    uploadStatus.innerHTML = 'Reconnaissance de texte (OCR) en cours...';
                                }
                            }
                            
                            updateOCRStatus(data.data);
                            break;
{{ ... }}
                        case 'follow_up_questions':
                            // Traiter les suggestions de questions de suivi
                            displayFollowUpQuestions(data.questions);
                            break;
                            
                        case 'pong':
                            console.log('[WebSocket] Pong reçu du serveur:', data.data);
                            break;
                            
                        case 'connected':
                            console.log('[WebSocket] Confirmation de connexion reçue:', data.data);
                            break;
                        
                        // Autres cas existants...
                        default:
                            console.log(`[WebSocket] Type de message non géré: ${data.type}`);
                            break;
                    }
                } catch (e) {
                    console.error('[WebSocket] Erreur lors du traitement du message:', e);
                }
            });
        } catch (error) {
            console.error('[WebSocket] Erreur lors de la création de la connexion WebSocket:', error);
            // En cas d'erreur, utiliser le polling comme fallback
            if (window.PollingManager && !window.PollingManager._polling) {
                window.PollingManager.startPolling();
            }
        }
    }
    
    // Fonction pour gérer les mises à jour de statut d'indexation via WebSocket
    function handleIndexingStatusUpdate(status) {
        console.log('Mise à jour du statut d\'indexation via WebSocket:', status);
        
        // S'assurer que la fenêtre de statut est visible si nécessaire
        if (status.in_progress || status.ocr_in_progress) {
            const uploadModal = document.getElementById('uploadModal');
            if (uploadModal) {
                uploadModal.classList.remove('hidden');
            }
            
            // Marquer explicitement le moment de la dernière mise à jour
            window.lastIndexingStatusTime = Date.now();
        } else if (status.completed === true) {
            // Vérifier si l'upload est récent
            const timeSinceUpload = Date.now() - window.lastUploadTime;
            if (timeSinceUpload < window.UPLOAD_GRACE_PERIOD) {
                console.log(`[WebSocket] Ignorer le statut completed=true (upload il y a ${Math.round(timeSinceUpload/1000)}s)`);
                // Ne pas fermer le modal, probablement une condition de course
                const uploadModal = document.getElementById('uploadModal');
                if (uploadModal) {
                    uploadModal.classList.remove('hidden');
                }
                return; // Très important: ne pas continuer le traitement
            }
        }
        
        // Mettre à jour l'interface utilisateur
        updateIndexingUI(status);
        
        // Si l'indexation est terminée (et pas une fausse alerte), finaliser le processus
        if (status.completed === true) {
            const timeSinceUpload = Date.now() - window.lastUploadTime;
            if (timeSinceUpload >= window.UPLOAD_GRACE_PERIOD) {
                console.log(`[WebSocket] Finalisation après ${Math.round(timeSinceUpload/1000)}s depuis l'upload`);
                finishProcessing();
            }
        }
        
        // Stocker le dernier statut reçu pour le fallback
        window.lastIndexingStatus = status;
        window.lastIndexingStatusTime = Date.now();
        
        // Partager le statut entre les onglets via localStorage
        try {
            localStorage.setItem('latest_indexing_status', JSON.stringify({
                data: status,
                timestamp: Date.now()
            }));
        } catch (e) {
            console.warn('Impossible de stocker le statut dans localStorage:', e);
        }
    }
    
    // Ajouter un écouteur d'événements storage pour synchroniser entre onglets
    window.addEventListener('storage', function(event) {
        if (event.key === 'latest_indexing_status') {
            try {
                const data = JSON.parse(event.newValue);
                if (data && data.timestamp > (window.lastIndexingStatusTime || 0)) {
                    handleIndexingStatusUpdate(data.data);
                }
            } catch (e) {
                console.error('Erreur lors du traitement du statut depuis localStorage:', e);
            }
        }
    });
    
    // Gérer les événements de cycle de vie de la page pour les WebSockets
    window.addEventListener('load', initializeWebSockets);
    window.addEventListener('beforeunload', cleanupWebSockets);
    
    // Fonction pour poser une question suggérée
    window.askQuestion = (question) => {
        queryInput.value = question;
        queryForm.dispatchEvent(new Event('submit'));
    };

    // Fonction pour afficher les questions de suivi suggérées
    function displayFollowUpQuestions(questions) {
        if (!questions || !Array.isArray(questions) || questions.length === 0) return;
        
        console.log('Affichage des questions de suivi:', questions);
        
        // Trouver l'élément où afficher les questions
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        // Créer l'élément HTML pour les questions suggérées
        const questionsHtml = `
            <div class="mt-4 space-y-2 follow-up-questions">
                <p class="font-semibold text-gray-700">Questions suggérées :</p>
                <ul class="space-y-1">
                    ${questions.map(q => `
                        <li>
                            <button class="text-left text-blue-600 hover:text-blue-800 hover:underline" onclick="askQuestion('${q.replace(/'/g, "\\'")}')">
                                ${q}
                            </button>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
        
        // Ajouter l'élément à la conversation
        const messageDiv = document.createElement('div');
        messageDiv.className = 'py-2 px-4 my-2 rounded-lg bg-gray-100 system-message';
        messageDiv.innerHTML = questionsHtml;
        chatMessages.appendChild(messageDiv);
        
        // Faire défiler jusqu'au bas du chat
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Gestion des requêtes
    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const query = queryInput.value.trim();
        if (!query) return;
        
        // Désactiver l'input pendant le traitement
        queryInput.disabled = true;
        sendButton.disabled = true;
        
        // Afficher la requête
        addMessage('user', query);
        
        // Vider l'input immédiatement
        queryInput.value = '';

        // Afficher la bulle de réflexion
        const thinkingId = showThinking();
        
        try {
            const response = await fetch('/api/v1/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query })
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la requête');
            }

            const result = await response.json();
            
            // Cacher la bulle de réflexion
            hideThinking(thinkingId);
            
            // Afficher la réponse
            if (result.answer) {
                addMessage('assistant', result.answer);
            } else {
                throw new Error('Réponse invalide du serveur');
            }

        } catch (error) {
            // Cacher la bulle de réflexion en cas d'erreur
            hideThinking(thinkingId);
            console.error('Erreur:', error);
            addMessage('system', 'Une erreur est survenue lors du traitement de votre requête.');
        } finally {
            // Réactiver l'input
            queryInput.disabled = false;
            sendButton.disabled = false;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    });

    function showThinking() {
        const thinkingDiv = document.createElement('div');
        const id = 'thinking-' + Date.now();
        thinkingDiv.id = id;
        thinkingDiv.className = 'p-4 rounded-lg bg-white shadow-sm mr-12 flex items-center';
        thinkingDiv.innerHTML = `
            <div class="flex space-x-2 items-center">
                <span class="text-gray-600">CFF IA réfléchit</span>
                <div class="flex space-x-1">
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot animation-delay-200"></div>
                    <div class="thinking-dot animation-delay-400"></div>
                </div>
            </div>
        `;
        chatMessages.appendChild(thinkingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return id;
    }

    function hideThinking(id) {
        const thinkingDiv = document.getElementById(id);
        if (thinkingDiv) {
            thinkingDiv.remove();
        }
    }

    function addMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `p-4 rounded-lg ${type === 'user' ? 'bg-blue-50 ml-12' : type === 'assistant' ? 'bg-white shadow-sm mr-12' : 'bg-gray-50 text-sm'}`;
        
        // Convertir les retours à la ligne en <br> sauf si le contenu contient des balises HTML
        if (typeof content === 'string' && !/<[a-z][\s\S]*>/i.test(content)) {
            content = content.replace(/\n/g, '<br>');
        }
        
        messageDiv.innerHTML = content;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showError(message) {
        addMessage('system', `⚠️ ${message}`);
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
    }

    // Fermer le modal en cliquant en dehors
    uploadModal.addEventListener('click', (e) => {
        if (e.target === uploadModal) {
            // Ne pas fermer le modal si un traitement est en cours
            if (!processingInProgress) {
                uploadModal.classList.add('hidden');
            } else {
                console.log('Tentative de fermeture du modal ignorée - traitement en cours');
            }
        }
    });

    // Fonction pour mettre à jour le statut OCR
    function updateOCRStatus(status) {
        if (!status) return;
        
        console.log('Mise à jour du statut OCR:', status);
        
        // Si les données OCR font partie d'un statut d'indexation plus large,
        // déléguer à updateIndexingUI
        if (status.in_progress !== undefined || status.completed !== undefined) {
            updateIndexingUI(status);
            return;
        }
        
        // Récupérer les éléments DOM nécessaires pour l'OCR spécifiquement
        const ocrStatusElement = document.getElementById('ocrStatus');
        if (!ocrStatusElement) return;
        
        // Construire l'affichage OCR
        let ocrHtml = '';
        
        if (status.ocr_in_progress) {
            const progress = status.ocr_progress || 0;
            
            ocrHtml = `
                <div class="mb-2">
                    <p>Reconnaissance de texte (OCR) en cours...</p>
                    <p class="text-sm text-gray-600">Page: ${status.ocr_current_page || 0}/${status.ocr_total_pages || '?'}</p>
                </div>
                <div>
                    <div class="flex justify-between mb-1">
                        <span>Progression OCR</span>
                        <span>${progress}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-purple-600 h-2 rounded-full" style="width: ${progress}%"></div>
                    </div>
                </div>
            `;
            
            // Afficher les logs OCR s'ils existent
            if (status.ocr_logs && status.ocr_logs.length > 0) {
                ocrHtml += `
                    <div class="mt-2">
                        <p class="text-sm font-semibold">Logs OCR:</p>
                        <pre class="text-xs bg-gray-100 p-2 max-h-32 overflow-y-auto">${status.ocr_logs.join('\n')}</pre>
                    </div>
                `;
            }
        } else {
            // OCR terminé ou non démarré
            ocrHtml = `<p>Aucun traitement OCR en cours</p>`;
        }
        
        // Mettre à jour l'élément DOM
        ocrStatusElement.innerHTML = ocrHtml;
    }

    // Fonction appelée quand l'indexation est terminée
    function finishProcessing() {
        console.log('Finalisation du traitement d\'indexation');
        
        // Arrêter le polling s'il est actif
        window.PollingManager.stopPolling();
        
        // Pour la compatibilité avec le code existant
        if (window.indexingTimer) {
            clearTimeout(window.indexingTimer);
            window.indexingTimer = null;
        }
        
        // Mettre à jour l'interface
        const uploadModal = document.getElementById('uploadModal');
        if (uploadModal) {
            // Augmenter le délai pour permettre à l'utilisateur de voir le message de succès
            setTimeout(() => {
                // Désactiver le drapeau de traitement APRÈS l'affichage du message de succès
                processingInProgress = false;
                uploadModal.classList.add('hidden');
            }, 3500); // Augmenté de 2000 à 3500 ms
        } else {
            // Désactiver le drapeau même si le modal n'est pas trouvé
            processingInProgress = false;
        }
        
        // Préparer l'interface pour les questions
        const queryForm = document.getElementById('questionForm');
        const queryInput = document.getElementById('query');
        
        if (queryForm && queryInput) {
            queryForm.classList.remove('opacity-50', 'pointer-events-none');
            queryInput.disabled = false;
            queryInput.placeholder = "Posez une question sur votre document...";
            queryInput.focus();
        }
        
        // Nettoyer les variables globales de suivi
        window.lastIndexingStatus = null;
        window.lastIndexingStatusTime = null;
        
        console.log('Traitement terminé, interface mise à jour');
    }
});
