import React from "react";
import { FiHelpCircle } from "react-icons/fi";

function ProdutosPaginationControls({
  itensPorPagina,
  onChangeItensPorPagina,
  onIrParaPagina,
  onIrParaPrimeiraPagina,
  onIrParaUltimaPagina,
  onPaginaAnterior,
  onProximaPagina,
  paginaAtual,
  totalItens,
  totalPaginas,
}) {
  if (totalItens <= 0) return null;

  const paginaInicial =
    totalPaginas <= 5
      ? 1
      : paginaAtual <= 3
        ? 1
        : paginaAtual >= totalPaginas - 2
          ? totalPaginas - 4
          : paginaAtual - 2;

  const paginasVisiveis = Array.from(
    { length: Math.min(totalPaginas, 5) },
    (_, index) => paginaInicial + index,
  );

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">
          Mostrando {(paginaAtual - 1) * itensPorPagina + 1} a{" "}
          {Math.min(paginaAtual * itensPorPagina, totalItens)} de {totalItens} produtos
        </span>
        <select
          value={itensPorPagina}
          onChange={(event) => onChangeItensPorPagina(event.target.value)}
          className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value={10}>10 por pagina</option>
          <option value={20}>20 por pagina</option>
          <option value={30}>30 por pagina</option>
          <option value={50}>50 por pagina</option>
          <option value={100}>100 por pagina</option>
        </select>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onIrParaPrimeiraPagina}
          disabled={paginaAtual === 1}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Primeira
        </button>
        <button
          onClick={onPaginaAnterior}
          disabled={paginaAtual === 1}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Anterior
        </button>

        <div className="flex items-center gap-1">
          {paginasVisiveis.map((pageNum) => (
            <button
              key={pageNum}
              onClick={() => onIrParaPagina(pageNum)}
              className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                paginaAtual === pageNum
                  ? "bg-blue-600 text-white"
                  : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
              }`}
            >
              {pageNum}
            </button>
          ))}
        </div>

        <button
          onClick={onProximaPagina}
          disabled={paginaAtual === totalPaginas}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Proxima
        </button>
        <button
          onClick={onIrParaUltimaPagina}
          disabled={paginaAtual === totalPaginas}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Ultima
        </button>
      </div>
    </div>
  );
}

export default function ProdutosMainContent({
  abrirModalColunas,
  categorias,
  copiarTexto,
  editandoPreco,
  filtrarColunas,
  filtros,
  fornecedores,
  getCorEstoque,
  getValidadeMaisProxima,
  handleCancelarEdicaoPreco,
  handleEditarPreco,
  handleExcluir,
  handleFiltroChange,
  handleSalvarPreco,
  handleSelecionar,
  handleSelecionarTodos,
  handleToggleAtivo,
  iniciarTour,
  isProdutoComComposicao,
  itensPorPagina,
  kitsExpandidos,
  linhaProdutoRefs,
  loading,
  marcas,
  menuRelatoriosAberto,
  menuRelatoriosRef,
  navigate,
  novoPreco,
  onChangeItensPorPagina,
  onExcluirSelecionados,
  onGerarRelatorioFiltrado,
  onGerarRelatorioGeral,
  onIrParaPagina,
  onIrParaPrimeiraPagina,
  onIrParaUltimaPagina,
  onOpenEdicaoLote,
  onOpenImportacao,
  onOpenModalRelatorio,
  onPaginaAnterior,
  onProximaPagina,
  onToggleMenuRelatorios,
  paginaAtual,
  paisExpandidos,
  persistirBusca,
  produtos,
  produtosColunas,
  selecionados,
  selecionadosCount,
  setNovoPreco,
  setPersistirBusca,
  toggleKitExpandido,
  togglePaiExpandido,
  totalItens,
  totalPaginas,
}) {
  const colunasVisiveis = produtosColunas.filter(filtrarColunas);

  return (
    <>
      <div className="mb-6 flex justify-between items-start">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Produtos</h1>
            <p className="text-gray-600 mt-1">Gerencie seu estoque de produtos</p>
          </div>
          <button
            onClick={iniciarTour}
            title="Ver tour guiado desta pagina"
            className="flex items-center gap-1 px-2 py-1 text-sm text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors mt-1"
          >
            <FiHelpCircle className="text-base" />
            <span className="hidden sm:inline text-xs">Tour</span>
          </button>
        </div>
        <div className="flex gap-2">
          {selecionadosCount > 0 && (
            <>
              <button
                onClick={onOpenEdicaoLote}
                className="px-4 py-2 text-white rounded-xl bg-emerald-600 hover:bg-emerald-700 shadow-sm hover:shadow-md transition-all duration-200 border border-emerald-500"
              >
                Editar em Lote ({selecionadosCount})
              </button>
              <button
                onClick={onExcluirSelecionados}
                className="px-4 py-2 text-white rounded-xl bg-red-600 hover:bg-red-700 shadow-sm hover:shadow-md transition-all duration-200 border border-red-500"
              >
                Excluir Selecionados ({selecionadosCount})
              </button>
            </>
          )}
          <button
            id="tour-produtos-importar"
            onClick={onOpenImportacao}
            className="px-4 py-2 text-white rounded-xl bg-sky-600 hover:bg-sky-700 shadow-sm hover:shadow-md transition-all duration-200 border border-sky-500 font-medium flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            Importar Excel
          </button>
          <button
            onClick={abrirModalColunas}
            className="px-4 py-2 text-slate-700 rounded-xl bg-white hover:bg-slate-50 shadow-sm hover:shadow-md transition-all duration-200 border border-slate-300 font-medium flex items-center gap-2"
            title="Configurar colunas visiveis"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            Colunas
          </button>
          <div className="relative" ref={menuRelatoriosRef}>
            <button
              onClick={onToggleMenuRelatorios}
              className="px-4 py-2 text-indigo-700 rounded-xl bg-indigo-50 hover:bg-indigo-100 shadow-sm hover:shadow-md transition-all duration-200 border border-indigo-200 font-medium"
            >
              Relatorios
            </button>

            {menuRelatoriosAberto && (
              <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 z-40">
                <button
                  onClick={onGerarRelatorioGeral}
                  className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50"
                >
                  Relatorio geral (todos os produtos)
                </button>
                <button
                  onClick={onGerarRelatorioFiltrado}
                  className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                >
                  Relatorio do que filtrei
                </button>
                <button
                  onClick={onOpenModalRelatorio}
                  className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                >
                  Relatorio personalizado
                </button>
              </div>
            )}
          </div>
          <button
            id="tour-produtos-novo"
            onClick={() => navigate("/produtos/novo")}
            className="px-4 py-2 text-white rounded-xl bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow-md transition-all duration-200 border border-blue-500 font-medium"
          >
            + Novo Produto
          </button>
        </div>
      </div>

      <div id="tour-produtos-filtros" className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
          <div id="tour-produtos-busca" className="md:col-span-2">
            <input
              type="text"
              placeholder="Buscar por codigo, nome ou codigo de barras..."
              value={filtros.busca}
              onChange={(event) => handleFiltroChange("busca", event.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <select
              value={filtros.categoria_id}
              onChange={(event) => handleFiltroChange("categoria_id", event.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todas as Categorias</option>
              {categorias.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.categoria_pai_id ? "  -> " : ""}
                  {cat.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={filtros.marca_id}
              onChange={(event) => handleFiltroChange("marca_id", event.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todas as Marcas</option>
              {marcas.map((marca) => (
                <option key={marca.id} value={marca.id}>
                  {marca.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={filtros.fornecedor_id}
              onChange={(event) => handleFiltroChange("fornecedor_id", event.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todos os Fornecedores</option>
              {fornecedores.map((fornecedor) => (
                <option key={fornecedor.id} value={fornecedor.id}>
                  {fornecedor.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={filtros.ativo}
              onChange={(event) => handleFiltroChange("ativo", event.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="ativos">Somente Ativos</option>
              <option value="inativos">Somente Inativos</option>
              <option value="todos">Ativos e Inativos</option>
            </select>
          </div>

          <div className="flex gap-4 items-center flex-wrap md:col-span-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filtros.estoque_baixo}
                onChange={(event) => handleFiltroChange("estoque_baixo", event.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Estoque Baixo</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filtros.em_promocao}
                onChange={(event) => handleFiltroChange("em_promocao", event.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Em Promocao</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filtros.mostrarPaisVariacoes}
                onChange={(event) =>
                  handleFiltroChange("mostrarPaisVariacoes", event.target.checked)
                }
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Mostrar Pais, Variacoes e Kits</span>
            </label>

            <label
              className="flex items-center gap-2 cursor-pointer px-2 py-1 rounded-md border border-gray-200 bg-gray-50"
              title="Quando ligado, a busca fica salva ao sair e voltar para a lista"
            >
              <input
                type="checkbox"
                checked={persistirBusca}
                onChange={(event) => setPersistirBusca(event.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-xs text-gray-700">Persistir pesquisa</span>
            </label>
          </div>
        </div>
      </div>

      {!loading && totalItens > 0 && (
        <div className="px-4 py-3 bg-gray-50 border border-gray-200 rounded-t-lg flex items-center justify-between mt-6 mb-0">
          <ProdutosPaginationControls
            itensPorPagina={itensPorPagina}
            onChangeItensPorPagina={onChangeItensPorPagina}
            onIrParaPagina={onIrParaPagina}
            onIrParaPrimeiraPagina={onIrParaPrimeiraPagina}
            onIrParaUltimaPagina={onIrParaUltimaPagina}
            onPaginaAnterior={onPaginaAnterior}
            onProximaPagina={onProximaPagina}
            paginaAtual={paginaAtual}
            totalItens={totalItens}
            totalPaginas={totalPaginas}
          />
        </div>
      )}

      <div id="tour-produtos-lista" className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {colunasVisiveis.map((coluna) => (
                  <React.Fragment key={coluna.key}>
                    {coluna.renderHeader({
                      produtos,
                      selecionados,
                      handleSelecionarTodos,
                    })}
                  </React.Fragment>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="10" className="px-4 py-8 text-center text-gray-500">
                    Carregando produtos...
                  </td>
                </tr>
              ) : produtos.length === 0 ? (
                <tr>
                  <td colSpan="10" className="px-4 py-8 text-center text-gray-500">
                    Nenhum produto encontrado
                  </td>
                </tr>
              ) : (
                produtos.map((produto, idx) => {
                  if (!produto || !produto.id) {
                    console.error(`Produto invalido no indice ${idx}:`, produto);
                    return null;
                  }

                  const isKit = isProdutoComComposicao(produto);
                  const isKitExpandido = kitsExpandidos.includes(produto.id);

                  return (
                    <React.Fragment key={produto.id}>
                      <tr
                        ref={(element) => {
                          linhaProdutoRefs.current[produto.id] = element;
                        }}
                        className={`hover:bg-gray-50 transition-colors cursor-pointer ${
                          produto.ativo === false ? "bg-slate-100 opacity-70" : ""
                        } ${
                          produto.tipo_produto === "VARIACAO" ? "bg-blue-50/30" : ""
                        } ${isKit ? "bg-amber-50/30" : ""}`}
                        onClick={(event) => {
                          if (!event.target.closest("button, input, a, svg")) {
                            navigate(`/produtos/${produto.id}/editar`);
                          }
                        }}
                      >
                        {colunasVisiveis.map((coluna) => (
                          <React.Fragment key={coluna.key}>
                            {coluna.renderCell(produto, {
                              selecionados,
                              handleSelecionar,
                              kitsExpandidos,
                              toggleKitExpandido,
                              paisExpandidos,
                              togglePaiExpandido,
                              copiarTexto,
                              editandoPreco,
                              novoPreco,
                              setNovoPreco,
                              handleSalvarPreco,
                              handleCancelarEdicaoPreco,
                              handleEditarPreco,
                              getValidadeMaisProxima,
                              getCorEstoque,
                              navigate,
                              handleExcluir,
                              handleToggleAtivo,
                            })}
                          </React.Fragment>
                        ))}
                      </tr>

                      {isKit &&
                        isKitExpandido &&
                        produto.composicao_kit &&
                        produto.composicao_kit.length > 0 && (
                          <tr
                            key={`kit-${produto.id}`}
                            className="bg-amber-50/50 border-l-4 border-amber-400"
                          >
                            <td colSpan="10" className="px-4 py-3">
                              <div className="ml-12">
                                <div className="text-xs font-semibold text-amber-800 mb-2 flex items-center gap-2">
                                  <svg
                                    className="w-4 h-4"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                                    />
                                  </svg>
                                  COMPOSICAO DO KIT:
                                </div>
                                <div className="grid gap-1">
                                  {produto.composicao_kit.map((componente, index) => (
                                    <div
                                      key={index}
                                      className="flex items-center gap-3 text-xs bg-white rounded px-3 py-2 border border-amber-200"
                                    >
                                      <span className="font-mono font-semibold text-amber-700 min-w-[40px]">
                                        {componente.quantidade}x
                                      </span>
                                      <span className="flex-1 text-gray-700">
                                        {componente.produto_nome ||
                                          componente.nome ||
                                          `Produto #${
                                            componente.produto_id ||
                                            componente.produto_componente_id
                                          }`}
                                      </span>
                                      {componente.produto_estoque !== undefined && (
                                        <span className="text-gray-500">
                                          Estoque:{" "}
                                          <span
                                            className={
                                              componente.produto_estoque > 0
                                                ? "text-green-600 font-semibold"
                                                : "text-red-600 font-semibold"
                                            }
                                          >
                                            {componente.produto_estoque}
                                          </span>
                                        </span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {!loading && totalItens > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
            <ProdutosPaginationControls
              itensPorPagina={itensPorPagina}
              onChangeItensPorPagina={onChangeItensPorPagina}
              onIrParaPagina={onIrParaPagina}
              onIrParaPrimeiraPagina={onIrParaPrimeiraPagina}
              onIrParaUltimaPagina={onIrParaUltimaPagina}
              onPaginaAnterior={onPaginaAnterior}
              onProximaPagina={onProximaPagina}
              paginaAtual={paginaAtual}
              totalItens={totalItens}
              totalPaginas={totalPaginas}
            />
          </div>
        )}

        {!loading && selecionadosCount > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
            <div className="flex justify-between items-center text-sm text-gray-600">
              <span>
                {selecionadosCount} produto{selecionadosCount > 1 ? "s" : ""} selecionado
                {selecionadosCount > 1 ? "s" : ""}
              </span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
