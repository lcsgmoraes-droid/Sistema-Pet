import React from "react";
import ModalImportacaoProdutos from "../ModalImportacaoProdutos";

export default function ProdutosModalsLayer({
  autoSelecionarConflito,
  bloqueiosExclusao,
  categorias,
  colunasRelatorio,
  colunasRelatorioProdutos,
  colunasTabela,
  colunasTemporarias,
  corrigirTextoQuebrado,
  dadosEdicaoLote,
  departamentos,
  marcas,
  modalColunas,
  modalConflitoExclusao,
  modalEdicaoLote,
  modalImportacao,
  modalRelatorioPersonalizado,
  onCancelarConflito,
  onCloseImportacao,
  onCloseModalColunas,
  onCloseModalConflito,
  onCloseModalEdicaoLote,
  onCloseModalRelatorio,
  onGerarRelatorioPersonalizado,
  onImportacaoSucesso,
  onRestaurarColunasPadrao,
  onSalvarColunas,
  onSalvarEdicaoLote,
  onSelecionarTodasVariacoesDoPai,
  onSelecionarVariacaoConflito,
  onToggleAutoSelecionarConflito,
  onToggleColuna,
  onToggleColunaRelatorio,
  onTogglePularConfirmacaoConflito,
  ordenacaoRelatorio,
  pularConfirmacaoConflito,
  resolvendoConflitoExclusao,
  selecionadosCount,
  setDadosEdicaoLote,
  setOrdenacaoRelatorio,
  variacoesSelecionadasConflito,
}) {
  return (
    <>
      {modalConflitoExclusao && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[85vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Produtos com bloqueio para exclusao
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Selecione as variacoes que deseja desativar agora para o sistema
                  tentar excluir os produtos pai automaticamente.
                </p>
              </div>
              <button
                onClick={onCloseModalConflito}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="border border-blue-100 bg-blue-50 rounded-lg p-3">
                <label className="flex items-center gap-2 text-sm text-blue-900">
                  <input
                    type="checkbox"
                    checked={autoSelecionarConflito}
                    onChange={(event) => onToggleAutoSelecionarConflito(event.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                  Selecionar tudo automaticamente
                </label>
                <label className="flex items-center gap-2 text-sm text-blue-900 mt-2">
                  <input
                    type="checkbox"
                    checked={pularConfirmacaoConflito}
                    onChange={(event) =>
                      onTogglePularConfirmacaoConflito(event.target.checked)
                    }
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                  Nao pedir confirmacao de novo nesta sessao
                </label>
              </div>

              {bloqueiosExclusao.map((bloqueio) => {
                const idsDoPai = bloqueio.variacoes.map((item) => item.id);
                const qtdSelecionada = idsDoPai.filter((id) =>
                  variacoesSelecionadasConflito.includes(id),
                ).length;

                return (
                  <div key={bloqueio.parentId} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div>
                        <h3 className="font-semibold text-gray-900">
                          {corrigirTextoQuebrado(bloqueio.parentNome)}
                        </h3>
                        <p className="text-xs text-gray-600 mt-1">
                          {corrigirTextoQuebrado(bloqueio.mensagem)}
                        </p>
                      </div>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                        {qtdSelecionada}/{bloqueio.variacoes.length} selecionadas
                      </span>
                    </div>

                    {bloqueio.variacoes.length > 0 ? (
                      <>
                        <label className="inline-flex items-center gap-2 text-sm text-gray-700 mb-3">
                          <input
                            type="checkbox"
                            checked={
                              idsDoPai.length > 0 && qtdSelecionada === idsDoPai.length
                            }
                            onChange={(event) =>
                              onSelecionarTodasVariacoesDoPai(
                                bloqueio.parentId,
                                event.target.checked,
                              )
                            }
                            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                          />
                          Selecionar todas variacoes deste produto
                        </label>

                        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                          {bloqueio.variacoes.map((variacao) => (
                            <label
                              key={variacao.id}
                              className="flex items-center justify-between gap-3 border border-gray-100 rounded px-3 py-2 hover:bg-gray-50"
                            >
                              <div className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={variacoesSelecionadasConflito.includes(
                                    variacao.id,
                                  )}
                                  onChange={(event) =>
                                    onSelecionarVariacaoConflito(
                                      variacao.id,
                                      event.target.checked,
                                    )
                                  }
                                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-800">
                                  {corrigirTextoQuebrado(
                                    variacao.nome || `Variacao #${variacao.id}`,
                                  )}
                                </span>
                              </div>
                              <span className="text-xs text-gray-500 font-mono">
                                {variacao.codigo || variacao.sku || `ID ${variacao.id}`}
                              </span>
                            </label>
                          ))}
                        </div>
                      </>
                    ) : (
                      <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                        Nao foi possivel listar variacoes automaticamente para este
                        item. Tente atualizar a tela e repetir.
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={onCloseModalConflito}
                disabled={resolvendoConflitoExclusao}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-60"
              >
                Cancelar
              </button>
              <button
                onClick={onCancelarConflito}
                disabled={resolvendoConflitoExclusao}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-60"
              >
                {resolvendoConflitoExclusao
                  ? "Aplicando resolucao..."
                  : "Resolver rapido e excluir"}
              </button>
            </div>
          </div>
        </div>
      )}

      {modalEdicaoLote && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">Editar em Lote</h2>
              <button onClick={onCloseModalEdicaoLote} className="text-gray-400 hover:text-gray-600">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <p className="text-sm text-gray-600 mb-4">
              Atualizar <strong>{selecionadosCount}</strong> produto(s) selecionado(s)
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Marca</label>
                <select
                  value={dadosEdicaoLote.marca_id}
                  onChange={(event) =>
                    setDadosEdicaoLote({
                      ...dadosEdicaoLote,
                      marca_id: event.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Nao alterar</option>
                  {marcas.map((marca) => (
                    <option key={marca.id} value={marca.id}>
                      {marca.nome}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Categoria
                </label>
                <select
                  value={dadosEdicaoLote.categoria_id}
                  onChange={(event) =>
                    setDadosEdicaoLote({
                      ...dadosEdicaoLote,
                      categoria_id: event.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Nao alterar</option>
                  {categorias.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.categoria_pai_id ? "  -> " : ""}
                      {cat.nome}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Departamento
                </label>
                <select
                  value={dadosEdicaoLote.departamento_id}
                  onChange={(event) =>
                    setDadosEdicaoLote({
                      ...dadosEdicaoLote,
                      departamento_id: event.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Nao alterar</option>
                  {departamentos.map((dep) => (
                    <option key={dep.id} value={dep.id}>
                      {dep.nome}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={onCloseModalEdicaoLote}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={onSalvarEdicaoLote}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Salvar Alteracoes
              </button>
            </div>
          </div>
        </div>
      )}

      {modalColunas && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Configurar Colunas</h3>
              <button
                onClick={onCloseModalColunas}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="px-6 py-4 max-h-96 overflow-y-auto">
              <p className="text-sm text-gray-600 mb-4">
                Selecione quais colunas deseja visualizar na tabela:
              </p>

              <div className="space-y-2">
                {colunasTabela.map((coluna) => (
                  <label
                    key={coluna.key}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={colunasTemporarias.includes(coluna.key)}
                      onChange={() => onToggleColuna(coluna.key)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      {coluna.label || coluna.key}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-between gap-3">
              <button
                onClick={onRestaurarColunasPadrao}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Restaurar Padrao
              </button>
              <div className="flex gap-3">
                <button
                  onClick={onCloseModalColunas}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={onSalvarColunas}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Salvar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {modalRelatorioPersonalizado && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Relatorio Personalizado de Produtos
              </h3>
              <button
                onClick={onCloseModalRelatorio}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="px-6 py-4 max-h-[60vh] overflow-y-auto space-y-4">
              <div>
                <label
                  htmlFor="ordenacao-relatorio-produtos"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Ordem do relatorio
                </label>
                <select
                  id="ordenacao-relatorio-produtos"
                  value={ordenacaoRelatorio}
                  onChange={(event) => setOrdenacaoRelatorio(event.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="nome_asc">Nome (A-Z)</option>
                  <option value="nome_desc">Nome (Z-A)</option>
                  <option value="estoque_asc">Estoque (menor para maior)</option>
                  <option value="estoque_desc">Estoque (maior para menor)</option>
                  <option value="preco_asc">Preco venda (menor para maior)</option>
                  <option value="preco_desc">Preco venda (maior para menor)</option>
                </select>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Colunas para exibir</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {colunasRelatorioProdutos.map((coluna) => (
                    <label
                      key={coluna.key}
                      className="flex items-center gap-2 p-2 rounded hover:bg-gray-50"
                    >
                      <input
                        type="checkbox"
                        checked={colunasRelatorio.includes(coluna.key)}
                        onChange={() => onToggleColunaRelatorio(coluna.key)}
                        className="w-4 h-4 text-indigo-600 rounded"
                      />
                      <span className="text-sm text-gray-700">{coluna.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={onCloseModalRelatorio}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={onGerarRelatorioPersonalizado}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
              >
                Gerar relatorio
              </button>
            </div>
          </div>
        </div>
      )}

      <ModalImportacaoProdutos
        isOpen={modalImportacao}
        onClose={onCloseImportacao}
        onSuccess={onImportacaoSucesso}
      />
    </>
  );
}
