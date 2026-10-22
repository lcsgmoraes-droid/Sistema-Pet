// Somente invalida consultas locais; a autoridade de preço e vigência é a API.
export const IFOOD_PROMOTION_MAX_TIMEOUT_MS = 2_147_483_647;
export const IFOOD_PROMOTION_BOUNDARY_GRACE_MS = 100;
export const IFOOD_PROMOTION_RETRY_DELAYS_MS = [5_000, 15_000, 60_000];
const RESUME_DEDUPE_MS = 1_000;

function timestamp(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Agenda a próxima virada pelo intervalo informado pelo servidor, sem depender
 * de o relógio do computador coincidir com o backend. `activity` é mantido pelo
 * hook entre respostas para deduplicar foco/visibilidade e preservar a âncora
 * quando uma gravação desabilita temporariamente o agendamento.
 *
 * Dependências injetáveis permitem testar suspensão, desmontagem e falhas sem
 * aguardar tempo real ou acrescentar uma biblioteca de testes ao frontend.
 */
export function scheduleIfoodPromotionRefresh(
  metadata,
  onRefresh,
  {
    enabled = true,
    activity = {},
    now = () => performance.now(),
    setTimer = (callback, delay) => window.setTimeout(callback, delay),
    clearTimer = (timer) => window.clearTimeout(timer),
    documentTarget = typeof document === "undefined" ? null : document,
    windowTarget = typeof window === "undefined" ? null : window,
  } = {},
) {
  const evaluated = timestamp(metadata?.evaluated_at);
  const nextChange = timestamp(metadata?.next_price_change_at);
  const anchorKey = `${metadata?.evaluated_at || ""}|${metadata?.next_price_change_at || ""}`;
  if (activity.anchorKey !== anchorKey) {
    activity.anchorKey = anchorKey;
    activity.receivedAt = now();
    activity.boundaryReached = false;
    activity.attempts = 0;
    activity.retryDueAt = null;
  }
  if (!enabled) return () => {};

  // A API só deve anunciar uma próxima virada estritamente após evaluated_at.
  // Um valor vencido/inválido nunca deve gerar um laço de chamadas imediatas.
  const deadline =
    evaluated !== null && nextChange !== null && nextChange > evaluated
      ? activity.receivedAt + (nextChange - evaluated) + IFOOD_PROMOTION_BOUNDARY_GRACE_MS
      : null;
  let stopped = false;
  let timer = null;
  const visible = () =>
    !documentTarget || (!documentTarget.hidden && documentTarget.visibilityState !== "hidden");

  function clearScheduled() {
    if (timer !== null) clearTimer(timer);
    timer = null;
  }

  function notify() {
    if (stopped || !visible()) return;
    try {
      // O chamador controla loading/erro. Falha ou ausência de nova resposta
      // mantém apenas as tentativas limitadas abaixo, sem rejection órfã.
      Promise.resolve(onRefresh()).catch(() => {});
    } catch {
      // Uma falha síncrona segue o mesmo retry limitado da consulta assíncrona.
    }
  }

  function scheduleRetry() {
    if (stopped || activity.retryDueAt === null) return;
    const remaining = activity.retryDueAt - now();
    timer = setTimer(
      () => {
        timer = null;
        if (stopped) return;
        if (now() < activity.retryDueAt) scheduleRetry();
        else attemptRefresh();
      },
      Math.max(0, Math.min(remaining, IFOOD_PROMOTION_MAX_TIMEOUT_MS)),
    );
  }

  function attemptRefresh() {
    if (stopped || !visible()) return;
    const attempt = activity.attempts;
    if (attempt > IFOOD_PROMOTION_RETRY_DELAYS_MS.length) return;
    activity.attempts = attempt + 1;
    activity.retryDueAt =
      attempt < IFOOD_PROMOTION_RETRY_DELAYS_MS.length
        ? now() + IFOOD_PROMOTION_RETRY_DELAYS_MS[attempt]
        : null;
    notify();
    scheduleRetry();
  }

  function crossBoundary() {
    activity.boundaryReached = true;
    clearScheduled();
    attemptRefresh();
  }

  function scheduleBoundary() {
    if (stopped || deadline === null) return;
    const remaining = deadline - now();
    timer = setTimer(
      () => {
        timer = null;
        if (stopped) return;
        if (now() < deadline) scheduleBoundary();
        else crossBoundary();
      },
      Math.max(0, Math.min(remaining, IFOOD_PROMOTION_MAX_TIMEOUT_MS)),
    );
  }

  function resume() {
    if (stopped || !visible()) return;
    const instant = now();
    if (instant - (activity.lastResumeAt ?? -Infinity) < RESUME_DEDUPE_MS) return;
    activity.lastResumeAt = instant;
    if (deadline !== null && instant >= deadline) {
      // Retomar a aba é uma nova oportunidade explícita de recuperar a leitura,
      // inclusive depois de esgotadas as tentativas de uma falha anterior.
      activity.attempts = 0;
      activity.retryDueAt = null;
      crossBoundary();
      return;
    }
    notify();
    // Antes da virada, o timer existente continua sendo a recuperação. Sem
    // virada pendente, permitir retry após retomar uma aba com consulta falha.
    if (deadline === null) {
      clearScheduled();
      activity.boundaryReached = true;
      activity.attempts = 1;
      activity.retryDueAt = now() + IFOOD_PROMOTION_RETRY_DELAYS_MS[0];
      scheduleRetry();
    }
  }

  documentTarget?.addEventListener("visibilitychange", resume);
  windowTarget?.addEventListener("focus", resume);
  if (activity.boundaryReached) {
    if (activity.attempts === 0) crossBoundary();
    else scheduleRetry();
  } else scheduleBoundary();

  return () => {
    stopped = true;
    clearScheduled();
    documentTarget?.removeEventListener("visibilitychange", resume);
    windowTarget?.removeEventListener("focus", resume);
  };
}
