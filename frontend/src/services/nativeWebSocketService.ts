/**
 * Native WebSocket Service - FastAPI WebSocket Client
 * Substitui Socket.IO para usar WebSocket nativo do FastAPI
 */

type WebSocketEventHandler = (data: any) => void;

interface EventHandlers {
  onNewHandoff?: (handoff: any) => void;
  onHandoffAssigned?: (handoff: any) => void;
  onHandoffResolved?: (handoffId: string) => void;
  onNewMessage?: (sessionId: string, message: any) => void;
  onAgentStatusChange?: (agent: any) => void;
  onTypingIndicator?: (sessionId: string, isTyping: boolean) => void;
}

class NativeWebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private reconnectTimeout: number | null = null;
  private pingInterval: number | null = null; // Keep-alive
  private agentId: string | null = null;
  private token: string | null = null;
  private handlers: EventHandlers = {};
  
  // Callbacks
  public onConnectionChange: ((connected: boolean) => void) | null = null;
  public onMaxReconnectAttemptsReached: (() => void) | null = null;
  
  connect(token: string, agentId: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }
    
    this.token = token;
    this.agentId = agentId;
    
    // Use a mesma URL base da API
    // @ts-ignore - Vite env variables
    const baseUrl = import.meta.env?.VITE_API_URL || 'http://127.0.0.1:8001';
    const wsUrl = baseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    const url = `${wsUrl}/ws/whatsapp/${agentId}?token=${token}`;
    
    console.log('🔌 Connecting to WebSocket:', url);
    
    try {
      this.ws = new WebSocket(url);
      this.setupEventListeners();
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      this.handleReconnect();
    }
  }
  
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    
    if (this.ws) {
      // Send leave message before closing
      if (this.ws.readyState === WebSocket.OPEN) {
        this.send({ event: 'leave_agent_room' });
      }
      
      this.ws.close();
      this.ws = null;
    }
    
    this.reconnectAttempts = 0;
    this.token = null;
    this.agentId = null;
  }
  
  private setupEventListeners(): void {
    if (!this.ws) return;
    
    this.ws.onopen = () => {
      console.log('✅ WebSocket connected');
      this.reconnectAttempts = 0;
      
      if (this.onConnectionChange) {
        this.onConnectionChange(true);
      }
      
      // Send join message
      this.send({ event: 'join_agent_room' });
      
      // Start keep-alive ping (every 30 seconds)
      this.pingInterval = window.setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.send({ event: 'ping' });
        }
      }, 30000);
    };
    
    this.ws.onclose = (event) => {
      console.log('❌ WebSocket disconnected:', event.code, event.reason);
      
      if (this.onConnectionChange) {
        this.onConnectionChange(false);
      }
      
      // Try to reconnect unless it was a clean close
      if (event.code !== 1000) {
        this.handleReconnect();
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
  }
  
  private handleMessage(message: any): void {
    const { event, data } = message;
    
    console.log('📩 WebSocket message:', event, data);
    
    switch (event) {
      case 'connected':
        console.log('Connection confirmed:', data);
        break;
        
      case 'new_handoff':
        if (this.handlers.onNewHandoff) {
          this.handlers.onNewHandoff(data);
        }
        break;
        
      case 'handoff_assigned':
        if (this.handlers.onHandoffAssigned) {
          this.handlers.onHandoffAssigned(data);
        }
        break;
        
      case 'handoff_resolved':
        if (this.handlers.onHandoffResolved) {
          this.handlers.onHandoffResolved(data.handoff_id);
        }
        break;
        
      case 'new_message':
        if (this.handlers.onNewMessage) {
          this.handlers.onNewMessage(data.session_id, data.message);
        }
        break;
        
      case 'agent_status_change':
        if (this.handlers.onAgentStatusChange) {
          this.handlers.onAgentStatusChange(data);
        }
        break;
        
      case 'typing_indicator':
        if (this.handlers.onTypingIndicator) {
          this.handlers.onTypingIndicator(data.session_id, data.is_typing);
        }
        break;
        
      default:
        console.warn('Unknown WebSocket event:', event);
    }
  }
  
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      if (this.onMaxReconnectAttemptsReached) {
        this.onMaxReconnectAttemptsReached();
      }
      return;
    }
    
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    this.reconnectTimeout = setTimeout(() => {
      if (this.token && this.agentId) {
        this.connect(this.token, this.agentId);
      }
    }, delay);
  }
  
  private send(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not open. Cannot send message:', message);
    }
  }
  
  // Public methods
  registerHandlers(handlers: EventHandlers): void {
    this.handlers = handlers;
  }
  
  joinAgentRoom(agentId: string): void {
    this.send({
      event: 'join_agent_room',
      data: { agent_id: agentId }
    });
  }
  
  leaveAgentRoom(agentId: string): void {
    this.send({
      event: 'leave_agent_room',
      data: { agent_id: agentId }
    });
  }
  
  sendTypingIndicator(sessionId: string, isTyping: boolean): void {
    this.send({
      event: 'typing',
      data: {
        session_id: sessionId,
        is_typing: isTyping
      }
    });
  }
  
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
  
  getSocketId(): string | null {
    return this.agentId; // FastAPI WS doesn't have socket.id, use agentId
  }
}

// Singleton instance
export const nativeWebSocketService = new NativeWebSocketService();
