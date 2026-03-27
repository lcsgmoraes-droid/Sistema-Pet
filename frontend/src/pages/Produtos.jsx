// ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
// Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
// NÃO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenário real
// 3. Validar impacto financeiro

/**
 * Página de Listagem de Produtos - Estilo Bling
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
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
  getProdutoVariacoes,
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

const corrigirTextoQuebrado = (value) => {
  if (value === null || value === undefined) return "";

  const textoOriginal = String(value);
  const scoreQuebrado = (texto) => (texto.match(/[ÃÂâ�]/g) || []).length;

  const tentarTextDecoderUtf8 = (texto) => {
    try {
      const bytes = Uint8Array.from(
        texto,
        (char) => (char.codePointAt(0) ?? 0) & 0xff,
      );
      return new TextDecoder("utf-8").decode(bytes);
    } catch {
      return texto;
    }
  };

  const candidatos = [
    textoOriginal,
    tentarTextDecoderUtf8(textoOriginal),
    tentarTextDecoderUtf8(tentarTextDecoderUtf8(textoOriginal)),
  ];

  let melhor = candidatos[0];
  let melhorScore = scoreQuebrado(melhor);

  for (const candidato of candidatos) {
    const score = scoreQuebrado(candidato);
    if (score < melhorScore) {
      melhor = candidato;
      melhorScore = score;
    }
  }

  return melhor
    .replaceAll("âŒ", "❌")
    .replaceAll("Ã§", "ç")
    .replaceAll("Ã£", "ã")
    .replaceAll("Ãµ", "õ")
    .replaceAll("Ã¡", "á")
    .replaceAll("Ã©", "é")
    .replaceAll("Ãª", "ê")
    .replaceAll("Ã­", "í")
    .replaceAll("Ã³", "ó")
    .replaceAll("Ãº", "ú")
    .replaceAll("â€“", "-")
    .replaceAll("Â", "");
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

const COLUNAS_RELATORIO_PRODUTOS = [
  { key: "nome", label: "Nome", value: (p) => p.nome || "" },
  { key: "codigo", label: "Codigo", value: (p) => p.codigo || p.sku || "" },
  { key: "codigo_barras", label: "Codigo de Barras", value: (p) => p.codigo_barras || "" },
  {
    key: "categoria",
    label: "Categoria",
    value: (p) => p.categoria_nome || p.categoria?.nome || "",
  },
  {
    key: "marca",
    label: "Marca",
    value: (p) => p.marca_nome || p.marca?.nome || "",
  },
  {
    key: "fornecedor",
    label: "Fornecedor",
    value: (p) => p.fornecedor_nome || p.fornecedor?.nome || "",
  },
  { key: "unidade", label: "Unidade", value: (p) => p.unidade || "UN" },
  {
    key: "estoque",
    label: "Estoque",
    value: (p) => Number(p.estoque_atual ?? p.estoque ?? 0),
  },
  {
    key: "estoque_minimo",
    label: "Estoque Minimo",
    value: (p) => Number(p.estoque_minimo ?? 0),
  },
  {
    key: "preco_custo",
    label: "Preco Custo",
    value: (p) => Number(p.preco_custo ?? 0),
  },
  {
    key: "preco_venda",
    label: "Preco Venda",
    value: (p) => Number(p.preco_venda ?? 0),
  },
  {
    key: "margem",
    label: "Margem %",
    value: (p) => {
      const pv = Number(p.preco_venda ?? 0);
      const pc = Number(p.preco_custo ?? 0);
      if (!pv) return 0;
      return Number((((pv - pc) / pv) * 100).toFixed(2));
    },
  },
  {
    key: "ativo",
    label: "Ativo",
    value: (p) => (p.ativo === false ? "Nao" : "Sim"),
  },
  {
    key: "tipo_produto",
    label: "Tipo",
    value: (p) => p.tipo_produto || "SIMPLES",
  },
  {
    key: "atualizado_em",
    label: "Atualizado em",
    value: (p) => p.updated_at || p.data_atualizacao || p.created_at || "",
  },
];

export default function Produtos() {
  const navigate = useNavigate();
  const { iniciarTour } = useTour("produtos", tourProdutos);
  const linhaProdutoRefs = useRef({});
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
  const [menuRelatoriosAberto, setMenuRelatoriosAberto] = useState(false);
  const [modalRelatorioPersonalizado, setModalRelatorioPersonalizado] =
    useState(false);
  const [colunasRelatorio, setColunasRelatorio] = useState([
    "nome",
    "codigo",
    "categoria",
    "estoque",
    "preco_custo",
    "preco_venda",
    "margem",
    "ativo",
  ]);
  const [ordenacaoRelatorio, setOrdenacaoRelatorio] = useState("nome_asc");
  const menuRelatoriosRef = useRef(null);

  // Modal de edição em lote
  const [modalEdicaoLote, setModalEdicaoLote] = useState(false);
  const [dadosEdicaoLote, setDadosEdicaoLote] = useState({
    marca_id: "",
    categoria_id: "",
    departamento_id: "",
  });
  const [departamentos, setDepartamentos] = useState([]);

  // Modal de resolucao rapida para conflitos de exclusao (409)
  const [modalConflitoExclusao, setModalConflitoExclusao] = useState(false);
  const [bloqueiosExclusao, setBloqueiosExclusao] = useState([]);
  const [variacoesSelecionadasConflito, setVariacoesSelecionadasConflito] =
    useState([]);
  const [resolvendoConflitoExclusao, setResolvendoConflitoExclusao] =
    useState(false);
  const [autoSelecionarConflito, setAutoSelecionarConflito] = useState(true);
  const [pularConfirmacaoConflito, setPularConfirmacaoConflito] =
    useState(false);

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
    mostrarPaisVariacoes: false,
  });

  // Paginação
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [itensPorPagina, setItensPorPagina] = useState(20);
  const [totalItensServidor, setTotalItensServidor] = useState(0);
  const [totalPaginasServidor, setTotalPaginasServidor] = useState(1);

  // Aplica apenas filtros locais visuais.
  // Busca/categoria/marca/fornecedor/estoque/promoção agora são filtrados no backend.
  const produtosFiltrados = useMemo(() => {
    let produtosTemp = [...produtosBrutos];

    // No modo padrão, mostrar apenas produtos normais (sem PAI e sem VARIAÇÃO).
    if (!filtros.mostrarPaisVariacoes) {
      return produtosTemp.filter(
        (p) => p.tipo_produto !== "PAI" && p.tipo_produto !== "VARIACAO",
      );
    }

    // Com "Mostrar Pais e Variações" ativo, exibe as variações
    // somente quando o respectivo PAI estiver expandido.
    produtosTemp = produtosTemp.filter((p) => {
      if (p.tipo_produto !== "VARIACAO") {
        return true;
      }

      return paisExpandidos.includes(p.produto_pai_id);
    });

    return produtosTemp;
  }, [produtosBrutos, filtros.mostrarPaisVariacoes, paisExpandidos]);

  const produtosPaginados = produtosFiltrados;
  const totalPaginas = Math.max(totalPaginasServidor, 1);
  const totalItens = totalItensServidor;

  // Alias para manter compatibilidade com o resto do código
  const produtos = produtosPaginados;
  const produtosVisiveisRef = useRef([]);

  // Resetar para página 1 quando filtros mudarem
  useEffect(() => {
    setPaginaAtual(1);
  }, [filtros]);

  useEffect(() => {
    const handleClickFora = (event) => {
      if (
        menuRelatoriosRef.current &&
        !menuRelatoriosRef.current.contains(event.target)
      ) {
        setMenuRelatoriosAberto(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  useEffect(() => {
    produtosVisiveisRef.current = produtos;
  }, [produtos]);

  // Carregar dados iniciais
  useEffect(() => {
    carregarCategorias();
    carregarMarcas();
    carregarFornecedores();
    carregarDepartamentos();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      carregarDados();
    }, filtros.busca ? 250 : 0);

    return () => clearTimeout(timer);
  }, [
    paginaAtual,
    itensPorPagina,
    filtros.busca,
    filtros.ativo,
    filtros.categoria_id,
    filtros.marca_id,
    filtros.fornecedor_id,
    filtros.estoque_baixo,
    filtros.em_promocao,
  ]);

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
      // Remover campos vazios dos filtros e montar paginação no backend.
      const filtrosLimpos = {};
      Object.keys(filtrosAtuais).forEach((key) => {
        const valor = filtrosAtuais[key];

        if (key === "mostrarPaisVariacoes") {
          return;
        }

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

      filtrosLimpos.page = paginaAtual;
      filtrosLimpos.page_size = itensPorPagina;
      filtrosLimpos.include_variations = filtrosAtuais.mostrarPaisVariacoes;

      const response = await getProdutos(filtrosLimpos);

      // API retorna { itens: [], total: 0, pagina: 1, ... } ou apenas array
      let produtosData;
      let totalApi = 0;
      let pagesApi = 1;
      if (Array.isArray(response.data)) {
        produtosData = response.data;
        totalApi = response.data.length;
      } else if (response.data.itens) {
        produtosData = response.data.itens;
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
      } else if (response.data.items) {
        produtosData = response.data.items;
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
      } else if (response.data.produtos) {
        produtosData = response.data.produtos;
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
      } else if (response.data.data) {
        produtosData = response.data.data;
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
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
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
      }

      // ========================================
      // 🔒 SPRINT 2 - SALVAR DADOS BRUTOS (SEM ORGANIZAR)
      // ========================================
      // Salvar dados originais sem hierarquia
      // A organização será feita no useMemo abaixo
      setProdutosBrutos(produtosData);
      setTotalItensServidor(totalApi);
      setTotalPaginasServidor(Math.max(pagesApi, 1));
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

    if (campo === "mostrarPaisVariacoes" && !valor) {
      // Ao ocultar variações, fecha expansões para manter o estado previsível.
      setPaisExpandidos([]);
    }

    if (campo !== "mostrarPaisVariacoes") {
      setPaginaAtual(1);
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

  const obterNomeProduto = (id) => {
    const produto = produtosBrutos.find((item) => item.id === id);
    return corrigirTextoQuebrado(produto?.nome || `Produto #${id}`);
  };

  const extrairErroExclusao = (error) => {
    const statusCode = error?.response?.status;
    const detalheServidor = corrigirTextoQuebrado(error?.response?.data?.detail);

    if (statusCode === 409) {
      return {
        statusCode,
        mensagem:
          detalheServidor ||
          "Nao foi possivel excluir porque este produto possui vinculos ativos.",
      };
    }

    if (statusCode === 404) {
      return {
        statusCode,
        mensagem: "Produto nao encontrado. Atualize a tela e tente novamente.",
      };
    }

    return {
      statusCode,
      mensagem:
        detalheServidor ||
        "Erro ao excluir produto. Tente novamente em instantes.",
    };
  };

  const abrirModalConflitoExclusao = async (falhas) => {
    const falhasConflito = falhas.filter((falha) => falha.statusCode === 409);

    if (falhasConflito.length === 0) {
      return false;
    }

    const paisComConflito = [...new Set(falhasConflito.map((falha) => falha.id))];
    const bloqueios = [];

    for (const parentId of paisComConflito) {
      const falhaPai = falhasConflito.find((falha) => falha.id === parentId);
      let variacoes = [];

      try {
        const response = await getProdutoVariacoes(parentId);
        variacoes = (response?.data || []).filter((item) => item.ativo !== false);
      } catch (error) {
        console.error(
          `Erro ao buscar variacoes do produto ${parentId} para resolver conflito:`,
          error,
        );
      }

      bloqueios.push({
        parentId,
        parentNome: obterNomeProduto(parentId),
        mensagem: corrigirTextoQuebrado(
          falhaPai?.mensagem || "Produto com bloqueio para exclusao.",
        ),
        variacoes,
      });
    }

    setBloqueiosExclusao(bloqueios);
    const todasVariacoes = bloqueios.flatMap((bloqueio) =>
      bloqueio.variacoes.map((variacao) => variacao.id),
    );
    setVariacoesSelecionadasConflito(autoSelecionarConflito ? todasVariacoes : []);
    setModalConflitoExclusao(true);
    return true;
  };

  const handleSelecionarVariacaoConflito = (variacaoId, checked) => {
    setVariacoesSelecionadasConflito((prev) => {
      if (checked) {
        if (prev.includes(variacaoId)) return prev;
        return [...prev, variacaoId];
      }

      return prev.filter((id) => id !== variacaoId);
    });
  };

  const handleSelecionarTodasVariacoesDoPai = (parentId, checked) => {
    const idsDoPai = (bloqueiosExclusao.find((item) => item.parentId === parentId)
      ?.variacoes || []
    ).map((variacao) => variacao.id);

    setVariacoesSelecionadasConflito((prev) => {
      if (checked) {
        const conjunto = new Set([...prev, ...idsDoPai]);
        return Array.from(conjunto);
      }

      return prev.filter((id) => !idsDoPai.includes(id));
    });
  };

  const handleResolverConflitosExclusao = async () => {
    if (bloqueiosExclusao.length === 0) {
      setModalConflitoExclusao(false);
      return;
    }

    if (!pularConfirmacaoConflito) {
      const confirma = confirm(
        "Confirmar resolucao rapida? O sistema vai desativar as variacoes selecionadas e tentar excluir os produtos pai.",
      );
      if (!confirma) return;
    }

    setResolvendoConflitoExclusao(true);

    const paisExcluidos = [];
    const paisComFalha = [];

    for (const bloqueio of bloqueiosExclusao) {
      const variacoesSelecionadas = bloqueio.variacoes.filter((variacao) =>
        variacoesSelecionadasConflito.includes(variacao.id),
      );

      const resultadosVariacoes = await Promise.allSettled(
        variacoesSelecionadas.map((variacao) => deleteProduto(variacao.id)),
      );

      const falhasVariacao = resultadosVariacoes
        .filter((resultado) => resultado.status === "rejected")
        .map((resultado) => extrairErroExclusao(resultado.reason));

      try {
        await deleteProduto(bloqueio.parentId);
        paisExcluidos.push(bloqueio);
      } catch (error) {
        const erroPai = extrairErroExclusao(error);
        paisComFalha.push({
          ...bloqueio,
          mensagem:
            falhasVariacao[0]?.mensagem || erroPai.mensagem || bloqueio.mensagem,
        });
      }
    }

    setResolvendoConflitoExclusao(false);
    setModalConflitoExclusao(false);

    if (paisExcluidos.length > 0) {
      toast.success(
        `${paisExcluidos.length} produto(s) pai excluido(s) apos resolver variacoes.`,
      );
    }

    if (paisComFalha.length > 0) {
      const detalhes = paisComFalha
        .slice(0, 3)
        .map((item) => `${item.parentNome}: ${item.mensagem}`)
        .join("\n");
      const sufixo =
        paisComFalha.length > 3 ? "\n...e outros produtos continuam bloqueados." : "";

      alert(
        `Ainda nao foi possivel excluir ${paisComFalha.length} produto(s):\n\n${detalhes}${sufixo}`,
      );
      setSelecionados(paisComFalha.map((item) => item.parentId));
    } else {
      setSelecionados([]);
    }

    setBloqueiosExclusao([]);
    await carregarDados();
  };

  const handleExcluir = async (id) => {
    if (!confirm("Deseja realmente excluir este produto?")) return;

    try {
      await deleteProduto(id);
      toast.success("Produto excluido com sucesso!");
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir produto:", error);
      const erro = extrairErroExclusao(error);

      if (erro.statusCode === 409) {
        const abriuModal = await abrirModalConflitoExclusao([{ id, ...erro }]);
        if (abriuModal) {
          return;
        }
      }

      alert(erro.mensagem);
    }
  };

  const handleExcluirSelecionados = async () => {
    if (!confirm(`Deseja realmente excluir ${selecionados.length} produtos?`))
      return;

    const resultados = await Promise.allSettled(
      selecionados.map((id) => deleteProduto(id)),
    );

    const idsExcluidos = [];
    const falhas = [];

    resultados.forEach((resultado, index) => {
      const id = selecionados[index];

      if (resultado.status === "fulfilled") {
        idsExcluidos.push(id);
        return;
      }

      const erro = extrairErroExclusao(resultado.reason);
      falhas.push({ id, ...erro });
      console.error(`Erro ao excluir produto ${id}:`, resultado.reason);
    });

    if (idsExcluidos.length > 0) {
      toast.success(
        `${idsExcluidos.length} produto(s) excluido(s) com sucesso!`,
      );
      carregarDados();
    }

    if (falhas.length > 0) {
      const abriuModal = await abrirModalConflitoExclusao(falhas);
      if (abriuModal) {
        setSelecionados(falhas.map((falha) => falha.id));
        return;
      }

      const mensagens = falhas.slice(0, 3).map((falha) => {
        return `ID ${falha.id}: ${falha.mensagem}`;
      });
      const sufixo =
        falhas.length > 3 ? "\n...e outros produtos com erro." : "";

      alert(
        `Nao foi possivel excluir ${falhas.length} produto(s):\n\n${mensagens.join("\n")}${sufixo}`,
      );

      setSelecionados(falhas.map((falha) => falha.id));
      return;
    }

    setSelecionados([]);
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

  const garantirLinhaVisivel = (produtoId) => {
    const linha = linhaProdutoRefs.current[produtoId];
    if (!linha) return;
    linha.scrollIntoView({
      behavior: "smooth",
      block: "center",
      inline: "nearest",
    });
  };

  const garantirGrupoPaiVisivel = (produtoId) => {
    const produtosVisiveis = produtosVisiveisRef.current || [];
    const variacoesVisiveis = produtosVisiveis.filter(
      (produto) =>
        produto.tipo_produto === "VARIACAO" && produto.produto_pai_id === produtoId,
    );

    const ultimoProdutoVisivel =
      variacoesVisiveis[variacoesVisiveis.length - 1] ||
      produtosVisiveis.find((produto) => produto.id === produtoId);

    if (!ultimoProdutoVisivel) {
      garantirLinhaVisivel(produtoId);
      return;
    }

    const linha = linhaProdutoRefs.current[ultimoProdutoVisivel.id];
    if (!linha) {
      garantirLinhaVisivel(produtoId);
      return;
    }

    linha.scrollIntoView({
      behavior: "smooth",
      block: variacoesVisiveis.length > 0 ? "end" : "center",
      inline: "nearest",
    });
  };

  // Expandir/colapsar KIT
  const toggleKitExpandido = (produtoId) => {
    const vaiExpandir = !kitsExpandidos.includes(produtoId);
    setKitsExpandidos((prev) =>
      prev.includes(produtoId)
        ? prev.filter((id) => id !== produtoId)
        : [...prev, produtoId],
    );
    if (vaiExpandir) {
      setTimeout(() => garantirLinhaVisivel(produtoId), 80);
    }
  };

  // Expandir/colapsar PAI (mostrar variações)
  const togglePaiExpandido = (produtoId) => {
    const vaiExpandir = !paisExpandidos.includes(produtoId);
    setPaisExpandidos((prev) =>
      prev.includes(produtoId)
        ? prev.filter((id) => id !== produtoId)
        : [...prev, produtoId],
    );
    if (vaiExpandir) {
      setTimeout(() => garantirGrupoPaiVisivel(produtoId), 120);
    }
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

  const extrairItensDaRespostaProdutos = (payload) => {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.itens)) return payload.itens;
    if (Array.isArray(payload.items)) return payload.items;
    if (Array.isArray(payload.produtos)) return payload.produtos;
    if (Array.isArray(payload.data)) return payload.data;
    return [];
  };

  const montarFiltroLimpo = (baseFiltros) => {
    const filtrosLimpos = {};
    Object.entries(baseFiltros || {}).forEach(([key, valor]) => {
      if (key === "mostrarPaisVariacoes") return;
      if (key === "ativo") {
        if (valor === "ativos") {
          filtrosLimpos[key] = true;
        } else if (valor === "inativos") {
          filtrosLimpos[key] = false;
        }
        return;
      }
      if (valor === "" || valor === null || valor === undefined) return;
      if (typeof valor === "boolean") {
        if (valor) filtrosLimpos[key] = true;
        return;
      }
      filtrosLimpos[key] = valor;
    });
    return filtrosLimpos;
  };

  const carregarProdutosRelatorio = async (escopo) => {
    const filtrosBase =
      escopo === "geral"
        ? { ativo: "todos", mostrarPaisVariacoes: filtros.mostrarPaisVariacoes }
        : { ...filtros };
    const filtrosLimpos = montarFiltroLimpo(filtrosBase);
    filtrosLimpos.include_variations = Boolean(filtrosBase.mostrarPaisVariacoes);

    const acumulado = [];
    let pagina = 1;
    let continuar = true;

    while (continuar && pagina <= 40) {
      const resposta = await getProdutos({
        ...filtrosLimpos,
        page: pagina,
        page_size: 300,
      });
      const itens = extrairItensDaRespostaProdutos(resposta?.data);
      if (itens.length === 0) {
        continuar = false;
      } else {
        acumulado.push(...itens);
        if (itens.length < 300) {
          continuar = false;
        }
        pagina += 1;
      }
    }

    return acumulado;
  };

  const ordenarProdutosRelatorio = (lista, ordenacao) => {
    const copia = [...lista];
    const porTexto = (a, b, getter, asc = true) => {
      const va = String(getter(a) || "").toLowerCase();
      const vb = String(getter(b) || "").toLowerCase();
      return asc ? va.localeCompare(vb, "pt-BR") : vb.localeCompare(va, "pt-BR");
    };

    switch (ordenacao) {
      case "nome_desc":
        return copia.sort((a, b) => porTexto(a, b, (p) => p.nome, false));
      case "estoque_asc":
        return copia.sort(
          (a, b) => Number(a.estoque_atual ?? a.estoque ?? 0) - Number(b.estoque_atual ?? b.estoque ?? 0),
        );
      case "estoque_desc":
        return copia.sort(
          (a, b) => Number(b.estoque_atual ?? b.estoque ?? 0) - Number(a.estoque_atual ?? a.estoque ?? 0),
        );
      case "preco_asc":
        return copia.sort((a, b) => Number(a.preco_venda ?? 0) - Number(b.preco_venda ?? 0));
      case "preco_desc":
        return copia.sort((a, b) => Number(b.preco_venda ?? 0) - Number(a.preco_venda ?? 0));
      case "nome_asc":
      default:
        return copia.sort((a, b) => porTexto(a, b, (p) => p.nome, true));
    }
  };

  const normalizarValorCsv = (valor) => {
    if (valor === null || valor === undefined) return "";
    if (typeof valor === "number") return String(valor).replace(".", ",");
    return String(valor).replaceAll("\"", '""');
  };

  const baixarCsvProdutos = (nomeArquivo, colunas, dados) => {
    const cabecalho = colunas.map((coluna) => `"${coluna.label}"`).join(";");
    const linhas = dados.map((item) => {
      const valores = colunas.map((coluna) => {
        const valorBruto = coluna.value(item);
        const valorFinal = coluna.key === "atualizado_em" ? formatarData(valorBruto) : valorBruto;
        return `"${normalizarValorCsv(valorFinal)}"`;
      });
      return valores.join(";");
    });

    const csv = [cabecalho, ...linhas].join("\n");
    const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", nomeArquivo);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const gerarRelatorioProdutos = async ({ escopo, personalizado = false }) => {
    try {
      toast.loading("Gerando relatorio...", { id: "relatorio-produtos" });
      const dados = await carregarProdutosRelatorio(escopo);

      if (!dados.length) {
        toast.error("Nenhum produto encontrado para este relatorio.", {
          id: "relatorio-produtos",
        });
        return;
      }

      const ordenados = ordenarProdutosRelatorio(dados, ordenacaoRelatorio);
      const colunasSelecionadas = new Set(colunasRelatorio.filter(Boolean));
      const colunas = COLUNAS_RELATORIO_PRODUTOS.filter((coluna) =>
        colunasSelecionadas.has(coluna.key),
      );

      if (!colunas.length) {
        toast.error("Selecione pelo menos uma coluna para gerar o relatorio.", {
          id: "relatorio-produtos",
        });
        return;
      }

      const sufixo = escopo === "geral" ? "geral" : "filtrado";
      const dataArquivo = new Date().toISOString().slice(0, 10);
      baixarCsvProdutos(`produtos_${sufixo}_${dataArquivo}.csv`, colunas, ordenados);

      toast.success(`Relatorio gerado com ${ordenados.length} produto(s).`, {
        id: "relatorio-produtos",
      });
    } catch (error) {
      console.error("Erro ao gerar relatorio de produtos:", error);
      toast.error("Nao foi possivel gerar o relatorio de produtos.", {
        id: "relatorio-produtos",
      });
    }
  };

  const toggleColunaRelatorio = (key) => {
    setColunasRelatorio((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    );
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
          <div className="relative" ref={menuRelatoriosRef}>
            <button
              onClick={() => setMenuRelatoriosAberto((prev) => !prev)}
              className="px-4 py-2 text-indigo-700 rounded-xl bg-indigo-50 hover:bg-indigo-100 shadow-sm hover:shadow-md transition-all duration-200 border border-indigo-200 font-medium"
            >
              Relatorios
            </button>

            {menuRelatoriosAberto && (
              <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 z-40">
                <button
                  onClick={() => {
                    setMenuRelatoriosAberto(false);
                    gerarRelatorioProdutos({ escopo: "geral" });
                  }}
                  className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50"
                >
                  Relatorio geral (todos os produtos)
                </button>
                <button
                  onClick={() => {
                    setMenuRelatoriosAberto(false);
                    gerarRelatorioProdutos({ escopo: "filtrado" });
                  }}
                  className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                >
                  Relatorio do que filtrei
                </button>
                <button
                  onClick={() => {
                    setMenuRelatoriosAberto(false);
                    setModalRelatorioPersonalizado(true);
                  }}
                  className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                >
                  Relatorio personalizado
                </button>
              </div>
            )}
          </div>
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

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filtros.mostrarPaisVariacoes}
                onChange={(e) =>
                  handleFiltroChange("mostrarPaisVariacoes", e.target.checked)
                }
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Mostrar Pais e Variações</span>
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
                        ref={(el) => {
                          linhaProdutoRefs.current[produto.id] = el;
                        }}
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

      {/* Modal de resolucao rapida para conflitos de exclusao */}
      {modalConflitoExclusao && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[85vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Produtos com bloqueio para exclusao
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Selecione as variacoes que deseja desativar agora para o sistema tentar excluir os produtos pai automaticamente.
                </p>
              </div>
              <button
                onClick={() => {
                  if (resolvendoConflitoExclusao) return;
                  setModalConflitoExclusao(false);
                }}
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

            <div className="space-y-4">
              <div className="border border-blue-100 bg-blue-50 rounded-lg p-3">
                <label className="flex items-center gap-2 text-sm text-blue-900">
                  <input
                    type="checkbox"
                    checked={autoSelecionarConflito}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      setAutoSelecionarConflito(checked);

                      if (checked) {
                        setVariacoesSelecionadasConflito(
                          bloqueiosExclusao.flatMap((bloqueio) =>
                            bloqueio.variacoes.map((variacao) => variacao.id),
                          ),
                        );
                      }
                    }}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                  Selecionar tudo automaticamente
                </label>
                <label className="flex items-center gap-2 text-sm text-blue-900 mt-2">
                  <input
                    type="checkbox"
                    checked={pularConfirmacaoConflito}
                    onChange={(e) => setPularConfirmacaoConflito(e.target.checked)}
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
                  <div
                    key={bloqueio.parentId}
                    className="border border-gray-200 rounded-lg p-4"
                  >
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
                            onChange={(e) =>
                              handleSelecionarTodasVariacoesDoPai(
                                bloqueio.parentId,
                                e.target.checked,
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
                                  onChange={(e) =>
                                    handleSelecionarVariacaoConflito(
                                      variacao.id,
                                      e.target.checked,
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
                        Nao foi possivel listar variacoes automaticamente para este item. Tente atualizar a tela e repetir.
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setModalConflitoExclusao(false)}
                disabled={resolvendoConflitoExclusao}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-60"
              >
                Cancelar
              </button>
              <button
                onClick={handleResolverConflitosExclusao}
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

      {modalRelatorioPersonalizado && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Relatorio Personalizado de Produtos
              </h3>
              <button
                onClick={() => setModalRelatorioPersonalizado(false)}
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
                  onChange={(e) => setOrdenacaoRelatorio(e.target.value)}
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
                <p className="text-sm font-medium text-gray-700 mb-2">
                  Colunas para exibir
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {COLUNAS_RELATORIO_PRODUTOS.map((coluna) => (
                    <label
                      key={coluna.key}
                      className="flex items-center gap-2 p-2 rounded hover:bg-gray-50"
                    >
                      <input
                        type="checkbox"
                        checked={colunasRelatorio.includes(coluna.key)}
                        onChange={() => toggleColunaRelatorio(coluna.key)}
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
                onClick={() => setModalRelatorioPersonalizado(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={async () => {
                  await gerarRelatorioProdutos({ escopo: "filtrado", personalizado: true });
                  setModalRelatorioPersonalizado(false);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
              >
                Gerar relatorio
              </button>
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
