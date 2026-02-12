// WebSocket Service - Socket.IO Client
import { io, Socket } from 'socket.io-client';
import type { HandoffItem, AgentStatus, Message } from '../stores/whatsappStore';

class SocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  
  connect(token: string): void {
    if (this.socket?.connected) {
      console.log('Socket already connected');
      return;
    }
    
    // Use a mesma URL base da API (para manter consistência)
    const backendUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
    
    console.log('🔌 Connecting to WebSocket at:', backendUrl);
    
    this.socket = io(backendUrl, {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
      reconnectionDelayMax: 5000,
      timeout: 10000
    });
    
    this.setupEventListeners();
  }
  
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.reconnectAttempts = 0;
    }
  }
  
  private setupEventListeners(): void {
    if (!this.socket) return;
    
    // Connection Events
    this.socket.on('connect', () => {
      console.log('✅ Socket connected:', this.socket?.id);
      this.reconnectAttempts = 0;
      
      // Notify store
      if (this.onConnectionChange) {
        this.onConnectionChange(true);
      }
    });
    
    this.socket.on('disconnect', (reason: string) => {
      console.log('❌ Socket disconnected:', reason);
      
      if (this.onConnectionChange) {
        this.onConnectionChange(false);
      }
      
      // Auto-reconnect logic
      if (reason === 'io server disconnect') {
        // Server disconnected, try to reconnect
        this.socket?.connect();
      }
    });
    
    this.socket.on('connect_error', (error: Error) => {
      console.error('Socket connection error:', error);
      this.reconnectAttempts++;
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached');
        if (this.onMaxReconnectAttemptsReached) {
          this.onMaxReconnectAttemptsReached();
        }
      }
    });
    
    this.socket.on('reconnect', (attemptNumber: number) => {
      console.log('✅ Socket reconnected after', attemptNumber, 'attempts');
      this.reconnectAttempts = 0;
    });
    
    this.socket.on('reconnect_attempt', (attemptNumber: number) => {
      console.log('🔄 Reconnection attempt', attemptNumber);
    });
    
    this.socket.on('reconnect_failed', () => {
      console.error('❌ Reconnection failed');
    });
  }
  
  // Event Emitters
  emit(event: string, data: any): void {
    if (!this.socket?.connected) {
      console.warn('Socket not connected, cannot emit:', event);
      return;
    }
    
    this.socket.emit(event, data);
  }
  
  // Event Listeners Registration
  on(event: string, handler: (...args: any[]) => void): void {
    if (!this.socket) {
      console.warn('Socket not initialized, cannot register listener:', event);
      return;
    }
    
    this.socket.on(event, handler);
  }
  
  off(event: string, handler?: (...args: any[]) => void): void {
    if (!this.socket) return;
    
    if (handler) {
      this.socket.off(event, handler);
    } else {
      this.socket.off(event);
    }
  }
  
  // Callbacks
  onConnectionChange?: (connected: boolean) => void;
  onMaxReconnectAttemptsReached?: () => void;
  onNewHandoff?: (handoff: HandoffItem) => void;
  onHandoffAssigned?: (handoff: HandoffItem) => void;
  onHandoffResolved?: (handoffId: string) => void;
  onNewMessage?: (sessionId: string, message: Message) => void;
  onAgentStatusChange?: (agent: AgentStatus) => void;
  onTypingIndicator?: (sessionId: string, isTyping: boolean) => void;
  
  // Register business event handlers
  registerHandlers(handlers: {
    onNewHandoff?: (handoff: HandoffItem) => void;
    onHandoffAssigned?: (handoff: HandoffItem) => void;
    onHandoffResolved?: (handoffId: string) => void;
    onNewMessage?: (sessionId: string, message: Message) => void;
    onAgentStatusChange?: (agent: AgentStatus) => void;
    onTypingIndicator?: (sessionId: string, isTyping: boolean) => void;
  }): void {
    this.onNewHandoff = handlers.onNewHandoff;
    this.onHandoffAssigned = handlers.onHandoffAssigned;
    this.onHandoffResolved = handlers.onHandoffResolved;
    this.onNewMessage = handlers.onNewMessage;
    this.onAgentStatusChange = handlers.onAgentStatusChange;
    this.onTypingIndicator = handlers.onTypingIndicator;
    
    // Register socket event listeners
    if (this.onNewHandoff) {
      this.on('new_handoff', this.onNewHandoff);
    }
    
    if (this.onHandoffAssigned) {
      this.on('handoff_assigned', this.onHandoffAssigned);
    }
    
    if (this.onHandoffResolved) {
      this.on('handoff_resolved', this.onHandoffResolved);
    }
    
    if (this.onNewMessage) {
      this.on('new_message', (data: { session_id: string; message: Message }) => {
        this.onNewMessage!(data.session_id, data.message);
      });
    }
    
    if (this.onAgentStatusChange) {
      this.on('agent_status_change', this.onAgentStatusChange);
    }
    
    if (this.onTypingIndicator) {
      this.on('typing_indicator', (data: { session_id: string; is_typing: boolean }) => {
        this.onTypingIndicator!(data.session_id, data.is_typing);
      });
    }
  }
  
  // Utility Methods
  isConnected(): boolean {
    return this.socket?.connected || false;
  }
  
  getSocketId(): string | undefined {
    return this.socket?.id;
  }
  
  // Send typing indicator
  sendTypingIndicator(sessionId: string, isTyping: boolean): void {
    this.emit('typing', { session_id: sessionId, is_typing: isTyping });
  }
  
  // Join agent room (for receiving notifications)
  joinAgentRoom(agentId: string): void {
    this.emit('join_agent_room', { agent_id: agentId });
  }
  
  // Leave agent room
  leaveAgentRoom(agentId: string): void {
    this.emit('leave_agent_room', { agent_id: agentId });
  }
}

// Singleton instance
export const socketService = new SocketService();
