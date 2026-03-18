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
  private readonly maxReconnectAttempts = 5;
  private readonly reconnectDelay = 1000;
  private reconnectTimeout: number | null = null;
  private pingInterval: number | null = null; // Keep-alive
  private isDisconnecting = false;
  private agentId: string | null = null;
  private token: string | null = null;
  private handlers: EventHandlers = {};
  private readonly debugWs = false;
  
  // Callbacks
  public onConnectionChange: ((connected: boolean) => void) | null = null;
  public onMaxReconnectAttemptsReached: (() => void) | null = null;

  private resolveWsBaseUrl(): string {
    // @ts-ignore - Vite env variables
    const configuredApiUrl = import.meta.env?.VITE_API_URL || '/api';
    const isRelative = configuredApiUrl.startsWith('/');

    if (isRelative) {
      const protocol = globalThis.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${globalThis.location.host}${configuredApiUrl}`;
    }

    return configuredApiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
  }
  
  connect(token: string, agentId: string): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      console.log('WebSocket already connected');
      return;
    }

    this.isDisconnecting = false;
    
    this.token = token;
    this.agentId = agentId;
    
    const wsBaseUrl = this.resolveWsBaseUrl().replace(/\/+$/, '');
    const url = `${wsBaseUrl}/ws/whatsapp/${agentId}?token=${token}`;
    
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
    this.isDisconnecting = true;

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
      this.isDisconnecting = false;

      if (this.pingInterval) {
        clearInterval(this.pingInterval);
        this.pingInterval = null;
      }
      
      if (this.onConnectionChange) {
        this.onConnectionChange(true);
      }
      
      // Send join message
      this.send({ event: 'join_agent_room' });
      
      // Start keep-alive ping (every 30 seconds)
      this.pingInterval = globalThis.setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.send({ event: 'ping' });
        }
      }, 30000);
    };
    
    this.ws.onclose = (event) => {
      console.log('❌ WebSocket disconnected:', event.code, event.reason);

      if (this.pingInterval) {
        clearInterval(this.pingInterval);
        this.pingInterval = null;
      }

      this.ws = null;
      
      if (this.onConnectionChange) {
        this.onConnectionChange(false);
      }
      
      // Try to reconnect unless it was a clean close or intentional disconnect
      if (event.code !== 1000 && !this.isDisconnecting) {
        this.handleReconnect();
      }
    };
    
    this.ws.onerror = (error) => {
      if (this.isDisconnecting) {
        return;
      }

      console.warn('WebSocket connection issue. Reconnecting automatically.', {
        readyState: this.ws?.readyState,
        error
      });
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

    if (event === 'pong') {
      return;
    }

    if (this.debugWs) {
      console.log('📩 WebSocket message:', event, data);
    }
    
    const eventActions: Record<string, () => void> = {
      connected: () => {
        if (this.debugWs) {
          console.log('Connection confirmed:', data);
        }
      },
      new_handoff: () => this.handlers.onNewHandoff?.(data),
      handoff_assigned: () => this.handlers.onHandoffAssigned?.(data),
      handoff_resolved: () => this.handlers.onHandoffResolved?.(data.handoff_id),
      new_message: () => this.handlers.onNewMessage?.(data.session_id, data.message),
      agent_status_change: () => this.handlers.onAgentStatusChange?.(data),
      typing_indicator: () => this.handlers.onTypingIndicator?.(data.session_id, data.is_typing)
    };

    const action = eventActions[event];
    if (action) {
      action();
    } else {
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
