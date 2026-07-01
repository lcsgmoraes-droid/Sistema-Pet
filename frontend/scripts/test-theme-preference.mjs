import assert from "node:assert/strict";
import {
  applyThemeToDocument,
  getSystemTheme,
  persistTheme,
  resolveInitialTheme,
  THEME_STORAGE_KEY,
  toggleThemeValue,
} from "../src/theme/themePreference.js";

function createStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, value),
    removeItem: (key) => data.delete(key),
  };
}

function createWindow(matchesDark) {
  return {
    matchMedia: (query) => ({
      matches: query === "(prefers-color-scheme: dark)" ? matchesDark : false,
    }),
  };
}

function createDocument() {
  const classes = new Set();
  return {
    documentElement: {
      dataset: {},
      style: {},
      classList: {
        add: (value) => classes.add(value),
        remove: (value) => classes.delete(value),
        toggle: (value, force) => {
          if (force) {
            classes.add(value);
            return true;
          }
          classes.delete(value);
          return false;
        },
        contains: (value) => classes.has(value),
      },
    },
  };
}

assert.equal(getSystemTheme(createWindow(true)), "dark");
assert.equal(getSystemTheme(createWindow(false)), "light");
assert.equal(resolveInitialTheme(createWindow(true), createStorage()), "dark");
assert.equal(
  resolveInitialTheme(createWindow(false), createStorage({ [THEME_STORAGE_KEY]: "dark" })),
  "dark",
);
assert.equal(
  resolveInitialTheme(createWindow(true), createStorage({ [THEME_STORAGE_KEY]: "light" })),
  "light",
);
assert.equal(toggleThemeValue("light"), "dark");
assert.equal(toggleThemeValue("dark"), "light");

const storage = createStorage();
persistTheme("dark", storage);
assert.equal(storage.getItem(THEME_STORAGE_KEY), "dark");

const doc = createDocument();
applyThemeToDocument(doc, "dark");
assert.equal(doc.documentElement.classList.contains("dark"), true);
assert.equal(doc.documentElement.dataset.theme, "dark");
assert.equal(doc.documentElement.style.colorScheme, "dark");
applyThemeToDocument(doc, "light");
assert.equal(doc.documentElement.classList.contains("dark"), false);
assert.equal(doc.documentElement.dataset.theme, "light");
assert.equal(doc.documentElement.style.colorScheme, "light");

console.log("theme preference contract ok");
