import React, { useEffect, useRef, useState } from 'react';
import type { HandoffItem, Message } from '../../../stores/whatsappStore';
import { useWhatsAppStore } from '../../../stores/whatsappStore';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface ChatInterfaceProps {
  handoff: HandoffItem;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ handoff }) => {
  const {
    messages,
    isLoadingMessages,
    fetchMessages,
    sendMessage,
    resolveHandoff,
    toggleBotAssist
  } = useWhatsAppStore();
  
  const [inputMessage, setInputMessage] = useState('');
  const [isResolving, setIsResolving] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionMessages = messages[handoff.session_id] || [];
  const isLoading = isLoadingMessages[handoff.session_id] || false;
  
  useEffect(() => {
    if (handoff.session_id) {
      fetchMessages(handoff.session_id);
    }
  }, [handoff.session_id]);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [sessionMessages]);
  
  const handleSend = async () => {
    if (!inputMessage.trim()) return;
    
    await sendMessage(handoff.session_id, inputMessage);
    setInputMessage('');
  };
  
  const handleResolve = async () => {
    if (!resolutionNotes.trim()) {
      alert('Por favor, adicione notas de resolução');
      return;
    }
    
    await resolveHandoff(handoff.id, resolutionNotes);
    setIsResolving(false);
    setResolutionNotes('');
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const priorityColors = {
    urgent: 'border-red-500 bg-red-50',
    high: 'border-orange-500 bg-orange-50',
    medium: 'border-yellow-500 bg-yellow-50',
    low: 'border-gray-500 bg-gray-50'
  };
  
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className={`border-b-4 ${priorityColors[handoff.priority]} p-4`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center text-white text-lg font-semibold">
              {handoff.customer_name
                ? handoff.customer_name.charAt(0).toUpperCase()
                : '👤'
              }
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {handoff.customer_name || 'Cliente'}
              </h2>
              <p className="text-sm text-gray-600">{handoff.phone_number}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Bot Assist Toggle */}
            <button
              onClick={toggleBotAssist}
              className="p-2 rounded-lg hover:bg-white hover:shadow transition-all"
              title="Bot Assist"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </button>
            
            {/* Resolve Button */}
            {handoff.status === 'active' && (
              <button
                onClick={() => setIsResolving(true)}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
              >
                Resolver
              </button>
            )}
          </div>
        </div>
        
        {/* Handoff Info */}
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-sm text-gray-700">
            <span className="font-medium">Motivo:</span> {handoff.reason}
          </p>
          {handoff.reason_details && (
            <p className="text-sm text-gray-600 mt-1">
              {handoff.reason_details}
            </p>
          )}
        </div>
      </div>
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-400">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-sm">Carregando mensagens...</p>
            </div>
          </div>
        ) : sessionMessages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <svg className="w-12 h-12 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p className="text-sm font-medium">Nenhuma mensagem ainda</p>
            </div>
          </div>
        ) : (
          <>
            {sessionMessages.map((message: Message) => {
              const isAgent = message.sender_type === 'agent';
              const isSystem = message.sender_type === 'system';
              
              if (isSystem) {
                return (
                  <div key={message.id} className="flex justify-center">
                    <div className="bg-gray-100 text-gray-600 text-xs px-3 py-1 rounded-full">
                      {message.content}
                    </div>
                  </div>
                );
              }
              
              return (
                <div
                  key={message.id}
                  className={`flex ${isAgent ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[70%] ${isAgent ? 'order-2' : 'order-1'}`}>
                    <div className={`
                      rounded-lg px-4 py-2
                      ${isAgent
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                      }
                    `}>
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    </div>
                    <p className={`text-xs text-gray-500 mt-1 ${isAgent ? 'text-right' : 'text-left'}`}>
                      {format(new Date(message.timestamp), 'HH:mm', { locale: ptBR })}
                    </p>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      
      {/* Input Area */}
      {handoff.status === 'active' && !isResolving && (
        <div className="border-t border-gray-200 p-4">
          <div className="flex gap-2">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Digite sua mensagem..."
              rows={3}
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleSend}
              disabled={!inputMessage.trim()}
              className="px-6 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              Enviar
            </button>
          </div>
        </div>
      )}
      
      {/* Resolution Modal */}
      {isResolving && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Resolver Conversa
            </h3>
            
            <textarea
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="Descreva como foi resolvido o atendimento..."
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
              autoFocus
            />
            
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setIsResolving(false);
                  setResolutionNotes('');
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleResolve}
                disabled={!resolutionNotes.trim()}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                Confirmar Resolução
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
