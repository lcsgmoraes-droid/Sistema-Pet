import React from 'react';

/**
 * Grid responsivo que se adapta automaticamente ao tamanho da tela
 * 
 * Uso:
 * <ResponsiveGrid cols={2}>
 *   <div>Coluna 1</div>
 *   <div>Coluna 2</div>
 * </ResponsiveGrid>
 * 
 * Props:
 * - cols: número de colunas no desktop (1, 2, 3, 4) - padrão: 2
 * - gap: espaçamento entre elementos (sm, md, lg) - padrão: md
 * - mobileFullWidth: se true, cada item ocupa 100% da largura em mobile
 */
const ResponsiveGrid = ({ 
  children, 
  cols = 2, 
  gap = 'md',
  mobileFullWidth = true,
  className = '' 
}) => {
  const gapClasses = {
    sm: 'gap-2 md:gap-3',
    md: 'gap-3 md:gap-4',
    lg: 'gap-4 md:gap-6'
  };
  
  const colsClasses = {
    1: 'md:grid-cols-1',
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-2 lg:grid-cols-3',
    4: 'md:grid-cols-2 lg:grid-cols-4'
  };
  
  return (
    <div 
      className={`
        grid 
        ${mobileFullWidth ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2'}
        ${colsClasses[cols] || colsClasses[2]}
        ${gapClasses[gap] || gapClasses.md}
        ${className}
      `}
    >
      {children}
    </div>
  );
};

/**
 * Container de formulário responsivo
 */
export const ResponsiveForm = ({ children, onSubmit, className = '' }) => {
  return (
    <form 
      onSubmit={onSubmit}
      className={`space-y-4 md:space-y-6 ${className}`}
    >
      {children}
    </form>
  );
};

/**
 * Grupo de campos de formulário com label responsivo
 */
export const FormGroup = ({ 
  label, 
  required = false, 
  error, 
  children,
  className = '' 
}) => {
  return (
    <div className={`flex flex-col ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      {children}
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
};

/**
 * Botões responsivos para ações do formulário
 */
export const FormActions = ({ 
  children, 
  align = 'right', 
  className = '' 
}) => {
  const alignClasses = {
    left: 'justify-start',
    center: 'justify-center',
    right: 'justify-end'
  };
  
  return (
    <div 
      className={`
        flex flex-col-reverse sm:flex-row gap-2 sm:gap-3 
        ${alignClasses[align] || alignClasses.right}
        pt-4 border-t border-gray-200
        ${className}
      `}
    >
      {children}
    </div>
  );
};

export default ResponsiveGrid;
