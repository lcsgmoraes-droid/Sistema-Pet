import { Bell, Heart, ImageOff, ShoppingCart } from 'lucide-react';
import {
  formatCatalogCategoryLabel,
  formatCurrency,
  getProductImages,
  hasPromotionalPrice,
  isProductOutOfStock,
  resolveOriginalProductPrice,
  resolveProductPrice,
  resolveValidityPromotionText,
} from './ecommerceMvpUtils';

export default function EcommerceCatalogProductCard({
  product,
  isHovered,
  wished,
  styles: S,
  onAddToCart,
  onHover,
  onNotifyMe,
  onOpen,
  onToggleWishlist,
}) {
  const outOfStock = isProductOutOfStock(product);
  const productImage = getProductImages(product)[0];
  const categoryLabel = formatCatalogCategoryLabel(product?.categoria_nome || product?.categoria || 'Sem categoria');

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onOpen(product)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onOpen(product);
        }
      }}
      onMouseEnter={() => onHover(product.id)}
      onMouseLeave={() => onHover(null)}
      style={S.card(isHovered)}
    >
      <div style={S.cardImgWrap}>
        {productImage ? (
          <img
            src={productImage}
            alt={product.nome}
            style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 12, background: '#fff' }}
          />
        ) : (
          <div style={{ color: '#d1d5db', fontSize: 12, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            <ImageOff size={28} strokeWidth={1.5} />
            <span>Sem imagem</span>
          </div>
        )}

        {outOfStock ? (
          <div style={S.unavailBadge}>{'Indispon\u00edvel'}</div>
        ) : null}

        <button
          aria-label={wished ? 'Remover da lista de desejos' : 'Adicionar a lista de desejos'}
          aria-pressed={wished}
          onClick={(event) => {
            event.stopPropagation();
            onToggleWishlist(product.id);
          }}
          title={wished ? 'Remover da lista de desejos' : 'Adicionar \u00e0 lista de desejos'}
          style={{ ...S.wishBtn, color: wished ? '#dc2626' : '#78716c' }}
        >
          <Heart size={16} fill={wished ? 'currentColor' : 'none'} />
        </button>
      </div>

      <div style={S.cardBody}>
        <div style={S.cardName}>{product.nome}</div>
        <div style={S.cardCat}>{categoryLabel}</div>
        <div style={S.cardSku}>SKU: {product?.codigo || '-'}</div>
        <div style={S.cardPrice}>{formatCurrency(resolveProductPrice(product))}</div>

        {hasPromotionalPrice(product) && (
          <div style={{ fontSize: 12, color: '#94a3b8', textDecoration: 'line-through', marginTop: 2 }}>
            {formatCurrency(resolveOriginalProductPrice(product))}
          </div>
        )}

        {resolveValidityPromotionText(product) && (
          <div style={{ marginTop: 6, fontSize: 11, fontWeight: 700, color: '#166534', lineHeight: 1.35 }}>
            {resolveValidityPromotionText(product)}
          </div>
        )}

        <button
          disabled={outOfStock}
          style={{ ...S.addBtn(outOfStock), display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
          onClick={(event) => {
            event.stopPropagation();
            onAddToCart(product);
          }}
        >
          {!outOfStock && <ShoppingCart size={15} />}
          {outOfStock ? 'Indispon\u00edvel' : 'Adicionar'}
        </button>

        {outOfStock && (
          <button
            onClick={(event) => {
              event.stopPropagation();
              onNotifyMe(product);
            }}
            style={{ ...S.notifyBtn, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
          >
            <Bell size={14} />
            Avise-me quando chegar
          </button>
        )}
      </div>
    </div>
  );
}
