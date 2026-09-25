import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FiClock,
  FiEdit3,
  FiPackage,
  FiRefreshCw,
  FiTrash2,
} from "react-icons/fi";
import { api } from "../../services/api";
import { confirmarCorePet } from "../../services/corepetDialog";

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

function providerMoney(value) {
  const raw = typeof value === "object" ? value?.value : value;
  return money(Number(raw || 0) / 100);
}

function paymentLines(payload) {
  const payment = payload?.payment || payload?.payments || {};
  return values(payment.methods || payment.paymentMethods).map((method, index) => {
    const card = method.card || {};
    const cash = method.cash || {};
    const description = [
      method.name || method.method || method.type,
      card.brand,
      cash.changeFor ? `troco para ${money(cash.changeFor)}` : null,
      method.amount ? providerMoney(method.amount) : method.value ? money(method.value) : null,
    ]
      .filter(Boolean)
      .join(" · ");
    return { id: method.id || `${description}-${index}`, description };
  });
}

function benefitLines(payload) {
  return values(payload?.benefit?.benefits || payload?.benefits).map((benefit, index) => {
    const sponsorship = values(benefit.sponsorships || benefit.sponsorshipValues)
      .map(
        (item) =>
          `${item.liability || item.name || item.responsible || "Responsável"}: ${
            item.amount ? providerMoney(item.amount) : money(item.value)
          }`,
      )
      .join(" · ");
    return {
      id: benefit.id || `${benefit.description || "cupom"}-${index}`,
      description: [benefit.description || benefit.target || "Benefício", sponsorship]
        .filter(Boolean)
        .join(" · "),
    };
  });
}

function OrderDetails({ order, onAction, onItemAction, action }) {
  const [quantities, setQuantities] = useState({});
  const payload = order.payload || {};
  const delivery = payload.delivery || payload.operationMode?.delivery || {};
  const address = delivery.deliveryAddress || delivery.destination || order.delivery_address || {};
  const phone = payload.customer?.phone || payload.customer?.localizer || {};
  const payments = paymentLines(payload);
  const benefits = benefitLines(payload);
  const items = values(payload.bag?.items || payload.items);

  useEffect(() => {
    setQuantities(
      Object.fromEntries(
        items.map((item, index) => [item.uniqueId || item.id || index, item.quantity || 1]),
      ),
    );
  }, [order.ifood_order_id, order.last_action_at, items.length]);

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
              <div
                key={item.uniqueId || item.id || `${item.name}-${index}`}
                className={`mt-3 rounded-lg border p-3 ${
                  item.unavailable ? "border-red-200 bg-red-50" : "border-slate-200 bg-white"
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium">
                      {item.quantity || 1}× {item.name || item.externalCode || "Item"}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      EAN {item.ean || "não informado"} · PLU {item.product?.plu || "não informado"}
                    </p>
                    <p className="font-mono text-[11px] text-slate-400">
                      uniqueId: {item.uniqueId || "não informado"}
                    </p>
                  </div>
                  <div className="text-right text-xs">
                    <p className={item.unavailable ? "font-semibold text-red-700" : "text-emerald-700"}>
                      unavailable: {String(Boolean(item.unavailable))}
                    </p>
                    {item.prices?.grossValue ? (
                      <p className="mt-1 text-slate-500">{providerMoney(item.prices.grossValue)}</p>
                    ) : null}
                  </div>
                </div>
                {item.uniqueId && !item.unavailable ? (
                  <div className="mt-3 flex flex-wrap items-end gap-2">
                    <label className="text-xs font-medium text-slate-600">
                      Quantidade separada
                      <input
                        type="number"
                        min="0.001"
                        step="0.001"
                        value={quantities[item.uniqueId] ?? item.quantity ?? 1}
                        onChange={(event) =>
                          setQuantities((current) => ({
                            ...current,
                            [item.uniqueId]: event.target.value,
                          }))
                        }
                        className="mt-1 block w-32 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() =>
                        onItemAction("update", item.uniqueId, {
                          quantity: Number(quantities[item.uniqueId] ?? item.quantity ?? 1),
                        })
                      }
                      disabled={Boolean(action)}
                      className="rounded-lg border border-blue-300 px-3 py-2 text-xs font-medium text-blue-800 disabled:opacity-50"
                    >
                      <FiEdit3 className="mr-1 inline" /> Atualizar quantidade
                    </button>
                    <button
                      type="button"
                      onClick={() => onItemAction("remove", item.uniqueId)}
                      disabled={Boolean(action)}
                      className="rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-700 disabled:opacity-50"
                    >
                      <FiTrash2 className="mr-1 inline" /> Marcar indisponível
                    </button>
                  </div>
                ) : null}
              </div>
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
          onClick={() => onAction("atualizar-sacola")}
          disabled={Boolean(action)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium disabled:opacity-50"
        >
          <FiRefreshCw className="mr-1 inline" /> Consultar Orders Virtual Bag
        </button>
        <button
          type="button"
          onClick={() => onAction("iniciar-separacao")}
          disabled={Boolean(action)}
          className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
        >
          <FiClock className="mr-1 inline" /> Iniciar separação
        </button>
        <button
          type="button"
          onClick={() => onAction("finalizar-separacao")}
          disabled={Boolean(action)}
          className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
        >
          <FiPackage className="mr-1 inline" /> Finalizar separação e consultar sacola
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
      const actionResponse = await api.post(
        `/integracoes/ifood/pedidos/${selectedId}/${name}`,
        body || {},
      );
      onMessage("success", "Ação executada no iFood e registrada para a homologação.");
      await loadOrders();
      if (name === "atualizar-sacola") {
        setSelected(actionResponse.data);
      } else if (actionResponse.data?.order) {
        setSelected(actionResponse.data.order);
      } else {
        const response = await api.get(`/integracoes/ifood/pedidos/${selectedId}`);
        setSelected(response.data);
      }
    } catch (error) {
      onMessage("error", errorMessage(error, "O iFood recusou a ação do pedido."));
    } finally {
      setAction(null);
    }
  }

  async function runItemAction(name, uniqueId, body) {
    if (!selectedId) return;
    if (
      name === "remove" &&
      !(await confirmarCorePet(
        "Confirma que este item está indisponível? O iFood o removerá da separação do pedido de teste.",
      ))
    ) {
      return;
    }
    try {
      setAction(`${name}-${uniqueId}`);
      const url = `/integracoes/ifood/pedidos/${selectedId}/itens/${uniqueId}`;
      if (name === "remove") {
        await api.delete(url);
      } else {
        await api.patch(url, body);
      }
      const response = await api.post(
        `/integracoes/ifood/pedidos/${selectedId}/atualizar-sacola`,
      );
      setSelected(response.data);
      await loadOrders();
      onMessage(
        "success",
        name === "remove"
          ? "Item marcado como indisponível e sacola consultada novamente."
          : "Quantidade separada atualizada e sacola consultada novamente.",
      );
    } catch (error) {
      onMessage("error", errorMessage(error, "O iFood recusou a alteração do item."));
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
            Orders Virtual Bag e Picking: consulta, início, alteração, indisponibilidade e fim da
            separação.
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
        <OrderDetails
          order={selected}
          onAction={runOrderAction}
          onItemAction={runItemAction}
          action={action}
        />
      ) : null}
      {!selected && selectedSummary ? (
        <p className="mt-3 text-sm text-slate-500">Carregando pedido...</p>
      ) : null}
    </div>
  );
}
