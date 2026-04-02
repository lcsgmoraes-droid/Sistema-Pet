import React from "react";
import { formatarMoeda } from "../../api/produtos";
import {
  isKitFisicoProduto,
  isKitVirtualProduto,
  isProdutoComComposicao,
  obterEstoqueVisualProduto,
} from "./produtosUtils";

// ====================================================
// DEFINICAO DE COLUNAS DA LISTAGEM
// ====================================================
const PRODUTOS_COLUNAS = [
  {
    key: "checkbox",
    label: "",
    visible: true,
    renderHeader: (props) => (
      <th className="px-4 py-3 text-left">
        <input
          type="checkbox"
          checked={
            props.produtos.length > 0 &&
            props.selecionados.length === props.produtos.length
          }
          onChange={props.handleSelecionarTodos}
          className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
        />
      </th>
    ),
    renderCell: (produto, props) => (
      <td className="px-4 py-3">
        <input
          type="checkbox"
          checked={props.selecionados.includes(produto.id)}
          onChange={(e) => props.handleSelecionar(produto.id, e.nativeEvent)}
          className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 cursor-pointer"
        />
      </td>
    ),
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
    renderCell: (produto, props) => {
      const isVariacao = produto.tipo_produto === "VARIACAO";
      return (
        <td className={`px-4 py-3 ${isVariacao ? "pl-12" : ""}`}>
          <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden border border-gray-200 flex-shrink-0">
            {produto.imagem_principal ? (
              <img
                src={
                  produto.imagem_principal.startsWith("http")
                    ? produto.imagem_principal
                    : `${window.location.origin}${produto.imagem_principal}`
                }
                alt={produto.nome}
                className="w-full h-full object-cover object-center"
                onError={(e) => {
                  console.error(
                    "Erro ao carregar imagem:",
                    produto.imagem_principal,
                  );
                  e.target.style.display = "none";
                  e.target.parentElement.innerHTML =
                    '<svg class="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>';
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
    label: "DescriÃ§Ã£o",
    visible: true,
    renderHeader: () => (
      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
        DescriÃ§Ã£o
      </th>
    ),
    renderCell: (produto, props) => {
      const isVariacao = produto.tipo_produto === "VARIACAO";
      const isPai = produto.tipo_produto === "PAI";
      const isKit = isProdutoComComposicao(produto);
      const isKitExpandido = (props.kitsExpandidos || []).includes(produto.id);
      const isPaiExpandido = (props.paisExpandidos || []).includes(produto.id);

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
                    title={
                      isPaiExpandido ? "Ocultar variaÃ§Ãµes" : "Ver variaÃ§Ãµes"
                    }
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
                    title={
                      isKitExpandido ? "Ocultar composiÃ§Ã£o" : "Ver composiÃ§Ã£o"
                    }
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
                <div className="text-sm font-medium text-gray-900">
                  {produto.nome}
                  {isPai && (
                    <span className="ml-2 text-xs text-blue-600">
                      (Pai {produto.total_variacoes || 0})
                    </span>
                  )}
                  {isKitVirtualProduto(produto) && (
                    <span className="ml-2 text-xs text-indigo-600">
                      (Kit â€¢ Virtual)
                    </span>
                  )}
                  {isKitFisicoProduto(produto) && (
                    <span className="ml-2 text-xs text-green-600">
                      (Kit â€¢ FÃ­sico)
                    </span>
                  )}
                  {produto.data_descontinuacao && (
                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                      âš ï¸ Descontinuado
                    </span>
                  )}
                  {produto.de_parceiro && (
                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
                      Pet Shop Parceiro
                    </span>
                  )}
                </div>
              </div>
              {produto.descricao && (
                <div className="text-xs text-gray-500 truncate max-w-xs mt-1">
                  {produto.descricao}
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
    label: "CÃ³digo",
    visible: true,
    renderHeader: () => (
      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
        CÃ³digo
      </th>
    ),
    renderCell: (produto, props) => (
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div>
            <div className="text-sm text-gray-900 font-mono">
              {produto.codigo || produto.sku}
            </div>
            {produto.codigo_barras && (
              <div className="text-xs text-gray-500 font-mono">
                {produto.codigo_barras}
              </div>
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
    key: "custo",
    label: "Custo",
    visible: true,
    renderHeader: () => (
      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
        Custo
      </th>
    ),
    renderCell: (produto, props) => (
      <td className="px-4 py-3 text-right">
        <span className="text-sm text-gray-900">
          {formatarMoeda(produto.preco_custo)}
        </span>
      </td>
    ),
  },
  {
    key: "preco_venda",
    label: "PV",
    visible: true,
    renderHeader: () => (
      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
        PV
      </th>
    ),
    renderCell: (produto, props) => (
      <td className="px-4 py-3 text-right">
        {props.editandoPreco === produto.id ? (
          <div
            className="flex items-center gap-1 justify-end"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="number"
              step="0.01"
              value={props.novoPreco}
              onChange={(e) => props.setNovoPreco(e.target.value)}
              className="w-24 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <button
              onClick={() => props.handleSalvarPreco(produto.id)}
              className="text-green-600 hover:text-green-800"
              title="Salvar"
            >
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
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </button>
            <button
              onClick={props.handleCancelarEdicaoPreco}
              className="text-red-600 hover:text-red-800"
              title="Cancelar"
            >
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
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 justify-end">
            <span className="text-sm font-semibold text-green-600">
              {formatarMoeda(produto.preco_venda)}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                props.handleEditarPreco(produto.id, produto.preco_venda);
              }}
              className="text-blue-600 hover:text-blue-800"
              title="Editar preÃ§o"
            >
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
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </button>
          </div>
        )}
      </td>
    ),
  },
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
      <td className="px-4 py-3 text-center text-sm">
        {props.getValidadeMaisProxima(produto)}
      </td>
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

      return (
        <td className="px-4 py-3 text-center">
          {produto.controlar_estoque ? (
            <div className="flex flex-col items-center">
              <span className={`text-sm ${props.getCorEstoque(produto)}`}>
                {estoqueDisponivel}
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
                <span className="text-xs text-gray-400 mt-0.5">
                  estoque virtual
                </span>
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
    key: "acoes",
    label: "AÃ§Ãµes",
    visible: true,
    renderHeader: () => (
      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
        AÃ§Ãµes
      </th>
    ),
    renderCell: (produto, props) => {
      const estoqueVisual = obterEstoqueVisualProduto(produto);
      let classeMovimentacao =
        "text-gray-500 border-gray-200 bg-gray-50 hover:bg-gray-100";

      if (produto.controlar_estoque === true) {
        if (estoqueVisual > 0) {
          classeMovimentacao =
            "text-green-700 border-green-200 bg-green-50 hover:bg-green-100";
        } else if (estoqueVisual === 0) {
          classeMovimentacao =
            "text-red-700 border-red-200 bg-red-50 hover:bg-red-100";
        }
      }

      return (
      <td
        className="px-4 py-3 text-center"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              console.log(
                "Produto:",
                produto.nome,
                "Controla estoque:",
                produto.controlar_estoque,
                "Estoque atual:",
                estoqueVisual,
              );
              props.navigate(`/produtos/${produto.id}/movimentacoes`);
            }}
            className={`rounded-lg p-1.5 border transition-all duration-200 ${classeMovimentacao}`}
            title="Ver movimentaÃ§Ãµes de estoque"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              props.navigate(`/produtos/${produto.id}/editar`);
            }}
            className="rounded-lg p-1.5 border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-all duration-200"
            title="Editar"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
          </button>
          {!produto.de_parceiro && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              props.handleToggleAtivo(produto);
            }}
            className={`rounded-lg p-1.5 border transition-all duration-200 ${
              produto.ativo === false
                ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                : "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
            }`}
            title={produto.ativo === false ? "Ativar" : "Desativar"}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              {produto.ativo === false ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v4m0 0l-1.5-1.5M12 13l1.5-1.5M5.636 5.636a9 9 0 1012.728 12.728M9.88 9.88a3 3 0 104.24 4.24"
                />
              )}
            </svg>
          </button>
          )}
        </div>
      </td>
      );
    },
  },
];

export default PRODUTOS_COLUNAS;
