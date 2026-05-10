import { BarChart3, Calendar, Filter } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import ExportActionButton from "../ui/ExportActionButton";
import FilterBar, { FilterRow } from "../ui/FilterBar";
import ModuleTabs from "../ui/ModuleTabs";

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
    <div className="mb-6 bg-white p-4 rounded-lg shadow">
      <div className="mb-4 flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <h1 className="text-2xl font-bold text-gray-800">
          Consulta de Vendas
        </h1>

        {podeVerFinanceiroCompleto ? (
          <div className="flex flex-wrap items-center gap-3 xl:justify-end">
            <div className="relative" ref={menuRelatoriosRef}>
              <ExportActionButton
                type="report"
                onClick={() => setMenuRelatoriosAberto((prev) => !prev)}
                title="Abrir relatorios do periodo"
              >
                Relatorios
              </ExportActionButton>

              {menuRelatoriosAberto && (
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 z-40">
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
              type="pdf"
              onClick={exportarParaPDF}
              disabled={!dataInicio || !dataFim}
              title={tituloExportacaoPDF}
            >
              PDF
            </ExportActionButton>

            <ExportActionButton
              type="excel"
              onClick={exportarParaExcel}
              disabled={!dataInicio || !dataFim}
              title={tituloExportacaoExcel}
            >
              Excel
            </ExportActionButton>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={modoComparacao}
                onChange={(event) => setModoComparacao(event.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm font-medium text-gray-700">
                Comparar com:
              </span>
            </label>

            {modoComparacao && (
              <select
                value={periodoComparacao}
                onChange={(event) => setPeriodoComparacao(event.target.value)}
                className="border rounded px-3 py-2 text-sm bg-blue-50 font-medium"
              >
                <option value="periodo_anterior">
                  Periodo imediatamente anterior (mesmo numero de dias)
                </option>
                <option value="mes_anterior">
                  Mesmo periodo do mes passado
                </option>
                <option value="ano_anterior">
                  Mesmo periodo do ano passado
                </option>
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
        <div className="flex flex-wrap gap-2 mb-4">
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
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
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
        <div className="flex gap-2 items-center mb-4 p-3 bg-gray-50 rounded">
          <Calendar className="w-5 h-5 text-gray-500" />
          <input
            type="date"
            value={dataInicio}
            onChange={(event) => setDataInicio(event.target.value)}
            className="border rounded px-3 py-2"
          />
          <span className="text-gray-600">ate</span>
          <input
            type="date"
            value={dataFim}
            onChange={(event) => setDataFim(event.target.value)}
            className="border rounded px-3 py-2"
          />
        </div>
      )}

      {podeVerFinanceiroCompleto && (
        <FilterBar
          className="mb-4 border-blue-200 bg-blue-50/70"
          onSubmit={(event) => event.preventDefault()}
          padding="sm"
        >
          <FilterRow className="items-center">
            <div className="inline-flex items-center gap-2 text-sm font-medium text-slate-700">
              <Filter className="h-5 w-5 text-blue-600" />
              <span>Filtros avancados:</span>
            </div>

            <select
              value={filtroFuncionario}
              onChange={(event) => setFiltroFuncionario(event.target.value)}
              className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm"
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
              className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm"
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
              className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm"
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
              onClick={() => {
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
              className="ml-auto"
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
