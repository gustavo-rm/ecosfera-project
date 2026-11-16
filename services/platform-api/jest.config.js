// Configuração do Jest. Dois projetos:
//  - unit: regras de domínio e funções puras, sem Docker;
//  - int: integração, contrato, segurança e e2e com Testcontainers (PostgreSQL, Redis, MinIO).
const transform = {
  '^.+\\.(t|j)s$': [
    'ts-jest',
    {
      tsconfig: {
        allowJs: true,
        module: 'commonjs',
        moduleResolution: 'node10',
        esModuleInterop: true,
        experimentalDecorators: true,
        emitDecoratorMetadata: true,
        target: 'ES2022',
        strict: true,
        strictPropertyInitialization: false,
        resolveJsonModule: true,
      },
      diagnostics: false,
    },
  ],
};
// jose 6 é publicado só como ESM; é transformado para CJS nos testes.
const transformIgnorePatterns = ['/node_modules/(?!(\\.pnpm/jose@|jose/))'];

const base = {
  moduleFileExtensions: ['js', 'json', 'ts'],
  rootDir: '.',
  transform,
  transformIgnorePatterns,
  testEnvironment: 'node',
};

module.exports = {
  projects: [
    { ...base, displayName: 'unit', testMatch: ['<rootDir>/src/**/*.spec.ts'] },
    {
      ...base,
      displayName: 'int',
      testMatch: ['<rootDir>/test/**/*.int-spec.ts'],
      globalSetup: '<rootDir>/test/support/global-setup.ts',
      globalTeardown: '<rootDir>/test/support/global-teardown.ts',
      setupFiles: ['<rootDir>/test/support/env.ts'],
      testTimeout: 60000,
    },
  ],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/main.ts',
    '!src/**/*.spec.ts',
    '!src/infrastructure/database/migrations/**',
    '!src/infrastructure/database/data-source.ts',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text-summary', 'json-summary', 'lcov'],
  // Gate de cobertura (docs/backend/relatorios/COBERTURA.md). Medido sobre unit + integração.
  coverageThreshold: { global: { lines: 80, statements: 78, functions: 70, branches: 60 } },
};
