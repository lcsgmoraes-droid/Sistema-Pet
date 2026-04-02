// âš ï¸ ARQUIVO CRÃTICO DE PRODUÃ‡ÃƒO
// Este arquivo impacta diretamente operaÃ§Ãµes reais (PDV / Financeiro / Estoque).
// NÃƒO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenÃ¡rio real
// 3. Validar impacto financeiro

/**
 * PÃ¡gina de Listagem de Produtos - Estilo Bling
 */
import React, { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import api from "../api";
import {
  deleteProduto,
  formatarData,
  formatarMoeda,
  getCategorias,
  getMarcas,
  getProdutoVariacoes,
  toggleProdutoAtivo,
} from "../api/produtos";
import ProdutosMainContent from "../components/produtos/ProdutosMainContent";
import ProdutosModalsLayer from "../components/produtos/ProdutosModalsLayer";
import useProdutosListagem from "../hooks/useProdutosListagem";
import useProdutosPageComposition from "../hooks/useProdutosPageComposition";
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
  const scoreQuebrado = (texto) => (texto.match(/[ÃƒÃ‚Ã¢ï¿½]/g) || []).length;

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
    .replaceAll("Ã¢ÂÅ’", "âŒ")
    .replaceAll("ÃƒÂ§", "Ã§")
    .replaceAll("ÃƒÂ£", "Ã£")
    .replaceAll("ÃƒÂµ", "Ãµ")
    .replaceAll("ÃƒÂ¡", "Ã¡")
    .replaceAll("ÃƒÂ©", "Ã©")
    .replaceAll("ÃƒÂª", "Ãª")
    .replaceAll("ÃƒÂ­", "Ã­")
    .replaceAll("ÃƒÂ³", "Ã³")
    .replaceAll("ÃƒÂº", "Ãº")
    .replaceAll("Ã¢â‚¬â€œ", "-")
    .replaceAll("Ã‚", "");
};

const montarMensagemConflitoExclusao = (nomeProduto, detalheServidor) => {
  const detalheLimpo = corrigirTextoQuebrado(detalheServidor || "");
  const correspondenciaQuantidade = detalheLimpo.match(/possui\s+(\d+)/i);
  const quantidadeVariacoes = correspondenciaQuantidade?.[1] || "1";
  const nomeLimpo = corrigirTextoQuebrado(nomeProduto || "Produto");

  return `Produto '${nomeLimpo}' possui ${quantidadeVariacoes} variacao(oes) ativa(s) e nao pode ser desativado. Desative primeiro todas as variacoes.`;
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

const isKitVirtualProduto = (produto) => {
  const tipoProduto = String(produto?.tipo_produto || "").toUpperCase();
  const tipoKit = String(produto?.tipo_kit || "").toUpperCase();
  return (tipoProduto === "KIT" || tipoProduto === "VARIACAO") && tipoKit === "VIRTUAL";
};

const isKitFisicoProduto = (produto) => {
  const tipoProduto = String(produto?.tipo_produto || "").toUpperCase();
  const tipoKit = String(produto?.tipo_kit || "").toUpperCase();
  return (tipoProduto === "KIT" || tipoProduto === "VARIACAO") && tipoKit === "FISICO";
};

const isProdutoComComposicao = (produto) =>
  isKitVirtualProduto(produto) || isKitFisicoProduto(produto);

const obterEstoqueVisualProduto = (produto) => {
  if (isKitVirtualProduto(produto)) {
    return Number(produto?.estoque_virtual ?? produto?.estoque_atual ?? produto?.estoque ?? 0);
  }
  return Number(produto?.estoque_atual ?? produto?.estoque ?? 0);
};

// ====================================================
// DEFINIÃ‡ÃƒO DE COLUNAS DA LISTAGEM
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
    value: (p) => obterEstoqueVisualProduto(p),
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
  const [categorias, setCategorias] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [fornecedores, setFornecedores] = useState([]);
  const [editandoPreco, setEditandoPreco] = useState(null);
  const [novoPreco, setNovoPreco] = useState("");

  // Estado para KITs expandidos
  const [kitsExpandidos, setKitsExpandidos] = useState([]);

  // Estado para PAIs expandidos (mostrar variaÃ§Ãµes)
  const [paisExpandidos, setPaisExpandidos] = useState([]);

  // Estado de colunas visÃ­veis (localStorage)
  const [colunasVisiveis, setColunasVisiveis] = useState(() => {
    const salvo = localStorage.getItem("produtos_colunas_visiveis");
    return salvo ? JSON.parse(salvo) : null;
  });

  // Modal de configuraÃ§Ã£o de colunas
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

  // Modal de ediÃ§Ã£o em lote
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

  // Modal de importaÃ§Ã£o
  const [modalImportacao, setModalImportacao] = useState(false);
  const {
    carregarDados,
    filtros,
    handleFiltroChange,
    handleSelecionar,
    handleSelecionarTodos,
    itensPorPagina,
    loading,
    paginaAtual,
    persistirBusca,
    produtos,
    produtosBrutos,
    produtosVisiveisRef,
    selecionados,
    setItensPorPagina,
    setPaginaAtual,
    setPersistirBusca,
    setSelecionados,
    totalItens,
    totalPaginas,
  } = useProdutosListagem({
    normalizeSearchText,
    onOcultarPaisVariacoes: () => setPaisExpandidos([]),
    paisExpandidos,
  });

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

  // Carregar dados iniciais
  useEffect(() => {
    carregarCategorias();
    carregarMarcas();
    carregarFornecedores();
    carregarDepartamentos();
  }, []);

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
      // NÃ£o Ã© erro crÃ­tico, apenas nÃ£o mostra departamentos
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
        mensagem: detalheServidor || "Nao foi possivel excluir porque este produto possui vinculos ativos.",
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
      const parentNome = obterNomeProduto(parentId);
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
        parentNome,
        mensagem: montarMensagemConflitoExclusao(parentNome, falhaPai?.mensagem),
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
      toast.success("PreÃ§o atualizado!");
      setEditandoPreco(null);
      carregarDados();
    } catch (error) {
      console.error("Erro ao atualizar preÃ§o:", error);
      toast.error("Erro ao atualizar preÃ§o");
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

    const estoque = obterEstoqueVisualProduto(produto);
    const minimo = produto.estoque_minimo || 0;

    // Estoque zerado
    if (estoque <= 0) return "text-red-600 font-semibold";

    // Estoque baixo
    if (estoque <= minimo) return "text-yellow-600 font-medium";

    // Estoque normal
    return "text-gray-700";
  };

  // Obter validade mais prÃ³xima dos lotes
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
      cor = "text-orange-600 font-semibold"; // PrÃ³ximo do vencimento
    else if (dias <= 90) cor = "text-yellow-600"; // AtenÃ§Ã£o

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

  // Expandir/colapsar PAI (mostrar variaÃ§Ãµes)
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
    toast.success("PreferÃªncias de colunas salvas!");
  };

  const restaurarColunasPadrao = () => {
    localStorage.removeItem("produtos_colunas_visiveis");
    setColunasVisiveis(null);
    setColunasTemporarias(PRODUTOS_COLUNAS.map((c) => c.key));
    toast.success("Colunas restauradas para o padrÃ£o!");
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
          (a, b) => obterEstoqueVisualProduto(a) - obterEstoqueVisualProduto(b),
        );
      case "estoque_desc":
        return copia.sort(
          (a, b) => obterEstoqueVisualProduto(b) - obterEstoqueVisualProduto(a),
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

  const { mainContentProps, modalsLayerProps } = useProdutosPageComposition({
    catalogosState: {
      categorias,
      departamentos,
      fornecedores,
      marcas,
    },
    columnsState: {
      abrirModalColunas,
      colunasRelatorio,
      colunasTemporarias,
      colunasTabela: PRODUTOS_COLUNAS,
      filtrarColunas,
      modalColunas,
      modalRelatorioPersonalizado,
      onCloseModalColunas: () => setModalColunas(false),
      onCloseModalRelatorio: () => setModalRelatorioPersonalizado(false),
      onGerarRelatorioPersonalizado: async () => {
        await gerarRelatorioProdutos({ escopo: 'filtrado', personalizado: true });
        setModalRelatorioPersonalizado(false);
      },
      onOpenModalRelatorio: () => {
        setMenuRelatoriosAberto(false);
        setModalRelatorioPersonalizado(true);
      },
      onRestaurarColunasPadrao: restaurarColunasPadrao,
      onSalvarColunas: salvarColunas,
      onToggleColuna: toggleColuna,
      onToggleColunaRelatorio: toggleColunaRelatorio,
      ordenacaoRelatorio,
      setOrdenacaoRelatorio,
    },
    conflictState: {
      autoSelecionarConflito,
      bloqueiosExclusao,
      modalConflitoExclusao,
      onCancelarConflito: handleResolverConflitosExclusao,
      onCloseModalConflito: () => {
        if (resolvendoConflitoExclusao) return;
        setModalConflitoExclusao(false);
      },
      onSelecionarTodasVariacoesDoPai: handleSelecionarTodasVariacoesDoPai,
      onSelecionarVariacaoConflito: handleSelecionarVariacaoConflito,
      onToggleAutoSelecionarConflito: (checked) => {
        setAutoSelecionarConflito(checked);
        if (checked) {
          setVariacoesSelecionadasConflito(
            bloqueiosExclusao.flatMap((bloqueio) =>
              bloqueio.variacoes.map((variacao) => variacao.id),
            ),
          );
        }
      },
      onTogglePularConfirmacaoConflito: setPularConfirmacaoConflito,
      pularConfirmacaoConflito,
      resolvendoConflitoExclusao,
      variacoesSelecionadasConflito,
    },
    filtersState: {
      filtros,
      handleFiltroChange,
      persistirBusca,
      setPersistirBusca,
    },
    headerState: {
      iniciarTour,
      menuRelatoriosAberto,
      menuRelatoriosRef,
      navigate,
      onExcluirSelecionados: handleExcluirSelecionados,
      onGerarRelatorioFiltrado: () => {
        setMenuRelatoriosAberto(false);
        gerarRelatorioProdutos({ escopo: 'filtrado' });
      },
      onGerarRelatorioGeral: () => {
        setMenuRelatoriosAberto(false);
        gerarRelatorioProdutos({ escopo: 'geral' });
      },
      onOpenEdicaoLote: handleAbrirEdicaoLote,
      onOpenImportacao: () => setModalImportacao(true),
      onToggleMenuRelatorios: () => setMenuRelatoriosAberto((prev) => !prev),
      selecionadosCount: selecionados.length,
    },
    importState: {
      modalImportacao,
      onCloseImportacao: () => setModalImportacao(false),
      onImportacaoSucesso: () => {
        carregarDados();
        setModalImportacao(false);
      },
    },
    modalsState: {
      dadosEdicaoLote,
      modalEdicaoLote,
      onCloseModalEdicaoLote: () => setModalEdicaoLote(false),
      onSalvarEdicaoLote: handleSalvarEdicaoLote,
      setDadosEdicaoLote,
    },
    reportState: {
      colunasRelatorioProdutos: COLUNAS_RELATORIO_PRODUTOS,
    },
    tableState: {
      editandoPreco,
      getCorEstoque,
      getValidadeMaisProxima,
      handleCancelarEdicaoPreco,
      handleEditarPreco,
      handleExcluir,
      handleSalvarPreco,
      handleSelecionar,
      handleSelecionarTodos,
      handleToggleAtivo,
      itensPorPagina,
      kitsExpandidos,
      linhaProdutoRefs,
      loading,
      novoPreco,
      onChangeItensPorPagina: (value) => {
        setItensPorPagina(Number(value));
        setPaginaAtual(1);
      },
      onIrParaPagina: setPaginaAtual,
      onIrParaPrimeiraPagina: () => setPaginaAtual(1),
      onIrParaUltimaPagina: () => setPaginaAtual(totalPaginas),
      onPaginaAnterior: () => setPaginaAtual((prev) => Math.max(prev - 1, 1)),
      onProximaPagina: () =>
        setPaginaAtual((prev) => Math.min(prev + 1, totalPaginas)),
      paginaAtual,
      paisExpandidos,
      produtos,
      selecionados,
      setNovoPreco,
      toggleKitExpandido,
      togglePaiExpandido,
      totalItens,
      totalPaginas,
    },
    utilsState: {
      copiarTexto,
      corrigirTextoQuebrado,
      isProdutoComComposicao,
    },
  });

  return (
    <div className="p-6">
      <ProdutosMainContent {...mainContentProps} />
      <ProdutosModalsLayer {...modalsLayerProps} />
    </div>
  );
}
