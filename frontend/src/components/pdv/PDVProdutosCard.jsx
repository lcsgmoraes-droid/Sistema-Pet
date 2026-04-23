import {
  BookmarkPlus,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  Layers,
  Minus,
  Package,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import QuantidadeInput from "../QuantidadeInput";
import SubtotalInput from "../SubtotalInput";
import { formatMoneyBRL } from "../../utils/formatters";
import { formatarVariacao } from "../../utils/variacoes";

function obterImagemPrincipalItem(item) {
  return item?.produto_imagem_principal || item?.produto?.imagem_principal || null;
}

function resolverImagemProduto(url) {
  if (!url) return null;
  if (String(url).startsWith("http")) return url;

  const origin = globalThis?.location?.origin || "";
  return origin && String(url).startsWith("/") ? `${origin}${url}` : url;
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
    <div
      id="tour-pdv-carrinho"
      className="bg-white rounded-lg shadow-sm border p-4"
    >
      <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center">
        <Package className="w-5 h-5 mr-2 text-blue-600" />
        Produtos e Servicos
      </h2>

      <div
        id="tour-pdv-busca"
        ref={buscaProdutoContainerRef}
        className="relative mb-4"
      >
        <div className="flex items-center">
          <input
            ref={inputProdutoRef}
            type="text"
            value={buscaProduto}
            onChange={(e) => onBuscarProdutoChange(e.target.value)}
            onFocus={onBuscarProdutoFocus}
            onKeyDown={onBuscarProdutoKeyDown}
            placeholder="Digite o nome do produto, codigo de barras ou servico..."
            disabled={modoVisualizacao}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
            autoFocus={!modoVisualizacao}
          />
          <Search className="w-5 h-5 text-gray-400 absolute right-3" />
        </div>

        {mostrarSugestoesProduto &&
          String(buscaProduto || "").trim().length >= 2 &&
          produtosSugeridos.length > 0 && (
            <div className="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {produtosSugeridos.map((produto) => {
                const estoqueZerado =
                  produto.tipo_produto === "KIT" &&
                  produto.tipo_kit === "VIRTUAL"
                    ? produto.estoque_virtual !== undefined &&
                      Math.floor(produto.estoque_virtual) <= 0
                    : produto.estoque_atual !== undefined &&
                      Math.floor(produto.estoque_atual) <= 0;

                return (
                  <button
                    key={produto.id}
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => onSelecionarProdutoSugerido(produto)}
                    className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b last:border-b-0"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-1.5 font-medium text-gray-900">
                          {produto.nome}
                          {estoqueZerado && vendaAtual.cliente && (
                            <span
                              onClick={(e) =>
                                onAdicionarNaListaEsperaRapido(produto, e)
                              }
                              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-orange-100 hover:bg-orange-200 text-orange-600 hover:text-orange-800 rounded text-xs font-medium transition-colors cursor-pointer"
                              title="Sem estoque, clique para adicionar a lista de espera"
                            >
                              <BookmarkPlus className="w-3 h-3" />
                              <span>Lista de espera</span>
                            </span>
                          )}
                        </div>
                        {produto.tipo_produto === "VARIACAO" &&
                          formatarVariacao(produto) && (
                            <div className="text-xs text-blue-600 font-medium mt-0.5">
                              Variacao: {formatarVariacao(produto)}
                            </div>
                          )}
                        <div className="text-sm text-gray-500">
                          {produto.codigo && `Cod: ${produto.codigo}`}
                          {produto.tipo_produto === "KIT" &&
                          produto.tipo_kit === "VIRTUAL"
                            ? produto.estoque_virtual !== undefined &&
                              ` | Estoque: ${Math.floor(produto.estoque_virtual)}`
                            : produto.estoque_atual !== undefined &&
                              ` | Estoque: ${Math.floor(produto.estoque_atual)}`}
                        </div>
                      </div>
                      <div className="text-lg font-semibold text-green-600">
                        {formatMoneyBRL(produto.preco_venda)}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
      </div>

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
              item.produto_codigo || item.codigo || item.sku || "";
            const imagemProduto = resolverImagemProduto(
              obterImagemPrincipalItem(item),
            );
            const chaveCodigoItem = `${item.produto_id || "item"}-${index}`;
            const hasComposicao =
              isKit &&
              item.composicao_kit &&
              item.composicao_kit.length > 0;
            const itemSemEstoque =
              item.tipo_produto === "KIT" && item.tipo_kit === "VIRTUAL"
                ? item.estoque_virtual !== undefined &&
                  Math.floor(item.estoque_virtual) <= 0
                : item.estoque_atual !== undefined &&
                  Math.floor(item.estoque_atual) <= 0;

            return (
              <div
                key={index}
                className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-400 space-y-3 transition-colors"
              >
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() =>
                    !modoVisualizacao && onAbrirModalDescontoItem(item)
                  }
                >
                  <div className="flex-1 flex items-start gap-2">
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

                    <div className="flex-1">
                      <div className="flex flex-wrap items-start gap-2">
                        <div className="inline-flex items-start gap-2">
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
                          <div className="inline-flex items-center gap-1.5 min-w-0">
                            <div className="font-medium text-gray-900 break-words">
                              {item.produto_nome}
                            </div>
                            {item.produto_nome && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onCopiarCodigoProdutoCarrinho(
                                    item.produto_nome,
                                    `nome-${chaveCodigoItem}`,
                                  );
                                }}
                                className="text-gray-400 hover:text-gray-700 transition-colors"
                                title="Copiar nome do produto"
                              >
                                {copiadoCodigoItem === `nome-${chaveCodigoItem}` ? (
                                  <Check className="w-3.5 h-3.5 text-green-600" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>
                            )}
                          </div>
                        </div>
                        {codigoProdutoExibicao && (
                          <div className="inline-flex items-center gap-1 text-xs text-gray-500">
                            <span>Cod: {codigoProdutoExibicao}</span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onCopiarCodigoProdutoCarrinho(
                                  codigoProdutoExibicao,
                                  chaveCodigoItem,
                                );
                              }}
                              className="text-gray-400 hover:text-gray-700"
                              title="Copiar codigo do produto"
                            >
                              {copiadoCodigoItem === chaveCodigoItem ? (
                                <Check className="w-3.5 h-3.5 text-green-600" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        )}
                        {vendaAtual.cliente && itemSemEstoque && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (
                                !pendenciasProdutoIds.includes(item.produto_id)
                              ) {
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
                      </div>
                      <div className="text-sm text-gray-500">
                        {item.quantidade} Unidade
                        {item.quantidade !== 1 ? "s" : ""} x{" "}
                        {formatMoneyBRL(item.preco_unitario)}
                        {item.desconto_valor > 0 && (
                          <span className="text-orange-600 ml-1">
                            com {formatMoneyBRL(item.desconto_valor)} de desconto
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div
                    className="flex items-center space-x-4"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center space-x-2 bg-white border border-gray-300 rounded-lg">
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

                    <SubtotalInput
                      subtotal={item.subtotal}
                      precoUnitario={item.preco_unitario}
                      disabled={modoVisualizacao}
                      onQuantidadeChange={(novaQuantidade) =>
                        onAtualizarQuantidadeItem(index, novaQuantidade)
                      }
                    />

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
                  <div className="ml-7 mt-3 p-3 bg-white rounded-lg border border-gray-200">
                    <div className="text-xs font-semibold text-gray-600 uppercase mb-2">
                      Composicao do KIT
                    </div>
                    <div className="space-y-1.5">
                      {item.composicao_kit.map((componente, compIndex) => (
                        <div
                          key={compIndex}
                          className="flex items-center justify-between text-sm py-1.5 px-2 rounded hover:bg-gray-50"
                        >
                          <div className="flex items-center gap-2">
                            <Package className="w-4 h-4 text-gray-400" />
                            <span className="text-gray-700">
                              {componente.produto_nome}
                            </span>
                          </div>
                          <span className="text-gray-500 font-medium">
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
                    className="flex items-center space-x-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <label className="text-sm font-medium text-gray-600 w-16">
                      Pet:
                    </label>
                    <select
                      value={item.pet_id || ""}
                      onChange={(e) =>
                        onAtualizarPetItem(
                          index,
                          e.target.value ? parseInt(e.target.value, 10) : null,
                        )
                      }
                      disabled={modoVisualizacao}
                      className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
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
    </div>
  );
}
