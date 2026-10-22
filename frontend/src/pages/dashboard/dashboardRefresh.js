export const DASHBOARD_REFRESH_INTERVAL_MS = 30000;

export function iniciarAtualizacaoDashboard({
  atualizar,
  documentTarget = globalThis.document,
  windowTarget = globalThis.window,
  setTimer = globalThis.setInterval,
  clearTimer = globalThis.clearInterval,
}) {
  let ativo = true;
  let emAndamento = false;

  const atualizarSeVisivel = async () => {
    if (!ativo || emAndamento || documentTarget?.visibilityState !== "visible") return;
    emAndamento = true;
    try {
      await atualizar();
    } catch {
      // Uma tentativa que falha nao interrompe as atualizacoes seguintes.
    } finally {
      emAndamento = false;
    }
  };

  const timer = setTimer(atualizarSeVisivel, DASHBOARD_REFRESH_INTERVAL_MS);
  windowTarget?.addEventListener?.("focus", atualizarSeVisivel);
  windowTarget?.addEventListener?.("online", atualizarSeVisivel);
  documentTarget?.addEventListener?.("visibilitychange", atualizarSeVisivel);

  return () => {
    if (!ativo) return;
    ativo = false;
    clearTimer(timer);
    windowTarget?.removeEventListener?.("focus", atualizarSeVisivel);
    windowTarget?.removeEventListener?.("online", atualizarSeVisivel);
    documentTarget?.removeEventListener?.("visibilitychange", atualizarSeVisivel);
  };
}
