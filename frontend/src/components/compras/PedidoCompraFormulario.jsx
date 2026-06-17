import FornecedorSelector from "../fornecedores/FornecedorSelector";
import ProductIdentity from "../ui/ProductIdentity";
import { normalizarTextoBusca } from "./pedidoCompraUtils";

export default function PedidoCompraFormulario({
  mostrarForm,
  modoEdicao,
  fecharFormularioPedido,
  editarPedido,
  handleSubmit,
  fornecedorTexto,
  setFornecedorTexto,
  fornecedores,
  gruposFornecedores,
  selecionarFornecedor,
  selecionarGrupoFornecedor,
  setFormData,
  setProdutos,
  setIncluirGrupoFornecedor,
  setProdutoTexto,
  setMostrarSugestoesProduto,
  setItemForm,
  itemFormInicial,
  limparEstadosSugestao,
  abrirNovoGrupoFornecedor,
  formData,
  grupoFornecedorAtual,
  incluirGrupoFornecedor,
  abrirFluxoSugestaoInteligente,
  loadingPrepararSugestao,
  produtoTexto,
  produtos,
  selecionarProduto,
  produtosFiltrados,
  mostrarSugestoesProduto,
  itemForm,
  adicionarItem,
  obterSkuItemPedido,
  atualizarItemPedido,
  numeroSeguro,
  removerItem,
  calcularTotal,
  loading,
}) {
  if (!mostrarForm) {
    return null;
  }

  const fornecedorSelecionado = fornecedores.find(
    (fornecedor) => Number(fornecedor.id) === Number(formData.fornecedor_id),
  );

  const limparFornecedorSelecionado = () => {
    setFormData((prev) => ({ ...prev, fornecedor_id: "", itens: [] }));
    setProdutos([]);
    setIncluirGrupoFornecedor(false);
    setProdutoTexto("");
    setMostrarSugestoesProduto(false);
    setItemForm(itemFormInicial);
    limparEstadosSugestao();
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">
          {modoEdicao ? "✏️ Editar Pedido" : "Novo Pedido de Compra"}
        </h2>
        <button
          type="button"
          onClick={fecharFormularioPedido}
          className="text-gray-500 hover:text-gray-700"
        >
          ✖️
        </button>
      </div>
      <form onSubmit={modoEdicao ? editarPedido : handleSubmit} className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Fornecedor *</label>
            <FornecedorSelector
              fornecedores={fornecedores}
              gruposFornecedores={gruposFornecedores}
              fornecedorId={formData.fornecedor_id}
              fornecedorSelecionado={fornecedorSelecionado}
              showLabel={false}
              required
              value={fornecedorTexto}
              placeholder="Digite ou selecione o fornecedor"
              onInputChange={(valor) => {
                setFornecedorTexto(valor);
                if (formData.fornecedor_id) {
                  limparFornecedorSelecionado();
                }
              }}
              onSelect={selecionarFornecedor}
              onSelectGrupo={selecionarGrupoFornecedor}
              onClear={() => {
                setFornecedorTexto("");
                limparFornecedorSelecionado();
              }}
            />
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <p className="text-xs text-gray-500">
                Digite ou selecione um fornecedor para carregar seus produtos
              </p>
              <button
                type="button"
                onClick={abrirNovoGrupoFornecedor}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Grupos de fornecedor
              </button>
            </div>
            {formData.fornecedor_id && grupoFornecedorAtual && (
              <label className="mt-2 flex cursor-pointer items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
                <input
                  type="checkbox"
                  checked={incluirGrupoFornecedor}
                  onChange={(e) => {
                    setIncluirGrupoFornecedor(e.target.checked);
                    limparEstadosSugestao();
                  }}
                  className="mt-0.5 h-4 w-4 rounded"
                />
                <span>
                  <strong>Unificar CNPJs do grupo {grupoFornecedorAtual.nome}</strong>
                  <span className="block text-emerald-700">
                    A sugestao inteligente considera todos os fornecedores vinculados ao grupo.
                  </span>
                </span>
              </label>
            )}
            {formData.fornecedor_id && !grupoFornecedorAtual && (
              <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                Este fornecedor ainda nao esta em um grupo. Use "Grupos de fornecedor" para unificar
                CNPJs.
              </div>
            )}
            {formData.fornecedor_id && (
              <button
                type="button"
                onClick={abrirFluxoSugestaoInteligente}
                disabled={loadingPrepararSugestao}
                className="mt-2 w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-lg font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2"
              >
                {loadingPrepararSugestao
                  ? "Verificando rascunho..."
                  : "💡 Sugestão Inteligente de Pedido"}
              </button>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data Prevista Entrega
            </label>
            <input
              type="date"
              value={formData.data_prevista_entrega}
              onChange={(e) => setFormData({ ...formData, data_prevista_entrega: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="border-t pt-4">
          <h3 className="font-semibold mb-4">Itens do Pedido ({formData.itens.length})</h3>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="col-span-2 relative">
              <input
                value={produtoTexto}
                onChange={(e) => {
                  const valor = e.target.value;
                  const valorNormalizado = normalizarTextoBusca(valor);

                  setProdutoTexto(valor);

                  if (!valorNormalizado) {
                    setMostrarSugestoesProduto(false);
                    setItemForm(itemFormInicial);
                    return;
                  }

                  setMostrarSugestoesProduto(true);

                  const produtoExato = produtos.find((p) =>
                    [p.nome, p.codigo, p.sku, p.codigo_barras].some((campo) => {
                      const campoNormalizado = normalizarTextoBusca(campo);
                      return campoNormalizado && campoNormalizado === valorNormalizado;
                    }),
                  );

                  if (produtoExato) {
                    selecionarProduto(produtoExato);
                  } else {
                    setItemForm((prev) => ({ ...prev, produto_id: "", preco_unitario: "" }));
                  }
                }}
                onFocus={() => {
                  if (formData.fornecedor_id) {
                    setMostrarSugestoesProduto(true);
                  }
                }}
                onBlur={() => {
                  setTimeout(() => setMostrarSugestoesProduto(false), 120);
                }}
                placeholder={
                  !formData.fornecedor_id
                    ? "Selecione um fornecedor primeiro"
                    : "Digite ou selecione o produto"
                }
                disabled={!formData.fornecedor_id}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100 focus:ring-2 focus:ring-blue-500"
              />
              {mostrarSugestoesProduto &&
                produtosFiltrados.length > 0 &&
                formData.fornecedor_id && (
                  <div className="absolute z-20 mt-1 w-full max-h-60 overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg">
                    {produtosFiltrados.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onMouseDown={(ev) => ev.preventDefault()}
                        onClick={() => selecionarProduto(p)}
                        className="w-full px-4 py-2 text-left hover:bg-blue-50 border-b border-gray-100 last:border-b-0"
                      >
                        <div className="font-medium text-gray-800">{p.nome}</div>
                        <div className="text-xs text-gray-500">
                          SKU: {p.sku || p.codigo || "N/A"} | Barras: {p.codigo_barras || "N/A"} |
                          Estoque: {p.estoque_atual || 0}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
            </div>
            <input
              type="number"
              step="0.01"
              placeholder="Quantidade"
              value={itemForm.quantidade_pedida}
              onChange={(e) => setItemForm({ ...itemForm, quantidade_pedida: e.target.value })}
              className="px-4 py-2 border border-gray-300 rounded-lg"
            />
            <div className="flex gap-2">
              <input
                type="number"
                step="0.01"
                placeholder="Preço"
                value={itemForm.preco_unitario}
                onChange={(e) => setItemForm({ ...itemForm, preco_unitario: e.target.value })}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
              />
              <button
                type="button"
                onClick={adicionarItem}
                className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
              >
                ➕
              </button>
            </div>
          </div>

          {formData.itens.length > 0 && (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="w-12 px-4 py-2 text-left text-sm font-semibold">#</th>
                    <th className="px-4 py-2 text-left text-sm font-semibold">Produto</th>
                    <th className="px-4 py-2 text-right text-sm font-semibold">Qtd</th>
                    <th className="px-4 py-2 text-right text-sm font-semibold">Preço</th>
                    <th className="px-4 py-2 text-right text-sm font-semibold">Total</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {formData.itens.map((item, index) => (
                    <tr key={index} className="border-t">
                      <td className="px-4 py-2 text-sm font-semibold text-slate-500">
                        {index + 1}
                      </td>
                      <td className="px-4 py-2">
                        <ProductIdentity
                          code={obterSkuItemPedido(item)}
                          name={item.produto_nome}
                          nameClassName="font-medium text-gray-900"
                        />
                      </td>
                      <td className="px-4 py-2 text-right">
                        <input
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={item.quantidade_pedida}
                          onChange={(e) =>
                            atualizarItemPedido(index, "quantidade_pedida", e.target.value)
                          }
                          className="w-24 rounded-lg border border-gray-300 px-3 py-2 text-right focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                        />
                      </td>
                      <td className="px-4 py-2 text-right">
                        R$ {numeroSeguro(item.preco_unitario).toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right font-semibold">
                        R$ {numeroSeguro(item.total).toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <button
                          type="button"
                          onClick={() => removerItem(index)}
                          className="text-red-600 hover:text-red-800"
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Frete (R$)</label>
            <input
              type="number"
              step="0.01"
              value={formData.valor_frete}
              onChange={(e) => setFormData({ ...formData, valor_frete: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Desconto (R$)</label>
            <input
              type="number"
              step="0.01"
              value={formData.valor_desconto}
              onChange={(e) => setFormData({ ...formData, valor_desconto: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Total</label>
            <div className="text-2xl font-bold text-green-600">R$ {calcularTotal().toFixed(2)}</div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? "⏳ Processando..." : modoEdicao ? "✏️ Salvar Alterações" : "✅ Criar Pedido"}
        </button>
      </form>
    </div>
  );
}
