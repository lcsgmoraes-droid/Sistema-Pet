type NotificationData = Record<string, unknown> | null | undefined;

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
