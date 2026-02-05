import { useState, useCallback, useMemo } from 'react';
import { COLUNAS_DISPONIVEIS } from '../constants/produtosColumns';

/**
 * Hook para gerenciar preferências de colunas da listagem de produtos
 * 
 * ESTRATÉGIA DE PERSISTÊNCIA:
 * - NÃO salva o schema completo das colunas
 * - Salva apenas: { order: string[], hidden: string[] }
 * - No load, faz MERGE com COLUNAS_DISPONIVEIS
 * 
 * BENEFÍCIOS:
 * - Novas colunas aparecem automaticamente
 * - Preferências do usuário são respeitadas
 * - Evolução do sistema sem quebrar clientes
 * - Reset fácil para padrão
 * 
 * @param {number} userId - ID do usuário logado
 * @returns {object} { columns, visibleColumns, savePreferences, resetToDefault, toggleColumn, reorderColumns }
 */
export const useColumnPreferences = (userId) => {
  const [columns, setColumns] = useState(() => {
    // Tentar carregar preferências salvas
    const saved = localStorage.getItem(`produtos_columns_${userId}`);
    
    if (!saved) {
      return COLUNAS_DISPONIVEIS;
    }
    
    try {
      const preferences = JSON.parse(saved);
      
      // Proteger contra colunas removidas do schema oficial
      const validIds = COLUNAS_DISPONIVEIS.map(c => c.id);
      const cleanedOrder = preferences.order?.filter(id => validIds.includes(id)) || [];
      const cleanedHidden = preferences.hidden?.filter(id => validIds.includes(id)) || [];
      
      // MERGE: schema oficial + preferências do usuário
      return COLUNAS_DISPONIVEIS.map(col => {
        // Se coluna é locked, sempre visível
        if (col.locked) {
          return col;
        }
        
        // Aplicar ordem customizada
        const userOrderIndex = cleanedOrder.indexOf(col.id);
        const order = userOrderIndex >= 0 ? userOrderIndex : col.order;
        
        // Aplicar visibilidade customizada
        const isHidden = cleanedHidden.includes(col.id);
        const visible = !isHidden;
        
        return {
          ...col,
          order,
          visible,
        };
      }).sort((a, b) => a.order - b.order);
      
    } catch (error) {
      console.error('Erro ao carregar preferências de colunas:', error);
      return COLUNAS_DISPONIVEIS;
    }
  });

  // Colunas visíveis ordenadas (memoized)
  const visibleColumns = useMemo(
    () => columns.filter(c => c.visible).sort((a, b) => a.order - b.order),
    [columns]
  );

  /**
   * Salva preferências no localStorage
   * Persiste apenas order e hidden, não o schema completo
   */
  const savePreferences = useCallback((newColumns) => {
    const preferences = {
      order: newColumns
        .filter(c => !c.locked)
        .sort((a, b) => a.order - b.order)
        .map(c => c.id),
      hidden: newColumns
        .filter(c => !c.locked && !c.visible)
        .map(c => c.id),
    };
    
    localStorage.setItem(
      `produtos_columns_${userId}`,
      JSON.stringify(preferences)
    );
    
    setColumns(newColumns);
  }, [userId]);

  /**
   * Reseta preferências para padrão
   */
  const resetToDefault = useCallback(() => {
    localStorage.removeItem(`produtos_columns_${userId}`);
    setColumns(COLUNAS_DISPONIVEIS);
  }, [userId]);

  /**
   * Alterna visibilidade de uma coluna
   */
  const toggleColumn = useCallback((columnId) => {
    const updated = columns.map(col =>
      col.id === columnId && !col.locked
        ? { ...col, visible: !col.visible }
        : col
    );
    savePreferences(updated);
  }, [columns, savePreferences]);

  /**
   * Reordena colunas (drag & drop)
   * @param {number} sourceIndex - Índice original
   * @param {number} destinationIndex - Índice destino
   */
  const reorderColumns = useCallback((sourceIndex, destinationIndex) => {
    const reordered = Array.from(columns);
    const [moved] = reordered.splice(sourceIndex, 1);
    reordered.splice(destinationIndex, 0, moved);
    
    // Recalcular orders
    const updated = reordered.map((col, idx) => ({ ...col, order: idx }));
    
    savePreferences(updated);
  }, [columns, savePreferences]);

  return {
    columns,
    visibleColumns,
    savePreferences,
    resetToDefault,
    toggleColumn,
    reorderColumns,
  };
};
