import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_", destructuredArrayIgnorePattern: "^_" }],
    },
  },
  {
    // The render layer mutates three.js objects and preallocated scratch values inside useFrame on purpose:
    // no React re-render per frame and no allocation per frame (ADR 0002). The React Compiler purity rules do not fit there.
    files: ["src/render/**"],
    rules: { "react-hooks/immutability": "off", "react-hooks/purity": "off", "react-hooks/refs": "off" },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "scripts/**", "public/sw.js", ".reports/**"]),
]);

export default eslintConfig;
