import { useEffect, useState } from 'react';
import { trackAddToCart } from '../../services/analytics';
import ecommerceApi from '../../services/ecommerceApi';
import {
  EMPTY_CART,
  STORAGE_GUEST_CART_KEY,
  extractApiErrorMessage,
  getGuestCart,
  recalculateGuestCart,
  resolveProductPrice,
  resolveProductStock,
  resolveValidityPromotionLimit,
} from './ecommerceMvpUtils';

export default function useEcommerceCart({ authHeaders, customerToken, productMap, onError, onSuccess }) {
  const [cart, setCart] = useState(() => getGuestCart());
  const [cartLoading, setCartLoading] = useState(false);
  const cartTotal = Number(cart?.total || 0);

  useEffect(() => {
    if (!customerToken) {
      localStorage.setItem(STORAGE_GUEST_CART_KEY, JSON.stringify(cart || EMPTY_CART));
    }
  }, [cart, customerToken]);

  function clearCart() {
    setCart({ ...EMPTY_CART });
  }

  function restoreGuestCart() {
    setCart(getGuestCart());
  }

  async function loadCart(customHeaders = authHeaders) {
    if (!customHeaders?.Authorization) return;
    setCartLoading(true);
    try {
      const response = await ecommerceApi.get('/api/carrinho', { headers: customHeaders });
      setCart(response.data || { ...EMPTY_CART });
    } catch (err) {
      onError(extractApiErrorMessage(err, 'Erro ao carregar carrinho'));
    } finally {
      setCartLoading(false);
    }
  }

  async function syncGuestCartToServer(token) {
    const guestCart = getGuestCart();
    if (!guestCart?.itens?.length) return;

    const headers = { Authorization: `Bearer ${token}` };

    for (const item of guestCart.itens) {
      await ecommerceApi.post(
        '/api/carrinho/adicionar',
        {
          produto_id: item.produto_id,
          quantidade: item.quantidade,
        },
        { headers }
      );
    }

    await loadCart(headers);
    localStorage.removeItem(STORAGE_GUEST_CART_KEY);
  }

  async function addToCart(product) {
    const availableStock = resolveProductStock(product);
    if (availableStock <= 0) {
      onError('Produto indispon\u00edvel no momento. Volto em breve.');
      return;
    }

    if (!customerToken) {
      const limiteValidade = resolveValidityPromotionLimit(product);
      const quantidadeAtual = Array.isArray(cart?.itens)
        ? Number(cart.itens.find((item) => item.produto_id === product.id)?.quantidade || 0)
        : 0;
      if (limiteValidade && quantidadeAtual + 1 > limiteValidade) {
        onError(`Oferta de validade disponivel para ate ${limiteValidade} unidade(s) nesse preco.`);
        return;
      }
      onError('');
      const price = resolveProductPrice(product);
      setCart((previousCart) => {
        const currentItems = Array.isArray(previousCart?.itens) ? previousCart.itens : [];
        const existing = currentItems.find((item) => item.produto_id === product.id);

        const nextItems = existing
          ? currentItems.map((item) =>
              item.produto_id === product.id
                ? { ...item, quantidade: Number(item.quantidade || 0) + 1 }
                : item
            )
          : [
              ...currentItems,
              {
                item_id: `guest-${product.id}`,
                produto_id: product.id,
                nome: product.nome,
                preco_unitario: price,
                quantidade: 1,
              },
            ];

        return recalculateGuestCart(nextItems);
      });
      onSuccess('Produto adicionado ao carrinho. Fa\u00e7a login no checkout para finalizar.');
      trackAddToCart(product);
      return;
    }

    onError('');
    try {
      const response = await ecommerceApi.post(
        '/api/carrinho/adicionar',
        { produto_id: product.id, quantidade: 1 },
        { headers: authHeaders }
      );
      setCart(response.data);
      onSuccess('Produto adicionado ao carrinho.');
      trackAddToCart(product);
    } catch (err) {
      onError(extractApiErrorMessage(err, 'Erro ao adicionar no carrinho'));
    }
  }

  async function updateCartItem(itemId, quantidade) {
    if (!customerToken) {
      const itemAtual = Array.isArray(cart?.itens)
        ? cart.itens.find((item) => item.item_id === itemId)
        : null;
      const produtoAtual = itemAtual ? productMap[itemAtual.produto_id] : null;
      const limiteValidade = resolveValidityPromotionLimit(produtoAtual);
      if (limiteValidade && quantidade > limiteValidade) {
        onError(`Oferta de validade disponivel para ate ${limiteValidade} unidade(s) nesse preco.`);
        return;
      }
      setCart((previousCart) => {
        const currentItems = Array.isArray(previousCart?.itens) ? previousCart.itens : [];

        if (quantidade <= 0) {
          const nextItems = currentItems.filter((item) => item.item_id !== itemId);
          return recalculateGuestCart(nextItems);
        }

        const nextItems = currentItems.map((item) =>
          item.item_id === itemId ? { ...item, quantidade } : item
        );
        return recalculateGuestCart(nextItems);
      });
      return;
    }
    onError('');
    try {
      const itemAtual = Array.isArray(cart?.itens)
        ? cart.itens.find((item) => item.item_id === itemId)
        : null;
      const produtoId = itemAtual?.produto_id || itemId;

      if (quantidade <= 0) {
        const response = await ecommerceApi.delete(`/api/carrinho/remover/${produtoId}`, { headers: authHeaders });
        setCart(response.data);
        return;
      }
      const response = await ecommerceApi.put(
        '/api/carrinho/atualizar',
        { produto_id: produtoId, quantidade },
        { headers: authHeaders }
      );
      setCart(response.data);
    } catch (err) {
      onError(extractApiErrorMessage(err, 'Erro ao atualizar carrinho'));
    }
  }

  return {
    cart,
    cartLoading,
    cartTotal,
    addToCart,
    clearCart,
    loadCart,
    restoreGuestCart,
    syncGuestCartToServer,
    updateCartItem,
  };
}
