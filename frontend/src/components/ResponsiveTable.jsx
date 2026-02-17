import React from 'react';

/**
 * Componente wrapper para tabelas responsivas em mobile
 * Adiciona scroll horizontal automático em telas pequenas
 * 
 * Uso:
 * <ResponsiveTable>
 *   <table>...</table>
 * </ResponsiveTable>
 */
const ResponsiveTable = ({ children, className = '' }) => {
  return (
    <div className={`overflow-x-auto -mx-3 md:mx-0 ${className}`}>
      <div className="inline-block min-w-full align-middle">
        <div className="overflow-hidden shadow-sm ring-1 ring-black ring-opacity-5 md:rounded-lg">
          {children}
        </div>
      </div>
    </div>
  );
};

export default ResponsiveTable;
