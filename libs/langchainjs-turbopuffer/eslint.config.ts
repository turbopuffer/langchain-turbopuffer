import js from "@eslint/js";
import tseslint from "typescript-eslint";
import prettierConfig from "eslint-config-prettier";
import noInstanceofPlugin from "eslint-plugin-no-instanceof";
import importPlugin from "eslint-plugin-import";

export default tseslint.config(
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/*.js",
      "**/*.cjs",
      "**/*.mjs",
      "**/*.d.ts",
      "**/eslint.config.ts",
      "**/tsdown.config.ts",
      "**/vitest.config.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  prettierConfig,
  {
    name: "base",
    plugins: {
      "@typescript-eslint": tseslint.plugin,
      "no-instanceof": noInstanceofPlugin,
      import: importPlugin,
    },
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        project: "./tsconfig.json",
        tsconfigRootDir: process.cwd(),
      },
      globals: {
        process: "readonly",
        console: "readonly",
      },
    },
    files: ["**/*.ts"],
    rules: {
      "@typescript-eslint/explicit-module-boundary-types": "off",
      "@typescript-eslint/no-shadow": "off",
      "@typescript-eslint/no-empty-interface": "off",
      "@typescript-eslint/no-use-before-define": [
        "error",
        { functions: false },
      ],
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          args: "none",
          vars: "all",
          varsIgnorePattern: "^_",
          argsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
          destructuredArrayIgnorePattern: "^_",
          ignoreRestSiblings: true,
        },
      ],
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-misused-promises": "error",
      "@typescript-eslint/no-this-alias": "off",
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/ban-ts-comment": "error",
      "@typescript-eslint/no-non-null-assertion": "off",
      "@typescript-eslint/no-wrapper-object-types": "off",
      "@typescript-eslint/no-unsafe-function-type": "off",
      "@typescript-eslint/no-empty-object-type": "off",
      "@typescript-eslint/no-empty-function": "off",

      "import/extensions": ["error", "ignorePackages"],
      "import/no-extraneous-dependencies": [
        "error",
        { devDependencies: ["**/*.test.ts", "**/*.test-d.ts", "**/*.spec.ts"] },
      ],
      "import/no-unresolved": "off",
      "import/prefer-default-export": "off",
      "import/no-cycle": "off",
      "import/no-relative-packages": "off",

      "no-instanceof/no-instanceof": "error",
      "no-process-env": "error",
      "no-void": "error",
      "no-param-reassign": "error",
      "no-constructor-return": "error",
      "no-constant-condition": "error",
      "default-case": "error",
      "prefer-template": "error",
      "dot-notation": "error",
      "keyword-spacing": "error",
      "no-empty": ["error", { allowEmptyCatch: true }],
      "new-cap": ["error", { properties: false, capIsNew: false }],
    },
  },
  {
    name: "test",
    files: ["**/*.test.ts", "**/*.test-d.ts", "**/*.spec.ts"],
    rules: {
      "@typescript-eslint/no-unused-vars": "off",
      "@typescript-eslint/no-floating-promises": "off",
      "@typescript-eslint/no-misused-promises": "off",
      "no-process-env": "off",
      "import/no-extraneous-dependencies": "off",
    },
  }
);
