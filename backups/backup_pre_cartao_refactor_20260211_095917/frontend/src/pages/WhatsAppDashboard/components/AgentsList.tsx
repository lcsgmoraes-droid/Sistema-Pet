import React, { memo, useCallback } from 'react';
import type { AgentStatus } from '../../../stores/whatsappStore';
import { useWhatsAppStore } from '../../../stores/whatsappStore';

interface AgentsListProps {
  agents: AgentStatus[];
  isLoading: boolean;
}

export const AgentsList: React.FC<AgentsListProps> = memo(({ agents, isLoading }) => {
  const { currentAgent, updateAgentStatus } = useWhatsAppStore();
  
  const statusColors = {
    online: 'bg-green-500',
    busy: 'bg-yellow-500',
    away: 'bg-orange-500',
    offline: 'bg-gray-400'
  };
  
  const statusLabels = {
    online: 'Online',
    busy: 'Ocupado',
    away: 'Ausente',
    offline: 'Offline'
  };
  
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-2 rounded-lg animate-pulse">
            <div className="w-2 h-2 bg-gray-200 rounded-full"></div>
            <div className="flex-1">
              <div className="h-3 bg-gray-200 rounded w-2/3 mb-1"></div>
              <div className="h-2 bg-gray-200 rounded w-1/2"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }
  
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
        Agentes ({agents.length})
      </h3>
      
      {agents.map((agent) => (
        <div
          key={agent.id}
          className={`
            flex items-center gap-3 p-2 rounded-lg transition-colors
            ${currentAgent?.id === agent.id ? 'bg-blue-50' : 'hover:bg-gray-50'}
          `}
        >
          {/* Status Indicator */}
          <div className="relative">
            <div className={`w-2 h-2 rounded-full ${statusColors[agent.status]}`}></div>
            {agent.status === 'online' && (
              <div className={`absolute inset-0 w-2 h-2 rounded-full ${statusColors[agent.status]} animate-ping opacity-75`}></div>
            )}
          </div>
          
          {/* Agent Info */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {agent.name}
            </p>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{statusLabels[agent.status]}</span>
              <span>•</span>
              <span>{agent.current_chats}/{agent.max_concurrent_chats}</span>
            </div>
          </div>
          
          {/* Status Change (if current agent) */}
          {currentAgent?.id === agent.id && (
            <select
              value={agent.status}
              onChange={(e) => updateAgentStatus(e.target.value as AgentStatus['status'])}
              className="text-xs border-gray-300 rounded px-2 py-1"
            >
              <option value="online">Online</option>
              <option value="busy">Ocupado</option>
              <option value="away">Ausente</option>
              <option value="offline">Offline</option>
            </select>
          )}
        </div>
      ))}
      
      {agents.length === 0 && (
        <p className="text-sm text-gray-500 text-center py-4">
          Nenhum agente disponível
        </p>
      )}
    </div>
  );
});
