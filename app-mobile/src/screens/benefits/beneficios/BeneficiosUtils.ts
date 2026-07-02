export interface RankingThresholds {
  silver_min_spent: number;
  silver_min_purchases: number;
  silver_min_months: number;
  gold_min_spent: number;
  gold_min_purchases: number;
  gold_min_months: number;
  diamond_min_spent: number;
  diamond_min_purchases: number;
  diamond_min_months: number;
  platinum_min_spent: number;
  platinum_min_purchases: number;
  platinum_min_months: number;
}

export interface ExtratoCashback {
  saldo_atual: number;
  transacoes: {
    id: number;
    amount: number;
    tx_type: string; // 'credit' | 'debit' | 'expired'
    source_type: string;
    description: string | null;
    created_at: string | null;
    expires_at: string | null;
    expired: boolean;
  }[];
}

export interface SugestaoCashback {
  saldo_disponivel: number;
  ticket_sugerido: number;
  valor_com_cashback: number;
  economia: number;
  proximo_expirando: {
    amount: number;
    expires_at: string;
    dias_restantes: number;
  } | null;
}

export interface Beneficios {
  cashback: { saldo: number };
  carimbos: {
    total_geral: number;
    carimbos_no_cartao: number;
    carimbos_ativos_brutos: number;
    carimbos_comprometidos_total: number;
    carimbos_convertidos: number;
    carimbos_em_debito: number;
    meta: number;
    min_purchase_value: number;
  };
  ranking: {
    nivel: string;
    total_spent: number;
    total_purchases: number;
    thresholds: RankingThresholds;
  };
  cupons: {
    id: number | string;
    code: string;
    coupon_type: string;
    discount_value: number | null;
    discount_percent: number | null;
    valid_until: string | null;
    expirado: boolean;
    min_purchase_value: number | null;
  }[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export const NIVEL_ORDEM = ["bronze", "silver", "gold", "diamond", "platinum"];

export const NIVEL_PT: Record<string, string> = {
  bronze: "Bronze",
  silver: "Prata",
  gold: "Ouro",
  diamond: "Diamante",
  platinum: "Platina",
};

export const NIVEL_COR: Record<string, string> = {
  bronze: "#CD7F32",
  silver: "#9CA3AF",
  gold: "#F59E0B",
  diamond: "#06B6D4",
  platinum: "#8B5CF6",
};

export const NIVEL_VANTAGENS: Record<string, string[]> = {
  bronze: [
    "Cashback básico em todas as compras",
    "Participa do Cartão Fidelidade",
    "Cupom de boas-vindas",
  ],
  silver: [
    "Cashback maior",
    "Participa de sorteios mensais",
    "Cupom de aniversário especial",
  ],
  gold: [
    "Cashback alto",
    "Sorteios com prêmios melhores",
    "Brinde mensal na loja",
  ],
  diamond: [
    "Cashback premium",
    "Sorteios exclusivos Diamante",
    "Ofertas antecipadas",
  ],
  platinum: [
    "Cashback máximo",
    "Sorteios exclusivos Platina",
    "Destaque do mês",
    "Atendimento prioritário",
  ],
};

export const THRESHOLD_KEY: Record<string, keyof RankingThresholds> = {
  silver: "silver_min_spent",
  gold: "gold_min_spent",
  diamond: "diamond_min_spent",
  platinum: "platinum_min_spent",
};

export const THRESHOLD_PURCHASES_KEY: Record<string, keyof RankingThresholds> = {
  silver: "silver_min_purchases",
  gold: "gold_min_purchases",
  diamond: "diamond_min_purchases",
  platinum: "platinum_min_purchases",
};

export const THRESHOLD_MONTHS_KEY: Record<string, keyof RankingThresholds> = {
  silver: "silver_min_months",
  gold: "gold_min_months",
  diamond: "diamond_min_months",
  platinum: "platinum_min_months",
};

export function brl(valor: number): string {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function numero(valor: unknown, fallback = 0): number {
  const n = Number(valor);
  return Number.isFinite(n) ? n : fallback;
}

export function inteiro(valor: unknown, fallback = 0): number {
  return Math.max(0, Math.trunc(numero(valor, fallback)));
}

export function nivelSeguro(nivel: unknown): string {
  const normalizado = String(nivel || "bronze").toLowerCase();
  return NIVEL_ORDEM.includes(normalizado) ? normalizado : "bronze";
}

export function normalizarBeneficios(raw: unknown): Beneficios {
  const payload = raw as any;
  const thresholds = payload?.ranking?.thresholds || {};
  const cuponsRaw = Array.isArray(payload?.cupons) ? payload.cupons : [];

  return {
    cashback: {
      saldo: numero(payload?.cashback?.saldo),
    },
    carimbos: {
      total_geral: inteiro(payload?.carimbos?.total_geral),
      carimbos_no_cartao: inteiro(payload?.carimbos?.carimbos_no_cartao),
      carimbos_ativos_brutos: inteiro(payload?.carimbos?.carimbos_ativos_brutos),
      carimbos_comprometidos_total: inteiro(
        payload?.carimbos?.carimbos_comprometidos_total,
      ),
      carimbos_convertidos: inteiro(payload?.carimbos?.carimbos_convertidos),
      carimbos_em_debito: inteiro(payload?.carimbos?.carimbos_em_debito),
      meta: Math.max(1, inteiro(payload?.carimbos?.meta, 10)),
      min_purchase_value: numero(payload?.carimbos?.min_purchase_value),
    },
    ranking: {
      nivel: nivelSeguro(payload?.ranking?.nivel),
      total_spent: numero(payload?.ranking?.total_spent),
      total_purchases: inteiro(payload?.ranking?.total_purchases),
      thresholds: {
        silver_min_spent: numero(thresholds.silver_min_spent, 300),
        silver_min_purchases: inteiro(thresholds.silver_min_purchases, 4),
        silver_min_months: inteiro(thresholds.silver_min_months, 2),
        gold_min_spent: numero(thresholds.gold_min_spent, 1000),
        gold_min_purchases: inteiro(thresholds.gold_min_purchases, 10),
        gold_min_months: inteiro(thresholds.gold_min_months, 4),
        diamond_min_spent: numero(thresholds.diamond_min_spent, 3000),
        diamond_min_purchases: inteiro(thresholds.diamond_min_purchases, 20),
        diamond_min_months: inteiro(thresholds.diamond_min_months, 6),
        platinum_min_spent: numero(thresholds.platinum_min_spent, 8000),
        platinum_min_purchases: inteiro(thresholds.platinum_min_purchases, 40),
        platinum_min_months: inteiro(thresholds.platinum_min_months, 10),
      },
    },
    cupons: cuponsRaw
      .map((c: any) => {
        const code = String(c?.code || c?.codigo || "").trim();
        if (!code) return null;
        return {
          id: inteiro(c?.id) || code,
          code,
          coupon_type: String(c?.coupon_type || c?.tipo_desconto || ""),
          discount_value:
            c?.discount_value != null
              ? numero(c.discount_value)
              : c?.valor_desconto != null
                ? numero(c.valor_desconto)
                : null,
          discount_percent:
            c?.discount_percent != null ? numero(c.discount_percent) : null,
          valid_until: c?.valid_until ?? null,
          expirado: Boolean(c?.expirado),
          min_purchase_value:
            c?.min_purchase_value != null
              ? numero(c.min_purchase_value)
              : c?.valor_minimo_pedido != null
                ? numero(c.valor_minimo_pedido)
                : null,
        };
      })
      .filter(Boolean) as Beneficios["cupons"],
  };
}

export function formatarDesconto(item: Beneficios["cupons"][number]): string {
  if (item.discount_percent != null)
    return `${item.discount_percent}% de desconto`;
  if (item.discount_value != null)
    return `R$ ${brl(item.discount_value)} de desconto`;
  return "Desconto especial";
}

export function diasRestantes(isoDate: string | null): string | null {
  if (!isoDate) return null;
  const diff = new Date(isoDate).getTime() - Date.now();
  const dias = Math.ceil(diff / (1000 * 60 * 60 * 24));
  if (dias < 0) return "Expirado";
  if (dias === 0) return "Expira hoje!";
  if (dias === 1) return "Expira amanhã";
  return `Expira em ${dias} dias`;
}

// ---------------------------------------------------------------------------
// Sub-componentes
// ---------------------------------------------------------------------------
