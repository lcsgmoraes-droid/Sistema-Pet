import { RefreshCw, Search, X } from 'lucide-react';

const CATALOG_METRICS = [
  {
    key: 'prontos',
    label: 'Prontos para vender',
    color: '#16a34a',
    border: '#bbf7d0',
    bg: '#f0fdf4',
  },
  {
    key: 'emEstoque',
    label: 'Com estoque',
    color: '#2563eb',
    border: '#bfdbfe',
    bg: '#eff6ff',
  },
  {
    key: 'comImagem',
    label: 'Com foto',
    color: '#ea580c',
    border: '#fed7aa',
    bg: '#fff7ed',
  },
];

export function EcommerceCatalogSummary({
  catalogMetrics,
  isMobile,
  productCount,
}) {
  const productCountText = `${productCount} produto${productCount !== 1 ? 's' : ''} encontrado${productCount !== 1 ? 's' : ''}`;

  return (
    <>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: isMobile ? '16px 12px 0' : '24px 20px 0' }}>
        <h2 style={{ margin: 0, fontSize: isMobile ? 18 : 22, fontWeight: 800, color: '#1c1917' }}>
          {'Cat\u00e1logo da loja'}
        </h2>
        <p style={{ margin: '4px 0 0', color: '#9ca3af', fontSize: 13 }}>{productCountText}</p>
      </div>

      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 20px' }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 14 }}>
          {CATALOG_METRICS.map((item) => (
            <div
              key={item.key}
              style={{
                minWidth: isMobile ? 'calc(50% - 8px)' : 180,
                background: item.bg,
                color: item.color,
                border: `1px solid ${item.border}`,
                borderRadius: 14,
                padding: '10px 14px',
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4 }}>{item.label}</div>
              <div style={{ fontSize: 20, fontWeight: 800, marginTop: 2 }}>{catalogMetrics[item.key]}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

export default function EcommerceCatalogControls({
  categories,
  category,
  isMobile,
  loading,
  order,
  search,
  showOnlyInStock,
  showOnlyWithImage,
  styles: S,
  onCategoryChange,
  onClearFilters,
  onImageFilterChange,
  onOrderChange,
  onRefresh,
  onSearchChange,
  onStockFilterChange,
}) {
  const hasActiveFilters = showOnlyInStock || showOnlyWithImage || order !== 'prontos' || category !== 'todas' || search;

  return (
    <div style={{ display: 'grid', gap: 14, marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', flexDirection: isMobile ? 'column' : 'row' }}>
          <div style={{ flex: 1, minWidth: 220, position: 'relative' }}>
            <Search
              size={14}
              color="#9ca3af"
              strokeWidth={2}
              style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }}
            />
            <input
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="O que seu pet precisa?"
              style={{ ...S.formInput, paddingLeft: 36 }}
            />
          </div>

          <select value={category} onChange={(event) => onCategoryChange(event.target.value)} style={{ ...S.formInput, width: 'auto', paddingRight: 30 }}>
            {categories.map((item) => (
              <option key={item} value={item}>{item === 'todas' ? 'Todas as categorias' : item}</option>
            ))}
          </select>

          <select value={order} onChange={(event) => onOrderChange(event.target.value)} style={{ ...S.formInput, width: 'auto', minWidth: 190, paddingRight: 30 }}>
            <option value="prontos">Mais prontos para vender</option>
            <option value="nome">{'Ordem alfab\u00e9tica'}</option>
            <option value="menor_preco">{'Menor pre\u00e7o'}</option>
            <option value="maior_preco">{'Maior pre\u00e7o'}</option>
          </select>

          <button
            onClick={onRefresh}
            disabled={loading}
            style={{
              padding: '10px 16px',
              border: '1.5px solid #e7e5e4',
              borderRadius: 9,
              fontSize: 13,
              fontWeight: 600,
              background: '#fff',
              color: '#f97316',
              cursor: loading ? 'wait' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <RefreshCw size={14} />
            {loading ? 'Atualizando' : 'Atualizar'}
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[
            { label: 'Somente com estoque', active: showOnlyInStock, onClick: onStockFilterChange },
            { label: 'Somente com foto', active: showOnlyWithImage, onClick: onImageFilterChange },
          ].map((item) => (
            <button
              key={item.label}
              onClick={item.onClick}
              aria-pressed={item.active}
              style={{
                padding: '8px 14px',
                borderRadius: 999,
                border: item.active ? '1.5px solid #16a34a' : '1.5px solid #e7e5e4',
                background: item.active ? '#f0fdf4' : '#fff',
                color: item.active ? '#166534' : '#57534e',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {item.label}
            </button>
          ))}

          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              style={{
                padding: '8px 14px',
                borderRadius: 999,
                border: '1.5px solid #fed7aa',
                background: '#fff7ed',
                color: '#c2410c',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
              }}
            >
              <X size={13} />
              Limpar filtros
            </button>
          )}
        </div>

        {categories.length > 2 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'space-between' }}>
            {categories.map((item) => (
              <button
                key={item}
                onClick={() => onCategoryChange(item)}
                style={{
                  flex: '1 1 auto',
                  textAlign: 'center',
                  padding: '6px 14px',
                  borderRadius: 20,
                  border: category === item ? '1.5px solid #f97316' : '1.5px solid #e7e5e4',
                  background: category === item ? '#fff7ed' : '#fff',
                  color: category === item ? '#ea580c' : '#78716c',
                  fontWeight: category === item ? 700 : 500,
                  fontSize: 12,
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {item === 'todas' ? 'Todas' : item}
              </button>
            ))}
          </div>
        )}
    </div>
  );
}
