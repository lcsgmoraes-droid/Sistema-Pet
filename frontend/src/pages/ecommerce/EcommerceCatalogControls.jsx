import { RefreshCw, Search, SlidersHorizontal, X } from "lucide-react";

const ORDER_OPTIONS = [
  { value: "relevancia", label: "Mais relevantes" },
  { value: "nome_asc", label: "Nome A-Z" },
  { value: "menor_preco", label: "Menor preco" },
  { value: "maior_preco", label: "Maior preco" },
];

export function EcommerceCatalogSummary({ isMobile, productCount }) {
  const productCountText = `${productCount} produto${productCount !== 1 ? "s" : ""} encontrado${productCount !== 1 ? "s" : ""}`;

  return (
    <div
      style={{
        maxWidth: 1280,
        margin: "0 auto",
        padding: isMobile ? "16px 12px 0" : "24px 20px 0",
      }}
    >
      <h2 style={{ margin: 0, fontSize: isMobile ? 20 : 24, fontWeight: 800, color: "#1c1917" }}>
        Catalogo da loja
      </h2>
      <p style={{ margin: "5px 0 0", color: "#78716c", fontSize: 13 }}>{productCountText}</p>
    </div>
  );
}

export default function EcommerceCatalogControls({
  categories,
  category,
  isMobile,
  loading,
  order,
  search,
  styles: S,
  onCategoryChange,
  onClearFilters,
  onOrderChange,
  onRefresh,
  onSearchChange,
}) {
  const hasActiveFilters = order !== "relevancia" || category !== "todas" || Boolean(search);
  const selectStyle = {
    ...S.formInput,
    width: isMobile ? "100%" : "auto",
    minWidth: isMobile ? "100%" : 220,
    paddingRight: 30,
    background: "#fff",
  };

  return (
    <div
      style={{
        display: "grid",
        gap: 12,
        marginBottom: 18,
        padding: isMobile ? 12 : 14,
        background: "#fff",
        border: "1px solid #e7e5e4",
        borderRadius: 14,
        boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          color: "#78716c",
          fontSize: 12,
          fontWeight: 800,
          textTransform: "uppercase",
        }}
      >
        <SlidersHorizontal size={15} />
        Encontrar produtos
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: isMobile
            ? "1fr"
            : "minmax(260px, 1.2fr) minmax(220px, 0.9fr) minmax(180px, 0.7fr) auto",
          gap: 10,
          alignItems: "center",
        }}
      >
        <div style={{ minWidth: 0, position: "relative" }}>
          <Search
            size={14}
            color="#9ca3af"
            strokeWidth={2}
            style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)" }}
          />
          <input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Buscar por nome, SKU ou codigo de barras"
            style={{ ...S.formInput, paddingLeft: 36, background: "#fff" }}
          />
        </div>

        <select
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          style={selectStyle}
        >
          {categories.map((item) => (
            <option key={item.value || item} value={item.value || item}>
              {item.label || (item === "todas" ? "Todas as categorias" : item)}
            </option>
          ))}
        </select>

        <select
          value={order}
          onChange={(event) => onOrderChange(event.target.value)}
          style={selectStyle}
        >
          {ORDER_OPTIONS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>

        <div style={{ display: "flex", gap: 8, justifyContent: isMobile ? "stretch" : "flex-end" }}>
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              style={{
                padding: "10px 12px",
                borderRadius: 10,
                border: "1.5px solid #fed7aa",
                background: "#fff7ed",
                color: "#c2410c",
                fontSize: 12,
                fontWeight: 800,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 5,
                flex: isMobile ? 1 : "0 0 auto",
              }}
            >
              <X size={14} />
              Limpar
            </button>
          )}

          <button
            onClick={onRefresh}
            disabled={loading}
            style={{
              padding: "10px 14px",
              border: "1.5px solid #e7e5e4",
              borderRadius: 10,
              fontSize: 12,
              fontWeight: 800,
              background: "#fff",
              color: "#f97316",
              cursor: loading ? "wait" : "pointer",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              flex: isMobile ? 1 : "0 0 auto",
            }}
          >
            <RefreshCw size={14} />
            {loading ? "Atualizando" : "Atualizar"}
          </button>
        </div>
      </div>
    </div>
  );
}
