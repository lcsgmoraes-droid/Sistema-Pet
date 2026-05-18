import { Lock, Package, ShoppingCart } from 'lucide-react';
import { formatCurrency, getProductImages } from './ecommerceMvpUtils';

function MiniCartItem({ item, productMap, styles: S }) {
  const product = productMap[item.produto_id];
  const image = product ? getProductImages(product)[0] : null;

  return (
    <div style={S.miniItem}>
      <div style={S.miniImg}>
        {image ? (
          <img src={image} alt={item.nome} style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 2 }} />
        ) : (
          <Package size={16} color="#a8a29e" />
        )}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1a1a2e' }}>
          {item.nome}
        </div>
        <div style={{ fontSize: 11, color: '#f97316', fontWeight: 600 }}>
          {item.quantidade}x {formatCurrency(item.preco_unitario)}
        </div>
      </div>
    </div>
  );
}

function CartSummaryRows({ items }) {
  return (
    <>
      {items.map((item) => (
        <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13, color: '#6b7280', marginBottom: 6 }}>
          <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {item.nome} x {item.quantidade}
          </span>
          <span style={{ flexShrink: 0 }}>{formatCurrency(item.preco_unitario * item.quantidade)}</span>
        </div>
      ))}
    </>
  );
}

export function EcommerceCartSidebar({
  cart,
  cartTotal,
  customerToken,
  isMobile,
  productMap,
  styles: S,
  onCheckout,
  onViewCart,
}) {
  const items = Array.isArray(cart?.itens) ? cart.itens : [];

  return (
    <aside style={{ ...S.sidebar, display: isMobile ? 'none' : 'block' }}>
      <div style={S.sidebarTitle}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
          <ShoppingCart size={16} />
          Seu carrinho
        </span>
        {items.length > 0 && <span style={S.sidebarBadge}>{items.length}</span>}
      </div>

      {items.length ? (
        <div style={{ display: 'grid', gap: 8 }}>
          {items.slice(0, 5).map((item) => (
            <MiniCartItem key={item.item_id} item={item} productMap={productMap} styles={S} />
          ))}

          {items.length > 5 && (
            <div style={{ fontSize: 12, color: '#9ca3af', textAlign: 'center' }}>
              + {items.length - 5} item(ns) a mais
            </div>
          )}

          <div style={S.subtotalBox}>
            <span style={{ fontWeight: 600, fontSize: 14, color: '#374151' }}>Subtotal</span>
            <span style={{ fontWeight: 800, fontSize: 17, color: '#1a1a2e' }}>{formatCurrency(cartTotal)}</span>
          </div>

          <button style={S.checkoutBig} onClick={onCheckout}>
            Finalizar compra -&gt;
          </button>
          <button style={S.viewCartBtn} onClick={onViewCart}>Ver / Editar carrinho</button>

          {!customerToken && (
            <div style={{ fontSize: 11, color: '#9ca3af', textAlign: 'center', display: 'inline-flex', justifyContent: 'center', alignItems: 'center', gap: 5 }}>
              <Lock size={12} />
              Login solicitado apenas no fechamento
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: '#c4c4d4', textAlign: 'center', padding: '28px 0', fontSize: 13 }}>
          <ShoppingCart size={34} color="#d6d3d1" style={{ marginBottom: 8 }} />
          <div style={{ fontWeight: 600, color: '#9ca3af' }}>Carrinho vazio</div>
          <div style={{ fontSize: 12, marginTop: 4 }}>{'Adicione produtos para come\u00e7ar'}</div>
        </div>
      )}
    </aside>
  );
}

export function EcommerceCartOrderSummary({
  cart,
  cartTotal,
  styles: S,
  onCheckout,
  onContinueShopping,
}) {
  const items = Array.isArray(cart?.itens) ? cart.itens : [];

  return (
    <div style={{ background: '#fff', border: '1px solid #e7e5e4', borderRadius: 16, padding: 20, boxShadow: '0 2px 12px rgba(0,0,0,0.06)' }}>
      <div style={{ fontWeight: 700, fontSize: 16, color: '#1c1917', marginBottom: 14 }}>Resumo do pedido</div>
      <CartSummaryRows items={items} />
      <div style={S.cartTotalRow}>
        <span>Total</span>
        <span>{formatCurrency(cartTotal)}</span>
      </div>
      <button onClick={onCheckout} style={{ ...S.checkoutBig, width: '100%', marginTop: 14 }}>
        Ir para o checkout -&gt;
      </button>
      <button onClick={onContinueShopping} style={{ width: '100%', marginTop: 8, background: 'transparent', border: '1.5px solid #e5e7eb', color: '#6b7280', borderRadius: 10, padding: '10px 0', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
        Continuar comprando
      </button>
    </div>
  );
}
