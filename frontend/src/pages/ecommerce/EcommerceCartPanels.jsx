import { Lock, Package, ShoppingCart, Trash2 } from 'lucide-react';
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
      <div style={{ flex: '1 1 0%', minWidth: 0, maxWidth: '100%', overflow: 'hidden' }}>
        <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1a1a2e', maxWidth: '100%' }}>
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

function CartPageItem({ item, productMap, styles: S, onUpdateItem }) {
  const product = productMap[item.produto_id];
  const image = product ? getProductImages(product)[0] : null;

  return (
    <div style={S.cartItem}>
      <div style={S.cartItemImg}>
        {image ? (
          <img src={image} alt={item.nome} style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 4 }} />
        ) : (
          <Package size={28} color="#a8a29e" />
        )}
      </div>
      <div style={{ flex: 1, minWidth: 0, display: 'grid', gap: 4 }}>
        <div style={{ fontWeight: 700, fontSize: 14, lineHeight: 1.3, color: '#1a1a2e' }}>{item.nome}</div>
        <div style={{ fontSize: 13, color: '#f97316', fontWeight: 700 }}>{formatCurrency(item.preco_unitario)} / un</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
          <button onClick={() => onUpdateItem(item.item_id, item.quantidade - 1)} style={S.qtyBtn} aria-label={`Reduzir quantidade de ${item.nome}`}>-</button>
          <span style={{ fontWeight: 700, fontSize: 14, minWidth: 26, textAlign: 'center' }}>{item.quantidade}</span>
          <button onClick={() => onUpdateItem(item.item_id, item.quantidade + 1)} style={S.qtyBtn} aria-label={`Aumentar quantidade de ${item.nome}`}>+</button>
          <button onClick={() => onUpdateItem(item.item_id, 0)} style={{ ...S.removeBtn, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <Trash2 size={13} />
            Remover
          </button>
        </div>
      </div>
      <div style={{ fontWeight: 800, fontSize: 16, color: '#1a1a2e', flexShrink: 0 }}>
        {formatCurrency(item.preco_unitario * item.quantidade)}
      </div>
    </div>
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
        <div style={{ display: 'grid', gap: 8, width: '100%', minWidth: 0, maxWidth: '100%', overflow: 'hidden' }}>
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

export function EcommerceCartPage({
  cart,
  cartLoading,
  cartTotal,
  cupom,
  cupomResult,
  isMobile,
  productMap,
  styles: S,
  onApplyCoupon,
  onCheckout,
  onContinueShopping,
  onCouponChange,
  onUpdateItem,
}) {
  const items = Array.isArray(cart?.itens) ? cart.itens : [];
  const itemCount = items.length;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '28px 16px', minHeight: 200 }}>
      <h2 style={{ margin: '0 0 20px', fontSize: 26, fontWeight: 800, color: '#1c1917' }}>
        Carrinho ({itemCount} {itemCount === 1 ? 'item' : 'itens'})
      </h2>

      {cartLoading ? (
        <div style={{ textAlign: 'center', color: '#64748b', padding: 40 }}>Carregando carrinho...</div>
      ) : itemCount ? (
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'minmax(0, 1fr)' : 'minmax(0, 1fr) 340px', gap: 20, alignItems: 'start' }}>
          <div style={{ display: 'grid', gap: 12 }}>
            {items.map((item) => (
              <CartPageItem key={item.item_id} item={item} productMap={productMap} styles={S} onUpdateItem={onUpdateItem} />
            ))}

            <form onSubmit={onApplyCoupon} style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: 8, marginTop: 4 }}>
              <input value={cupom} onChange={(event) => onCouponChange(event.target.value)} placeholder="Codigo de cupom" style={{ ...S.formInput, flex: 1 }} />
              <button type="submit" style={{ background: '#f1f5f9', border: '1.5px solid #e5e7eb', color: '#374151', borderRadius: 10, padding: '0 18px', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
                Aplicar
              </button>
            </form>

            {cupomResult && (
              <div style={{ fontSize: 13, color: '#065f46', background: '#ecfdf5', borderRadius: 8, padding: '8px 12px', fontWeight: 600 }}>
                Cupom {cupomResult.codigo}: -{formatCurrency(cupomResult.desconto)}
              </div>
            )}
          </div>

          <EcommerceCartOrderSummary
            cart={cart}
            cartTotal={cartTotal}
            styles={S}
            onCheckout={onCheckout}
            onContinueShopping={onContinueShopping}
          />
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '48px 0', display: 'grid', gap: 12, justifyItems: 'center' }}>
          <ShoppingCart size={52} color="#d6d3d1" />
          <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a2e' }}>{'Seu carrinho est\u00e1 vazio'}</div>
          <div style={{ fontSize: 14, color: '#9ca3af' }}>Explore nossa loja e adicione produtos!</div>
          <button onClick={onContinueShopping} style={{ ...S.checkoutBig, width: 'auto', padding: '12px 28px' }}>Ver produtos</button>
        </div>
      )}
    </div>
  );
}
