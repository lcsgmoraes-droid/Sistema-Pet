import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  X,
} from "lucide-react";
import { formatMoneyBRL } from "../../utils/formatters";

function getCanalInfo(canal) {
  return (
    {
      ecommerce: {
        cor: "border-l-purple-500",
        bg: "bg-purple-50",
        icon: "🛒",
        label: "Ecommerce",
      },
      aplicativo: {
        cor: "border-l-green-500",
        bg: "bg-green-50",
        icon: "📱",
        label: "App",
      },
      loja_fisica: {
        cor: "border-l-blue-500",
        bg: "bg-blue-50",
        icon: "🏪",
        label: "PDV",
      },
    }[canal] || {
      cor: "border-l-gray-400",
      bg: "bg-gray-50",
      icon: "🏪",
      label: "PDV",
    }
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
  setConfirmandoRetirada,
}) {
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
              <button
                onClick={() => setPainelVendasAberto(false)}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title="Fechar painel"
                type="button"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            <div className="flex space-x-1 mb-3">
              {["24h", "7d", "30d"].map((periodo) => (
                <button
                  key={periodo}
                  onClick={() => setFiltroVendas(periodo)}
                  className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    filtroVendas === periodo
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                  type="button"
                >
                  {periodo === "24h" && "Últimas 24h"}
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
                  className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${
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
              <span className="text-xs font-medium text-gray-700">
                Apenas com entrega
              </span>
            </label>

            <div className="px-2 pb-2">
              <input
                type="text"
                value={buscaNumeroVenda}
                onChange={(e) => setBuscaNumeroVenda(e.target.value)}
                placeholder="Buscar por número..."
                className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {vendasRecentes.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-xs">Nenhuma venda encontrada</p>
              </div>
            ) : (
              vendasRecentes.map((venda) => {
                const canalInfo = getCanalInfo(venda.canal);

                return (
                  <div
                    key={venda.id}
                    onClick={() => reabrirVenda(venda)}
                    className={`rounded-lg p-2.5 border border-gray-200 border-l-4 ${canalInfo.cor} hover:border-blue-300 cursor-pointer transition-colors ${canalInfo.bg}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-gray-500 flex items-center gap-0.5">
                        <span>{canalInfo.icon}</span>
                        <span>{canalInfo.label}</span>
                        {venda.tem_entrega && (
                          <span className="ml-1" title="Entrega">
                            🚚
                          </span>
                        )}
                      </span>
                      {venda.palavra_chave_retirada && (
                        <span
                          className="text-[10px] bg-orange-100 text-orange-700 font-semibold px-1.5 py-0.5 rounded-full border border-orange-200"
                          title="Senha de retirada"
                        >
                          🔑 {venda.palavra_chave_retirada}
                        </span>
                      )}
                    </div>

                    <div className="flex items-start justify-between mb-1.5">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {venda.cliente_nome || "Cliente não informado"}
                        </div>
                        <div className="text-xs text-gray-500">
                          #{venda.numero_venda}
                        </div>
                      </div>
                      <div className="text-right ml-2 flex-shrink-0">
                        {venda.status === "baixa_parcial" ? (
                          <>
                            <div className="text-[10px] text-gray-500">
                              Pago
                            </div>
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
                        <div
                          className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full mt-1 inline-block ${
                            venda.status === "pago_nf"
                              ? "bg-emerald-100 text-emerald-700"
                              : venda.status === "finalizada"
                                ? "bg-green-100 text-green-700"
                                : venda.status === "baixa_parcial"
                                  ? "bg-blue-100 text-blue-700"
                                  : venda.status === "aberta"
                                    ? "bg-yellow-100 text-yellow-700"
                                    : "bg-red-100 text-red-700"
                          }`}
                        >
                          {venda.status === "pago_nf" && "Pago NF"}
                          {venda.status === "finalizada" && "Pago"}
                          {venda.status === "baixa_parcial" && "Parcial"}
                          {venda.status === "aberta" && "Aberta"}
                          {venda.status === "cancelada" && "Cancelada"}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="text-[10px] text-gray-500">
                        {formatarDataVenda(venda.data_venda)}
                      </div>
                      {venda.tipo_retirada === "terceiro" &&
                        venda.status_entrega !== "entregue" &&
                        confirmandoRetirada.vendaId !== venda.id && (
                          <button
                            onClick={(e) =>
                              abrirConfirmacaoRetirada(e, venda.id)
                            }
                            className="text-[10px] bg-white hover:bg-green-50 text-green-700 font-semibold px-2 py-0.5 rounded border border-green-600 transition-colors"
                            type="button"
                          >
                            Confirmar retirada
                          </button>
                        )}
                      {venda.status_entrega === "entregue" &&
                        venda.retirado_por && (
                          <span
                            className="text-[10px] text-green-600 font-medium"
                            title={`Retirado por: ${venda.retirado_por}`}
                          >
                            ✅ {venda.retirado_por}
                          </span>
                        )}
                      {venda.status_entrega === "entregue" &&
                        !venda.retirado_por && (
                          <span className="text-[10px] text-green-600 font-medium">
                            ✅ Retirado
                          </span>
                        )}
                    </div>

                    {confirmandoRetirada.vendaId === venda.id && (
                      <div
                        onClick={(e) => e.stopPropagation()}
                        className="mt-1.5 flex flex-col gap-1.5"
                      >
                        <input
                          autoFocus
                          type="text"
                          placeholder="Nome de quem está retirando (opcional)"
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
                            ✅ Confirmar
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
                            ✕
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
        title={
          painelVendasAberto
            ? "Recolher vendas recentes"
            : "Expandir vendas recentes"
        }
        type="button"
      >
        {painelVendasAberto ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <>
            <ChevronLeft className="w-4 h-4" />
            <span className="text-[10px] font-medium whitespace-nowrap">
              Vendas
            </span>
          </>
        )}
      </button>
    </>
  );
}
