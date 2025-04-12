/**
 * Script principal du tableau de bord OCR
 * 
 * Ce script fournit les fonctionnalités interactives pour le tableau de bord
 * de suivi des tâches OCR. Il gère les mises à jour en temps réel, les contrôles
 * des tâches, et l'affichage des graphiques de performance.
 * 
 * Caractéristiques principales:
 * - Connexion WebSocket pour les mises à jour en temps réel
 * - Gestion des actions sur les tâches (pause, reprise, annulation)
 * - Mise à jour dynamique des éléments de l'interface
 * - Utilitaires pour formater les durées, dates et pourcentages
 * 
 * Auteur: Équipe Technicia
 * Date: Mars 2025
 */

// Utilitaires pour la manipulation de dates et durées
const DateUtils = {
    /**
     * Formate une date en format lisible par l'utilisateur
     * @param {string|Date} date - Date à formater
     * @param {boolean} includeTime - Inclure l'heure dans le format
     * @returns {string} Date formatée
     */
    formatDate: function(date, includeTime = true) {
        if (!date) return '';
        
        const d = new Date(date);
        if (isNaN(d.getTime())) return '';
        
        const options = {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        };
        
        if (includeTime) {
            options.hour = '2-digit';
            options.minute = '2-digit';
            options.second = '2-digit';
        }
        
        return d.toLocaleDateString('fr-FR', options);
    },
    
    /**
     * Formate une durée en secondes en format lisible par l'utilisateur
     * @param {number} seconds - Durée en secondes
     * @returns {string} Durée formatée
     */
    formatDuration: function(seconds) {
        if (!seconds || isNaN(seconds)) return '0s';
        
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        
        return `${h > 0 ? h + 'h ' : ''}${m > 0 || h > 0 ? m + 'm ' : ''}${s}s`;
    },
    
    /**
     * Calcule le temps écoulé depuis une date donnée
     * @param {string|Date} date - Date de référence
     * @returns {string} Temps écoulé formaté
     */
    timeAgo: function(date) {
        if (!date) return '';
        
        const d = new Date(date);
        if (isNaN(d.getTime())) return '';
        
        const now = new Date();
        const diffMs = now - d;
        const diffSec = Math.floor(diffMs / 1000);
        
        if (diffSec < 60) return 'à l\'instant';
        if (diffSec < 3600) return `il y a ${Math.floor(diffSec / 60)} min`;
        if (diffSec < 86400) return `il y a ${Math.floor(diffSec / 3600)} h`;
        
        return this.formatDate(date, false);
    }
};

// Utilitaires pour le formatage des valeurs
const FormatUtils = {
    /**
     * Formate un pourcentage
     * @param {number} value - Valeur entre 0 et 1
     * @param {number} decimals - Nombre de décimales
     * @returns {string} Pourcentage formaté
     */
    formatPercent: function(value, decimals = 1) {
        if (value === undefined || value === null || isNaN(value)) return '0%';
        
        return (value * 100).toFixed(decimals) + '%';
    },
    
    /**
     * Tronque une chaîne à une longueur donnée
     * @param {string} str - Chaîne à tronquer
     * @param {number} maxLength - Longueur maximale
     * @param {boolean} addEllipsis - Ajouter des points de suspension
     * @returns {string} Chaîne tronquée
     */
    truncate: function(str, maxLength = 20, addEllipsis = true) {
        if (!str) return '';
        
        if (str.length <= maxLength) return str;
        
        return str.substring(0, maxLength) + (addEllipsis ? '...' : '');
    },
    
    /**
     * Récupère le nom de fichier à partir d'un chemin
     * @param {string} path - Chemin du fichier
     * @returns {string} Nom du fichier
     */
    basename: function(path) {
        if (!path) return '';
        
        // Normaliser les séparateurs de chemin
        path = path.replace(/\\/g, '/');
        
        // Récupérer le dernier segment du chemin
        return path.split('/').pop();
    }
};

// Gestionnaire d'état des tâches
const TaskStateManager = {
    /**
     * Obtient la couleur associée à un état de tâche
     * @param {string} state - État de la tâche
     * @returns {string} Classe de couleur Bootstrap
     */
    getStateColor: function(state) {
        const colors = {
            'pending': 'secondary',
            'running': 'primary',
            'failed': 'danger',
            'paused': 'warning',
            'completed': 'success',
            'retrying': 'info'
        };
        
        return colors[state] || 'secondary';
    },
    
    /**
     * Obtient le libellé lisible d'un état de tâche
     * @param {string} state - État de la tâche
     * @returns {string} Libellé lisible
     */
    getStateLabel: function(state) {
        const labels = {
            'pending': 'En attente',
            'running': 'En cours',
            'failed': 'Échec',
            'paused': 'En pause',
            'completed': 'Terminée',
            'retrying': 'Nouvelle tentative'
        };
        
        return labels[state] || 'Inconnu';
    },
    
    /**
     * Vérifie si une tâche est active (non terminée)
     * @param {string} state - État de la tâche
     * @returns {boolean} True si la tâche est active
     */
    isActiveState: function(state) {
        return ['pending', 'running', 'paused', 'retrying'].includes(state);
    }
};

// Gestionnaire d'API pour le tableau de bord
const DashboardAPI = {
    /**
     * URL de base pour l'API du tableau de bord
     */
    baseUrl: '/api/dashboard',
    
    /**
     * Récupère les tâches actives
     * @returns {Promise<Array>} Liste des tâches actives
     */
    getActiveTasks: async function() {
        const response = await fetch(`${this.baseUrl}/tasks?active_only=true`);
        return response.json();
    },
    
    /**
     * Récupère l'historique des tâches
     * @param {string} state - État optionnel pour filtrer les tâches
     * @param {number} limit - Nombre maximum de tâches à récupérer
     * @returns {Promise<Array>} Liste des tâches
     */
    getTaskHistory: async function(state = null, limit = 100) {
        let url = `${this.baseUrl}/tasks?limit=${limit}`;
        if (state) {
            url += `&state=${state}`;
        }
        
        const response = await fetch(url);
        return response.json();
    },
    
    /**
     * Récupère les détails d'une tâche
     * @param {string} taskId - ID de la tâche
     * @returns {Promise<Object>} Détails de la tâche
     */
    getTaskDetails: async function(taskId) {
        const response = await fetch(`${this.baseUrl}/tasks/${taskId}`);
        
        if (!response.ok) {
            throw new Error(`Erreur lors de la récupération de la tâche: ${response.status}`);
        }
        
        return response.json();
    },
    
    /**
     * Met à jour l'état d'une tâche
     * @param {string} taskId - ID de la tâche
     * @param {string} state - Nouvel état
     * @param {Object} additionalData - Données supplémentaires
     * @returns {Promise<Object>} Tâche mise à jour
     */
    updateTaskState: async function(taskId, state, additionalData = {}) {
        const response = await fetch(`${this.baseUrl}/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                state: state,
                ...additionalData
            })
        });
        
        if (!response.ok) {
            throw new Error(`Erreur lors de la mise à jour de la tâche: ${response.status}`);
        }
        
        return response.json();
    },
    
    /**
     * Crée une nouvelle tâche
     * @param {Object} taskData - Données de la tâche
     * @returns {Promise<Object>} Tâche créée
     */
    createTask: async function(taskData) {
        const response = await fetch(`${this.baseUrl}/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        });
        
        if (!response.ok) {
            throw new Error(`Erreur lors de la création de la tâche: ${response.status}`);
        }
        
        return response.json();
    },
    
    /**
     * Supprime une tâche
     * @param {string} taskId - ID de la tâche
     * @returns {Promise<boolean>} True si la suppression a réussi
     */
    deleteTask: async function(taskId) {
        const response = await fetch(`${this.baseUrl}/tasks/${taskId}`, {
            method: 'DELETE'
        });
        
        return response.ok;
    },
    
    /**
     * Récupère les métriques de performance
     * @param {string} provider - Fournisseur OCR optionnel
     * @returns {Promise<Array|Object>} Métriques de performance
     */
    getMetrics: async function(provider = null) {
        let url = `${this.baseUrl}/metrics`;
        if (provider) {
            url += `/${provider}`;
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Erreur lors de la récupération des métriques: ${response.status}`);
        }
        
        return response.json();
    }
};

// Gestionnaire d'interface utilisateur pour le tableau de bord
const DashboardUI = {
    /**
     * Initialise l'interface utilisateur du tableau de bord
     */
    init: function() {
        // Initialiser les sélecteurs d'éléments courants
        this.initSelectors();
        
        // Initialiser les gestionnaires d'événements
        this.initEventHandlers();
        
        // Initialiser les mises à jour en temps réel
        this.initRealTimeUpdates();
    },
    
    /**
     * Initialise les sélecteurs d'éléments courants
     */
    initSelectors: function() {
        // Éléments pour la mise à jour des tâches actives
        this.activeTasksTable = document.getElementById('active-tasks-table');
        this.activeTasksCount = document.getElementById('active-tasks-count');
        
        // Boutons de contrôle
        this.refreshButton = document.getElementById('refresh-dashboard');
    },
    
    /**
     * Initialise les gestionnaires d'événements
     */
    initEventHandlers: function() {
        // Gestionnaire pour le bouton de rafraîchissement
        if (this.refreshButton) {
            this.refreshButton.addEventListener('click', function() {
                location.reload();
            });
        }
        
        // Gestionnaires pour les boutons de contrôle des tâches
        this.initTaskControlHandlers();
    },
    
    /**
     * Initialise les gestionnaires pour les boutons de contrôle des tâches
     */
    initTaskControlHandlers: function() {
        // Gestionnaire pour les boutons de pause/reprise
        document.querySelectorAll('.btn-pause-task, .btn-resume-task').forEach(button => {
            button.addEventListener('click', async function() {
                const taskId = this.getAttribute('data-task-id');
                const action = this.classList.contains('btn-pause-task') ? 'pause' : 'resume';
                
                try {
                    const newState = action === 'pause' ? 'paused' : 'running';
                    await DashboardAPI.updateTaskState(taskId, newState);
                    
                    // Mettre à jour l'interface
                    if (action === 'pause') {
                        this.innerHTML = '<i class="fas fa-play"></i>';
                        this.classList.remove('btn-pause-task');
                        this.classList.add('btn-resume-task');
                    } else {
                        this.innerHTML = '<i class="fas fa-pause"></i>';
                        this.classList.remove('btn-resume-task');
                        this.classList.add('btn-pause-task');
                    }
                } catch (error) {
                    console.error(error);
                    alert(`Erreur lors de la ${action === 'pause' ? 'mise en pause' : 'reprise'} de la tâche: ${error.message}`);
                }
            });
        });
        
        // Gestionnaire pour les boutons d'annulation
        document.querySelectorAll('.btn-cancel-task').forEach(button => {
            button.addEventListener('click', async function() {
                const taskId = this.getAttribute('data-task-id');
                
                if (!confirm('Êtes-vous sûr de vouloir annuler cette tâche ?')) {
                    return;
                }
                
                try {
                    await DashboardAPI.updateTaskState(taskId, 'failed', {
                        metadata: {
                            cancelled: true,
                            cancelled_at: new Date().toISOString()
                        }
                    });
                    
                    // Recharger la page
                    location.reload();
                } catch (error) {
                    console.error(error);
                    alert(`Erreur lors de l'annulation de la tâche: ${error.message}`);
                }
            });
        });
        
        // Gestionnaire pour les boutons de relance
        document.querySelectorAll('.btn-retry-task').forEach(button => {
            button.addEventListener('click', async function() {
                const taskId = this.getAttribute('data-task-id');
                
                try {
                    // Récupérer les détails de la tâche
                    const task = await DashboardAPI.getTaskDetails(taskId);
                    
                    // Créer une nouvelle tâche basée sur l'ancienne
                    const newTask = await DashboardAPI.createTask({
                        name: `${task.name} (relance)`,
                        description: `Relance de la tâche ${task.task_id}`,
                        document_path: task.document_path,
                        output_path: task.output_path,
                        ocr_provider: task.ocr_provider,
                        metadata: {
                            ...task.metadata,
                            original_task_id: task.task_id
                        }
                    });
                    
                    // Rediriger vers les détails de la nouvelle tâche
                    window.location.href = `/dashboard/tasks/${newTask.task_id}`;
                } catch (error) {
                    console.error(error);
                    alert(`Erreur lors de la relance de la tâche: ${error.message}`);
                }
            });
        });
    },
    
    /**
     * Initialise les mises à jour en temps réel via WebSocket
     */
    initRealTimeUpdates: function() {
        // Écouter les événements de mise à jour des tâches
        document.addEventListener('task-updated', event => {
            this.updateTaskRow(event.detail);
            this.updateDashboardCounters();
        });
        
        // Écouter les événements de suppression des tâches
        document.addEventListener('task-deleted', event => {
            const taskRow = document.getElementById(`task-row-${event.detail}`);
            if (taskRow) {
                taskRow.remove();
            }
            this.updateDashboardCounters();
        });
        
        // Mettre à jour les durées toutes les secondes
        this.startDurationUpdates();
    },
    
    /**
     * Démarre la mise à jour périodique des durées
     */
    startDurationUpdates: function() {
        setInterval(() => {
            document.querySelectorAll('.task-duration').forEach(element => {
                const startedAt = element.getAttribute('data-started');
                if (startedAt) {
                    const startTime = new Date(startedAt);
                    const now = new Date();
                    const durationMs = now - startTime;
                    element.textContent = DateUtils.formatDuration(durationMs / 1000);
                }
            });
        }, 1000);
    },
    
    /**
     * Met à jour les compteurs du tableau de bord
     */
    updateDashboardCounters: async function() {
        try {
            // Récupérer les tâches actives
            const activeTasks = await DashboardAPI.getActiveTasks();
            if (this.activeTasksCount) {
                this.activeTasksCount.textContent = activeTasks.length;
            }
            
            // Mettre à jour les autres compteurs si nécessaire
            const elements = {
                'completed-tasks-count': { state: 'completed' },
                'error-tasks-count': { state: 'failed' },
                'processed-pages-count': { metrics: true }
            };
            
            for (const [id, config] of Object.entries(elements)) {
                const element = document.getElementById(id);
                if (!element) continue;
                
                if (config.state) {
                    const tasks = await DashboardAPI.getTaskHistory(config.state);
                    element.textContent = tasks.length;
                } else if (config.metrics) {
                    const metrics = await DashboardAPI.getMetrics();
                    let totalPages = 0;
                    
                    if (Array.isArray(metrics)) {
                        metrics.forEach(metric => {
                            totalPages += metric.total_pages;
                        });
                    }
                    
                    element.textContent = totalPages;
                }
            }
        } catch (error) {
            console.error('Erreur lors de la mise à jour des compteurs:', error);
        }
    },
    
    /**
     * Met à jour une ligne de tâche dans le tableau
     * @param {Object} task - Données de la tâche mise à jour
     */
    updateTaskRow: function(task) {
        const row = document.getElementById(`task-row-${task.task_id}`);
        if (!row) return;
        
        // Mettre à jour la progression
        const progressBar = row.querySelector('.progress-bar');
        if (progressBar) {
            const progressPercent = task.progress * 100;
            progressBar.style.width = `${progressPercent}%`;
            progressBar.setAttribute('aria-valuenow', progressPercent);
            progressBar.textContent = FormatUtils.formatPercent(task.progress);
        }
        
        // Mettre à jour la page actuelle
        const pageCounter = row.querySelector('small.text-muted');
        if (pageCounter) {
            pageCounter.textContent = `Page ${task.current_page + 1}/${task.total_pages}`;
        }
        
        // Mettre à jour la durée
        const durationCell = row.querySelector('.task-duration');
        if (durationCell && task.started_at) {
            durationCell.setAttribute('data-started', task.started_at);
        }
        
        // Mettre à jour l'état
        const stateCell = row.querySelector('.task-state');
        if (stateCell) {
            const stateColor = TaskStateManager.getStateColor(task.state);
            const stateLabel = TaskStateManager.getStateLabel(task.state);
            stateCell.innerHTML = `<span class="badge bg-${stateColor}">${stateLabel}</span>`;
        }
        
        // Si la tâche est terminée, recharger la page après un délai
        if (task.state === 'completed' || task.state === 'failed') {
            setTimeout(() => location.reload(), 1000);
        }
    }
};

// Initialiser le tableau de bord lorsque le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser l'interface utilisateur du tableau de bord
    DashboardUI.init();
    
    // Exposer les utilitaires et API pour le débogage
    window.DateUtils = DateUtils;
    window.FormatUtils = FormatUtils;
    window.TaskStateManager = TaskStateManager;
    window.DashboardAPI = DashboardAPI;
});
