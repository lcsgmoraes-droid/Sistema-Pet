import {
  Bell,
  Heart,
  Home,
  Mail,
  MapPin,
  Package,
  Search,
  ShoppingBag,
  ShoppingCart,
  Smartphone,
  UserRound,
} from 'lucide-react';
import { formatCurrency, resolveMediaUrl } from './ecommerceMvpUtils';

const NAV_ITEMS = [
  { id: 'loja', label: 'Loja', icon: Home },
  { id: 'carrinho', label: 'Carrinho', icon: ShoppingCart },
  { id: 'pedidos', label: 'Pedidos', icon: Package },
  { id: 'conta', label: 'Conta', icon: UserRound },
];

function StoreTopbar({ cart, cartTotal, styles: S }) {
  const itemCount = Array.isArray(cart?.itens) ? cart.itens.length : 0;

  return (
    <div style={S.topbar}>
      <div style={S.topbarInner}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShoppingCart size={13} />
          <span>{itemCount > 0 ? `${itemCount} item(ns) no carrinho` : 'Carrinho vazio'}</span>
        </div>
        <span>{itemCount > 0 ? `${formatCurrency(cartTotal)} >` : 'Frete gratis acima de R$ 199'}</span>
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
  wishlistCount,
  onSearchChange,
  onViewChange,
}) {
  const itemCount = Array.isArray(cart?.itens) ? cart.itens.length : 0;

  return (
    <div style={S.header}>
      <div style={S.headerInner}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={S.logo} onClick={() => onViewChange('loja')}>
            <span style={{ fontSize: 42, lineHeight: 1, flexShrink: 0 }}>🐾</span>
            <div>
              <div style={{ fontSize: 18, fontWeight: 800, color: '#1c1917', lineHeight: 1.1 }}>{storeDisplayName}</div>
              {(tenantContext?.cidade || tenantContext?.uf) && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#a8a29e', fontWeight: 400, marginTop: 1 }}>
                  <MapPin size={11} />
                  {tenantContext?.cidade || ''}{tenantContext?.uf ? ` - ${tenantContext.uf}` : ''}
                </div>
              )}
            </div>
          </div>
        </div>

        <div style={{ flex: 1, maxWidth: 440, display: isMobile ? 'none' : 'flex' }} className="eco-search-wrap">
          <div style={{ position: 'relative', width: '100%' }}>
            <Search size={15} color="#9ca3af" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
            <input
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Buscar produtos para o seu pet..."
              style={{ ...S.formInput, paddingLeft: 36, borderRadius: 24, fontSize: 13 }}
            />
          </div>
        </div>

        <div style={S.headerActions}>
          <button onClick={() => onViewChange('conta')} style={S.headerWishBtn} title={`Lista de desejos${wishlistCount > 0 ? ` (${wishlistCount})` : ''}`}>
            <Heart size={20} fill={wishlistCount > 0 ? '#f97316' : 'none'} color={wishlistCount > 0 ? '#f97316' : 'currentColor'} />
          </button>

          {customerDisplayName ? (
            <button onClick={() => onViewChange('conta')} style={S.avatarBtn}>
              <span style={{ width: 22, height: 22, borderRadius: '50%', background: '#f97316', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800 }}>{customerDisplayName.charAt(0).toUpperCase()}</span>
              {customerDisplayName.split(' ')[0]}
            </button>
          ) : (
            <button onClick={() => onViewChange('conta')} style={{ ...S.loginBtn, gap: 6, padding: isMobile ? '7px 10px' : '7px 16px' }}>
              <UserRound size={15} />
              {!isMobile && 'Entrar'}
            </button>
          )}

          <button onClick={() => onViewChange('carrinho')} style={{ ...S.cartBtn, padding: isMobile ? '0 12px' : '0 18px' }}>
            <ShoppingCart size={17} />
            {isMobile ? (itemCount > 0 ? `(${itemCount})` : '') : `Carrinho${itemCount > 0 ? ` (${itemCount})` : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}

function StoreBanner({ activeBanners, bannerSlide, isMobile, styles: S, onBannerSlideChange, onViewChange }) {
  if (!activeBanners?.length) return null;

  return (
    <div style={{ padding: '16px 20px 0', boxSizing: 'border-box' }}>
      <div style={{ ...S.bannerWrap, borderRadius: isMobile ? 12 : 16, maxWidth: 1280, margin: '0 auto', height: isMobile ? 180 : 260 }}>
        {activeBanners.map((banner, index) => (
          <div key={index} style={{ position: 'absolute', inset: 0, opacity: bannerSlide === index ? 1 : 0, transition: 'opacity 0.8s ease', pointerEvents: bannerSlide === index ? 'auto' : 'none' }}>
            {banner.type === 'image' ? (
              <img src={resolveMediaUrl(banner.url)} alt={`Banner ${index + 1}`} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
            ) : (
              <div style={{ background: banner.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 48px', gap: 24, height: '100%' }}>
                <span style={{ fontSize: 72, flexShrink: 0, filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.25))' }}>{banner.emoji}</span>
                <div>
                  <div style={{ color: '#fff', fontWeight: 800, fontSize: 34, lineHeight: 1.2, textShadow: '0 2px 12px rgba(0,0,0,0.2)' }}>{banner.title}</div>
                  <div style={{ color: 'rgba(255,255,255,0.88)', fontSize: 16, marginTop: 8 }}>{banner.sub}</div>
                  <button onClick={() => onViewChange('loja')} style={{ marginTop: 16, background: '#fff', color: '#f97316', border: 'none', borderRadius: 24, padding: '10px 24px', fontWeight: 700, fontSize: 14, cursor: 'pointer' }}>
                    Ver produtos
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        <div style={S.bannerDots}>
          {activeBanners.map((_, index) => (
            <button key={index} onClick={() => onBannerSlideChange(index)} style={S.bannerDot(bannerSlide === index)} />
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
        <span style={{ background: '#16a34a', borderRadius: 8, width: 28, height: 28, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Smartphone size={14} color="#fff" />
        </span>
        Baixe nosso <strong>APP</strong> para notificacoes de pedidos, promocoes e aviso de reposicao de estoque.
      </div>
    </div>
  );
}

function StoreNav({ cart, isMobile, styles: S, view, onViewChange }) {
  const itemCount = Array.isArray(cart?.itens) ? cart.itens.length : 0;

  return (
    <div style={{ ...S.navWrap, overflowX: isMobile ? 'auto' : 'visible' }}>
      <div style={S.navInner}>
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
          const navLabel = id === 'carrinho' && itemCount > 0 ? `${label} (${itemCount})` : label;

          return (
            <button key={id} onClick={() => onViewChange(id)} style={{ ...S.navTab(view === id), display: 'flex', alignItems: 'center', gap: 5 }}>
              <Icon size={15} />
              {navLabel}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function TenantWarning({ tenantRef }) {
  if (tenantRef) return null;

  return (
    <div style={{ background: '#fef2f2', color: '#991b1b', padding: '10px 20px', fontSize: 13, borderBottom: '1px solid #fecaca' }}>
      Use a URL no formato: /slug-da-loja
    </div>
  );
}

function StoreAlerts({ error, success, styles: S }) {
  if (!error && !success) return null;

  return (
    <div style={{ padding: '0 20px' }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        {error && <div style={S.alertError}>{error}</div>}
        {success && <div style={S.alertSuccess}>{success}</div>}
      </div>
    </div>
  );
}

function NotifyMeModal({ modal, styles: S, onClose, onEmailChange, onSubmit }) {
  if (!modal?.open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
      onClick={onClose}
    >
      <div
        style={{ background: '#fff', borderRadius: 18, padding: 28, maxWidth: 380, width: '100%', boxShadow: '0 24px 80px rgba(0,0,0,0.25)', border: '1px solid #e5e7eb' }}
        onClick={(event) => event.stopPropagation()}
      >
        <Bell size={32} color="#f97316" style={{ marginBottom: 8 }} />
        <h3 style={{ margin: '0 0 8px', fontSize: 18, fontWeight: 800, color: '#1c1917' }}>Avise-me quando chegar</h3>
        <p style={{ margin: '0 0 18px', fontSize: 14, color: '#6b7280' }}>
          <strong>{modal.product?.nome}</strong> esta sem estoque agora. Informe seu email e te avisamos quando voltar.
        </p>
        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input type="email" required placeholder="seu@email.com" value={modal.email} autoFocus onChange={(event) => onEmailChange(event.target.value)} style={S.formInput} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, padding: '10px 0', borderRadius: 10, border: '1.5px solid #e5e7eb', background: '#fff', color: '#374151', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>Cancelar</button>
            <button type="submit" disabled={modal.loading} style={{ flex: 2, padding: '10px 0', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer', opacity: modal.loading ? 0.7 : 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 7 }}>
              <Bell size={14} />
              {modal.loading ? 'Registrando...' : 'Me avise'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StoreFooter({ styles: S, tenantContext, onViewChange }) {
  const storeName = tenantContext?.nome_fantasia || tenantContext?.nome || 'Pet Store';

  return (
    <footer style={S.footer}>
      <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 28 }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontWeight: 800, fontSize: 20, color: '#fff', marginBottom: 8 }}>
            <ShoppingBag size={20} />
            {storeName}
          </div>
          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
            Produtos de qualidade para o seu pet com carinho e dedicacao. Compre online com facilidade.
          </div>
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.85)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Navegacao</div>
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => onViewChange(id)} style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: 'rgba(255,255,255,0.65)', fontSize: 13, cursor: 'pointer', padding: '3px 0', textAlign: 'left' }}>
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.85)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Contato</div>
          {tenantContext?.whatsapp && (
            <a href={`https://wa.me/55${tenantContext.whatsapp.replace(/\D/g, '')}`} target="_blank" rel="noreferrer" style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'rgba(255,255,255,0.65)', fontSize: 13, textDecoration: 'none', marginBottom: 4 }}>
              <Smartphone size={13} />
              WhatsApp
            </a>
          )}
          {tenantContext?.email && (
            <a href={`mailto:${tenantContext.email}`} style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'rgba(255,255,255,0.65)', fontSize: 13, textDecoration: 'none' }}>
              <Mail size={13} />
              {tenantContext.email}
            </a>
          )}
          {tenantContext?.cidade && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'rgba(255,255,255,0.5)', fontSize: 12, marginTop: 8 }}>
              <MapPin size={12} />
              {tenantContext.cidade}{tenantContext.uf ? `, ${tenantContext.uf}` : ''}
            </div>
          )}
        </div>
      </div>
      <div style={{ maxWidth: 1100, margin: '20px auto 0', paddingTop: 16, borderTop: '1px solid rgba(255,255,255,0.1)', fontSize: 12, color: 'rgba(255,255,255,0.4)', textAlign: 'center' }}>
        © {new Date().getFullYear()} {storeName}. Todos os direitos reservados.
      </div>
    </footer>
  );
}

export default function EcommerceStorefrontShell({
  activeBanners,
  bannerSlide,
  cart,
  cartTotal,
  children,
  customerDisplayName,
  error,
  isMobile,
  notifyMeModal,
  search,
  storeDisplayName,
  styles: S,
  success,
  tenantContext,
  tenantRef,
  view,
  wishlistCount,
  onBannerSlideChange,
  onNotifyMeClose,
  onNotifyMeEmailChange,
  onNotifyMeSubmit,
  onSearchChange,
  onViewChange,
}) {
  return (
    <div style={S.page}>
      <StoreTopbar cart={cart} cartTotal={cartTotal} styles={S} />
      <StoreHeader
        cart={cart}
        customerDisplayName={customerDisplayName}
        isMobile={isMobile}
        search={search}
        storeDisplayName={storeDisplayName}
        styles={S}
        tenantContext={tenantContext}
        wishlistCount={wishlistCount}
        onSearchChange={onSearchChange}
        onViewChange={onViewChange}
      />

      {view === 'loja' && (
        <StoreBanner
          activeBanners={activeBanners}
          bannerSlide={bannerSlide}
          isMobile={isMobile}
          styles={S}
          onBannerSlideChange={onBannerSlideChange}
          onViewChange={onViewChange}
        />
      )}

      {view === 'loja' && !isMobile && <StoreAppBar styles={S} />}

      <StoreNav cart={cart} isMobile={isMobile} styles={S} view={view} onViewChange={onViewChange} />
      <TenantWarning tenantRef={tenantRef} />
      <StoreAlerts error={error} success={success} styles={S} />

      {children}

      <NotifyMeModal
        modal={notifyMeModal}
        styles={S}
        onClose={onNotifyMeClose}
        onEmailChange={onNotifyMeEmailChange}
        onSubmit={onNotifyMeSubmit}
      />
      <StoreFooter styles={S} tenantContext={tenantContext} onViewChange={onViewChange} />
    </div>
  );
}
