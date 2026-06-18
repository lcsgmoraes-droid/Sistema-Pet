import { BarChart3, Calendar, Filter } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import ExportActionButton from "../ui/ExportActionButton";
import FilterBar, { FilterRow } from "../ui/FilterBar";
import ModuleTabs from "../ui/ModuleTabs";
import { VENDAS_FINANCEIRO_CHANNEL_FILTERS } from "./vendasFinanceiroChannels";

const FILTROS_RAPIDOS = [
  { id: "hoje", label: "Hoje" },
  { id: "ontem", label: "Ontem" },
  { id: "esta_semana", label: "Esta semana" },
  { id: "este_mes", label: "Este mes" },
  { id: "mes_anterior", label: "Mes anterior" },
  { id: "ultimos_7_dias", label: "Ultimos 7 dias" },
  { id: "ultimos_30_dias", label: "Ultimos 30 dias" },
  { id: "este_ano", label: "Este ano" },
  { id: "personalizado", label: "Personalizado" },
];

export default function VendasFinanceiroHeader({
  abaAtiva,
  abasVendasFinanceiro,
  aplicarFiltroRapido,
  dataFim,
  dataInicio,
  exportarParaExcel,
  exportarParaPDF,
  exportarRelatorioListaVendas,
  filtroCategoria,
  filtroCanalVenda,
  filtroFormaPagamento,
  filtroFuncionario,
  filtroSelecionado,
  formasRecebimentoConsolidadas,
  formatarData,
  menuRelatoriosAberto,
  menuRelatoriosRef,
  modoComparacao,
  mostrarGraficos,
  periodoComparacao,
  podeVerFinanceiroCompleto,
  produtosDetalhados,
  setAbaAtiva,
  setDataFim,
  setDataInicio,
  setFiltroCategoria,
  setFiltroCanalVenda,
  setFiltroFormaPagamento,
  setFiltroFuncionario,
  setFiltroSelecionado,
  setMenuRelatoriosAberto,
  setModalRelatorioAberto,
  setModoComparacao,
  setMostrarGraficos,
  setPeriodoComparacao,
  vendasPorFuncionario,
}) {
  const tituloExportacaoPDF =
    dataInicio && dataFim
      ? `Exportar PDF de ${formatarData(dataInicio)} ate ${formatarData(dataFim)}`
      : "Selecione um periodo";

  const tituloExportacaoExcel =
    dataInicio && dataFim
      ? `Exportar dados de ${formatarData(dataInicio)} ate ${formatarData(dataFim)}`
      : "Selecione um periodo";

  return (
    <div className="mb-6 rounded-lg bg-white p-3 shadow sm:p-4">
      <div className="mb-4 flex flex-col gap-3 2xl:flex-row 2xl:items-start 2xl:justify-between">
        <h1 className="text-xl font-bold text-gray-800 sm:text-2xl">Consulta de Vendas</h1>

        {podeVerFinanceiroCompleto ? (
          <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2 lg:flex lg:flex-wrap lg:items-center lg:justify-end 2xl:w-auto">
            <div
              className="relative w-full sm:col-span-2 lg:col-span-1 lg:w-auto"
              ref={menuRelatoriosRef}
            >
              <ExportActionButton
                className="w-full justify-center lg:w-auto"
                type="report"
                onClick={() => setMenuRelatoriosAberto((prev) => !prev)}
                title="Abrir relatorios do periodo"
              >
                Relatorios
              </ExportActionButton>

              {menuRelatoriosAberto && (
                <div className="absolute left-0 z-40 mt-2 w-[calc(100vw_-_2rem)] max-w-sm rounded-lg border border-gray-200 bg-white shadow-lg sm:left-auto sm:right-0 sm:w-80">
                  <button
                    onClick={() => {
                      setMenuRelatoriosAberto(false);
                      exportarRelatorioListaVendas({ escopo: "geral" });
                    }}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50"
                  >
                    Relatorio geral da lista de vendas
                  </button>
                  <button
                    onClick={() => {
                      setMenuRelatoriosAberto(false);
                      exportarRelatorioListaVendas({ escopo: "filtrado" });
                    }}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                  >
                    Relatorio do que filtrei
                  </button>
                  <button
                    onClick={() => {
                      setMenuRelatoriosAberto(false);
                      setModalRelatorioAberto(true);
                    }}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                  >
                    Relatorio personalizado
                  </button>
                </div>
              )}
            </div>

            <ExportActionButton
              className="w-full justify-center lg:w-auto"
              type="pdf"
              onClick={exportarParaPDF}
              disabled={!dataInicio || !dataFim}
              title={tituloExportacaoPDF}
            >
              PDF
            </ExportActionButton>

            <ExportActionButton
              className="w-full justify-center lg:w-auto"
              type="excel"
              onClick={exportarParaExcel}
              disabled={!dataInicio || !dataFim}
              title={tituloExportacaoExcel}
            >
              Excel
            </ExportActionButton>

            <label className="flex min-h-[44px] w-full cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 sm:col-span-2 lg:min-h-0 lg:w-auto lg:border-0 lg:px-0 lg:py-0">
              <input
                type="checkbox"
                checked={modoComparacao}
                onChange={(event) => setModoComparacao(event.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm font-medium text-gray-700">Comparar com:</span>
            </label>

            {modoComparacao && (
              <select
                value={periodoComparacao}
                onChange={(event) => setPeriodoComparacao(event.target.value)}
                className="h-11 w-full min-w-0 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium lg:h-9 lg:w-auto lg:max-w-xs"
              >
                <option value="periodo_anterior">
                  Periodo imediatamente anterior (mesmo numero de dias)
                </option>
                <option value="mes_anterior">Mesmo periodo do mes passado</option>
                <option value="ano_anterior">Mesmo periodo do ano passado</option>
              </select>
            )}
          </div>
        ) : null}
      </div>

      {!podeVerFinanceiroCompleto && (
        <div className="mb-4 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-700">
          Acesso limitado: voce pode consultar apenas a aba Historico por Cliente.
        </div>
      )}

      {podeVerFinanceiroCompleto && (
        <div className="-mx-1 mb-4 flex gap-2 overflow-x-auto px-1 pb-1 sm:flex-wrap sm:overflow-visible">
          {FILTROS_RAPIDOS.map((filtro) => (
            <button
              key={filtro.id}
              onClick={() => {
                if (filtro.id === "personalizado") {
                  setFiltroSelecionado("personalizado");
                  return;
                }

                aplicarFiltroRapido(filtro.id);
              }}
              className={`shrink-0 rounded px-3 py-2 text-sm font-medium transition-colors sm:py-1 ${
                filtroSelecionado === filtro.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {filtro.label}
            </button>
          ))}
        </div>
      )}

      {podeVerFinanceiroCompleto && filtroSelecionado === "personalizado" && (
        <div className="mb-4 rounded bg-gray-50 p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-600 sm:mb-0 sm:hidden">
            <Calendar className="h-5 w-5 text-gray-500" />
            Periodo personalizado
          </div>
          <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-[auto_minmax(0,180px)_auto_minmax(0,180px)] sm:items-center">
            <Calendar className="hidden h-5 w-5 text-gray-500 sm:block" />
            <input
              type="date"
              value={dataInicio}
              onChange={(event) => setDataInicio(event.target.value)}
              className="w-full rounded border px-3 py-2"
            />
            <span className="text-center text-sm text-gray-600 sm:text-left">ate</span>
            <input
              type="date"
              value={dataFim}
              onChange={(event) => setDataFim(event.target.value)}
              className="w-full rounded border px-3 py-2"
            />
          </div>
        </div>
      )}

      {podeVerFinanceiroCompleto && (
        <FilterBar
          className="mb-4 border-blue-200 bg-blue-50/70"
          onSubmit={(event) => event.preventDefault()}
          padding="sm"
        >
          <FilterRow className="items-stretch lg:items-center">
            <div className="flex w-full items-center gap-2 text-sm font-medium text-slate-700 lg:w-auto">
              <Filter className="h-5 w-5 text-blue-600" />
              <span>Filtros avancados:</span>
            </div>

            <select
              value={filtroCanalVenda}
              onChange={(event) => setFiltroCanalVenda(event.target.value)}
              title={filtroCanalVenda ? "Canal selecionado" : "Todos os canais"}
              className="h-11 w-full min-w-0 rounded-md border border-slate-300 bg-white px-3 text-sm sm:min-w-[200px] sm:flex-1 lg:h-9 lg:w-auto lg:min-w-[160px] lg:flex-none"
            >
              {VENDAS_FINANCEIRO_CHANNEL_FILTERS.map((canal) => (
                <option key={`canal-${canal.value || "todos"}`} value={canal.value}>
                  {canal.filterLabel}
                </option>
              ))}
            </select>

            <select
              value={filtroFuncionario}
              onChange={(event) => setFiltroFuncionario(event.target.value)}
              className="h-11 w-full min-w-0 rounded-md border border-slate-300 bg-white px-3 text-sm sm:min-w-[220px] sm:flex-1 lg:h-9 lg:w-auto lg:min-w-[180px] lg:flex-none"
            >
              <option value="">Todos os funcionarios</option>
              {vendasPorFuncionario.map((funcionario) => (
                <option
                  key={`func-${funcionario.funcionario || "sem-nome"}`}
                  value={funcionario.funcionario}
                >
                  {funcionario.funcionario}
                </option>
              ))}
            </select>

            <select
              value={filtroFormaPagamento}
              onChange={(event) => setFiltroFormaPagamento(event.target.value)}
              className="h-11 w-full min-w-0 rounded-md border border-slate-300 bg-white px-3 text-sm sm:min-w-[220px] sm:flex-1 lg:h-9 lg:w-auto lg:min-w-[180px] lg:flex-none"
            >
              <option value="">Todas as formas</option>
              {formasRecebimentoConsolidadas.map((forma) => (
                <option
                  key={`forma-${forma.forma_pagamento || "sem-forma"}`}
                  value={forma.forma_pagamento}
                >
                  {forma.forma_pagamento}
                </option>
              ))}
            </select>

            <select
              value={filtroCategoria}
              onChange={(event) => setFiltroCategoria(event.target.value)}
              className="h-11 w-full min-w-0 rounded-md border border-slate-300 bg-white px-3 text-sm sm:min-w-[220px] sm:flex-1 lg:h-9 lg:w-auto lg:min-w-[180px] lg:flex-none"
            >
              <option value="">Todas as categorias</option>
              {produtosDetalhados.map((categoria) => (
                <option
                  key={`cat-${categoria.categoria || "sem-categoria"}`}
                  value={categoria.categoria}
                >
                  {categoria.categoria}
                </option>
              ))}
            </select>

            <ActionButton
              intent="neutral"
              tone="soft"
              size="md"
              className="w-full justify-center sm:w-auto sm:flex-1 lg:w-auto lg:flex-none"
              onClick={() => {
                setFiltroCanalVenda("");
                setFiltroFuncionario("");
                setFiltroFormaPagamento("");
                setFiltroCategoria("");
              }}
            >
              Limpar filtros
            </ActionButton>

            <ActionButton
              onClick={() => setMostrarGraficos(!mostrarGraficos)}
              intent="edit"
              size="md"
              icon={BarChart3}
              className="w-full justify-center sm:w-auto sm:flex-1 lg:ml-auto lg:w-auto lg:flex-none"
            >
              {mostrarGraficos ? "Ocultar" : "Mostrar"} graficos
            </ActionButton>
          </FilterRow>
        </FilterBar>
      )}

      <ModuleTabs
        active={abaAtiva}
        ariaLabel="Abas do financeiro de vendas"
        onChange={setAbaAtiva}
        tabs={abasVendasFinanceiro}
      />
    </div>
  );
}
