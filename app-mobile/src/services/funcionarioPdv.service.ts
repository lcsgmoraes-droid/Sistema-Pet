import api from "./api";
import {
  FuncionarioPdvBeneficiosPreview,
  FuncionarioPdvBeneficiosPreviewPayload,
  FuncionarioPdvCaixa,
  FuncionarioPdvCliente,
  FuncionarioPdvFormaPagamentoOpcao,
  FuncionarioPdvFinalizarPayload,
  FuncionarioPdvFinalizarResponse,
  FuncionarioPdvProduto,
  FuncionarioPdvSalvarPayload,
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
    tipo_cadastro: data.tipo_cadastro ?? null,
    email: data.email ?? null,
    endereco: data.endereco ?? null,
    credito: Number(data.credito ?? 0),
    fidelidade: data.fidelidade ?? null,
    cupons_disponiveis: data.cupons_disponiveis ?? [],
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

export async function listarFormasPagamentoPdv(): Promise<FuncionarioPdvFormaPagamentoOpcao[]> {
  const response = await api.get("/app/funcionario/pdv/formas-pagamento");
  return Array.isArray(response.data)
    ? response.data.map((item: any) => ({
        id: Number(item.id),
        nome: String(item.nome ?? ""),
        tipo: String(item.tipo ?? ""),
        key: item.key,
        taxa_percentual: Number(item.taxa_percentual ?? 0),
        permite_parcelamento: Boolean(item.permite_parcelamento),
        numero_parcelas: Number(item.numero_parcelas ?? 1),
        max_parcelas: Number(item.max_parcelas ?? item.numero_parcelas ?? 1),
        parcelas_maximas: Number(item.parcelas_maximas ?? item.numero_parcelas ?? 1),
      }))
    : [];
}

export async function previewBeneficiosPdv(
  payload: FuncionarioPdvBeneficiosPreviewPayload,
): Promise<FuncionarioPdvBeneficiosPreview> {
  const response = await api.post("/app/funcionario/pdv/beneficios/preview", payload);
  const cupons = Array.isArray(response.data?.cupons_disponiveis)
    ? response.data.cupons_disponiveis
    : [];
  const beneficiosGerados = Array.isArray(response.data?.beneficios_gerados)
    ? response.data.beneficios_gerados
    : [];

  return {
    subtotal: Number(response.data?.subtotal ?? 0),
    desconto_cupom: Number(response.data?.desconto_cupom ?? 0),
    cupom_code: response.data?.cupom_code ?? null,
    cashback_disponivel: Number(response.data?.cashback_disponivel ?? 0),
    cashback_valor: Number(response.data?.cashback_valor ?? 0),
    total_venda: Number(response.data?.total_venda ?? 0),
    valor_pagamento: Number(response.data?.valor_pagamento ?? 0),
    cupons_disponiveis: cupons.map((item: any) => ({
      code: String(item.code ?? ""),
      coupon_type: String(item.coupon_type ?? ""),
      discount_value: item.discount_value == null ? null : Number(item.discount_value),
      discount_percent: item.discount_percent == null ? null : Number(item.discount_percent),
      discount_applied: Number(item.discount_applied ?? 0),
      min_purchase_value: item.min_purchase_value == null ? null : Number(item.min_purchase_value),
      valid_until: item.valid_until ?? null,
    })),
    beneficios_gerados: beneficiosGerados.map((item: any) => ({
      tipo: String(item.tipo ?? ""),
      titulo: String(item.titulo ?? ""),
      valor: item.valor == null ? null : Number(item.valor),
      percentual: item.percentual == null ? null : Number(item.percentual),
      quantidade: item.quantidade == null ? null : Number(item.quantidade),
      descricao: item.descricao ?? null,
    })),
    mensagens: Array.isArray(response.data?.mensagens)
      ? response.data.mensagens.map((item: any) => String(item))
      : [],
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

export async function salvarVendaPdv(
  payload: FuncionarioPdvSalvarPayload,
): Promise<FuncionarioPdvFinalizarResponse> {
  const response = await api.post("/app/funcionario/pdv/vendas/salvar", payload);
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
