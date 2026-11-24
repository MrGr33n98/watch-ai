# CI/CD Specification — GitHub Actions

Workflows propostos: `.github/workflows/backend-ci.yml`, `wear-ci.yml`, `security.yml` e `release-manual.yml`.

## Backend CI

- triggers: pull_request + push em main; concurrency cancel-in-progress na mesma branch.
- job checkout -> setup Python 3.12 -> setup uv/cache -> `uv sync --frozen --all-groups` -> `uv run ruff check .` -> `uv run mypy app` -> `uv run pytest --junitxml=test-results/pytest.xml --cov=app --cov-report=xml` -> OpenAPI validate/diff -> subir DB de teste via service container.
- mocks de WAHA/OpenRouter; nenhum segredo real em testes de PR.
- artifacts: reports XML, openapi diff, logs sanitizados.

## Wear CI

- checkout -> setup JDK compatível -> Android SDK component installation -> Gradle cache -> `./gradlew --no-daemon lint testDebugUnitTest assembleDebug` -> upload APK debug + HTML/XML reports.
- Instrumentation/E2E UI: emulador Wear OS no job compatível com aceleração KVM ou em hardware lab; não marcar sucesso se não foi executado. Fallback: agendar device-farm manual; marcar gate como PENDING, não PASS.

## Security CI

- Secret scan (`gitleaks`), dependency audit (uv pip audit/gradle dependency scanning), static scanners, SBOM opcional, container scan, pinned workflow actions to full SHA.
- CI não deve puxar/usar QR code de WhatsApp real ou OpenRouter key para PRs de forks.

## Release Manual

- gatilho workflow_dispatch somente aprovado; checar CI + security + testes físicos + version bump.
- runtime compose de backend isolado, health probes, migration, smoke, rollback.
- Android APK assinado com key fora do repositório, distribuído internamente; não confundir APK debug com release.
- Não publicar em Galaxy Store/Play Store sem políticas de dados e revisão.

## Gate matrix

Unit: obrigatório. Integration: obrigatório. Contract: obrigatório. Security: obrigatório. Compose UI: obrigatório. Device physical: obrigatório antes de concluir hardware. Live WAHA/OpenRouter: smoke isolado documentado antes de release. Visual: screenshot auditado para dois tamanhos. Coverage e tempo de execução reportados, sem inventar números.
