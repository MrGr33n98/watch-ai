# Watch AI Validation Report — 2026-11-23

## Status

Implementation is in progress on `feat/001-watch-ai-mvp`. This report records observed commands only. The API, Wear OS app, real WAHA/OpenRouter integration, physical hardware path, APK, screenshots, and GitHub Actions are not yet complete.

## Discovery Evidence

- Initial branch: `main`; HEAD: `7b8cc95fb43a95ea64d0fadcb82c1f9f67e6e364`.
- Initial tracked tree: `README.md` only. No app code, tests, OpenAPI contract, or CI workflow existed in the repository.
- Initial local state included untracked `.agents/` and `.specify/`. The Spec Kit 1.0.11 CLI was already initialized for Codex skills; it was not reinitialized with `--force`.
- Runtime tools observed: Python 3.12.3, uv 0.12.17, Docker Compose v5.4.0. `java`, `adb`, and `emulator` were not found.
- The source pack's four synthetic JPEG fixtures are 1800×1200. They do not prove Y3000 focus or iPhone import behavior.
- Official references reviewed: [Wear Compose](https://developer.android.com/training/wearables/compose), [Wear network communication](https://developer.android.com/training/wearables/data/network-communication), [Samsung phone compatibility](https://www.samsung.com/us/support/answer/ANS10004668/), [OpenRouter image input](https://openrouter.ai/blog/tutorials/send-image-to-llm/), [WAHA receive messages](https://waha.devlike.pro/docs/how-to/receive-messages/), and [Spec Kit quickstart](https://github.github.com/spec-kit/quickstart).

## Pack Checks

| Check | Command | Result |
|---|---|---|
| Required pack files, example JSON, OpenAPI 3.1, task IDs | `python3 tools/validate_pack.py` | PASS after importing the pack prompts; 18 required files validated |
| Golden arithmetic before backend environment existed | `python3 tools/validate_goldens.py` | Arithmetic PASS; symbolic SymPy portion SKIP because SymPy was not installed at that time |
| Whitespace validation | `git diff --check` | PASS at the time recorded |

These checks validate source artifacts only; they are not product, API, integration, or hardware passes.

## TDD Evidence

### T006 — API health and development-only ingest

**RED** — tests were written before `app/main.py` existed.

Command:

```sh
cd apps/api
uv run pytest -q tests/integration/test_health.py tests/integration/test_dev_ingest.py
```

Observed result: exit code 2 during collection. Both test modules failed with `ModuleNotFoundError: No module named 'app'`. This is the expected initial failure because the application module has not yet been implemented.

**Files written before implementation**: `apps/api/pyproject.toml`, `apps/api/tests/integration/test_health.py`, `apps/api/tests/integration/test_dev_ingest.py`.

Initial implementation result: `4 passed, 1 warning` (Starlette warns that its `TestClient` integration with `httpx` is deprecated). Ruff initially found an unsorted import and mypy found the optional environment value was not narrowed. The import was sorted; the app environment resolution was made explicit; Ruff test assertions are allowed by the test-only lint rule; and FastAPI's upload argument uses `Annotated` so it passes Ruff B008.

**GREEN** — final deterministic checks:

```sh
cd apps/api
uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
cd apps/api
uv run python ../../tools/validate_goldens.py
```

Observed: `4 passed, 1 warning`; `All checks passed!`; `Success: no issues found in 6 source files`; pack validation PASS for 18 required files/OpenAPI/tasks; golden fixture arithmetic and symbolic identities PASS with SymPy available. Golden validation checks fixture values, not the product verification pipeline or Pint integration.

Compose configuration/build and local smoke evidence:

```sh
docker compose --env-file infra/.env.example -f infra/docker-compose.yml config --quiet
docker compose --env-file infra/.env.example -f infra/docker-compose.yml build api
docker compose --env-file infra/.env.example -f infra/docker-compose.yml up --build --detach --wait
curl -sS --fail http://127.0.0.1:8000/health
curl -sS --fail -F file=@examples/synthetic_jpg/Q1_synthetic.jpg http://127.0.0.1:8000/dev/ingest
docker compose --env-file infra/.env.example -f infra/docker-compose.yml down
```

The first Compose check was RED because the example env file/stack did not exist. The first container smoke then exposed a runtime failure: scripts in a virtualenv created at `/build` retained that absolute path after copying to `/app`. Changing the builder `WORKDIR` to `/app` fixed the path. Final result: Compose reported both `infra-db-1` and `infra-api-1` healthy; `/health` returned `{"status":"ok"}` (HTTP 200); dev JPEG ingest returned `{"status":"accepted"}` (HTTP 202). Containers/network were removed with `down`; the named local database volume was preserved. No real provider or hardware was used.

**REFACTOR** — Ruff, mypy, unit/integration checks, package validation, golden fixture validation, Compose config, image build, container health, and local HTTP smoke all passed after the fixes above. Remaining warning: Starlette's deprecated `TestClient`/`httpx` bridge.

**T006 status**: complete for the API scaffold, health route, development-only ingest route, lockfile, local Docker image, and PostgreSQL Compose service. This does not claim PostgreSQL persistence, production ingestion, image byte validation, or full API behavior; those belong to later tasks.

### T007 — Session aggregate, question order, and lifecycle

**RED** — added `apps/api/tests/unit/test_study_session.py` before creating the session domain.

```sh
cd apps/api
uv run pytest -q tests/unit/test_study_session.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.domain'`.

An additional boundary test was added before tightening expected-count validation. Its first run produced `1 failed, 4 passed`: `1.5` was accepted as an expected question count. The domain now rejects non-integer values and booleans as well as values outside 1–4.

Implemented `QuestionOrder`, immutable `QuestionItem` snapshots, and the `StudySession` aggregate. Questions receive one-based arrival ordinals, a fifth or otherwise excess question is rejected, a full batch queues automatically, and a non-empty short batch can be queued explicitly. Session/question transitions are allowlisted; a question cannot become ready without validated step references; the session result is derived from question outcomes and timestamps are timezone-aware.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/unit/test_study_session.py
```

Observed: `13 passed in 0.14s`.

**REFACTOR** — full backend checks after the domain changes:

```sh
cd apps/api
uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
git diff --check
```

Observed: `17 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 9 source files`; whitespace validation passed. The warning is the existing Starlette `TestClient`/`httpx` deprecation. No database persistence or HTTP session API is claimed by T007.

**T007 status**: complete for the pure session aggregate, question ordering, count limits, and lifecycle rules.

### T008 — PostgreSQL mappings, constraints, and initial migration

**RED** — added `apps/api/tests/integration/test_persistence.py` before creating the DB adapter. The first run failed during collection with `ModuleNotFoundError: No module named 'app.adapters.db'`.

After the initial mappings and migration were in place, an additional PostgreSQL boundary test was added before adding a cross-count constraint. The test run observed `1 failed, 1 passed`: the database accepted `received_count=2` when `expected_count=1`. Added `ck_session_received_le_expected` to the mapping and migration; the final persistence suite passes.

Implemented SQLAlchemy mappings for users, sessions, and ordered questions; UUID keys, session/question status and confidence constraints, count bounds, foreign keys, unique per-session ordinals, and indexes; plus the initial Alembic migration and environment configuration that reads `DATABASE_URL`.

**GREEN** — local disposable PostgreSQL was started with Docker Compose and the following suite ran against it:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q tests/integration/test_persistence.py
```

Observed: `9 passed`. Tests exercise the real PostgreSQL constraints and Alembic upgrade/downgrade, not SQLite substitutes.

**REFACTOR** — full API and schema checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic upgrade head
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic check
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic downgrade base
docker compose --env-file infra/.env.example -f infra/docker-compose.yml down
```

Observed: `26 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 12 source files`; Alembic `No new upgrade operations detected.` The single test warning is the existing Starlette `TestClient`/`httpx` deprecation. The temporary schema was downgraded and the database container/network stopped; the named development volume remains.

**T008 status**: complete for the initial users/session/question PostgreSQL schema and migration. Later tables (media, outbox, authorization) remain in their dependent tasks.

### T009 — Inbound idempotency, ordering, outbox, and unit of work

**RED** — added `apps/api/tests/unit/test_idempotency.py` before adding application ports or ingestion models.

```sh
cd apps/api
uv run pytest -q tests/unit/test_idempotency.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.application'`.

Implemented immutable inbound/outbox domain records, a source-time ordering policy, repository and unit-of-work protocols, an ingestion use case, and SQLAlchemy/PostgreSQL repositories. `INSERT ... ON CONFLICT DO NOTHING` on `(provider, provider_message_id)` arbitrates duplicates; the message and outbox event share one transaction. Outbox payloads contain internal message/session UUIDs and omit sender HMACs and media URLs. A second Alembic revision adds inbox and JSONB outbox tables and indexes.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/unit/test_idempotency.py
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q tests/integration/test_persistence.py::test_duplicate_inbound_event_persists_one_row_and_one_outbox_event tests/integration/test_persistence.py::test_database_repository_orders_out_of_order_webhooks_by_provider_timestamp
```

Observed: `2 passed` in the unit suite and `2 passed` against the local PostgreSQL container for durable duplicate suppression, single outbox creation, and out-of-order recovery.

**REFACTOR** — full API and migration checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic upgrade head
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic check
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic downgrade base
docker compose --env-file infra/.env.example -f infra/docker-compose.yml down
```

Observed: `30 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 18 source files`; Alembic `No new upgrade operations detected.` The warning remains Starlette's `TestClient`/`httpx` deprecation. The disposable schema was downgraded and its container/network stopped.

**T009 status**: complete for inbound deduplication, deterministic source-time ordering, transactional outbox creation, PostgreSQL persistence, and unit-of-work ports. Webhook authentication and media access restrictions remain in T028–T029.

### T010 — Authenticated session and question read API

**RED** — added `apps/api/tests/contract/test_watch_api.py` before adding the auth dependency and routes.

```sh
cd apps/api
uv run pytest -q tests/contract/test_watch_api.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.adapters.http.auth'`.

Implemented list/detail/question GET routes with Pydantic response models, OpenAPI operation IDs and error models, SQLAlchemy read queries, and owner filtering. Unauthenticated requests fail closed with 401. Foreign-owner session and question reads return 404. A ready row with no persisted solution steps is never returned as verified; actual step storage/rendering remains in T019.

Two contract gaps were captured with follow-up RED checks and fixed:

- A `ready`/`verified` row with no steps returned `verified=true`; the added test failed until verification required non-empty step data.
- 401/404 bodies used FastAPI's default `{"detail": ...}` shape instead of the contract's `{code,message,correlation_id}`; both response tests failed until a shared handler emitted the documented shape.

**GREEN** — contract tests against the local PostgreSQL test schema:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q tests/contract/test_watch_api.py
```

Observed: `3 passed`. The tests compare generated route operation IDs, status responses, and bearer scheme to the source OpenAPI file; they also check list/detail/question responses, 401, owner-scoped 404, and the unverified-without-steps rule.

**REFACTOR** — full backend suite and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
git diff --check
```

Observed: `33 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 23 source files`; pack validation PASS for 18 required files/OpenAPI/T001–T041; whitespace check passed. The remaining warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T010 status**: complete for the read API, response contract, and owner-scoped queries. The bearer dependency intentionally rejects all tokens until T012 implements pairing/token validation; tests inject a principal to exercise authorized read behavior. No production access token is accepted yet.

### T011 — Asynchronous interpretation wake-up and deterministic fake vision

**RED** — added the end-to-end fake pipeline and duplicate scheduling assertions before implementing the queue and scheduler port.

```sh
cd apps/api
uv run pytest -q tests/e2e/test_fake_pipeline.py tests/unit/test_idempotency.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.adapters.queue'`.

Implemented a bounded in-process interpretation queue, application processor, provider/scheduler ports, typed interpretation result, and deterministic fake fixtures for the four checked-in goldens. Ingestion now commits inbox and outbox records before waking the queue; duplicate provider messages do not enqueue another task. Missing or ambiguous fake recognition has low confidence, no guessed statement/type, and `needs_review=true`. The durable outbox remains the recovery source; production polling, retry, and dead-letter behavior is T031.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/e2e/test_fake_pipeline.py tests/unit/test_idempotency.py
```

Observed: `4 passed`. The gated-provider test verifies ingestion returns while interpretation is still blocked, then verifies the Fourier fixture; additional assertions cover ambiguous review state and duplicate suppression.

**REFACTOR** — full backend suite and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
```

Observed: `35 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 29 source files`. The remaining warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T011 status**: complete for asynchronous in-process wake-up and deterministic fake interpretation. The endpoint still does not accept a WAHA webhook; T028 will provide that adapter. The in-process executor is a development/MVP adapter and is not durable; the committed outbox supports later recovery work in T031.

### T012 — One-time pairing, scoped watch tokens, ownership, and revocation

**RED** — added PostgreSQL/API integration cases before adding the delivery repository and pairing routes.

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q tests/integration/test_pairing.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.adapters.db.delivery'`. A separate rate-limit unit test also failed collection before implementation with `ModuleNotFoundError: No module named 'app.adapters.http.pairing_rate_limit'`.

Implemented expiring, single-use pairing codes and 256-bit opaque access tokens. PostgreSQL stores SHA-256 hashes only; pairing redemption uses one conditional update to prevent code reuse under concurrent requests. Tokens are limited to `sessions:read`, expire after 30 days, resolve to a user/device principal, and can be revoked by that device. Pairing attempts receive a bounded process-local rate limit. The OpenAPI contract now describes opaque bearer tokens, pairing, and self-revocation.

**GREEN**:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q tests/integration/test_pairing.py tests/contract/test_watch_api.py
uv run pytest -q tests/unit/test_pairing_rate_limit.py
```

Observed: `6 passed` across the PostgreSQL pairing/auth and OpenAPI contract tests; `2 passed` for rate-limit window reset and bounded client tracking. Covered expired/reused code denial, hashed-only persistence, scoped credentials, owner isolation, pairing endpoint, and immediate revocation.

**REFACTOR** — full backend, schema, contract, and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic upgrade head
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic check
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic downgrade base
cd ../..
python3 tools/validate_pack.py
git diff --check
```

Observed: `40 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 35 source files`; Alembic `No new upgrade operations detected.`; package/OpenAPI validation PASS; whitespace check passed. The warning remains Starlette's deprecated `TestClient`/`httpx` bridge.

**T012 status**: complete for code redemption, token scope, owner resolution, and self-revocation. The rate limiter is process-local; production must also enforce a shared gateway limit when running multiple API replicas. Pairing-code provisioning is an internal service operation and has no operator-facing admin route yet.

### T013 — Typed OpenRouter multimodal adapter

**RED** — added provider contract tests before adding the OpenRouter adapter.

```sh
cd apps/api
uv run pytest -q tests/contract/test_openrouter_provider.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.adapters.openrouter'`.

Implemented the typed `VisionProvider` contract and an OpenRouter Chat Completions adapter. It sends a private JPEG data URL, requests strict JSON, uses a prompt that treats image text as untrusted and prohibits solving or expression execution, applies explicit timeout and bounded retries, and maps invalid/unclear output to typed failures or `needs_review`. The adapter loads its key/model only from server environment configuration; neither is placed in the Wear app. The transport and image content shape follow the [official OpenRouter Chat Completions API](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion) and [image input guide](https://openrouter.ai/blog/tutorials/send-image-to-llm/).

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/contract/test_openrouter_provider.py
```

Observed: `5 passed`. Covered typed success, invalid JSON, missing required fields, 429 with bounded `Retry-After`, and bounded timeout retries. A `httpx.MockTransport` is used; no network call or external credential was used.

**REFACTOR** — backend suite and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
```

Observed: `45 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 37 source files`. The focused OpenRouter suite was rerun after the final retry typing adjustment and remained `5 passed`. The remaining full-suite warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T013 status**: complete for the provider port, private multimodal request, strict typed response, safe prompt, timeout, and bounded retries. Model approval, budget approval, and a live provider smoke remain pending under T005/T034.

### T014 — JPEG admission and EXIF normalization

**RED** — added unit cases for valid, corrupt, disguised, oversized, rotated, and excessive-pixel images before adding the Pillow adapter.

```sh
cd apps/api
uv run pytest -q tests/unit/test_jpeg_admission.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.adapters.storage'`.

Implemented bounded byte and decoded-pixel admission, strict declared MIME and actual JPEG checks, full decode validation, EXIF orientation correction, metadata stripping, and a normalized SHA-256 result. The development upload endpoint now uses the same validator and maps rejection to structured 413/415 errors. Default admission limits are 8 MiB and 40 million decoded pixels.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/unit/test_jpeg_admission.py tests/integration/test_dev_ingest.py
```

Observed: `10 passed`. The tests cover corrupt bytes, PNG disguised as JPEG, mismatched MIME, byte limit, pixel budget, EXIF rotation, stripped orientation metadata, and existing dev endpoint behavior.

**REFACTOR** — backend suite and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
git diff --check
```

Observed: `52 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 40 source files`; pack/OpenAPI validation PASS; whitespace check passed. The remaining warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T014 status**: complete for JPEG validation and normalization in the development upload path. Production WAHA media download integration remains T029; no original camera or phone images were available, so physical image-quality checks remain T003.

### T015 — Safe typed expression AST

**RED** — added parser cases before creating the domain grammar.

```sh
cd apps/api
uv run pytest -q tests/unit/test_safe_expression.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.domain.math_verification'`.

Implemented a bounded parser using Python's syntax tree only to inspect syntax and build an application-owned typed tree. The allowlist supports numeric literals, known symbols, arithmetic operators, and a small set of unary math functions. It rejects imports, attributes, arbitrary function calls, keywords, indexing, booleans, unknown symbols, excessive source/AST size or depth, and exponents outside the configured bound. It never compiles or evaluates OCR text; conversion to symbolic operations is deferred to T016.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/unit/test_safe_expression.py
```

Observed: `10 passed`, including malicious Python syntax, unknown symbols, excessive nesting, source length, and power bounds.

**REFACTOR** — full backend and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
git diff --check
```

Observed: `62 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 42 source files`; pack/OpenAPI validation PASS; whitespace check passed. The remaining warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T015 status**: complete for bounded expression parsing and typed AST construction. Supported SymPy conversion and operation verification remain T016.

### T016 — Exact symbolic algebra, derivatives, and integrals

**RED** — added deterministic symbolic golden tests before adding the SymPy adapter.

```sh
cd apps/api
uv run pytest -q tests/unit/test_symbolic_verifier.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.adapters.math'`.

Implemented exact conversion from the allowlisted typed AST into SymPy constructors. Supported operations include simplification, differentiation, and definite integration with exact numeric bounds. The adapter does not call `eval`, `sympify`, or another source-string interpreter. Expressions or operations outside the grammar and verifier capability raise `UnsupportedMathInput` for the later review policy.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/unit/test_symbolic_verifier.py
```

Observed: `5 passed`; GOLD-DERIV-002 returns `2*x + 3`, GOLD-INTEGRAL-003 returns `9`, algebra simplifies exactly, unsupported syntax is rejected, and symbolic integration bounds are denied.

**REFACTOR** — full backend and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
git diff --check
```

Observed: `67 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 45 source files`; pack/OpenAPI validation PASS; whitespace check passed. SymPy has no bundled type stubs in the pinned environment, so the mypy override is limited to the external `sympy` module boundary. The remaining warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T016 status**: complete for exact simplification, differentiation, definite integration, and safe rejection. Physical unit verification remains T017; policy and ordered steps remain T018.

### T017 — Dimensional verification with Pint and Decimal

**RED** — added dimensional golden tests before implementing the Pint adapter.

```sh
cd apps/api
uv run pytest -q tests/unit/test_dimensional_verifier.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.adapters.math.dimensional'`.

Implemented typed `PhysicalQuantity` Decimal inputs, Pint calculations, exact unit conversions, and a closed unit-alias allowlist. Fourier heat-rate verification computes `k × A × ΔT / L` and requires the result to convert to watts. Unit strings are never passed through Pint's free-form parser. The registry's kelvin name and distinction between temperature and temperature difference were checked against [Pint's unit documentation](https://pint.readthedocs.io/en/0.26.2/default-units.html).

The first implementation run exposed that the installed Pint registry does not define `delta_kelvin`; four focused tests failed at adapter construction. The implementation was corrected to use the registry's multiplicative `kelvin` unit for this temperature-difference formula.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/unit/test_dimensional_verifier.py
```

Observed: `4 passed`; GOLD-FOURIER-001 returns exactly `2400 W`, GOLD-UNIT-004 converts `1500 W` to `1.5 kW`, incompatible dimensions and unrecognized unit expressions are rejected.

**REFACTOR** — full backend and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
git diff --check
```

Observed: `71 passed, 1 warning`; Ruff `All checks passed!`; mypy `Success: no issues found in 47 source files`; pack/OpenAPI validation PASS; whitespace check passed. The remaining warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T017 status**: complete for the Fourier heat-rate golden, watt conversion, Decimal values, and incompatible-unit rejection. Combining OCR into validated solution policy remains T018.

### T018 — Ordered solution steps and review policy

**RED** — added policy integration tests before adding the solution request/result types and application service.

```sh
cd apps/api
uv run pytest -q tests/integration/test_solution_policy.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.application.solution_policy'`.

Implemented typed supported-operation requests and ordered statement, data, formula, substitution, calculation, verification, and result steps. Only high-confidence, non-review items with complete inputs reach the exact SymPy/Pint verifiers. Missing fields, low confidence, unsupported operations, unsafe expressions, and incompatible units return `needs_review`, no final answer, and no verified flag.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/integration/test_solution_policy.py
```

Observed: `7 passed`; covers ambiguous reading, missing Fourier values, hostile/unsupported expression input, ordered steps, and all four current golden operations.

**REFACTOR** — full backend and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
git diff --check
```

Observed: `78 passed, 1 warning in 33.38s`; Ruff `All checks passed!`; mypy `Success: no issues found in 49 source files`; pack/OpenAPI validation PASS; whitespace check passed. The remaining warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T018 status**: complete for deterministic supported calculations and conservative review policy. The application accepts typed analysis input; extracting structured values from real photos remains dependent on T013/T034 and the later fake-to-watch integration in T032.

### T019 — Private formula SVG rendering and text fallback

**RED** — added renderer/storage tests before creating the SVG adapter.

```sh
cd apps/api
uv run pytest -q tests/integration/test_formula_rendering.py
```

Observed result: exit code 2 during collection with `ModuleNotFoundError: No module named 'app.adapters.renderer'`. A follow-up RED check for `\lim_{x \to 0}` also showed the initial renderer falling back instead of rendering the required limit form.

Implemented an allowlisted LaTeX-to-Unicode text renderer that emits escaped SVG into private content-addressed files. Storage enforces a byte limit, `0700` directory permissions, and `0600` file permissions; asset keys are path-validated. Supported forms include fractions, roots, integral bounds, superscripts/subscripts, Greek symbols, and limit indices. Unknown commands or oversized formulas return accessible plain-text fallback and create no asset.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/integration/test_formula_rendering.py
```

Observed: `8 passed`, covering the required notation, limit fallback behavior, unsupported LaTeX, byte bounds, path traversal rejection, and filesystem permissions.

**REFACTOR** — full backend and static checks:

```sh
cd apps/api
TEST_DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
git diff --check
```

Observed: `86 passed, 1 warning in 55.21s`; Ruff `All checks passed!`; mypy `Success: no issues found in 51 source files`; pack/OpenAPI validation PASS; whitespace check passed. The remaining warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T019 status**: complete for private bounded SVG generation and text fallback. The API does not expose an asset download route or bind formula assets to session ownership yet; watch clients can use the returned plain-text step until authenticated asset delivery is added.

## External and Physical Gates

- Y3000/microSD/Lightning/iPhone 14: NOT RUN; hardware is not connected.
- Galaxy Watch4 setup, ADB Wi-Fi, 40/44 mm rendering, and installation: BLOCKED; Java, Android SDK, ADB, and emulator are unavailable.
- WAHA DEV webhook/media smoke: NOT RUN; no isolated session or credentials provided.
- OpenRouter live smoke/model budget: NOT RUN; no credential or budget approval provided.
- APK, physical screenshots, live service costs, and production readiness: NOT AVAILABLE.

### Wear UI skill adaptation (in progress)

The requested local paths `.agents/skills/wear-compose-m3/SKILL.md`, `.agents/skills/wear-widgets/SKILL.md`, and `.agents/skills/android/SKILL.md` were not present in this checkout. The implementation used the upstream Android guidance and its linked references: [Wear Compose Material 3 skill](https://github.com/android/skills/blob/main/wear/wear-compose-m3/SKILL.md), [Wear widgets skill](https://raw.githubusercontent.com/android/skills/main/wear/wear-widgets/SKILL.md), [Android CLI skill](https://github.com/android/skills/blob/main/devtools/android-cli/SKILL.md), [Material 3 scaffold sample](https://github.com/android/skills/blob/main/wear/wear-compose-m3/references/material3/ScaffoldSample.kt.md), [migration guide](https://github.com/android/skills/blob/main/wear/wear-compose-m3/references/android/training/wearables/compose/migrate-to-material3.md), and the [official Wear Compose sample](https://github.com/android/wear-os-samples/blob/main/ComposeStarter/app/src/main/java/com/example/android/wearable/composestarter/presentation/MainActivity.kt). The widgets skill applies to Wear widgets; this full-screen app does not add a widget. The upstream Android skills repository has an Android CLI skill rather than the requested generic `android` skill.

Adapted the existing Wear app in place. It now has one `AppScaffold` at the app root; the existing pairing, session, question, and solution screens use `ScreenScaffold` with `TransformingLazyColumn`, transformed surfaces, and default list spacing. Typography and colors use Wear Material 3 theme tokens; screen preview annotations cover device shapes and font scales. The stable Wear Compose 1.7.2 preview artifact is declared alongside Material 3 1.7.2, Kotlin 2.4.10, AGP 9.5.0, and compile SDK 37. The manifest still declares only network access and no audio permission.

**Validation status**: no Java/Javac, Gradle, ADB, or Android SDK executable is available in this environment, and `apps/wear/gradlew` is absent. The earlier unit-test invocation stopped with exit 127 (`./gradlew: No such file or directory`); it did not produce a RED or GREEN test result. The new UI tests and previews have not been compiled or executed. T020–T027 remain unchecked; APK, emulator screenshots, 40/44 mm rendering, and accessibility/performance measurements remain pending.

### T028 — Authenticated WAHA message webhook

**RED** — added the webhook contract suite before creating the WAHA adapter. The first collection attempt exited 2 with `ModuleNotFoundError: No module named 'app.adapters.waha'`.

Implemented an environment-gated `/waha/webhook` route with a 1 MiB streaming body limit, WAHA SHA-512 HMAC verification over the raw request bytes, exact configured session and sender allowlists, `fromMe` and event filtering, and JPEG metadata checks. Sender identities and composite WAHA message IDs are HMAC-pseudonymized before persistence; message bodies and media URLs are not logged or stored in the inbound record. Accepted events use the existing transactional inbox/outbox ingestion service, so provider ID replays resolve through the current idempotency constraint. WAHA HMAC headers and event/media fields follow the [official WAHA event docs](https://waha.devlike.pro/docs/how-to/events/) and [receive messages docs](https://waha.devlike.pro/docs/how-to/receive-messages/).

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/contract/test_waha_webhook.py
```

Observed: `7 passed, 1 warning`. Full credential-free API suite: `77 passed, 16 skipped, 1 warning in 58.31s`; the skipped tests require a disposable PostgreSQL `TEST_DATABASE_URL`. Ruff passed and mypy reported no issues in 53 source files.

**T028 status**: complete for the authenticated, allowlisted WAHA webhook contract and idempotent event normalization. Downloading and validating remote media URLs is T029; command-to-session association is T030; durable retries and dead-letter processing are T031. `ENABLE_WAHA_INGEST` remains false by default.

### T029 — WAHA JPEG media admission and private storage

**RED** — created downloader integration tests and private-store unit tests before implementing their modules.

```sh
cd apps/api
uv run pytest -q tests/integration/test_waha_download.py
uv run pytest -q tests/unit/test_private_media_store.py
```

Observed: both collection attempts exited 2 with `ModuleNotFoundError` for the not-yet-created `app.adapters.waha.media` and `app.adapters.storage.private_media` modules.

Implemented a WAHA media downloader restricted to the configured scheme, host, and port and `/api/files/` route. It rejects userinfo, queries, fragments, encoded path tricks, redirects, unexpected MIME, and over-limit responses; requests send `X-Api-Key`, disable proxy environment inheritance, and use bounded timeouts. Responses pass through the existing JPEG decoder/admission policy (including byte/pixel limits and EXIF cleanup). The private content-addressed store verifies digest identity, writes atomically, and uses owner-only directory/file permissions. Webhook ingestion stores the normalized admitted JPEG digest. Docker Compose keeps WAHA disabled unless explicitly configured and mounts a private media volume.

**GREEN**:

```sh
cd apps/api
uv run pytest -q tests/contract/test_waha_webhook.py tests/integration/test_waha_download.py tests/unit/test_private_media_store.py
```

Observed: `21 passed, 1 warning in 8.40s`.

**REFACTOR** — full API regression and static checks:

```sh
cd apps/api
uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
docker compose --env-file infra/.env.example -f infra/docker-compose.yml config --quiet
git diff --check
```

Observed: API suite `91 passed, 16 skipped, 1 warning in 38.78s`; skips require a disposable PostgreSQL `TEST_DATABASE_URL`. Ruff passed, mypy reported no issues in 55 source files, Compose configuration parsed, and `git diff --check` passed. The warning is Starlette's deprecated `TestClient`/`httpx` bridge. WAHA live download remains untested because no isolated WAHA QA credentials/session are configured.

**T029 status**: complete for bounded JPEG download from configured WAHA media URLs and private content-addressed storage. Actual running integration with WAHA remains gated by the isolated QA environment; command association is T030 and durable retries/dead-letter handling is T031.

### T030 — WhatsApp batch commands and sender/session ownership

**RED** — added command lifecycle and ordering integration tests before creating the batch application service.

```sh
cd apps/api
uv run pytest -q tests/integration/test_batch_commands.py
```

Observed: collection exited 2 because `app.application.batches` did not yet exist. Added tests for duplicate start, 1–4 item limits, Q1–Q4 arrival order, incomplete close, empty close rejection, expiry, and fifth-photo rejection.

Implemented `BatchSessionService` around the existing `StudySession` aggregate. Exact `INICIAR` and `FINALIZAR` commands are accepted from already authorized WAHA senders; `INICIAR 1` through `INICIAR 4` override the configured default count. A sender HMAC is bound to one session at a time. Images require an active, non-expired batch; accepted JPEG hashes become ordered `questions` rows. Full batches queue automatically, incomplete non-empty batches queue on `FINALIZAR`, and expired batches reject late images. The new `sender_session_bindings` table stores only the sender HMAC and expiry. The API maps configured senders to pre-provisioned `users.id` UUIDs via `WAHA_SENDER_USER_IDS`; every allowed sender must have a mapping before WAHA ingestion is considered ready. No raw sender identity is stored in the mapping table.

Added Alembic revision `202611230004` for sender bindings and `questions.media_sha`. The first SQL-repository integration run exposed SQLite's naive timestamp reads; the adapter now normalizes naive fixture timestamps to UTC. A subsequent webhook-to-SQL integration test covers `INICIAR 3`, two ordered JPGs, and `FINALIZAR`, verifying owner, session state, question ordinals, and inbound session references.

**GREEN** — focused contract, application, SQL repository, and webhook tests:

```sh
cd apps/api
uv run pytest -q tests/integration/test_batch_commands.py tests/integration/test_batch_repository.py tests/contract/test_waha_webhook.py
```

Observed: `16 passed, 1 warning in 5.67s`.

**REFACTOR** — complete API suite and static/contract checks:

```sh
cd apps/api
uv run pytest -q
uv run ruff check .
uv run mypy app
DATABASE_URL='postgresql+psycopg://watch_ai:placeholder@127.0.0.1:15432/watch_ai' uv run alembic upgrade head --sql
cd ../..
docker compose --env-file infra/.env.example -f infra/docker-compose.yml config --quiet
python3 tools/validate_pack.py
git diff --check
```

Observed: `100 passed, 16 skipped, 1 warning in 34.22s`; skips require a disposable PostgreSQL `TEST_DATABASE_URL`. Ruff passed; mypy found no issues in 58 source files. Alembic generated the full PostgreSQL migration SQL through revision `202611230004` without connecting to a database. Compose config and pack/OpenAPI validation passed. As in T029, the single warning is Starlette's deprecated `TestClient`/`httpx` bridge.

**T030 status**: complete for batch start/finish, owner binding, ordering, expiry, and incomplete close in simulated tests. PostgreSQL migration application and real WAHA messages have not run. T031 extends this slice with an atomic inbox/outbox photo path and replay protection.

### T031 — Bounded outbox retry, dead-letter, audit, and replay safety

**RED** — added retry/dead-letter integration tests and the ten-delivery webhook test before implementing the dispatcher and atomic receipt path.

```sh
cd apps/api
uv run pytest -q tests/integration/test_webhook_retries.py
uv run pytest -q tests/integration/test_batch_repository.py::test_ten_duplicate_webhooks_create_one_question_and_one_outbox_event
uv run pytest -q tests/unit/test_outbox_audit.py
```

Observed: the retry tests first failed collection because `app.application.outbox_dispatch` did not exist. The audit test failed collection because `app.adapters.queue.audit` did not exist. The ten-replay test failed during replay before it could satisfy the one-question assertion; it exposed that T030 mutated the batch before inbox deduplication and that SQLite returns naive timestamps from the generic inbox adapter.

Implemented `OutboxDispatcher` with bounded exponential backoff, maximum attempts, claim leases, crash recovery, and terminal dead-letter state. SQL claims use row locks with `SKIP LOCKED`; only allowlisted error codes (`timeout`, `connection_error`, `processor_error`) are persisted. `StructuredOutboxAudit` logs event type, outcome, attempt count, and safe error code without exception text, sender hash, provider message ID, media digest, or image contents. Alembic revisions `202611230005` and `202611230006` add retry/lease/dead-letter columns and question ordinal on inbox records.

The WAHA photo path now checks duplicates before downloading media, then uses a per-sender PostgreSQL advisory transaction lock and persists the ordered question, inbound receipt, and outbox event in one database transaction. A replay that wins the same sender lock sees the committed receipt and returns `duplicate`; it cannot add another question or outbox job. The in-memory fake contract still tests the non-atomic ingestion port separately.

**GREEN** — focused batch, retry, outbox SQL, audit, and WAHA contract tests:

```sh
cd apps/api
uv run pytest -q tests/integration/test_webhook_retries.py tests/integration/test_batch_repository.py tests/integration/test_batch_commands.py tests/contract/test_waha_webhook.py tests/unit/test_outbox_audit.py
```

Observed: `21 passed, 1 warning in 10.43s`. This includes a SQLite lease-expiry recovery test and ten identical signed webhook deliveries resulting in one question, one inbox row, and one outbox row.

**REFACTOR** — full backend regression and static checks:

```sh
cd apps/api
uv run pytest -q
uv run ruff check .
uv run mypy app
DATABASE_URL='postgresql+psycopg://watch_ai:placeholder@127.0.0.1:15432/watch_ai' uv run alembic upgrade head --sql
```

Observed: `105 passed, 16 skipped, 1 warning in 29.64s`; the skips require a disposable PostgreSQL `TEST_DATABASE_URL`. Ruff passed; mypy reported no issues in 61 source files. Alembic generated PostgreSQL SQL through revision `202611230006` without connecting to PostgreSQL. The warning remains Starlette's deprecated `TestClient`/`httpx` bridge.

**T031 status**: complete for bounded durable outbox retries, dead-letter state, sanitized audit fields, and sequential/concurrent-safe photo replay transaction design. PostgreSQL itself has not been run here; advisory-lock behavior and migration application remain unverified against a live disposable PostgreSQL instance. A process supervisor/worker command that continuously drains the outbox and a real interpretation handler remain part of later pipeline integration, not live-provider evidence.

### T032 — Four-JPG fake pipeline to authenticated watch API

**RED** — added `apps/api/tests/e2e/test_four_question_flow.py` before the solution persistence adapter and pipeline existed. The first run failed collection because `app.adapters.db.solutions` was missing. Follow-up runs exposed implementation defects before GREEN: a missing inbound-message reader, a duplicate `question_ordinal` keyword, a missing `SolutionStepRead` import, and Pydantic step DTOs that did not accept attribute-based reads. The test therefore exercised the missing path and surfaced both wiring and contract failures.

Implemented persisted, ordered `solution_steps` with Alembic revision `202611240007`; the inbound repository now retains the batch-assigned question ordinal. `InboundMessageOutboxHandler` loads the durable inbox message and private JPEG, then calls `SolutionPipeline`, which uses the fake multimodal provider, a typed problem mapper, and `SolutionPolicy` (SymPy/Pint) before saving verified steps. The authenticated watch API now reads those steps from the database and withholds a final answer and calculation/result steps unless the required verification steps are present and marked verified.

**GREEN** — simulated four-image end-to-end flow and focused test:

```sh
cd apps/api
uv run pytest -q tests/e2e/test_four_question_flow.py
```

Observed: `1 passed, 1 warning in 40.14s`. Four generated JPEGs passed through signed fake WAHA requests, batch ordering, private-media storage, the durable outbox dispatcher, fake vision, typed mapping, SymPy/Pint verification, SQL persistence, and bearer-authenticated watch endpoints. API responses returned Q1 `2400 W`, Q2 `2*x + 3`, Q3 `9`, and Q4 `needs_review`/`inconclusive` with no final answer or calculation/result steps. The session and stored rows preserved Q1–Q4 order.

**REFACTOR** — full API regression, static checks, migration SQL, Compose, and Spec Kit validation:

```sh
cd apps/api
uv run pytest -q
uv run ruff check .
uv run mypy app
uv run alembic upgrade head --sql
cd ../..
docker compose --env-file infra/.env.example -f infra/docker-compose.yml config --quiet
python3 tools/validate_pack.py
```

Observed: `106 passed, 16 skipped, 1 warning in 100.38s`; the 16 skipped tests require an explicitly configured disposable PostgreSQL `TEST_DATABASE_URL`. Ruff passed and mypy found no issues in 64 source files. Alembic generated PostgreSQL SQL through revision `202611240007`; Compose parsed successfully; the Spec Kit validator passed all 18 required files, example JSON, OpenAPI syntax, and task IDs T001–T041. The warning remains Starlette's deprecated `TestClient`/`httpx` bridge.

**T032 status**: complete for the simulated four-JPG pipeline, ordered mathematical results, review state, and answer redaction at the watch API. No real WAHA, OpenRouter, disposable PostgreSQL instance, physical Galaxy Watch4, APK install, or continuous outbox worker was exercised by this E2E. Those remain separate validation and integration work; no external credentials were used.

### T033–T034 — Live external-provider smoke tests

**BLOCKED** — no isolated WAHA DEV session or authorized WAHA credentials were available for this run, and no approved OpenRouter key/budget was configured. No outbound WAHA or OpenRouter request was attempted. Both tasks remain unchecked; continue only after the isolated QA environment and credential/budget approval are supplied.

### T035 — Security regression coverage and Wear credential scan

**RED** — added `apps/api/tests/security/test_security_regression.py` first. The initial run had `2 failed, 2 passed`: the SQLite fixture had omitted the `questions` table needed by the session query, and the static scanner looked for `gradle.properties` under `apps/wear/app` instead of its actual `apps/wear` location. Ruff also rejected an unused import, a literal test token, and XML parsing of the trusted manifest. These were corrected in the test harness without changing production security behavior.

The new SQLite-backed tests exercise unauthenticated watch access (401), owner-scoped session listing and cross-owner 404, device revocation followed by 401, and an HMAC-valid but unauthorized WAHA sender (403). The prompt-injection regression feeds a Python side-effect expression to the safe symbolic policy and verifies `needs_review`, no final answer, and no side effect; it also checks that the OpenRouter system prompt treats image instructions as untrusted. A static source scan checks Wear production sources and Gradle configuration for OpenRouter/WAHA key literals, plus manifest backup and cleartext settings.

Existing regression tests in the same full run cover signed duplicate webhook replay (`tests/integration/test_batch_repository.py` and `tests/integration/test_webhook_retries.py`), SSRF and redirect rejection (`tests/integration/test_waha_download.py`), and corrupt, disguised, oversized, or decompression-bomb JPEGs (`tests/unit/test_jpeg_admission.py`).

**GREEN** — focused local security tests:

```sh
cd apps/api
uv run pytest -q tests/security/test_security_regression.py
```

Observed: `4 passed, 1 warning in 8.79s`. The Wear source/config scanner reported no matching provider credentials; manifest assertions confirmed `allowBackup=false` and `usesCleartextTraffic=false`.

**REFACTOR** — full API regression, lint, typing, and Spec Kit validation:

```sh
cd apps/api
uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
```

Observed: `110 passed, 16 skipped, 1 warning in 60.23s`; the skips still require an explicitly configured disposable PostgreSQL `TEST_DATABASE_URL`. Ruff passed, mypy found no issues in 64 source files, and Spec Kit validation passed all 18 required files and T001–T041 task IDs. The sole test warning remains Starlette's deprecated `TestClient`/`httpx` bridge.

**T035 status**: complete for API regression coverage and a static scan of the Wear source/configuration. This workspace has no built APK, so no packaged APK or bytecode scanner result is claimed. PostgreSQL-specific pairing/persistence cases remain skipped; security-relevant auth/revocation behavior is also exercised using SQLite in the new test.

### T036 — Configurable retention, authorized session deletion, and cache purge

**RED** — added `apps/api/tests/integration/test_retention_delete.py` and extended the Wear cache test to assert that deleting a session also removes its entry from the offline session index. The first API run failed collection because the SQL retention repository did not yet exist.

Implemented `DELETE /v1/sessions/{session_id}` with bearer authentication and owner-scoped 404 behavior. The transaction removes the session, questions, solution steps, sender binding, and pending inbound outbox rows; it clears the deleted inbox row's session/media references while keeping its deduplication metadata. Content-addressed JPGs are removed only after no other question or active inbox message references the digest. Raw JPG expiry uses `MEDIA_RETENTION_HOURS` (default 24) after question processing; session/solution expiry uses `SESSION_RETENTION_DAYS` (default 30) from completion (or creation for incomplete sessions). Expired solution records remain until the session period ends; the image digest remains in the minimal inbox metadata after the raw file is removed.

Added `python -m app.maintenance.purge_retention`, which processes bounded batches using `DATABASE_URL` and `WATCH_AI_MEDIA_DIR`. `infra/.env.example` and Docker Compose expose the two settings. The source privacy document labels these periods as proposed and requiring approval, so no scheduler or production purge was enabled. The Wear API client and controller call the DELETE route, ask for an explicit on-watch confirmation, remove cached session/question files, and update the offline session index. The existing Android cache test now verifies this index purge.

**GREEN** — focused API deletion, expiry, shared-media, and OpenAPI contract tests:

```sh
cd apps/api
uv run pytest -q tests/integration/test_retention_delete.py tests/contract/test_watch_api.py
```

Observed: `5 passed, 2 skipped, 1 warning in 13.87s`; the two contract cases need a disposable PostgreSQL database. SQLite tests confirmed 401 without credentials, 404 for another owner's session, 204 for owner deletion, removal of steps/outbox, shared-image preservation until the final reference is deleted, raw-image expiry before session expiry, digest-only inbox retention, and session expiry measured from completion time.

**REFACTOR** — full backend regression, type/style checks, pack validation, and Compose:

```sh
cd apps/api
uv run pytest -q
uv run ruff check .
uv run mypy app
cd ../..
python3 tools/validate_pack.py
docker compose --env-file infra/.env.example -f infra/docker-compose.yml config --quiet
```

Observed: `114 passed, 16 skipped, 1 warning in 73.23s`; skipped tests require an explicitly configured disposable PostgreSQL `TEST_DATABASE_URL`. Ruff passed, mypy found no issues in 68 source files, the Spec Kit validator passed, and Compose configuration parsed successfully. The warning remains Starlette's deprecated `TestClient`/`httpx` bridge.

**T036 status**: partial. Backend API, retention service/command, and Wear delete/cache code plus tests are present. The backend tests passed, but Wear JVM/instrumentation tests were not run because this workspace has no Gradle wrapper or Android SDK; no live PostgreSQL purge was run. The proposed retention values still need privacy approval before the command is scheduled in production.

### T037 — Correlated, redacted telemetry and model-cost accounting

**RED** — extended `apps/api/tests/unit/test_redacted_telemetry.py` before adding the persistent ledger. Its first run failed collection because `ModelUsageRecord` and the SQL telemetry adapter did not exist. The initial request-telemetry assertions also found that framework-generated 404 responses had a correlation response header but lacked a correlation ID in the JSON body; the Starlette HTTP exception handler was widened to cover those errors.

Implemented request correlation IDs (validated caller ID or generated UUID), correlation response headers and JSON errors, and structured HTTP logs containing only the correlation ID, method, route template, status, and duration. Metrics use bounded route-template labels and expose request counts and duration sums in Prometheus text format. The in-memory budget ledger supports local/no-database runs; with a configured SQL session factory, provider-reported OpenRouter costs are persisted in `model_usage_records`, aggregated by UTC calendar month, and checked before subsequent requests. The app exposes a server-side provider factory wired to that recorder; no provider key is put in the watch app. Added Alembic revision `202611240008`.

**GREEN** — focused behavior and redaction checks:

```sh
cd apps/api
uv run pytest -q tests/unit/test_redacted_telemetry.py
uv run ruff check app tests
```

Observed: `5 passed, 1 warning in 18.93s`; Ruff passed. The tests cover generated and accepted correlation IDs, error JSON/header correlation, query and bearer redaction, route counters and Prometheus output, in-memory monthly totals/limit behavior, SQL ledger persistence across adapter instances in SQLite, provider-reported usage cost, and absence of the test image/key markers from logs.

**REFACTOR** — full regression, typing, and offline PostgreSQL migration generation:

```sh
cd apps/api
uv run pytest -q
uv run ruff check app tests
uv run mypy app
DATABASE_URL='postgresql+psycopg://watch_ai:replace-with-a-random-local-password@127.0.0.1:15432/watch_ai' uv run alembic upgrade head --sql
```

Observed: `119 passed, 16 skipped, 1 warning in 168.65s`; skipped tests require a disposable PostgreSQL `TEST_DATABASE_URL`. Ruff passed, mypy found no issues in 71 source files, and Alembic generated SQL through `202611240008` without connecting to a database. The warning remains Starlette's deprecated `TestClient`/`httpx` bridge.

**T037 status**: complete for local request telemetry and simulated/in-process or SQLite-backed budget accounting. No PostgreSQL ledger query/write or migration was applied to a live database, and no OpenRouter request was made. Accounting is based on provider-reported `usage.cost`; the preflight check does not reserve costs for concurrent in-flight requests. Prometheus text is available from the metrics object but is not exposed through an unauthenticated HTTP endpoint.

### T038 — Backend, Wear, dependency-audit, and secret-scan workflows

**RED** — added `apps/api/tests/contract/test_ci_workflows.py` first. It failed because `.github/workflows/` did not exist. After adding the three workflow files, two further runs exposed test-harness regex mistakes for SHA-pinned action paths; those were corrected. The final contract checks YAML parsing, triggers, read-only token permissions, 40-character action SHA pins, required backend/Wear steps, and the dependency/secret scan commands.

Added `backend-ci.yml` for locked Python setup, API tests plus coverage, Ruff, mypy, and a 14-day coverage artifact; `wear-ci.yml` provisions JDK 17, Android API 36, Gradle 9.6.0, runs Wear JVM tests, compiles Android test Kotlin sources, builds the debug APK, and uploads it; `security.yml` scans repository history with Gitleaks and audits the exported, hash-pinned Python dependency set with pip-audit. The workflows use read-only repository permissions and no OpenRouter or WAHA credentials. Third-party actions are pinned to reviewed commit SHAs. CI uses a GitHub-provided read token only for Gitleaks API reads; PR comments and SARIF upload are disabled.

The first local dependency audit found 42 advisory IDs affecting the locked Pillow `12.3.0` package, all listing `13.0.0` as the fix. Updated the API constraint to `pillow>=13,<14` and lock to `13.0.0`. This was a security finding discovered while validating the workflow and is included in this slice.

**GREEN** — workflow contract and available backend checks:

```sh
cd apps/api
uv run pytest -q tests/contract/test_ci_workflows.py
uv sync --locked --all-groups
uv run pytest -q --cov=app --cov-report=xml:coverage.xml --cov-report=term-missing
uv run ruff check .
uv run mypy app
uv export --locked --all-groups --format requirements-txt --no-emit-project --output-file /tmp/watch-ai-requirements.txt
```

Observed after the Pillow update: workflow contract `1 passed`; backend regression `120 passed, 16 skipped, 1 warning in 190.27s`; total Python coverage `85%` (3,064 statements, 473 missed); Ruff passed; mypy found no issues in 71 source files. The 16 skipped tests require a disposable PostgreSQL `TEST_DATABASE_URL`.

The audit itself initially could not run through `uvx` on this workstation because its system Python lacks `ensurepip`; using the already-existing project venv avoided system changes. After exporting without the editable local project and retaining hashes, this completed:

```sh
uv pip install --python .venv/bin/python pip-audit
.venv/bin/pip-audit --strict --disable-pip --require-hashes --requirement /tmp/watch-ai-requirements.txt
```

Observed: `No known vulnerabilities found`. GitHub Actions on PR #1 subsequently
passed Backend CI and both Security Scans jobs, including Gitleaks and
`pip-audit` (runs `45363573729` and `45363573709`). The first Wear run failed
before Gradle because SDK Manager could not find API 37. Follow-up run
`45365440891` successfully installed API 36, JDK 17, and Gradle 9.6, then failed
because AGP 9 rejects `org.jetbrains.kotlin.android`. The codebase now removes
that legacy plugin and `kotlinOptions`, keeping the Compose compiler plugin.
This follows the [official AGP built-in Kotlin migration](https://developer.android.com/build/migrate-to-built-in-kotlin).

**T038 status at first PR run**: partial. GitHub Actions for commit
`6d2b74ff2b1c977676d4ce5c4916296908ab95a1` completed Backend CI successfully,
including tests, Ruff, mypy, and coverage artifact upload. Both Security Scans
jobs passed: Gitleaks history scan and `pip-audit`. Wear OS CI failed in SDK
setup before invoking Gradle because `sdkmanager` reported that
`platforms;android-37` was not found. The Android platform release list
documents Android 16/API 36; the app/workflow have been changed to API 36, and
the workflow now also compiles `androidTest` Kotlin sources. No real provider
credentials were used.

The next run (`45365440891`, commit `ed4c5a1ffe3a20db6ddabd3ffd534118e20316cc`)
installed API 36 successfully but failed before compilation because AGP 9.5
rejects the legacy Kotlin Android plugin. The app/build files removed that
plugin and the legacy `kotlinOptions` DSL, while retaining the Compose compiler
plugin. A contract test recorded RED before the change (`1 failed in 0.39s`)
and GREEN after it (`3 passed in 0.26s`).

The next Wear run (`45367334579`, commit
`2038fd72e86687ec470f2006b1acc4e83b32e7c4`) passed SDK/JDK/Gradle setup and
reached Gradle, then failed at `:app:checkDebugAarMetadata`. The exact diagnostic
was that `androidx.wear.compose:compose-material:1.7.2` requires compile API 37
or later, while the app used API 36; the metadata check reported 17 issues.
The app now uses `compileSdk = 37` and the Wear workflow installs
`platforms;android-37` and `build-tools;37.0.0` with
`sdkmanager --channel=3`. This keeps `targetSdk = 36`, so Android 17 runtime
behavior is not opted into. Android's [Android 17 SDK setup](https://developer.android.com/about/versions/17/setup-sdk)
identifies API 37 as a preview platform and directs developers to install its
SDK platform/build tools; the official [`sdkmanager` documentation](https://developer.android.com/tools/sdkmanager)
documents channel selection.

**TDD evidence for this correction** — first ran
`uv run pytest -q tests/contract/test_ci_workflows.py::test_wear_ci_installs_api_37_preview_required_by_wear_compose`
against the API 36 configuration: RED, `1 failed in 0.72s`, with the failure
at `compileSdk = 37`. After updating the app and workflow, ran
`uv run pytest -q tests/contract/test_ci_workflows.py` → `3 passed in 0.82s`
and `uv run ruff check tests/contract/test_ci_workflows.py` → `All checks passed!`.
The changed workflow has not yet run on GitHub; its SDK package availability,
Gradle compilation, unit tests, Android-test compilation, and APK upload remain
unverified.

**T038 status**: partial. Backend CI and both Security Scans passed for commit
`2038fd7`; Wear CI failed at dependency metadata as described above. The local
SDK/workflow contract is green, but the fix is not yet verified by GitHub CI.
No real WAHA/OpenRouter credentials were used.

### T039 — Performance, accessibility, offline, and regression coverage

Added `apps/api/tests/performance/test_ingestion_latency.py` to record 24 in-memory ingestion acceptance durations while both fake vision workers are held behind an event. The test asserts p95 and maximum acceptance latency stay under one second and verifies work finishes after the fake provider is released. The existing `apps/api/tests/e2e/test_fake_pipeline.py` continues to assert that accepted ingestion returns before interpretation completes. This is a characterization of the already-implemented queue behavior from T011; it passed on its first run, so no production RED failure is claimed for this test-only extension.

Extended `apps/wear/app/src/androidTest/java/com/watchai/ui/QuestionStepsScreenTest.kt` with assertions for spoken problem text, previous/next enabled state, an offline label, and four representative circular display/font-scale combinations (180/200 dp proxies, 1.3/1.5 text scale). The existing `OfflineSessionCacheTest` already covers offline reads, misses, and session deletion. These are instrumentation test sources only; no emulator execution or screenshots are available in this workspace.

**GREEN** — measured backend acceptance and async regression:

```sh
cd apps/api
uv run pytest -q -s tests/performance/test_ingestion_latency.py tests/e2e/test_fake_pipeline.py
uv run ruff check tests/performance/test_ingestion_latency.py tests/e2e/test_fake_pipeline.py
```

Observed: `3 passed in 0.43s`; Ruff passed. Latest run measured `p95=2.471 ms`, `max=6.531 ms` over 24 in-memory acceptances. A prior repeat measured `p95=17.576 ms`, `max=18.128 ms`. The fake provider remained blocked until all webhook-equivalent application acceptances returned, and all 24 jobs then completed. These measurements exclude HTTP, PostgreSQL, WAHA, storage I/O, OpenRouter, device rendering, and network time; they are queue handoff measurements, not end-to-end production latency.

**T039 status**: partial. Backend performance and async behavior are measured; Compose instrumentation sources now describe accessibility, offline, and representative circular bounds. Those Wear tests, screenshot checks, actual 40/44 mm emulator configurations, and the app's 1.3/1.5 system font scale remain unverified because Android tooling is unavailable. No physical or emulator compatibility claim is made.

### T040 — Deployment, migration, retention, backup, and incident runbooks

Added the isolated staging procedure to `docs/09_ENV_RUNBOOK.md` and clarified
that the current Compose definition is loopback-only local/staging infrastructure,
not a production deployment, in `infra/README.md`. The runbook covers protected
server-side secrets, WAHA isolation, a separate Alembic release step, an
expand/transition/contract sequence, the destructive nature of current
downgrades, paired database/media backup and recovery, manually scheduled
retention, incident actions, and rollback boundaries. No deploy, backup, restore,
provider request, or retention purge was performed.

The new contract test first failed because the runtime image did not contain
`alembic/` or `alembic.ini`, making the documented migration command impossible
inside that image. Added both assets to the runtime stage of `apps/api/Dockerfile`.
During the same audit, found that Compose did not pass `MONTHLY_MODEL_BUDGET_USD`
to the API; wired it through and added a blank approval placeholder to
`infra/.env.example`.

**RED** — `uv run pytest -q tests/contract/test_deployment_artifact.py` initially
failed with the missing Alembic-copy assertion (`1 failed in 0.49s`).

**GREEN** — the contract passed after the Dockerfile and Compose changes:
`uv run pytest -q tests/contract/test_deployment_artifact.py` → `1 passed in
0.11s`; `uv run ruff check tests/contract/test_deployment_artifact.py` → `All
checks passed!`. The full API regression then reported `122 passed, 16 skipped,
1 warning in 117.50s`; the skips require an explicitly disposable
`TEST_DATABASE_URL`, and the warning is the existing Starlette/httpx deprecation.
`uv run ruff check .` passed and `uv run mypy app` found no issues in 71 source
files. `docker compose --env-file infra/.env.example -p watch-ai-staging -f
infra/docker-compose.yml config --quiet` exited successfully; the Spec Kit
validator passed all 18 required files, example JSON, OpenAPI syntax, and task
IDs T001–T041.

Attempted `docker compose ... build api` to verify the final runtime image.
BuildKit completed the builder stage and showed both migration `COPY` steps, but
stalled during image export for more than seven minutes; the build was manually
interrupted with exit 130. The following `alembic --version` container command
therefore did not run. The Docker image build remains unverified; no claim is
made that the final image was produced.

**T040 status**: complete as documentation/configuration and contract scope.
Production hosting, TLS ingress, secret management, backup storage/scheduler,
restore drill, and final Docker image export remain external/unverified work.

### T041 — Final review and release evidence

The final staged review covers 220 files (20,618 insertions); `git diff --cached
--check` passed. A filename-only scan found no local `.env`, APK/AAB, JKS, or
keystore artifacts. A repository scan for common OpenRouter/GitHub/cloud key and
PEM patterns returned no matching files. This is a local pattern scan, not a
Gitleaks workflow result. The branch starts at `7b8cc95` (`origin/main`) and
there was no existing remote branch or PR for `feat/001-watch-ai-mvp`.

Final review found a production-blocking device revocation gap: the only
implemented endpoint, `DELETE /v1/devices/me`, requires the token of the device
being revoked. It cannot revoke a lost watch remotely. The runbook and security
report now state that limitation; an owner/admin revocation workflow must be
implemented before a production launch. Do not treat self-revocation as lost
device recovery.

No debug APK, screenshot, APK hash, Android build, or instrumented Wear test is
available because Java/Gradle/Android SDK tooling is missing. The Docker image
build also stalled at final export and was interrupted; it does not qualify as
a build pass. No physical hardware or live WAHA/OpenRouter credentials were
available/used, and no deployment, database backup/restore, retention purge,
merge, or production action was performed. The 16 PostgreSQL tests remain
skipped pending an explicitly disposable test database.

The latest backend regression evidence remains `122 passed, 16 skipped, 1
warning`; Ruff, mypy, Compose config, and pack validation passed. For draft PR
[#1](https://github.com/MrGr33n98/watch-ai/pull/1), Backend CI and Security
Scans passed on commit `2038fd7`; Wear CI failed at the dependency metadata
check because API 37 was required. The local API 37 configuration contract is
green, and a GitHub run after that fix is pending. No APK or screenshots were
produced by the failed CI run. The draft remains a review handoff, not release
readiness. T041 remains partial; device-loss revocation, PostgreSQL integration,
and live-provider checks also remain pending regardless of PR status. No merge
or deployment was performed.
