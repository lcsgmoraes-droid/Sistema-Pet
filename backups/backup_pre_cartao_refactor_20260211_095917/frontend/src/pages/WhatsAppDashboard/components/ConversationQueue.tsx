import React, { memo, useCallback } from 'react';
import type { HandoffItem } from '../../../stores/whatsappStore';
import { useWhatsAppStore } from '../../../stores/whatsappStore';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface ConversationQueueProps {
  handoffs: HandoffItem[];
  activeHandoff: HandoffItem | null;
  isLoading: boolean;
}

export const ConversationQueue: React.FC<ConversationQueueProps> = memo(({
  handoffs,
  activeHandoff,
  isLoading
}) => {
  const { setActiveHandoff, takeHandoff } = useWhatsAppStore();
  
  const priorityColors = {
    urgent: 'bg-red-100 text-red-700 border-red-200',
    high: 'bg-orange-100 text-orange-700 border-orange-200',
    medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    low: 'bg-gray-100 text-gray-700 border-gray-200'
  };
  
  const priorityLabels = {
    urgent: '🚨 Urgente',
    high: '⚠️ Alta',
    medium: '📌 Média',
    low: '📋 Baixa'
  };
  
  const statusIcons = {
    pending: '⏳',
    active: '💬',
    resolved: '✅',
    cancelled: '❌'
  };
  
  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="border border-gray-200 rounded-lg p-3 animate-pulse">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-gray-200 rounded-full"></div>
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-2/3"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }
  
  if (handoffs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center text-gray-400">
          <svg className="w-12 h-12 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-sm font-medium">Nenhuma conversa</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="p-4 space-y-3">
      {handoffs.map((handoff) => {
        const isActive = activeHandoff?.id === handoff.id;
        const isPending = handoff.status === 'pending';
        
        return (
          <div
            key={handoff.id}
            onClick={() => setActiveHandoff(handoff)}
            className={`
              border rounded-lg p-3 cursor-pointer transition-all
              ${isActive
                ? 'border-blue-500 bg-blue-50 shadow-md'
                : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
              }
            `}
          >
            <div className="flex items-start gap-3">
              {/* Avatar */}
              <div className={`
                w-10 h-10 rounded-full flex items-center justify-center text-lg font-semibold
                ${priorityColors[handoff.priority]}
              `}>
                {handoff.customer_name
                  ? handoff.customer_name.charAt(0).toUpperCase()
                  : '👤'
                }
              </div>
              
              {/* Content */}
              <div className="flex-1 min-w-0">
                {/* Header */}
                <div className="flex items-start justify-between gap-2 mb-1">
                  <p className="font-medium text-gray-900 truncate">
                    {handoff.customer_name || 'Cliente'}
                  </p>
                  <span className="text-xs text-gray-500 whitespace-nowrap">
                    {formatDistanceToNow(new Date(handoff.created_at), {
                      addSuffix: true,
                      locale: ptBR
                    })}
                  </span>
                </div>
                
                {/* Phone */}
                <p className="text-xs text-gray-600 mb-2">
                  {handoff.phone_number}
                </p>
                
                {/* Reason */}
                <p className="text-sm text-gray-700 mb-2 line-clamp-2">
                  {handoff.reason_details || handoff.reason}
                </p>
                
                {/* Footer */}
                <div className="flex items-center justify-between">
                  {/* Priority Badge */}
                  <span className={`
                    text-xs px-2 py-1 rounded border
                    ${priorityColors[handoff.priority]}
                  `}>
                    {priorityLabels[handoff.priority]}
                  </span>
                  
                  {/* Status + Action */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {statusIcons[handoff.status]}
                    </span>
                    
                    {isPending && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          takeHandoff(handoff.id);
                        }}
                        className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                      >
                        Assumir
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
});
