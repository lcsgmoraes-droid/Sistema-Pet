import { Pedido } from "../../../types";

export type StatusConfig = {
  cor: string;
  corTexto: string;
  label: string;
  emoji: string;
  icone: string;
};

export type EntregaStatusConfig = {
  label: string;
  cor: string;
};

export type PedidoItemResumo = NonNullable<Pedido["itens"]>[number];

export const STATUS_CONFIG: Record<string, StatusConfig> = {
  pendente: {
    cor: "#FEF3C7",
    corTexto: "#78350F",
    label: "Aguardando pagamento",
    emoji: "⏳",
    icone: "time-outline",
  },
  pago: {
    cor: "#D1FAE5",
    corTexto: "#065F46",
    label: "Pago",
    emoji: "💳",
    icone: "checkmark-circle-outline",
  },
  em_preparo: {
    cor: "#DBEAFE",
    corTexto: "#1E40AF",
    label: "Em preparo",
    emoji: "📦",
    icone: "construct-outline",
  },
  pronto: {
    cor: "#D1FAE5",
    corTexto: "#065F46",
    label: "Pronto para retirada",
    emoji: "🎉",
    icone: "bag-check-outline",
  },
  entregue: {
    cor: "#F3F4F6",
    corTexto: "#374151",
    label: "Entregue",
    emoji: "📬",
    icone: "home-outline",
  },
  aprovado: {
    cor: "#D1FAE5",
    corTexto: "#065F46",
    label: "Confirmado",
    emoji: "✅",
    icone: "checkmark-done-outline",
  },
  finalizada: {
    cor: "#D1FAE5",
    corTexto: "#065F46",
    label: "Pago",
    emoji: "✅",
    icone: "checkmark-done-outline",
  },
  pago_nf: {
    cor: "#D1FAE5",
    corTexto: "#065F46",
    label: "Pago",
    emoji: "✅",
    icone: "receipt-outline",
  },
  baixa_parcial: {
    cor: "#DBEAFE",
    corTexto: "#1E40AF",
    label: "Parcial",
    emoji: "✅",
    icone: "checkmark-done-outline",
  },
  cancelado: {
    cor: "#FEE2E2",
    corTexto: "#991B1B",
    label: "Cancelado",
    emoji: "❌",
    icone: "close-circle-outline",
  },
  cancelada: {
    cor: "#FEE2E2",
    corTexto: "#991B1B",
    label: "Cancelado",
    emoji: "❌",
    icone: "close-circle-outline",
  },
  finalizada_devolucao: {
    cor: "#FFEDD5",
    corTexto: "#9A3412",
    label: "Dev. parcial",
    emoji: "↩️",
    icone: "return-up-back-outline",
  },
  finalizada_devolucao_parcial: {
    cor: "#FFEDD5",
    corTexto: "#9A3412",
    label: "Dev. parcial",
    emoji: "↩️",
    icone: "return-up-back-outline",
  },
  finalizada_devolucao_total: {
    cor: "#F3F4F6",
    corTexto: "#374151",
    label: "Devolvida",
    emoji: "↩️",
    icone: "return-up-back-outline",
  },
  devolvida_total: {
    cor: "#F3F4F6",
    corTexto: "#374151",
    label: "Devolvida",
    emoji: "↩️",
    icone: "return-up-back-outline",
  },
  criado: {
    cor: "#E0E7FF",
    corTexto: "#3730A3",
    label: "Recebido",
    emoji: "🛍️",
    icone: "receipt-outline",
  },
  desconhecido: {
    cor: "#F3F4F6",
    corTexto: "#374151",
    label: "Em processamento",
    emoji: "•",
    icone: "ellipse-outline",
  },
};

export const STATUS_ENTREGA: Record<string, EntregaStatusConfig> = {
  pendente: { label: "Despacho pendente", cor: "#F59E0B" },
  pronto: { label: "Pronto para retirada", cor: "#10B981" },
  em_andamento: { label: "🛵 Entregador a caminho", cor: "#3B82F6" },
  em_rota: { label: "🛵 Em rota", cor: "#3B82F6" },
  entregue: { label: "✅ Entregue", cor: "#10B981" },
};

export const CANAL_LABELS: Record<string, string> = {
  ecommerce: "Ecommerce",
  app: "App mobile",
  loja_fisica: "Loja fisica / ERP",
  mercado_livre: "Mercado Livre",
  shopee: "Shopee",
  amazon: "Amazon",
};

export const PENDING_ORDER_POLL_MS = 12_000;

export function safeText(value: unknown, fallback = ""): string {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return fallback;
  return String(value);
}

export function getPedidoStatusKey(pedido?: Pedido | null): string {
  const status = safeText(pedido?.status, "desconhecido").trim().toLowerCase();
  return status || "desconhecido";
}

export function getPedidoItens(pedido?: Pedido | null): PedidoItemResumo[] {
  return Array.isArray(pedido?.itens)
    ? pedido.itens.filter(
        (item): item is PedidoItemResumo =>
          !!item && typeof item === "object",
      )
    : [];
}

export function getCanalLabel(pedido?: Pedido | null): string {
  if (pedido?.canal_label) return safeText(pedido.canal_label, "Ecommerce");
  const canal = safeText(pedido?.canal || pedido?.origem, "ecommerce")
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, "_");
  return CANAL_LABELS[canal] || canal.replace(/_/g, " ") || "Ecommerce";
}

export function getEntregaStatusConfig(
  pedido?: Pedido | null,
): EntregaStatusConfig | null {
  const statusEntrega = safeText(pedido?.status_entrega).trim().toLowerCase();
  if (!statusEntrega) return null;

  const retiradaNaLoja = !pedido?.tem_entrega && !!pedido?.tipo_retirada;
  if (pedido?.tem_entrega && statusEntrega === "entregue") {
    return { label: "Compra com entrega", cor: "#10B981" };
  }
  if (retiradaNaLoja && statusEntrega === "pendente") {
    return { label: "A retirar", cor: "#F59E0B" };
  }
  if (retiradaNaLoja && statusEntrega === "pronto") {
    return { label: "Pronto para retirada", cor: "#10B981" };
  }
  if (retiradaNaLoja && statusEntrega === "entregue") {
    return { label: "Retirado", cor: "#10B981" };
  }

  return STATUS_ENTREGA[statusEntrega] || null;
}

export function hasOpenFulfillmentOrder(pedido?: Pedido | null): boolean {
  if (!pedido || pedido.tem_entrega) return false;
  const statusEntrega = safeText(pedido.status_entrega).trim().toLowerCase();
  return Boolean(pedido.tipo_retirada) && ["pendente", "pronto"].includes(statusEntrega);
}

export function getPedidoRenderKey(
  pedido?: Pedido | null,
  index?: number,
): string {
  if (pedido?.historico_id) return safeText(pedido.historico_id);
  if (pedido?.pedido_id) return `pedido:${safeText(pedido.pedido_id)}`;
  if (pedido?.venda_id) return `venda:${safeText(pedido.venda_id)}`;
  if (pedido?.numero) return `numero:${safeText(pedido.numero)}`;
  return `pedido-sem-id-${index ?? "item"}`;
}

export function getPedidoTitulo(pedido?: Pedido | null): string {
  const numero = pedido?.pedido_id || pedido?.numero || pedido?.venda_id;
  if (!numero) return "Pedido";
  return `#${safeText(numero).slice(-8).toUpperCase()}`;
}
