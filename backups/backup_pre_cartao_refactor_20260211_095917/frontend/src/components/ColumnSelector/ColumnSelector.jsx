import React, { useState } from 'react';
import { Settings2, GripVertical, Lock, RotateCcw, Eye, EyeOff } from 'lucide-react';
import './ColumnSelector.css';

/**
 * Componente para personalizar colunas da listagem
 * 
 * Funcionalidades:
 * - Mostrar/ocultar colunas (exceto locked)
 * - Reordenar colunas via drag & drop
 * - Reset para padrão
 * - Interface simples e intuitiva
 * 
 * @param {Array} columns - Array de colunas
 * @param {Function} onToggle - Callback para alternar visibilidade
 * @param {Function} onReorder - Callback para reordenar
 * @param {Function} onReset - Callback para resetar
 */
const ColumnSelector = ({ columns, onToggle, onReorder, onReset }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState(null);

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    
    if (draggedIndex === null || draggedIndex === index) {
      return;
    }

    // Reordenar temporariamente para feedback visual
    onReorder(draggedIndex, index);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const toggleOpen = () => {
    setIsOpen(!isOpen);
  };

  const closePopover = () => {
    setIsOpen(false);
  };

  // Contar colunas visíveis e customizáveis
  const visibleCount = columns.filter(c => c.visible).length;
  const customizableCount = columns.filter(c => !c.locked).length;

  return (
    <div className="column-selector">
      <button
        onClick={toggleOpen}
        className="column-selector-trigger"
        title="Personalizar Colunas"
      >
        <Settings2 size={16} />
        <span>Colunas ({visibleCount})</span>
      </button>

      {isOpen && (
        <>
          <div className="column-selector-backdrop" onClick={closePopover} />
          <div className="column-selector-popover">
            <div className="column-selector-header">
              <h3>Personalizar Colunas</h3>
              <button
                onClick={onReset}
                className="column-selector-reset"
                title="Restaurar Padrão"
              >
                <RotateCcw size={14} />
                Restaurar Padrão
              </button>
            </div>

            <div className="column-selector-info">
              {visibleCount} de {columns.length} colunas visíveis
              {customizableCount > 0 && (
                <span className="text-muted">
                  {' • '}Arraste para reordenar
                </span>
              )}
            </div>

            <div className="column-selector-list">
              {columns.map((col, index) => (
                <div
                  key={col.id}
                  className={`column-selector-item ${
                    col.locked ? 'locked' : ''
                  } ${draggedIndex === index ? 'dragging' : ''}`}
                  draggable={!col.locked}
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDragEnd={handleDragEnd}
                >
                  <div className="column-selector-item-drag">
                    {!col.locked ? (
                      <GripVertical size={16} className="drag-handle" />
                    ) : (
                      <div style={{ width: 16 }} />
                    )}
                  </div>

                  <button
                    onClick={() => !col.locked && onToggle(col.id)}
                    disabled={col.locked}
                    className="column-selector-item-toggle"
                  >
                    {col.visible ? (
                      <Eye size={16} className="icon-visible" />
                    ) : (
                      <EyeOff size={16} className="icon-hidden" />
                    )}
                  </button>

                  <span className="column-selector-item-label">{col.label}</span>

                  {col.locked && (
                    <Lock size={14} className="column-selector-item-lock" />
                  )}
                </div>
              ))}
            </div>

            <div className="column-selector-footer">
              <button onClick={closePopover} className="btn-primary">
                Fechar
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ColumnSelector;
