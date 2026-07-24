import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    // A camada 3D (react-three-fiber) é imperativa por natureza: a animação
    // acontece mutando uniforms e refs dentro de `useFrame`. As regras do React
    // Compiler (purity/immutability) pressupõem componentes puros e não se
    // aplicam a esse loop de renderização do Three.js.
    files: [
      "src/components/planet/**/*.{ts,tsx}",
      "src/hooks/useAtmospherePulse.ts",
      "src/hooks/usePlanetRotation.ts",
      "src/hooks/useLifeEvents.ts",
      "src/hooks/useDustParticles.ts",
    ],
    rules: {
      "react-hooks/immutability": "off",
      "react-hooks/purity": "off",
    },
  },
]);

export default eslintConfig;
