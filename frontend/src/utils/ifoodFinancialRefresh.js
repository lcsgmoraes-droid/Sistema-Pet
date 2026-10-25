export const IFOOD_FINANCIAL_UPDATED_EVENT = "corepet:ifood-financial-updated";
export const IFOOD_FINANCIAL_REFRESH_MS = 30_000;

export function notifyIfoodFinancialUpdated() {
  const target = typeof window === "undefined" ? null : window;
  const EventClass = target?.Event || globalThis.Event;
  if (typeof EventClass === "function")
    target?.dispatchEvent?.(new EventClass(IFOOD_FINANCIAL_UPDATED_EVENT));
}

/** Rele somente o ERP. Nunca consulta iFood nem grava venda, caixa ou estoque. */
export function scheduleIfoodFinancialReportRefresh(
  onRefresh,
  {
    enabled = true,
    intervalMs = IFOOD_FINANCIAL_REFRESH_MS,
    documentTarget = typeof document === "undefined" ? null : document,
    windowTarget = typeof window === "undefined" ? null : window,
    setTimer = (callback, delay) => setTimeout(callback, delay),
    clearTimer = (timer) => clearTimeout(timer),
    now = () => Date.now(),
  } = {},
) {
  if (!enabled) return () => {};
  let stopped = false;
  let pending = false;
  let timer = null;
  let lastResumeAt = -Infinity;
  const visible = () =>
    !documentTarget || (!documentTarget.hidden && documentTarget.visibilityState !== "hidden");
  function schedule() {
    if (stopped) return;
    timer = setTimer(() => {
      timer = null;
      refresh();
      schedule();
    }, intervalMs);
  }
  function refresh() {
    if (stopped || pending || !visible()) return;
    pending = true;
    Promise.resolve()
      .then(() => (stopped ? undefined : onRefresh()))
      .catch(() => {})
      .finally(() => {
        pending = false;
      });
  }
  function resume() {
    if (!visible()) return;
    const current = now();
    if (current - lastResumeAt < 1_000) return;
    lastResumeAt = current;
    refresh();
  }
  documentTarget?.addEventListener("visibilitychange", resume);
  windowTarget?.addEventListener("focus", resume);
  windowTarget?.addEventListener(IFOOD_FINANCIAL_UPDATED_EVENT, refresh);
  schedule();
  return () => {
    stopped = true;
    if (timer !== null) clearTimer(timer);
    documentTarget?.removeEventListener("visibilitychange", resume);
    windowTarget?.removeEventListener("focus", resume);
    windowTarget?.removeEventListener(IFOOD_FINANCIAL_UPDATED_EVENT, refresh);
  };
}
