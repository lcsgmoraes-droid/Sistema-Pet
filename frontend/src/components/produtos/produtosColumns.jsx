import { actionButtonClasses } from "../ui/actionStyles";
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  History,
  Pencil,
  Unlock,
  UploadCloud,
  XCircle,
} from "lucide-react";
import { markdownToPlainText } from "../../utils/safeMarkdown";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoMenuAcoes from "../v2/BotaoMenuAcoes/BotaoMenuAcoes";
import InputCheckbox from "../v2/InputCheckbox/InputCheckbox";
import ChannelBadges from "../ui/ChannelBadges";
import {
  isKitFisicoProduto,
  isKitVirtualProduto,
  isExpandIdSelected,
  isProdutoComComposicao,
  obterFontesImagemProduto,
  obterCanaisAtivosProduto,
  obterEstoqueVisualProduto,
} from "./produtosUtils";
import { createProdutosPricingColumns } from "./produtosPricingColumns";

const getProdutoBlingId = (produto) => String(produto?.bling_produto_id || "").trim();
const getProdutoBlingActionKey = (produtoId) => `produto-bling-${produtoId}`;

function renderBlingStatusBadge(produto, props) {
  const blingId = getProdutoBlingId(produto);
  const status = String(produto?.bling_sync_status || "").toLowerCase();
  const temErro = status === "erro" || Boolean(produto?.bling_ultimo_erro);
  const loading = props.blingActionKey === getProdutoBlingActionKey(produto.id);

  if (produto?.tipo_produto === "PAI") {
    return (
      <span className="inline-flex items-center whitespace-nowrap rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600">
        Agrupador
      </span>
    );
  }

  if (!blingId) {
    return (
      <span className="inline-flex items-center whitespace-nowrap rounded-full border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700">
        Sem Bling
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        props.onValidarVinculoProdutoBling?.(produto);
      }}
      disabled={loading || !props.onValidarVinculoProdutoBling}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-1 text-xs font-medium ${
        temErro
          ? "border-amber-200 bg-amber-50 text-amber-700"
          : "border-emerald-200 bg-emerald-50 text-emerald-700"
      } hover:brightness-95 disabled:cursor-wait`}
      title={
        temErro
          ? `${produto?.bling_ultimo_erro || "Produto vinculado com erro de sync"}. Clique para conferir no Bling.`
          : "Clique para conferir se este cadastro ainda existe no Bling"
      }
    >
      {temErro ? <AlertTriangle size={13} /> : <CheckCircle2 size={13} />}
      {loading ? "Conferindo..." : `Bling #${blingId}`}
    </button>
  );
}

// ====================================================
// DEFINICAO DE COLUNAS DA LISTAGEM
// ====================================================
export function createProdutosColunas() {
  const colunas = [
    {
      key: "checkbox",
      label: "",
      visible: true,
      renderHeader: (props) => (
        <th className="px-4 py-3 text-left">
          <InputCheckbox
            rotulo="Selecionar todos os produtos"
            checked={
              props.produtos.length > 0 && props.selecionados.length === props.produtos.length
            }
            onChange={props.handleSelecionarTodos}
          />
        </th>
      ),
      renderCell: (produto, props) => {
        if (produto.dados_incompletos_nesta_loja) {
          return <td className="px-4 py-3" />;
        }

        return (
          <td className="px-4 py-3">
            <InputCheckbox
              rotulo={`Selecionar ${produto.nome}`}
              checked={props.selecionados.includes(produto.id)}
              onChange={(e) => props.handleSelecionar(produto.id, e.nativeEvent)}
            />
          </td>
        );
      },
    },
    {
      key: "acoes",
      label: "Ações",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
          Ações
        </th>
      ),
      renderCell: (produto, props) => {
        if (produto.dados_incompletos_nesta_loja) {
          return (
            <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
              <BotaoInteracao
                tamanho="pequeno"
                onClick={() =>
                  props.navigate(
                    `/produtos/novo?pre_cadastro_grupo=${produto.id}&tenant_origem=${produto.tenant_id}`,
                  )
                }
              >
                Completar aqui
              </BotaoInteracao>
            </td>
          );
        }

        const podeGerenciarCatalogo = !produto.de_parceiro || produto.acesso_catalogo_completo;
        const podeLiberarSku =
          produto.ativo === false &&
          !String(produto.codigo || "").startsWith("__LIBERADO__") &&
          podeGerenciarCatalogo;

        const acoes = [
          {
            icon: History,
            label: "Movimentações de estoque",
            onClick: () => props.navigate(`/produtos/${produto.id}/movimentacoes`),
          },
          {
            icon: Pencil,
            label: "Editar",
            onClick: () => props.navigate(`/produtos/${produto.id}/editar`),
          },
          {
            icon: Copy,
            label: "Clonar produto",
            onClick: () => props.navigate(`/produtos/novo?clone=${produto.id}`),
          },
          podeGerenciarCatalogo && {
            icon: produto.ativo === false ? CheckCircle2 : XCircle,
            label: produto.ativo === false ? "Ativar" : "Desativar",
            onClick: () => props.handleToggleAtivo(produto),
            tom: produto.ativo === false ? undefined : "perigo",
          },
          podeLiberarSku && {
            icon: Unlock,
            label: "Liberar SKU",
            title: "Liberar SKU para outro produto",
            onClick: () => props.handleLiberarSku(produto),
          },
        ];

        return (
          <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
            <BotaoMenuAcoes acoes={acoes} rotulo={`Ações de ${produto.nome}`} />
          </td>
        );
      },
    },
    {
      key: "imagem",
      label: "Imagem",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
          Imagem
        </th>
      ),
      renderCell: (produto) => {
        const isVariacao = produto.tipo_produto === "VARIACAO";
        const imagem = obterFontesImagemProduto(produto);
        return (
          <td className={`px-4 py-3 ${isVariacao ? "pl-12" : ""}`}>
            <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden border border-gray-200 flex-shrink-0">
              {imagem.src ? (
                <img
                  src={imagem.src}
                  alt={produto.nome}
                  width="64"
                  height="64"
                  loading="lazy"
                  decoding="async"
                  fetchPriority="low"
                  className="w-full h-full object-cover object-center"
                  onError={(e) => {
                    if (imagem.fallbackSrc && e.currentTarget.src !== imagem.fallbackSrc) {
                      e.currentTarget.src = imagem.fallbackSrc;
                      return;
                    }
                    e.currentTarget.style.display = "none";
                  }}
                />
              ) : (
                <svg
                  className="w-8 h-8 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
              )}
            </div>
          </td>
        );
      },
    },
    {
      key: "descricao",
      label: "Descrição",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
          Descrição
        </th>
      ),
      renderCell: (produto, props) => {
        const isVariacao = produto.tipo_produto === "VARIACAO";
        const isPai = produto.tipo_produto === "PAI";
        const isKit = isProdutoComComposicao(produto);
        const isKitExpandido = isExpandIdSelected(props.kitsExpandidos, produto.id);
        const isPaiExpandido = isExpandIdSelected(props.paisExpandidos, produto.id);

        return (
          <td className="px-4 py-3">
            <div className="flex items-center gap-2">
              <div className={`flex-1 ${isVariacao ? "pl-6" : ""}`}>
                <div className="flex items-center">
                  {isVariacao && (
                    <svg
                      className="w-4 h-4 text-blue-400 mr-1"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  )}
                  {isPai && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        props.togglePaiExpandido(produto.id);
                      }}
                      className="flex items-center text-blue-600 hover:text-blue-700 transition-colors mr-1"
                      title={isPaiExpandido ? "Ocultar variações" : "Ver variações"}
                    >
                      <svg
                        className={`w-4 h-4 transition-transform ${isPaiExpandido ? "rotate-90" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </button>
                  )}
                  {isKit && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        props.toggleKitExpandido(produto.id);
                      }}
                      className={`flex items-center transition-colors mr-1 ${
                        produto.tipo_kit === "VIRTUAL"
                          ? "text-indigo-600 hover:text-indigo-700"
                          : "text-green-600 hover:text-green-700"
                      }`}
                      title={isKitExpandido ? "Ocultar composição" : "Ver composição"}
                    >
                      <svg
                        className={`w-4 h-4 transition-transform ${isKitExpandido ? "rotate-90" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </button>
                  )}
                  <div className="flex flex-wrap items-center gap-x-2 text-sm font-medium text-gray-900">
                    <span>{produto.nome}</span>
                    {isPai && (
                      <span className="whitespace-nowrap text-xs text-blue-600">
                        (Pai {produto.total_variacoes || 0})
                      </span>
                    )}
                    {isKitVirtualProduto(produto) && (
                      <span className="whitespace-nowrap text-xs text-indigo-600">
                        (Kit • Virtual)
                      </span>
                    )}
                    {isKitFisicoProduto(produto) && (
                      <span className="whitespace-nowrap text-xs text-green-600">
                        (Kit • Físico)
                      </span>
                    )}
                    {produto.data_descontinuacao && (
                      <span className="inline-flex items-center whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800">
                        Descontinuado
                      </span>
                    )}
                    {produto.acesso_catalogo_completo ? (
                      <span className="inline-flex items-center whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium bg-violet-100 text-violet-700">
                        Catálogo de {produto.estoque_origem_nome || "empresa do grupo"}
                      </span>
                    ) : produto.de_parceiro ? (
                      <span className="inline-flex items-center whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700">
                        Pet Shop Parceiro
                      </span>
                    ) : null}
                    {produto.dados_incompletos_nesta_loja && (
                      <span
                        className="inline-flex items-center whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-700"
                        title={`Este produto já existe no grupo, mas esta loja ainda não tem os dados dela (preço, estoque etc.) — já cadastrado em ${produto.loja_nome}.`}
                      >
                        Dados incompletos aqui
                      </span>
                    )}
                  </div>
                </div>
                {produto.descricao && (
                  <div className="text-xs text-gray-500 truncate max-w-xs mt-1">
                    {markdownToPlainText(produto.descricao)}
                  </div>
                )}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  props.copiarTexto(produto.nome, "Nome");
                }}
                className="text-gray-400 hover:text-gray-600"
                title="Copiar nome"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </button>
            </div>
          </td>
        );
      },
    },
    {
      key: "codigo",
      label: "Código",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
          Código
        </th>
      ),
      renderCell: (produto, props) => (
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <div>
              <div className="text-sm text-gray-900 font-mono">{produto.codigo || produto.sku}</div>
              {produto.codigo_barras && (
                <div className="text-xs text-gray-500 font-mono">{produto.codigo_barras}</div>
              )}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                props.copiarTexto(produto.codigo || produto.sku, "SKU");
              }}
              className="text-gray-400 hover:text-gray-600"
              title="Copiar SKU"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            </button>
          </div>
        </td>
      ),
    },
    {
      key: "unidade",
      label: "Unidade",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
          Unidade
        </th>
      ),
      renderCell: (produto) => (
        <td className="px-4 py-3 text-center">
          <span className="text-sm text-gray-700">{produto.unidade || "UN"}</span>
        </td>
      ),
    },
    {
      key: "bling",
      label: "Bling",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
          Bling
        </th>
      ),
      renderCell: (produto, props) => {
        if (produto.dados_incompletos_nesta_loja) {
          return (
            <td className="px-4 py-3 text-center">
              <span className="text-sm text-gray-400">-</span>
            </td>
          );
        }

        const blingId = getProdutoBlingId(produto);
        const isPai = produto.tipo_produto === "PAI";
        const loading = props.blingActionKey === getProdutoBlingActionKey(produto.id);
        const podeCriar = !blingId && !isPai && props.onExportarProdutoBling;

        return (
          <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
            <div className="flex flex-col items-center gap-1.5">
              {renderBlingStatusBadge(produto, props)}
              {podeCriar && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    props.onExportarProdutoBling(produto);
                  }}
                  disabled={loading}
                  className={actionButtonClasses({
                    intent: "create",
                    tone: "soft",
                    size: "xs",
                    className: "min-w-20",
                  })}
                  title="Cadastrar este produto no Bling"
                >
                  <UploadCloud size={14} aria-hidden="true" />
                  {loading ? "Criando..." : "Criar"}
                </button>
              )}
            </div>
          </td>
        );
      },
    },
    ...createProdutosPricingColumns(),
    {
      key: "validade",
      label: "Validade",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
          Validade
        </th>
      ),
      renderCell: (produto, props) => (
        <td className="px-4 py-3 text-center text-sm">{props.getValidadeMaisProxima(produto)}</td>
      ),
    },
    {
      key: "estoque",
      label: "Estoque",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
          Estoque
        </th>
      ),
      renderCell: (produto, props) => {
        const isKitVirtual = isKitVirtualProduto(produto);
        const estoqueAtual = obterEstoqueVisualProduto(produto);
        const reservado = produto.estoque_reservado || 0;
        const estoqueDisponivel = estoqueAtual - reservado;
        const estoqueFormatado = parseFloat(estoqueDisponivel.toFixed(2));

        return (
          <td className="px-4 py-3 text-center">
            {produto.controlar_estoque ? (
              <div className="flex flex-col items-center">
                <span className={`text-sm ${props.getCorEstoque(produto)}`}>
                  {estoqueFormatado}
                </span>
                {reservado > 0 && (
                  <span
                    className="text-xs text-yellow-600 mt-0.5"
                    title={`${reservado} unidade(s) reservada(s) em pedidos Bling`}
                  >
                    {reservado} reservado{reservado > 1 ? "s" : ""}
                  </span>
                )}
                {isKitVirtual && (
                  <span className="text-xs text-gray-400 mt-0.5">estoque virtual</span>
                )}
              </div>
            ) : (
              <span className="text-sm text-gray-400">-</span>
            )}
          </td>
        );
      },
    },
    {
      key: "canais",
      label: "Canais",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
          Canais
        </th>
      ),
      renderCell: (produto) => {
        const canaisAtivos = obterCanaisAtivosProduto(produto);

        return (
          <td className="px-4 py-3 text-center">
            <ChannelBadges channels={canaisAtivos} />
          </td>
        );
      },
    },
  ];

  return colunas;
}

export default createProdutosColunas;
