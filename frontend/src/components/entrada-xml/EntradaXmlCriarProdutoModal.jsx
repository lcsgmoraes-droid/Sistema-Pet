import PropTypes from "prop-types";
import { X } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import IconActionButton from "../ui/IconActionButton";
import LoadingState from "../ui/LoadingState";

function CampoTexto({
  children,
  help,
  id,
  inputClassName,
  onChange,
  placeholder,
  required,
  type,
  value,
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-semibold text-gray-700">
        {children}
        {required ? " *" : ""}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        className={[
          "w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-blue-500",
          inputClassName,
        ]
          .filter(Boolean)
          .join(" ")}
        placeholder={placeholder}
      />
      {help ? <p className="mt-1 text-xs text-gray-500">{help}</p> : null}
    </div>
  );
}

CampoTexto.propTypes = {
  children: PropTypes.node.isRequired,
  help: PropTypes.string,
  id: PropTypes.string.isRequired,
  inputClassName: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
  required: PropTypes.bool,
  type: PropTypes.string,
  value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
};

CampoTexto.defaultProps = {
  help: "",
  inputClassName: "",
  placeholder: "",
  required: false,
  type: "text",
};

export default function EntradaXmlCriarProdutoModal({
  aberto,
  calcularMargemLucro,
  calcularPrecoVenda,
  carregandoSugestao,
  criarProdutoNovo,
  formProduto,
  formatarValorFiscal,
  itemSelecionadoParaCriar,
  loading,
  obterCustoAquisicaoItem,
  onClose,
  setFormProduto,
  sugestaoSku,
}) {
  if (!aberto || !itemSelecionadoParaCriar) return null;

  const produtoValido = Boolean(
    formProduto.sku &&
    formProduto.nome &&
    formProduto.preco_custo &&
    Number.parseFloat(formProduto.preco_custo) > 0 &&
    formProduto.preco_venda &&
    Number.parseFloat(formProduto.preco_venda) > 0,
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white">
        <div className="sticky top-0 flex items-center justify-between border-b bg-white px-6 py-4">
          <div>
            <h2 className="text-xl font-bold">Criar Novo Produto</h2>
            <p className="text-sm text-gray-600">A partir do item da NF-e</p>
          </div>
          <IconActionButton
            icon={X}
            intent="neutral"
            tone="ghost"
            title="Fechar"
            onClick={onClose}
          />
        </div>

        <div className="px-6 py-4">
          {carregandoSugestao ? (
            <LoadingState label="Gerando sugestoes de SKU..." />
          ) : (
            <div className="space-y-4">
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                <div className="mb-2 font-semibold text-blue-900">Dados da NF-e:</div>
                <div className="space-y-1 text-sm text-blue-800">
                  <div>
                    <strong>Descricao:</strong> {itemSelecionadoParaCriar.descricao}
                  </div>
                  <div>
                    <strong>Codigo Fornecedor:</strong> {itemSelecionadoParaCriar.codigo_produto}
                  </div>
                  <div>
                    <strong>NCM:</strong> {itemSelecionadoParaCriar.ncm}
                  </div>
                  {itemSelecionadoParaCriar.ean && (
                    <div>
                      <strong>EAN:</strong> {itemSelecionadoParaCriar.ean}
                    </div>
                  )}
                  <div>
                    <strong>Valor Unitario NF:</strong> R${" "}
                    {itemSelecionadoParaCriar.valor_unitario.toFixed(2)}
                  </div>
                  <div>
                    <strong>Custo de Aquisicao:</strong> R${" "}
                    {formatarValorFiscal(obterCustoAquisicaoItem(itemSelecionadoParaCriar), 4)}
                  </div>
                </div>
              </div>

              {sugestaoSku?.ja_existe && (
                <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4">
                  <div className="mb-2 font-semibold text-yellow-900">
                    Codigo do fornecedor "{sugestaoSku.sku_proposto}" ja esta em uso.
                  </div>
                  <div className="mb-3 text-sm text-yellow-800">
                    Produto existente: <strong>{sugestaoSku.produto_existente.nome}</strong>
                    <br />
                    <span className="text-xs">
                      Um SKU alternativo foi sugerido automaticamente. Voce pode alterar se
                      preferir.
                    </span>
                  </div>
                  <div className="mb-2 text-sm font-semibold text-yellow-800">
                    Outras opcoes de SKU disponiveis:
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {sugestaoSku.sugestoes.map((sugestao) => (
                      <ActionButton
                        key={sugestao.sku}
                        type="button"
                        intent="edit"
                        tone={formProduto.sku === sugestao.sku ? "solid" : "soft"}
                        size="xs"
                        className={sugestao.padrao ? "ring-2 ring-yellow-400" : ""}
                        onClick={() => setFormProduto({ ...formProduto, sku: sugestao.sku })}
                      >
                        {sugestao.sku}
                        {sugestao.padrao ? " (padrao)" : ""}
                      </ActionButton>
                    ))}
                  </div>
                </div>
              )}

              {sugestaoSku && !sugestaoSku.ja_existe && (
                <div className="rounded-lg border border-green-300 bg-green-50 p-3">
                  <div className="text-sm text-green-800">
                    <strong>SKU disponivel.</strong> O codigo do fornecedor pode ser usado
                    diretamente.
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <CampoTexto
                  id="novo-produto-sku"
                  value={formProduto.sku}
                  onChange={(event) => setFormProduto({ ...formProduto, sku: event.target.value })}
                  inputClassName="font-mono"
                  placeholder="Ex: MGZ-12345"
                  help="Voce pode editar o SKU se preferir"
                  required
                >
                  SKU / Codigo do Produto
                </CampoTexto>

                <CampoTexto
                  id="novo-produto-nome"
                  value={formProduto.nome}
                  onChange={(event) => setFormProduto({ ...formProduto, nome: event.target.value })}
                  placeholder="Nome completo do produto"
                  required
                >
                  Nome do Produto
                </CampoTexto>

                <div>
                  <label
                    htmlFor="novo-produto-descricao"
                    className="mb-1 block text-sm font-semibold text-gray-700"
                  >
                    Descricao
                  </label>
                  <textarea
                    id="novo-produto-descricao"
                    value={formProduto.descricao}
                    onChange={(event) =>
                      setFormProduto({ ...formProduto, descricao: event.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-blue-500"
                    rows="2"
                    placeholder="Descricao detalhada (opcional)"
                  />
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <CampoTexto
                    id="novo-produto-preco-custo"
                    type="number"
                    value={formProduto.preco_custo}
                    onChange={(event) => {
                      const custo = event.target.value;
                      const margem = Number.parseFloat(formProduto.margem_lucro) || 0;
                      setFormProduto({
                        ...formProduto,
                        preco_custo: custo,
                        preco_venda: custo
                          ? calcularPrecoVenda(Number.parseFloat(custo), margem)
                          : "",
                      });
                    }}
                    required
                  >
                    Preco de Custo
                  </CampoTexto>

                  <CampoTexto
                    id="novo-produto-margem"
                    type="number"
                    value={formProduto.margem_lucro}
                    onChange={(event) => {
                      const margem = event.target.value;
                      const custo = Number.parseFloat(formProduto.preco_custo) || 0;
                      setFormProduto({
                        ...formProduto,
                        margem_lucro: margem,
                        preco_venda:
                          custo && margem
                            ? calcularPrecoVenda(custo, Number.parseFloat(margem))
                            : "",
                      });
                    }}
                    required
                  >
                    Margem (%)
                  </CampoTexto>

                  <CampoTexto
                    id="novo-produto-preco-venda"
                    type="number"
                    value={formProduto.preco_venda}
                    onChange={(event) => {
                      const venda = event.target.value;
                      const custo = Number.parseFloat(formProduto.preco_custo) || 0;
                      setFormProduto({
                        ...formProduto,
                        preco_venda: venda,
                        margem_lucro:
                          custo && venda
                            ? calcularMargemLucro(custo, Number.parseFloat(venda))
                            : "",
                      });
                    }}
                    required
                  >
                    Preco de Venda
                  </CampoTexto>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <CampoTexto
                    id="novo-produto-estoque-minimo"
                    type="number"
                    value={formProduto.estoque_minimo}
                    onChange={(event) =>
                      setFormProduto({
                        ...formProduto,
                        estoque_minimo: Number.parseInt(event.target.value),
                      })
                    }
                  >
                    Estoque Minimo
                  </CampoTexto>

                  <CampoTexto
                    id="novo-produto-estoque-maximo"
                    type="number"
                    value={formProduto.estoque_maximo}
                    onChange={(event) =>
                      setFormProduto({
                        ...formProduto,
                        estoque_maximo: Number.parseInt(event.target.value),
                      })
                    }
                  >
                    Estoque Maximo
                  </CampoTexto>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="sticky bottom-0 flex justify-end gap-3 border-t bg-white px-6 py-4">
          <ActionButton type="button" intent="neutral" tone="soft" size="md" onClick={onClose}>
            Cancelar
          </ActionButton>
          <ActionButton
            type="button"
            intent="create"
            size="md"
            loading={loading}
            disabled={loading || !produtoValido}
            onClick={criarProdutoNovo}
          >
            {loading ? "Criando..." : "Criar e Vincular Produto"}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}

EntradaXmlCriarProdutoModal.propTypes = {
  aberto: PropTypes.bool.isRequired,
  calcularMargemLucro: PropTypes.func.isRequired,
  calcularPrecoVenda: PropTypes.func.isRequired,
  carregandoSugestao: PropTypes.bool.isRequired,
  criarProdutoNovo: PropTypes.func.isRequired,
  formProduto: PropTypes.shape({
    descricao: PropTypes.string,
    estoque_maximo: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    estoque_minimo: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    margem_lucro: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    nome: PropTypes.string,
    preco_custo: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    preco_venda: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    sku: PropTypes.string,
  }).isRequired,
  formatarValorFiscal: PropTypes.func.isRequired,
  itemSelecionadoParaCriar: PropTypes.shape({
    codigo_produto: PropTypes.string,
    descricao: PropTypes.string,
    ean: PropTypes.string,
    ncm: PropTypes.string,
    valor_unitario: PropTypes.number,
  }),
  loading: PropTypes.bool.isRequired,
  obterCustoAquisicaoItem: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
  setFormProduto: PropTypes.func.isRequired,
  sugestaoSku: PropTypes.shape({
    ja_existe: PropTypes.bool,
    produto_existente: PropTypes.shape({
      nome: PropTypes.string,
    }),
    sku_proposto: PropTypes.string,
    sugestoes: PropTypes.arrayOf(
      PropTypes.shape({
        padrao: PropTypes.bool,
        sku: PropTypes.string,
      }),
    ),
  }),
};

EntradaXmlCriarProdutoModal.defaultProps = {
  itemSelecionadoParaCriar: null,
  sugestaoSku: null,
};
