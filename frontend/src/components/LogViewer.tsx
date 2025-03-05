import React, { useState, useEffect, useRef } from 'react';
import DOMPurify from 'dompurify';

// Interface des props du composant
interface LogViewerProps {
  logs: string[];
  maxHeight?: string;
  autoScroll?: boolean;
  title?: string;
  className?: string;
}

/**
 * Composant pour afficher des logs en temps réel avec auto-scroll et mise en forme.
 * 
 * @param logs Tableau de messages de log à afficher
 * @param maxHeight Hauteur maximale du conteneur (par défaut: "300px")
 * @param autoScroll Activer le défilement automatique (par défaut: true)
 * @param title Titre optionnel à afficher en haut du visualiseur
 * @param className Classes CSS additionnelles
 */
const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  maxHeight = "300px",
  autoScroll = true,
  title,
  className = ""
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [coloredLogs, setColoredLogs] = useState<string[]>([]);

  // Fonction pour colorer les logs selon le niveau (info, warning, error)
  const formatLogs = (logEntries: string[]) => {
    return logEntries.map(log => {
      // Colorer selon le type de log
      if (log.toLowerCase().includes("error") || log.toLowerCase().includes("erreur")) {
        return `<span class="text-red-500">${DOMPurify.sanitize(log)}</span>`;
      } else if (log.toLowerCase().includes("warning") || log.toLowerCase().includes("avertissement")) {
        return `<span class="text-yellow-500">${DOMPurify.sanitize(log)}</span>`;
      } else if (log.toLowerCase().includes("info")) {
        return `<span class="text-blue-500">${DOMPurify.sanitize(log)}</span>`;
      } else if (log.toLowerCase().includes("success") || log.toLowerCase().includes("succès") || log.toLowerCase().includes("terminé")) {
        return `<span class="text-green-500">${DOMPurify.sanitize(log)}</span>`;
      } else if (log.includes("%")) {
        // Mettre en évidence les pourcentages (progression)
        return log.replace(/(\d+)%/g, '<span class="font-bold text-indigo-500">$1%</span>');
      } else {
        return DOMPurify.sanitize(log);
      }
    });
  };

  // Mettre à jour les logs formatés quand les logs changent
  useEffect(() => {
    setColoredLogs(formatLogs(logs));
  }, [logs]);

  // Gestion de l'auto-scroll
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [coloredLogs, autoScroll]);

  return (
    <div className={`log-viewer border border-gray-300 rounded-md shadow-sm ${className}`}>
      {title && (
        <div className="log-header p-2 bg-gray-100 border-b border-gray-300 font-medium text-gray-700">
          {title}
        </div>
      )}
      <div 
        ref={containerRef}
        className="log-container p-3 font-mono text-sm bg-gray-50 overflow-y-auto"
        style={{ maxHeight }}
      >
        {coloredLogs.length === 0 ? (
          <div className="text-gray-400 italic">Aucune entrée de log disponible</div>
        ) : (
          <div className="space-y-1">
            {coloredLogs.map((log, index) => (
              <div 
                key={index} 
                className="log-entry" 
                dangerouslySetInnerHTML={{ __html: log }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default LogViewer;
