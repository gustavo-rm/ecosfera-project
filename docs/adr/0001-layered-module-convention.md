# 0001 — Convenção de camadas por módulo de domínio

- Status: Aceito
- Data: 2026-07-22

## Contexto

`platform-api` (NestJS) e `ai-sim-service` (Python) ainda não possuem módulos de
domínio implementados — apenas o boilerplate inicial de cada framework. Sem uma
convenção fixada antes do primeiro módulo real, é comum que controllers/rotas
acessem o ORM diretamente, acoplando regra de negócio à infraestrutura de
persistência e violando a inversão de dependência (Clean Architecture / SOLID
"D").

## Decisão

Todo módulo de domínio novo, em qualquer um dos dois serviços, é organizado em
quatro camadas:

```
<modulo>/
├── domain/           # entidades, agregados, value objects — sem dependência de framework/ORM
├── application/      # casos de uso / serviços de aplicação — orquestram o domínio
├── infrastructure/   # implementações concretas (TypeORM/SQLAlchemy, clients externos)
└── interface/        # controllers/rotas, DTOs, mapeamento de entrada e saída
```

Regras de dependência entre camadas (de fora para dentro apenas):

- `interface` depende de `application`.
- `application` depende de `domain` e de abstrações (interfaces/ports) de `infrastructure`.
- `infrastructure` implementa as abstrações definidas por `application`/`domain`, nunca o contrário.
- `domain` não importa nada de `infrastructure` ou `interface`.

Isso vale tanto para os módulos de negócio do `platform-api` (ex.: quando
`auth`, `users`, `sessions` forem criados) quanto para os bounded contexts do
`ai-sim-service` (`simulation`, `tutor` — ver ADR 0002).

## Consequências

- Controllers/rotas nunca chamam o ORM/driver diretamente.
- Regra de negócio é testável sem subir banco de dados (mocks nas abstrações de `infrastructure`).
- Onboarding de novos membros do time fica previsível: a pergunta "onde isso vai?" tem resposta única.
- Não força a criação prematura de módulos que ainda não existem (ex.: `auth`,
  `users`) — a convenção só se aplica quando um módulo de domínio real for
  criado.
