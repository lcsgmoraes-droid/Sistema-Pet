import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Scissors,
  Smartphone,
  Stethoscope,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { formatMoneyBRL } from "../../utils/formatters";
import { getSalesChannelInfo, isOnlineSalesChannel } from "../../utils/salesChannel";
import CopyableCode from "../ui/CopyableCode";
import CustomerIdentity, { getCustomerIdentityCode } from "../ui/CustomerIdentity";
import IconActionButton from "../ui/IconActionButton";
import SaleReference from "../ui/SaleReference";
import StatusBadge from "../ui/StatusBadge";

const CANAL_APP_FUNCIONARIO = "app_funcionario";
const APP_FUNCIONARIO_LABEL = "App Funcionario";
const APP_FUNCIONARIO_TITLE = "Venda pelo app do funcionario";

function getCanalInfo(canal) {
  const info = getSalesChannelInfo(canal);
  const iconByKey = {
    scissors: Scissors,
    smartphone: Smartphone,
    stethoscope: Stethoscope,
  };
  if (info.value === CANAL_APP_FUNCIONARIO) {
    return {
      ...info,
      label: APP_FUNCIONARIO_LABEL,
      title: APP_FUNCIONARIO_TITLE,
      Icon: Smartphone,
    };
  }
  return { ...info, Icon: iconByKey[info.iconKey] };
}

function isCanalOnline(canal) {
  return isOnlineSalesChannel(canal);
}

function isRetiradaOnlineSemEntrega(venda) {
  return (
    isCanalOnline(venda?.canal) &&
    !venda?.tem_entrega &&
    ["proprio", "terceiro", "app_loja"].includes(venda?.tipo_retirada)
  );
}

function isPedidoOnlineOperacional(venda) {
  return (
    isCanalOnline(venda?.canal) &&
    (Boolean(venda?.tem_entrega) || isRetiradaOnlineSemEntrega(venda))
  );
}

function isPedidoOnlinePendente(venda) {
  return isPedidoOnlineOperacional(venda) && venda?.status_entrega === "pendente";
}

function canConfirmarRetirada(venda) {
  return (
    venda?.status_entrega !== "entregue" &&
    (isPedidoOnlineOperacional(venda) ||
      venda?.tipo_retirada === "terceiro" ||
      Boolean(venda?.palavra_chave_retirada))
  );
}

function formatarDataVenda(dataStr) {
  if (typeof dataStr === "string" && dataStr.includes("T")) {
    const [date, timeWithTz] = dataStr.split("T");
    const time = timeWithTz.split("-")[0].split("+")[0];
    const [, m, d] = date.split("-");
    const [h, min] = time.split(":");
    return `${d}/${m} ${h}:${min}`;
  }

  return new Date(dataStr).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getEntregaStatusInfo(venda) {
  if (isPedidoOnlineOperacional(venda)) {
    if (venda.status_entrega === "pendente") {
      return {
        intent: "warning",
        label: "Separar",
        title: "Pedido online aguardando separacao",
      };
    }

    if (venda.status_entrega === "pronto") {
      return {
        intent: "success",
        label: "Pronto",
        title: venda.tem_entrega ? "Pedido pronto para entrega" : "Pedido pronto para retirada",
      };
    }
  }

  if (venda.status_entrega === "pendente" && venda.tem_entrega) {
    return {
      intent: "warning",
      label: "Entrega",
      title: "Entrega pendente",
    };
  }

  if (venda.status_entrega !== "entregue") {
    return null;
  }

  if (venda.tem_entrega) {
    return {
      intent: "success",
      label: "Entregue",
      title: "Pedido entregue ao cliente",
    };
  }

  if (venda.retirado_por) {
    return {
      intent: "success",
      label: venda.retirado_por,
      title: `Retirado por: ${venda.retirado_por}`,
    };
  }

  return {
    intent: "success",
    label: "Retirado",
    title: "Pedido retirado na loja",
  };
}

export default function PDVVendasRecentesSidebar({
  painelVendasAberto,
  setPainelVendasAberto,
  filtroVendas,
  setFiltroVendas,
  filtroStatus,
  setFiltroStatus,
  filtroTemEntrega,
  setFiltroTemEntrega,
  buscaNumeroVenda,
  setBuscaNumeroVenda,
  vendasRecentes,
  reabrirVenda,
  confirmandoRetirada,
  abrirConfirmacaoRetirada,
  confirmarRetirada,
  marcarProntoRetirada,
  setConfirmandoRetirada,
}) {
  const [mostrarSomentePendenciasSeparacao, setMostrarSomentePendenciasSeparacao] = useState(false);
  const pendenciasSeparacao = vendasRecentes.filter(isPedidoOnlinePendente).length;
  const vendasRecentesVisiveis = useMemo(
    () =>
      mostrarSomentePendenciasSeparacao
        ? vendasRecentes.filter(isPedidoOnlinePendente)
        : vendasRecentes,
    [mostrarSomentePendenciasSeparacao, vendasRecentes],
  );

  useEffect(() => {
    if (pendenciasSeparacao === 0 && mostrarSomentePendenciasSeparacao) {
      setMostrarSomentePendenciasSeparacao(false);
    }
  }, [mostrarSomentePendenciasSeparacao, pendenciasSeparacao]);

  return (
    <>
      {painelVendasAberto && (
        <div className="w-52 bg-white border-l flex flex-col">
          <div className="p-3 border-b">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-gray-900 flex items-center">
                <Clock className="w-4 h-4 mr-2 text-blue-600" />
                Vendas Recentes
              </h2>
              <IconActionButton
                onClick={() => setPainelVendasAberto(false)}
                icon={X}
                intent="neutral"
                tone="ghost"
                size="xs"
                title="Fechar painel"
              />
            </div>

            <div className="flex space-x-1 mb-3">
              {["24h", "7d", "30d"].map((periodo) => (
                <button
                  key={periodo}
                  onClick={() => setFiltroVendas(periodo)}
                  className={`flex h-9 flex-1 items-center justify-center rounded-lg px-2 text-center text-xs font-medium leading-tight transition-colors ${
                    filtroVendas === periodo
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                  type="button"
                >
                  {periodo === "24h" && "Ultimas 24h"}
                  {periodo === "7d" && "7 dias"}
                  {periodo === "30d" && "30 dias"}
                </button>
              ))}
            </div>

            <div className="flex space-x-1 mb-2">
              {[
                { id: "todas", label: "Todas" },
                { id: "pago", label: "Pago" },
                { id: "aberta", label: "Aberta" },
              ].map((status) => (
                <button
                  key={status.id}
                  onClick={() => setFiltroStatus(status.id)}
                  className={`flex h-9 flex-1 items-center justify-center rounded-lg px-2 text-center text-xs font-medium leading-tight transition-colors ${
                    filtroStatus === status.id
                      ? "bg-green-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                  type="button"
                >
                  {status.label}
                </button>
              ))}
            </div>

            <label className="flex items-center gap-2 cursor-pointer p-2 hover:bg-gray-50 rounded-lg">
              <input
                type="checkbox"
                checked={filtroTemEntrega}
                onChange={(e) => setFiltroTemEntrega(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-xs font-medium text-gray-700">Apenas com entrega</span>
            </label>

            <div className="px-2 pb-2">
              <input
                type="text"
                value={buscaNumeroVenda}
                onChange={(e) => setBuscaNumeroVenda(e.target.value)}
                placeholder="Buscar por numero..."
                className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {pendenciasSeparacao > 0 && (
              <button
                className={`mx-2 mb-2 flex w-[calc(100%-1rem)] items-start gap-2 rounded-lg border px-2 py-2 text-left text-[11px] font-semibold leading-snug transition-colors ${
                  mostrarSomentePendenciasSeparacao
                    ? "border-red-300 bg-red-100 text-red-900"
                    : "border-red-200 bg-red-50 text-red-800 hover:bg-red-100"
                }`}
                onClick={() => {
                  setFiltroStatus("todas");
                  setFiltroTemEntrega(false);
                  setBuscaNumeroVenda("");
                  setMostrarSomentePendenciasSeparacao(true);
                }}
                title="Filtrar pedidos online aguardando separacao"
                type="button"
              >
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
                <span>{pendenciasSeparacao} pedido(s) online aguardando separacao.</span>
              </button>
            )}

            {mostrarSomentePendenciasSeparacao && pendenciasSeparacao > 0 && (
              <button
                className="mx-2 mb-2 w-[calc(100%-1rem)] rounded-lg border border-red-200 bg-white px-2 py-1.5 text-[11px] font-semibold text-red-700 transition-colors hover:bg-red-50"
                onClick={() => setMostrarSomentePendenciasSeparacao(false)}
                type="button"
              >
                Limpar filtro de separacao
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {vendasRecentesVisiveis.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-xs">Nenhuma venda encontrada</p>
              </div>
            ) : (
              vendasRecentesVisiveis.map((venda) => {
                const canalInfo = getCanalInfo(venda.canal);
                const CanalIcon = canalInfo.Icon;
                const entregaStatus = getEntregaStatusInfo(venda);
                const customerCode = getCustomerIdentityCode(venda);
                const pedidoOnlineOperacional = isPedidoOnlineOperacional(venda);
                const podeMarcarPronto =
                  pedidoOnlineOperacional && venda?.status_entrega === "pendente";
                const podeConfirmarConclusao =
                  canConfirmarRetirada(venda) &&
                  (!pedidoOnlineOperacional || venda.status_entrega === "pronto") &&
                  confirmandoRetirada.vendaId !== venda.id;
                const conclusaoLabel = venda.tem_entrega ? "Entregue" : "Retirada";
                const conclusaoTitle = venda.tem_entrega
                  ? "Informar quem recebeu"
                  : "Informar quem retirou";

                return (
                  <div
                    key={venda.id}
                    onClick={() => reabrirVenda(venda)}
                    className={`overflow-hidden rounded-lg p-2.5 border border-l-4 ${canalInfo.cor} ${canalInfo.border} cursor-pointer transition-colors ${canalInfo.bg}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className="text-[10px] text-gray-500 flex items-center gap-0.5"
                        title={canalInfo.title || canalInfo.label}
                      >
                        {CanalIcon ? (
                          <CanalIcon
                            className={`w-3 h-3 ${canalInfo.iconColor || "text-gray-500"}`}
                            aria-hidden="true"
                          />
                        ) : (
                          <span>{canalInfo.icon}</span>
                        )}
                        <span>{canalInfo.label}</span>
                        {venda.tem_entrega && (
                          <span className="ml-1" title="Entrega">
                            {"\uD83D\uDE9A"}
                          </span>
                        )}
                      </span>
                      {venda.palavra_chave_retirada && (
                        <button
                          onClick={(e) => {
                            if (canConfirmarRetirada(venda)) {
                              abrirConfirmacaoRetirada(e, venda.id);
                              return;
                            }
                            e.stopPropagation();
                          }}
                          className="rounded-full border border-orange-200 bg-orange-100 px-1.5 py-0.5 text-[10px] font-semibold text-orange-700 transition-colors hover:bg-orange-200"
                          title={
                            canConfirmarRetirada(venda)
                              ? "Informar quem retirou"
                              : "Senha de retirada"
                          }
                          type="button"
                        >
                          {"\uD83D\uDD11"} {venda.palavra_chave_retirada}
                        </button>
                      )}
                    </div>

                    <div className="mb-1.5 min-w-0">
                      <div className="min-w-0">
                        <CustomerIdentity
                          className="max-w-full min-w-0"
                          nameClassName="text-[13px] font-semibold text-gray-900"
                          nameWrapperClassName="max-w-full min-w-0"
                          showCode={false}
                          venda={venda}
                        />
                        <div className="mt-0.5 flex min-w-0 flex-wrap items-center gap-1 text-xs text-gray-500">
                          <SaleReference sale={venda} showPrefix={false} />
                          {customerCode ? (
                            <CopyableCode
                              className="max-w-full overflow-hidden bg-white/70 px-1 py-0 text-[10px]"
                              label="Cliente"
                              title="Copiar codigo do cliente"
                              value={customerCode}
                            />
                          ) : null}
                        </div>
                      </div>

                      <div className="mt-1 flex justify-end">
                        <div className="text-right">
                          {venda.status === "baixa_parcial" ? (
                            <>
                              <div className="text-[10px] text-gray-500">Pago</div>
                              <div className="text-xs font-semibold text-green-600">
                                {formatMoneyBRL(venda.valor_pago || 0)}
                              </div>
                              <div className="text-[10px] text-gray-500 mt-0.5">
                                de {formatMoneyBRL(venda.total || 0)}
                              </div>
                            </>
                          ) : (
                            <div className="text-sm font-semibold text-green-600">
                              {formatMoneyBRL(venda.total || 0)}
                            </div>
                          )}
                          <StatusBadge status={venda.status} size="xs" className="mt-1" />
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="text-[10px] text-gray-500">
                        {formatarDataVenda(venda.data_venda)}
                      </div>
                      <div className="flex flex-wrap justify-end gap-1">
                        {podeMarcarPronto && (
                          <button
                            onClick={(e) => marcarProntoRetirada(e, venda.id)}
                            className="rounded border border-amber-500 bg-white px-2 py-0.5 text-[10px] font-semibold text-amber-700 transition-colors hover:bg-amber-50"
                            title={
                              venda.tem_entrega
                                ? "Marcar pedido como pronto para entrega"
                                : "Marcar pedido como pronto para retirada"
                            }
                            type="button"
                          >
                            Pronto
                          </button>
                        )}
                        {podeConfirmarConclusao && (
                          <button
                            onClick={(e) => abrirConfirmacaoRetirada(e, venda.id)}
                            className="rounded border border-green-600 bg-white px-2 py-0.5 text-[10px] font-semibold text-green-700 transition-colors hover:bg-green-50"
                            title={conclusaoTitle}
                            type="button"
                          >
                            {conclusaoLabel}
                          </button>
                        )}
                        {entregaStatus && (
                          <StatusBadge
                            intent={entregaStatus.intent || "success"}
                            size="xs"
                            title={entregaStatus.title}
                          >
                            {entregaStatus.label}
                          </StatusBadge>
                        )}
                      </div>
                    </div>

                    {confirmandoRetirada.vendaId === venda.id && (
                      <div
                        onClick={(e) => e.stopPropagation()}
                        className="mt-1.5 flex flex-col gap-1.5"
                      >
                        <input
                          autoFocus
                          type="text"
                          placeholder={
                            venda.tem_entrega
                              ? "Nome de quem recebeu (opcional)"
                              : "Nome de quem esta retirando (opcional)"
                          }
                          value={confirmandoRetirada.nome}
                          onChange={(e) =>
                            setConfirmandoRetirada((prev) => ({
                              ...prev,
                              nome: e.target.value,
                            }))
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              confirmarRetirada(e, venda.id);
                            }
                            if (e.key === "Escape") {
                              setConfirmandoRetirada({
                                vendaId: null,
                                nome: "",
                              });
                            }
                          }}
                          className="w-full text-[11px] px-2 py-1 border border-gray-300 rounded focus:outline-none focus:border-green-500"
                        />
                        <div className="flex gap-1">
                          <button
                            onClick={(e) => confirmarRetirada(e, venda.id)}
                            className="flex-1 text-[10px] bg-green-600 hover:bg-green-700 text-white font-semibold py-1 rounded transition-colors"
                            type="button"
                          >
                            {"\u2705"} Confirmar
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmandoRetirada({
                                vendaId: null,
                                nome: "",
                              });
                            }}
                            className="text-[10px] bg-gray-200 hover:bg-gray-300 text-gray-600 font-semibold px-2 py-1 rounded transition-colors"
                            type="button"
                          >
                            {"\u2715"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      <button
        onClick={() => setPainelVendasAberto(!painelVendasAberto)}
        className="fixed right-0 bottom-20 bg-blue-600 hover:bg-blue-700 text-white rounded-l-lg shadow-lg transition-all z-10 flex items-center gap-1"
        style={{
          right: painelVendasAberto ? "208px" : "0",
          padding: painelVendasAberto ? "6px" : "6px 8px",
        }}
        title={painelVendasAberto ? "Recolher vendas recentes" : "Expandir vendas recentes"}
        type="button"
      >
        {painelVendasAberto ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <>
            <ChevronLeft className="w-4 h-4" />
            <span className="text-[10px] font-medium whitespace-nowrap">Vendas</span>
          </>
        )}
      </button>
    </>
  );
}
