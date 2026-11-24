# Tasks: Watch AI Math Study Companion

**Input**: Design documents under specs/001-watch-ai-mvp/.
**Source of truth**: Keep IDs, order, and acceptance intent T001–T041 from the supplied pack.
**Source priority/estimate**: All source tasks are P0. Pack estimates are 13 SP for Phase 0, 21 SP for Phases 1, 2, 4, and 5, and 34 SP for Phase 3 (131 SP total); these remain relative estimates, not schedule commitments.
**TDD**: For every implementable task, run a deterministic test first (RED), implement the minimum change (GREEN), then refactor and rerun related checks. Record exact commands and outputs in docs/reports/watch-ai-validation-20261123.md.
**Status**: Mark [X] only when evidence exists. Hardware and real-provider work stays pending until an authorized environment is available.

## Phase 0: Preflight, Spec Kit, and Hardware

- [X] T001 Inspect main, tree, commits, and local changes; record 7b8cc95fb43a95ea64d0fadcb82c1f9f67e6e364 and the README-only tracked tree in docs/01_DISCOVERY.md and specs/001-watch-ai-mvp/research.md; create feat/001-watch-ai-mvp for the requested review PR.
- [X] T002 Use installed Specify CLI 1.0.11/Codex skills; reconcile .specify/memory/constitution.md, .specify/feature.json, specs/001-watch-ai-mvp/spec.md, plan.md, research.md, contracts/openapi.yaml, and tasks.md without rerunning init --force.
- [ ] T003 [US1] Test Y3000, microSD, Lightning reader, and iPhone 14 with four original JPGs; record focus, resolution, orientation, and import evidence in docs/reports/watch-ai-validation-20261123.md.
- [ ] T004 [US3] Configure Watch4 from compatible Android, enable Wireless Debugging, install/launch APK, and verify HTTPS; record device and ADB evidence in docs/reports/watch-ai-validation-20261123.md.
- [ ] T005 [US2] Complete approved model/budget and isolated WAHA DEV readiness; document ADRs in docs/adr/ and evidence in docs/reports/watch-ai-validation-20261123.md. Never use production WAHA.

## Phase 1: API and Domain Foundation

- [X] T006 Create apps/api/ FastAPI/Python 3.12 project, uv.lock, GET /health, Docker setup, and POST /dev/ingest gated to development/test only (404 elsewhere). First add apps/api/tests/integration/test_health.py and test_dev_ingest.py, capture RED, then implement and capture GREEN. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T007 Model StudySession, QuestionItem, ordering, and lifecycle in apps/api/app/domain/sessions/; first add apps/api/tests/unit/test_study_session.py for 1–4 items, fifth-item rejection, and transitions. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T008 Add PostgreSQL SQLAlchemy mappings, Alembic migrations, and constraints in apps/api/app/adapters/db/ and apps/api/alembic/; first add apps/api/tests/integration/test_persistence.py for unique order, foreign keys, and constraints. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T009 Add inbound-message deduplication, outbox, and unit-of-work ports in apps/api/app/domain/ingestion/ and apps/api/app/application/; first add apps/api/tests/unit/test_idempotency.py for duplicates and out-of-order events. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T010 Implement GET /v1/sessions, /v1/sessions/{id}, and /questions/{ordinal} in apps/api/app/adapters/http/; first add apps/api/tests/contract/test_watch_api.py against specs/001-watch-ai-mvp/contracts/openapi.yaml, including 401 and cross-device denial. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T011 Add async job handling and deterministic FakeVisionProvider in apps/api/app/application/ and apps/api/app/adapters/queue/; first add apps/api/tests/e2e/test_fake_pipeline.py proving webhook acceptance does not wait for interpretation. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T012 Add one-time pairing codes, scoped watch tokens, ownership, and revocation in apps/api/app/domain/delivery/ and apps/api/app/adapters/http/; first add apps/api/tests/integration/test_pairing.py for expiry, reuse, access denial, and revocation. Evidence: docs/reports/watch-ai-validation-20261123.md.

## Phase 2: Interpretation, Verification, and Presentation

- [X] T013 [US2] Define VisionProvider and OpenRouter adapter with typed output, safe prompt, timeout, and bounded retries in apps/api/app/application/ports/ and apps/api/app/adapters/openrouter/; first add apps/api/tests/contract/test_openrouter_provider.py for valid/invalid JSON, missing fields, 429, and timeout. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T014 [US1] Validate JPEG bytes, MIME, decode, size/pixels, and EXIF in apps/api/app/domain/ingestion/ and apps/api/app/adapters/storage/; first add apps/api/tests/unit/test_jpeg_admission.py for valid, corrupt, disguised, oversized, rotated, and bomb inputs. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T015 [US2] Parse expressions with a typed AST allowlist in apps/api/app/domain/math_verification/; first add apps/api/tests/unit/test_safe_expression.py rejecting eval, imports, attributes, arbitrary calls, excess depth, and unknown symbols. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T016 [US2] Verify supported algebra, derivatives, and definite integrals with SymPy in apps/api/app/adapters/math/; first add apps/api/tests/unit/test_symbolic_verifier.py for GOLD-DERIV-002, GOLD-INTEGRAL-003, and unsupported input. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T017 [US2] Verify physical quantities and conversions with Pint/Decimal in apps/api/app/adapters/math/; first add apps/api/tests/unit/test_dimensional_verifier.py for GOLD-FOURIER-001, GOLD-UNIT-004, and incompatible dimensions. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T018 [US2] Build ordered solution steps and verified/needs_review policy in apps/api/app/domain/math_verification/ and apps/api/app/application/; first add apps/api/tests/integration/test_solution_policy.py for ambiguity, missing data, unsupported math, and goldens. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T019 [US2] Render supported formulas to private bounded assets with text fallback in apps/api/app/adapters/renderer/; first add apps/api/tests/integration/test_formula_rendering.py for fractions, roots, integrals, indices, Greek symbols, limits, and fallback. Evidence: docs/reports/watch-ai-validation-20261123.md.

## Phase 3: Wear OS Native App

- [ ] T020 [US3] Scaffold apps/wear/ as standalone Kotlin/Compose for Wear OS Material 3 using compatible pinned toolchains; first add a JUnit/Compose test under apps/wear/app/src/test/ and capture RED.
- [ ] T021 [US5] Add pairing and Android Keystore token storage in apps/wear/app/src/main/; first add tests under apps/wear/app/src/test/ for storage, expiry, clearing, and revocation.
- [ ] T022 [US3] Add versioned HTTPS DTOs, repository, timeouts, and error mapping in apps/wear/app/src/main/; first add MockWebServer tests under apps/wear/app/src/test/ for success, 401, timeout, and malformed response.
- [ ] T023 [US3] Build session list and Q1–Q4 states in apps/wear/app/src/main/; first add Compose UI tests under apps/wear/app/src/androidTest/ for empty, loading, processing, ready, partial, and review.
- [ ] T024 [US3] Build statement/data/formula/substitution/calculation/verification/result steps and previous/next controls in apps/wear/app/src/main/; first add UI tests for every step and accessibility labels.
- [ ] T025 [US4] Add app-private offline cache, stale indicator, and reconnect behavior in apps/wear/app/src/main/; first add tests for cached read, cache miss, offline, and deletion.
- [ ] T026 [US3] Verify round safe areas, 40/44 mm, 1.3/1.5 text scale, touch targets, contrast, and no audio permission in apps/wear/app/src/androidTest/; capture screenshots before visual refinements.
- [ ] T027 [US3] Build debug APK and sanitized emulator screenshots under apps/wear/build/outputs/apk/debug/; record hashes in docs/reports/watch-ai-validation-20261123.md. Mark physical install only with ADB evidence.

## Phase 4: WhatsApp and WAHA Adapter

- [X] T028 [US1] Normalize WAHA events and enforce webhook auth, session allowlist, fromMe filter, and sender authorization in apps/api/app/adapters/waha/; first add apps/api/tests/contract/test_waha_webhook.py. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T029 [US1] Download media only from configured WAHA host, with redirects disabled and X-Api-Key header, supporting image/JPEG document in apps/api/app/adapters/waha/; first add apps/api/tests/integration/test_waha_download.py for SSRF, MIME, auth, timeout, and size. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T030 [US1] Implement INICIAR/FINALIZAR and sender-to-session association in apps/api/app/application/ and apps/api/app/domain/sessions/; first add apps/api/tests/integration/test_batch_commands.py for order, incomplete close, expiry, and fifth item. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T031 [US1] Add bounded retry, dead-letter state, replay safety, and sanitized audit in apps/api/app/application/ and apps/api/app/adapters/queue/; first add apps/api/tests/integration/test_webhook_retries.py for crash/retry and ten duplicate deliveries. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T032 [US1][US2][US3] Run four JPG fake WAHA → API → FakeVisionProvider → SymPy/Pint → database → watch API in apps/api/tests/e2e/test_four_question_flow.py; verify order, goldens, review state, and redaction. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [ ] T033 [US1] **BLOCKED** — requires an isolated WAHA DEV session and approved credentials; no live call was made. See docs/reports/watch-ai-validation-20261123.md.
- [ ] T034 [US2] **BLOCKED** — requires an approved OpenRouter key and budget; no live call was made. See docs/reports/watch-ai-validation-20261123.md.

## Phase 5: Security, CI, and Release Readiness

- [X] T035 [US5] Test 401/403, ownership, revocation, replay, SSRF, hostile images, prompt injection, and APK secrets in apps/api/tests/security/ and apps/wear/; record actual scanner results. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [ ] T036 [US6] PARTIAL — API deletion/retention, owner/admin remote device revocation, and Wear cache-delete flow are implemented; PostgreSQL backend checks pass (157 passed, 0 skipped). Wear unit/instrumentation execution awaits the updated GitHub Actions Wear OS CI run. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T037 Add correlation IDs, redacted structured logs, durable monthly model-cost accounting, and request metrics in apps/api/app/infrastructure/; first add apps/api/tests/unit/test_redacted_telemetry.py asserting private data is absent. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [ ] T038 PARTIAL — Backend CI, PostgreSQL checks, Compose live smoke, and Wear workflow contract pass locally; `.github/workflows/wear-ci.yml` now targets channel-0 emulator `api-level: 34` (`android-wear`) with fixed UI/cache test selectors awaiting GitHub Actions validation on push. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [ ] T039 PARTIAL — measured async-ingestion latency, Docker worker processing, and updated Wear accessibility/offline/polling sources are verified on the backend; Wear emulator instrumentation execution awaits GitHub Actions validation. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [X] T040 Document isolated deploy, expand/contract migrations, retention, secrets, backup, incident response, and rollback in docs/09_ENV_RUNBOOK.md and infra/README.md; align the runtime image with Alembic and pass the monthly budget setting through Compose. Evidence: docs/reports/watch-ai-validation-20261123.md.
- [ ] T041 PARTIAL — MVP backend + `/phone` console + worker + remote revocation + Docker live smoke are verified (`157 passed`, `0 skipped`); Wear OS CI run on this push will confirm APK/screenshot artifacts while physical hardware and live-provider gates remain pending. No merge or deployment. Evidence: docs/reports/watch-ai-validation-20261123.md.

## Dependency Order

- T001–T002 establish repository and Spec Kit. T003–T005 gate physical/live readiness but do not block fake-based development.
- T006 precedes T007–T012. T008/T009 precede ingestion and worker integration; T010–T012 establish the watch API and authorization.
- T013–T019 depend on domain/API contracts. Unsafe images and expressions must be rejected before interpretation or symbolic operations.
- T020–T027 consume the stable watch contract; emulator work does not require a physical device.
- T028–T032 depend on image admission, contract, and idempotency. T033–T034 require approved QA credentials.
- T035–T041 depend on code slices. Skipped physical/live checks are never reported as passing.
