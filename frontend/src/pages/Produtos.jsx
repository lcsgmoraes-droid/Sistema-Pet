// ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
// Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
// NÃO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenário real
// 3. Validar impacto financeiro

/**
 * Página de Listagem de Produtos - Estilo Bling
 */
import React, { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { FiHelpCircle } from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import api from "../api";
import {
  deleteProduto,
  formatarData,
  formatarMoeda,
  getCategorias,
  getMarcas,
  getProdutos,
  toggleProdutoAtivo,
} from "../api/produtos";
import ModalImportacaoProdutos from "../components/ModalImportacaoProdutos";
import { useTour } from "../hooks/useTour";
import { tourProdutos } from "../tours/tourDefinitions";

const normalizeSearchText = (value) => {
  if (value === null || value === undefined) return "";
  return String(value)
    .toLowerCase()
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "");
};

const getProdutoSearchRank = (produto, buscaNormalizada) => {
  const termo = normalizeSearchText(buscaNormalizada).trim();
  if (!termo) return 999;

  const codigo = normalizeSearchText(produto.codigo || produto.sku);
  const codigoBarras = normalizeSearchText(produto.codigo_barras);
  const nome = normalizeSearchText(produto.nome);

  const regras = [
    [1, codigo === termo],
    [2, codigoBarras === termo],
    [3, nome === termo],
    [4, codigo?.startsWith(termo)],
    [5, codigoBarras?.startsWith(termo)],
    [6, nome?.startsWith(termo)],
    [7, codigo?.includes(termo)],
    [8, codigoBarras?.includes(termo)],
    [9, nome?.includes(termo)],
  ];

  const match = regras.find(([, condicao]) => Boolean(condicao));
  return match ? Number(match[0]) : 999;
};

const compareProdutosByBusca = (produtoA, produtoB, buscaNormalizada) => {
  const rankA = getProdutoSearchRank(produtoA, buscaNormalizada);
  const rankB = getProdutoSearchRank(produtoB, buscaNormalizada);

  if (rankA !== rankB) {
    return rankA - rankB;
  }

  const codigoA = String(produtoA.codigo || produtoA.sku || "");
  const codigoB = String(produtoB.codigo || produtoB.sku || "");
  const codigoCompare = codigoA.localeCompare(codigoB, "pt-BR", {
    numeric: true,
    sensitivity: "base",
  });

  if (codigoCompare !== 0) {
    return codigoCompare;
  }

  return String(produtoA.nome || "").localeCompare(String(produtoB.nome || ""), "pt-BR", {
    sensitivity: "base",
    numeric: true,
  });
};

// ====================================================
// DEFINIÇÃO DE COLUNAS DA LISTAGEM
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
      const isKit = produto.tipo_produto === "KIT";
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
                      isPaiExpandido ? "Ocultar variações" : "Ver variações"
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
                      isKitExpandido ? "Ocultar composição" : "Ver composição"
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
                  {isKit && produto.tipo_kit === "VIRTUAL" && (
                    <span className="ml-2 text-xs text-indigo-600">
                      (Kit • Virtual)
                    </span>
                  )}
                  {isKit && produto.tipo_kit === "FISICO" && (
                    <span className="ml-2 text-xs text-green-600">
                      (Kit • Físico)
                    </span>
                  )}
                  {produto.data_descontinuacao && (
                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                      ⚠️ Descontinuado
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
              title="Editar preço"
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
      const isKitVirtual =
        produto.tipo_produto === "KIT" && produto.tipo_kit === "VIRTUAL";
      const estoqueAtual = isKitVirtual
        ? (produto.estoque_virtual ?? 0)
        : produto.estoque_atual || 0;
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
    label: "Ações",
    visible: true,
    renderHeader: () => (
      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
        Ações
      </th>
    ),
    renderCell: (produto, props) => {
      let classeMovimentacao =
        "text-gray-500 border-gray-200 bg-gray-50 hover:bg-gray-100";

      if (produto.controlar_estoque === true) {
        if ((produto.estoque_atual || 0) > 0) {
          classeMovimentacao =
            "text-green-700 border-green-200 bg-green-50 hover:bg-green-100";
        } else if ((produto.estoque_atual || 0) === 0) {
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
                produto.estoque_atual,
              );
              props.navigate(`/produtos/${produto.id}/movimentacoes`);
            }}
            className={`rounded-lg p-1.5 border transition-all duration-200 ${classeMovimentacao}`}
            title="Ver movimentações de estoque"
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

export default function Produtos() {
  const navigate = useNavigate();
  const { iniciarTour } = useTour("produtos", tourProdutos);
  const [persistirBusca, setPersistirBusca] = useState(() => {
    const salvo = localStorage.getItem("produtos_persistir_busca");
    return salvo === null ? true : salvo === "true";
  });
  const [produtosBrutos, setProdutosBrutos] = useState([]); // Dados originais da API
  const [categorias, setCategorias] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [fornecedores, setFornecedores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selecionados, setSelecionados] = useState([]);
  const [ultimoSelecionado, setUltimoSelecionado] = useState(null);
  const [editandoPreco, setEditandoPreco] = useState(null);
  const [novoPreco, setNovoPreco] = useState("");

  // Estado para KITs expandidos
  const [kitsExpandidos, setKitsExpandidos] = useState([]);

  // Estado para PAIs expandidos (mostrar variações)
  const [paisExpandidos, setPaisExpandidos] = useState([]);

  // Estado de colunas visíveis (localStorage)
  const [colunasVisiveis, setColunasVisiveis] = useState(() => {
    const salvo = localStorage.getItem("produtos_colunas_visiveis");
    return salvo ? JSON.parse(salvo) : null;
  });

  // Modal de configuração de colunas
  const [modalColunas, setModalColunas] = useState(false);
  const [colunasTemporarias, setColunasTemporarias] = useState([]);

  // Modal de edição em lote
  const [modalEdicaoLote, setModalEdicaoLote] = useState(false);
  const [dadosEdicaoLote, setDadosEdicaoLote] = useState({
    marca_id: "",
    categoria_id: "",
    departamento_id: "",
  });
  const [departamentos, setDepartamentos] = useState([]);

  // Modal de importação
  const [modalImportacao, setModalImportacao] = useState(false);

  // Filtros
  const [filtros, setFiltros] = useState({
    busca: (() => {
      if (!persistirBusca) return "";
      return localStorage.getItem("produtos_filtro_busca") || "";
    })(),
    ativo: "ativos",
    categoria_id: "",
    marca_id: "",
    fornecedor_id: "",
    estoque_baixo: false,
    em_promocao: false,
  });

  // Paginação
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [itensPorPagina, setItensPorPagina] = useState(20);

  // ========================================
  // ORGANIZAR PRODUTOS HIERARQUICAMENTE (useMemo para performance)
  // ========================================
  // Reorganiza produtos sempre que produtosBrutos ou paisExpandidos mudar
  // SEM fazer nova requisição à API (evita scroll ao topo)
  const produtosOrganizados = useMemo(() => {
    if (!produtosBrutos || produtosBrutos.length === 0) return [];

    const resultado = [];
    const variacoes = produtosBrutos.filter((p) => p.tipo_produto === "VARIACAO");

    // Manter ordem de entrada do backend (created_at desc).
    // VARIACAOs só aparecem logo abaixo do seu PAI quando expandido.
    produtosBrutos.forEach((produto) => {
      if (produto.tipo_produto === "VARIACAO") return; // pulado aqui, entra via PAI

      resultado.push(produto);

      if (produto.tipo_produto === "PAI" && paisExpandidos.includes(produto.id)) {
        const variacoesDoPai = variacoes.filter(
          (v) => v.produto_pai_id === produto.id,
        );
        resultado.push(...variacoesDoPai);
      }
    });

    return resultado;
  }, [produtosBrutos, paisExpandidos]);

  // ========================================
  // APLICAR FILTROS (useMemo para performance)
  // ========================================
  // Aplica filtros de busca, categoria, marca, estoque e promoção
  const produtosFiltrados = useMemo(() => {
    const buscaNormalizada = normalizeSearchText(filtros.busca).trim();
    let produtosTemp = buscaNormalizada
      ? [...produtosBrutos]
      : [...produtosOrganizados];

    // Filtro de busca inteligente (multi-termo + sem acento)
    if (buscaNormalizada) {
      const termos = buscaNormalizada
        .split(/\s+/)
        .filter(Boolean);

      produtosTemp = produtosTemp.filter(
        (p) => {
          const searchableText = normalizeSearchText(
            [
              p.nome,
              p.codigo,
              p.codigo_barras,
              p.sku,
              p.referencia,
              p.referencia_sku,
            ]
              .filter(Boolean)
              .join(" "),
          );

          return termos.every((termo) => searchableText.includes(termo));
        },
      );

      produtosTemp.sort((produtoA, produtoB) =>
        compareProdutosByBusca(produtoA, produtoB, buscaNormalizada),
      );
    }

    // Filtro de categoria
    if (filtros.categoria_id) {
      produtosTemp = produtosTemp.filter(
        (p) => p.categoria_id == filtros.categoria_id,
      );
    }

    // Filtro de marca
    if (filtros.marca_id) {
      produtosTemp = produtosTemp.filter((p) => p.marca_id == filtros.marca_id);
    }

    // Filtro de estoque baixo
    if (filtros.estoque_baixo) {
      produtosTemp = produtosTemp.filter((p) => {
        const estoque =
          p.tipo_produto === "KIT" && p.tipo_kit === "VIRTUAL"
            ? (p.estoque_virtual ?? 0)
            : p.estoque_atual || 0;
        const minimo = p.estoque_minimo || 0;
        return p.controlar_estoque && estoque <= minimo;
      });
    }

    // Filtro de em promoção
    if (filtros.em_promocao) {
      produtosTemp = produtosTemp.filter((p) => p.promocao_ativa === true);
    }

    return produtosTemp;
  }, [produtosBrutos, produtosOrganizados, filtros]);

  // Calcular produtos paginados
  const { produtosPaginados, totalPaginas, totalItens } = useMemo(() => {
    const total = Math.ceil(produtosFiltrados.length / itensPorPagina);
    const inicio = (paginaAtual - 1) * itensPorPagina;
    const fim = inicio + itensPorPagina;
    const paginados = produtosFiltrados.slice(inicio, fim);

    return {
      produtosPaginados: paginados,
      totalPaginas: total,
      totalItens: produtosFiltrados.length,
    };
  }, [produtosFiltrados, paginaAtual, itensPorPagina]);

  // Alias para manter compatibilidade com o resto do código
  const produtos = produtosPaginados;

  // Resetar para página 1 quando filtros mudarem
  useEffect(() => {
    setPaginaAtual(1);
  }, [filtros]);

  // Carregar dados iniciais
  useEffect(() => {
    carregarDados();
    carregarCategorias();
    carregarMarcas();
    carregarFornecedores();
    carregarDepartamentos();
  }, []);

  // Persistência opcional da busca para que cada usuário escolha seu comportamento.
  useEffect(() => {
    localStorage.setItem("produtos_persistir_busca", String(persistirBusca));

    if (persistirBusca) {
      localStorage.setItem("produtos_filtro_busca", filtros.busca || "");
      return;
    }

    localStorage.removeItem("produtos_filtro_busca");
  }, [persistirBusca, filtros.busca]);

  const carregarDados = async (filtrosAtuais = filtros) => {
    try {
      setLoading(true);
      // Remover campos vazios dos filtros
      const filtrosLimpos = {};
      Object.keys(filtrosAtuais).forEach((key) => {
        const valor = filtrosAtuais[key];

        if (key === "ativo") {
          if (valor === "ativos") {
            filtrosLimpos[key] = true;
          } else if (valor === "inativos") {
            filtrosLimpos[key] = false;
          }
          return;
        }

        // Só incluir se não for string vazia
        if (valor !== "" && valor !== null && valor !== undefined) {
          filtrosLimpos[key] = valor;
        }
      });
      const response = await getProdutos(filtrosLimpos);

      // API retorna { itens: [], total: 0, pagina: 1, ... } ou apenas array
      let produtosData;
      if (Array.isArray(response.data)) {
        produtosData = response.data;
      } else if (response.data.itens) {
        produtosData = response.data.itens;
      } else if (response.data.produtos) {
        produtosData = response.data.produtos;
      } else if (response.data.data) {
        produtosData = response.data.data;
      } else {
        // Procurar por qualquer propriedade que seja um array
        const arrayKeys = Object.keys(response.data).filter((key) =>
          Array.isArray(response.data[key]),
        );
        if (arrayKeys.length > 0) {
          produtosData = response.data[arrayKeys[0]];
        } else {
          produtosData = [];
        }
      }

      // ========================================
      // 🔒 SPRINT 2 - SALVAR DADOS BRUTOS (SEM ORGANIZAR)
      // ========================================
      // Salvar dados originais sem hierarquia
      // A organização será feita no useMemo abaixo
      setProdutosBrutos(produtosData);
    } catch (error) {
      console.error("Erro ao carregar produtos:", error);
      alert("Erro ao carregar produtos");
    } finally {
      setLoading(false);
    }
  };

  const carregarCategorias = async () => {
    try {
      const response = await getCategorias();
      setCategorias(response.data);
    } catch (error) {
      console.error("Erro ao carregar categorias:", error);
    }
  };

  const carregarMarcas = async () => {
    try {
      const response = await getMarcas();
      setMarcas(response.data);
    } catch (error) {
      console.error("Erro ao carregar marcas:", error);
    }
  };

  const carregarFornecedores = async () => {
    try {
      const response = await api.get(
        "/clientes/?tipo_cadastro=fornecedor&apenas_ativos=true",
      );
      const dados = response.data;
      const lista = Array.isArray(dados)
        ? dados
        : dados.items || dados.clientes || dados.data || [];
      setFornecedores(lista);
    } catch (error) {
      console.error("Erro ao carregar fornecedores:", error);
    }
  };

  const carregarDepartamentos = async () => {
    try {
      const response = await api.get("/produtos/departamentos");
      setDepartamentos(response.data);
    } catch (error) {
      console.error("Erro ao carregar departamentos:", error);
      // Não é erro crítico, apenas não mostra departamentos
    }
  };

  const handleFiltroChange = (campo, valor) => {
    const proximoFiltro = { ...filtros, [campo]: valor };
    setFiltros(proximoFiltro);

    // Fornecedor filtra no backend (relacionamento N:N via produto_fornecedores)
    if (campo === "fornecedor_id" || campo === "ativo") {
      carregarDados(proximoFiltro);
    }
  };

  const handleToggleAtivo = async (produto) => {
    const proximoAtivo = produto.ativo === false;
    const acao = proximoAtivo ? "ativar" : "desativar";

    if (!confirm(`Deseja realmente ${acao} o produto "${produto.nome}"?`)) {
      return;
    }

    try {
      await toggleProdutoAtivo(produto.id, proximoAtivo);
      toast.success(`Produto ${proximoAtivo ? "ativado" : "desativado"} com sucesso!`);
      carregarDados();
    } catch (error) {
      console.error(`Erro ao ${acao} produto:`, error);
      alert(`Erro ao ${acao} produto`);
    }
  };

  const handleSelecionar = (id, event) => {
    if (!id) {
      console.error("Erro: ID do produto é undefined ou null");
      return;
    }

    // Se for Shift+click e houver um último selecionado, selecionar intervalo
    if (event?.shiftKey && ultimoSelecionado !== null) {
      const indexUltimo = produtos.findIndex((p) => p.id === ultimoSelecionado);
      const indexAtual = produtos.findIndex((p) => p.id === id);

      if (indexUltimo !== -1 && indexAtual !== -1) {
        const inicio = Math.min(indexUltimo, indexAtual);
        const fim = Math.max(indexUltimo, indexAtual);
        const intervalo = produtos.slice(inicio, fim + 1).map((p) => p.id);

        // Adicionar todos do intervalo aos já selecionados
        setSelecionados((prev) => {
          const novo = new Set(prev);
          intervalo.forEach((prodId) => novo.add(prodId));
          return Array.from(novo);
        });
        setUltimoSelecionado(id);
        return;
      }
    }

    // Seleção normal
    setSelecionados((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
    setUltimoSelecionado(id);
  };

  const handleSelecionarTodos = () => {
    if (selecionados.length === produtos.length) {
      setSelecionados([]);
    } else {
      setSelecionados(produtos.map((p) => p.id));
    }
  };

  const handleExcluir = async (id) => {
    if (!confirm("Deseja realmente excluir este produto?")) return;

    try {
      await deleteProduto(id);
      alert("Produto excluído com sucesso!");
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir produto:", error);
      alert("Erro ao excluir produto");
    }
  };

  const handleExcluirSelecionados = async () => {
    if (!confirm(`Deseja realmente excluir ${selecionados.length} produtos?`))
      return;

    try {
      await Promise.all(selecionados.map((id) => deleteProduto(id)));
      alert("Produtos excluídos com sucesso!");
      setSelecionados([]);
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir produtos:", error);
      alert("Erro ao excluir produtos");
    }
  };

  const copiarTexto = (texto, tipo) => {
    navigator.clipboard.writeText(texto);
    toast.success(`${tipo} copiado!`);
  };

  const handleEditarPreco = (produtoId, precoAtual) => {
    setEditandoPreco(produtoId);
    setNovoPreco(precoAtual.toString());
  };

  const handleSalvarPreco = async (produtoId) => {
    try {
      await api.patch(`/produtos/${produtoId}?preco_venda=${novoPreco}`, {});
      toast.success("Preço atualizado!");
      setEditandoPreco(null);
      carregarDados();
    } catch (error) {
      console.error("Erro ao atualizar preço:", error);
      toast.error("Erro ao atualizar preço");
    }
  };

  const handleCancelarEdicaoPreco = () => {
    setEditandoPreco(null);
  };

  const handleAbrirEdicaoLote = () => {
    if (selecionados.length === 0) {
      toast.error("Selecione pelo menos um produto");
      return;
    }
    setDadosEdicaoLote({
      marca_id: "",
      categoria_id: "",
      departamento_id: "",
    });
    setModalEdicaoLote(true);
  };

  const handleSalvarEdicaoLote = async () => {
    try {
      // Validar se pelo menos um campo foi preenchido
      const camposPreenchidos = Object.values(dadosEdicaoLote).filter(
        (v) => v !== "",
      );
      if (camposPreenchidos.length === 0) {
        toast.error("Preencha pelo menos um campo para atualizar");
        return;
      }

      // Enviar apenas campos preenchidos
      const dadosEnvio = {};
      if (dadosEdicaoLote.marca_id)
        dadosEnvio.marca_id = parseInt(dadosEdicaoLote.marca_id);
      if (dadosEdicaoLote.categoria_id)
        dadosEnvio.categoria_id = parseInt(dadosEdicaoLote.categoria_id);
      if (dadosEdicaoLote.departamento_id)
        dadosEnvio.departamento_id = parseInt(dadosEdicaoLote.departamento_id);

      await api.patch("/produtos/atualizar-lote", {
        produto_ids: selecionados,
        ...dadosEnvio,
      });

      toast.success(
        `${selecionados.length} produto(s) atualizado(s) com sucesso!`,
      );
      setModalEdicaoLote(false);
      setSelecionados([]);
      carregarDados();
    } catch (error) {
      console.error("Erro ao atualizar produtos:", error);
      toast.error("Erro ao atualizar produtos");
    }
  };

  // Determinar cor do estoque
  const getCorEstoque = (produto) => {
    if (!produto.controlar_estoque) return "text-gray-500";

    // KIT virtual usa estoque_virtual, outros usam estoque_atual
    const estoque =
      produto.tipo_produto === "KIT" && produto.tipo_kit === "VIRTUAL"
        ? (produto.estoque_virtual ?? 0)
        : produto.estoque_atual || 0;
    const minimo = produto.estoque_minimo || 0;

    // Estoque zerado
    if (estoque <= 0) return "text-red-600 font-semibold";

    // Estoque baixo
    if (estoque <= minimo) return "text-yellow-600 font-medium";

    // Estoque normal
    return "text-gray-700";
  };

  // Obter validade mais próxima dos lotes
  const getValidadeMaisProxima = (produto) => {
    if (!produto.lotes || produto.lotes.length === 0) return "-";

    const lotes = produto.lotes
      .filter((l) => l.data_validade)
      .sort((a, b) => new Date(a.data_validade) - new Date(b.data_validade));

    if (lotes.length === 0) return "-";

    const proximaValidade = lotes[0].data_validade;
    const dias = Math.floor(
      (new Date(proximaValidade) - new Date()) / (1000 * 60 * 60 * 24),
    );

    let cor = "text-gray-700";
    if (dias < 0)
      cor = "text-red-600 font-bold"; // Vencido
    else if (dias <= 30)
      cor = "text-orange-600 font-semibold"; // Próximo do vencimento
    else if (dias <= 90) cor = "text-yellow-600"; // Atenção

    return <span className={cor}>{formatarData(proximaValidade)}</span>;
  };

  // Expandir/colapsar KIT
  const toggleKitExpandido = (produtoId) => {
    setKitsExpandidos((prev) =>
      prev.includes(produtoId)
        ? prev.filter((id) => id !== produtoId)
        : [...prev, produtoId],
    );
  };

  // Expandir/colapsar PAI (mostrar variações)
  const togglePaiExpandido = (produtoId) => {
    setPaisExpandidos((prev) =>
      prev.includes(produtoId)
        ? prev.filter((id) => id !== produtoId)
        : [...prev, produtoId],
    );
  };

  const abrirModalColunas = () => {
    const keys = colunasVisiveis || PRODUTOS_COLUNAS.map((c) => c.key);
    setColunasTemporarias(keys);
    setModalColunas(true);
  };

  const toggleColuna = (key) => {
    setColunasTemporarias((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  };

  const salvarColunas = () => {
    localStorage.setItem(
      "produtos_colunas_visiveis",
      JSON.stringify(colunasTemporarias),
    );
    setColunasVisiveis(colunasTemporarias);
    setModalColunas(false);
    toast.success("Preferências de colunas salvas!");
  };

  const restaurarColunasPadrao = () => {
    localStorage.removeItem("produtos_colunas_visiveis");
    setColunasVisiveis(null);
    setColunasTemporarias(PRODUTOS_COLUNAS.map((c) => c.key));
    toast.success("Colunas restauradas para o padrão!");
  };

  const filtrarColunas = (coluna) => {
    if (!colunasVisiveis) return true;
    return colunasVisiveis.includes(coluna.key);
  };

  return (
    <div className="p-6">
      {/* Cabeçalho */}
      <div className="mb-6 flex justify-between items-start">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Produtos</h1>
            <p className="text-gray-600 mt-1">
              Gerencie seu estoque de produtos
            </p>
          </div>
          <button
            onClick={iniciarTour}
            title="Ver tour guiado desta página"
            className="flex items-center gap-1 px-2 py-1 text-sm text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors mt-1"
          >
            <FiHelpCircle className="text-base" />
            <span className="hidden sm:inline text-xs">Tour</span>
          </button>
        </div>
        <div className="flex gap-2">
          {selecionados.length > 0 && (
            <>
              <button
                onClick={handleAbrirEdicaoLote}
                className="px-4 py-2 text-white rounded-xl bg-emerald-600 hover:bg-emerald-700 shadow-sm hover:shadow-md transition-all duration-200 border border-emerald-500"
              >
                ✏️ Editar em Lote ({selecionados.length})
              </button>
              <button
                onClick={handleExcluirSelecionados}
                className="px-4 py-2 text-white rounded-xl bg-red-600 hover:bg-red-700 shadow-sm hover:shadow-md transition-all duration-200 border border-red-500"
              >
                Excluir Selecionados ({selecionados.length})
              </button>
            </>
          )}
          <button
            id="tour-produtos-importar"
            onClick={() => setModalImportacao(true)}
            className="px-4 py-2 text-white rounded-xl bg-sky-600 hover:bg-sky-700 shadow-sm hover:shadow-md transition-all duration-200 border border-sky-500 font-medium flex items-center gap-2"
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
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            Importar Excel
          </button>
          <button
            onClick={abrirModalColunas}
            className="px-4 py-2 text-slate-700 rounded-xl bg-white hover:bg-slate-50 shadow-sm hover:shadow-md transition-all duration-200 border border-slate-300 font-medium flex items-center gap-2"
            title="Configurar colunas visíveis"
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
          <button
            id="tour-produtos-novo"
            onClick={() => navigate("/produtos/novo")}
            className="px-4 py-2 text-white rounded-xl bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow-md transition-all duration-200 border border-blue-500 font-medium"
          >
            + Novo Produto
          </button>
        </div>
      </div>

      {/* Filtros */}
      <div
        id="tour-produtos-filtros"
        className="bg-white rounded-lg shadow-sm p-4 mb-6"
      >
        <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
          {/* Busca Geral */}
          <div id="tour-produtos-busca" className="md:col-span-2">
            <input
              type="text"
              placeholder="Buscar por código, nome ou código de barras..."
              value={filtros.busca}
              onChange={(e) => handleFiltroChange("busca", e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Categoria */}
          <div>
            <select
              value={filtros.categoria_id}
              onChange={(e) =>
                handleFiltroChange("categoria_id", e.target.value)
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todas as Categorias</option>
              {categorias.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.categoria_pai_id ? "  └─ " : ""}
                  {cat.nome}
                </option>
              ))}
            </select>
          </div>

          {/* Marca */}
          <div>
            <select
              value={filtros.marca_id}
              onChange={(e) => handleFiltroChange("marca_id", e.target.value)}
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

          {/* Fornecedor */}
          <div>
            <select
              value={filtros.fornecedor_id}
              onChange={(e) =>
                handleFiltroChange("fornecedor_id", e.target.value)
              }
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
              onChange={(e) => handleFiltroChange("ativo", e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="ativos">Somente Ativos</option>
              <option value="inativos">Somente Inativos</option>
              <option value="todos">Ativos e Inativos</option>
            </select>
          </div>

          {/* Toggles */}
          <div className="flex gap-4 items-center flex-wrap md:col-span-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filtros.estoque_baixo}
                onChange={(e) =>
                  handleFiltroChange("estoque_baixo", e.target.checked)
                }
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Estoque Baixo</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filtros.em_promocao}
                onChange={(e) =>
                  handleFiltroChange("em_promocao", e.target.checked)
                }
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Em Promoção</span>
            </label>

            <label
              className="flex items-center gap-2 cursor-pointer px-2 py-1 rounded-md border border-gray-200 bg-gray-50"
              title="Quando ligado, a busca fica salva ao sair e voltar para a lista"
            >
              <input
                type="checkbox"
                checked={persistirBusca}
                onChange={(e) => setPersistirBusca(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-xs text-gray-700">Persistir pesquisa</span>
            </label>
          </div>
        </div>
      </div>

      {/* Paginação Superior */}
      {!loading && totalItens > 0 && (
        <div className="px-4 py-3 bg-gray-50 border border-gray-200 rounded-t-lg flex items-center justify-between mt-6 mb-0">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              Mostrando {(paginaAtual - 1) * itensPorPagina + 1} a{" "}
              {Math.min(paginaAtual * itensPorPagina, totalItens)} de{" "}
              {totalItens} produtos
            </span>
            <select
              value={itensPorPagina}
              onChange={(e) => {
                setItensPorPagina(Number(e.target.value));
                setPaginaAtual(1);
              }}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value={10}>10 por página</option>
              <option value={20}>20 por página</option>
              <option value={30}>30 por página</option>
              <option value={50}>50 por página</option>
              <option value={100}>100 por página</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPaginaAtual(1)}
              disabled={paginaAtual === 1}
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Primeira
            </button>
            <button
              onClick={() => setPaginaAtual((prev) => Math.max(prev - 1, 1))}
              disabled={paginaAtual === 1}
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Anterior
            </button>

            {/* Páginas numeradas */}
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(totalPaginas, 5) }, (_, i) => {
                let pageNum;
                if (totalPaginas <= 5) {
                  pageNum = i + 1;
                } else if (paginaAtual <= 3) {
                  pageNum = i + 1;
                } else if (paginaAtual >= totalPaginas - 2) {
                  pageNum = totalPaginas - 4 + i;
                } else {
                  pageNum = paginaAtual - 2 + i;
                }

                return (
                  <button
                    key={pageNum}
                    onClick={() => setPaginaAtual(pageNum)}
                    className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                      paginaAtual === pageNum
                        ? "bg-blue-600 text-white"
                        : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() =>
                setPaginaAtual((prev) => Math.min(prev + 1, totalPaginas))
              }
              disabled={paginaAtual === totalPaginas}
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Próxima
            </button>
            <button
              onClick={() => setPaginaAtual(totalPaginas)}
              disabled={paginaAtual === totalPaginas}
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Última
            </button>
          </div>
        </div>
      )}

      {/* Tabela */}
      <div
        id="tour-produtos-lista"
        className="bg-white rounded-lg shadow-sm overflow-hidden"
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {PRODUTOS_COLUNAS.filter(filtrarColunas).map((coluna) => (
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
                  <td
                    colSpan="10"
                    className="px-4 py-8 text-center text-gray-500"
                  >
                    Carregando produtos...
                  </td>
                </tr>
              ) : produtos.length === 0 ? (
                <tr>
                  <td
                    colSpan="10"
                    className="px-4 py-8 text-center text-gray-500"
                  >
                    Nenhum produto encontrado
                  </td>
                </tr>
              ) : (
                produtos.map((produto, idx) => {
                  if (!produto || !produto.id) {
                    console.error(
                      `Produto inválido no índice ${idx}:`,
                      produto,
                    );
                    return null;
                  }

                  const isKit = produto.tipo_produto === "KIT";
                  const isKitExpandido = kitsExpandidos.includes(produto.id);

                  return (
                    <React.Fragment key={produto.id}>
                      <tr
                        className={`hover:bg-gray-50 transition-colors cursor-pointer ${
                          produto.ativo === false
                            ? "bg-slate-100 opacity-70"
                            : ""
                        } ${
                          produto.tipo_produto === "VARIACAO"
                            ? "bg-blue-50/30"
                            : ""
                        } ${isKit ? "bg-amber-50/30" : ""}`}
                        onClick={(e) => {
                          if (!e.target.closest("button, input, a, svg")) {
                            navigate(`/produtos/${produto.id}/editar`);
                          }
                        }}
                      >
                        {PRODUTOS_COLUNAS.filter(filtrarColunas).map(
                          (coluna) => (
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
                          ),
                        )}
                      </tr>

                      {/* Linha expansível com composição do KIT */}
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
                                  COMPOSIÇÃO DO KIT:
                                </div>
                                <div className="grid gap-1">
                                  {produto.composicao_kit.map(
                                    (componente, idx) => (
                                      <div
                                        key={idx}
                                        className="flex items-center gap-3 text-xs bg-white rounded px-3 py-2 border border-amber-200"
                                      >
                                        <span className="font-mono font-semibold text-amber-700 min-w-[40px]">
                                          {componente.quantidade}x
                                        </span>
                                        <span className="flex-1 text-gray-700">
                                          {componente.produto_nome ||
                                            componente.nome ||
                                            `Produto #${componente.produto_id || componente.produto_componente_id}`}
                                        </span>
                                        {componente.produto_estoque !==
                                          undefined && (
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
                                    ),
                                  )}
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

        {/* Paginação Inferior */}
        {!loading && totalItens > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">
                Mostrando {(paginaAtual - 1) * itensPorPagina + 1} a{" "}
                {Math.min(paginaAtual * itensPorPagina, totalItens)} de{" "}
                {totalItens} produtos
              </span>
              <select
                value={itensPorPagina}
                onChange={(e) => {
                  setItensPorPagina(Number(e.target.value));
                  setPaginaAtual(1);
                }}
                className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value={10}>10 por página</option>
                <option value={20}>20 por página</option>
                <option value={30}>30 por página</option>
                <option value={50}>50 por página</option>
                <option value={100}>100 por página</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPaginaAtual(1)}
                disabled={paginaAtual === 1}
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Primeira
              </button>
              <button
                onClick={() => setPaginaAtual((prev) => Math.max(prev - 1, 1))}
                disabled={paginaAtual === 1}
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Anterior
              </button>

              {/* Páginas numeradas */}
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(totalPaginas, 5) }, (_, i) => {
                  let pageNum;
                  if (totalPaginas <= 5) {
                    pageNum = i + 1;
                  } else if (paginaAtual <= 3) {
                    pageNum = i + 1;
                  } else if (paginaAtual >= totalPaginas - 2) {
                    pageNum = totalPaginas - 4 + i;
                  } else {
                    pageNum = paginaAtual - 2 + i;
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPaginaAtual(pageNum)}
                      className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                        paginaAtual === pageNum
                          ? "bg-blue-600 text-white"
                          : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() =>
                  setPaginaAtual((prev) => Math.min(prev + 1, totalPaginas))
                }
                disabled={paginaAtual === totalPaginas}
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Próxima
              </button>
              <button
                onClick={() => setPaginaAtual(totalPaginas)}
                disabled={paginaAtual === totalPaginas}
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Última
              </button>
            </div>
          </div>
        )}

        {/* Footer - Informações de seleção */}
        {!loading && selecionados.length > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
            <div className="flex justify-between items-center text-sm text-gray-600">
              <span>
                {selecionados.length} produto
                {selecionados.length > 1 ? "s" : ""} selecionado
                {selecionados.length > 1 ? "s" : ""}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Modal de Edição em Lote */}
      {modalEdicaoLote && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">
                Editar em Lote
              </h2>
              <button
                onClick={() => setModalEdicaoLote(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg
                  className="w-6 h-6"
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

            <p className="text-sm text-gray-600 mb-4">
              Atualizar <strong>{selecionados.length}</strong> produto(s)
              selecionado(s)
            </p>

            <div className="space-y-4">
              {/* Marca */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Marca
                </label>
                <select
                  value={dadosEdicaoLote.marca_id}
                  onChange={(e) =>
                    setDadosEdicaoLote({
                      ...dadosEdicaoLote,
                      marca_id: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Não alterar</option>
                  {marcas.map((marca) => (
                    <option key={marca.id} value={marca.id}>
                      {marca.nome}
                    </option>
                  ))}
                </select>
              </div>

              {/* Categoria */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Categoria
                </label>
                <select
                  value={dadosEdicaoLote.categoria_id}
                  onChange={(e) =>
                    setDadosEdicaoLote({
                      ...dadosEdicaoLote,
                      categoria_id: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Não alterar</option>
                  {categorias.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.categoria_pai_id ? "  └─ " : ""}
                      {cat.nome}
                    </option>
                  ))}
                </select>
              </div>

              {/* Departamento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Departamento
                </label>
                <select
                  value={dadosEdicaoLote.departamento_id}
                  onChange={(e) =>
                    setDadosEdicaoLote({
                      ...dadosEdicaoLote,
                      departamento_id: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Não alterar</option>
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
                onClick={() => setModalEdicaoLote(false)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleSalvarEdicaoLote}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Salvar Alterações
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Configuração de Colunas */}
      {modalColunas && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Configurar Colunas
              </h3>
              <button
                onClick={() => setModalColunas(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg
                  className="w-6 h-6"
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

            {/* Body */}
            <div className="px-6 py-4 max-h-96 overflow-y-auto">
              <p className="text-sm text-gray-600 mb-4">
                Selecione quais colunas deseja visualizar na tabela:
              </p>

              <div className="space-y-2">
                {PRODUTOS_COLUNAS.map((coluna) => (
                  <label
                    key={coluna.key}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={colunasTemporarias.includes(coluna.key)}
                      onChange={() => toggleColuna(coluna.key)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      {coluna.label || coluna.key}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex justify-between gap-3">
              <button
                onClick={restaurarColunasPadrao}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Restaurar Padrão
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => setModalColunas(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={salvarColunas}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Salvar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Importação */}
      <ModalImportacaoProdutos
        isOpen={modalImportacao}
        onClose={() => setModalImportacao(false)}
        onSuccess={() => {
          carregarDados();
          setModalImportacao(false);
        }}
      />
    </div>
  );
}
