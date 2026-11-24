# Implementation Plan — Feature 001

## Technical Context

Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy/Alembic, PostgreSQL, httpx, Pillow, SymPy, Pint, uv; Kotlin + Compose for Wear OS Material3, Retrofit/OkHttp, Room/DataStore; Docker Compose, GitHub Actions.

## Constitution Check

1. Correctness Before Confidence: provider output is untrusted; only supported deterministic checks can produce `verified`; otherwise `needs_review`.
2. Test First: each implementation task begins with a failing deterministic test and records RED/GREEN/REFACTOR evidence.
3. Domain-Driven Design: bounded contexts and ports isolate HTTP, persistence, WAHA, OpenRouter, and Wear UI.
4. API-First Contracts: `contracts/openapi.yaml` is the source contract and is validated against backend DTOs and watch clients.
5. Privacy and Security: validate real JPEG data, keep private media server-side, enforce device ownership, support revocation, and redact logs.
6. Native Wear OS: use Wear Compose Material 3, direct HTTPS, circular-safe layouts, accessible controls, and offline cache; no audio.
7. Reproducibility and Observability: pin dependencies/toolchains and run fake-based CI without external credentials.
8. No Silent Deployment: no merge, production WAHA use, secret publication, or deploy; draft PR only for review.

**Gate result before implementation**: design aligns with all eight principles. Hardware compatibility, production retention configuration, live model/budget, and isolated WAHA credentials remain explicit release gates; they do not block mock-based implementation.

## Fases

Phase 0: hardware feasibility, Android pairing, 4 JPG reais de ensaio, GitHub/Spec Kit inicializados.
Phase 1: dominio + modelos + DB + stub provider, testes unit/integration em RED-GREEN.
Phase 2: WAHA webhook adapter e upload local de DEV, dedupe, validação MIME e fila.
Phase 3: OpenRouter provider com schema, verificação SymPy/Pint, renderer e estado `needs_review`.
Phase 4: Wear app Material3/Compose, pareamento, status HTTP, cache, steps e erro offline.
Phase 5: E2E/hardening, dispositivos físicos, custos, CI artifact APK, runbook, release gated.

## Architecture gates

- C1: GET /health + OpenAPI models + sqlite mock em testes; PostgreSQL migration padronizada.
- C2: POST /internal/waha/events retorna 202 após persistir `inbound_messages` único; segredo HMAC/gateway.
- C3: POST /dev/ingest existe apenas em desenvolvimento e envia payload sintético.
- C4: worker mock gera `ready` ou `needs_review` pela mesma interface de provider real.
- C5: watch consome `/v1/sessions` e `/v1/sessions/{id}/questions/{n}`.
- C6: watch consegue ler cache offline e revogar token.

## Performance / Complexity

Não executar IA dentro do processo de request. Limite de 4 imagens/sessão e até 8MB por JPG. Sem microserviços desnecessários; API/worker podem ser dois processos do mesmo pacote Python. Pool de workers pequeno e com limites de CPU/RAM. OpenRouter timeout por job e budget mensal. Polling 15s apenas ativo, backoff 60s em background.

## Rollout

Feature flag `ENABLE_WAHA_INGEST=false`, `ENABLE_REAL_OPENROUTER=false`, `ENABLE_WEAR_PAIRING=true`; primeiro release testes offline e mock, depois QA isolado e, por último, integrações reais. Nenhum deploy automático por agente.

## Deliverables

Arvore do monorepo, DB migrations, schema OpenAPI, tests pytest, app Wear, APK debug, screenshots, CI, docs e relatório técnico evidenciando hipóteses testadas.

## Project Structure

The following is the proposed target layout for implementation; these paths were not present in the initial repository inventory.

```text
apps/api/
  app/domain/{ingestion,sessions,interpretation,math_verification,presentation,delivery}/
  app/application/{commands,queries,ports,handlers}/
  app/adapters/{http,db,queue,waha,openrouter,math,renderer,storage}/
  app/infrastructure/{config,logging,observability}/
  tests/{unit,contract,integration,e2e}/
  alembic/
apps/wear/
  app/src/main/
  app/src/test/
  app/src/androidTest/
infra/docker-compose.yml
fixtures/{golden,blurry,invalid,webhooks}/
docs/reports/
.github/workflows/{backend-ci.yml,wear-ci.yml,security.yml}
specs/001-watch-ai-mvp/{spec.md,plan.md,tasks.md,research.md,data-model.md,contracts/}
```

The first backend slice may use a lightweight local persistence adapter for deterministic development, but the production model and migrations must target PostgreSQL. Live WAHA/OpenRouter adapters remain behind ports and disabled by default.
