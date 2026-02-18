import React from 'react';

/**
 * Componente de Abas (Tabs) Responsivo
 * 
 * Uso:
 * <ResponsiveTabs
 *   tabs={[
 *     { id: 'dados', label: '📋 Dados', count: null },
 *     { id: 'imagens', label: '🖼️ Imagens', count: 5 },
 *     { id: 'config', label: '⚙️ Configurações', count: null }
 *   ]}
 *   activeTab="dados"
 *   onChange={(tabId) => setActiveTab(tabId)}
 * />
 */
const ResponsiveTabs = ({ 
  tabs = [], 
  activeTab, 
  onChange,
  className = ''
}) => {
  return (
    <div className={`border-b border-gray-200 mb-4 md:mb-6 ${className}`}>
      <nav 
        className="flex space-x-4 md:space-x-8 overflow-x-auto overflow-y-hidden -mb-px scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent"
        style={{
          scrollbarWidth: 'thin',
          WebkitOverflowScrolling: 'touch'
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`
              py-3 md:py-4 px-3 md:px-1 
              border-b-2 
              font-medium 
              text-xs md:text-sm 
              transition 
              whitespace-nowrap
              flex-shrink-0
              flex items-center gap-1.5
              ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <span className="hidden sm:inline">{tab.label}</span>
            <span className="sm:hidden">{tab.label.replace(/[📋🖼️⚙️🏭📦🔹]/g, '').trim()}</span>
            {tab.count !== null && tab.count !== undefined && (
              <span className="ml-1 px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>
  );
};

/**
 * Container para conteúdo das abas
 */
export const TabContent = ({ children, className = '' }) => {
  return (
    <div className={`animate-fade-in ${className}`}>
      {children}
    </div>
  );
};

export default ResponsiveTabs;
