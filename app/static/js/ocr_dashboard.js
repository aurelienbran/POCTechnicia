/**
 * Script JavaScript pour le tableau de bord OCR
 * 
 * Ce script gère l'interface utilisateur du tableau de bord OCR, incluant :
 * - Connexions WebSocket pour les mises à jour en temps réel
 * - Gestion de l'affichage de la liste des tâches OCR
 * - Contrôles pour pause/reprise/annulation des tâches
 * - Mise à jour des statistiques et graphiques
 * 
 * Auteur: Équipe Technicia
 * Date: Avril 2025
 */

// Configuration
const API_BASE_URL = '/api/ocr';
const WS_BASE_URL = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const WS_HOST = window.location.host;

// Statut des connexions WebSocket
let taskSocket = null;
let statsSocket = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_INTERVAL = 3000; // 3 secondes

// Cache des données
let tasksCache = new Map();
let statsCache = null;

// État de l'interface
let selectedTaskId = null;
let sortField = 'added_at';
let sortDirection = 'desc';
let currentFilter = 'all';

/**
 * Initialise le tableau de bord OCR
 */
document.addEventListener('DOMContentLoaded', function() {
    initTasksList();
    initStatistics();
    initControlButtons();
    initTaskFilters();
    initTaskSort();
    initUploadForm();
    
    // Établir les connexions WebSocket
    connectToTasksSocket();
    connectToStatsSocket();
    
    // Charger les données initiales
    refreshTasksList();
    refreshStatistics();
    
    // Configuration des rafraîchissements périodiques en cas de problème WebSocket
    setInterval(function() {
        if (taskSocket === null || taskSocket.readyState !== WebSocket.OPEN) {
            refreshTasksList();
        }
        if (statsSocket === null || statsSocket.readyState !== WebSocket.OPEN) {
            refreshStatistics();
        }
    }, 10000); // 10 secondes
});

/**
 * Établit une connexion WebSocket pour les mises à jour des tâches
 */
function connectToTasksSocket() {
    const wsUrl = `${WS_BASE_URL}${WS_HOST}/ws/ocr/all`;
    
    try {
        taskSocket = new WebSocket(wsUrl);
        
        taskSocket.onopen = function() {
            console.log('Connexion WebSocket établie pour les tâches OCR');
            reconnectAttempts = 0;
            updateConnectionStatus('tasks', 'connected');
        };
        
        taskSocket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'task_update') {
                updateTaskInList(data.task_id, data.data);
            } else if (data.type === 'stats') {
                updateStatistics(data.data);
            }
        };
        
        taskSocket.onclose = function() {
            console.log('Connexion WebSocket fermée pour les tâches OCR');
            updateConnectionStatus('tasks', 'disconnected');
            
            // Tenter de se reconnecter
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                setTimeout(connectToTasksSocket, RECONNECT_INTERVAL);
            }
        };
        
        taskSocket.onerror = function(error) {
            console.error('Erreur WebSocket pour les tâches OCR:', error);
            updateConnectionStatus('tasks', 'error');
        };
    } catch (error) {
        console.error('Erreur lors de la création de la connexion WebSocket:', error);
        updateConnectionStatus('tasks', 'error');
    }
}

/**
 * Établit une connexion WebSocket pour les statistiques globales
 */
function connectToStatsSocket() {
    const wsUrl = `${WS_BASE_URL}${WS_HOST}/ws/ocr/all`;
    
    try {
        statsSocket = new WebSocket(wsUrl);
        
        statsSocket.onopen = function() {
            console.log('Connexion WebSocket établie pour les statistiques OCR');
            updateConnectionStatus('stats', 'connected');
        };
        
        statsSocket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'stats') {
                updateStatistics(data.data);
            }
        };
        
        statsSocket.onclose = function() {
            console.log('Connexion WebSocket fermée pour les statistiques OCR');
            updateConnectionStatus('stats', 'disconnected');
        };
        
        statsSocket.onerror = function(error) {
            console.error('Erreur WebSocket pour les statistiques OCR:', error);
            updateConnectionStatus('stats', 'error');
        };
    } catch (error) {
        console.error('Erreur lors de la création de la connexion WebSocket:', error);
        updateConnectionStatus('stats', 'error');
    }
}

/**
 * Met à jour l'indicateur de statut de connexion dans l'interface
 */
function updateConnectionStatus(type, status) {
    const statusElement = document.getElementById(`${type}-connection-status`);
    if (!statusElement) return;
    
    statusElement.className = `connection-status status-${status}`;
    
    switch (status) {
        case 'connected':
            statusElement.innerHTML = '<i class="fas fa-link"></i> Connecté';
            break;
        case 'disconnected':
            statusElement.innerHTML = '<i class="fas fa-unlink"></i> Déconnecté';
            break;
        case 'error':
            statusElement.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Erreur';
            break;
        default:
            statusElement.innerHTML = '<i class="fas fa-question-circle"></i> Inconnu';
    }
}

/**
 * Initialise la liste des tâches OCR
 */
function initTasksList() {
    const tableBody = document.getElementById('tasks-table-body');
    if (!tableBody) return;
    
    // Écouter les événements de clic sur les lignes de tâche
    tableBody.addEventListener('click', function(event) {
        const row = event.target.closest('tr');
        if (!row) return;
        
        const taskId = row.dataset.taskId;
        if (taskId) {
            selectTask(taskId);
        }
    });
}

/**
 * Rafraîchit la liste des tâches OCR via l'API
 */
function refreshTasksList() {
    fetch(`${API_BASE_URL}/tasks`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erreur lors de la récupération des tâches: ${response.status}`);
            }
            return response.json();
        })
        .then(tasks => {
            // Mettre à jour le cache et l'affichage
            tasks.forEach(task => {
                tasksCache.set(task.task_id, task);
            });
            
            renderTasksList();
        })
        .catch(error => {
            console.error('Erreur lors du chargement des tâches:', error);
            showNotification('error', 'Erreur lors du chargement des tâches OCR');
        });
}

/**
 * Met à jour une tâche dans la liste et le cache
 */
function updateTaskInList(taskId, taskData) {
    // Mettre à jour le cache
    tasksCache.set(taskId, taskData);
    
    // Vérifier si la tâche est actuellement affichée
    const tableBody = document.getElementById('tasks-table-body');
    if (!tableBody) return;
    
    // Mettre à jour la ligne correspondante si elle existe
    const row = tableBody.querySelector(`tr[data-task-id="${taskId}"]`);
    if (row) {
        updateTaskRow(row, taskData);
    } else {
        // Sinon, rafraîchir toute la liste
        renderTasksList();
    }
    
    // Mettre à jour les détails si cette tâche est sélectionnée
    if (selectedTaskId === taskId) {
        renderTaskDetails(taskData);
    }
}

/**
 * Met à jour une ligne de tâche existante
 */
function updateTaskRow(row, task) {
    // Mettre à jour les cellules de la ligne
    const statusCell = row.querySelector('.task-status');
    if (statusCell) {
        statusCell.textContent = task.status;
        statusCell.className = `task-status status-${task.status.toLowerCase()}`;
    }
    
    const progressCell = row.querySelector('.task-progress');
    if (progressCell) {
        const progressBar = progressCell.querySelector('.progress-bar');
        if (progressBar) {
            const progressPercent = Math.round(task.progress * 100);
            progressBar.style.width = `${progressPercent}%`;
            progressBar.setAttribute('aria-valuenow', progressPercent);
            progressCell.querySelector('.progress-text').textContent = `${progressPercent}%`;
        }
    }
    
    // Autres mises à jour...
    const timeCell = row.querySelector('.task-time');
    if (timeCell) {
        if (task.status === 'COMPLETED') {
            timeCell.textContent = formatDateTime(task.completed_at);
        } else if (task.status === 'RUNNING' || task.status === 'PREPROCESSING' || task.status === 'POSTPROCESSING') {
            timeCell.textContent = formatTimeDuration(task.estimated_time_remaining);
        } else {
            timeCell.textContent = formatDateTime(task.added_at);
        }
    }
}

/**
 * Sélectionne une tâche et affiche ses détails
 */
function selectTask(taskId) {
    selectedTaskId = taskId;
    
    // Mettre en surbrillance la ligne sélectionnée
    const tableBody = document.getElementById('tasks-table-body');
    if (tableBody) {
        // Supprimer la sélection actuelle
        tableBody.querySelectorAll('tr.selected').forEach(row => {
            row.classList.remove('selected');
        });
        
        // Ajouter la sélection à la nouvelle ligne
        const row = tableBody.querySelector(`tr[data-task-id="${taskId}"]`);
        if (row) {
            row.classList.add('selected');
        }
    }
    
    // Afficher les détails de la tâche
    const task = tasksCache.get(taskId);
    if (task) {
        renderTaskDetails(task);
    } else {
        // Charger les détails si non présents dans le cache
        fetch(`${API_BASE_URL}/tasks/${taskId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Erreur lors de la récupération de la tâche: ${response.status}`);
                }
                return response.json();
            })
            .then(taskData => {
                tasksCache.set(taskId, taskData);
                renderTaskDetails(taskData);
            })
            .catch(error => {
                console.error(`Erreur lors du chargement de la tâche ${taskId}:`, error);
                showNotification('error', `Erreur lors du chargement des détails de la tâche`);
            });
    }
}

// Utilitaires de formatage de dates et durées

/**
 * Formate une date ISO en format lisible
 */
function formatDateTime(isoDate) {
    if (!isoDate) return 'N/A';
    
    const date = new Date(isoDate);
    return date.toLocaleString();
}

/**
 * Formate une durée en secondes en format lisible
 */
function formatTimeDuration(seconds) {
    if (!seconds || seconds <= 0) return 'Terminé';
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    if (minutes > 0) {
        return `${minutes}m ${remainingSeconds}s`;
    } else {
        return `${remainingSeconds}s`;
    }
}

/**
 * Affiche les tâches dans le tableau
 */
function renderTasksList() {
    const tableBody = document.getElementById('tasks-table-body');
    if (!tableBody) return;
    
    // Convertir la Map en tableau pour filtrage et tri
    let tasks = Array.from(tasksCache.values());
    
    // Filtrer selon le filtre actuel
    if (currentFilter !== 'all') {
        tasks = tasks.filter(task => task.status === currentFilter.toUpperCase());
    }
    
    // Trier selon le champ et la direction actuels
    tasks.sort((a, b) => {
        let valueA, valueB;
        
        // Extraire les valeurs à comparer
        switch (sortField) {
            case 'priority':
                valueA = a.priority_value;
                valueB = b.priority_value;
                break;
            case 'progress':
                valueA = a.progress;
                valueB = b.progress;
                break;
            case 'added_at':
                valueA = new Date(a.added_at).getTime();
                valueB = new Date(b.added_at).getTime();
                break;
            case 'status':
                valueA = a.status;
                valueB = b.status;
                break;
            default:
                valueA = a[sortField];
                valueB = b[sortField];
        }
        
        // Comparer les valeurs
        if (valueA < valueB) return sortDirection === 'asc' ? -1 : 1;
        if (valueA > valueB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Vider le tableau
    tableBody.innerHTML = '';
    
    // Remplir avec les nouvelles données
    if (tasks.length === 0) {
        const noTasksRow = document.createElement('tr');
        noTasksRow.innerHTML = '<td colspan="6" class="text-center">Aucune tâche OCR trouvée</td>';
        tableBody.appendChild(noTasksRow);
    } else {
        tasks.forEach(task => {
            const row = createTaskRow(task);
            tableBody.appendChild(row);
        });
    }
    
    // Mettre à jour le compteur
    const counter = document.getElementById('tasks-counter');
    if (counter) {
        counter.textContent = `${tasks.length} tâche(s)`;
    }
}

/**
 * Crée une ligne de tableau pour une tâche
 */
function createTaskRow(task) {
    const row = document.createElement('tr');
    row.dataset.taskId = task.task_id;
    
    // Ajouter la classe selected si la tâche est sélectionnée
    if (selectedTaskId === task.task_id) {
        row.classList.add('selected');
    }
    
    // Définir la classe en fonction du statut
    row.classList.add(`status-${task.status.toLowerCase()}`);
    
    // Créer les cellules
    const progressPercent = Math.round(task.progress * 100);
    
    // Construire le contenu de la ligne
    row.innerHTML = `
        <td class="task-name">${getFileNameFromPath(task.document_path)}</td>
        <td class="task-priority priority-${task.priority.toLowerCase()}">${task.priority}</td>
        <td class="task-status status-${task.status.toLowerCase()}">${task.status}</td>
        <td class="task-progress">
            <div class="progress">
                <div class="progress-bar" role="progressbar" style="width: ${progressPercent}%;"
                     aria-valuenow="${progressPercent}" aria-valuemin="0" aria-valuemax="100">
                </div>
                <span class="progress-text">${progressPercent}%</span>
            </div>
        </td>
        <td class="task-time">
            ${task.status === 'COMPLETED' ? formatDateTime(task.completed_at) :
              (task.status === 'RUNNING' || task.status === 'PREPROCESSING' || task.status === 'POSTPROCESSING') ? 
                formatTimeDuration(task.estimated_time_remaining) : 
                formatDateTime(task.added_at)
            }
        </td>
        <td class="task-actions">
            <div class="btn-group">
                ${getTaskActionButtons(task)}
            </div>
        </td>
    `;
    
    return row;
}

/**
 * Génère les boutons d'action en fonction du statut de la tâche
 */
function getTaskActionButtons(task) {
    const status = task.status;
    
    let buttons = `<button type="button" class="btn btn-sm btn-info view-task" title="Voir les détails">
                     <i class="fas fa-info-circle"></i>
                   </button>`;
    
    if (status === 'QUEUED' || status === 'RUNNING' || status === 'PREPROCESSING' || status === 'POSTPROCESSING') {
        buttons += `<button type="button" class="btn btn-sm btn-warning pause-task" title="Mettre en pause"
                            data-task-id="${task.task_id}">
                      <i class="fas fa-pause"></i>
                    </button>`;
    }
    
    if (status === 'PAUSED') {
        buttons += `<button type="button" class="btn btn-sm btn-success resume-task" title="Reprendre"
                            data-task-id="${task.task_id}">
                      <i class="fas fa-play"></i>
                    </button>`;
    }
    
    if (status !== 'COMPLETED' && status !== 'CANCELLED' && status !== 'FAILED') {
        buttons += `<button type="button" class="btn btn-sm btn-danger cancel-task" title="Annuler"
                            data-task-id="${task.task_id}">
                      <i class="fas fa-times"></i>
                    </button>`;
    }
    
    return buttons;
}

/**
 * Extrait le nom de fichier à partir du chemin complet
 */
function getFileNameFromPath(path) {
    if (!path) return 'Inconnu';
    
    // Gérer les chemins Windows et Unix
    const parts = path.split(/[\\/]/);
    return parts[parts.length - 1];
}

/**
 * Affiche les détails d'une tâche
 */
function renderTaskDetails(task) {
    const detailsPane = document.getElementById('task-details-pane');
    if (!detailsPane) return;
    
    // Rendre les détails visibles
    detailsPane.classList.remove('d-none');
    
    // Mettre à jour le titre
    const detailsTitle = document.getElementById('task-details-title');
    if (detailsTitle) {
        detailsTitle.textContent = `Tâche: ${getFileNameFromPath(task.document_path)}`;
    }
    
    // Mettre à jour le contenu
    const detailsContent = document.getElementById('task-details-content');
    if (detailsContent) {
        const progressPercent = Math.round(task.progress * 100);
        
        // Construire le HTML des détails
        let detailsHtml = `
            <div class="card mb-3">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">Informations générales</h5>
                </div>
                <div class="card-body">
                    <dl class="row">
                        <dt class="col-sm-4">ID de la tâche</dt>
                        <dd class="col-sm-8">${task.task_id}</dd>
                        
                        <dt class="col-sm-4">Document</dt>
                        <dd class="col-sm-8">${task.document_path}</dd>
                        
                        <dt class="col-sm-4">Statut</dt>
                        <dd class="col-sm-8">
                            <span class="badge status-${task.status.toLowerCase()}">${task.status}</span>
                        </dd>
                        
                        <dt class="col-sm-4">Priorité</dt>
                        <dd class="col-sm-8">
                            <span class="badge priority-${task.priority.toLowerCase()}">${task.priority}</span>
                        </dd>
                        
                        <dt class="col-sm-4">Progression</dt>
                        <dd class="col-sm-8">
                            <div class="progress">
                                <div class="progress-bar" role="progressbar" style="width: ${progressPercent}%;"
                                     aria-valuenow="${progressPercent}" aria-valuemin="0" aria-valuemax="100">
                                    ${progressPercent}%
                                </div>
                            </div>
                        </dd>
                        
                        <dt class="col-sm-4">Ajoutée le</dt>
                        <dd class="col-sm-8">${formatDateTime(task.added_at)}</dd>
                        
                        ${task.started_at ? `
                            <dt class="col-sm-4">Démarrée le</dt>
                            <dd class="col-sm-8">${formatDateTime(task.started_at)}</dd>
                        ` : ''}
                        
                        ${task.completed_at ? `
                            <dt class="col-sm-4">Terminée le</dt>
                            <dd class="col-sm-8">${formatDateTime(task.completed_at)}</dd>
                        ` : ''}
                        
                        ${task.estimated_time_remaining ? `
                            <dt class="col-sm-4">Temps restant estimé</dt>
                            <dd class="col-sm-8">${formatTimeDuration(task.estimated_time_remaining)}</dd>
                        ` : ''}
                    </dl>
                </div>
            </div>
        `;
        
        // Ajouter les options OCR si présentes
        if (task.options && Object.keys(task.options).length > 0) {
            detailsHtml += `
                <div class="card mb-3">
                    <div class="card-header bg-info text-white">
                        <h5 class="mb-0">Options OCR</h5>
                    </div>
                    <div class="card-body">
                        <dl class="row">
                            ${Object.entries(task.options).map(([key, value]) => `
                                <dt class="col-sm-4">${key}</dt>
                                <dd class="col-sm-8">${value}</dd>
                            `).join('')}
                        </dl>
                    </div>
                </div>
            `;
        }
        
        // Ajouter les métadonnées si présentes
        if (task.metadata && Object.keys(task.metadata).length > 0) {
            detailsHtml += `
                <div class="card mb-3">
                    <div class="card-header bg-secondary text-white">
                        <h5 class="mb-0">Métadonnées</h5>
                    </div>
                    <div class="card-body">
                        <dl class="row">
                            ${Object.entries(task.metadata).map(([key, value]) => `
                                <dt class="col-sm-4">${key}</dt>
                                <dd class="col-sm-8">${typeof value === 'object' ? JSON.stringify(value) : value}</dd>
                            `).join('')}
                        </dl>
                    </div>
                </div>
            `;
        }
        
        // Ajouter le message d'erreur si présent
        if (task.error_message) {
            detailsHtml += `
                <div class="card mb-3 border-danger">
                    <div class="card-header bg-danger text-white">
                        <h5 class="mb-0">Erreur</h5>
                    </div>
                    <div class="card-body">
                        <pre class="error-message">${task.error_message}</pre>
                    </div>
                </div>
            `;
        }
        
        // Ajouter les boutons d'action
        detailsHtml += `
            <div class="card mb-3">
                <div class="card-header bg-dark text-white">
                    <h5 class="mb-0">Actions</h5>
                </div>
                <div class="card-body task-actions-container">
                    <div class="btn-group">
                        ${getDetailActionButtons(task)}
                    </div>
                </div>
            </div>
        `;
        
        detailsContent.innerHTML = detailsHtml;
        
        // Ajouter les écouteurs d'événements aux boutons
        attachActionButtonListeners(detailsContent, task.task_id);
    }
}

/**
 * Génère les boutons d'action pour la vue détaillée
 */
function getDetailActionButtons(task) {
    const status = task.status;
    let buttons = '';
    
    if (status === 'QUEUED' || status === 'RUNNING' || status === 'PREPROCESSING' || status === 'POSTPROCESSING') {
        buttons += `<button type="button" class="btn btn-warning pause-task" data-task-id="${task.task_id}">
                      <i class="fas fa-pause"></i> Mettre en pause
                    </button>`;
    }
    
    if (status === 'PAUSED') {
        buttons += `<button type="button" class="btn btn-success resume-task" data-task-id="${task.task_id}">
                      <i class="fas fa-play"></i> Reprendre
                    </button>`;
    }
    
    if (status !== 'COMPLETED' && status !== 'CANCELLED' && status !== 'FAILED') {
        buttons += `<button type="button" class="btn btn-danger cancel-task" data-task-id="${task.task_id}">
                      <i class="fas fa-times"></i> Annuler
                    </button>`;
    }
    
    if (status === 'COMPLETED' && task.output_path) {
        buttons += `<a href="/download?path=${encodeURIComponent(task.output_path)}" 
                       class="btn btn-primary" target="_blank">
                      <i class="fas fa-download"></i> Télécharger le résultat
                    </a>`;
    }
    
    return buttons;
}

/**
 * Attache les écouteurs d'événements aux boutons d'action
 */
function attachActionButtonListeners(container, taskId) {
    // Bouton pause
    container.querySelectorAll('.pause-task').forEach(button => {
        button.addEventListener('click', function() {
            pauseTask(taskId);
        });
    });
    
    // Bouton reprise
    container.querySelectorAll('.resume-task').forEach(button => {
        button.addEventListener('click', function() {
            resumeTask(taskId);
        });
    });
    
    // Bouton annulation
    container.querySelectorAll('.cancel-task').forEach(button => {
        button.addEventListener('click', function() {
            cancelTask(taskId);
        });
    });
}

/**
 * Initialise les contrôles des boutons d'action
 */
function initControlButtons() {
    // Délégation d'événement pour les boutons dans la liste des tâches
    const tasksTable = document.getElementById('tasks-table');
    if (tasksTable) {
        tasksTable.addEventListener('click', function(event) {
            const target = event.target.closest('button');
            if (!target) return;
            
            const taskId = target.dataset.taskId;
            if (!taskId) return;
            
            if (target.classList.contains('pause-task')) {
                pauseTask(taskId);
                event.stopPropagation(); // Éviter la sélection de la ligne
            } else if (target.classList.contains('resume-task')) {
                resumeTask(taskId);
                event.stopPropagation();
            } else if (target.classList.contains('cancel-task')) {
                cancelTask(taskId);
                event.stopPropagation();
            } else if (target.classList.contains('view-task')) {
                selectTask(taskId);
                // Pas besoin d'arrêter la propagation ici, car nous voulons sélectionner la ligne
            }
        });
    }
    
    // Bouton de fermeture des détails
    const closeDetailsButton = document.getElementById('close-details-button');
    if (closeDetailsButton) {
        closeDetailsButton.addEventListener('click', function() {
            const detailsPane = document.getElementById('task-details-pane');
            if (detailsPane) {
                detailsPane.classList.add('d-none');
            }
            selectedTaskId = null;
            
            // Désélectionner la ligne du tableau
            const tableBody = document.getElementById('tasks-table-body');
            if (tableBody) {
                tableBody.querySelectorAll('tr.selected').forEach(row => {
                    row.classList.remove('selected');
                });
            }
        });
    }
}

/**
 * Met en pause une tâche OCR
 */
function pauseTask(taskId) {
    fetch(`${API_BASE_URL}/tasks/${taskId}/pause`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Erreur lors de la mise en pause: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        showNotification('success', `Tâche ${taskId} mise en pause avec succès`);
        
        // Mettre à jour le cache et l'affichage
        const task = tasksCache.get(taskId);
        if (task) {
            task.status = 'PAUSED';
            updateTaskInList(taskId, task);
        }
    })
    .catch(error => {
        console.error(`Erreur lors de la mise en pause de la tâche ${taskId}:`, error);
        showNotification('error', `Erreur lors de la mise en pause de la tâche`);
    });
}

/**
 * Reprend une tâche OCR en pause
 */
function resumeTask(taskId) {
    fetch(`${API_BASE_URL}/tasks/${taskId}/resume`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Erreur lors de la reprise: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        showNotification('success', `Tâche ${taskId} reprise avec succès`);
        
        // Mettre à jour le cache et l'affichage
        const task = tasksCache.get(taskId);
        if (task) {
            task.status = 'QUEUED';
            updateTaskInList(taskId, task);
        }
    })
    .catch(error => {
        console.error(`Erreur lors de la reprise de la tâche ${taskId}:`, error);
        showNotification('error', `Erreur lors de la reprise de la tâche`);
    });
}

/**
 * Annule une tâche OCR
 */
function cancelTask(taskId) {
    // Demander confirmation
    if (!confirm('Êtes-vous sûr de vouloir annuler cette tâche OCR ? Cette action est irréversible.')) {
        return;
    }
    
    fetch(`${API_BASE_URL}/tasks/${taskId}/cancel`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Erreur lors de l'annulation: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        showNotification('success', `Tâche ${taskId} annulée avec succès`);
        
        // Mettre à jour le cache et l'affichage
        const task = tasksCache.get(taskId);
        if (task) {
            task.status = 'CANCELLED';
            updateTaskInList(taskId, task);
        }
    })
    .catch(error => {
        console.error(`Erreur lors de l'annulation de la tâche ${taskId}:`, error);
        showNotification('error', `Erreur lors de l'annulation de la tâche`);
    });
}

/**
 * Affiche une notification à l'utilisateur
 */
function showNotification(type, message) {
    const container = document.getElementById('notifications-container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.role = 'alert';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fermer"></button>
    `;
    
    container.appendChild(notification);
    
    // Supprimer automatiquement après 5 secondes
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 150);
    }, 5000);
}

/**
 * Initialise les filtres de tâches
 */
function initTaskFilters() {
    const filterButtons = document.querySelectorAll('.task-filter');
    if (!filterButtons.length) return;
    
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Mettre à jour le filtre actif
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Mettre à jour le filtre courant
            currentFilter = button.dataset.filter;
            
            // Rafraîchir l'affichage
            renderTasksList();
        });
    });
}

/**
 * Initialise le tri des tâches
 */
function initTaskSort() {
    const sortHeaders = document.querySelectorAll('th[data-sort]');
    if (!sortHeaders.length) return;
    
    sortHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const field = header.dataset.sort;
            
            // Inverser la direction si le même champ est cliqué à nouveau
            if (field === sortField) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortField = field;
                sortDirection = 'asc';
            }
            
            // Mettre à jour les indicateurs visuels
            sortHeaders.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            
            header.classList.add(`sort-${sortDirection}`);
            
            // Rafraîchir l'affichage
            renderTasksList();
        });
    });
}

/**
 * Initialise les statistiques
 */
function initStatistics() {
    // Rien à faire ici pour l'instant, les stats seront initialisées 
    // par le premier appel à refreshStatistics()
}

/**
 * Rafraîchit les statistiques via l'API
 */
function refreshStatistics() {
    fetch(`${API_BASE_URL}/stats`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erreur lors de la récupération des statistiques: ${response.status}`);
            }
            return response.json();
        })
        .then(stats => {
            statsCache = stats;
            updateStatistics(stats);
        })
        .catch(error => {
            console.error('Erreur lors du chargement des statistiques:', error);
        });
}

/**
 * Met à jour l'affichage des statistiques
 */
function updateStatistics(stats) {
    // Mettre à jour les compteurs
    updateStatCounter('active-tasks-count', stats.active_tasks);
    updateStatCounter('queued-tasks-count', stats.queue_length);
    updateStatCounter('completed-tasks-count', stats.completed_tasks);
    updateStatCounter('paused-tasks-count', stats.paused_tasks);
    
    // Mettre à jour les graphiques si Chart.js est disponible
    updateStatCharts(stats);
}

/**
 * Met à jour un compteur de statistiques
 */
function updateStatCounter(id, value) {
    const counter = document.getElementById(id);
    if (counter) {
        counter.textContent = value;
    }
}

/**
 * Met à jour les graphiques de statistiques
 */
function updateStatCharts(stats) {
    // Mettre à jour le graphique des statuts
    updateStatusChart(stats.status_counts);
    
    // Mettre à jour le graphique des priorités
    updatePriorityChart(stats.priority_counts);
}

/**
 * Met à jour le graphique de statuts
 */
function updateStatusChart(statusCounts) {
    if (typeof Chart === 'undefined') return;
    
    const canvas = document.getElementById('status-chart');
    if (!canvas) return;
    
    // Détruire le graphique existant s'il y en a un
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Créer un nouveau graphique
    const ctx = canvas.getContext('2d');
    canvas.chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(statusCounts),
            datasets: [{
                data: Object.values(statusCounts),
                backgroundColor: [
                    '#28a745', // COMPLETED
                    '#17a2b8', // RUNNING
                    '#ffc107', // QUEUED
                    '#dc3545', // FAILED
                    '#6c757d', // CANCELLED
                    '#fd7e14'  // PAUSED
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                position: 'right'
            }
        }
    });
}

/**
 * Met à jour le graphique de priorités
 */
function updatePriorityChart(priorityCounts) {
    if (typeof Chart === 'undefined') return;
    
    const canvas = document.getElementById('priority-chart');
    if (!canvas) return;
    
    // Détruire le graphique existant s'il y en a un
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Créer un nouveau graphique
    const ctx = canvas.getContext('2d');
    canvas.chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(priorityCounts),
            datasets: [{
                label: 'Nombre de tâches',
                data: Object.values(priorityCounts),
                backgroundColor: [
                    '#dc3545', // CRITICAL
                    '#fd7e14', // HIGH
                    '#ffc107', // NORMAL
                    '#28a745'  // LOW
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true,
                        precision: 0
                    }
                }]
            }
        }
    });
}

/**
 * Initialise le formulaire d'upload
 */
function initUploadForm() {
    const uploadForm = document.getElementById('ocr-upload-form');
    if (!uploadForm) return;
    
    uploadForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const formData = new FormData(uploadForm);
        
        // Désactiver le bouton pendant l'upload
        const submitButton = uploadForm.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Envoi en cours...';
        }
        
        fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erreur lors de l'upload: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            showNotification('success', `Document ajouté à la file d'attente OCR avec succès`);
            
            // Réinitialiser le formulaire
            uploadForm.reset();
            
            // Rafraîchir la liste des tâches
            refreshTasksList();
        })
        .catch(error => {
            console.error('Erreur lors de l\'upload:', error);
            showNotification('error', `Erreur lors de l'ajout du document à la file d'attente OCR: ${error.message}`);
        })
        .finally(() => {
            // Réactiver le bouton
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = '<i class="fas fa-upload"></i> Envoyer pour OCR';
            }
        });
    });
}
