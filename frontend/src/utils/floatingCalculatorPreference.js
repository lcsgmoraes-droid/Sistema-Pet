export const FLOATING_CALCULATOR_ENABLED_KEY = "floating_calculator_enabled";
export const FLOATING_CALCULATOR_PREF_EVENT = "floating-calculator-preference-changed";

function getBrowserStorage() {
  if (typeof window === "undefined") return null;

  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function getBrowserEventTarget() {
  if (typeof window === "undefined") return null;
  return window;
}

function createPreferenceEvent(enabled) {
  const detail = { enabled };

  if (typeof CustomEvent === "function") {
    return new CustomEvent(FLOATING_CALCULATOR_PREF_EVENT, { detail });
  }

  return {
    type: FLOATING_CALCULATOR_PREF_EVENT,
    detail,
  };
}

export function isFloatingCalculatorEnabled(storage = getBrowserStorage()) {
  try {
    return storage?.getItem(FLOATING_CALCULATOR_ENABLED_KEY) === "true";
  } catch {
    return false;
  }
}

export function setFloatingCalculatorEnabled(
  enabled,
  { storage = getBrowserStorage(), eventTarget = getBrowserEventTarget() } = {},
) {
  const nextEnabled = enabled === true;

  try {
    storage?.setItem(FLOATING_CALCULATOR_ENABLED_KEY, nextEnabled ? "true" : "false");
  } catch {
    // Se o navegador bloquear localStorage, mantemos a tela funcionando sem persistir.
  }

  eventTarget?.dispatchEvent?.(createPreferenceEvent(nextEnabled));
  return nextEnabled;
}
