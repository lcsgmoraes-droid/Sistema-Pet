const uiDebugEnabled =
  import.meta.env.DEV || import.meta.env.VITE_DEBUG_UI === "true";

export function debugLog(...args) {
  if (uiDebugEnabled) {
    console.log(...args);
  }
}

export function debugWarn(...args) {
  if (uiDebugEnabled) {
    console.warn(...args);
  }
}
