import React, { useState, useEffect } from 'react';
import { X, AlertTriangle, Check, RefreshCw, FileText, Layers, Search, Clock } from 'lucide-react';
import LogViewer from './LogViewer';

interface UploadProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  status: {
    in_progress: boolean;
    files_progress: number;
    chunks_progress: number;
    current_file?: string;
    error_occurred?: boolean;
    error_message?: string;
    current_step?: string;
    ocr_in_progress?: boolean;
    ocr_progress?: number;
    ocr_current_page?: number;
    ocr_total_pages?: number;
    ocr_logs?: string[];
    [key: string]: any;
  };
  onRefresh?: () => void; // Optional callback for manual refresh
}

/**
 * Composant modal qui affiche la progression d'un upload et du traitement d'un document,
 * y compris les détails spécifiques à l'OCR et les logs en temps réel.
 */
const UploadProgressModal: React.FC<UploadProgressModalProps> = ({ 
  isOpen, 
  onClose, 
  status,
  onRefresh
}) => {
  const [showLogs, setShowLogs] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());
  
  // Update the last update timestamp whenever status changes
  useEffect(() => {
    setLastUpdateTime(new Date());
  }, [status]);
  
  // Empêcher la fermeture si le traitement est en cours
  const handleClose = () => {
    if (!status.in_progress) {
      onClose();
    }
  };
  
  // Fonction pour déterminer l'étape actuelle du traitement
  const getStepStatus = (step: string) => {
    if (!status.current_step) return 'pending';
    
    const steps = ['uploading', 'analyzing', 'ocr', 'indexing', 'completed', 'error'];
    const currentIndex = steps.indexOf(status.current_step);
    const stepIndex = steps.indexOf(step);
    
    if (status.current_step === 'error') {
      return step === 'error' ? 'current' : 'pending';
    }
    
    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return 'current';
    return 'pending';
  };
  
  // Icône et couleur pour chaque étape
  const getStepIcon = (step: string) => {
    const status = getStepStatus(step);
    
    const icons = {
      uploading: <FileText size={18} />,
      analyzing: <Search size={18} />,
      ocr: <Layers size={18} />,
      indexing: <Layers size={18} />,
      completed: <Check size={18} />,
      error: <AlertTriangle size={18} />
    };
    
    const colors = {
      completed: 'text-green-500 bg-green-100 border-green-200',
      current: 'text-blue-500 bg-blue-100 border-blue-200',
      pending: 'text-gray-400 bg-gray-100 border-gray-200'
    };
    
    const icon = icons[step as keyof typeof icons] || <RefreshCw size={18} />;
    const colorClass = colors[status as keyof typeof colors];
    
    return (
      <div className={`rounded-full p-2 border ${colorClass}`}>
        {status === 'current' && step !== 'completed' && step !== 'error' ? (
          <div className="animate-spin">{icon}</div>
        ) : icon}
      </div>
    );
  };
  
  // Texte pour chaque étape
  const getStepText = (step: string) => {
    const texts = {
      uploading: "Téléchargement",
      analyzing: "Analyse du document",
      ocr: "Reconnaissance de texte (OCR)",
      indexing: "Indexation vectorielle",
      completed: "Traitement terminé",
      error: "Erreur de traitement"
    };
    
    return texts[step as keyof typeof texts] || step;
  };
  
  // Calcul de la progression globale
  const getOverallProgress = () => {
    if (status.error_occurred) return 100;
    if (!status.in_progress && status.files_progress === 100 && status.chunks_progress === 100) return 100;
    
    let progress = 0;
    
    // Pondération des étapes
    if (status.current_step === 'uploading') {
      progress = 10;
    } else if (status.current_step === 'analyzing') {
      progress = 20;
    } else if (status.current_step === 'ocr') {
      // OCR compte pour 40% de la progression totale
      progress = 20 + (status.ocr_progress || 0) * 0.4;
    } else if (status.current_step === 'indexing') {
      // L'indexation compte pour 40% de la progression totale
      progress = 60 + (status.chunks_progress || 0) * 0.4;
    } else if (status.current_step === 'completed') {
      progress = 100;
    }
    
    return Math.min(Math.round(progress), 100);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-semibold text-gray-800">
            Traitement du document
          </h2>
          <button 
            onClick={handleClose}
            className={`rounded-full p-1 ${status.in_progress ? 'text-gray-400 cursor-not-allowed' : 'text-gray-600 hover:bg-gray-100'}`}
            disabled={status.in_progress}
          >
            <X size={20} />
          </button>
        </div>
        
        <div className="p-6">
          {/* Current file and status summary */}
          <div className="mb-6 bg-gray-50 p-3 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-800">
                Fichier actuel
              </h3>
              <span className={`text-xs px-2 py-1 rounded-full ${
                status.current_step === 'uploading' ? 'bg-blue-100 text-blue-700' : 
                status.current_step === 'ocr' ? 'bg-purple-100 text-purple-700' : 
                status.current_step === 'indexing' ? 'bg-indigo-100 text-indigo-700' : 
                status.error_occurred ? 'bg-red-100 text-red-700' : 
                status.current_step === 'completed' ? 'bg-green-100 text-green-700' : 
                'bg-gray-100 text-gray-700'
              }`}>
                {status.current_step === 'uploading' ? 'Téléchargement' : 
                 status.current_step === 'ocr' ? 'OCR en cours' : 
                 status.current_step === 'indexing' ? 'Indexation' : 
                 status.error_occurred ? 'Erreur' : 
                 status.current_step === 'completed' ? 'Terminé' : 
                 status.in_progress ? 'En cours' : 'En attente'}
              </span>
            </div>
            <p className="text-sm text-gray-600 truncate font-mono bg-white p-1 rounded border border-gray-200">
              {status.current_file || 'Aucun fichier sélectionné'}
            </p>

            {status.current_step === 'indexing' && (
              <div className="mt-2 text-xs text-gray-500">
                <span className="font-semibold">Progrès de l'indexation: </span>
                {status.indexed_chunks || 0}/{status.total_chunks || 0} fragments traités
              </div>
            )}

            {status.ocr_in_progress && (
              <div className="mt-2 text-xs text-gray-500">
                <span className="font-semibold">Progrès OCR: </span>
                Page {status.ocr_current_page || 0}/{status.ocr_total_pages || 0}
              </div>
            )}
          </div>

          {/* Barre de progression globale */}
          <div className="mb-6">
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">
                Progression globale
              </span>
              <span className="text-sm font-medium text-gray-700">
                {getOverallProgress()}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div 
                className={`h-2.5 rounded-full ${status.error_occurred ? 'bg-red-500' : 
                  status.current_step === 'completed' ? 'bg-green-500' : 'bg-blue-500'}`}
                style={{ width: `${getOverallProgress()}%` }}
              ></div>
            </div>
            
            {/* Last update time and refresh button */}
            <div className="flex items-center mt-2 text-xs text-gray-500 justify-end">
              <Clock size={12} className="mr-1" />
              <span>Dernière mise à jour: {lastUpdateTime.toLocaleTimeString()}</span>
              
              {onRefresh && (
                <button 
                  className="ml-3 flex items-center text-blue-500 hover:text-blue-700"
                  onClick={() => {
                    onRefresh();
                    setLastUpdateTime(new Date());
                  }}
                  title="Rafraîchir le statut manuellement"
                >
                  <RefreshCw size={12} className="mr-1" />
                  Rafraîchir
                </button>
              )}
            </div>
          </div>
          
          {/* Étapes du traitement */}
          <div className="mb-6 space-y-4">
            {['uploading', 'analyzing', 'ocr', 'indexing', 'completed', status.error_occurred ? 'error' : null]
              .filter(Boolean)
              .map((step, index) => (
                <div key={index} className="flex items-center">
                  {getStepIcon(step!)}
                  <div className="ml-3 flex-1">
                    <h3 className={`text-sm font-medium ${
                      getStepStatus(step!) === 'current' ? 'text-blue-700' :
                      getStepStatus(step!) === 'completed' ? 'text-green-700' : 'text-gray-500'
                    }`}>
                      {getStepText(step!)}
                    </h3>
                    
                    {/* Informations supplémentaires par étape */}
                    {step === 'uploading' && status.current_file && (
                      <p className="text-xs text-gray-500">Fichier: {status.current_file}</p>
                    )}
                    
                    {step === 'ocr' && status.ocr_in_progress && (
                      <div className="mt-1">
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>Page {status.ocr_current_page || 0}/{status.ocr_total_pages || 0}</span>
                          <span>{status.ocr_progress || 0}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div 
                            className="h-1.5 rounded-full bg-indigo-500"
                            style={{ width: `${status.ocr_progress || 0}%` }}
                          ></div>
                        </div>
                      </div>
                    )}
                    
                    {step === 'indexing' && (
                      <p className="text-xs text-gray-500">
                        {status.indexed_chunks || 0}/{status.total_chunks || 0} passages indexés
                      </p>
                    )}
                    
                    {step === 'error' && status.error_message && (
                      <p className="text-xs text-red-500">{status.error_message}</p>
                    )}
                  </div>
                </div>
              ))}
          </div>
          
          {/* Affichage des logs */}
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <button 
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
                onClick={() => setShowLogs(!showLogs)}
              >
                {showLogs ? 'Masquer les logs' : 'Afficher les logs détaillés'}
              </button>
              
              <span className="text-xs text-gray-500">
                {status.ocr_logs?.length || 0} entrées de log
              </span>
            </div>
            
            {/* Latest log entry summary */}
            {!showLogs && status.ocr_logs && status.ocr_logs.length > 0 && (
              <div className="bg-gray-50 border border-gray-200 rounded-md p-2 mb-2">
                <p className="text-xs font-mono text-gray-600 truncate">
                  {status.ocr_logs[status.ocr_logs.length - 1]}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Cliquez sur "Afficher les logs détaillés" pour voir tous les logs
                </p>
              </div>
            )}
            
            {showLogs && status.ocr_logs && status.ocr_logs.length > 0 && (
              <div className="mt-3">
                <LogViewer 
                  logs={status.ocr_logs.slice(-50)} // Show only the last 50 logs to prevent overwhelming
                  maxHeight="200px" 
                  title={`Logs OCR (${Math.min(status.ocr_logs.length, 50)} dernières entrées sur ${status.ocr_logs.length})`}
                />
              </div>
            )}
          </div>
        </div>
        
        <div className="bg-gray-50 px-6 py-3 flex justify-end border-t">
          <button
            onClick={handleClose}
            disabled={status.in_progress}
            className={`px-4 py-2 rounded-md ${
              status.in_progress 
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {status.in_progress ? 'Traitement en cours...' : 'Fermer'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UploadProgressModal;
