import React, { useEffect } from 'react';
import { useWhatsAppStore } from '../../stores/whatsappStore';
import { useSocket } from '../../hooks/useSocket';
import './responsive.css';
import { ErrorBoundary } from '../../components/ErrorBoundary.tsx';
import { StatsCards } from './components/StatsCards.tsx';
import { AgentsList } from './components/AgentsList.tsx';
import { ConversationQueue } from './components/ConversationQueue.tsx';
import { ChatInterface } from './components/ChatInterface.tsx';
import { BotAssist } from './components/BotAssist.tsx';
import { NotificationToast } from './components/NotificationToast.tsx';
import { ConnectionStatus } from './components/ConnectionStatus.tsx';
import { NotificationPermission } from './components/NotificationPermission.tsx';

export const WhatsAppDashboard: React.FC = () => {
  const [isInitializing, setIsInitializing] = React.useState(true);
  
  console.log('🎯 WhatsAppDashboard component rendering...');
  
  const {
    stats,
    agents,
    handoffs,
    activeHandoff,
    filterStatus,
    isLoadingStats,
    isLoadingAgents,
    isLoadingHandoffs,
    isSidebarOpen,
    isBotAssistOpen,
    isConnected,
    notifications,
    currentAgent,
    fetchStats,
    fetchAgents,
    fetchHandoffs,
    initializeCurrentAgent,
    setFilterStatus,
    toggleSidebar,
    removeNotification
  } = useWhatsAppStore();
  
  // Get auth token (use access_token from localStorage)
  const token = localStorage.getItem('access_token');
  
  // Initialize WebSocket connection
  const { socketId } = useSocket(
    token,
    currentAgent?.id || null
  );
  
  useEffect(() => {
    let mounted = true;
    let initialized = false; // Previne re-execução
    let pollingInterval: NodeJS.Timeout | null = null;
    let isFetching = false; // Previne requisições simultâneas
    
    const initialize = async () => {
      if (!mounted || initialized) return;
      initialized = true;
      
      try {
        console.log('🚀 Initializing WhatsApp Dashboard...');
        
        // Initial data fetch with timeout protection (15s)
        const timeout = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Initialization timeout')), 15000)
        );
        
        try {
          await Promise.race([
            Promise.all([
              initializeCurrentAgent(),
              fetchStats(),
              fetchAgents(),
              fetchHandoffs()
            ]),
            timeout
          ]);
        } catch (timeoutError) {
          console.warn('⚠️ Initialization timeout, continuing anyway:', timeoutError);
        }
        
        console.log('✅ Dashboard initialized');
      } catch (error) {
        console.error('❌ Error initializing dashboard:', error);
      } finally {
        if (mounted) {
          setIsInitializing(false);
        }
      }
    };
    
    // Debounced refresh function
    const refreshData = async () => {
      // Previne requisições simultâneas
      if (isFetching || !mounted) return;
      
      // Não fazer polling se a aba não está ativa (performance)
      if (document.hidden) {
        console.log('⏸️ Page hidden, skipping refresh');
        return;
      }
      
      isFetching = true;
      console.log('🔄 Refreshing dashboard data...');
      
      try {
        await Promise.all([
          fetchStats(),
          fetchHandoffs(filterStatus === 'all' ? undefined : filterStatus)
        ]);
      } catch (error) {
        console.error('Error refreshing data:', error);
      } finally {
        isFetching = false;
      }
    };
    
    initialize();
    
    // Refresh a cada 60 segundos (reduzido de 30s para melhor performance)
    pollingInterval = setInterval(refreshData, 60000);
    
    // Atualizar quando a aba voltar a ficar ativa
    const handleVisibilityChange = () => {
      if (!document.hidden && mounted) {
        console.log('👁️ Page visible again, refreshing data');
        refreshData();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      mounted = false;
      if (pollingInterval) clearInterval(pollingInterval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []); // IMPORTANTE: array vazio - executar apenas uma vez
  
  // Show loading spinner during initialization
  if (isInitializing) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando WhatsApp Dashboard...</p>
        </div>
      </div>
    );
  }
  
  return (
    <ErrorBoundary>
      <div className="flex h-screen bg-gray-50" role="main" aria-label="WhatsApp Dashboard">
      {/* Sidebar - Agents & Queue */}
      <div className={`
        transition-all duration-300 ease-in-out
        ${isSidebarOpen ? 'w-80' : 'w-0'}
        border-r border-gray-200 bg-white overflow-hidden
      `}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <div className="flex-1">
                <h1 className="text-lg font-semibold text-gray-900">
                  Atendimento WhatsApp
                </h1>
                <div className="mt-2">
                  <ConnectionStatus 
                    isConnected={isConnected} 
                    socketId={socketId}
                  />
                </div>
              </div>
              <button
                onClick={toggleSidebar}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                title="Recolher painel"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
              </button>
            </div>
            
            {/* Status Filter */}
            <div className="flex gap-2">
              {(['all', 'pending', 'active', 'my'] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  className={`
                    px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                    ${filterStatus === status
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }
                  `}
                >
                  {status === 'all' && 'Todas'}
                  {status === 'pending' && 'Aguardando'}
                  {status === 'active' && 'Ativas'}
                  {status === 'my' && 'Minhas'}
                </button>
              ))}
            </div>
          </div>
          
          {/* Agents List */}
          <div className="px-4 py-3 border-b border-gray-200">
            <AgentsList agents={agents} isLoading={isLoadingAgents} />
          </div>
          
          {/* Conversation Queue */}
          <div className="flex-1 overflow-y-auto">
            <ConversationQueue
              handoffs={handoffs}
              activeHandoff={activeHandoff}
              isLoading={isLoadingHandoffs}
            />
          </div>
        </div>
      </div>
      
      {/* Sidebar Toggle Button (when closed) */}
      {!isSidebarOpen && (
        <button
          onClick={toggleSidebar}
          className="absolute top-4 left-4 z-10 p-2 bg-white rounded-lg shadow-lg hover:bg-gray-50 transition-colors"
          title="Expandir painel"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        </button>
      )}
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Notification Permission Banner */}
        <div className="p-4 bg-white border-b border-gray-200">
          <NotificationPermission />
        </div>
        
        {/* Stats Cards */}
        <div className="p-4 bg-white border-b border-gray-200">
          <StatsCards stats={stats} isLoading={isLoadingStats} />
        </div>
        
        {/* Chat Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Interface */}
          <div className="flex-1">
            {activeHandoff ? (
              <ChatInterface handoff={activeHandoff} />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <p className="text-lg font-medium">Selecione uma conversa</p>
                  <p className="text-sm mt-1">Escolha uma conversa da fila para começar</p>
                </div>
              </div>
            )}
          </div>
          
          {/* Bot Assist Panel */}
          {isBotAssistOpen && (
            <div className="w-80 border-l border-gray-200 bg-white">
              <BotAssist handoff={activeHandoff} />
            </div>
          )}
        </div>
      </div>
      
      {/* Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {notifications.map((notification: any) => (
          <NotificationToast
            key={notification.id}
            notification={notification}
            onClose={() => removeNotification(notification.id)}
          />
        ))}
      </div>
    </div>
    </ErrorBoundary>
  );
};
