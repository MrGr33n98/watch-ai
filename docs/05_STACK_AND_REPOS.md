# Stack, referências e estratégia de implantação

## Referências oficiais (estudar, NÃO copiar código sem revisar licença)

| Projeto | Link | Aproveitamento correto |
|---|---|---|
| GitHub Spec Kit | https://github.com/github/spec-kit | processo constitution/spec/plan/tasks/implement |
| Android Wear OS Samples / ComposeStarter | https://github.com/android/wear-os-samples | estrutura de app Watch e Wear Compose |
| Google Horologist | https://github.com/google/horologist | padrão de desenvolvimento para Wear; evitar importar libs que não sejam necessárias |
| WAHA | https://github.com/devlikeapro/waha | documentação e exemplo de webhook/media; validar licença e engine instalados |
| OpenRouter docs | https://github.com/OpenRouterTeam/docs | contrato multimodal e escolha de modelos |
| SymPy | https://github.com/sympy/sympy | avaliação simbólica; diferenças entre `sympify` e parsing seguro |
| Pint | https://github.com/hgrecco/pint | operações dimensionais e conversões |
| FastAPI | https://github.com/fastapi/fastapi | app API/validação e testes TestClient |
| uv | https://github.com/astral-sh/uv | pin, lock e gerenciamento Python |

## Versões e pinning

- Python alvo: 3.12+; fixar versão minor e dependências em `uv.lock` após resolver compatibilidade no ambiente.
- Kotlin/AGP/Gradle/JDK: obter matriz de compatibilidade diretamente do projeto `ComposeStarter` e Android docs ao inicializar; não combinar números arbitrários.
- `androidx.wear.compose:compose-material3` e `foundation`: seguir documentação Android vigente e testar no API real do Watch4.
- Android SDK: usar SDK Manager CLI + Gradle Wrapper; IDE Android Studio é opcional para CI e build, útil para emulador/UI.
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2/Alembic, httpx, Pillow, SymPy, Pint, pytest, respx, Ruff, mypy, Bandit/Pip-Audit.
- Fila MVP: PostgreSQL jobs com SKIP LOCKED ou fila dedicada só se justificada; evitar Redis/Sidekiq desnecessários na VM de desenvolvimento.
- Storage: filesystem privado sob volume Docker, interface S3 compatível opcional para produção.
- Render LaTeX: no MVP gerar imagem por método seguro com fallback texto; considerar MathJax->SVG em serviço isolado, sanitizar SVG e avaliar custo RAM; evitar executar TeX não confiável em shell.
- E2E: pytest/httpx + mocks de WAHA/OpenRouter, Android emulator instrumentation; prova real só na Watch4 física.

## Estrutura de monorepo proposta

```
watch-ai/
├── .github/workflows/{backend-ci.yml,wear-ci.yml,security.yml}
├── .specify/memory/constitution.md
├── specs/001-watch-ai-mvp/{spec.md,plan.md,tasks.md,research.md,data-model.md,contracts/}
├── apps/
│   ├── api/
│   │   ├── app/{domain,application,adapters,infrastructure}/
│   │   ├── tests/{unit,integration,contract,e2e}/
│   │   ├── pyproject.toml
│   │   └── alembic/
│   └── wear/
│       ├── app/src/{main,test,androidTest}/
│       ├── gradle/libs.versions.toml
│       └── gradlew
├── infra/{docker-compose.yml,.env.example,README.md}
├── fixtures/{golden,blurry,invalid,webhooks}/
├── docs/{ADR,runbooks,security,observability}/
└── tools/
```

## Segurança crítica

Não reutilizar diretamente a API WAHA de Avalia Solar em produção sem isolamento de sessão, webhook, credenciais, storage, quotas e verificação de memória/capacidade. Logs sem dados de exercícios nem número de WhatsApp em claro. `OPENROUTER_API_KEY`, `WAHA_API_KEY`, `DATABASE_URL` somente no backend/CI secrets. TLS obrigatório no watch; nada de `usesCleartextTraffic=true` para produzir APK.

## Plataforma física

Galaxy Watch4 não emparelha com iOS; configurar inicialmente com Android via Galaxy Wearable. Depois testar ADB Wi-Fi e tráfego HTTPS direto; confirmar que o relógio em questão suporta a API de Compose/SDK prevista. Foto Y3000: JPG lido do microSD por leitor Lightning; validar cartão, JPEG e compatibilidade do leitor em hardware real.
