import { Search } from "lucide-react";
import EcommerceCatalogControls, { EcommerceCatalogSummary } from "./EcommerceCatalogControls";
import EcommerceCatalogPagination from "./EcommerceCatalogPagination";
import EcommerceCatalogProductCard from "./EcommerceCatalogProductCard";
import { EcommerceCartSidebar } from "./EcommerceCartPanels";

export default function EcommerceStorePage({
  cart,
  cartTotal,
  categories,
  category,
  customerToken,
  filteredProducts,
  hoveredCard,
  isMobile,
  loading,
  order,
  pagination,
  productMap,
  productCount,
  search,
  styles: S,
  wishlist,
  onAddToCart,
  onCategoryChange,
  onCheckout,
  onClearFilters,
  onHoverProduct,
  onOpenProduct,
  onOrderChange,
  onPageChange,
  onRefresh,
  onSearchChange,
  onToggleWishlist,
  onViewCart,
  onNotifyMe,
}) {
  return (
    <>
      <EcommerceCatalogSummary isMobile={isMobile} productCount={productCount} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: isMobile ? "1fr" : "minmax(0, 1fr) 300px",
          gap: 24,
          maxWidth: 1280,
          margin: "0 auto",
          padding: isMobile ? "12px 12px 28px" : "16px 20px 28px",
        }}
      >
        <div>
          <EcommerceCatalogControls
            categories={categories}
            category={category}
            isMobile={isMobile}
            loading={loading}
            order={order}
            search={search}
            styles={S}
            onCategoryChange={onCategoryChange}
            onClearFilters={onClearFilters}
            onOrderChange={onOrderChange}
            onRefresh={onRefresh}
            onSearchChange={onSearchChange}
          />

          <div
            style={{
              ...S.grid,
              gridTemplateColumns: isMobile
                ? "repeat(2, 1fr)"
                : "repeat(auto-fill, minmax(200px, 1fr))",
              gap: isMobile ? 10 : 16,
            }}
          >
            {filteredProducts.map((product) => (
              <EcommerceCatalogProductCard
                key={product.id}
                product={product}
                isHovered={hoveredCard === product.id}
                wished={wishlist.includes(product.id)}
                styles={S}
                onAddToCart={onAddToCart}
                onHover={onHoverProduct}
                onNotifyMe={onNotifyMe}
                onOpen={onOpenProduct}
                onToggleWishlist={onToggleWishlist}
              />
            ))}
            {!loading && filteredProducts.length === 0 && (
              <div
                style={{
                  gridColumn: "1/-1",
                  textAlign: "center",
                  padding: "60px 0",
                  color: "#9ca3af",
                }}
              >
                <Search size={44} strokeWidth={1.5} style={{ marginBottom: 12 }} />
                <div style={{ fontWeight: 800, fontSize: 18, color: "#374151" }}>
                  Nenhum produto encontrado
                </div>
                <div style={{ fontSize: 13, marginTop: 4 }}>
                  Tente buscar por outro termo ou categoria
                </div>
                <button
                  onClick={onClearFilters}
                  style={{
                    marginTop: 16,
                    padding: "8px 20px",
                    borderRadius: 20,
                    border: "1.5px solid #e7e5e4",
                    background: "#fff",
                    cursor: "pointer",
                    fontSize: 13,
                    fontWeight: 600,
                    color: "#f97316",
                  }}
                >
                  Limpar filtros
                </button>
              </div>
            )}
          </div>

          <EcommerceCatalogPagination
            isMobile={isMobile}
            loading={loading}
            pagination={pagination}
            onPageChange={onPageChange}
          />
        </div>

        <EcommerceCartSidebar
          cart={cart}
          cartTotal={cartTotal}
          customerToken={customerToken}
          isMobile={isMobile}
          productMap={productMap}
          styles={S}
          onCheckout={onCheckout}
          onViewCart={onViewCart}
        />
      </div>
    </>
  );
}
