import api from "./api";
import {
  FuncionarioPdvCaixa,
  FuncionarioPdvCliente,
  FuncionarioPdvFinalizarPayload,
  FuncionarioPdvFinalizarResponse,
  FuncionarioPdvProduto,
} from "../types";

function normalizarProdutoPdv(data: any): FuncionarioPdvProduto {
  return {
    id: Number(data.id),
    nome: String(data.nome ?? ""),
    codigo: data.codigo ?? null,
    codigo_barras: data.codigo_barras ?? null,
    unidade: data.unidade ?? "UN",
    preco_venda: Number(data.preco_venda ?? 0),
    estoque_atual: Number(data.estoque_atual ?? 0),
    imagem_url: data.imagem_url ?? null,
    tipo_produto: data.tipo_produto ?? null,
    tipo_kit: data.tipo_kit ?? null,
    vendavel: data.vendavel !== false,
    aviso: data.aviso ?? null,
  };
}

function normalizarClientePdv(data: any): FuncionarioPdvCliente {
  return {
    id: Number(data.id),
    codigo: data.codigo ?? null,
    nome: String(data.nome ?? ""),
    telefone: data.telefone ?? null,
    celular: data.celular ?? null,
    documento: data.documento ?? null,
  };
}

export async function buscarProdutoPdvPorBarcode(
  barcode: string,
): Promise<FuncionarioPdvProduto | null> {
  try {
    const response = await api.get(
      `/app/funcionario/pdv/produtos/barcode/${encodeURIComponent(barcode)}`,
    );
    return normalizarProdutoPdv(response.data);
  } catch (error: any) {
    if (error?.response?.status === 404) return null;
    throw error;
  }
}

export async function buscarProdutosPdv(termo: string): Promise<FuncionarioPdvProduto[]> {
  const q = termo.trim();
  if (q.length < 2) return [];
  const response = await api.get("/app/funcionario/pdv/produtos/buscar", {
    params: { q },
  });
  return Array.isArray(response.data) ? response.data.map(normalizarProdutoPdv) : [];
}

export async function buscarClientesPdv(termo: string): Promise<FuncionarioPdvCliente[]> {
  const q = termo.trim();
  if (q.length < 2) return [];
  const response = await api.get("/app/funcionario/pdv/clientes/buscar", {
    params: { q },
  });
  return Array.isArray(response.data) ? response.data.map(normalizarClientePdv) : [];
}

export async function obterCaixaAbertoPdv(): Promise<FuncionarioPdvCaixa> {
  const response = await api.get("/app/funcionario/pdv/caixa/aberto");
  return {
    aberto: Boolean(response.data?.aberto),
    caixa_id: response.data?.caixa_id ?? null,
    numero_caixa: response.data?.numero_caixa ?? null,
    mensagem: String(response.data?.mensagem ?? ""),
  };
}

export async function finalizarVendaPdv(
  payload: FuncionarioPdvFinalizarPayload,
): Promise<FuncionarioPdvFinalizarResponse> {
  const response = await api.post("/app/funcionario/pdv/vendas/finalizar", payload);
  return {
    status: String(response.data?.status ?? ""),
    venda_id: Number(response.data?.venda_id ?? 0),
    numero_venda: String(response.data?.numero_venda ?? ""),
    total: Number(response.data?.total ?? 0),
    total_pago: Number(response.data?.total_pago ?? 0),
    forma_pagamento: String(response.data?.forma_pagamento ?? ""),
    mensagem: String(response.data?.mensagem ?? ""),
  };
}
