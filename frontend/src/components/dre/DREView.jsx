import {
  Brain,
  CheckCircle,
  DollarSign,
  FileText,
  MessageCircle,
  Percent,
  RefreshCw,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import AnaliseInteligente from "../AnaliseInteligente";
import ChatIAModal from "../ChatIAModal";
import ClassificarLancamentosModal from "../ClassificarLancamentosModal";
import ExtratoBancario from "../ExtratoBancario";
import ActionButton from "../ui/ActionButton";
import DataTable from "../ui/DataTable";
import ExportActionButton from "../ui/ExportActionButton";
import LoadingState from "../ui/LoadingState";
import MetricCard from "../ui/MetricCard";
import MetricGrid from "../ui/MetricGrid";
import MoneyCell from "../ui/MoneyCell";
import ModuleTabs from "../ui/ModuleTabs";
import NumberCell from "../ui/NumberCell";

export default function DREView({
  DRE_DETAIL_COLUMNS,
  DRE_TABLE_COLUMNS,
  DRE_TABS,
  abrirDetalhesLinha,
  calcularPercentual,
  canaisDisponiveis,
  canaisSelecionados,
  chatIAAberto,
  dados,
  detalhesLinha,
  exportarExcel,
  exportarPDF,
  fecharDetalhesLinha,
  formatarData,
  formatarPercentual,
  handlePeriodoPreset,
  linhaDetalhe,
  limparSelecaoCanais,
  loading,
  loadingDetalhes,
  modalClassificarOpen,
  periodo,
  setChatIAAberto,
  setModalClassificarOpen,
  setPeriodo,
  setTabAtiva,
  tabAtiva,
  toggleCanal,
}) {
  if (loading && !dados) {
    return <LoadingState className="min-h-screen" label="Carregando DRE..." />;
  }

  return (
    <div className="space-y-4 p-3 md:space-y-6 md:p-6">
      {/* Header */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 md:text-3xl">
            📊 DRE - Demonstração do Resultado
          </h1>
          <p className="text-gray-600 mt-1">Análise gerencial de receitas, custos e lucro</p>
        </div>

        <div className="flex flex-wrap gap-2">
          <ActionButton
            onClick={() => setModalClassificarOpen(true)}
            intent="edit"
            size="sm"
            className="shadow-sm"
            title="Classificar lançamentos no DRE"
          >
            <span className="text-base">🏷️</span>
            <span className="font-medium">Classificar</span>
          </ActionButton>
          <ActionButton
            onClick={() => setChatIAAberto(true)}
            intent="neutral"
            tone="soft"
            size="sm"
            className="shadow-sm"
            title="Consultar Especialista IA"
          >
            <MessageCircle size={20} />
            <span className="font-medium">Chat IA</span>
            <Sparkles size={16} className="animate-pulse" />
          </ActionButton>
          <ExportActionButton type="pdf" onClick={exportarPDF} title="Exportar para PDF">
            PDF
          </ExportActionButton>
          <ExportActionButton type="excel" onClick={exportarExcel} title="Exportar para Excel">
            Excel
          </ExportActionButton>
        </div>
      </div>

      {/* Tabs de Navegação */}
      <ModuleTabs
        active={tabAtiva}
        ariaLabel="Abas da DRE"
        onChange={setTabAtiva}
        tabs={DRE_TABS}
      />

      {/* Conteúdo da Tab Demonstrativo */}
      {tabAtiva === "demonstrativo" && (
        <>
          {/* Filtros */}
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex flex-wrap items-end gap-3 md:gap-4">
              {/* Botões de período rápido */}
              <div className="flex flex-wrap gap-2">
                <ActionButton
                  onClick={() => handlePeriodoPreset("mes_atual")}
                  intent="neutral"
                  tone="soft"
                  size="sm"
                >
                  Mês Atual
                </ActionButton>
                <ActionButton
                  onClick={() => handlePeriodoPreset("mes_anterior")}
                  intent="neutral"
                  tone="soft"
                  size="sm"
                >
                  Mês Anterior
                </ActionButton>
                <ActionButton
                  onClick={() => handlePeriodoPreset("ano_atual")}
                  intent="neutral"
                  tone="soft"
                  size="sm"
                >
                  Ano Atual
                </ActionButton>
              </div>

              <div className="min-w-[260px] flex-1">
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Período (Mês/Ano)
                </label>
                <input
                  type="month"
                  value={periodo}
                  onChange={(e) => setPeriodo(e.target.value)}
                  className="h-[38px] w-full rounded-md border border-gray-300 px-3 py-2"
                />
              </div>
            </div>
          </div>

          {/* Conteúdo do DRE */}
          {dados && (
            <div className="space-y-6">
              {/* Cards de Resumo */}
              <MetricGrid>
                <MetricCard
                  intent="emerald"
                  icon={<TrendingUp className="h-5 w-5" />}
                  label="Receita Bruta"
                  value={<MoneyCell value={dados.totais?.receita_bruta || 0} />}
                  subtitle="Base de cálculo"
                />
                <MetricCard
                  intent="red"
                  icon={<TrendingDown className="h-5 w-5" />}
                  label="CMV"
                  value={<MoneyCell value={dados.totais?.cmv || 0} />}
                  subtitle={`${formatarPercentual(
                    calcularPercentual(dados.totais?.cmv, dados.totais?.receita_bruta),
                  )} da receita`}
                />
                <MetricCard
                  intent="blue"
                  icon={<DollarSign className="h-5 w-5" />}
                  label="Lucro Bruto"
                  value={<MoneyCell value={dados.totais?.lucro_bruto || 0} />}
                  subtitle="Após custos"
                />
                <MetricCard
                  intent="violet"
                  icon={<Percent className="h-5 w-5" />}
                  label="Margem Bruta"
                  value={
                    <NumberCell value={dados.totais?.margem_bruta || 0} decimals={2} suffix="%" />
                  }
                  subtitle="Rentabilidade"
                />
              </MetricGrid>

              {/* Seletor de Canais - ABA 7 */}
              <div className="bg-white rounded-lg shadow p-4 md:p-6">
                <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                      <CheckCircle size={20} className="text-blue-600" />
                      Análise por Canal de Vendas
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Selecione os canais para adicionar suas métricas na tabela DRE
                    </p>
                  </div>
                  {canaisSelecionados.length > 0 && (
                    <ActionButton
                      onClick={limparSelecaoCanais}
                      intent="neutral"
                      tone="ghost"
                      size="xs"
                    >
                      Limpar Seleção
                    </ActionButton>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  {canaisDisponiveis.map((canal) => {
                    const selecionado = canaisSelecionados.includes(canal.id);
                    const corClasses = {
                      blue: selecionado
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100",
                      yellow: selecionado
                        ? "bg-yellow-500 text-white border-yellow-500"
                        : "bg-yellow-50 text-yellow-700 border-yellow-200 hover:bg-yellow-100",
                      orange: selecionado
                        ? "bg-orange-500 text-white border-orange-500"
                        : "bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100",
                      green: selecionado
                        ? "bg-green-600 text-white border-green-600"
                        : "bg-green-50 text-green-700 border-green-200 hover:bg-green-100",
                      purple: selecionado
                        ? "bg-purple-600 text-white border-purple-600"
                        : "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100",
                      indigo: selecionado
                        ? "bg-indigo-600 text-white border-indigo-600"
                        : "bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100",
                    };

                    return (
                      <button
                        key={canal.id}
                        onClick={() => toggleCanal(canal.id)}
                        className={`${corClasses[canal.cor]} border-2 rounded-lg p-3 transition-all duration-200 transform md:p-4 ${
                          selecionado ? "scale-105 shadow-lg" : "hover:scale-102"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold">{canal.nome}</span>
                          {selecionado && <CheckCircle size={20} className="flex-shrink-0" />}
                        </div>
                        {selecionado && (
                          <div className="text-xs mt-1 opacity-90">Ativo na tabela</div>
                        )}
                      </button>
                    );
                  })}
                </div>

                {canaisSelecionados.length > 0 && (
                  <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Brain size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-blue-800">
                        <span className="font-semibold">
                          {canaisSelecionados.length} canal(is) selecionado(s).
                        </span>{" "}
                        As métricas de cada canal serão adicionadas na tabela DRE abaixo com suas
                        respectivas receitas, custos e lucros.
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Tabela DRE Detalhada */}
              <div className="overflow-hidden rounded-lg bg-white shadow">
                <DataTable
                  data={dados?.linhas || []}
                  emptyMessage="Nenhuma linha encontrada para o período selecionado"
                  getRowKey={(linha, idx) => `${linha.descricao}-${idx}`}
                  onRowClick={(linha) => abrirDetalhesLinha(linha)}
                  rowClassName={(linha) => {
                    const podeDetalhar = Boolean(linha.detalhavel);
                    const ehTotal = linha.nivel === 0;
                    return [
                      ehTotal ? "font-bold" : "",
                      podeDetalhar
                        ? "cursor-pointer hover:brightness-[0.98]"
                        : linha.origem
                          ? "cursor-help hover:brightness-[0.98]"
                          : "",
                    ]
                      .filter(Boolean)
                      .join(" ");
                  }}
                  tableClassName="min-w-[760px]"
                  theadClassName="bg-gray-50"
                  tbodyClassName="divide-y divide-gray-200"
                  columns={DRE_TABLE_COLUMNS.map((column) => ({
                    ...column,
                    className: (linha) =>
                      [
                        column.className,
                        linha.nivel === 1 && column.key === "descricao" ? "pl-12" : "",
                        linha.nivel === 0 ? "font-bold" : "",
                      ]
                        .filter(Boolean)
                        .join(" "),
                    cellStyle: (linha) =>
                      linha.cor_bg && linha.cor_bg !== "#ffffff"
                        ? { backgroundColor: linha.cor_bg, color: linha.cor }
                        : { color: linha.cor },
                    cellTitle: (linha) =>
                      linha.detalhavel
                        ? "Clique para ver os lançamentos desta linha"
                        : linha.origem || undefined,
                  }))}
                />
              </div>

              {/* Seletor de Canais (removido - nÃ£o necessÃ¡rio com novo endpoint) */}
              {canaisSelecionados.length === 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    ðŸ’¡ A DRE agora mostra automaticamente todos os canais com vendas no perÃ­odo
                    selecionado.
                  </p>
                </div>
              )}
            </div>
          )}

          {!dados && !loading && (
            <div className="bg-gray-50 rounded-lg p-12 text-center">
              <FileText className="mx-auto mb-4 text-gray-400" size={64} />
              <p className="text-gray-600 text-lg">Selecione um período para visualizar a DRE</p>
            </div>
          )}
        </>
      )}

      {/* Conteúdo da Tab Extrato Bancário */}
      {tabAtiva === "extrato" && <ExtratoBancario />}

      {/* Conteúdo da Tab Análise Inteligente */}
      {tabAtiva === "analise" && (
        <AnaliseInteligente dados={dados} periodo={{ mes: periodo.mes, ano: periodo.ano }} />
      )}

      {/* Modal Chat IA */}
      <ChatIAModal
        isOpen={chatIAAberto}
        onClose={() => setChatIAAberto(false)}
        contexto={{
          tipo: "DRE",
          periodo: `${periodo.mes}/${periodo.ano}`,
          valor: dados?.lucro_liquido,
          dados: dados,
        }}
      />

      {/* Modal Classificar DRE */}
      <ClassificarLancamentosModal
        isOpen={modalClassificarOpen}
        onClose={() => setModalClassificarOpen(false)}
      />

      {linhaDetalhe && (
        <div className="fixed inset-0 z-[70] bg-slate-900/30" onClick={fecharDetalhesLinha}>
          <aside
            className="fixed inset-x-0 bottom-0 max-h-[86dvh] overflow-hidden rounded-t-2xl bg-white shadow-2xl md:inset-y-0 md:left-auto md:right-0 md:max-h-none md:w-[760px] md:rounded-none"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex h-full flex-col">
              <div className="border-b border-gray-200 p-4 md:p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Lancamentos da DRE
                    </p>
                    <h2 className="mt-1 text-lg font-bold text-gray-900 md:text-xl">
                      {linhaDetalhe.descricao}
                    </h2>
                    <p className="mt-1 text-sm text-gray-600">
                      {detalhesLinha?.periodo || periodo} • {linhaDetalhe.canal_nome}
                    </p>
                  </div>
                  <ActionButton
                    type="button"
                    onClick={fecharDetalhesLinha}
                    intent="neutral"
                    tone="ghost"
                    size="sm"
                    aria-label="Fechar detalhes"
                  >
                    <X size={20} />
                  </ActionButton>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase text-gray-500">Total da linha</p>
                    <p className="mt-1 text-lg font-bold text-gray-900">
                      <MoneyCell value={detalhesLinha?.total ?? linhaDetalhe.valor} />
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase text-gray-500">Lancamentos</p>
                    <p className="mt-1 text-lg font-bold text-gray-900">
                      <NumberCell value={detalhesLinha?.total_itens} zeroAsDash />
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase text-gray-500">Fonte</p>
                    <p className="mt-1 text-sm font-semibold text-gray-800">
                      {detalhesLinha?.items?.[0]?.origem_label || "Aguardando dados"}
                    </p>
                  </div>
                </div>

                {detalhesLinha?.origem && (
                  <p className="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800">
                    {detalhesLinha.origem}
                  </p>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-4 md:p-5">
                {loadingDetalhes ? (
                  <div className="flex h-48 items-center justify-center text-gray-500">
                    <RefreshCw className="mr-2 animate-spin" size={18} />
                    Carregando lancamentos...
                  </div>
                ) : (detalhesLinha?.items || []).length === 0 ? (
                  <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
                    Nenhum lancamento encontrado para esta linha no periodo.
                  </div>
                ) : (
                  <>
                    <div className="hidden overflow-hidden rounded-lg border border-gray-200 md:block">
                      <DataTable
                        columns={DRE_DETAIL_COLUMNS}
                        data={detalhesLinha.items}
                        getCellContext={() => ({ formatarData })}
                        getRowKey={(item, index) => item.id || index}
                        tableClassName="min-w-full"
                        theadClassName="bg-gray-50"
                        tbodyClassName="divide-y divide-gray-100 bg-white"
                      />
                    </div>

                    <div className="space-y-3 md:hidden">
                      {detalhesLinha.items.map((item) => (
                        <div
                          key={item.id}
                          className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-xs font-medium text-gray-500">
                                {formatarData(item.data)} • {item.origem_label}
                              </p>
                              <h3 className="mt-1 text-sm font-semibold text-gray-900">
                                {item.descricao}
                              </h3>
                              {item.contraparte && (
                                <p className="mt-1 text-xs text-gray-500">{item.contraparte}</p>
                              )}
                            </div>
                            <p className="shrink-0 text-sm font-bold text-gray-900">
                              <MoneyCell value={item.valor} zeroAsDash />
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {detalhesLinha && detalhesLinha.pages > 1 && (
                <div className="flex items-center justify-between border-t border-gray-200 p-4 text-sm">
                  <ActionButton
                    type="button"
                    disabled={loadingDetalhes || detalhesLinha.page <= 1}
                    onClick={() => abrirDetalhesLinha(linhaDetalhe, detalhesLinha.page - 1)}
                    intent="neutral"
                    tone="soft"
                    size="sm"
                  >
                    Anterior
                  </ActionButton>
                  <span className="text-gray-600">
                    Pagina {detalhesLinha.page} de {detalhesLinha.pages}
                  </span>
                  <ActionButton
                    type="button"
                    disabled={loadingDetalhes || detalhesLinha.page >= detalhesLinha.pages}
                    onClick={() => abrirDetalhesLinha(linhaDetalhe, detalhesLinha.page + 1)}
                    intent="neutral"
                    tone="soft"
                    size="sm"
                  >
                    Proxima
                  </ActionButton>
                </div>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
