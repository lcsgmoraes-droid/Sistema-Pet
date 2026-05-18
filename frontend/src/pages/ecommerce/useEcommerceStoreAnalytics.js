import { useEffect, useRef } from 'react';
import {
  trackPageView,
  trackViewItem,
  trackAddToCart,
  trackBeginCheckout,
  trackPurchase,
  trackViewCart,
} from '../../services/analytics';

export function useEcommerceStoreAnalytics({ view, cart }) {
  const cartRef = useRef(cart);

  useEffect(() => {
    cartRef.current = cart;
  }, [cart]);

  useEffect(() => {
    trackPageView(view);
    if (view === 'carrinho') trackViewCart(cartRef.current);
  }, [view]);

  return {
    trackProductView: trackViewItem,
    trackProductAdded: trackAddToCart,
    trackCheckoutStarted: () => trackBeginCheckout(cart),
    trackCheckoutCompleted: (result) => trackPurchase(result, cart),
  };
}
