import {
  BookmarkPlus,
  ChevronDown,
  ChevronRight,
  Layers,
  Minus,
  Package,
  Plus,
  Trash2,
} from "lucide-react";
import QuantidadeInput from "../QuantidadeInput";
import SubtotalInput from "../SubtotalInput";
import { formatMoneyBRL } from "../../utils/formatters";
import { resolveMediaUrl } from "../../utils/mediaUrl";
import { obterResumoPrecoPorKg } from "../../utils/racaoPrecoKg";
import { formatarVariacao } from "../../utils/variacoes";
import ProdutoSelector from "../produtos/ProdutoSelector";
import CopyableCode from "../ui/CopyableCode";
import CopyableValue from "../ui/CopyableValue";
import Panel from "../ui/Panel";

function obterImagemMiniaturaItem(item) {
  return (
    item?.produto_imagem_thumbnail ||
    item?.produto?.imagem_principal_thumbnail ||
    item?.produto_imagem_principal ||
    item?.produto?.imagem_principal ||
    null
  );
}

function obterImagemSugestaoProduto(produto) {
  return produto?.imagem_principal_thumbnail || produto?.imagem_principal || null;
}

function obterPrecoPDV(produto) {
  const preco = produto?.preco_venda_pdv ?? produto?.preco_venda_efetivo ?? produto?.preco_venda;
  const numero = Number.parseFloat(preco);
  return Number.isFinite(numero) ? numero : 0;
}

function ProdutoSugestaoPDV({
  onAdicionarNaListaEsperaRapido,
  onSelecionarProdutoSugerido,
  produto,
  vendaAtual,
}) {
  const estoqueZerado =
    produto.tipo_produto === "KIT" && produto.tipo_kit === "VIRTUAL"
      ? produto.estoque_virtual !== undefined && Math.floor(produto.estoque_virtual) <= 0
      : produto.estoque_atual !== undefined && Math.floor(produto.estoque_atual) <= 0;
  const imagemSugestao = resolveMediaUrl(obterImagemSugestaoProduto(produto));
  const precoPDV = obterPrecoPDV(produto);
  const precoOriginal = Number.parseFloat(produto.preco_venda_original ?? produto.preco_venda ?? 0);
  const promocaoAtiva = Boolean(produto.promocao_pdv_ativa);
  const resumoPrecoKg = obterResumoPrecoPorKg(produto);

  return (
    <button
      key={produto.id}
      type="button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={() => onSelecionarProdutoSugerido(produto)}
      className="w-full border-b px-4 py-3 text-left last:border-b-0 hover:bg-gray-50"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          {imagemSugestao ? (
            <img
              src={imagemSugestao}
              alt={produto.nome || "Produto"}
              className="h-12 w-12 flex-shrink-0 rounded-lg border border-gray-200 bg-white object-cover"
              loading="lazy"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          ) : (
            <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50 text-gray-300">
              <Package className="h-5 w-5" />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 items-center gap-1.5 font-medium text-gray-900">
              <span className="min-w-0 truncate" title={produto.nome}>
                {produto.nome}
              </span>
              {estoqueZerado && vendaAtual.cliente && (
                <span
                  onClick={(e) => onAdicionarNaListaEsperaRapido(produto, e)}
                  className="inline-flex cursor-pointer items-center gap-0.5 rounded bg-orange-100 px-1.5 py-0.5 text-xs font-medium text-orange-600 transition-colors hover:bg-orange-200 hover:text-orange-800"
                  title="Sem estoque, clique para adicionar a lista de espera"
                >
                  <BookmarkPlus className="h-3 w-3" />
                  <span>Lista de espera</span>
                </span>
              )}
            </div>
            {produto.tipo_produto === "VARIACAO" && formatarVariacao(produto) && (
              <div className="mt-0.5 text-xs font-medium text-blue-600">
                Variacao: {formatarVariacao(produto)}
              </div>
            )}
            <div className="text-sm text-gray-500">
              {produto.codigo && `Cod: ${produto.codigo}`}
              {produto.tipo_produto === "KIT" && produto.tipo_kit === "VIRTUAL"
                ? produto.estoque_virtual !== undefined &&
                  ` | Estoque: ${Math.floor(produto.estoque_virtual)}`
                : produto.estoque_atual !== undefined &&
                  ` | Estoque: ${Math.floor(produto.estoque_atual)}`}
            </div>
            {resumoPrecoKg.disponivel && (
              <div className="mt-1 text-xs font-semibold text-teal-700">
                {resumoPrecoKg.pesoFormatado} - {resumoPrecoKg.precoPorKgFormatado}
              </div>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-row items-center justify-between gap-2 sm:flex-col sm:items-end sm:justify-start">
          {promocaoAtiva && precoOriginal > precoPDV && (
            <span className="text-xs text-gray-400 line-through">
              {formatMoneyBRL(precoOriginal)}
            </span>
          )}
          <div className="text-lg font-semibold text-green-600">{formatMoneyBRL(precoPDV)}</div>
          {promocaoAtiva && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
              promocao
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

export default function PDVProdutosCard({
  buscaProduto,
  buscaProdutoContainerRef,
  copiadoCodigoItem,
  inputProdutoRef,
  itensKitExpandidos,
  modoVisualizacao,
  mostrarSugestoesProduto,
  onAbrirModalDescontoItem,
  onAdicionarNaListaEsperaRapido,
  onAlterarQuantidade,
  onAtualizarPetItem,
  onAtualizarQuantidadeItem,
  onBuscarProdutoChange,
  onBuscarProdutoFocus,
  onBuscarProdutoKeyDown,
  onCopiarCodigoProdutoCarrinho,
  onRemoverItem,
  onSelecionarProdutoSugerido,
  onToggleKitExpansion,
  pendenciasProdutoIds,
  produtosSugeridos,
  vendaAtual,
}) {
  return (
    <Panel id="tour-pdv-carrinho" padding="sm">
      <h2 className="mb-3 flex items-center text-base font-semibold text-gray-900">
        <Package className="mr-2 h-4 w-4 text-blue-600" />
        Produtos e Servicos
      </h2>

      <ProdutoSelector
        id="tour-pdv-busca"
        autoFocus={!modoVisualizacao}
        className="mb-4"
        containerRef={buscaProdutoContainerRef}
        disabled={modoVisualizacao}
        inputRef={inputProdutoRef}
        onChange={onBuscarProdutoChange}
        onFocus={onBuscarProdutoFocus}
        onKeyDown={onBuscarProdutoKeyDown}
        onSelect={onSelecionarProdutoSugerido}
        placeholder="Digite o nome do produto, codigo de barras ou servico..."
        renderSuggestion={(produto) => (
          <ProdutoSugestaoPDV
            key={produto.id}
            onAdicionarNaListaEsperaRapido={onAdicionarNaListaEsperaRapido}
            onSelecionarProdutoSugerido={onSelecionarProdutoSugerido}
            produto={produto}
            vendaAtual={vendaAtual}
          />
        )}
        showSuggestions={mostrarSugestoesProduto}
        suggestions={produtosSugeridos}
        value={buscaProduto}
      />

      {vendaAtual.itens.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>Nenhum item adicionado</p>
          <p className="text-sm mt-1">Busque e adicione produtos ou servicos</p>
        </div>
      ) : (
        <div className="space-y-3">
          {vendaAtual.itens.map((item, index) => {
            const isKit = item.tipo_produto === "KIT";
            const isExpanded = itensKitExpandidos[index];
            const codigoProdutoExibicao =
              item.produto_codigo ||
              item.codigo ||
              item.sku ||
              item.produto?.codigo ||
              item.produto?.sku ||
              item.produto?.codigo_barras ||
              item.produto_codigo_barras ||
              "";
            const imagemProduto = resolveMediaUrl(obterImagemMiniaturaItem(item));
            const chaveCodigoItem = `${item.produto_id || "item"}-${index}`;
            const hasComposicao = isKit && item.composicao_kit && item.composicao_kit.length > 0;
            const itemSemEstoque =
              item.tipo_produto === "KIT" && item.tipo_kit === "VIRTUAL"
                ? item.estoque_virtual !== undefined && Math.floor(item.estoque_virtual) <= 0
                : item.estoque_atual !== undefined && Math.floor(item.estoque_atual) <= 0;
            const itemEmPromocao = Boolean(item.em_promocao);
            const resumoPrecoKg = obterResumoPrecoPorKg(item);

            return (
              <div
                key={index}
                data-testid="pdv-cart-item"
                className="space-y-2.5 overflow-hidden rounded-lg border border-gray-200 bg-gray-50 p-3 transition-colors hover:border-blue-400"
              >
                <div
                  className="flex cursor-pointer flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"
                  onClick={() => !modoVisualizacao && onAbrirModalDescontoItem(item)}
                >
                  <div className="flex min-w-0 flex-1 items-start gap-2">
                    {hasComposicao && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleKitExpansion(index);
                        }}
                        className="mt-1 text-gray-500 hover:text-blue-600 transition-colors"
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-5 h-5" />
                        ) : (
                          <ChevronRight className="w-5 h-5" />
                        )}
                      </button>
                    )}

                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 flex-wrap items-start gap-2">
                        <div
                          className="flex min-w-0 max-w-full flex-1 items-start gap-2"
                          title={item.produto_nome}
                        >
                          {imagemProduto && (
                            <img
                              src={imagemProduto}
                              alt={item.produto_nome || "Produto"}
                              className="w-11 h-11 rounded-lg object-cover border border-gray-200 bg-white flex-shrink-0"
                              loading="lazy"
                              onError={(e) => {
                                e.currentTarget.style.display = "none";
                              }}
                            />
                          )}
                          <CopyableValue
                            className="max-w-full flex-1"
                            copied={copiadoCodigoItem === `nome-${chaveCodigoItem}`}
                            title="Copiar nome do produto"
                            value={item.produto_nome}
                            valueClassName="font-medium text-gray-900"
                            onCopy={() =>
                              onCopiarCodigoProdutoCarrinho(
                                item.produto_nome,
                                `nome-${chaveCodigoItem}`,
                              )
                            }
                          />
                        </div>
                        <CopyableCode
                          copied={copiadoCodigoItem === chaveCodigoItem}
                          label="SKU"
                          onCopy={() =>
                            onCopiarCodigoProdutoCarrinho(codigoProdutoExibicao, chaveCodigoItem)
                          }
                          title="Copiar SKU do produto"
                          value={codigoProdutoExibicao}
                        />
                        {itemEmPromocao && (
                          <span
                            title={item.promocao_origem || "Promocao aplicada no PDV"}
                            className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-amber-700"
                          >
                            promocao
                          </span>
                        )}
                        {vendaAtual.cliente && itemSemEstoque && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (!pendenciasProdutoIds.includes(item.produto_id)) {
                                onAdicionarNaListaEsperaRapido(
                                  {
                                    id: item.produto_id,
                                    nome: item.produto_nome,
                                  },
                                  e,
                                );
                              }
                            }}
                            title={
                              pendenciasProdutoIds.includes(item.produto_id)
                                ? "Ja na lista de espera"
                                : "Adicionar a lista de espera"
                            }
                            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium transition-colors ${
                              pendenciasProdutoIds.includes(item.produto_id)
                                ? "bg-orange-100 text-orange-600 cursor-default"
                                : "bg-gray-100 text-gray-400 hover:bg-orange-100 hover:text-orange-500 cursor-pointer"
                            }`}
                          >
                            <BookmarkPlus className="w-3 h-3" />
                            Espera
                          </button>
                        )}
                        {isKit && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                            <Layers className="w-3 h-3" />
                            KIT
                          </span>
                        )}
                        {resumoPrecoKg.disponivel && (
                          <span
                            className="inline-flex items-center rounded-full bg-teal-50 px-2 py-0.5 text-xs font-semibold text-teal-700"
                            title={`${resumoPrecoKg.pesoFormatado} - ${resumoPrecoKg.precoFormatado}`}
                          >
                            {resumoPrecoKg.precoPorKgFormatado}
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-1 gap-y-0.5 text-sm text-gray-500">
                        <span>
                          {item.quantidade} Unidade
                          {item.quantidade !== 1 ? "s" : ""} x {formatMoneyBRL(item.preco_unitario)}
                        </span>
                        {resumoPrecoKg.disponivel && (
                          <span className="font-medium text-teal-700">
                            ({resumoPrecoKg.pesoFormatado})
                          </span>
                        )}
                        {itemEmPromocao && item.preco_venda_original > item.preco_unitario && (
                          <span className="ml-1 text-xs text-gray-400 line-through">
                            {formatMoneyBRL(item.preco_venda_original)}
                          </span>
                        )}
                        {item.desconto_valor > 0 && (
                          <span className="text-orange-600 ml-1">
                            com {formatMoneyBRL(item.desconto_valor)} de desconto
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div
                    className="flex w-full shrink-0 flex-wrap items-center justify-end gap-2 sm:w-auto sm:flex-nowrap"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex shrink-0 items-center rounded-lg border border-gray-300 bg-white">
                      <button
                        type="button"
                        onClick={() => onAlterarQuantidade(index, -1)}
                        disabled={modoVisualizacao}
                        className="p-2 hover:bg-gray-100 rounded-l-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Minus className="w-4 h-4" />
                      </button>
                      <QuantidadeInput
                        value={item.quantidade}
                        onChange={(novaQuantidade) =>
                          onAtualizarQuantidadeItem(index, novaQuantidade)
                        }
                        disabled={modoVisualizacao}
                        className="w-20 px-2 py-1 text-center font-medium border-none focus:ring-0 disabled:bg-gray-50"
                      />
                      <button
                        type="button"
                        onClick={() => onAlterarQuantidade(index, 1)}
                        disabled={modoVisualizacao}
                        className="p-2 hover:bg-gray-100 rounded-r-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="shrink-0">
                      <SubtotalInput
                        subtotal={item.subtotal}
                        precoUnitario={item.preco_unitario}
                        disabled={modoVisualizacao}
                        onQuantidadeChange={(novaQuantidade) =>
                          onAtualizarQuantidadeItem(index, novaQuantidade)
                        }
                      />
                    </div>

                    <button
                      type="button"
                      onClick={() => onRemoverItem(index)}
                      disabled={modoVisualizacao}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {hasComposicao && isExpanded && (
                  <div className="ml-7 mt-3 overflow-hidden p-3 bg-white rounded-lg border border-gray-200">
                    <div className="text-xs font-semibold text-gray-600 uppercase mb-2">
                      Composicao do KIT
                    </div>
                    <div className="space-y-1.5">
                      {item.composicao_kit.map((componente, compIndex) => (
                        <div
                          key={compIndex}
                          className="flex min-w-0 items-center justify-between gap-3 text-sm py-1.5 px-2 rounded hover:bg-gray-50"
                        >
                          <div className="flex min-w-0 items-center gap-2">
                            <Package className="w-4 h-4 shrink-0 text-gray-400" />
                            <span
                              className="truncate text-gray-700"
                              title={componente.produto_nome}
                            >
                              {componente.produto_nome}
                            </span>
                          </div>
                          <span className="shrink-0 text-gray-500 font-medium">
                            {componente.quantidade}x
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 text-xs text-gray-500 italic">
                      Componentes apenas informativos (nao editaveis)
                    </div>
                  </div>
                )}

                {vendaAtual.cliente?.pets && vendaAtual.cliente.pets.length > 0 && (
                  <div
                    className="flex flex-col gap-2 sm:flex-row sm:items-center"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <label className="text-sm font-medium text-gray-600 sm:w-16">Pet:</label>
                    <select
                      value={item.pet_id || ""}
                      onChange={(e) =>
                        onAtualizarPetItem(
                          index,
                          e.target.value ? parseInt(e.target.value, 10) : null,
                        )
                      }
                      disabled={modoVisualizacao}
                      className="h-9 flex-1 rounded-lg border border-gray-300 px-3 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-50"
                    >
                      <option value="">Nao especificado</option>
                      {vendaAtual.cliente.pets.map((pet) => (
                        <option key={pet.id} value={pet.id}>
                          {pet.codigo} - {pet.nome}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}
