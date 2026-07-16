type NotificationData = Record<string, unknown> | null | undefined;

type NavigationTarget = {
  route: string;
  params?: Record<string, unknown>;
};

function toPositiveInteger(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isInteger(value) && value > 0 ? value : null;
  }
  if (typeof value !== "string") return null;

  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) return null;

  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

export function stockNotificationToProductId(data: NotificationData): number | null {
  if (!data) return null;
  const isStockWaitlist =
    data.source === "stock_waitlist" &&
    (!data.kind || data.kind === "stock_available");
  const isLegacyNotifyMe = !data.source && data.type === "stock_available";
  if (!isStockWaitlist && !isLegacyNotifyMe) return null;

  return toPositiveInteger(data.produto_id) ?? toPositiveInteger(data.product_id);
}

export function recurrenceNotificationToProductId(
  data: NotificationData,
): number | null {
  if (
    !data ||
    data.source !== "product_recurrence" ||
    data.kind !== "repurchase_due"
  ) {
    return null;
  }
  return toPositiveInteger(data.produto_id) ?? toPositiveInteger(data.product_id);
}

export function appointmentNotificationTarget(data: NotificationData): NavigationTarget | null {
  if (!data || data.source !== "appointment_reminder") return null;

  const module = String(data.module || "");
  const kind = String(data.kind || "");
  if (module === "banho_tosa" || kind === "banho_tosa_agendamento") {
    return { route: "Pets", params: { screen: "BanhoTosa" } };
  }
  if (module === "veterinario" || kind === "veterinario_agendamento") {
    return { route: "Pets", params: { screen: "Veterinario" } };
  }
  return null;
}

export function campaignNotificationTarget(data: NotificationData): NavigationTarget | null {
  if (!data || data.source !== "campaign") return null;

  const kind = String(data.kind || "");
  const target = String(data.target || "");
  if (target === "banho_tosa" || kind === "banho_tosa_retorno") {
    return { route: "Pets", params: { screen: "BanhoTosa" } };
  }

  if (target === "coupons") {
    return { route: "Beneficios", params: { screen: "MeusCupons" } };
  }
  if (target === "benefits") {
    return { route: "Beneficios", params: { screen: "MeusBeneficios" } };
  }

  if ([
    "birthday_customer",
    "birthday_pet",
    "welcome_app",
    "welcome_ecommerce",
    "inactivity",
    "quick_repurchase",
    "monthly_highlight",
  ].includes(kind)) {
    return { route: "Beneficios", params: { screen: "MeusCupons" } };
  }

  return { route: "Beneficios", params: { screen: "MeusBeneficios" } };
}
