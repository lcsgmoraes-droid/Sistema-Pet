import { useCallback, useEffect, useRef, useState } from "react";
import ecommerceApi from "../../services/ecommerceApi";
import { STORAGE_ORDERS_KEY, extractApiErrorMessage } from "./ecommerceMvpUtils";

const PENDING_ORDER_POLL_MS = 12_000;

function hasOpenFulfillmentOrder(pedido) {
  if (!pedido || pedido.tem_entrega) return false;
  const statusEntrega = String(pedido.status_entrega || "")
    .trim()
    .toLowerCase();
  return Boolean(pedido.tipo_retirada) && ["pendente", "pronto"].includes(statusEntrega);
}

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
      const ids = typeof idsOrUpdater === "function" ? idsOrUpdater(currentIds) : idsOrUpdater;
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

  const recordOrderId = useCallback(
    async (orderId) => {
      if (!orderId) return;
      persistOrderIds((currentIds) => Array.from(new Set([orderId, ...currentIds])));
      await loadOrdersDetailed();
    },
    [loadOrdersDetailed, persistOrderIds],
  );

  useEffect(() => {
    if (!customerToken || view !== "pedidos") return;
    loadOrdersDetailed();
  }, [customerToken, loadOrdersDetailed, view]);

  useEffect(() => {
    if (!customerToken || view !== "pedidos") return;
    const hasPendingOrder = ordersDetailed.some(
      (pedido) => pedido?.status === "pendente" || pedido?.status === "pending",
    );
    const hasOpenFulfillment = ordersDetailed.some(hasOpenFulfillmentOrder);
    if (!hasPendingOrder && !hasOpenFulfillment) return;

    const interval = setInterval(loadOrdersDetailed, PENDING_ORDER_POLL_MS);
    return () => clearInterval(interval);
  }, [customerToken, loadOrdersDetailed, ordersDetailed, view]);

  const avisarCheguei = useCallback(
    async (pedidoId) => {
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
    },
    [authHeaders, loadOrdersDetailed, onError],
  );

  return {
    ordersDetailed,
    ordersError,
    ordersLoading,
    loadOrdersDetailed,
    avisarCheguei,
    recordOrderId,
  };
}
