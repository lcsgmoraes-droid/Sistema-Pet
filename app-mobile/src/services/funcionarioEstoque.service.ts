import api from "./api";
import {
  FuncionarioBalancoPayload,
  FuncionarioBalancoResponse,
  FuncionarioProdutoEstoque,
} from "../types";
import { API_BASE_URL } from "../config";

function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  const base = API_BASE_URL.replace(/\/api\/?$/, "").replace(/\/$/, "");
  return `${base}${url.startsWith("/") ? url : `/${url}`}`;
}

function normalizarProduto(data: any): FuncionarioProdutoEstoque {
  return {
    id: Number(data.id),
    nome: String(data.nome ?? ""),
    codigo: data.codigo ?? null,
    codigo_barras: data.codigo_barras ?? null,
    gtin_ean: data.gtin_ean ?? null,
    unidade: data.unidade ?? "UN",
    preco_venda: Number(data.preco_venda ?? 0),
    preco_custo: Number(data.preco_custo ?? 0),
    estoque_atual: Number(data.estoque_atual ?? 0),
    imagem_url: resolveMediaUrl(data.imagem_url ?? data.imagem_principal ?? data.foto_url),
    is_parent: Boolean(data.is_parent),
    tipo_produto: data.tipo_produto ?? null,
    tipo_kit: data.tipo_kit ?? null,
    permite_balanco: data.permite_balanco !== false,
    aviso: data.aviso ?? null,
  };
}

export async function buscarProdutoFuncionarioPorBarcode(
  barcode: string,
): Promise<FuncionarioProdutoEstoque | null> {
  try {
    const response = await api.get(
      `/app/funcionario/estoque/produtos/barcode/${encodeURIComponent(barcode)}`,
    );
    return normalizarProduto(response.data);
  } catch (error: any) {
    if (error?.response?.status === 404) return null;
    throw error;
  }
}

export async function buscarProdutosFuncionario(
  termo: string,
): Promise<FuncionarioProdutoEstoque[]> {
  const q = termo.trim();
  if (q.length < 2) return [];
  const response = await api.get("/app/funcionario/estoque/produtos/buscar", {
    params: { q },
  });
  return Array.isArray(response.data) ? response.data.map(normalizarProduto) : [];
}

export async function registrarBalancoFuncionario(
  payload: FuncionarioBalancoPayload,
): Promise<FuncionarioBalancoResponse> {
  const response = await api.post("/app/funcionario/estoque/balanco", payload);
  return {
    ...response.data,
    produto: normalizarProduto(response.data?.produto ?? {}),
    estoque_anterior: Number(response.data?.estoque_anterior ?? 0),
    estoque_novo: Number(response.data?.estoque_novo ?? 0),
    diferenca: Number(response.data?.diferenca ?? 0),
    quantidade_movimentada: Number(response.data?.quantidade_movimentada ?? 0),
  };
}
