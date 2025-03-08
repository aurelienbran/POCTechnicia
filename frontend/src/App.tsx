import React, { useState, useRef, useEffect } from 'react';
import { PlusCircle, Send, Copy, Loader2, FileText, Home, BarChart2, AlertCircle } from 'lucide-react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import UploadProgressModal from './components/UploadProgressModal';
import LogViewer from './components/LogViewer';

// Types
interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  sources?: Source[];
  followUpQuestions?: string[];
  timestamp: Date;
}

interface Source {
  file: string;
  score: number;
}

interface IndexingStatus {
  status: 'idle' | 'processing' | 'completed' | 'error';
  progress: number;
  currentFile?: string;
  message?: string;
  ocrInProgress?: boolean;
  ocrProgress?: number;
  ocrCurrentPage?: number;
  ocrTotalPages?: number;
  ocrLogs?: string[];
}

// Mock API for development (forcé à false pour utiliser l'API réelle)
const useMockApi = false; // import.meta.env.DEV;

const mockStats = {
  indexed_documents: 3,
  total_pages: 42,
  vector_chunks: 156
};

const mockResponses = {
  query: {
    answer: "Voici une réponse générée par le système. Dans un environnement de production, cette réponse proviendrait du modèle Claude 3.5 Sonnet.\n\n## Fonctionnement\n\nLe système utilise une architecture RAG (Retrieval Augmented Generation) pour:\n1. Rechercher les informations pertinentes dans les documents indexés\n2. Générer une réponse contextuelle basée sur ces informations\n\nCela permet d'obtenir des réponses précises et à jour.",
    sources: [
      { file: "manuel_technique.pdf", score: 0.95 },
      { file: "schemas_hydrauliques.pdf", score: 0.87 }
    ],
    follow_up_questions: [
      "Comment ajouter un nouveau document?",
      "Quelle est la taille maximale supportée?",
      "Comment fonctionne l'indexation vectorielle?"
    ]
  }
};

function App() {
  // State
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'system',
      content: 'Bienvenue sur CFF AI Assistant! Téléchargez un document PDF ou posez une question.',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [indexingStatus, setIndexingStatus] = useState<IndexingStatus>({
    status: 'idle',
    progress: 0,
    ocrLogs: []
  });
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<any>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const mainWsRef = useRef<WebSocket | null>(null);
  const ocrWsRef = useRef<WebSocket | null>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Check indexing status periodically
  useEffect(() => {
    if (indexingStatus.status === 'processing') {
      const interval = setInterval(checkIndexingStatus, 2000);
      return () => clearInterval(interval);
    }
  }, [indexingStatus.status]);

  // Fetch initial stats
  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      if (useMockApi) {
        // Use mock data in development
        setStats(mockStats);
        return;
      }
      
      const response = await fetch('/api/v1/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
      if (useMockApi) {
        // Use mock data if API fails
        setStats(mockStats);
      }
    }
  };

  // Create a function to throttle status checks based on process stage
  const getStatusCheckDelay = (currentStatus: string, progress: number) => {
    // If we're in OCR or almost done with the process, check less frequently
    if (currentStatus === 'ocr') {
      return 5000; // 5 seconds
    } else if (currentStatus === 'indexing' && progress > 80) {
      return 4000; // 4 seconds
    } else if (currentStatus === 'indexing' && progress > 50) {
      return 3000; // 3 seconds
    }
    return 2000; // Default: 2 seconds
  };

  const checkIndexingStatus = async () => {
    try {
      if (useMockApi) {
        // Simulate indexing progress in development
        setIndexingStatus(prev => {
          const newProgress = Math.min(prev.progress + 10, 100);
          
          // Simuler des logs OCR pour le développement
          const ocrLogs = prev.ocrLogs || [];
          if (newProgress > 30 && newProgress < 70) {
            ocrLogs.push(`[${new Date().toISOString()}] OCR en cours - page ${Math.floor((newProgress - 30) / 4)} sur 10`);
          }
          
          if (newProgress === 100) {
            fetchStats();
            addSystemMessage('Document indexé avec succès!');
            return {
              status: 'completed',
              progress: 100,
              ocrLogs
            };
          }
          
          return {
            ...prev,
            progress: newProgress,
            ocrLogs,
            ocrInProgress: newProgress > 30 && newProgress < 70,
            ocrProgress: newProgress > 30 && newProgress < 70 ? Math.floor((newProgress - 30) * 2.5) : 0,
            ocrCurrentPage: Math.floor((newProgress - 30) / 4),
            ocrTotalPages: 10
          };
        });
        return;
      }
      
      const response = await fetch('/api/v1/indexing-status');
      if (response.ok) {
        const data = await response.json();
        console.log('Indexing status response:', data);
        
        // Adapter les propriétés du serveur à notre format interne
        let status = 'idle';
        let progress = 0;
        
        // Valeurs par défaut pour OCR
        let ocrInProgress = data.ocr_in_progress || false;
        let ocrProgress = data.ocr_progress || 0;
        let ocrCurrentPage = data.ocr_current_page || 0;
        let ocrTotalPages = data.ocr_total_pages || 0;
        let ocrLogs = data.ocr_logs || indexingStatus.ocrLogs || [];
        
        // Ajouter les nouveaux logs s'ils existent
        if (data.ocr_logs && Array.isArray(data.ocr_logs) && data.ocr_logs.length > 0) {
          // Filtrer pour n'ajouter que les nouveaux logs
          const existingLogs = new Set(indexingStatus.ocrLogs || []);
          const newLogs = data.ocr_logs.filter((log: string) => !existingLogs.has(log));
          
          if (newLogs.length > 0) {
            ocrLogs = [...(indexingStatus.ocrLogs || []), ...newLogs];
          }
        }
        
        if (data.in_progress) {
          status = 'processing';
          
          // Calculer la progression globale
          if (data.total_chunks && data.total_chunks > 0) {
            progress = Math.round((data.indexed_chunks / data.total_chunks) * 100);
          }
          
          // Déterminer l'étape actuelle (OCR ou indexation)
          let currentStep = 'indexing';
          if (ocrInProgress) {
            currentStep = 'ocr';
            // Si OCR en cours, ajuster la progression globale
            progress = Math.min(60 + (ocrProgress * 0.4), 100);
          }
          
          // Continuer à vérifier le statut avec une fréquence adaptative
          const delay = getStatusCheckDelay(currentStep, progress);
          setTimeout(checkIndexingStatus, delay);
        } else if (data.error || data.error_occurred) {
          status = 'error';
          addSystemMessage(`Erreur d'indexation: ${data.error || data.error_message || 'Une erreur inconnue est survenue'}`);
          // Keep modal open to show the error - user can close it manually
        } else {
          status = 'completed';
          progress = 100;
          fetchStats();
          addSystemMessage('Document indexé avec succès!');
          // Keep modal open to show completion - user can close it manually
        }
        
        setIndexingStatus({
          status,
          progress,
          currentFile: data.current_file,
          ocrInProgress,
          ocrProgress,
          ocrCurrentPage,
          ocrTotalPages,
          ocrLogs
        });
      }
    } catch (error) {
      console.error('Error checking indexing status:', error);
      // En cas d'erreur, arrêter la vérification et afficher un message
      // Keep modal open but update status to error
      setIndexingStatus(prev => ({
        ...prev,
        status: 'error',
        message: "Erreur lors de la vérification du statut d'indexation."
      }));
      addSystemMessage("Erreur lors de la vérification du statut d'indexation.");
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    // For now, just use the first file to maintain compatibility with existing code
    // In a full implementation, we would process each file according to the queue design
    const file = files[0];
    
    // Validate file type
    if (file.type !== 'application/pdf') {
      setError('Seuls les fichiers PDF sont acceptés.');
      setTimeout(() => setError(null), 3000);
      return;
    }
    
    // Validate file size (150MB max)
    if (file.size > 150 * 1024 * 1024) {
      setError('La taille du fichier ne doit pas dépasser 150 MB.');
      setTimeout(() => setError(null), 3000);
      return;
    }
    
    // Show upload progress for multiple files
    const totalFiles = files.length;
    if (totalFiles > 1) {
      addSystemMessage(`${totalFiles} fichiers sélectionnés. Traitement du premier fichier: ${file.name}`);
    }
    
    setShowUploadModal(true);
    setUploadProgress(0);
    
    if (useMockApi) {
      // Simulate file upload in development
      const simulateUpload = () => {
        let progress = 0;
        const interval = setInterval(() => {
          progress += 5;
          setUploadProgress(progress);
          
          if (progress >= 100) {
            clearInterval(interval);
            setIndexingStatus({
              status: 'processing',
              progress: 0,
              currentFile: file.name
            });
            
            addSystemMessage(`Indexation de ${file.name} en cours...`);
          }
        }, 200);
      };
      
      simulateUpload();
      return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      });
      
      xhr.addEventListener('load', async () => {
        // Log the response for debugging
        console.log('Upload response:', xhr.status, xhr.responseText);
        
        if (xhr.status === 200 || xhr.status === 202) {
          setIndexingStatus({
            status: 'processing',
            progress: 0,
            currentFile: file.name
          });
          
          addSystemMessage(`Indexation de ${file.name} en cours...`);
          
          // Start checking indexing status
          await checkIndexingStatus();
        } else {
          let errorMsg = 'Erreur lors du téléchargement du fichier.';
          try {
            // Tenter de parser la réponse JSON pour obtenir le message d'erreur
            const response = JSON.parse(xhr.responseText);
            if (response && response.detail) {
              errorMsg = response.detail;
            }
          } catch (e) {
            console.error('Erreur de parsing JSON:', e);
          }
          
          setError(errorMsg);
          setShowUploadModal(false);
        }
      });
      
      xhr.addEventListener('error', () => {
        console.error('XHR error event triggered');
        setError('Erreur lors du téléchargement du fichier.');
        setShowUploadModal(false);
      });
      
      xhr.open('POST', '/api/v1/documents');
      xhr.send(formData);
    } catch (error) {
      console.error('Error uploading file:', error);
      setError('Erreur lors du téléchargement du fichier.');
      setShowUploadModal(false);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    
    try {
      if (useMockApi) {
        // Simulate API response delay in development
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        const assistantMessage: Message = {
          id: Date.now().toString(),
          type: 'assistant',
          content: mockResponses.query.answer,
          sources: mockResponses.query.sources,
          followUpQuestions: mockResponses.query.follow_up_questions,
          timestamp: new Date()
        };
        
        setMessages(prev => [...prev, assistantMessage]);
        setIsLoading(false);
        return;
      }
      
      const response = await fetch('/api/v1/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: inputValue,
          k: 4
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        const assistantMessage: Message = {
          id: Date.now().toString(),
          type: 'assistant',
          content: data.answer,
          sources: data.sources,
          followUpQuestions: data.follow_up_questions,
          timestamp: new Date()
        };
        
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        addSystemMessage('Erreur lors de la récupération de la réponse.');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      addSystemMessage('Erreur de connexion au serveur.');
    } finally {
      setIsLoading(false);
    }
  };

  const addSystemMessage = (content: string) => {
    const systemMessage: Message = {
      id: Date.now().toString(),
      type: 'system',
      content,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, systemMessage]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // Show a temporary notification
    setError('Copié dans le presse-papier!');
    setTimeout(() => setError(null), 2000);
  };

  const toggleStats = () => {
    if (stats) {
      setStats(null);
    } else {
      fetchStats();
    }
  };

  const renderMessageContent = (message: Message) => {
    if (message.type === 'assistant') {
      const sanitizedHtml = DOMPurify.sanitize(marked.parse(message.content));
      
      return (
        <div className="flex flex-col space-y-2 w-full">
          <div 
            className="prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
          />
          
          {message.sources && message.sources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-500 mb-2">Sources:</h4>
              <ul className="text-xs text-gray-600 space-y-1">
                {message.sources.map((source, index) => (
                  <li key={index} className="flex items-center">
                    <FileText size={12} className="mr-1 text-red-500" />
                    <span>{source.file}</span>
                    <span className="ml-2 text-gray-400">(Score: {(source.score * 100).toFixed(1)}%)</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {message.followUpQuestions && message.followUpQuestions.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-500 mb-2">Questions suggérées:</h4>
              <ul className="text-xs text-red-600 space-y-1">
                {message.followUpQuestions.map((question, index) => (
                  <li 
                    key={index} 
                    className="cursor-pointer hover:underline"
                    onClick={() => {
                      setInputValue(question);
                      if (chatContainerRef.current) {
                        chatContainerRef.current.querySelector('textarea')?.focus();
                      }
                    }}
                  >
                    {question}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          <button 
            className="self-end text-gray-400 hover:text-gray-600 flex items-center text-xs mt-2"
            onClick={() => copyToClipboard(message.content)}
          >
            <Copy size={12} className="mr-1" />
            Copier
          </button>
        </div>
      );
    }
    
    return <p>{message.content}</p>;
  };

  useEffect(() => {
    connectMainWebSocket();
    connectOcrWebSocket();
    fetchStats();
    
    return () => {
      if (mainWsRef.current) {
        mainWsRef.current.close();
      }
      if (ocrWsRef.current) {
        ocrWsRef.current.close();
      }
    };
  }, []);

  const connectMainWebSocket = () => {
    if (useMockApi) return;
    
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ws`;
    console.log('Connecting to main WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('Main WebSocket connection established');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Main WebSocket message received:', data);
      
      if (data.type === 'indexing_update') {
        updateIndexingStatus(data);
      } else if (data.type === 'follow_up_questions') {
        updateFollowUpQuestions(data.questions);
      }
    };
    
    ws.onclose = () => {
      console.log('Main WebSocket connection closed, attempting to reconnect...');
      setTimeout(connectMainWebSocket, 2000);
    };
    
    ws.onerror = (error) => {
      console.error('Main WebSocket error:', error);
    };
    
    mainWsRef.current = ws;
  };

  const connectOcrWebSocket = () => {
    if (useMockApi) return;
    
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ocr-ws`;
    console.log('Connecting to OCR WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('OCR WebSocket connection established');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('OCR WebSocket message received:', data);
      
      if (data.type === 'ocr_progress' || data.type === 'ocr_log') {
        setIndexingStatus(prev => {
          const newLogs = [...(prev.ocrLogs || [])];
          if (data.message && !newLogs.includes(data.message)) {
            newLogs.push(data.message);
          }
          
          return {
            ...prev,
            ocrInProgress: true,
            ocrProgress: data.progress !== undefined ? data.progress : prev.ocrProgress,
            ocrCurrentPage: data.current_page !== undefined ? data.current_page : prev.ocrCurrentPage,
            ocrTotalPages: data.total_pages !== undefined ? data.total_pages : prev.ocrTotalPages,
            ocrLogs: newLogs
          };
        });
      } else if (data.type === 'history') {
        if (data.messages && Array.isArray(data.messages)) {
          setIndexingStatus(prev => {
            const existingLogs = new Set(prev.ocrLogs || []);
            const newLogs = data.messages
              .filter((msg: { message: string }) => msg.message && !existingLogs.has(msg.message))
              .map((msg: { message: string }) => msg.message);
              
            if (newLogs.length === 0) return prev;
            
            return {
              ...prev,
              ocrLogs: [...(prev.ocrLogs || []), ...newLogs]
            };
          });
        }
      }
    };
    
    ws.onclose = () => {
      console.log('OCR WebSocket connection closed, attempting to reconnect...');
      setTimeout(connectOcrWebSocket, 2000);
    };
    
    ws.onerror = (error) => {
      console.error('OCR WebSocket error:', error);
    };
    
    ocrWsRef.current = ws;
  };

  /**
   * Mise à jour du statut d'indexation en fonction des données reçues via WebSocket
   * @param data Données de mise à jour reçues du WebSocket
   */
  const updateIndexingStatus = (data: any) => {
    console.log('Updating indexing status from WebSocket:', data);
    
    if (!data) return;
    
    let status = indexingStatus.status;
    let progress = indexingStatus.progress;
    let ocrInProgress = data.ocr_in_progress || indexingStatus.ocrInProgress || false;
    let ocrProgress = data.ocr_progress || indexingStatus.ocrProgress || 0;
    let ocrCurrentPage = data.ocr_current_page || indexingStatus.ocrCurrentPage || 0;
    let ocrTotalPages = data.ocr_total_pages || indexingStatus.ocrTotalPages || 0;
    let ocrLogs = indexingStatus.ocrLogs || [];
    
    // Ajouter les nouveaux logs s'ils existent
    if (data.ocr_logs && Array.isArray(data.ocr_logs) && data.ocr_logs.length > 0) {
      const existingLogs = new Set(ocrLogs);
      const newLogs = data.ocr_logs.filter((log: string) => !existingLogs.has(log));
      
      if (newLogs.length > 0) {
        ocrLogs = [...ocrLogs, ...newLogs];
      }
    }
    
    if (data.in_progress) {
      status = 'processing';
      
      // Calculer la progression
      if (data.total_chunks && data.total_chunks > 0) {
        progress = Math.round((data.indexed_chunks / data.total_chunks) * 100);
      }
      
      // Si OCR en cours, ajuster la progression
      if (ocrInProgress) {
        progress = Math.min(60 + (ocrProgress * 0.4), 100);
      }
    } else if (data.error || data.error_occurred) {
      status = 'error';
      addSystemMessage(`Erreur d'indexation: ${data.error_message || data.error || 'Une erreur inconnue est survenue'}`);
      // Keep modal open to show the error
    } else if (data.completed) {
      status = 'completed';
      progress = 100;
      fetchStats();
      addSystemMessage('Document indexé avec succès!');
      // Keep modal open to show completion
    }
    
    setIndexingStatus({
      status,
      progress,
      currentFile: data.current_file || indexingStatus.currentFile,
      ocrInProgress,
      ocrProgress,
      ocrCurrentPage,
      ocrTotalPages,
      ocrLogs
    });
  };
  
  /**
   * Mise à jour des questions de suivi à partir des données WebSocket
   * @param questions Tableau de questions de suivi
   */
  const updateFollowUpQuestions = (questions: string[]) => {
    if (!questions || !Array.isArray(questions) || questions.length === 0) return;
    
    console.log('Received follow-up questions:', questions);
    
    // Mettre à jour le dernier message assistant avec les nouvelles questions
    setMessages(prevMessages => {
      const newMessages = [...prevMessages];
      const lastAssistantMessageIndex = newMessages
        .map((msg, i) => ({ type: msg.type, index: i }))
        .filter(item => item.type === 'assistant')
        .pop()?.index;
      
      if (lastAssistantMessageIndex !== undefined) {
        newMessages[lastAssistantMessageIndex] = {
          ...newMessages[lastAssistantMessageIndex],
          followUpQuestions: questions
        };
      }
      
      return newMessages;
    });
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-[70px] bg-white border-r border-gray-200 flex flex-col items-center py-6">
        <div className="flex flex-col items-center space-y-6">
          <div className="w-10 h-10 flex items-center justify-center">
            <img src="/cff-logo.svg" alt="CFF Logo" className="w-full h-full" />
          </div>
          
          <button 
            className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 hover:bg-gray-200 transition-colors"
            onClick={() => {
              setMessages([{
                id: '1',
                type: 'system',
                content: 'Bienvenue sur CFF AI Assistant! Téléchargez un document PDF ou posez une question.',
                timestamp: new Date()
              }]);
            }}
          >
            <Home size={20} />
          </button>
          
          <button 
            className={`w-10 h-10 rounded-full ${stats ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600'} flex items-center justify-center hover:bg-gray-200 transition-colors`}
            onClick={toggleStats}
          >
            <BarChart2 size={20} />
          </button>
          
          <button 
            className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center text-red-600 hover:bg-red-200 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <PlusCircle size={20} />
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              accept=".pdf"
              multiple 
              onChange={handleFileUpload} 
            />
          </button>
        </div>
      </div>
      
      {/* Main content */}
      <div className="flex-1 flex flex-col" ref={chatContainerRef}>
        {/* Header */}
        <div className="bg-white border-b border-gray-200 py-3 px-4">
          <div className="max-w-4xl mx-auto flex items-center">
            <img src="/cff-logo.svg" alt="CFF Logo" className="h-6 mr-3" />
            <h1 className="text-lg font-semibold text-gray-800">CFF AI Assistant</h1>
          </div>
        </div>
        
        {/* Messages container */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.map((message) => (
              <div 
                key={message.id} 
                className={`flex ${
                  message.type === 'user' 
                    ? 'justify-end' 
                    : message.type === 'system' 
                      ? 'justify-center' 
                      : 'justify-start'
                }`}
              >
                <div 
                  className={`rounded-lg p-3 max-w-[80%] ${
                    message.type === 'user' 
                      ? 'bg-red-100 text-red-900' 
                      : message.type === 'system' 
                        ? 'bg-gray-100 text-gray-600 text-sm py-2 px-4' 
                        : 'bg-white shadow-sm border border-gray-100'
                  }`}
                >
                  {renderMessageContent(message)}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>
        
        {/* Input area */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end space-x-2">
              <div className="flex-1 bg-gray-100 rounded-lg p-2">
                <textarea 
                  className="w-full bg-transparent border-0 focus:ring-0 resize-none min-h-[60px] max-h-[200px] outline-none"
                  placeholder="Posez votre question..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  disabled={isLoading}
                />
              </div>
              <button 
                className={`rounded-full p-3 ${
                  isLoading || !inputValue.trim() 
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                    : 'bg-red-600 text-white hover:bg-red-700'
                } transition-colors`}
                onClick={handleSendMessage}
                disabled={isLoading || !inputValue.trim()}
              >
                {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Upload modal */}
      {showUploadModal && (
        <UploadProgressModal
          isOpen={showUploadModal}
          onClose={() => setShowUploadModal(false)}
          status={{
            in_progress: indexingStatus.status === 'processing',
            files_progress: uploadProgress,
            chunks_progress: indexingStatus.progress,
            current_file: indexingStatus.currentFile,
            error_occurred: indexingStatus.status === 'error',
            error_message: indexingStatus.message,
            current_step: indexingStatus.ocrInProgress ? 'ocr' : 
                         indexingStatus.status === 'processing' ? 'indexing' :
                         indexingStatus.status === 'completed' ? 'completed' : 
                         indexingStatus.status === 'error' ? 'error' : 'uploading',
            ocr_in_progress: indexingStatus.ocrInProgress,
            ocr_progress: indexingStatus.ocrProgress,
            ocr_current_page: indexingStatus.ocrCurrentPage,
            ocr_total_pages: indexingStatus.ocrTotalPages,
            ocr_logs: indexingStatus.ocrLogs,
            indexed_chunks: 0,
            total_chunks: 0
          }}
        />
      )}
      
      {/* Error notification */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-white shadow-lg rounded-lg p-4 flex items-center space-x-2 z-50 max-w-xs animate-fade-in">
          {error.includes('Copié') ? (
            <Copy size={18} className="text-green-500" />
          ) : (
            <AlertCircle size={18} className="text-red-500" />
          )}
          <p className={`text-sm ${error.includes('Copié') ? 'text-green-600' : 'text-red-600'}`}>
            {error}
          </p>
        </div>
      )}
      
      {/* Stats modal */}
      {stats && (
        <div className="fixed bottom-4 left-4 bg-white shadow-lg rounded-lg p-4 z-40 max-w-xs">
          <h4 className="text-sm font-medium text-gray-700 mb-2 flex justify-between items-center">
            <span>Statistiques d'indexation</span>
          </h4>
          <ul className="text-xs text-gray-600 space-y-1">
            <li>Documents indexés: {stats.processed_files || 0}</li>
            <li>Pages totales: {stats.total_files || 0}</li>
            <li>Chunks vectorisés: {stats.vectors_count || 0}</li>
            <li>Documents disponibles: {stats.vectors_count > 0 ? 'Oui' : 'Non'}</li>
          </ul>
          <button 
            className="mt-2 text-xs text-gray-400 hover:text-gray-600"
            onClick={() => setStats(null)}
          >
            Fermer
          </button>
        </div>
      )}
    </div>
  );
}

export default App;