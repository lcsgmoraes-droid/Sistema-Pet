import * as Location from "expo-location";
import { Alert, Linking } from "react-native";

import { formatarMoeda } from "@/utils/format";
import { limparEnderecoParaMaps } from "@/utils/mapsAddress";

export interface PagamentoEntrega {
  forma_pagamento?: string;
  valor?: number | null;
  valor_recebido?: number | null;
  troco?: number | null;
  numero_parcelas?: number | null;
  bandeira?: string | null;
  modalidade_cartao?: string | null;
  status?: string | null;
}

export interface Parada {
  id: number;
  venda_id: number;
  ordem: number;
  endereco: string;
  status: string;
  cliente_nome?: string;
  cliente_telefone?: string;
  cliente_celular?: string;
  observacoes?: string;
  data_entrega?: string;
  forma_pagamento?: string;
  valor_venda?: number | null;
  pagamentos?: PagamentoEntrega[];
}

export interface Rota {
  id: number;
  numero: string;
  status: string;
  paradas: Parada[];
}

export interface VendaDetalhes {
  id: number;
  cliente?: {
    nome?: string;
    telefone?: string;
    celular?: string;
  };
  data_venda?: string;
  forma_pagamento?: string;
  status_pagamento?: string;
  endereco_entrega?: string;
  observacoes_entrega?: string;
  total?: number;
  valor_total?: number;
  pagamentos?: PagamentoEntrega[];
  itens?: Array<{
    produto_nome?: string;
    servico_descricao?: string;
    quantidade?: number;
    subtotal?: number;
    preco_unitario?: number;
  }>;
}

export type FormaRecebimento = "pix" | "cartao_debito" | "cartao_credito";

type FontePagamentoEntrega = {
  forma_pagamento?: string;
  valor_venda?: number | null;
  valor_total?: number | null;
  total?: number | null;
  pagamentos?: PagamentoEntrega[];
};

export interface InstrucaoPagamentoEntrega {
  chave: string;
  resumo: string;
  alerta?: string;
  complemento?: string;
}

function normalizarPagamento(valor?: string | null) {
  return String(valor || "")
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function detalhesFormaPagamento(pagamento: PagamentoEntrega) {
  const modalidade = normalizarPagamento(pagamento.modalidade_cartao);
  const identificacao = normalizarPagamento(pagamento.forma_pagamento);
  const nome = String(pagamento.forma_pagamento || "").trim();
  const ehDinheiro = identificacao.includes("dinheiro");
  const ehCredito =
    modalidade === "credito" ||
    (identificacao.includes("cartao") && identificacao.includes("credito"));
  const ehDebito =
    modalidade === "debito" ||
    (identificacao.includes("cartao") && identificacao.includes("debito"));
  const ehCartao = identificacao.includes("cartao") || ehCredito || ehDebito;
  const ehPix = identificacao.includes("pix");

  return {
    ehDinheiro,
    ehCartao,
    rotulo: ehCredito
      ? "CARTÃO DE CRÉDITO"
      : ehDebito
        ? "CARTÃO DE DÉBITO"
        : nome
          ? nome.toLocaleUpperCase("pt-BR")
          : "NÃO INFORMADA",
    icone: ehDinheiro ? "💵" : ehCartao ? "💳" : ehPix ? "📱" : "💰",
  };
}

export function montarInstrucoesPagamentoEntrega(
  fonte: FontePagamentoEntrega = {},
): InstrucaoPagamentoEntrega[] {
  const totalVenda = Number(fonte.valor_venda ?? fonte.valor_total ?? fonte.total ?? 0);
  const pagamentos = fonte.pagamentos?.length
    ? fonte.pagamentos
    : fonte.forma_pagamento
      ? [{ forma_pagamento: fonte.forma_pagamento, valor: totalVenda }]
      : [];

  if (!pagamentos.length) {
    return [
      {
        chave: "nao-informada",
        resumo: "⚠️ FORMA NÃO INFORMADA",
        alerta: "CONFIRME O PAGAMENTO COM A LOJA",
      },
    ];
  }

  return pagamentos.map((pagamento, index) => {
    const { ehDinheiro, ehCartao, icone, rotulo } = detalhesFormaPagamento(pagamento);
    const valor = Number(pagamento.valor ?? 0);
    const troco = Number(pagamento.troco ?? 0);
    const valorRecebido = Number(pagamento.valor_recebido ?? 0);
    const parcelas = Number(pagamento.numero_parcelas ?? 1);
    const sufixoParcelas = ehCartao && parcelas > 1 ? ` (${parcelas}x)` : "";
    const resumoValor = valor > 0 ? ` — ${formatarMoeda(valor)}` : "";

    if (ehDinheiro && troco > 0.005) {
      const recebido = valorRecebido > 0 ? valorRecebido : valor + troco;
      return {
        chave: `${rotulo}-${index}`,
        resumo: `${icone} ${rotulo}${resumoValor}`,
        alerta: `LEVAR TROCO: ${formatarMoeda(troco)}`,
        complemento:
          recebido > 0 ? `Cliente paga com ${formatarMoeda(recebido)}` : undefined,
      };
    }

    return {
      chave: `${rotulo}-${index}`,
      resumo: `${icone} ${rotulo}${sufixoParcelas}${resumoValor}`,
      alerta: ehCartao ? "LEVAR MÁQUINA DE CARTÃO" : undefined,
      complemento:
        ehDinheiro && valorRecebido > 0 ? "Cliente informou valor exato (sem troco)" : undefined,
    };
  });
}

export function reordenarParadasPorPosicao(
  paradas: Parada[],
  paradaId: number,
  novaPosicao: number,
) {
  const ordenadas = [...paradas].sort((a, b) => a.ordem - b.ordem);
  const indiceAtual = ordenadas.findIndex((parada) => parada.id === paradaId);

  if (indiceAtual < 0) {
    return null;
  }

  const posicaoClamped = Math.max(1, Math.min(novaPosicao, ordenadas.length));
  const [paradaMovida] = ordenadas.splice(indiceAtual, 1);
  ordenadas.splice(posicaoClamped - 1, 0, paradaMovida);

  return ordenadas;
}

export function rotaPermiteReordenacao(status?: string | null) {
  return !!status && !["concluida", "cancelada"].includes(status);
}

export function extrairPosicaoOrdem(texto: string) {
  const match = texto.match(/\d+/);
  return match ? Number.parseInt(match[0], 10) : Number.NaN;
}

export function obterMensagemErro(error: unknown, fallback: string) {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const data = error.response.data;
    if (data && typeof data === "object" && "detail" in data) {
      const detail = data.detail;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
    }
  }
  return fallback;
}

export function abrirMapa(endereco: string) {
  const enderecoMaps = limparEnderecoParaMaps(endereco) || endereco;
  const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(enderecoMaps)}`;
  Linking.openURL(url).catch(() =>
    Alert.alert("Erro", "Não foi possível abrir o mapa."),
  );
}

export function ligar(telefone?: string | null) {
  if (!telefone) return;
  const digits = telefone.replaceAll(/\D/g, "");
  Linking.openURL(`tel:${digits}`).catch(() =>
    Alert.alert("Erro", "Não foi possível ligar."),
  );
}

export async function obterLocalizacaoOpcional(): Promise<{
  latitude?: number;
  longitude?: number;
}> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== "granted") {
      return {};
    }

    const posicao = await Promise.race([
      Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      }),
      new Promise<null>((resolve) => {
        setTimeout(() => resolve(null), 3500);
      }),
    ]);

    if (!posicao) {
      return {};
    }

    return {
      latitude: posicao.coords.latitude,
      longitude: posicao.coords.longitude,
    };
  } catch {
    return {};
  }
}

export const STATUS_BADGE: Record<
  string,
  { label: string; color: string; bg: string }
> = {
  pendente: { label: "Pendente", color: "#92400e", bg: "#fef3c7" },
  entregue: { label: "Entregue ✓", color: "#065f46", bg: "#d1fae5" },
  nao_entregue: { label: "Não entregue ✗", color: "#7f1d1d", bg: "#fee2e2" },
};
