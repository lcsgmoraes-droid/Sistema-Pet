import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

const sharedGlobals = {
  ...globals.browser,
  ...globals.node,
};

export default [
  {
    ignores: ["dist/**", "node_modules/**"],
  },
  js.configs.recommended,
  {
    files: ["scripts/**/*.{js,mjs,cjs}", "src/**/*.{js,jsx,mjs,cjs}"],
    languageOptions: {
      ecmaVersion: "latest",
      globals: sharedGlobals,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      sourceType: "module",
    },
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      "no-empty": ["error", { allowEmptyCatch: true }],
      "no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],
      "no-restricted-globals": [
        "error",
        { name: "confirm", message: "Use confirmarCorePet para manter o visual do sistema." },
        { name: "prompt", message: "Use perguntarCorePet para manter o visual do sistema." },
      ],
      "no-restricted-properties": [
        "error",
        { object: "window", property: "confirm", message: "Use confirmarCorePet." },
        { object: "window", property: "prompt", message: "Use perguntarCorePet." },
        { object: "globalThis", property: "confirm", message: "Use confirmarCorePet." },
        { object: "globalThis", property: "prompt", message: "Use perguntarCorePet." },
      ],
      "react-hooks/rules-of-hooks": "error",
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      globals: sharedGlobals,
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      sourceType: "module",
    },
    plugins: {
      "@typescript-eslint": tseslint.plugin,
      "react-hooks": reactHooks,
    },
    rules: {
      "no-empty": ["error", { allowEmptyCatch: true }],
      "no-undef": "off",
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],
      "no-restricted-globals": [
        "error",
        { name: "confirm", message: "Use confirmarCorePet para manter o visual do sistema." },
        { name: "prompt", message: "Use perguntarCorePet para manter o visual do sistema." },
      ],
      "no-restricted-properties": [
        "error",
        { object: "window", property: "confirm", message: "Use confirmarCorePet." },
        { object: "window", property: "prompt", message: "Use perguntarCorePet." },
        { object: "globalThis", property: "confirm", message: "Use confirmarCorePet." },
        { object: "globalThis", property: "prompt", message: "Use perguntarCorePet." },
      ],
      "react-hooks/rules-of-hooks": "error",
    },
  },
];
