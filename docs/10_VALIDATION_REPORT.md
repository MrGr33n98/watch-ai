# Relatório de validação Watch AI — 2026-11-24

## Estado atual

O branch `feat/001-watch-ai-mvp` contém a implementação ponta a ponta do backend
FastAPI, worker assíncrono (`app.worker`), console mobile `/phone` e API
administrativa (`/v1/admin/*`, incluindo revogação remota de relógio perdido),
código-fonte Wear OS Compose atualizado (polling adaptativo, restauração de
estado, códigos de pareamento de 8 caracteres e testes `WatchControllerTest`),
contratos OpenAPI, migrations, testes, workflows e documentação. O relatório
técnico com evidências por slice está em
[`docs/reports/watch-ai-validation-20261123.md`](reports/watch-ai-validation-20261123.md).
O draft PR [#1](https://github.com/MrGr33n98/watch-ai/pull/1) está aberto;
nenhuma integração ou implantação em produção foi executada.

## Implementado no código-fonte

- Domínios FastAPI para ingestão, sessões, interpretação estruturada OpenRouter,
  verificação simbólica expandida com SymPy (`simplify`, `solve_equation`,
  derivadas e integrais), unidades com Pint, renderização SVG privada via
  `/v1/sessions/{session_id}/questions/{ordinal}/steps/{step_ordinal}/render`,
  pairing e sincronização.
- Worker assíncrono em background (`python -m app.worker` e suporte opcional
  embutido), console `/phone` com upload de 1–4 JPGs, CLI administrativo
  (`python -m app.maintenance.admin`) e respostas opcionais no WAHA DEV.
- Adaptadores PostgreSQL/Alembic, OpenRouter, WAHA, armazenamento privado de JPG
  e fila/outbox com idempotência e retry limitado.
- Cliente Wear OS em Kotlin/Compose com pareamento, Keystore, leitura HTTPS,
  passos da solução, cache offline, polling ativo (`15s -> 30s -> 60s`), pausa
  de ciclo de vida e restauração do último item aberto.
- Workflows GitHub Actions (emulador Wear atualizado para API 34 `android-wear`),
  fixtures sintéticas de quatro JPGs, contratos, runbooks e stack Compose com
  `db` + `api` + `worker` + perfil opcional `tls` (`caddy`).

## Verificações executadas

| Verificação | Resultado observado |
| --- | --- |
| `cd apps/api && TEST_DATABASE_URL=... uv run pytest -q` | `157 passed, 1 warning in 52.45s` (`0 skipped`, incluindo testes PostgreSQL e upload `/phone`). |
| `cd apps/api && uv run ruff check .` | `All checks passed!` |
| `cd apps/api && uv run mypy app` | `Success: no issues found in 77 source files` |
| `cd apps/api && uv run bandit -r app -q` | 1 achado Low pré-existente (`B406` em `formulas.py:11`), 0 Medium/High. |
| Alembic `upgrade head` / `check` / `downgrade base` em PostgreSQL | `ALEMBIC_OK` (sem divergências de schema). |
| Spec Kit `python3 tools/validate_pack.py` & `validate_goldens.py` | `PASS` (18 arquivos obrigatórios, exemplos JSON, OpenAPI, IDs T001–T041 e goldens). |
| Compose `config --quiet` com `infra/.env.example` | Exit `0`. |
| Docker Compose build + smoke E2E vivo (`watch-ai-smoke`) | `alembic 1.20.1`, `db`/`api`/`worker` `Healthy`, `/health` `200`, `/phone` `200`, upload `202`, worker processou sessão, SVG/detalhe OK e `DELETE` remoto revogou Watch (`401`) → `COMPOSE_SMOKE_OK`. |
| Auditoria local anterior de dependências (`pip-audit`) | Nenhuma vulnerabilidade conhecida no lock auditado (sem alteração no `uv.lock`). |

O aviso pytest remanescente é a depreciação do bridge Starlette/httpx.

## Riscos e bloqueios

| Prioridade | Risco ou bloqueio | Evidência/ação pendente |
| --- | --- | --- |
| Resolvido | Revogação remota de relógio perdido (ex-P0). | Implementado `DELETE /v1/admin/users/{user_id}/devices/{device_id}`, seção no `/phone` e CLI; coberto em SQLite, PostgreSQL e Compose smoke (`401` após revogação). |
| Resolvido | Build Docker e worker assíncrono não validados (ex-P1). | Build de `api` e `worker`, `alembic 1.20.1` e smoke E2E ponta a ponta com PostgreSQL aprovados nesta rodada. |
| P1 | APK, screenshots e emulação Wear OS no CI pendentes deste push. | Sem JDK/Android SDK nesta estação; workflow Wear ajustado para `api-level: 34` (`android-wear`) e correções nos testes UI aguardam execução no GitHub Actions. |
| P1 | Hardware físico (Galaxy Watch4, Y3000) e provedores externos reais ausentes. | T003–T005 e T033–T034 dependem de dispositivo físico, sessão WAHA DEV isolada, chave OpenRouter e orçamento explicitamente aprovados. |
| P1 | Deploy público e TLS externo não gerenciados automaticamente. | Compose inclui perfil opcional `caddy` (`tls`), mas operação em nuvem, backups off-host e secret manager continuam responsabilidade de infra externa. |
| P2 | Limite de gasto não reserva custo para chamadas concorrentes. | `MONTHLY_MODEL_BUDGET_USD` tem preflight/persistência, mas chamadas já em voo podem ultrapassar o limite. |

## Itens da missão ainda pendentes

- T003–T005: transferência real de fotos, configuração física do Galaxy Watch4
  e readiness de provedores externos.
- T020–T027: aguardar compilação/execução no GitHub Actions (`Wear OS CI`) e,
  posteriormente, validação física no Galaxy Watch4.
- T033–T034: integrações reais de WAHA DEV e OpenRouter com credenciais aprovadas.
- T036, T038 e T039 aguardam a conclusão do run atual de Wear OS no GitHub Actions.
- T041: PR draft [#1](https://github.com/MrGr33n98/watch-ai/pull/1) atualizado para
  revisão e disparo dos workflows finais; nenhum merge ou deploy executado.
