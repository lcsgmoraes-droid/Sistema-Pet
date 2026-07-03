import { RefreshCw, Search, X } from "lucide-react";

export default function PedidosCompraSugestaoHeader({
  fecharModalSugestao,
  filtroSugestao,
  setFiltroSugestao,
  filtroMarcasRef,
  setMostrarFiltroMarcas,
  resumoMarcasSelecionadas,
  mostrarFiltroMarcas,
  setMarcasSelecionadas,
  marcasSelecionadas,
  marcasFornecedor,
  alternarMarcaSelecionada,
  periodoSugestao,
  setPeriodoSugestao,
  diasCobertura,
  setDiasCobertura,
  buscarSugestoes,
  loadingSugestao,
  apenasCriticos,
  setApenasCriticos,
  incluirAlerta,
  setIncluirAlerta,
  grupoFornecedorAtual,
  incluirGrupoFornecedor,
  setIncluirGrupoFornecedor,
  apenasFornecedorPrincipal,
  setApenasFornecedorPrincipal,
  limparEstadosSugestao,
  sugestoes,
  produtosSelecionados,
  obterQuantidadeTotalUnidadesSugestao,
  calcularValorTotalSugestao,
}) {
  return (
    <>
      {/* Header */}
      <div className="border-b border-slate-200 bg-white px-5 py-4 text-slate-900 shadow-sm">
        <div className="flex flex-col gap-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-teal-700">
                Sugestão Inteligente
              </div>
              <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h2 className="text-lg font-bold leading-tight">
                  Pedido guiado por vendas e estoque
                </h2>
                <p className="text-xs text-slate-500">
                  Ajuste rápido dos filtros sem perder área útil.
                </p>
              </div>
            </div>
            <button
              onClick={fecharModalSugestao}
              className="shrink-0 rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
              title="Fechar sugestao"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Filtros */}
          <div className="grid gap-2 xl:grid-cols-12">
            <div className="xl:col-span-4">
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
                Buscar por nome ou SKU
              </label>
              <input
                type="text"
                placeholder="Ex: Special Dog, SKU 211..."
                value={filtroSugestao}
                onChange={(e) => setFiltroSugestao(e.target.value)}
                className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-slate-800 shadow-sm focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              />
            </div>
            <div ref={filtroMarcasRef} className="relative sm:col-span-2 xl:col-span-3">
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
                Marcas
              </label>
              <button
                type="button"
                onClick={() => setMostrarFiltroMarcas((aberto) => !aberto)}
                className="flex h-11 w-full items-center justify-between rounded-lg border border-slate-300 bg-white px-3 text-left text-slate-800 shadow-sm transition hover:bg-slate-50"
              >
                <span className="truncate">{resumoMarcasSelecionadas}</span>
                <span
                  className={`ml-3 text-sm transition-transform ${mostrarFiltroMarcas ? "rotate-180" : ""}`}
                >
                  ▾
                </span>
              </button>

              {mostrarFiltroMarcas && (
                <div className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-slate-200 bg-white text-gray-800 shadow-2xl">
                  <button
                    type="button"
                    onClick={() => setMarcasSelecionadas([])}
                    className="flex w-full items-center justify-between border-b border-gray-100 px-3 py-2 text-sm font-medium transition hover:bg-slate-50"
                  >
                    <span className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={marcasSelecionadas.length === 0}
                        readOnly
                        className="h-4 w-4 rounded"
                      />
                      Todas
                    </span>
                    <span className="text-xs text-gray-500">
                      {marcasSelecionadas.length === 0 ? "sem filtro" : "limpar"}
                    </span>
                  </button>

                  <div className="max-h-56 overflow-y-auto py-1">
                    {marcasFornecedor.map((marca) => (
                      <label
                        key={marca.id}
                        className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm transition hover:bg-slate-50"
                      >
                        <input
                          type="checkbox"
                          checked={marcasSelecionadas.includes(marca.id)}
                          onChange={() => alternarMarcaSelecionada(marca.id)}
                          className="h-4 w-4 rounded"
                        />
                        <span className="truncate">{marca.nome}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="sm:col-span-1 xl:col-span-2">
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
                Período
              </label>
              <select
                value={periodoSugestao}
                onChange={(e) => setPeriodoSugestao(parseInt(e.target.value))}
                className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-slate-800 shadow-sm focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              >
                <option value={30}>Últimos 30 dias</option>
                <option value={60}>Últimos 60 dias</option>
                <option value={90}>Últimos 90 dias</option>
                <option value={180}>Últimos 180 dias</option>
              </select>
            </div>
            <div className="sm:col-span-1 xl:col-span-2">
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
                Cobertura
              </label>
              <select
                value={diasCobertura}
                onChange={(e) => setDiasCobertura(parseInt(e.target.value))}
                className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-slate-800 shadow-sm focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              >
                <option value={15}>15 dias</option>
                <option value={30}>30 dias</option>
                <option value={45}>45 dias</option>
                <option value={60}>60 dias</option>
                <option value={90}>90 dias</option>
              </select>
            </div>
            <div className="sm:col-span-2 xl:col-span-1 flex flex-col justify-end">
              <span className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-transparent select-none">
                Atualizar
              </span>
              <button
                onClick={() => buscarSugestoes()}
                disabled={loadingSugestao}
                className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:opacity-50"
              >
                {loadingSugestao ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Analisando
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    Atualizar
                  </>
                )}
              </button>
            </div>
            <div className="xl:col-span-12">
              <div className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex flex-wrap items-center gap-4 text-sm text-slate-700">
                  <label className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={apenasCriticos}
                      onChange={(e) => setApenasCriticos(e.target.checked)}
                      className="h-4 w-4 rounded"
                    />
                    <span>Apenas Críticos</span>
                  </label>
                  <label className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={incluirAlerta}
                      onChange={(e) => setIncluirAlerta(e.target.checked)}
                      className="h-4 w-4 rounded"
                    />
                    <span>Incluir Alertas</span>
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1">
                    <input
                      type="checkbox"
                      checked={apenasFornecedorPrincipal}
                      onChange={(e) => {
                        setApenasFornecedorPrincipal(e.target.checked);
                        limparEstadosSugestao();
                      }}
                      className="h-4 w-4 rounded"
                    />
                    <span>
                      {incluirGrupoFornecedor
                        ? "Somente principais do grupo"
                        : "Somente fornecedor principal"}
                    </span>
                  </label>
                  {grupoFornecedorAtual && (
                    <label className="flex cursor-pointer items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1">
                      <input
                        type="checkbox"
                        checked={incluirGrupoFornecedor}
                        onChange={(e) => {
                          setIncluirGrupoFornecedor(e.target.checked);
                          limparEstadosSugestao();
                        }}
                        className="h-4 w-4 rounded"
                      />
                      <span>Todos os CNPJs do grupo {grupoFornecedorAtual.nome}</span>
                    </label>
                  )}
                </div>

                {sugestoes.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                    {(() => {
                      const selecionados = sugestoes.filter((s) =>
                        produtosSelecionados.includes(s.produto_id),
                      );
                      const totalQtd = selecionados.reduce(
                        (sum, s) => sum + obterQuantidadeTotalUnidadesSugestao(s),
                        0,
                      );
                      const totalPeso = selecionados.reduce(
                        (sum, s) =>
                          sum + obterQuantidadeTotalUnidadesSugestao(s) * (s.peso_bruto || 0),
                        0,
                      );
                      const totalValor = selecionados.reduce(
                        (sum, s) => sum + calcularValorTotalSugestao(s),
                        0,
                      );
                      return (
                        <>
                          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1">
                            <strong className="text-slate-900">{totalQtd}</strong> unidades
                          </span>
                          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1">
                            <strong className="text-slate-900">{totalPeso.toFixed(1)} kg</strong>
                          </span>
                          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1">
                            <strong className="text-slate-900">
                              R${" "}
                              {totalValor.toLocaleString("pt-BR", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                            </strong>
                          </span>
                          {selecionados.length === 0 && (
                            <span className="italic opacity-80">
                              (selecione produtos para ver o total)
                            </span>
                          )}
                        </>
                      );
                    })()}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
