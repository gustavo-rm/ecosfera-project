-- ECOSFERA platform-api — papéis de banco restritos por schema (RNF-013, ADR 0003).
-- Rodar como dono do banco, uma vez por ambiente, DEPOIS das migrações (e de novo após novas tabelas,
-- ou use o ALTER DEFAULT PRIVILEGES abaixo). As senhas vêm do cofre:
--   ALTER ROLE platform_app PASSWORD '<do cofre>';  ALTER ROLE platform_migrator PASSWORD '<do cofre>';
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'platform_migrator') THEN
    CREATE ROLE platform_migrator LOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'platform_app') THEN
    CREATE ROLE platform_app LOGIN;
  END IF;
END
$$;

-- O migrador é dono do schema platform e só dele.
GRANT USAGE, CREATE ON SCHEMA platform TO platform_migrator;

-- A aplicação lê e escreve dados do schema platform, sem DDL.
GRANT USAGE ON SCHEMA platform TO platform_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA platform TO platform_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA platform TO platform_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA platform GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO platform_app;
-- Tabelas criadas pelas migrações futuras (rodadas como platform_migrator) também ficam acessíveis ao app.
ALTER DEFAULT PRIVILEGES FOR ROLE platform_migrator IN SCHEMA platform GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO platform_app;
ALTER DEFAULT PRIVILEGES FOR ROLE platform_migrator IN SCHEMA platform GRANT USAGE, SELECT ON SEQUENCES TO platform_app;

-- audit_log: só INSERT e SELECT (o gatilho de imutabilidade é a segunda barreira).
REVOKE UPDATE, DELETE, TRUNCATE ON platform.audit_log FROM platform_app;
-- Tabela de controle das migrações: só leitura para a aplicação.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON platform.platform_migrations FROM platform_app;

-- Nenhum acesso ao schema do ai-sim-service.
REVOKE ALL ON SCHEMA rag FROM platform_app;
REVOKE ALL ON ALL TABLES IN SCHEMA rag FROM platform_app;
