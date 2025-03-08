# Multi-Upload Files System Implementation

This document outlines a solution for implementing a multi-file upload system with a queue where files are processed one at a time.

## Overview

Current Behavior:
- Users can select and upload a single PDF file
- The upload progress and processing are tracked and displayed
- The backend processes one file at a time

Proposed Enhancement:
- Allow selection of multiple files at once
- Maintain a client-side queue of files waiting to be uploaded
- Upload and process files sequentially
- Show status of each file in the queue

## Implementation Plan

### 1. Frontend Changes

#### A. Create a File Queue Manager

```tsx
// types.ts
interface QueuedFile {
  id: string;
  file: File;
  status: 'queued' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  error?: string;
}

// fileQueueContext.tsx
import React, { createContext, useState, useContext, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

interface FileQueueContextType {
  fileQueue: QueuedFile[];
  addFiles: (files: File[]) => void;
  removeFile: (id: string) => void;
  clearQueue: () => void;
  uploadNext: () => Promise<void>;
  updateFileStatus: (id: string, status: QueuedFile['status'], progress?: number, error?: string) => void;
  isUploading: boolean;
}

const FileQueueContext = createContext<FileQueueContextType | undefined>(undefined);

export const FileQueueProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [fileQueue, setFileQueue] = useState<QueuedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  
  const addFiles = useCallback((files: File[]) => {
    const newFiles = Array.from(files).map(file => ({
      id: uuidv4(),
      file,
      status: 'queued' as const,
      progress: 0
    }));
    
    setFileQueue(prev => [...prev, ...newFiles]);
  }, []);
  
  const removeFile = useCallback((id: string) => {
    setFileQueue(prev => prev.filter(file => file.id !== id));
  }, []);
  
  const clearQueue = useCallback(() => {
    setFileQueue([]);
  }, []);
  
  const updateFileStatus = useCallback((id: string, status: QueuedFile['status'], progress?: number, error?: string) => {
    setFileQueue(prev => prev.map(file => 
      file.id === id 
        ? { ...file, status, progress: progress ?? file.progress, error } 
        : file
    ));
  }, []);
  
  const uploadNext = useCallback(async () => {
    const pendingFile = fileQueue.find(f => f.status === 'queued');
    if (!pendingFile || isUploading) return;
    
    setIsUploading(true);
    updateFileStatus(pendingFile.id, 'uploading');
    
    try {
      // This function will be implemented in App.tsx
      // and will handle the actual upload and process tracking
      await uploadFile(pendingFile.file, (progress) => {
        updateFileStatus(pendingFile.id, 'uploading', progress);
      });
      
      updateFileStatus(pendingFile.id, 'completed', 100);
    } catch (error) {
      updateFileStatus(pendingFile.id, 'error', 0, error.message);
    } finally {
      setIsUploading(false);
      
      // Check if there are more files to upload
      const nextPendingFile = fileQueue.find(f => f.status === 'queued');
      if (nextPendingFile) {
        // Start next upload after a short delay
        setTimeout(() => {
          uploadNext();
        }, 500);
      }
    }
  }, [fileQueue, isUploading, updateFileStatus]);
  
  return (
    <FileQueueContext.Provider value={{ 
      fileQueue, 
      addFiles, 
      removeFile, 
      clearQueue, 
      uploadNext,
      updateFileStatus,
      isUploading 
    }}>
      {children}
    </FileQueueContext.Provider>
  );
};

export const useFileQueue = () => {
  const context = useContext(FileQueueContext);
  if (context === undefined) {
    throw new Error('useFileQueue must be used within a FileQueueProvider');
  }
  return context;
};
```

#### B. Create a File Queue Component

```tsx
// components/FileQueuePanel.tsx
import React from 'react';
import { X, FileText, AlertCircle, Check, Loader2 } from 'lucide-react';
import { useFileQueue } from '../fileQueueContext';

const FileQueuePanel: React.FC = () => {
  const { fileQueue, removeFile, uploadNext, isUploading } = useFileQueue();
  
  if (fileQueue.length === 0) return null;
  
  return (
    <div className="fixed bottom-4 right-4 bg-white shadow-lg rounded-lg p-4 max-w-md z-50">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-sm font-medium text-gray-700">
          Files Queue {isUploading ? '(Uploading...)' : ''}
        </h3>
        {!isUploading && fileQueue.some(f => f.status === 'queued') && (
          <button
            className="text-xs bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700"
            onClick={() => uploadNext()}
          >
            Start Upload
          </button>
        )}
      </div>
      
      <ul className="divide-y divide-gray-100">
        {fileQueue.map((queuedFile) => (
          <li key={queuedFile.id} className="py-2 flex items-center">
            <div className="mr-2">
              {queuedFile.status === 'queued' && <FileText size={16} className="text-gray-400" />}
              {queuedFile.status === 'uploading' && <Loader2 size={16} className="text-blue-500 animate-spin" />}
              {queuedFile.status === 'processing' && <Loader2 size={16} className="text-amber-500 animate-spin" />}
              {queuedFile.status === 'completed' && <Check size={16} className="text-green-500" />}
              {queuedFile.status === 'error' && <AlertCircle size={16} className="text-red-500" />}
            </div>
            
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 truncate">
                {queuedFile.file.name}
              </p>
              <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
                <div 
                  className={`h-1 rounded-full ${
                    queuedFile.status === 'error' ? 'bg-red-500' :
                    queuedFile.status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${queuedFile.progress}%` }}
                ></div>
              </div>
              {queuedFile.error && (
                <p className="text-xs text-red-500 mt-1">{queuedFile.error}</p>
              )}
            </div>
            
            {(queuedFile.status === 'queued' || queuedFile.status === 'error' || queuedFile.status === 'completed') && (
              <button
                className="ml-2 text-gray-400 hover:text-gray-600"
                onClick={() => removeFile(queuedFile.id)}
              >
                <X size={14} />
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FileQueuePanel;
```

#### C. Modify App.tsx to use the File Queue

```tsx
// App.tsx (modifications)

// 1. Import and wrap with provider
import { FileQueueProvider, useFileQueue } from './fileQueueContext';
import FileQueuePanel from './components/FileQueuePanel';

// 2. Wrap your component
const AppWithProviders = () => (
  <FileQueueProvider>
    <App />
  </FileQueueProvider>
);

// 3. Use the hook inside App component
function App() {
  // Existing state ...
  const { addFiles, uploadNext } = useFileQueue();
  
  // 4. Modify file input to accept multiple files
  <input 
    type="file" 
    ref={fileInputRef} 
    className="hidden" 
    accept=".pdf" 
    multiple  // Add this attribute
    onChange={handleFileSelection} // Change to a new handler
  />
  
  // 5. New file selection handler
  const handleFileSelection = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = event.target.files;
    if (!fileList || fileList.length === 0) return;
    
    // Validate files (type and size)
    const validFiles: File[] = [];
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      
      if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        setError(`Type de fichier non supporté: ${file.name}. Seuls les PDF sont acceptés.`);
        continue;
      }
      
      if (file.size > 150 * 1024 * 1024) {
        setError(`La taille du fichier ${file.name} ne doit pas dépasser 150 MB.`);
        continue;
      }
      
      validFiles.push(file);
    }
    
    if (validFiles.length > 0) {
      addFiles(validFiles);
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      // Start uploading automatically if desired
      uploadNext();
    }
  };
  
  // 6. Implement upload file function
  // This function should be defined at the top level and passed to the provider
  const uploadFile = async (file: File, onProgress: (progress: number) => void): Promise<void> => {
    setShowUploadModal(true);
    setUploadProgress(0);
    
    if (useMockApi) {
      // Simulate file upload (existing mock logic)
      // ...
      return;
    }
    
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('file', file);
      
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
          onProgress(progress);
        }
      });
      
      xhr.addEventListener('load', async () => {
        if (xhr.status === 200 || xhr.status === 202) {
          setIndexingStatus({
            status: 'processing',
            progress: 0,
            currentFile: file.name
          });
          
          addSystemMessage(`Indexation de ${file.name} en cours...`);
          
          // Start checking indexing status
          await checkIndexingStatus();
          resolve();
        } else {
          let errorMsg = 'Erreur lors du téléchargement du fichier.';
          try {
            const response = JSON.parse(xhr.responseText);
            if (response && response.detail) {
              errorMsg = response.detail;
            }
          } catch (e) {
            console.error('Erreur de parsing JSON:', e);
          }
          
          setError(errorMsg);
          setShowUploadModal(false);
          reject(new Error(errorMsg));
        }
      });
      
      xhr.addEventListener('error', () => {
        console.error('XHR error event triggered');
        const errorMsg = 'Erreur lors du téléchargement du fichier.';
        setError(errorMsg);
        setShowUploadModal(false);
        reject(new Error(errorMsg));
      });
      
      xhr.open('POST', '/api/v1/documents');
      xhr.send(formData);
    });
  };
  
  // 7. Add FileQueuePanel to the component render
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Existing code... */}
      
      {/* Add this line to show the file queue */}
      <FileQueuePanel />
      
      {/* Existing modals and UI... */}
    </div>
  );
}

export default AppWithProviders;
```

### 2. Backend Considerations

The current backend design already handles one file at a time, which is ideal. No changes are needed on the backend since:

1. The frontend will handle queueing and sequential sending of files
2. Each file is processed individually via separate HTTP requests
3. The backend already has proper error handling and status tracking

### 3. Security and Error Handling

1. **File Validation**:
   - Continue to validate each file's type (PDF only)
   - Enforce size limits per file (currently 150MB)
   - Consider adding a maximum number of files in the queue (e.g., 10)

2. **Error Handling**:
   - Each file in the queue should have its own error state
   - If one file fails, the system should continue with the next file
   - Track which files failed and allow for retry functionality

3. **Progress Tracking**:
   - Each file should have its own progress indicator
   - Overall progress across all files could be shown as well
   - Show clear status indicators (queued, uploading, processing, completed, error)

### 4. Additional Features

1. **Drag and Drop Area**:
   - Add a drop zone for easier file selection

2. **Queue Management**:
   - Allow reordering of queued files
   - Enable pausing/resuming the upload process
   - Add "Clear All" and "Remove Completed" options

3. **Batch Operations**:
   - Allow selection of multiple files for removal from the queue
   - Provide statistics about the upload batch

## Implementation Strategy

1. First, implement the basic file queue with sequential uploading
2. Add the file queue panel to display the status of each file
3. Enhance the upload input to accept multiple files
4. Test thoroughly with various file sizes and quantities
5. Add advanced features like drag-and-drop and queue management

This approach allows for a progressive enhancement while maintaining the current functionality.