# Roadmap e Story Points — 6 etapas

Estimativas são planejamento, não datas nem horas garantidas.

| Sprint | Entregas | SP (Fibonacci) | Critério de saída |
|---|---|---:|---|
| S0 — Discovery | hardware PoC, Wear4 ADB, Spec Kit, ADR, openapi | 13 | G01-G03 documentados |
| S1 — Backend mock | FastAPI, DB, schemas, fixtures, sessões, TDD, CI | 21 | 4 JPG sintéticos processados com fake vision |
| S2 — Matemática | extração schema, SymPy, Pint, verificação, `needs_review`, renderer | 21 | golden tests com resultado correto |
| S3 — Wear OS | 7 telas, cache, layout redondo, pareamento, API, testes UI | 34 | APK debug emulador+Watch4 |
| S4 — WAHA | adapter webhook/media, autorização, idempotência, fila, E2E | 21 | pipeline real via WhatsApp em ambiente isolado |
| S5 — Hardening | segurança, acessibilidade, observabilidade, custos, perf, docs, release | 21 | gates e runbook aprovados |
| **Total aproximado** |  | **131 SP** | Não é previsão de duração |

## Dependências críticas

- S0 desbloqueia instalação no hardware.
- S1 pode começar com mock antes da câmera.
- S2 usa schema estabilizado em S1.
- S3 pode avançar em paralelo a S2 com API fake.
- S4 só integra depois de idempotência/autorização.
- S5 não pode ser ignorada para execução contínua.

## Definition of Ready

Story tem valor de usuário, evento de entrada, estados de erro, critérios Given/When/Then, risco, estimativa, contrato, testes propostos e owner.

## Definition of Done

Teste RED documentado, implementação GREEN, refactor, lint/typecheck, segurança, contrato, tela acessível, 0 regressão crítica, evidência em PR, atualização de documentação e rollback claro; sem secrets, sem merge/deploy sem aprovação.
