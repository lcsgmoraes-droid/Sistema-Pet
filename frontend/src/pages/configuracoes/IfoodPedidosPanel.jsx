import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Clock, Package, Pencil, RefreshCw, Trash2 } from "lucide-react";
import { api } from "../../services/api";
import { confirmarCorePet } from "../../services/corepetDialog";
import { formatMoneyBRL } from "../../utils/formatters";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputQuantidade from "../../components/v2/InputQuantidade/InputQuantidade";
import IfoodPedidoPdvPilot, {
  canImportIfoodPdvPilot,
} from "../../components/ifood/IfoodPedidoPdvPilot";

function errorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

function money(value) {
  return formatMoneyBRL(value);
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

export function OrderDetails({
  order,
  onAction,
  onItemAction,
  onImportPdv,
  action,
  actionsEnabled,
}) {
  const [quantities, setQuantities] = useState({});
  const payload = order.payload || {};
  const delivery = payload.delivery || payload.operationMode?.delivery || {};
  const address = delivery.deliveryAddress || delivery.destination || order.delivery_address || {};
  const phone = payload.customer?.phone || payload.customer?.localizer || {};
  const payments = paymentLines(payload);
  const benefits = benefitLines(payload);
  const items = values(payload.bag?.items || payload.items);
  const controlsDisabled = !actionsEnabled || Boolean(action);
  const pickingItemsDisabled = controlsDisabled || Boolean(order.pdv_bridge?.sale_id);

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

      <IfoodPedidoPdvPilot
        bridge={order.pdv_bridge}
        busy={Boolean(action)}
        onImport={onImportPdv}
      />

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
                    <p
                      className={
                        item.unavailable ? "font-semibold text-red-700" : "text-emerald-700"
                      }
                    >
                      unavailable: {String(Boolean(item.unavailable))}
                    </p>
                    {item.prices?.grossValue ? (
                      <p className="mt-1 text-slate-500">{providerMoney(item.prices.grossValue)}</p>
                    ) : null}
                  </div>
                </div>
                {item.uniqueId && !item.unavailable ? (
                  <div className="mt-3 flex flex-wrap items-end gap-2">
                    <div className="w-36">
                      <InputQuantidade
                        label="Quantidade separada"
                        min={0.001}
                        disabled={pickingItemsDisabled}
                        value={quantities[item.uniqueId] ?? item.quantity ?? 1}
                        onChange={(quantity) =>
                          setQuantities((current) => ({
                            ...current,
                            [item.uniqueId]: quantity,
                          }))
                        }
                      />
                    </div>
                    <BotaoInteracao
                      icon={Pencil}
                      tamanho="pequeno"
                      onClick={() =>
                        onItemAction("update", item.uniqueId, {
                          quantity: Number(quantities[item.uniqueId] ?? item.quantity ?? 1),
                        })
                      }
                      disabled={pickingItemsDisabled}
                    >
                      Atualizar quantidade
                    </BotaoInteracao>
                    <BotaoInteracao
                      icon={Trash2}
                      tamanho="pequeno"
                      onClick={() => onItemAction("remove", item.uniqueId)}
                      disabled={pickingItemsDisabled}
                    >
                      Marcar indisponível
                    </BotaoInteracao>
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

      {order.pdv_bridge?.sale_id ? (
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          Os itens estão vinculados à reserva do PDV. Quantidade e indisponibilidade ficam
          bloqueadas neste piloto para preservar a conferência de estoque.
        </p>
      ) : null}

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
        <BotaoInteracao
          icon={RefreshCw}
          tamanho="pequeno"
          onClick={() => onAction("atualizar-sacola")}
          disabled={controlsDisabled}
        >
          Consultar Orders Virtual Bag
        </BotaoInteracao>
        <BotaoInteracao
          icon={Clock}
          tamanho="pequeno"
          onClick={() => onAction("iniciar-separacao")}
          disabled={controlsDisabled}
        >
          Iniciar separação
        </BotaoInteracao>
        <BotaoInteracao
          icon={Package}
          tamanho="pequeno"
          onClick={() => onAction("finalizar-separacao")}
          disabled={controlsDisabled}
        >
          Finalizar separação e consultar sacola
        </BotaoInteracao>
      </div>
    </div>
  );
}

export default function IfoodPedidosPanel({ enabled: externalEnabled, onMessage }) {
  const [orders, setOrders] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [action, setAction] = useState(null);
  const [loadingOrders, setLoadingOrders] = useState(true);
  const [loadingSelected, setLoadingSelected] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [selectedError, setSelectedError] = useState("");
  const pilotImportRef = useRef(false);
  const selectedIdRef = useRef(selectedId);
  selectedIdRef.current = selectedId;

  const loadOrders = useCallback(async (isCurrent = () => true) => {
    const response = await api.get("/integracoes/ifood/pedidos", { params: { limit: 30 } });
    if (isCurrent()) {
      setOrders(response.data?.orders || []);
      setLoadError("");
    }
  }, []);

  useEffect(() => {
    let active = true;
    void loadOrders(() => active)
      .catch(() => {
        if (active) setLoadError("Não foi possível carregar os pedidos. Atualize a consulta.");
      })
      .finally(() => {
        if (active) setLoadingOrders(false);
      });
    return () => {
      active = false;
    };
  }, [loadOrders]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      setLoadingSelected(false);
      setSelectedError("");
      return;
    }
    let active = true;
    setSelected(null);
    setLoadingSelected(true);
    setSelectedError("");
    void api
      .get(`/integracoes/ifood/pedidos/${selectedId}`)
      .then((response) => {
        if (active) setSelected(response.data);
      })
      .catch(() => {
        if (active) {
          setSelected(null);
          setSelectedError("Não foi possível carregar este pedido. Atualize a consulta.");
        }
      })
      .finally(() => {
        if (active) setLoadingSelected(false);
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  const selectedSummary = useMemo(
    () => orders.find((order) => order.ifood_order_id === selectedId),
    [orders, selectedId],
  );

  function selectOrder(orderId) {
    if (selectedId === orderId) return;
    setSelected(null);
    setSelectedError("");
    setLoadingSelected(true);
    setSelectedId(orderId);
  }

  async function refreshSelected(orderId = selectedId) {
    if (!orderId) return;
    const response = await api.get(`/integracoes/ifood/pedidos/${orderId}`);
    if (selectedIdRef.current === orderId) {
      setSelected(response.data);
      setSelectedError("");
    }
  }

  async function refreshLocalOrders() {
    try {
      setAction("refresh");
      await loadOrders();
      await refreshSelected();
    } catch (error) {
      onMessage("error", errorMessage(error, "Não foi possível atualizar os pedidos do CorePet."));
    } finally {
      setAction(null);
    }
  }

  async function poll() {
    if (!externalEnabled) return;
    try {
      setAction("poll");
      const response = await api.post("/integracoes/ifood/pedidos/processar-eventos");
      const summary = response.data;
      onMessage(
        "success",
        `Eventos consultados: ${summary.received}; confirmados: ${summary.acknowledged}.`,
      );
      await loadOrders();
      await refreshSelected();
    } catch (error) {
      onMessage("error", errorMessage(error, "Não foi possível consultar eventos de pedidos."));
    } finally {
      setAction(null);
    }
  }

  async function runOrderAction(name, body) {
    if (!selectedId || !externalEnabled) return;
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

  async function importPdvPilot() {
    if (!selectedId || pilotImportRef.current || !canImportIfoodPdvPilot(selected?.pdv_bridge)) {
      return;
    }
    const orderId = selectedId;
    pilotImportRef.current = true;
    try {
      setAction("piloto-pdv/importar");
      const response = await api.post(`/integracoes/ifood/pedidos/${orderId}/piloto-pdv/importar`);
      if (selectedIdRef.current === orderId) setSelected(response.data);
      await loadOrders();
      onMessage(
        "success",
        "Pedido de teste enviado ao PDV com reserva. A baixa ocorre ao finalizar a venda no PDV.",
      );
    } catch (error) {
      onMessage("error", errorMessage(error, "Não foi possível enviar o pedido de teste ao PDV."));
    } finally {
      pilotImportRef.current = false;
      setAction(null);
    }
  }

  async function runItemAction(name, uniqueId, body) {
    if (!selectedId || !externalEnabled || selected?.pdv_bridge?.sale_id) return;
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
      const response = await api.post(`/integracoes/ifood/pedidos/${selectedId}/atualizar-sacola`);
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
        <div className="flex flex-wrap gap-2">
          <BotaoInteracao
            icon={RefreshCw}
            tamanho="pequeno"
            onClick={refreshLocalOrders}
            disabled={Boolean(action)}
            loading={action === "refresh"}
          >
            Atualizar pedidos
          </BotaoInteracao>
          <BotaoInteracao
            icon={RefreshCw}
            tamanho="pequeno"
            onClick={poll}
            disabled={!externalEnabled || Boolean(action)}
            loading={action === "poll"}
          >
            Buscar eventos agora
          </BotaoInteracao>
        </div>
      </div>

      {!externalEnabled ? (
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          A consulta de eventos e as ações no iFood permanecem bloqueadas. A importação local ao PDV
          depende da autorização do piloto DEV mostrada em cada pedido.
        </p>
      ) : null}

      {loadingOrders ? (
        <p role="status" className="mt-4 text-sm text-slate-500">
          Carregando pedidos...
        </p>
      ) : loadError ? (
        <p role="alert" className="mt-4 text-sm text-red-700 dark:text-red-300">
          {loadError}
        </p>
      ) : orders.length ? (
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {orders.map((order) => (
            <div
              key={order.ifood_order_id}
              className={`rounded-lg border p-3 text-sm dark:text-slate-100 ${selectedId === order.ifood_order_id ? "border-red-400 bg-red-50 dark:bg-red-950/30" : "border-slate-200 dark:border-slate-800"}`}
            >
              <BotaoInteracao
                aria-pressed={selectedId === order.ifood_order_id}
                disabled={Boolean(action)}
                larguraTotal
                onClick={() => selectOrder(order.ifood_order_id)}
                tamanho="pequeno"
              >
                Ver pedido #{order.display_id || order.ifood_order_id.slice(0, 8)}
              </BotaoInteracao>
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
            </div>
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
          onImportPdv={importPdvPilot}
          action={action}
          actionsEnabled={externalEnabled}
        />
      ) : null}
      {loadingSelected && selectedSummary ? (
        <p role="status" className="mt-3 text-sm text-slate-500">
          Carregando pedido...
        </p>
      ) : null}
      {selectedError ? (
        <p role="alert" className="mt-3 text-sm text-red-700 dark:text-red-300">
          {selectedError}
        </p>
      ) : null}
    </div>
  );
}
