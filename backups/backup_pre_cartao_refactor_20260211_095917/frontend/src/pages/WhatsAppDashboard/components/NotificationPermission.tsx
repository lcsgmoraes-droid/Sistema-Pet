import React, { useState, useEffect } from 'react';

export const NotificationPermission: React.FC = () => {
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [showBanner, setShowBanner] = useState(false);
  
  useEffect(() => {
    if ('Notification' in window) {
      setPermission(Notification.permission);
      
      // Show banner if permission not granted
      if (Notification.permission === 'default') {
        setShowBanner(true);
      }
    }
  }, []);
  
  const requestPermission = async () => {
    if ('Notification' in window) {
      const result = await Notification.requestPermission();
      setPermission(result);
      
      if (result === 'granted') {
        setShowBanner(false);
        
        // Show test notification
        new Notification('Notificações Ativadas', {
          body: 'Você receberá alertas de novas conversas',
          icon: '/logo192.png'
        });
      }
    }
  };
  
  if (!showBanner || permission === 'granted') {
    return null;
  }
  
  return (
    <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
          </svg>
        </div>
        
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-blue-900 mb-1">
            Ativar Notificações
          </h3>
          <p className="text-sm text-blue-700 mb-3">
            Receba alertas instantâneos quando novas conversas precisarem de atendimento
          </p>
          
          <div className="flex gap-2">
            <button
              onClick={requestPermission}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Ativar Notificações
            </button>
            <button
              onClick={() => setShowBanner(false)}
              className="px-4 py-2 bg-white text-blue-700 text-sm font-medium rounded-lg border border-blue-200 hover:bg-blue-50 transition-colors"
            >
              Agora Não
            </button>
          </div>
        </div>
        
        <button
          onClick={() => setShowBanner(false)}
          className="flex-shrink-0 text-blue-400 hover:text-blue-600 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};
