// Custom Hook for Native WebSocket Integration (FastAPI)
import { useEffect, useState } from 'react';
import { nativeWebSocketService } from '../services/nativeWebSocketService';
import { useWhatsAppStore } from '../stores/whatsappStore';

export const useSocket = (token: string | null, agentId: string | null) => {
  const [hasInitialized, setHasInitialized] = useState(false);
  
  const {
    addNotification,
    fetchHandoffs,
    setConnected,
    addMessage,
    fetchStats
  } = useWhatsAppStore();
  
  useEffect(() => {
    if (!token || !agentId || hasInitialized) return;
    
    setHasInitialized(true);
    console.log('🔌 useSocket: Initializing WebSocket connection...');
    
    // Connection change handler
    nativeWebSocketService.onConnectionChange = (connected) => {
      setConnected(connected);
      
      if (connected) {
        addNotification({
          type: 'success',
          title: 'Conectado',
          message: 'Conexão com servidor estabelecida',
          timestamp: new Date().toISOString()
        });
        
        // NÃO chamar fetchStats/fetchHandoffs aqui - conflita com HTTP!
        // Deixar o polling do useEffect fazer isso
      } else {
        addNotification({
          type: 'warning',
          title: 'Desconectado',
          message: 'Tentando reconectar ao servidor...',
          timestamp: new Date().toISOString()
        });
      }
    };
    
    // Max reconnect attempts handler
    nativeWebSocketService.onMaxReconnectAttemptsReached = () => {
      addNotification({
        type: 'error',
        title: 'Erro de Conexão',
        message: 'Não foi possível conectar ao servidor. Recarregue a página.',
        timestamp: new Date().toISOString()
      });
    };
    
    // Register business event handlers
    nativeWebSocketService.registerHandlers({
      // New handoff created
      onNewHandoff: (handoff) => {
        console.log('🆕 New handoff received:', handoff);
        
        // Refresh APENAS handoffs (stats será atualizado pelo polling)
        fetchHandoffs();
        
        // Show notification
        addNotification({
          type: 'info',
          title: 'Nova Conversa',
          message: `${handoff.customer_name || handoff.phone_number} precisa de ajuda`,
          timestamp: new Date().toISOString()
        });
        
        // Browser notification
        showBrowserNotification(
          'Nova Conversa - WhatsApp',
          `${handoff.customer_name || handoff.phone_number} - ${handoff.reason}`,
          handoff.priority
        );
        
        // Play sound for urgent/high priority
        if (handoff.priority === 'urgent' || handoff.priority === 'high') {
          playNotificationSound();
        }
      },
      
      // Handoff assigned to agent
      onHandoffAssigned: (handoff) => {
        console.log('👤 Handoff assigned:', handoff);
        
        // Refresh APENAS handoffs
        fetchHandoffs();
        
        // Notify if assigned to current agent
        if (handoff.assigned_agent_id === agentId) {
          addNotification({
            type: 'success',
            title: 'Conversa Atribuída',
            message: `Você foi atribuído à conversa com ${handoff.customer_name || handoff.phone_number}`,
            timestamp: new Date().toISOString()
          });
        }
      },
      
      // Handoff resolved
      onHandoffResolved: (handoffId) => {
        console.log('✅ Handoff resolved:', handoffId);
        
        // Refresh data
        fetchHandoffs();
        fetchStats();
      },
      
      // New message in conversation
      onNewMessage: (sessionId, message) => {
        console.log('💬 New message:', sessionId, message);
        
        // Add to store
        addMessage(sessionId, message);
        
        // Show notification if from customer
        if (message.sender_type === 'customer') {
          addNotification({
            type: 'info',
            title: 'Nova Mensagem',
            message: message.content.substring(0, 50) + '...',
            timestamp: new Date().toISOString()
          });
          
          // Play sound
          playNotificationSound('message');
        }
      },
      
      // Agent status changed
      onAgentStatusChange: (agent) => {
        console.log('📊 Agent status changed:', agent);
        
        // Refresh agents list
        fetchStats();
      },
      
      // Typing indicator
      onTypingIndicator: (sessionId, isTyping) => {
        console.log('⌨️ Typing indicator:', sessionId, isTyping);
        // Could update UI to show "Cliente está digitando..."
      }
    });
    
    // Connect
    nativeWebSocketService.connect(token, agentId);
    
    // Cleanup
    return () => {
      nativeWebSocketService.disconnect();
    };
  }, [token, agentId]);
  
  // Return simple status without causing re-renders
  return {
    isConnected: nativeWebSocketService.isConnected(),
    socketId: nativeWebSocketService.getSocketId(),
    sendTypingIndicator: nativeWebSocketService.sendTypingIndicator.bind(nativeWebSocketService)
  };
};

// Browser Notifications
function showBrowserNotification(title: string, body: string, priority?: string) {
  // Check if browser supports notifications
  if (!('Notification' in window)) {
    console.warn('Browser does not support notifications');
    return;
  }
  
  // Check permission
  if (Notification.permission === 'granted') {
    const notification = new Notification(title, {
      body,
      icon: '/favicon.svg',
      badge: '/favicon.svg',
      tag: 'whatsapp-notification',
      requireInteraction: priority === 'urgent',
      silent: false
    });
    
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
    
    // Auto-close after 10 seconds
    setTimeout(() => notification.close(), 10000);
  } else if (Notification.permission !== 'denied') {
    // Request permission
    Notification.requestPermission().then((permission) => {
      if (permission === 'granted') {
        showBrowserNotification(title, body, priority);
      }
    });
  }
}

// Sound Notifications
function playNotificationSound(type: 'handoff' | 'message' = 'handoff') {
  try {
    const audioContext = new (globalThis.AudioContext || (globalThis as any).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.type = 'sine';
    oscillator.frequency.value = type === 'handoff' ? 880 : 660;
    gainNode.gain.value = 0.04;

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.12);

    oscillator.onended = () => {
      audioContext.close().catch(() => {
        // ignore close errors
      });
    };
  } catch (error) {
    console.warn('Error playing sound:', error);
  }
}
