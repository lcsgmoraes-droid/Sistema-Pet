import js from "@eslint/js";
import globals from "globals";

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
    files: [
      "scripts/**/*.{js,mjs,cjs}",
      "src/api/**/*.{js,mjs,cjs}",
      "src/helpers/**/*.{js,mjs,cjs}",
      "src/utils/**/*.{js,mjs,cjs}",
    ],
    languageOptions: {
      ecmaVersion: "latest",
      globals: sharedGlobals,
      sourceType: "module",
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
    },
  },
];
