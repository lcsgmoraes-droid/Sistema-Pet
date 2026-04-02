import React from "react";
import ProdutosPaginationControls from "./ProdutosPaginationControls";

export default function ProdutosTabelaSection({
  colunasVisiveis,
  copiarTexto,
  editandoPreco,
  getCorEstoque,
  getValidadeMaisProxima,
  handleCancelarEdicaoPreco,
  handleEditarPreco,
  handleExcluir,
  handleSalvarPreco,
  handleSelecionar,
  handleSelecionarTodos,
  handleToggleAtivo,
  isProdutoComComposicao,
  itensPorPagina,
  kitsExpandidos,
  linhaProdutoRefs,
  loading,
  navigate,
  novoPreco,
  onChangeItensPorPagina,
  onIrParaPagina,
  onIrParaPrimeiraPagina,
  onIrParaUltimaPagina,
  onPaginaAnterior,
  onProximaPagina,
  paginaAtual,
  paisExpandidos,
  produtos,
  selecionados,
  selecionadosCount,
  setNovoPreco,
  toggleKitExpandido,
  togglePaiExpandido,
  totalItens,
  totalPaginas,
}) {
  return (
    <>
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
