// WhatsApp Atendimento - Estado Global
import { create } from 'zustand';
import { whatsappService } from '../services/whatsappService.ts';

export interface DashboardStats {
  total_handoffs: number;
  pending_count: number;
  active_count: number;
  resolved_count: number;
  available_agents: number;
  avg_response_time_seconds: number;
}

export interface AgentStatus {
  id: string;
  tenant_id: string;
  user_id: number;
  name: string;
  email: string;
  status: 'online' | 'offline' | 'busy' | 'away';
  max_concurrent_chats: number;
  current_chats: number;
  auto_assign: boolean;
  receive_notifications: boolean;
  created_at: string;
  updated_at: string;
}

export interface HandoffItem {
  id: string;
  tenant_id: string;
  session_id: string;
  phone_number: string;
  customer_name: string | null;
  reason: string;
  reason_details: string | null;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'active' | 'resolved' | 'cancelled';
  assigned_agent_id: string | null;
  assigned_at: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  rating: number | null;
  rating_feedback: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  sender_type: 'customer' | 'bot' | 'agent' | 'system';
  content: string;
  timestamp: string;
  read: boolean;
}

interface WhatsAppStore {
  // Stats
  stats: DashboardStats | null;
  isLoadingStats: boolean;
  
  // Agents
  agents: AgentStatus[];
  currentAgent: AgentStatus | null;
  isLoadingAgents: boolean;
  
  // Handoffs
  handoffs: HandoffItem[];
  activeHandoff: HandoffItem | null;
  isLoadingHandoffs: boolean;
  filterStatus: 'all' | 'pending' | 'active' | 'my';
  
  // Messages
  messages: Record<string, Message[]>;
  isLoadingMessages: Record<string, boolean>;
  
  // UI State
  isConnected: boolean;
  isSidebarOpen: boolean;
  isBotAssistOpen: boolean;
  notifications: Notification[];
  
  // Actions - Stats
  fetchStats: () => Promise<void>;
  
  // Actions - Agents
  fetchAgents: () => Promise<void>;
  initializeCurrentAgent: () => Promise<void>;
  updateAgentStatus: (status: AgentStatus['status']) => Promise<void>;
  
  // Actions - Handoffs
  fetchHandoffs: (status?: string) => Promise<void>;
  setFilterStatus: (status: WhatsAppStore['filterStatus']) => void;
  takeHandoff: (handoffId: string) => Promise<void>;
  resolveHandoff: (handoffId: string, notes: string) => Promise<void>;
  setActiveHandoff: (handoff: HandoffItem | null) => void;
  
  // Actions - Messages
  fetchMessages: (sessionId: string) => Promise<void>;
  sendMessage: (sessionId: string, content: string) => Promise<void>;
  addMessage: (sessionId: string, message: Message) => void;
  
  // Actions - UI
  setConnected: (connected: boolean) => void;
  toggleSidebar: () => void;
  toggleBotAssist: () => void;
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
}

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
}

export const useWhatsAppStore = create<WhatsAppStore>()((set, get) => ({
  // Initial State
  stats: null,
  isLoadingStats: false,
  
  agents: [],
  currentAgent: null,
  isLoadingAgents: false,
  
  handoffs: [],
  activeHandoff: null,
  isLoadingHandoffs: false,
  filterStatus: 'all',
  
  messages: {},
  isLoadingMessages: {},
  
  isConnected: false,
  isSidebarOpen: true,
  isBotAssistOpen: false,
  notifications: [],
  
  // Stats Actions
  fetchStats: async () => {
    const state = get();
    
    // Prevenir requisições simultâneas
    if (state.isLoadingStats) {
      console.log('⏭️ Stats already loading, skipping...');
      return;
    }
    
    console.log('📊 Fetching stats...');
    set({ isLoadingStats: true });
    
    // Timeout aumentado para 10 segundos
    const timeout = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Stats timeout')), 10000)
    );
    
    try {
      const stats = await Promise.race([
        whatsappService.getStats(),
        timeout
      ]);
      console.log('✅ Stats received:', stats);
      set({ stats, isLoadingStats: false });
    } catch (error) {
      console.error('❌ Error fetching stats:', error);
      // Mesmo com erro, desbloqueia o loading
      set({ isLoadingStats: false });
    }
  },
  
  // Agents Actions
  fetchAgents: async () => {
    set({ isLoadingAgents: true });
    try {
      const agents = await whatsappService.getAgents();
      set({ agents, isLoadingAgents: false });
    } catch (error) {
      console.error('Error fetching agents:', error);
      set({ isLoadingAgents: false });
    }
  },
  
  initializeCurrentAgent: async () => {
    try {
      console.log('🔄 Initializing current agent...');
      
      // Buscar dados do usuário logado
      const userStr = localStorage.getItem('user');
      if (!userStr) {
        console.warn('⚠️ No user found in localStorage');
        return;
      }
      
      const user = JSON.parse(userStr);
      console.log('👤 User loaded:', user.email);
      
      // Buscar ou criar agente
      const agents = await whatsappService.getAgents();
      console.log('📋 Agents fetched:', agents.length);
      
      let currentAgent = agents.find(a => a.user_id === user.id);
      
      if (!currentAgent) {
        console.log('➕ Creating new agent...');
        // Criar agente se não existir
        currentAgent = await whatsappService.createAgent({
          name: user.name || user.email,
          email: user.email,
          status: 'online',
          max_concurrent_chats: 5,
          auto_assign: true,
          receive_notifications: true
        });
        console.log('✅ Created new agent:', currentAgent.id);
      } else {
        console.log('🔄 Updating existing agent to online...');
        // Atualizar status para online
        currentAgent = await whatsappService.updateAgent(currentAgent.id, { status: 'online' });
        console.log('✅ Agent set to online:', currentAgent.id);
      }
      
      set({ currentAgent });
      console.log('✅ Current agent initialized');
    } catch (error) {
      console.error('❌ Error initializing current agent:', error);
      // Não bloquear o dashboard se falhar
    }
  },
  
  updateAgentStatus: async (status) => {
    const { currentAgent } = get();
    if (!currentAgent) return;
    
    try {
      const updated = await whatsappService.updateAgent(currentAgent.id, { status });
      set({ currentAgent: updated });
      
      // Update in agents list
      set((state) => ({
        agents: state.agents.map(a => a.id === updated.id ? updated : a)
      }));
    } catch (error) {
      console.error('Error updating agent status:', error);
    }
  },
  
  // Handoffs Actions
  fetchHandoffs: async (status) => {
    set({ isLoadingHandoffs: true });
    try {
      const handoffs = await whatsappService.getHandoffs(status);
      set({ handoffs, isLoadingHandoffs: false });
    } catch (error) {
      console.error('Error fetching handoffs:', error);
      set({ isLoadingHandoffs: false });
    }
  },
  
  setFilterStatus: (filterStatus) => {
    set({ filterStatus });
    const statusMap = {
      all: undefined,
      pending: 'pending',
      active: 'active',
      my: 'active' // Will need additional filtering
    };
    get().fetchHandoffs(statusMap[filterStatus]);
  },
  
  takeHandoff: async (handoffId) => {
    const { currentAgent } = get();
    if (!currentAgent) return;
    
    try {
      const updated = await whatsappService.assignHandoff(handoffId, currentAgent.id);
      
      // Update in list
      set((state) => ({
        handoffs: state.handoffs.map(h => h.id === updated.id ? updated : h)
      }));
      
      // Set as active
      set({ activeHandoff: updated });
      
      get().addNotification({
        type: 'success',
        title: 'Conversa assumida',
        message: `Você assumiu a conversa com ${updated.customer_name || updated.phone_number}`,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error taking handoff:', error);
      get().addNotification({
        type: 'error',
        title: 'Erro',
        message: 'Não foi possível assumir a conversa',
        timestamp: new Date().toISOString()
      });
    }
  },
  
  resolveHandoff: async (handoffId, notes) => {
    try {
      await whatsappService.resolveHandoff(handoffId, notes);
      
      // Remove from list
      set((state) => ({
        handoffs: state.handoffs.filter(h => h.id !== handoffId),
        activeHandoff: state.activeHandoff?.id === handoffId ? null : state.activeHandoff
      }));
      
      get().addNotification({
        type: 'success',
        title: 'Conversa resolvida',
        message: 'A conversa foi finalizada com sucesso',
        timestamp: new Date().toISOString()
      });
      
      // Refresh stats
      get().fetchStats();
    } catch (error) {
      console.error('Error resolving handoff:', error);
      get().addNotification({
        type: 'error',
        title: 'Erro',
        message: 'Não foi possível resolver a conversa',
        timestamp: new Date().toISOString()
      });
    }
  },
  
  setActiveHandoff: (handoff) => {
    set({ activeHandoff: handoff });
  },
  
  // Messages Actions
  fetchMessages: async (sessionId) => {
    set((state) => ({
      isLoadingMessages: { ...state.isLoadingMessages, [sessionId]: true }
    }));
    
    try {
      const messages = await whatsappService.getMessages(sessionId);
      set((state) => ({
        messages: { ...state.messages, [sessionId]: messages },
        isLoadingMessages: { ...state.isLoadingMessages, [sessionId]: false }
      }));
    } catch (error) {
      console.error('Error fetching messages:', error);
      set((state) => ({
        isLoadingMessages: { ...state.isLoadingMessages, [sessionId]: false }
      }));
    }
  },
  
  sendMessage: async (sessionId, content) => {
    try {
      const message = await whatsappService.sendMessage(sessionId, content);
      
      // Add to messages
      set((state) => ({
        messages: {
          ...state.messages,
          [sessionId]: [...(state.messages[sessionId] || []), message]
        }
      }));
    } catch (error) {
      console.error('Error sending message:', error);
      get().addNotification({
        type: 'error',
        title: 'Erro ao enviar',
        message: 'Não foi possível enviar a mensagem',
        timestamp: new Date().toISOString()
      });
    }
  },
  
  addMessage: (sessionId, message) => {
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: [...(state.messages[sessionId] || []), message]
      }
    }));
  },
  
  // UI Actions
  setConnected: (connected) => set({ isConnected: connected }),
  
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  
  toggleBotAssist: () => set((state) => ({ isBotAssistOpen: !state.isBotAssistOpen })),
  
  addNotification: (notification) => {
    const id = Math.random().toString(36).substring(7);
    set((state) => ({
      notifications: [...state.notifications, { ...notification, id }]
    }));
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      get().removeNotification(id);
    }, 5000);
  },
  
  removeNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter(n => n.id !== id)
    }));
  }
}));
