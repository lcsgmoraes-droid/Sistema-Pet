import { useEffect, useRef, useState } from "react";
import { api } from "../../../services/api";
import { confirmarCorePet } from "../../../services/corepetDialog";
import {
  accountPayload,
  canIssueOrder,
  downloadFiscalDocument,
  fiscalError,
  FISCAL_BASE,
} from "./amazonFiscalUtils";

export default function useAmazonFiscal({ loadLists = true, onChanged } = {}) {
  const [accounts, setAccounts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [version, setVersion] = useState(0);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const operation = useRef(false);
  const mounted = useRef(true);
  const detailRequest = useRef(0);
  const changedCallback = useRef(onChanged);
  changedCallback.current = onChanged;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      detailRequest.current += 1;
    };
  }, []);

  useEffect(() => {
    if (!loadLists) {
      setLoading(false);
      return undefined;
    }
    let active = true;
    setRefreshing(true);
    Promise.all([
      api.get(`${FISCAL_BASE}/accounts`),
      api.get(`${FISCAL_BASE}/orders`, {
        params: { page, page_size: 25, status: status || undefined },
      }),
    ])
      .then(([accountResponse, orderResponse]) => {
        if (!active) return;
        setAccounts(accountResponse.data.items || []);
        setOrders(orderResponse.data.items || []);
        setTotal(orderResponse.data.total || 0);
      })
      .catch(async (failure) => {
        const text = await fiscalError(failure);
        if (active) setError(text);
      })
      .finally(() => {
        if (active) {
          setLoading(false);
          setRefreshing(false);
        }
      });
    return () => {
      active = false;
    };
  }, [page, status, version, loadLists]);

  async function run(task, successMessage) {
    if (operation.current) return false;
    operation.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await task();
      if (mounted.current) {
        if (successMessage) setMessage(successMessage);
        setVersion((value) => value + 1);
        changedCallback.current?.();
      }
      return true;
    } catch (failure) {
      const text = await fiscalError(failure);
      if (mounted.current) setError(text);
      return false;
    } finally {
      operation.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  async function openOrder(order) {
    const request = ++detailRequest.current;
    setDetailOpen(true);
    setDetailLoading(true);
    setDetail(null);
    setError("");
    try {
      const { data } = await api.get(`${FISCAL_BASE}/orders/${order.id}`);
      if (mounted.current && request === detailRequest.current) setDetail(data);
    } catch (failure) {
      const text = await fiscalError(failure);
      if (mounted.current && request === detailRequest.current) setError(text);
    } finally {
      if (mounted.current && request === detailRequest.current) setDetailLoading(false);
    }
  }

  function closeOrder() {
    if (operation.current) return;
    detailRequest.current += 1;
    setDetailOpen(false);
    setDetail(null);
  }

  function updateDetail(data) {
    setDetail((current) => (current?.id === data.id ? { ...current, ...data } : current));
  }

  const issue = (order) =>
    run(async () => {
      if (!canIssueOrder(order)) throw new Error("Revise as pendências do pedido antes de emitir.");
      const accepted = await confirmarCorePet(
        `Emitir a NF-e do pedido Amazon ${order.external_order_id}? Confira destinatário, itens e pagamentos antes de confirmar.`,
      );
      if (!accepted) return;
      if (!mounted.current) return;
      const { data: current } = await api.get(`${FISCAL_BASE}/orders/${order.id}`);
      if (
        !canIssueOrder(current) ||
        current.source_revision !== order.source_revision ||
        current.payload_hash !== order.payload_hash
      ) {
        updateDetail(current);
        throw new Error("O pedido foi atualizado. Revise os dados novamente antes de emitir.");
      }
      try {
        const { data } = await api.post(`${FISCAL_BASE}/orders/${order.id}/emitir`, {
          expected_revision: current.source_revision,
          expected_payload_hash: current.payload_hash,
        });
        updateDetail(data);
      } catch (failure) {
        try {
          const { data } = await api.get(`${FISCAL_BASE}/orders/${order.id}`);
          updateDetail(data);
        } catch {
          updateDetail({ id: order.id, status: "unknown" });
        }
        throw failure;
      }
    });

  const consult = (order) =>
    run(async () => {
      const { data } = await api.post(`${FISCAL_BASE}/orders/${order.id}/consultar`, {});
      updateDetail(data);
    });

  const reviewHistorical = (order) =>
    run(async () => {
      const { data } = await api.post(`${FISCAL_BASE}/orders/${order.id}/review`, {
        acknowledge_historical: true,
      });
      updateDetail(data);
    }, "Revisão do pedido anterior à ativação registrada. A nota ainda precisa ser emitida.");

  const saveAccount = (form) =>
    run(async () => {
      const payload = accountPayload(form);
      if (form.id) await api.put(`${FISCAL_BASE}/accounts/${form.id}`, payload);
      else await api.post(`${FISCAL_BASE}/accounts`, payload);
    }, "Configuração fiscal salva.");

  return {
    accounts,
    orders,
    total,
    page,
    status,
    loading,
    refreshing,
    busy,
    error,
    message,
    detail,
    detailOpen,
    detailLoading,
    openOrder,
    closeOrder,
    issue,
    consult,
    reviewHistorical,
    saveAccount,
    refresh: () => {
      setError("");
      setVersion((value) => value + 1);
    },
    filter: (value) => {
      setPage(1);
      setStatus(value);
    },
    setPage,
    download: (order, kind) => run(() => downloadFiscalDocument(api, order, kind)),
  };
}
