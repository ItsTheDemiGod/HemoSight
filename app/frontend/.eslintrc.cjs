/* The rule that matters here is react-hooks/exhaustive-deps, set to "error".
 *
 * The polling defect this configuration was added for lived behind an
 * `// eslint-disable-line react-hooks/exhaustive-deps` comment - which is what a
 * suppressed lint rule costs when there is no lint run to suppress it from. Both
 * remaining suppressions are now deliberate and carry a reason.
 */
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module",
                   ecmaFeatures: { jsx: true } },
  plugins: ["@typescript-eslint", "react-hooks", "react-refresh"],
  extends: ["eslint:recommended",
            "plugin:@typescript-eslint/recommended"],
  ignorePatterns: ["dist", "node_modules", "tools", "*.cjs", "*.config.ts"],
  rules: {
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "error",
    "no-unused-vars": "off",
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/no-explicit-any": "off",
    "no-empty": ["error", { allowEmptyCatch: true }],
  },
};
