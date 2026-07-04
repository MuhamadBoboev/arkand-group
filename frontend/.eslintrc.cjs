/**
 * FSD-границы слоёв (§3.2): импорт ТОЛЬКО вниз.
 * app → processes → pages → widgets → features → entities → shared
 * Нарушение границы = ошибка сборки lint. Внутри слайса — относительные импорты.
 */
const deny = (groups, msg) => groups.map((g) => ({ group: [g], message: msg }));
const RULE = (patterns) => ["error", { patterns }];

module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module", ecmaFeatures: { jsx: true } },
  plugins: ["@typescript-eslint", "react-hooks"],
  extends: ["eslint:recommended", "plugin:@typescript-eslint/recommended", "plugin:react-hooks/recommended"],
  ignorePatterns: ["dist", "node_modules", "*.config.ts", "*.cjs", "vite-env.d.ts"],
  rules: {
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/no-explicit-any": "off",
    "@typescript-eslint/no-empty-object-type": "off",
  },
  overrides: [
    // processes: не тянет app
    {
      files: ["src/processes/**/*.{ts,tsx}"],
      rules: { "no-restricted-imports": RULE(deny(["@/app/*"], "FSD: импорт только вниз")) },
    },
    // pages: не тянет app/processes и соседние pages
    {
      files: ["src/pages/**/*.{ts,tsx}"],
      rules: { "no-restricted-imports": RULE(deny(["@/app/*", "@/processes/*", "@/pages/*"], "FSD: импорт только вниз")) },
    },
    // widgets: ниже — features/entities/shared
    {
      files: ["src/widgets/**/*.{ts,tsx}"],
      rules: { "no-restricted-imports": RULE(deny(["@/app/*", "@/processes/*", "@/pages/*", "@/widgets/*"], "FSD: импорт только вниз")) },
    },
    // features: ниже — entities/shared, без соседних features
    {
      files: ["src/features/**/*.{ts,tsx}"],
      rules: { "no-restricted-imports": RULE(deny(["@/app/*", "@/processes/*", "@/pages/*", "@/widgets/*", "@/features/*"], "FSD: features не тянет features/выше")) },
    },
    // entities: ниже — shared (и другие entities)
    {
      files: ["src/entities/**/*.{ts,tsx}"],
      rules: { "no-restricted-imports": RULE(deny(["@/app/*", "@/processes/*", "@/pages/*", "@/widgets/*", "@/features/*"], "FSD: entities не тянет features/выше")) },
    },
    // shared: ничего кроме shared
    {
      files: ["src/shared/**/*.{ts,tsx}"],
      rules: { "no-restricted-imports": RULE(deny(["@/app/*", "@/processes/*", "@/pages/*", "@/widgets/*", "@/features/*", "@/entities/*"], "FSD: shared не тянет вышестоящие слои")) },
    },
  ],
};
