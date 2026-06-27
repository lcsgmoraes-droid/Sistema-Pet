import React from "react";
import {
  FiArrowLeft,
  FiCalendar,
  FiChevronDown,
  FiChevronLeft,
  FiChevronRight,
  FiChevronUp,
  FiCreditCard,
  FiDollarSign,
  FiPackage,
  FiShoppingCart,
} from "react-icons/fi";

import ActionButton from "../../components/ui/ActionButton";
import EmptyState from "../../components/ui/EmptyState";
import ErrorState from "../../components/ui/ErrorState";
import IconActionButton from "../../components/ui/IconActionButton";
import LoadingState from "../../components/ui/LoadingState";
import MetricCard from "../../components/ui/MetricCard";
import MetricGrid from "../../components/ui/MetricGrid";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import ProductIdentity from "../../components/ui/ProductIdentity";
import SaleReference from "../../components/ui/SaleReference";

const formatCurrency = (value) => `R$ ${(Number(value) || 0).toFixed(2).replace(".", ",")}`;

const getTipoIcon = (tipo) => {
  switch (tipo) {
    case "venda":
      return "Venda";
    case "devolucao":
      return "Dev.";
    case "conta_receber":
      return "CR";
    case "recebimento":
      return "Rec.";
    case "credito":
      return "Cred.";
    default:
      return "Mov.";
  }
};

const getTipoLabel = (tipo) => {
  switch (tipo) {
    case "venda":
      return "Venda";
    case "devolucao":
      return "Devolucao";
    case "conta_receber":
      return "Conta a Receber";
    case "recebimento":
      return "Recebimento";
    case "credito":
      return "Credito";
    default:
      return tipo;
  }
};

const getStatusBadge = (status) => {
  const badges = {
    finalizada: "bg-green-100 text-green-700",
    concluida: "bg-green-100 text-green-700",
    pendente: "bg-yellow-100 text-yellow-700",
    paga: "bg-blue-100 text-blue-700",
    cancelada: "bg-red-100 text-red-700",
    devolvida: "bg-red-100 text-red-700",
    efetivado: "bg-green-100 text-green-700",
  };
  return badges[status] || "bg-gray-100 text-gray-700";
};

export default function ClienteFinanceiroView({
  cliente,
  detalhesVendas,
  error,
  expandedRows,
  filtros,
  historico,
  loading,
  loadingDetalhes,
  onAplicarFiltros,
  onLimparFiltros,
  onMudarPagina,
  onNavegarParaVenda,
  onToggleExpansao,
  onVoltarClientes,
  paginacao,
  resumo,
}) {
  const temFiltros =
    filtros.tipo || filtros.status || filtros.data_inicio || filtros.data_fim;

  if (loading && !historico.length) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">
          <Panel>
            <LoadingState label="Carregando historico financeiro..." />
          </Panel>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-2xl">
          <ErrorState
            title="Erro ao carregar dados"
            description={error}
            action={
              <ActionButton onClick={onVoltarClientes} intent="neutral" icon={FiArrowLeft} size="md">
                Voltar para Clientes
              </ActionButton>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="space-y-4">
          <ActionButton onClick={onVoltarClientes} intent="neutral" tone="ghost" icon={FiArrowLeft}>
            Voltar para Clientes
          </ActionButton>

          <PageHeader
            icon={FiCreditCard}
            title="Historico Financeiro"
            subtitle={
              cliente
                ? `${cliente.nome}${cliente.codigo ? ` (${cliente.codigo})` : ""}`
                : "Historico de vendas e movimentacoes do cliente"
            }
          />
        </div>

        {resumo && (
          <MetricGrid className="xl:grid-cols-5">
            <MetricCard
              intent="violet"
              label="Credito disponivel"
              value={formatCurrency(cliente?.credito_atual)}
            />
            <MetricCard
              intent="blue"
              label="Total vendas (90d)"
              value={formatCurrency(resumo.total_vendas_90d)}
            />
            <MetricCard
              intent="amber"
              label="Total em aberto"
              value={formatCurrency(resumo.total_em_aberto)}
            />
            <MetricCard
              intent="emerald"
              label="Ultima compra"
              value={resumo.ultima_compra ? formatCurrency(resumo.ultima_compra.valor) : "-"}
              subtitle={
                resumo.ultima_compra?.data
                  ? new Date(resumo.ultima_compra.data).toLocaleDateString("pt-BR")
                  : "Nenhuma compra"
              }
            />
            <MetricCard
              intent="slate"
              label="Total transacoes"
              value={resumo.total_transacoes_historico || 0}
            />
          </MetricGrid>
        )}

        <Panel
          title="Filtros"
          subtitle="Refine o historico por periodo, tipo, status e quantidade por pagina."
          actions={
            <ActionButton onClick={onLimparFiltros} intent="neutral" tone="ghost" size="sm">
              Limpar filtros
            </ActionButton>
          }
        >
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                <FiCalendar className="inline mr-1" />
                Data Inicio
              </label>
              <input
                type="date"
                value={filtros.data_inicio}
                onChange={(e) => onAplicarFiltros({ data_inicio: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                <FiCalendar className="inline mr-1" />
                Data Fim
              </label>
              <input
                type="date"
                value={filtros.data_fim}
                onChange={(e) => onAplicarFiltros({ data_fim: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Tipo</label>
              <select
                value={filtros.tipo}
                onChange={(e) => onAplicarFiltros({ tipo: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                <option value="">Todas as transacoes</option>
                <option value="venda">Vendas</option>
                <option value="devolucao">Devolucoes</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filtros.status}
                onChange={(e) => onAplicarFiltros({ status: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                <option value="">Todos os status</option>
                <option value="aberta">Em Aberto</option>
                <option value="finalizada">Finalizada (Paga)</option>
                <option value="cancelada">Cancelada</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Por pagina</label>
              <select
                value={filtros.per_page}
                onChange={(e) => onAplicarFiltros({ per_page: parseInt(e.target.value, 10) })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
          </div>
        </Panel>

        <Panel padding="none" className="overflow-hidden">
          {loading ? (
            <LoadingState label="Atualizando historico..." />
          ) : historico.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12"></th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Data
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Tipo
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Descricao
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Valor
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Acoes
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {historico.map((transacao, index) => {
                      const key = `${transacao.tipo}-${index}`;
                      const isExpanded = expandedRows[key];
                      const vendaId = transacao.detalhes?.venda_id;
                      const detalhes = vendaId ? detalhesVendas[vendaId] : null;

                      return (
                        <React.Fragment key={key}>
                          <tr className="hover:bg-gray-50 transition-colors">
                            <td className="px-4 py-4 text-center">
                              <IconActionButton
                                icon={isExpanded ? FiChevronUp : FiChevronDown}
                                intent="neutral"
                                tone="ghost"
                                onClick={() => onToggleExpansao(transacao, index)}
                                title={isExpanded ? "Recolher detalhes" : "Ver detalhes"}
                              />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {transacao.data
                                ? new Date(transacao.data).toLocaleDateString("pt-BR")
                                : "-"}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="inline-flex items-center gap-2 text-sm font-medium">
                                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                                  {getTipoIcon(transacao.tipo)}
                                </span>
                                {getTipoLabel(transacao.tipo)}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-900 max-w-md">
                              <div className="truncate">{transacao.descricao}</div>
                              {transacao.detalhes?.numero_venda && (
                                <div className="text-xs text-blue-600 mt-1">
                                  <SaleReference
                                    showPrefix={false}
                                    value={transacao.detalhes.numero_venda}
                                  />
                                </div>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                              <span
                                className={`font-bold ${
                                  transacao.valor < 0 ? "text-red-600" : "text-green-600"
                                }`}
                              >
                                {transacao.valor < 0 ? "- " : "+ "}
                                {formatCurrency(Math.abs(transacao.valor))}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              <span
                                className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadge(
                                  transacao.status,
                                )}`}
                              >
                                {transacao.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              {transacao.tipo === "venda" && vendaId && (
                                <ActionButton
                                  onClick={() => onNavegarParaVenda(vendaId)}
                                  intent="edit"
                                  icon={FiShoppingCart}
                                  size="xs"
                                >
                                  Ver no PDV
                                </ActionButton>
                              )}
                            </td>
                          </tr>

                          {isExpanded && (
                            <tr>
                              <td colSpan="7" className="px-6 py-4 bg-gray-50">
                                {transacao.tipo === "venda" && vendaId ? (
                                  <DetalhesVenda
                                    detalhes={detalhes}
                                    loading={loadingDetalhes[vendaId]}
                                  />
                                ) : (
                                  <DetalhesTransacao transacao={transacao} />
                                )}
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {paginacao && paginacao.total_paginas > 1 && (
                <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-600">
                      Mostrando {(paginacao.pagina_atual - 1) * paginacao.itens_por_pagina + 1} a{" "}
                      {Math.min(
                        paginacao.pagina_atual * paginacao.itens_por_pagina,
                        paginacao.total_itens,
                      )}{" "}
                      de {paginacao.total_itens} transacoes
                    </div>
                    <div className="flex items-center gap-2">
                      <ActionButton
                        onClick={() => onMudarPagina(paginacao.pagina_atual - 1)}
                        disabled={!paginacao.tem_anterior}
                        intent="neutral"
                        icon={FiChevronLeft}
                        size="sm"
                      >
                        Anterior
                      </ActionButton>
                      <span className="px-4 py-2 text-sm text-gray-700">
                        Pagina {paginacao.pagina_atual} de {paginacao.total_paginas}
                      </span>
                      <ActionButton
                        onClick={() => onMudarPagina(paginacao.pagina_atual + 1)}
                        disabled={!paginacao.tem_proxima}
                        intent="neutral"
                        icon={FiChevronRight}
                        iconPosition="right"
                        size="sm"
                      >
                        Proxima
                      </ActionButton>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState
              icon={FiDollarSign}
              title="Nenhuma transacao encontrada"
              description={
                temFiltros
                  ? "Tente ajustar os filtros para ver mais resultados."
                  : "Ainda nao ha transacoes financeiras para este cliente."
              }
              action={
                temFiltros ? (
                  <ActionButton onClick={onLimparFiltros} intent="neutral" size="md">
                    Limpar filtros
                  </ActionButton>
                ) : null
              }
            />
          )}
        </Panel>
      </div>
    </div>
  );
}

function DetalhesVenda({ detalhes, loading }) {
  if (loading) {
    return <LoadingState compact label="Carregando detalhes..." />;
  }

  if (!detalhes) {
    return (
      <div className="text-center py-4 text-gray-500">
        <p>Nao foi possivel carregar os detalhes da venda</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-gray-200 pb-3">
        <h4 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <FiShoppingCart className="text-blue-600" />
          Detalhes da Venda
          <SaleReference
            showPrefix={false}
            value={detalhes.numero_venda}
            valueClassName="font-semibold"
          />
        </h4>
        <div className="text-sm text-gray-600">
          {new Date(detalhes.data_venda).toLocaleString("pt-BR")}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white rounded-lg p-4 border border-gray-200">
        <div>
          <p className="text-xs text-gray-500 mb-1">Total da Venda</p>
          <p className="text-xl font-bold text-green-600">{formatCurrency(detalhes.total)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Total de Itens</p>
          <p className="text-xl font-bold text-blue-600">{detalhes.itens?.length || 0}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Desconto Total</p>
          <p className="text-xl font-bold text-orange-600">{formatCurrency(detalhes.desconto)}</p>
        </div>
      </div>

      {detalhes.itens && detalhes.itens.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="bg-blue-50 px-4 py-2 border-b border-gray-200">
            <h5 className="font-semibold text-gray-800 flex items-center gap-2">
              <FiPackage className="text-blue-600" />
              Produtos Vendidos
            </h5>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                    Produto
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Qtd</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">
                    Preco Unit.
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">
                    Desc. %
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">
                    Desc. R$
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">
                    Subtotal
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {detalhes.itens.map((item, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">
                      <ProductIdentity product={item} />
                    </td>
                    <td className="px-4 py-3 text-sm text-center font-semibold text-gray-700">
                      {item.quantidade}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-gray-700">
                      {formatCurrency(item.preco_unitario)}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-orange-600">
                      {item.desconto_percentual || 0}%
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-orange-600">
                      {formatCurrency(item.desconto)}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-bold text-green-600">
                      {formatCurrency(item.subtotal)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-50">
                <tr>
                  <td colSpan="5" className="px-4 py-3 text-right text-sm font-semibold text-gray-700">
                    Total Geral:
                  </td>
                  <td className="px-4 py-3 text-right text-lg font-bold text-green-600">
                    {formatCurrency(detalhes.total)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {detalhes.observacoes && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p className="text-xs font-semibold text-yellow-800 mb-1">Observacoes:</p>
          <p className="text-sm text-gray-700">{detalhes.observacoes}</p>
        </div>
      )}
    </div>
  );
}

function DetalhesTransacao({ transacao }) {
  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200">
      <h5 className="font-semibold text-gray-800 mb-3">Detalhes da Transacao</h5>
      <div className="grid grid-cols-2 gap-3 text-sm">
        {Object.entries(transacao.detalhes || {}).map(([key, value]) => (
          <div key={key} className="flex justify-between border-b border-gray-100 pb-2">
            <span className="text-gray-600 capitalize">{key.replace(/_/g, " ")}:</span>
            <span className="font-semibold text-gray-900">
              {typeof value === "number" ? formatCurrency(value) : value?.toString() || "N/A"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
