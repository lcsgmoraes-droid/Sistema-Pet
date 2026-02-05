import React from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import './Pagination.css';

/**
 * Componente de paginação reutilizável
 * 
 * @param {number} page - Página atual
 * @param {number} pages - Total de páginas
 * @param {number} total - Total de registros
 * @param {number} pageSize - Tamanho da página
 * @param {Function} onPageChange - Callback ao mudar página
 * @param {Function} onNextPage - Callback próxima página
 * @param {Function} onPreviousPage - Callback página anterior
 */
const Pagination = ({
  page,
  pages,
  total,
  pageSize,
  onPageChange,
  onNextPage,
  onPreviousPage,
}) => {
  if (pages <= 1) return null;

  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  // Gerar array de páginas para exibir
  const getPageNumbers = () => {
    const delta = 2; // Páginas antes e depois da atual
    const range = [];
    const rangeWithDots = [];

    for (
      let i = Math.max(2, page - delta);
      i <= Math.min(pages - 1, page + delta);
      i++
    ) {
      range.push(i);
    }

    if (page - delta > 2) {
      rangeWithDots.push(1, '...');
    } else {
      rangeWithDots.push(1);
    }

    rangeWithDots.push(...range);

    if (page + delta < pages - 1) {
      rangeWithDots.push('...', pages);
    } else if (pages > 1) {
      rangeWithDots.push(pages);
    }

    return rangeWithDots;
  };

  const pageNumbers = getPageNumbers();

  return (
    <div className="pagination-container">
      <div className="pagination-info">
        Mostrando <strong>{startItem}</strong> a <strong>{endItem}</strong> de{' '}
        <strong>{total}</strong> produtos
      </div>

      <div className="pagination-controls">
        {/* Primeira página */}
        <button
          onClick={() => onPageChange(1)}
          disabled={page === 1}
          className="pagination-btn"
          title="Primeira página"
        >
          <ChevronsLeft size={16} />
        </button>

        {/* Página anterior */}
        <button
          onClick={onPreviousPage}
          disabled={page === 1}
          className="pagination-btn"
          title="Página anterior"
        >
          <ChevronLeft size={16} />
        </button>

        {/* Números das páginas */}
        {pageNumbers.map((num, idx) => {
          if (num === '...') {
            return (
              <span key={`dots-${idx}`} className="pagination-dots">
                ...
              </span>
            );
          }

          return (
            <button
              key={num}
              onClick={() => onPageChange(num)}
              className={`pagination-btn ${
                page === num ? 'pagination-btn-active' : ''
              }`}
            >
              {num}
            </button>
          );
        })}

        {/* Próxima página */}
        <button
          onClick={onNextPage}
          disabled={page === pages}
          className="pagination-btn"
          title="Próxima página"
        >
          <ChevronRight size={16} />
        </button>

        {/* Última página */}
        <button
          onClick={() => onPageChange(pages)}
          disabled={page === pages}
          className="pagination-btn"
          title="Última página"
        >
          <ChevronsRight size={16} />
        </button>
      </div>
    </div>
  );
};

export default Pagination;
