-- ECOSFERA — inicialização do PostgreSQL (executa apenas na 1ª subida do volume).
-- Roda no banco definido por POSTGRES_DB (ecosfera), como superusuário.

-- Extensão de busca vetorial para o RAG (pgvector).
CREATE EXTENSION IF NOT EXISTS vector;

-- Separação de responsabilidades por schema:
--   platform → migrations do platform-api (TypeORM)
--   rag      → migrations do ai-sim-service (Alembic)
CREATE SCHEMA IF NOT EXISTS platform;
CREATE SCHEMA IF NOT EXISTS rag;

-- Observação (produção): criar roles distintas com permissão restrita por schema.
-- Em dev, usa-se o POSTGRES_USER único como owner de ambos os schemas.
