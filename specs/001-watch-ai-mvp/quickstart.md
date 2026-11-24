# Quickstart — Watch AI MVP

## Ambiente e estado inicial

O repositório usa Spec Kit 1.0.11 com integração Codex skills. A feature ativa fica em `.specify/feature.json`; os comandos Spec Kit são skills do agente, não comandos do shell. A branch de implementação é `feat/001-watch-ai-mvp`.

Para desenvolvimento local, instale Python 3.12+, `uv`, Docker Compose v2 e uma versão de JDK/Android SDK compatível com as versões fixadas pelo Gradle Wrapper. Não escolha versões Android/Kotlin independentemente: confira a matriz oficial Wear Compose e os arquivos de versão do projeto.

## Validação da API local

Depois que a fatia backend estiver implementada:

```sh
cd apps/api
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run mypy app
```

O modo de desenvolvimento usa fake vision e fixtures sintéticas; não precisa de WAHA ou OpenRouter real. Para integração persistente, inicie apenas os serviços locais definidos em `infra/docker-compose.yml` e aplique as migrations conforme `docs/09_ENV_RUNBOOK.md`.

## Validação do relógio

Depois que `apps/wear` estiver implementado:

```sh
cd apps/wear
./gradlew lint testDebugUnitTest assembleDebug
```

Testes instrumentados exigem um emulador Wear OS configurado. A prova em Galaxy Watch4 real também exige setup prévio em Android compatível, Wireless Debugging e `adb devices` com o relógio conectado.

## E2E e integrações externas

O E2E de CI deve percorrer quatro JPGs sintéticos → WAHA fake → API → fake OpenRouter → verificador → armazenamento → contrato do watch. Desative a rede externa ou injete fakes para demonstrar que o fluxo não usa credenciais reais.

Executar smoke real somente em ambiente QA explicitamente isolado, com remetente e sessão WAHA de teste e uma credencial OpenRouter aprovada com limite de custo. Não usar sessão WAHA produtiva nem publicar chaves em arquivo, logs ou APK. Consulte `tests/acceptance/E2E_RUNBOOK.md` para os gates físicos e externos.
