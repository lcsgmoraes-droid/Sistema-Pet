import { ChevronLeft, ChevronRight } from 'lucide-react';

export default function EcommerceCatalogPagination({
  isMobile,
  loading,
  pagination,
  onPageChange,
}) {
  if (!pagination || pagination.totalPages <= 0) return null;

  const buttonBase = {
    minWidth: 38,
    height: 38,
    borderRadius: 10,
    border: '1.5px solid #e7e5e4',
    background: '#fff',
    color: '#57534e',
    fontWeight: 800,
    cursor: loading ? 'wait' : 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  };

  return (
    <div
      style={{
        marginTop: 18,
        padding: '12px 14px',
        background: '#fff',
        border: '1px solid #e7e5e4',
        borderRadius: 14,
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        alignItems: isMobile ? 'stretch' : 'center',
        justifyContent: 'space-between',
        gap: 12,
      }}
    >
      <div style={{ color: '#78716c', fontSize: 13, fontWeight: 700 }}>
        Mostrando {pagination.startItem}-{pagination.endItem} de {pagination.total}
      </div>

      {pagination.totalPages > 1 && (
        <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', justifyContent: isMobile ? 'space-between' : 'flex-end' }}>
          <button
            disabled={!pagination.hasPrevious || loading}
            onClick={() => onPageChange(pagination.page - 1)}
            style={{
              ...buttonBase,
              padding: '0 12px',
              opacity: !pagination.hasPrevious ? 0.5 : 1,
              flex: isMobile ? '1 1 auto' : '0 0 auto',
            }}
          >
            <ChevronLeft size={16} />
            Anterior
          </button>

          {pagination.pages.map((item) => (
            <button
              key={item}
              disabled={loading}
              onClick={() => onPageChange(item)}
              aria-current={item === pagination.page ? 'page' : undefined}
              style={{
                ...buttonBase,
                background: item === pagination.page ? '#f97316' : '#fff',
                borderColor: item === pagination.page ? '#f97316' : '#e7e5e4',
                color: item === pagination.page ? '#fff' : '#57534e',
              }}
            >
              {item}
            </button>
          ))}

          <button
            disabled={!pagination.hasNext || loading}
            onClick={() => onPageChange(pagination.page + 1)}
            style={{
              ...buttonBase,
              padding: '0 12px',
              opacity: !pagination.hasNext ? 0.5 : 1,
              flex: isMobile ? '1 1 auto' : '0 0 auto',
            }}
          >
            Proxima
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
