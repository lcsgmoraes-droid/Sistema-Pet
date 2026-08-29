const OPERATIONAL_DATE_TIME = /^\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2})/;

export function formatOperationalTime(value?: string | null): string {
  const match = String(value || "").match(OPERATIONAL_DATE_TIME);
  return match ? `${match[1]}:${match[2]}` : "--:--";
}
