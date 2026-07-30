import { RefreshCw, Search, SlidersHorizontal, X } from "lucide-react";
import CurrencyInput from "../../components/CurrencyInput";

const ORDER_OPTIONS = [
  { value: "relevancia", label: "Mais relevantes" },
  { value: "nome_asc", label: "Nome A-Z" },
  { value: "menor_preco", label: "Menor preço" },
  { value: "maior_preco", label: "Maior preço" },
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
        Catálogo da loja
      </h2>
      <p style={{ margin: "5px 0 0", color: "#78716c", fontSize: 13 }}>{productCountText}</p>
    </div>
  );
}

export default function EcommerceCatalogControls({
  categories,
  category,
  brands = [],
  brand = "",
  onlyInStock = false,
  onlyWithImage = false,
  minPrice = "",
  maxPrice = "",
  isMobile,
  loading,
  order,
  search,
  styles: S,
  onCategoryChange,
  onBrandChange,
  onOnlyInStockChange,
  onOnlyWithImageChange,
  onMinPriceChange,
  onMaxPriceChange,
  onClearFilters,
  onOrderChange,
  onRefresh,
  onSearchChange,
}) {
  const hasActiveFilters =
    order !== "relevancia" ||
    category !== "todas" ||
    Boolean(search) ||
    Boolean(brand) ||
    Boolean(onlyInStock) ||
    Boolean(onlyWithImage) ||
    Number(minPrice) > 0 ||
    Number(maxPrice) > 0;
  const groupedCategories = categories
    .filter((item) => (item.value || item) !== "todas")
    .reduce((groups, item) => {
      const group = item.group || "Outros";
      if (!groups[group]) groups[group] = [];
      groups[group].push(item);
      return groups;
    }, {});
  const selectStyle = {
    ...S.formInput,
    width: "100%",
    minWidth: 0,
    maxWidth: "100%",
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
          gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(170px, 1fr))",
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
            id="ecommerce-catalog-search"
            name="catalog_search"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Buscar por nome, SKU ou código de barras"
            style={{ ...S.formInput, paddingLeft: 36, background: "#fff" }}
          />
        </div>

        <select
          id="ecommerce-catalog-category"
          name="catalog_category"
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          style={selectStyle}
        >
          <option value="todas">Todas as categorias e subcategorias</option>
          {Object.entries(groupedCategories).map(([group, items]) => (
            <optgroup key={group} label={group}>
              {group !== "Outros" && items.length > 1 && (
                <option value={`grupo:${encodeURIComponent(group)}`}>
                  Todos em {group} ({items.reduce((total, item) => total + (item.total || 0), 0)})
                </option>
              )}
              {items.map((item) => (
                <option key={item.value || item} value={item.value || item}>
                  {item.label || item} ({item.total || 0})
                </option>
              ))}
            </optgroup>
          ))}
        </select>

        <select
          id="ecommerce-catalog-brand"
          name="catalog_brand"
          value={brand}
          onChange={(event) => onBrandChange(event.target.value)}
          style={selectStyle}
        >
          <option value="">Todas as marcas</option>
          {brands.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>

        <select
          id="ecommerce-catalog-order"
          name="catalog_order"
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
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: isMobile ? "1fr 1fr" : "auto auto 150px 150px 1fr",
          gap: 10,
          alignItems: "end",
        }}
      >
        {[
          ["Somente em estoque", onlyInStock, onOnlyInStockChange],
          ["Somente com imagem", onlyWithImage, onOnlyWithImageChange],
        ].map(([label, checked, onChange]) => (
          <label
            key={label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 7,
              minHeight: 40,
              fontSize: 12,
              fontWeight: 700,
              color: "#57534e",
            }}
          >
            <input
              name={label === "Somente em estoque" ? "only_in_stock" : "only_with_image"}
              type="checkbox"
              checked={checked}
              onChange={(event) => onChange(event.target.checked)}
            />
            {label}
          </label>
        ))}

        <label style={{ fontSize: 11, fontWeight: 700, color: "#78716c" }}>
          Preço mínimo
          <CurrencyInput
            id="ecommerce-catalog-min-price"
            name="catalog_min_price"
            value={minPrice}
            onChange={onMinPriceChange}
            aria-label="Preço mínimo"
            style={{ ...S.formInput, marginTop: 4, background: "#fff" }}
          />
        </label>
        <label style={{ fontSize: 11, fontWeight: 700, color: "#78716c" }}>
          Preço máximo
          <CurrencyInput
            id="ecommerce-catalog-max-price"
            name="catalog_max_price"
            value={maxPrice}
            onChange={onMaxPriceChange}
            aria-label="Preço máximo"
            style={{ ...S.formInput, marginTop: 4, background: "#fff" }}
          />
        </label>

        <div
          style={{
            display: "flex",
            gap: 8,
            justifyContent: isMobile ? "stretch" : "flex-end",
            gridColumn: isMobile ? "1 / -1" : "auto",
          }}
        >
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
