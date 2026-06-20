import { useCallback, useEffect, useRef, useState } from "react";
import ecommerceApi from "../../services/ecommerceApi";
import { STORAGE_ORDERS_KEY, extractApiErrorMessage } from "./ecommerceMvpUtils";

export default function useEcommerceOrders({ authHeaders, customerToken, view, onError }) {
  const [, setOrderIds] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_ORDERS_KEY) || "[]");
    } catch {
      return [];
    }
  });
  const [ordersDetailed, setOrdersDetailed] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");
  const loadingOrdersRef = useRef(false);

  const persistOrderIds = useCallback((idsOrUpdater) => {
    setOrderIds((currentIds) => {
      const ids =
        typeof idsOrUpdater === "function" ? idsOrUpdater(currentIds) : idsOrUpdater;
      const normalizedIds = Array.isArray(ids) ? ids : [];
      localStorage.setItem(STORAGE_ORDERS_KEY, JSON.stringify(normalizedIds));
      return normalizedIds;
    });
  }, []);

  const loadOrdersDetailed = useCallback(async () => {
    if (!customerToken) return;
    if (loadingOrdersRef.current) return;
    loadingOrdersRef.current = true;
    setOrdersLoading(true);
    setOrdersError("");
    try {
      const response = await ecommerceApi.get("/api/checkout/pedidos", {
        headers: authHeaders,
        params: { limit: 20 },
      });
      const pedidos = Array.isArray(response?.data?.pedidos) ? response.data.pedidos : [];
      setOrdersDetailed(pedidos);

      if (pedidos.length) {
        const ids = pedidos.map((pedido) => pedido?.pedido_id).filter(Boolean);
        persistOrderIds((currentIds) => Array.from(new Set([...ids, ...currentIds])));
      }
    } catch (err) {
      const message = extractApiErrorMessage(err, "Erro ao carregar detalhes dos pedidos");
      setOrdersDetailed([]);
      setOrdersError(message);
      onError(message);
    } finally {
      loadingOrdersRef.current = false;
      setOrdersLoading(false);
    }
  }, [authHeaders, customerToken, onError, persistOrderIds]);

  const recordOrderId = useCallback(async (orderId) => {
    if (!orderId) return;
    persistOrderIds((currentIds) => Array.from(new Set([orderId, ...currentIds])));
    await loadOrdersDetailed();
  }, [loadOrdersDetailed, persistOrderIds]);

  useEffect(() => {
    if (!customerToken || view !== "pedidos") return;
    loadOrdersDetailed();
  }, [customerToken, loadOrdersDetailed, view]);

  const avisarCheguei = useCallback(async (pedidoId) => {
    try {
      await ecommerceApi.post(
        `/api/checkout/pedido/${pedidoId}/drive-cheguei`,
        {},
        { headers: authHeaders },
      );
      await loadOrdersDetailed();
    } catch (err) {
      onError(extractApiErrorMessage(err, "Erro ao avisar chegada"));
    }
  }, [authHeaders, loadOrdersDetailed, onError]);

  return {
    ordersDetailed,
    ordersError,
    ordersLoading,
    loadOrdersDetailed,
    avisarCheguei,
    recordOrderId,
  };
}
