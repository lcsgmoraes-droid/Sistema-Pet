// WhatsApp API Service
import { api } from './api';
import type { DashboardStats, AgentStatus, HandoffItem, Message } from '../stores/whatsappStore';

const BASE_URL = '/whatsapp';

export const whatsappService = {
  // Configuration
  async getConfig(): Promise<any> {
    const response = await api.get(`${BASE_URL}/config`);
    return response.data;
  },
  
  // Stats
  async getStats(): Promise<DashboardStats> {
    const response = await api.get(`${BASE_URL}/analytics/dashboard`);
    return response.data;
  },
  
  // Agents
  async getAgents(): Promise<AgentStatus[]> {
    const response = await api.get(`${BASE_URL}/agents`);
    return response.data;
  },
  
  async createAgent(data: {
    name: string;
    email: string;
    status?: string;
    max_concurrent_chats?: number;
    auto_assign?: boolean;
    receive_notifications?: boolean;
  }): Promise<AgentStatus> {
    const response = await api.post(`${BASE_URL}/agents`, data);
    return response.data;
  },
  
  async getAgent(agentId: string): Promise<AgentStatus> {
    const response = await api.get(`${BASE_URL}/agents/${agentId}`);
    return response.data;
  },
  
  async updateAgent(agentId: string, data: Partial<AgentStatus>): Promise<AgentStatus> {
    const response = await api.put(`${BASE_URL}/agents/${agentId}`, data);
    return response.data;
  },
  
  async deleteAgent(agentId: string): Promise<void> {
    await api.delete(`${BASE_URL}/agents/${agentId}`);
  },
  
  // Handoffs
  async getHandoffs(status?: string): Promise<HandoffItem[]> {
    const params = status ? { status } : {};
    const response = await api.get(`${BASE_URL}/handoffs/pending`, { params });
    return response.data;
  },
  
  async createHandoff(data: {
    session_id: string;
    phone_number: string;
    customer_name?: string;
    reason: string;
    reason_details?: string;
    priority?: string;
  }): Promise<HandoffItem> {
    const response = await api.post(`${BASE_URL}/handoffs`, data);
    return response.data;
  },
  
  async getHandoff(handoffId: string): Promise<HandoffItem> {
    const response = await api.get(`${BASE_URL}/handoffs/${handoffId}`);
    return response.data;
  },
  
  async assignHandoff(handoffId: string, agentId: string): Promise<HandoffItem> {
    const response = await api.post(`${BASE_URL}/handoffs/${handoffId}/assign`, {
      agent_id: agentId
    });
    return response.data;
  },
  
  async resolveHandoff(handoffId: string, notes: string): Promise<void> {
    await api.post(`${BASE_URL}/handoffs/${handoffId}/resolve`, {
      resolution_notes: notes
    });
  },
  
  async cancelHandoff(handoffId: string): Promise<void> {
    await api.post(`${BASE_URL}/handoffs/${handoffId}/cancel`);
  },
  
  // Internal Notes
  async getNotes(handoffId: string): Promise<any[]> {
    const response = await api.get(`${BASE_URL}/handoffs/${handoffId}/notes`);
    return response.data;
  },
  
  async addNote(handoffId: string, content: string): Promise<any> {
    const response = await api.post(`${BASE_URL}/handoffs/${handoffId}/notes`, {
      content
    });
    return response.data;
  },
  
  // Messages
  async getMessages(sessionId: string): Promise<Message[]> {
    const response = await api.get(`${BASE_URL}/sessions/${sessionId}/messages`);
    return response.data;
  },
  
  async sendMessage(sessionId: string, content: string): Promise<Message> {
    const response = await api.post(`${BASE_URL}/messages`, {
      session_id: sessionId,
      message: content
    });
    return response.data;
  },
  
  // Sessions
  async createSession(data: {
    phone_number: string;
    customer_name?: string;
    initial_message?: string;
  }): Promise<any> {
    const response = await api.post(`${BASE_URL}/sessions`, data);
    return response.data;
  },
  
  async getSession(sessionId: string): Promise<any> {
    const response = await api.get(`${BASE_URL}/sessions/${sessionId}`);
    return response.data;
  },
  
  // Sentiment Testing
  async testSentiment(text: string): Promise<{
    score: number;
    label: string;
    emotions: string[];
    triggers: string[];
    should_handoff: boolean;
  }> {
    const response = await api.post(`${BASE_URL}/sentiment/test`, { text });
    return response.data;
  }
};
