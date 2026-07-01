export const THEME_STORAGE_KEY = "corepet_theme";

export const THEMES = Object.freeze({
  LIGHT: "light",
  DARK: "dark",
});

export function isThemeValue(value) {
  return value === THEMES.LIGHT || value === THEMES.DARK;
}

export function getSystemTheme(win = globalThis.window) {
  try {
    return win?.matchMedia?.("(prefers-color-scheme: dark)")?.matches ? THEMES.DARK : THEMES.LIGHT;
  } catch {
    return THEMES.LIGHT;
  }
}

export function getStoredTheme(storage = globalThis.localStorage) {
  try {
    const stored = storage?.getItem?.(THEME_STORAGE_KEY);
    return isThemeValue(stored) ? stored : null;
  } catch {
    return null;
  }
}

export function persistTheme(theme, storage = globalThis.localStorage) {
  if (!isThemeValue(theme)) return;

  try {
    storage?.setItem?.(THEME_STORAGE_KEY, theme);
  } catch {
    // Theme persistence must never block the app.
  }
}

export function resolveInitialTheme(win = globalThis.window, storage = globalThis.localStorage) {
  return getStoredTheme(storage) || getSystemTheme(win);
}

export function applyThemeToDocument(doc = globalThis.document, theme) {
  if (!doc?.documentElement || !isThemeValue(theme)) return;

  doc.documentElement.classList.toggle("dark", theme === THEMES.DARK);
  doc.documentElement.dataset.theme = theme;
  doc.documentElement.style.colorScheme = theme;
}

export function toggleThemeValue(theme) {
  return theme === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK;
}
