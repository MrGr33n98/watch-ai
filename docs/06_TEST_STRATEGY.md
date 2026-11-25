# Estratégia de qualidade — TDD, contratos, E2E, não-funcionais

## Pirâmide

1. **Domínio unitário (>= 60%)**: determinístico, sem rede; lote de quatro, deduplicação, transições de estado, parser de expressões, unidade Pint, regras de retenção.
2. **Contratos (>= 20%)**: OpenAPI schema request/response; WAHA media `image` e `document`; OpenRouter JSON inválido/válido; watch DTO e migração de schema.
3. **Integração (>= 15%)**: DB real de teste, worker, armazenamento, inbox/outbox, mock server WAHA/OpenRouter.
4. **E2E (<= 5%)**: fixture JPG -> callback -> status -> resposta -> render -> emulador/Watch4. Execução real de WhatsApp/OpenRouter é smoke controlado, não CI ordinário.

## Ciclo TDD obrigatório

Para cada tarefa implementável: escrever teste RED baseado em contrato -> executar e capturar falha -> menor código GREEN -> refatorar preservando teste -> reexecutar testes relacionados + gates -> commit com evidência. Não declarar sucesso a partir de testes apenas estáticos ou marcados skip.

## Suítes e casos

| ID | Camada | Caso | Resultado esperado |
|---|---|---|---|
| UT-01 | Domain | criar lote com 4 JPG | ordens 1..4, status collecting |
| UT-02 | Domain | quinto JPG em lote | 409 ou nova sessão, nunca sobrepor |
| UT-03 | Domain | webhook duplicado | registro único e custo IA único |
| UT-04 | Domain | eventos fora de ordem | estado monotônico por versão |
| UT-05 | Math | k1.2, A10, dT40, L0.2 | 2400 W |
| UT-06 | Math | derivada x² + 3x | 2x + 3 |
| UT-07 | Math | integral de 2x em [0,3] | 9 |
| UT-08 | Units | m², W/(m K), K, m | saída W |
| UT-09 | Security | `eval`, `import os`, input malicioso | proibido, needs_review |
| CT-01 | WAHA | imagem recebida no webhook | idempotência e enfileiramento |
| CT-02 | WAHA | imagem enviada como documento | mime JPEG e filename tratados |
| CT-03 | OpenRouter | JSON com campos ausentes | `needs_review`; nunca travar |
| CT-04 | OpenRouter | resposta maliciosa | ignorar instruções da imagem |
| CT-05 | API | cliente não autorizado | 401 sem detalhes |
| CT-06 | API | acesso à sessão de outro dispositivo | 403/404 |
| IT-01 | Data | worker crash após download | retry sem duplicar |
| IT-02 | Storage | mídia > limite ou zip disguised as jpg | 415/413 |
| IT-03 | Storage | EXIF orientação/arquivo corrompido | normalizar/rejeitar |
| IT-04 | DB | tombstone/delete cascade | arquivo e registros limpos |
| E2E-01 | User | 4 JPG -> 4 soluções verificadas | Watch4 Q1..Q4 |
| E2E-02 | User | JPG borrado | needs_review e sem resultado inventado |
| E2E-03 | Watch | offline ao iniciar | cache e erro explícitos |
| E2E-04 | Watch | trocar entre Q1 e Q4 | sem cortar fórmulas |
| E2E-05 | Device | token revogado | 401 e reset seguro do pareamento |
| PERF-01 | API | 50 requests status/s | latência p95 conforme meta |
| PERF-02 | Worker | 4 imagens com provider lento | API responde 202 rapidamente |
| PERF-03 | Watch | polling ativo 15s -> background | pausa/backoff, consumo monitorado |
| A11Y-01 | Watch | font scale 1.3/1.5 | texto legível e scroll |
| SEC-01 | Secrets | APK descompilado e logs | nenhum segredo provider |

## Golden data

`examples/golden_cases.json`: casos simbólicos e físicos com valores conhecidos. `tools/generate_study_jpgs.py` gera quatro JPGs sintéticos para teste de pipelines; **não simula lente Y3000**, que precisa de ensaio separado de hardware.

## Matriz de dispositivos

- Emulador Wear OS redondo API 30+; duas densidades/tamanhos.
- Watch4 físico 40 e/ou 44 mm quando disponível; testar bezel, scroll, toque, modo economia, Wi-Fi.
- iPhone 14: microSD Lightning importação JPG, WhatsApp documento.
- Browser/CI Linux: testes API, contrato e fixtures (sem conta WhatsApp real).

## Instrumentation e evidências

- `pytest -q`, `ruff check .`, `mypy`, `pytest --cov ... --cov-fail-under=85` para backend (meta inicial, ajustar ao volume de código).
- Android `./gradlew lint testDebugUnitTest connectedDebugAndroidTest assembleDebug` com tasks condicionalmente disponíveis.
- Contract diff OpenAPI, versionamento e snapshot/golden do schema.
- Screenshots do app no emulador + relógio; manifesto de versões, ADB e hashes.
- Fuzzing limitado do parser simbólico, incluindo payloads hostis.
- Pipeline deve gerar artifacts de JUnit XML, cobertura, APK debug e screenshots; nunca screenshots com dados pessoais em CI público.

## Critérios para release

Nenhum job crítico vermelho; 0 `skip` injustificados em requisitos P0; análise de segurança sem críticas abertas; `needs_review` funcional; 4 golden cases; transição offline; upload sem vazamento; build assinável; instalação real verificada; rollback documentado.
