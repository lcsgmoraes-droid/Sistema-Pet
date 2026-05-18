import { Bell, Heart, Link, Package, ShoppingCart, X } from 'lucide-react';
import {
  formatCurrency,
  getProductImages,
  hasPromotionalPrice,
  isProductOutOfStock,
  resolveOriginalProductPrice,
  resolveProductPrice,
  resolveProductStock,
  resolveValidityPromotionText,
} from './ecommerceMvpUtils';

export default function EcommerceProductDetailModal({
  activeImage,
  isMobile,
  product,
  styles: S,
  wishlist,
  onAddToCart,
  onClose,
  onCopyLink,
  onImageChange,
  onNotifyMe,
  onToggleWishlist,
  onViewCart,
}) {
  const images = getProductImages(product);
  const outOfStock = isProductOutOfStock(product);
  const stock = resolveProductStock(product);
  const wished = wishlist.includes(product.id);

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, zIndex: 60 }}
      onClick={onClose}
    >
      <div
        style={{ background: '#fff', width: 'min(960px, 100%)', maxHeight: isMobile ? '100dvh' : '90vh', overflowY: 'auto', borderRadius: isMobile ? 0 : 18, border: '1px solid #e5e7eb', boxShadow: '0 24px 80px rgba(0,0,0,0.2)', display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1.1fr 1fr', gap: 0 }}
        onClick={(event) => event.stopPropagation()}
      >
        <div style={{ background: '#f5f5f4', borderRadius: isMobile ? 0 : '18px 0 0 18px', padding: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ borderRadius: 12, background: '#fff', aspectRatio: '1/1', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e7e5e4' }}>
            {activeImage ? (
              <img src={activeImage} alt={product.nome} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
            ) : (
              <span style={{ color: '#9ca3af', fontSize: 13 }}>Sem imagem disponivel</span>
            )}
          </div>
          {images.length > 1 && (
            <div style={{ display: 'flex', gap: 8, overflowX: 'auto' }}>
              {images.map((image) => (
                <button key={image} onClick={() => onImageChange(image)} style={{ border: activeImage === image ? '2.5px solid #f97316' : '1.5px solid #e7e5e4', borderRadius: 10, width: 70, height: 70, overflow: 'hidden', padding: 0, background: '#fff', cursor: 'pointer', flexShrink: 0 }}>
                  <img src={image} alt="Miniatura" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                </button>
              ))}
            </div>
          )}
        </div>

        <div style={{ padding: 28, display: 'grid', alignContent: 'start', gap: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
            <h3 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#1c1917', lineHeight: 1.3 }}>{product.nome}</h3>
            <button onClick={onClose} style={{ background: '#f1f5f9', border: 'none', borderRadius: 8, width: 34, height: 34, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: '#6b7280' }} aria-label="Fechar detalhes do produto">
              <X size={16} />
            </button>
          </div>

          <div style={{ fontSize: 30, fontWeight: 800, color: '#1a1a2e', letterSpacing: -1 }}>
            {formatCurrency(resolveProductPrice(product))}
          </div>
          {hasPromotionalPrice(product) && (
            <div style={{ marginTop: -6, fontSize: 14, color: '#94a3b8', textDecoration: 'line-through' }}>
              {formatCurrency(resolveOriginalProductPrice(product))}
            </div>
          )}
          {resolveValidityPromotionText(product) && (
            <div style={{ marginTop: -6, fontSize: 12, fontWeight: 700, color: '#166534' }}>
              {resolveValidityPromotionText(product)}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, background: '#faf7f4', borderRadius: 10, padding: '12px 14px' }}>
            <div style={{ fontSize: 13, color: '#6b7280' }}>Categoria: <strong style={{ color: '#1a1a2e' }}>{product?.categoria_nome || product?.categoria || 'Sem categoria'}</strong></div>
            <div style={{ fontSize: 13, color: '#6b7280' }}>SKU: <strong style={{ color: '#1a1a2e', fontFamily: 'monospace' }}>{product?.codigo || '-'}</strong></div>
            <div style={{ fontSize: 13, color: outOfStock ? '#b45309' : '#065f46', display: 'inline-flex', alignItems: 'center', gap: 5 }}>
              {outOfStock ? (
                <>
                  <Package size={13} />
                  Fora de estoque
                </>
              ) : (
                `Em estoque: ${Number.isFinite(stock) ? stock : 'Disponivel'}`
              )}
            </div>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
            {!outOfStock ? (
              <button onClick={() => onAddToCart(product)} style={{ ...S.addBtn(false), width: 'auto', padding: '12px 24px', fontSize: 14, display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                <ShoppingCart size={15} />
                Adicionar ao carrinho
              </button>
            ) : (
              <button onClick={() => onNotifyMe(product)} style={{ ...S.notifyBtn, width: 'auto', padding: '10px 20px', fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                <Bell size={14} />
                Avise-me quando chegar
              </button>
            )}
            <button onClick={() => onToggleWishlist(product.id)} style={{ background: '#fff', border: '1.5px solid #f97316', color: '#f97316', borderRadius: 9, padding: '10px 16px', fontWeight: 700, fontSize: 13, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Heart size={14} fill={wished ? 'currentColor' : 'none'} />
              {wished ? 'Remover' : 'Salvar'}
            </button>
            <button onClick={onViewCart} style={{ background: '#fff', border: '1.5px solid #e5e7eb', color: '#6b7280', borderRadius: 9, padding: '10px 16px', fontWeight: 500, fontSize: 13, cursor: 'pointer' }}>
              Ver carrinho
            </button>
          </div>

          <button
            onClick={() => onCopyLink(product)}
            style={{ background: 'transparent', border: '1px solid #e5e7eb', color: '#9ca3af', borderRadius: 8, padding: '8px 12px', cursor: 'pointer', fontSize: 12, justifySelf: 'start', display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            <Link size={13} />
            Copiar link do produto
          </button>
        </div>
      </div>
    </div>
  );
}
