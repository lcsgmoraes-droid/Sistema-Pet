import React from 'react';

/**
 * Componente para exibir dados em formato de card em dispositivos móveis
 * Ideal para substituir tabelas em telas pequenas
 * 
 * Uso:
 * <MobileCard 
 *   title="Nome do Cliente"
 *   items={[
 *     { label: 'Email', value: 'email@exemplo.com' },
 *     { label: 'Telefone', value: '(11) 99999-9999' },
 *   ]}
 *   actions={<button>Editar</button>}
 * />
 */
const MobileCard = ({ 
  title, 
  subtitle, 
  items = [], 
  actions, 
  onClick,
  className = '' 
}) => {
  return (
    <div 
      className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-3 ${
        onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''
      } ${className}`}
      onClick={onClick}
    >
      {/* Header */}
      {(title || subtitle) && (
        <div className="mb-3 pb-3 border-b border-gray-100">
          {title && (
            <h3 className="font-semibold text-gray-900 text-base">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">
              {subtitle}
            </p>
          )}
        </div>
      )}
      
      {/* Items */}
      {items.length > 0 && (
        <div className="space-y-2">
          {items.map((item, index) => (
            <div key={index} className="flex justify-between items-start">
              <span className="text-sm text-gray-600 font-medium">
                {item.label}:
              </span>
              <span className="text-sm text-gray-900 text-right max-w-[60%]">
                {item.value}
              </span>
            </div>
          ))}
        </div>
      )}
      
      {/* Actions */}
      {actions && (
        <div className="mt-4 pt-3 border-t border-gray-100 flex gap-2 flex-wrap">
          {actions}
        </div>
      )}
    </div>
  );
};

export default MobileCard;
