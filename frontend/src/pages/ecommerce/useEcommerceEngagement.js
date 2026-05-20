import { useEffect, useState } from 'react';
import ecommerceApi from '../../services/ecommerceApi';
import { STORAGE_NOTIFY_KEY, STORAGE_WISHLIST_KEY } from './ecommerceMvpUtils';

export default function useEcommerceEngagement({
  customer,
  loginEmail,
  registerEmail,
  storefrontRef,
  tenantContext,
  tenantRef,
  onError,
  onSuccess,
}) {
  const [wishlist, setWishlist] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_WISHLIST_KEY) || '[]');
    } catch {
      return [];
    }
  });
  const [notifyRequests, setNotifyRequests] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_NOTIFY_KEY) || '[]');
    } catch {
      return [];
    }
  });
  const [notifyMeModal, setNotifyMeModal] = useState({ open: false, product: null, email: '', loading: false });

  useEffect(() => {
    localStorage.setItem(STORAGE_WISHLIST_KEY, JSON.stringify(wishlist));
  }, [wishlist]);

  useEffect(() => {
    localStorage.setItem(STORAGE_NOTIFY_KEY, JSON.stringify(notifyRequests));
  }, [notifyRequests]);

  function toggleWishlist(productId) {
    setWishlist((prev) => {
      if (prev.includes(productId)) {
        onSuccess('Produto removido da sua lista de desejos.');
        return prev.filter((id) => id !== productId);
      }
      onSuccess('Produto adicionado \u00e0 sua lista de desejos.');
      return [...prev, productId];
    });
  }

  function registerNotifyMe(product) {
    const fallbackEmail = customer?.email || registerEmail || loginEmail || '';
    setNotifyMeModal({ open: true, product, email: fallbackEmail, loading: false });
  }

  async function submitNotifyMe(event) {
    event.preventDefault();
    const { product, email } = notifyMeModal;
    if (!email.trim() || !product) return;

    setNotifyMeModal((prev) => ({ ...prev, loading: true }));
    const tenantParam = tenantContext?.id || storefrontRef || tenantRef;
    try {
      await ecommerceApi.post('/api/ecommerce-notify/registrar', {
        email: email.trim(),
        product_id: product.id,
        product_name: product.nome,
        tenant_id: tenantParam,
      });
      setNotifyMeModal({ open: false, product: null, email: '', loading: false });
      onSuccess('Perfeito! Te avisaremos por e-mail quando o produto voltar ao estoque. \u{1F4E7}');
      setNotifyRequests((prev) => {
        const exists = prev.some(
          (item) => item.productId === product.id && String(item.email || '').toLowerCase() === email.trim().toLowerCase()
        );
        if (exists) return prev;
        return [...prev, { productId: product.id, productName: product.nome, email: email.trim(), createdAt: new Date().toISOString() }];
      });
    } catch {
      setNotifyMeModal((prev) => ({ ...prev, loading: false }));
      onError('N\u00e3o foi poss\u00edvel registrar o aviso. Tente novamente.');
    }
  }

  return {
    wishlist,
    notifyRequests,
    notifyMeModal,
    setNotifyMeModal,
    toggleWishlist,
    registerNotifyMe,
    submitNotifyMe,
  };
}
