import FornecedorSelector from "../fornecedores/FornecedorSelector";
import ProductIdentity from "../ui/ProductIdentity";
import { Check, Lightbulb, Plus, Save, X } from "lucide-react";
import { formatMoneyBRL } from "../../utils/formatters";
import PedidoCompraCatalogoProdutos from "./PedidoCompraCatalogoProdutos";
import { PedidoCompraVinculoLote } from "./PedidoCompraModoMontagem";
import {
  formatarQuantidadeCompraPedido,
  montarTooltipQuantidadeCompraPedido,
  normalizarQuantidadePorEmbalagemPedido,
  normalizarTextoBusca,
  normalizarUnidadeCompraPedido,
  UNIDADES_COMPRA_OPCOES,
} from "./pedidoCompraUtils";

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
  registrarFornecedorCriado,
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
  porProdutos,
}) {
  if (!mostrarForm) {
    return null;
  }

  const fornecedorSelecionado = fornecedores.find(
    (fornecedor) => Number(fornecedor.id) === Number(formData.fornecedor_id),
  );
  const {
    adicionarProdutoCatalogo,
    alterarFiltroProdutosPedido,
    alterarTermoProdutosPedido,
    alternarProdutoVinculo,
    alternarTodosProdutosVinculo,
    filtroProdutosPedido,
    loadingProdutosPedido,
    modoMontagem,
    paginacaoProdutosPedido,
    produtosVinculoSelecionados,
    setPaginaProdutosPedido,
    setVinculoComoPrincipal,
    vincularProdutosFornecedorPedido,
    vinculandoProdutos,
    vinculoComoPrincipal,
  } = porProdutos;
  const modoPorProdutos = modoMontagem === "produtos";
  const idsProdutosPedido = [
    ...new Set(formData.itens.map((item) => Number(item.produto_id)).filter(Boolean)),
  ];
  const todosProdutosSelecionados =
    idsProdutosPedido.length > 0 && produtosVinculoSelecionados.length === idsProdutosPedido.length;
  const unidadeCompraAtual = normalizarUnidadeCompraPedido(itemForm.unidade_compra);
  const itemUsaEmbalagem = unidadeCompraAtual !== "UN";
  const produtoSelecionadoItem = produtos.find(
    (produto) => Number(produto.id) === Number(itemForm.produto_id),
  );
  const quantidadePorEmbalagemAtual = normalizarQuantidadePorEmbalagemPedido(
    unidadeCompraAtual,
    itemForm.quantidade_por_embalagem,
  );
  const itemPreview = {
    quantidade_pedida: itemForm.quantidade_pedida,
    unidade_compra: unidadeCompraAtual,
    quantidade_por_embalagem: quantidadePorEmbalagemAtual,
  };
  const tooltipQuantidadeItem = montarTooltipQuantidadeCompraPedido(itemPreview);

  const limparFornecedorSelecionado = () => {
    setFormData((prev) => ({
      ...prev,
      fornecedor_id: "",
      itens: modoPorProdutos ? prev.itens : [],
    }));
    if (!modoPorProdutos) setProdutos([]);
    setIncluirGrupoFornecedor(false);
    setProdutoTexto("");
    setMostrarSugestoesProduto(false);
    setItemForm(itemFormInicial);
    limparEstadosSugestao();
  };

  return (
    <div className="mb-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            {modoEdicao
              ? "Editar Pedido"
              : modoPorProdutos
                ? "Novo pedido por produtos"
                : "Novo pedido por fornecedor"}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {modoPorProdutos
              ? "Escolha na lista sugerida ou pesquise em todo o catálogo."
              : "Selecione o fornecedor para carregar os produtos vinculados."}
          </p>
        </div>
        <button
          type="button"
          onClick={fecharFormularioPedido}
          className="rounded-lg p-2 text-slate-500 transition hover:bg-white hover:text-slate-900"
          title="Fechar formulario"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      <form onSubmit={modoEdicao ? editarPedido : handleSubmit} className="space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fornecedor {modoPorProdutos ? "(opcional)" : "*"}
            </label>
            <FornecedorSelector
              fornecedores={fornecedores}
              gruposFornecedores={gruposFornecedores}
              fornecedorId={formData.fornecedor_id}
              fornecedorSelecionado={fornecedorSelecionado}
              showLabel={false}
              required={!modoPorProdutos}
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
              onFornecedorCriado={registrarFornecedorCriado}
              onClear={() => {
                setFornecedorTexto("");
                limparFornecedorSelecionado();
              }}
            />
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <p className="text-xs text-gray-500">
                {modoPorProdutos
                  ? "Selecione ou cadastre um fornecedor para corrigir os vínculos em lote"
                  : "Digite ou selecione um fornecedor para carregar seus produtos"}
              </p>
              <button
                type="button"
                onClick={abrirNovoGrupoFornecedor}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Grupos de fornecedor
              </button>
            </div>
            {!modoPorProdutos && formData.fornecedor_id && grupoFornecedorAtual && (
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
            {!modoPorProdutos && formData.fornecedor_id && !grupoFornecedorAtual && (
              <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                Este fornecedor ainda nao esta em um grupo. Use "Grupos de fornecedor" para unificar
                CNPJs.
              </div>
            )}
            {!modoPorProdutos && formData.fornecedor_id && (
              <button
                type="button"
                onClick={abrirFluxoSugestaoInteligente}
                disabled={loadingPrepararSugestao}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-teal-700 disabled:opacity-60"
              >
                <Lightbulb className="h-4 w-4" />
                {loadingPrepararSugestao
                  ? "Verificando rascunho..."
                  : "Sugestao Inteligente de Pedido"}
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

        {modoPorProdutos ? (
          <PedidoCompraCatalogoProdutos
            filtro={filtroProdutosPedido}
            itensPedido={formData.itens}
            loading={loadingProdutosPedido}
            onAdicionar={adicionarProdutoCatalogo}
            onChangeFiltro={alterarFiltroProdutosPedido}
            onChangePagina={setPaginaProdutosPedido}
            onChangeTermo={alterarTermoProdutosPedido}
            paginacao={paginacaoProdutosPedido}
            produtos={produtos}
            termo={produtoTexto}
          />
        ) : null}

        <div className="border-t pt-4">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold text-slate-900">
                {modoPorProdutos ? "Produtos adicionados" : "Itens do pedido"} (
                {formData.itens.length})
              </h3>
              {modoPorProdutos ? (
                <p className="mt-1 text-xs text-slate-500">
                  Revise as quantidades e selecione os itens que deseja vincular ao fornecedor.
                </p>
              ) : null}
            </div>
          </div>
          {!modoPorProdutos ? (
            <div className="grid grid-cols-1 gap-3 mb-4 md:grid-cols-12">
              <div className="relative md:col-span-4">
                <label className="mb-1 block text-xs font-semibold text-slate-600">Produto</label>
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
                    if (modoPorProdutos || formData.fornecedor_id) {
                      setMostrarSugestoesProduto(true);
                    }
                  }}
                  onBlur={() => {
                    setTimeout(() => setMostrarSugestoesProduto(false), 120);
                  }}
                  placeholder={
                    !modoPorProdutos && !formData.fornecedor_id
                      ? "Selecione um fornecedor primeiro"
                      : "Pesquise por nome, SKU ou código de barras"
                  }
                  disabled={!modoPorProdutos && !formData.fornecedor_id}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100 focus:ring-2 focus:ring-blue-500"
                />
                {mostrarSugestoesProduto &&
                  produtosFiltrados.length > 0 &&
                  (modoPorProdutos || formData.fornecedor_id) && (
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
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-semibold text-slate-600">
                  Qtd. pedida
                </label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="Ex: 2"
                  value={itemForm.quantidade_pedida}
                  onChange={(e) => setItemForm({ ...itemForm, quantidade_pedida: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
                {itemForm.quantidade_pedida && (
                  <div
                    className="mt-1 text-xs font-semibold text-slate-600"
                    title={tooltipQuantidadeItem}
                  >
                    {formatarQuantidadeCompraPedido(itemPreview)}
                  </div>
                )}
              </div>
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-semibold text-slate-600">Unidade</label>
                <select
                  value={unidadeCompraAtual}
                  onChange={(e) => {
                    const unidade = e.target.value;
                    const quantidadeAtual =
                      itemForm.quantidade_por_embalagem && itemForm.quantidade_por_embalagem !== "1"
                        ? itemForm.quantidade_por_embalagem
                        : "";
                    const proximaQuantidadePorEmbalagem =
                      unidade === "UN"
                        ? "1"
                        : quantidadeAtual || produtoSelecionadoItem?.itens_por_caixa || "";
                    setItemForm({
                      ...itemForm,
                      unidade_compra: unidade,
                      quantidade_por_embalagem: proximaQuantidadePorEmbalagem,
                    });
                  }}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  title="Unidade usada para pedir ao fornecedor"
                >
                  {UNIDADES_COMPRA_OPCOES.map((opcao) => (
                    <option key={opcao.value} value={opcao.value}>
                      {opcao.label}
                    </option>
                  ))}
                </select>
              </div>
              {itemUsaEmbalagem && (
                <div className="md:col-span-2">
                  <label className="mb-1 block text-xs font-semibold text-slate-600">
                    Unid. por {unidadeCompraAtual}
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min="1"
                      step="1"
                      placeholder="Opcional"
                      value={itemForm.quantidade_por_embalagem}
                      onChange={(e) =>
                        setItemForm({ ...itemForm, quantidade_por_embalagem: e.target.value })
                      }
                      className="min-w-0 flex-1 px-4 py-2 border border-gray-300 rounded-lg"
                      title="Quantas unidades vendaveis vem em cada caixa, fardo ou pacote"
                    />
                    <button
                      type="button"
                      onClick={() => setItemForm({ ...itemForm, quantidade_por_embalagem: "" })}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                      title="Deixar a quantidade por embalagem para conferir na entrada da nota"
                    >
                      Nao sei
                    </button>
                  </div>
                </div>
              )}
              <div className={itemUsaEmbalagem ? "md:col-span-2" : "md:col-span-4"}>
                <label className="mb-1 block text-xs font-semibold text-slate-600">
                  Custo unitario
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    step="0.01"
                    placeholder="R$"
                    value={itemForm.preco_unitario}
                    onChange={(e) => setItemForm({ ...itemForm, preco_unitario: e.target.value })}
                    className="min-w-0 flex-1 px-4 py-2 border border-gray-300 rounded-lg"
                  />
                  <button
                    type="button"
                    onClick={adicionarItem}
                    className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                    title="Adicionar item ao pedido"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          {formData.itens.length > 0 && (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    {modoPorProdutos ? (
                      <th className="w-10 px-3 py-2 text-left">
                        <input
                          type="checkbox"
                          checked={todosProdutosSelecionados}
                          onChange={alternarTodosProdutosVinculo}
                          aria-label="Selecionar todos os produtos para vincular"
                          className="h-4 w-4 rounded"
                        />
                      </th>
                    ) : null}
                    <th className="w-12 px-4 py-2 text-left text-sm font-semibold">#</th>
                    <th className="px-4 py-2 text-left text-sm font-semibold">Produto</th>
                    <th className="px-4 py-2 text-right text-sm font-semibold">Qtd. pedida</th>
                    <th className="px-4 py-2 text-right text-sm font-semibold">Preço</th>
                    <th className="px-4 py-2 text-right text-sm font-semibold">Total</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {formData.itens.map((item, index) => (
                    <tr key={index} className="border-t">
                      {modoPorProdutos ? (
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={produtosVinculoSelecionados.includes(Number(item.produto_id))}
                            onChange={() => alternarProdutoVinculo(item.produto_id)}
                            aria-label={`Selecionar ${item.produto_nome} para vincular`}
                            className="h-4 w-4 rounded"
                          />
                        </td>
                      ) : null}
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
                      <td
                        className="px-4 py-2 text-right"
                        title={montarTooltipQuantidadeCompraPedido(item)}
                      >
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
                        <div className="mt-1 text-xs font-semibold text-slate-600">
                          {formatarQuantidadeCompraPedido(item)}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatMoneyBRL(numeroSeguro(item.preco_unitario))}
                      </td>
                      <td className="px-4 py-2 text-right font-semibold">
                        {formatMoneyBRL(numeroSeguro(item.total))}
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
          {modoPorProdutos && formData.itens.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center">
              <p className="font-semibold text-slate-700">Nenhum produto adicionado ainda</p>
              <p className="mt-1 text-sm text-slate-500">
                Use a lista de produtos sugeridos acima para começar o pedido.
              </p>
            </div>
          ) : null}
          {modoPorProdutos && formData.itens.length > 0 ? (
            <PedidoCompraVinculoLote
              fornecedorSelecionado={fornecedorSelecionado}
              onVincular={vincularProdutosFornecedorPedido}
              selecionados={produtosVinculoSelecionados.length}
              setVinculoComoPrincipal={setVinculoComoPrincipal}
              vinculando={vinculandoProdutos}
              vinculoComoPrincipal={vinculoComoPrincipal}
            />
          ) : null}
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
            <div className="text-2xl font-bold text-green-600">
              {formatMoneyBRL(calcularTotal())}
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3 font-semibold text-white hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? (
            "Processando..."
          ) : modoEdicao ? (
            <>
              <Save className="h-4 w-4" />
              Salvar alteracoes
            </>
          ) : (
            <>
              <Check className="h-4 w-4" />
              Criar Pedido
            </>
          )}
        </button>
      </form>
    </div>
  );
}
