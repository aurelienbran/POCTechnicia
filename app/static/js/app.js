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

    // Vérifier l'état du système et des documents indexés au démarrage
    checkSystemStatus();

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
    pdfFile.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        if (file.type !== 'application/pdf') {
            showError('Veuillez sélectionner un fichier PDF');
            return;
        }

        if (file.size > 157286400) { // 150 MB
            showError('Le fichier ne doit pas dépasser 150 MB');
            return;
        }

        // Afficher le modal et la progression
        uploadModal.classList.remove('hidden');
        uploadProgress.classList.remove('hidden');
        
        // Afficher les informations du document
        documentName.textContent = `Fichier : ${file.name}`;
        documentSize.textContent = `Taille : ${formatFileSize(file.size)}`;
        uploadStatus.textContent = 'Envoi du fichier...';
        
        const formData = new FormData(uploadForm);

        try {
            const response = await fetch('/api/v1/documents', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Erreur lors de l\'upload');
            }

            // Commencer le polling du statut
            checkIndexingStatus();
            
        } catch (error) {
            showError(error.message);
            uploadStatus.textContent = 'Erreur : ' + error.message;
            setTimeout(() => {
                uploadModal.classList.add('hidden');
                uploadProgress.classList.add('hidden');
            }, 3000);
        }
    });

    async function checkIndexingStatus() {
        try {
            const response = await fetch('/api/v1/indexing-status');
            const status = await response.json();
            
            if (status.in_progress) {
                // Mettre à jour le modal
                uploadStatus.textContent = `Traitement en cours : ${status.processed_files}/${status.total_files} fichiers`;
                if (status.total_chunks) {
                    documentPages.textContent = `Pages traitées : ${status.total_chunks}`;
                }
                
                // Mettre à jour le badge dans la sidebar
                indexingStatus.classList.remove('hidden');
                indexingStatus.querySelector('div').textContent = `${Math.round((status.processed_files / status.total_files) * 100)}%`;
                
                // Continuer le polling
                setTimeout(checkIndexingStatus, 1000);
            } else {
                if (status.error) {
                    uploadStatus.textContent = `Erreur : ${status.error}`;
                    setTimeout(() => {
                        uploadModal.classList.add('hidden');
                        uploadProgress.classList.add('hidden');
                        indexingStatus.classList.add('hidden');
                    }, 3000);
                } else {
                    uploadStatus.textContent = 'Traitement terminé avec succès';
                    setTimeout(() => {
                        uploadModal.classList.add('hidden');
                        uploadProgress.classList.add('hidden');
                        indexingStatus.classList.add('hidden');
                    }, 2000);
                    
                    // Rafraîchir les stats
                    const statsResponse = await fetch('/api/v1/stats');
                    if (statsResponse.ok) {
                        const stats = await statsResponse.json();
                        addMessage('system', `Document traité avec succès. ${stats.points_count} passages sont maintenant indexés.`);
                    }
                }
            }
        } catch (error) {
            console.error('Erreur lors de la vérification du statut:', error);
        }
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
        
        try {
            const response = await fetch('/api/v1/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    k: 4
                })
            });
            
            if (!response.ok) {
                throw new Error('Erreur lors du traitement de la requête');
            }
            
            const result = await response.json();
            
            // Afficher la réponse
            addMessage('assistant', result.answer);
            
            // Afficher les sources si disponibles
            if (result.sources && result.sources.length > 0) {
                const sourcesHtml = `
                    <div class="mt-2 text-sm text-gray-600">
                        <p class="font-semibold">Sources :</p>
                        <ul class="list-disc list-inside">
                            ${result.sources.map(s => `<li>${s.file} (pertinence: ${Math.round(s.score * 100)}%)</li>`).join('')}
                        </ul>
                    </div>
                `;
                addMessage('system', sourcesHtml);
            }
            
        } catch (error) {
            console.error('Erreur:', error);
            addMessage('system', 'Une erreur est survenue lors du traitement de votre requête.');
        } finally {
            // Réactiver l'input
            queryInput.disabled = false;
            sendButton.disabled = false;
            queryInput.value = '';
            queryInput.focus();
        }
    });

    function addMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `p-4 rounded-lg ${type === 'user' ? 'bg-blue-50 ml-12' : type === 'assistant' ? 'bg-white shadow-sm mr-12' : 'bg-gray-50 text-sm'}`;
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
            uploadModal.classList.add('hidden');
        }
    });
});
