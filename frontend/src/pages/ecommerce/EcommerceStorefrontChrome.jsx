import { formatCurrency, resolveMediaUrl } from "./ecommerceMvpUtils";

function CartIcon({ size = 17 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="9" cy="21" r="1" />
      <circle cx="20" cy="21" r="1" />
      <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#9ca3af"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)" }}
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function HeartIcon({ active }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill={active ? "#f97316" : "none"}
      stroke={active ? "#f97316" : "currentColor"}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  );
}

function PhoneIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#fff"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
      <line x1="12" y1="18" x2="12.01" y2="18" />
    </svg>
  );
}

function HomeIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

function BoxIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  );
}

function StoreTopbar({ cart, cartTotal, styles: S }) {
  const cartCount = cart?.itens?.length || 0;

  return (
    <div style={S.topbar}>
      <div style={S.topbarInner}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <CartIcon size={13} />
          <span>{cartCount > 0 ? `${cartCount} item(ns) no carrinho` : "Carrinho vazio"}</span>
        </div>
        <span>
          {cartCount > 0 ? `${formatCurrency(cartTotal)} →` : "Frete grátis acima de R$ 199"}
        </span>
      </div>
    </div>
  );
}

function StoreHeader({
  cart,
  customerDisplayName,
  isMobile,
  search,
  storeDisplayName,
  styles: S,
  tenantContext,
  wishlist,
  onNavigate,
  onSearchChange,
}) {
  const cartCount = cart?.itens?.length || 0;
  const hasWishlist = wishlist.length > 0;

  return (
    <div style={S.header}>
      <div style={S.headerInner}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={S.logo} onClick={() => onNavigate("loja")}>
            <span style={{ fontSize: 42, lineHeight: 1, flexShrink: 0 }}>🐾</span>
            <div>
              <div style={{ fontSize: 18, fontWeight: 800, color: "#1c1917", lineHeight: 1.1 }}>
                {storeDisplayName}
              </div>
              {(tenantContext?.cidade || tenantContext?.uf) && (
                <div style={{ fontSize: 11, color: "#a8a29e", fontWeight: 400, marginTop: 1 }}>
                  📍 {tenantContext?.cidade || ""}
                  {tenantContext?.uf ? ` - ${tenantContext.uf}` : ""}
                </div>
              )}
            </div>
          </div>
        </div>

        <div
          style={{ flex: 1, maxWidth: 440, display: isMobile ? "none" : "flex" }}
          className="eco-search-wrap"
        >
          <div style={{ position: "relative", width: "100%" }}>
            <SearchIcon />
            <input
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Buscar produtos para o seu pet..."
              style={{ ...S.formInput, paddingLeft: 36, borderRadius: 24, fontSize: 13 }}
            />
          </div>
        </div>

        <div style={S.headerActions}>
          <button
            onClick={() => onNavigate("conta")}
            style={S.headerWishBtn}
            title={`Lista de desejos${hasWishlist ? ` (${wishlist.length})` : ""}`}
          >
            <HeartIcon active={hasWishlist} />
          </button>
          {customerDisplayName ? (
            <button onClick={() => onNavigate("conta")} style={S.avatarBtn}>
              <span
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  background: "#f97316",
                  color: "#fff",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 10,
                  fontWeight: 800,
                }}
              >
                {customerDisplayName.charAt(0).toUpperCase()}
              </span>
              {customerDisplayName.split(" ")[0]}
            </button>
          ) : (
            <button
              onClick={() => onNavigate("conta")}
              style={{ ...S.loginBtn, gap: 6, padding: isMobile ? "7px 10px" : "7px 16px" }}
            >
              <UserIcon />
              {!isMobile && "Entrar"}
            </button>
          )}
          <button
            onClick={() => onNavigate("carrinho")}
            style={{ ...S.cartBtn, padding: isMobile ? "0 12px" : "0 18px" }}
          >
            <CartIcon />
            {isMobile
              ? cartCount > 0
                ? `(${cartCount})`
                : ""
              : `Carrinho${cartCount > 0 ? ` (${cartCount})` : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
}

function StoreBanner({
  activeBanners,
  bannerSlide,
  isMobile,
  styles: S,
  onBannerSlideChange,
  onNavigate,
}) {
  return (
    <div style={{ padding: "16px 20px 0", boxSizing: "border-box" }}>
      <div
        style={{
          ...S.bannerWrap,
          borderRadius: isMobile ? 12 : 16,
          maxWidth: 1280,
          margin: "0 auto",
          height: isMobile ? 180 : 260,
        }}
      >
        {activeBanners.map((banner, index) => (
          <div
            key={index}
            style={{
              position: "absolute",
              inset: 0,
              opacity: bannerSlide === index ? 1 : 0,
              transition: "opacity 0.8s ease",
              pointerEvents: bannerSlide === index ? "auto" : "none",
            }}
          >
            {banner.type === "image" ? (
              <img
                src={resolveMediaUrl(banner.url)}
                alt={`Banner ${index + 1}`}
                style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
              />
            ) : (
              <div
                style={{
                  background: banner.bg,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "0 48px",
                  gap: 24,
                  height: "100%",
                }}
              >
                <span
                  style={{
                    fontSize: 72,
                    flexShrink: 0,
                    filter: "drop-shadow(0 4px 12px rgba(0,0,0,0.25))",
                  }}
                >
                  {banner.emoji}
                </span>
                <div>
                  <div
                    style={{
                      color: "#fff",
                      fontWeight: 800,
                      fontSize: 34,
                      lineHeight: 1.2,
                      textShadow: "0 2px 12px rgba(0,0,0,0.2)",
                    }}
                  >
                    {banner.title}
                  </div>
                  <div style={{ color: "rgba(255,255,255,0.88)", fontSize: 16, marginTop: 8 }}>
                    {banner.sub}
                  </div>
                  <button
                    onClick={() => onNavigate("loja")}
                    style={{
                      marginTop: 16,
                      background: "#fff",
                      color: "#f97316",
                      border: "none",
                      borderRadius: 24,
                      padding: "10px 24px",
                      fontWeight: 700,
                      fontSize: 14,
                      cursor: "pointer",
                    }}
                  >
                    Ver produtos →
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        <div style={S.bannerDots}>
          {activeBanners.map((_, index) => (
            <button
              key={index}
              onClick={() => onBannerSlideChange(index)}
              style={S.bannerDot(bannerSlide === index)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function StoreAppBar({ styles: S }) {
  return (
    <div style={S.appBar}>
      <div style={S.appBarInner}>
        <span
          style={{
            background: "#16a34a",
            borderRadius: 8,
            width: 28,
            height: 28,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <PhoneIcon />
        </span>
        Baixe nosso <strong>APP</strong> para notificações de pedidos, promoções e aviso de
        reposição de estoque.
      </div>
    </div>
  );
}

function StoreNavTabs({ cart, isMobile, styles: S, view, onNavigate }) {
  const navItems = [
    { id: "loja", label: "Loja", icon: <HomeIcon /> },
    {
      id: "carrinho",
      label: cart?.itens?.length ? `Carrinho (${cart.itens.length})` : "Carrinho",
      icon: <CartIcon size={15} />,
    },
    { id: "pedidos", label: "Pedidos", icon: <BoxIcon /> },
    { id: "conta", label: "Conta", icon: <UserIcon /> },
  ];

  return (
    <div style={{ ...S.navWrap, overflowX: isMobile ? "auto" : "visible" }}>
      <div style={S.navInner}>
        {navItems.map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => onNavigate(id)}
            style={{ ...S.navTab(view === id), display: "flex", alignItems: "center", gap: 5 }}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function EcommerceStorefrontChrome({
  activeBanners,
  bannerSlide,
  cart,
  cartTotal,
  customerDisplayName,
  isMobile,
  search,
  storeDisplayName,
  styles: S,
  tenantContext,
  view,
  wishlist,
  onBannerSlideChange,
  onNavigate,
  onSearchChange,
}) {
  const isStoreView = view === "loja";

  return (
    <>
      <StoreTopbar cart={cart} cartTotal={cartTotal} styles={S} />
      <StoreHeader
        cart={cart}
        customerDisplayName={customerDisplayName}
        isMobile={isMobile}
        search={search}
        storeDisplayName={storeDisplayName}
        styles={S}
        tenantContext={tenantContext}
        wishlist={wishlist}
        onNavigate={onNavigate}
        onSearchChange={onSearchChange}
      />
      {isStoreView && (
        <StoreBanner
          activeBanners={activeBanners}
          bannerSlide={bannerSlide}
          isMobile={isMobile}
          styles={S}
          onBannerSlideChange={onBannerSlideChange}
          onNavigate={onNavigate}
        />
      )}
      {isStoreView && !isMobile && <StoreAppBar styles={S} />}
      <StoreNavTabs
        cart={cart}
        isMobile={isMobile}
        styles={S}
        view={view}
        onNavigate={onNavigate}
      />
    </>
  );
}
