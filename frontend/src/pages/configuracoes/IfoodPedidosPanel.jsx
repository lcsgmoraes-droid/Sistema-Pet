import { useCallback, useEffect, useMemo, useState } from "react";
import { FiCheck, FiClock, FiPackage, FiRefreshCw, FiTruck, FiX } from "react-icons/fi";
import { api } from "../../services/api";

function errorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

function money(value) {
  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function dateTime(value) {
  if (!value) return "Não informado";
  return new Date(value).toLocaleString("pt-BR");
}

function statusClass(status) {
  if (["CONCLUDED", "CONFIRMED", "READY_TO_PICKUP"].includes(status)) {
    return "bg-emerald-100 text-emerald-700";
  }
  if (["CANCELLED", "CANCELLATION_REQUEST_FAILED"].includes(status)) {
    return "bg-red-100 text-red-700";
  }
  return "bg-amber-100 text-amber-700";
}

function values(value) {
  return Array.isArray(value) ? value : [];
}

function paymentLines(payload) {
  const payment = payload?.payments || payload?.payment || {};
  return values(payment.methods || payment.paymentMethods).map((method, index) => {
    const card = method.card || {};
    const cash = method.cash || {};
    const description = [
      method.method || method.type,
      card.brand,
      cash.changeFor ? `troco para ${money(cash.changeFor)}` : null,
      method.value ? money(method.value) : null,
    ]
      .filter(Boolean)
      .join(" · ");
    return { id: method.id || `${description}-${index}`, description };
  });
}

function benefitLines(payload) {
  return values(payload?.benefits).map((benefit, index) => {
    const sponsorship = values(benefit.sponsorshipValues)
      .map((item) => `${item.name || item.responsible || "Responsável"}: ${money(item.value)}`)
      .join(" · ");
    return {
      id: benefit.id || `${benefit.description || "cupom"}-${index}`,
      description: [benefit.description || benefit.target || "Benefício", sponsorship]
        .filter(Boolean)
        .join(" · "),
    };
  });
}

function OrderDetails({ order, onAction, action }) {
  const [reasons, setReasons] = useState([]);
  const [reason, setReason] = useState("");
  const [code, setCode] = useState("");
  const payload = order.payload || {};
  const delivery = payload.delivery || {};
  const address = delivery.deliveryAddress || order.delivery_address || {};
  const phone = payload.customer?.phone || {};
  const payments = paymentLines(payload);
  const benefits = benefitLines(payload);
  const items = values(payload.items);

  async function loadReasons() {
    const response = await api.get(
      `/integracoes/ifood/pedidos/${order.ifood_order_id}/motivos-cancelamento`,
    );
    const next = values(response.data?.reasons);
    setReasons(next);
    setReason(String(next[0]?.code || next[0]?.reason || ""));
  }

  return (
    <div className="mt-4 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-900 dark:text-slate-100">
            Pedido #{order.display_id || order.ifood_order_id}
          </p>
          <p className="text-xs text-slate-500">
            {order.order_type || "Pedido"} · {order.order_timing || "Horário não informado"} ·{" "}
            {order.delivered_by || "Entrega não informada"}
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusClass(order.status)}`}>
          {order.status}
        </span>
      </div>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-xs uppercase text-slate-500">Cliente</p>
          <p>{order.customer_name || payload.customer?.name || "Não informado"}</p>
        </div>
        <div>
          <p className="text-xs uppercase text-slate-500">Total</p>
          <p>{money(order.total)}</p>
        </div>
        <div>
          <p className="text-xs uppercase text-slate-500">Recebido</p>
          <p>{dateTime(order.placed_at)}</p>
        </div>
        <div>
          <p className="text-xs uppercase text-slate-500">Localizador</p>
          <p className="font-mono">{phone.localizer || "Não informado"}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase text-slate-500">Itens</p>
          {items.length ? (
            items.map((item, index) => (
              <p key={item.id || `${item.name}-${index}`} className="mt-2 text-sm">
                {item.quantity || 1}× {item.name || item.externalCode || "Item"}
                {item.totalPrice || item.unitPrice ? (
                  <span className="text-slate-500">
                    {" "}
                    · {money(item.totalPrice || item.unitPrice)}
                  </span>
                ) : null}
              </p>
            ))
          ) : (
            <p className="mt-2 text-sm text-slate-500">Itens ainda não carregados.</p>
          )}
        </div>
        <div className="space-y-3">
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-900">
            <p className="text-xs font-semibold uppercase text-slate-500">Pagamento</p>
            {payments.length ? (
              payments.map((line) => (
                <p key={line.id} className="mt-2 text-sm">
                  {line.description}
                </p>
              ))
            ) : (
              <p className="mt-2 text-sm text-slate-500">Não informado.</p>
            )}
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-900">
            <p className="text-xs font-semibold uppercase text-slate-500">Cupons e benefícios</p>
            {benefits.length ? (
              benefits.map((line) => (
                <p key={line.id} className="mt-2 text-sm">
                  {line.description}
                </p>
              ))
            ) : (
              <p className="mt-2 text-sm text-slate-500">Nenhum benefício informado.</p>
            )}
          </div>
        </div>
      </div>

      {Object.keys(address).length ? (
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase text-slate-500">Entrega</p>
          <p className="mt-1">
            {[address.streetName, address.streetNumber, address.neighborhood, address.city]
              .filter(Boolean)
              .join(", ")}
          </p>
          {address.complement ? <p className="text-slate-500">{address.complement}</p> : null}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onAction("confirmar")}
          disabled={Boolean(action)}
          className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
        >
          <FiCheck className="mr-1 inline" /> Confirmar
        </button>
        <button
          type="button"
          onClick={() => onAction("iniciar-preparacao")}
          disabled={Boolean(action)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium disabled:opacity-50"
        >
          <FiClock className="mr-1 inline" /> Iniciar separação
        </button>
        <button
          type="button"
          onClick={() => onAction("pronto")}
          disabled={Boolean(action)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium disabled:opacity-50"
        >
          <FiPackage className="mr-1 inline" /> Marcar pronto
        </button>
        {order.order_type === "DELIVERY" && order.delivered_by === "MERCHANT" ? (
          <button
            type="button"
            onClick={() => onAction("despachar")}
            disabled={Boolean(action)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium disabled:opacity-50"
          >
            <FiTruck className="mr-1 inline" /> Despachar
          </button>
        ) : null}
        <button
          type="button"
          onClick={loadReasons}
          disabled={Boolean(action)}
          className="rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-700 disabled:opacity-50"
        >
          <FiX className="mr-1 inline" /> Consultar cancelamento
        </button>
      </div>

      {reasons.length ? (
        <div className="mt-3 flex flex-wrap items-end gap-2 rounded-lg border border-red-100 bg-red-50 p-3">
          <label className="min-w-64 flex-1 text-xs font-medium text-red-900">
            Motivo retornado pelo iFood
            <select
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              className="mt-1 w-full rounded-lg border border-red-200 bg-white px-3 py-2 text-sm"
            >
              {reasons.map((item) => {
                const value = String(item.code || item.reason || "");
                return (
                  <option key={value} value={value}>
                    {value} — {item.description || item.message}
                  </option>
                );
              })}
            </select>
          </label>
          <button
            type="button"
            onClick={() => onAction("cancelar", { reason })}
            disabled={!reason || Boolean(action)}
            className="rounded-lg bg-red-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
          >
            Solicitar cancelamento
          </button>
        </div>
      ) : null}

      <div className="mt-3 flex flex-wrap items-end gap-2 rounded-lg border border-blue-100 bg-blue-50 p-3">
        <label className="min-w-48 flex-1 text-xs font-medium text-blue-900">
          Código de coleta/entrega
          <input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            className="mt-1 w-full rounded-lg border border-blue-200 bg-white px-3 py-2 font-mono text-sm"
          />
        </label>
        <button
          type="button"
          onClick={() => onAction("validar-coleta", { code })}
          disabled={!code || Boolean(action)}
          className="rounded-lg border border-blue-300 px-3 py-2 text-xs font-medium text-blue-800 disabled:opacity-50"
        >
          Validar coleta
        </button>
        <button
          type="button"
          onClick={() => onAction("validar-entrega", { code })}
          disabled={!code || Boolean(action)}
          className="rounded-lg border border-blue-300 px-3 py-2 text-xs font-medium text-blue-800 disabled:opacity-50"
        >
          Validar entrega
        </button>
      </div>
    </div>
  );
}

export default function IfoodPedidosPanel({ enabled, onMessage }) {
  const [orders, setOrders] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [action, setAction] = useState(null);

  const loadOrders = useCallback(async () => {
    const response = await api.get("/integracoes/ifood/pedidos", { params: { limit: 30 } });
    setOrders(response.data?.orders || []);
  }, []);

  useEffect(() => {
    void loadOrders().catch(() => null);
  }, [loadOrders]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    void api
      .get(`/integracoes/ifood/pedidos/${selectedId}`)
      .then((response) => setSelected(response.data))
      .catch(() => setSelected(null));
  }, [selectedId]);

  const selectedSummary = useMemo(
    () => orders.find((order) => order.ifood_order_id === selectedId),
    [orders, selectedId],
  );

  async function poll() {
    try {
      setAction("poll");
      const response = await api.post("/integracoes/ifood/pedidos/processar-eventos");
      const summary = response.data;
      onMessage(
        "success",
        `Eventos consultados: ${summary.received}; confirmados: ${summary.acknowledged}.`,
      );
      await loadOrders();
    } catch (error) {
      onMessage("error", errorMessage(error, "Não foi possível consultar eventos de pedidos."));
    } finally {
      setAction(null);
    }
  }

  async function runOrderAction(name, body) {
    if (!selectedId) return;
    try {
      setAction(name);
      await api.post(`/integracoes/ifood/pedidos/${selectedId}/${name}`, body || {});
      onMessage("success", "Ação aceita pelo iFood. O status será atualizado pelo próximo evento.");
      await loadOrders();
      const response = await api.get(`/integracoes/ifood/pedidos/${selectedId}`);
      setSelected(response.data);
    } catch (error) {
      onMessage("error", errorMessage(error, "O iFood recusou a ação do pedido."));
    } finally {
      setAction(null);
    }
  }

  return (
    <div className="mt-5 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-900 dark:text-slate-100">Pedidos para homologação</p>
          <p className="text-xs text-slate-500">
            Recebimento, confirmação, cancelamento, despacho e validação sem publicar produtos.
          </p>
        </div>
        <button
          type="button"
          onClick={poll}
          disabled={!enabled || Boolean(action)}
          className="inline-flex items-center gap-2 rounded-xl border border-red-200 px-3 py-2 text-xs font-medium text-red-700 disabled:opacity-50"
        >
          <FiRefreshCw className={action === "poll" ? "animate-spin" : ""} /> Buscar eventos agora
        </button>
      </div>

      {!enabled ? (
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          As ações de pedidos estão prontas, mas permanecem bloqueadas até a homologação assistida
          ser iniciada.
        </p>
      ) : null}

      {orders.length ? (
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {orders.map((order) => (
            <button
              key={order.ifood_order_id}
              type="button"
              onClick={() => setSelectedId(order.ifood_order_id)}
              className={`rounded-lg border p-3 text-left text-sm ${selectedId === order.ifood_order_id ? "border-red-400 bg-red-50" : "border-slate-200"}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">
                  #{order.display_id || order.ifood_order_id.slice(0, 8)}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] ${statusClass(order.status)}`}
                >
                  {order.status}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {order.order_type} · {order.order_timing}
              </p>
              <p className="mt-2 font-medium">{money(order.total)}</p>
            </button>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-500">Nenhum pedido de teste recebido ainda.</p>
      )}

      {selected ? (
        <OrderDetails order={selected} onAction={runOrderAction} action={action} />
      ) : null}
      {!selected && selectedSummary ? (
        <p className="mt-3 text-sm text-slate-500">Carregando pedido...</p>
      ) : null}
    </div>
  );
}
