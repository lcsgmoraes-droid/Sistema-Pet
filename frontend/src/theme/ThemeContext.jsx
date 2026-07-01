import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  THEMES,
  applyThemeToDocument,
  getStoredTheme,
  getSystemTheme,
  isThemeValue,
  persistTheme,
  resolveInitialTheme,
  toggleThemeValue,
} from "./themePreference";

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => resolveInitialTheme());
  const [hasUserPreference, setHasUserPreference] = useState(() => Boolean(getStoredTheme()));

  useEffect(() => {
    applyThemeToDocument(document, theme);
  }, [theme]);

  useEffect(() => {
    if (hasUserPreference) {
      persistTheme(theme);
    }
  }, [hasUserPreference, theme]);

  useEffect(() => {
    if (hasUserPreference || typeof window === "undefined" || !window.matchMedia) return undefined;

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => setThemeState(getSystemTheme(window));

    mediaQuery.addEventListener?.("change", handleChange);
    mediaQuery.addListener?.(handleChange);

    return () => {
      mediaQuery.removeEventListener?.("change", handleChange);
      mediaQuery.removeListener?.(handleChange);
    };
  }, [hasUserPreference]);

  const setTheme = useCallback((nextTheme) => {
    setThemeState((currentTheme) => {
      const resolved = typeof nextTheme === "function" ? nextTheme(currentTheme) : nextTheme;
      return isThemeValue(resolved) ? resolved : currentTheme;
    });
    setHasUserPreference(true);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((currentTheme) => toggleThemeValue(currentTheme));
  }, [setTheme]);

  const value = useMemo(
    () => ({
      isDark: theme === THEMES.DARK,
      setTheme,
      theme,
      toggleTheme,
    }),
    [setTheme, theme, toggleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used inside ThemeProvider");
  }
  return context;
}
