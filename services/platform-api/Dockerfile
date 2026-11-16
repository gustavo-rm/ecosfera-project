# syntax=docker/dockerfile:1.7
# ECOSFERA platform-api — imagem multi-stage. Contexto de build: RAIZ do monorepo.
#   docker build -f services/platform-api/Dockerfile -t ecosfera/platform-api .
FROM node:22.23-bookworm-slim AS base
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH CI=true
RUN corepack enable

FROM base AS build
WORKDIR /repo
RUN --mount=type=secret,id=ca,required=false \
    if [ -f /run/secrets/ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/ca; fi; corepack prepare pnpm@11.15.1 --activate
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json .npmrc* ./
COPY services/platform-api/package.json services/platform-api/
# CA extra opcional (proxy corporativo): docker build --secret id=ca,src=ca.crt ...
RUN --mount=type=secret,id=ca,required=false \
    if [ -f /run/secrets/ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/ca; fi; \
    pnpm install --frozen-lockfile --filter platform-api... --ignore-scripts
COPY services/platform-api services/platform-api
RUN pnpm --filter platform-api build \
 && pnpm --filter platform-api deploy --legacy --prod --ignore-scripts /out \
 && cp -r services/platform-api/dist /out/dist \
 && cp -r services/platform-api/db /out/db

FROM node:22.23-bookworm-slim AS runtime
ENV NODE_ENV=production PORT=3000
WORKDIR /app
COPY --from=build --chown=node:node /out /app
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/platform/api/v1/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
# Migrações rodam como passo separado (papel de migração), não no boot da aplicação:
#   docker run --rm --env-file ... ecosfera/platform-api node dist/migrar.js
CMD ["node", "dist/main.js"]
