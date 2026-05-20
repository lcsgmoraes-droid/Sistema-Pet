import { useEffect, useState } from 'react';
import ecommerceApi from '../../services/ecommerceApi';
import { STORAGE_ORDERS_KEY, extractApiErrorMessage } from './ecommerceMvpUtils';

export default function useEcommerceOrders({ authHeaders, customerToken, view, onError }) {
  const [orderIds, setOrderIds] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_ORDERS_KEY) || '[]');
    } catch {
      return [];
    }
  });
  const [ordersDetailed, setOrdersDetailed] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);

  function persistOrderIds(ids) {
    setOrderIds(ids);
    localStorage.setItem(STORAGE_ORDERS_KEY, JSON.stringify(ids));
  }

  async function loadOrdersDetailed() {
    if (!customerToken) return;
    setOrdersLoading(true);
    try {
      const response = await ecommerceApi.get('/api/checkout/pedidos', {
        headers: authHeaders,
        params: { limit: 20 },
      });
      const pedidos = Array.isArray(response?.data?.pedidos) ? response.data.pedidos : [];
      setOrdersDetailed(pedidos);

      if (pedidos.length) {
        const ids = pedidos.map((pedido) => pedido?.pedido_id).filter(Boolean);
        persistOrderIds(Array.from(new Set([...ids, ...orderIds])));
      }
    } catch (err) {
      setOrdersDetailed([]);
      onError(extractApiErrorMessage(err, 'Erro ao carregar detalhes dos pedidos'));
    } finally {
      setOrdersLoading(false);
    }
  }

  async function recordOrderId(orderId) {
    if (!orderId) return;
    persistOrderIds(Array.from(new Set([orderId, ...orderIds])));
    await loadOrdersDetailed();
  }

  useEffect(() => {
    if (!customerToken || view !== 'pedidos') return;
    loadOrdersDetailed();
  }, [view, customerToken]);

  async function avisarCheguei(pedidoId) {
    try {
      await ecommerceApi.post(`/api/checkout/pedido/${pedidoId}/drive-cheguei`, {}, { headers: authHeaders });
      await loadOrdersDetailed();
    } catch (err) {
      onError(extractApiErrorMessage(err, 'Erro ao avisar chegada'));
    }
  }

  return {
    ordersDetailed,
    ordersLoading,
    loadOrdersDetailed,
    avisarCheguei,
    recordOrderId,
  };
}
