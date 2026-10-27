import React from "react";
import {
  FiArrowLeft,
  FiChevronDown,
  FiChevronLeft,
  FiChevronRight,
  FiChevronUp,
  FiCreditCard,
  FiDollarSign,
  FiDownload,
  FiPackage,
  FiShoppingCart,
} from "react-icons/fi";

import EmptyState from "../../components/ui/EmptyState";
import ErrorState from "../../components/ui/ErrorState";
import LoadingState from "../../components/ui/LoadingState";
import MetricCard from "../../components/ui/MetricCard";
import MetricGrid from "../../components/ui/MetricGrid";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import ProductIdentity from "../../components/ui/ProductIdentity";
import SaleReference from "../../components/ui/SaleReference";
import ClienteBaixasLotePanel from "../../components/clientes/ClienteBaixasLotePanel";

import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputData from "../../components/v2/InputData/InputData";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import { formatMoneyBRL } from "../../utils/formatters.js";
import {
  camposDetalhesHistorico,
  formatarDataHistorico,
  obterStatusHistorico,
} from "../../utils/historicoFinanceiro.js";

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

const getStatusBadge = (tom) =>
  ({
    sucesso: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-200",
    atencao: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
    perigo: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-200",
    neutro: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  })[tom] || "bg-slate-100 text-slate-700";

export default function ClienteFinanceiroView({
  cliente,
  detalhesVendas,
  error,
  expandedRows,
  filtros,
  gerandoPdf,
  historico,
  loading,
  loadingDetalhes,
  onAplicarFiltros,
  onFinanceiroAtualizado,
  onExportarPdf,
  onLimparFiltros,
  onMudarPagina,
  onNavegarParaVenda,
  onToggleExpansao,
  onVoltarClientes,
  paginacao,
  resumo,
}) {
  const temFiltros = filtros.tipo || filtros.status || filtros.data_inicio || filtros.data_fim;

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
              <BotaoInteracao onClick={onVoltarClientes} icon={FiArrowLeft}>
                Voltar para Clientes
              </BotaoInteracao>
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
          <BotaoInteracao onClick={onVoltarClientes} icon={FiArrowLeft}>
            Voltar para Clientes
          </BotaoInteracao>

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
              value={formatMoneyBRL(cliente?.credito_atual)}
            />
            <MetricCard
              intent="blue"
              label="Total vendas (90d)"
              value={formatMoneyBRL(resumo.total_vendas_90d)}
            />
            <MetricCard
              intent="amber"
              label="Total em aberto"
              value={formatMoneyBRL(resumo.total_em_aberto)}
            />
            <MetricCard
              intent="emerald"
              label="Ultima compra"
              value={resumo.ultima_compra ? formatMoneyBRL(resumo.ultima_compra.valor) : "-"}
              subtitle={
                resumo.ultima_compra?.data
                  ? formatarDataHistorico(resumo.ultima_compra.data)
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

        {cliente?.id ? (
          <ClienteBaixasLotePanel
            key={cliente.id}
            clienteId={cliente.id}
            onAtualizado={onFinanceiroAtualizado}
          />
        ) : null}

        <Panel
          title="Filtros"
          subtitle="Refine o historico por periodo, tipo, status e quantidade por pagina."
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <BotaoInteracao onClick={onLimparFiltros} tamanho="pequeno">
                Limpar filtros
              </BotaoInteracao>
              <BotaoInteracao
                onClick={onExportarPdf}
                disabled={loading || !paginacao?.total_itens}
                loading={gerandoPdf}
                icon={FiDownload}
                tamanho="pequeno"
              >
                {gerandoPdf ? "Gerando PDF..." : "Gerar PDF"}
              </BotaoInteracao>
            </div>
          }
        >
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <InputData
              label="Data inicial"
              value={filtros.data_inicio}
              onChange={(data_inicio) => onAplicarFiltros({ data_inicio })}
            />
            <InputData
              label="Data final"
              value={filtros.data_fim}
              onChange={(data_fim) => onAplicarFiltros({ data_fim })}
            />
            <InputCombobox
              label="Tipo"
              value={filtros.tipo}
              onChange={(tipo) => onAplicarFiltros({ tipo: tipo || "" })}
              opcoes={[
                { value: "", label: "Todas as transações" },
                { value: "venda", label: "Vendas" },
                { value: "devolucao", label: "Devoluções" },
                { value: "conta_receber", label: "Contas a receber" },
                { value: "recebimento", label: "Recebimentos" },
                { value: "credito", label: "Créditos" },
              ]}
            />
            <InputCombobox
              label="Situação"
              value={filtros.status}
              onChange={(status) => onAplicarFiltros({ status: status || "" })}
              opcoes={[
                { value: "", label: "Todas as situações" },
                { value: "em_aberto", label: "Em aberto" },
                { value: "vencido", label: "Vencido" },
                { value: "parcial", label: "Parcial" },
                { value: "recebido", label: "Pago / recebido" },
                { value: "cancelado", label: "Cancelada" },
                { value: "estornado", label: "Estornado" },
              ]}
            />
            <InputCombobox
              label="Por página"
              value={filtros.per_page}
              onChange={(per_page) => onAplicarFiltros({ per_page: Number(per_page) || 20 })}
              permitirLimpar={false}
              opcoes={[10, 20, 50, 100].map((value) => ({ value, label: String(value) }))}
            />
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
                      const situacao = obterStatusHistorico(transacao);
                      const isExpanded = expandedRows[key];
                      const vendaId = transacao.detalhes?.venda_id;
                      const detalhes = vendaId ? detalhesVendas[vendaId] : null;

                      return (
                        <React.Fragment key={key}>
                          <tr className="hover:bg-gray-50 transition-colors">
                            <td className="px-4 py-4 text-center">
                              <BotaoInteracao
                                icon={isExpanded ? FiChevronUp : FiChevronDown}
                                onClick={() => onToggleExpansao(transacao, index)}
                                title={isExpanded ? "Recolher detalhes" : "Ver detalhes"}
                                aria-label={isExpanded ? "Recolher detalhes" : "Ver detalhes"}
                                aria-expanded={isExpanded}
                                tamanho="pequeno"
                              />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {transacao.data ? formatarDataHistorico(transacao.data) : "-"}
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
                              <div className="whitespace-pre-wrap break-words">
                                {transacao.descricao}
                              </div>
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
                                {formatMoneyBRL(Math.abs(transacao.valor))}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              <span
                                className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadge(
                                  situacao.tom,
                                )}`}
                              >
                                {situacao.label}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              {transacao.tipo === "venda" && vendaId && (
                                <BotaoInteracao
                                  onClick={() => onNavegarParaVenda(vendaId)}
                                  icon={FiShoppingCart}
                                  tamanho="pequeno"
                                >
                                  Ver no PDV
                                </BotaoInteracao>
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
                      <BotaoInteracao
                        onClick={() => onMudarPagina(paginacao.pagina_atual - 1)}
                        disabled={!paginacao.tem_anterior}
                        icon={FiChevronLeft}
                        tamanho="pequeno"
                      >
                        Anterior
                      </BotaoInteracao>
                      <span className="px-4 py-2 text-sm text-gray-700">
                        Pagina {paginacao.pagina_atual} de {paginacao.total_paginas}
                      </span>
                      <BotaoInteracao
                        onClick={() => onMudarPagina(paginacao.pagina_atual + 1)}
                        disabled={!paginacao.tem_proxima}
                        icon={FiChevronRight}
                        tamanho="pequeno"
                      >
                        Proxima
                      </BotaoInteracao>
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
                  <BotaoInteracao onClick={onLimparFiltros}>Limpar filtros</BotaoInteracao>
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
          {formatarDataHistorico(detalhes.data_venda, { comHora: true })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white rounded-lg p-4 border border-gray-200">
        <div>
          <p className="text-xs text-gray-500 mb-1">Total da Venda</p>
          <p className="text-xl font-bold text-green-600">{formatMoneyBRL(detalhes.total)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Total de Itens</p>
          <p className="text-xl font-bold text-blue-600">{detalhes.itens?.length || 0}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Desconto Total</p>
          <p className="text-xl font-bold text-orange-600">{formatMoneyBRL(detalhes.desconto)}</p>
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
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Produto</th>
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
                      {formatMoneyBRL(item.preco_unitario)}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-orange-600">
                      {item.desconto_percentual || 0}%
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-orange-600">
                      {formatMoneyBRL(item.desconto)}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-bold text-green-600">
                      {formatMoneyBRL(item.subtotal)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-50">
                <tr>
                  <td
                    colSpan="5"
                    className="px-4 py-3 text-right text-sm font-semibold text-gray-700"
                  >
                    Total Geral:
                  </td>
                  <td className="px-4 py-3 text-right text-lg font-bold text-green-600">
                    {formatMoneyBRL(detalhes.total)}
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
          <p className="whitespace-pre-wrap break-words text-sm text-gray-700">
            {detalhes.observacoes}
          </p>
        </div>
      )}
    </div>
  );
}

export function DetalhesTransacao({ transacao }) {
  const detalhes = camposDetalhesHistorico(transacao);
  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200 dark:bg-slate-900 dark:border-slate-700">
      <h5 className="font-semibold text-gray-800 mb-3 dark:text-slate-100">
        {getTipoLabel(transacao.tipo)} — detalhes
      </h5>
      <dl className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
        {detalhes.map(({ chave, label, tipo, valor }) => (
          <div
            key={chave}
            className={`border-b border-gray-100 pb-2 dark:border-slate-700 ${tipo === "observacao" ? "md:col-span-2" : ""}`}
          >
            <dt className="text-gray-600 dark:text-slate-400">{label}</dt>
            <dd className="whitespace-pre-wrap break-words font-semibold text-gray-900 dark:text-slate-100">
              {valor}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
