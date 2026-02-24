import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommendedTypeChecked],
    files: ["**/*.ts"],
    languageOptions: {
      ecmaVersion: 2022,
      parserOptions: {
        project: true,
      },
    },
    rules: {
      complexity: ["error", { max: 30 }],
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@sentry/react", "@sentry/react/*"],
              message:
                "Use @sentry/node for Node.js backend. @sentry/react is for frontend only.",
            },
          ],
        },
      ],
      "@typescript-eslint/no-deprecated": "error",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  }
);
