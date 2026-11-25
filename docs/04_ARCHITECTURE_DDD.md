# DDD — Domain Model, Bounded Contexts e arquitetura

## Context Map

```
[Capture/Import (externo: Y3000, iPhone)]
            |
     [WhatsApp / WAHA ACL] -- Anti-Corruption Layer / trusted webhook adapter
            |
   [Ingestion Context] -- ImageReceived
            v
    [Session Context] -- BatchReady
            v
   [AI Interpretation] -- StatementParsed / NeedsReview
            v
  [Math Verification] -- SolutionVerified / VerificationInconclusive
            v
 [Presentation Context] -- StepsRendered
            v
  [Delivery/Watch API] -- SessionReady / SyncCursor
```

### 1. Ingestion BC

Entidades: `ReceivedMedia`, `InboundMessage`. Aggregate Root: `InboundMessage` pelo `provider_message_id`. Value Objects: `MessageId`, `MimeType`, `Sha256`, `SenderId`, `ImageDimensions`. Serviço de domínio: `ImageAdmissionPolicy`. Invariantes: rejeitar mídia não-JPEG, dados > limite, sender não autorizado, duplicidade; não confiar apenas no MIME; EXIF orientation corrigida; validar magic bytes e `Pillow.verify()` em sandbox; limite de pixels para mitigar descompressão.

### 2. Session/Batch BC

Aggregate root: `StudySession`; children `QuestionItem` (slots 1..4). Value Objects `QuestionOrder`, `SessionStatus`, `QuestionStatus`, `SessionId`. Invariantes: máximo de quatro questões por sessão; ordem de chegada preservada; questão não pode ser `ready` sem steps validáveis; `partial` possível, não travar lote por uma foto ilegível. Emparelhamento explícito remetente->sessão; mensagem comando `INICIAR`, fotos, `FINALIZAR` ou alternativa de lote definido no backend. Sessão criada automaticamente com comando idempotente; mensagens fora de sessão podem receber instruções sem processar. Não permitir que contato aleatório reivindique sessão do relógio.

### 3. AI Interpretation BC

Aggregate: `InterpretationJob`. Adapter `VisionModelPort` recebe JPG privado e extrai enunciado, unidades, símbolos, alternativas e score qualitativo; devolve JSON validado pelo schema. O modelo não é domínio: respostas sempre normalizadas em `ProblemStatement`. Se houver baixa legibilidade, símbolos alternativos ou falta de dados, emitir `needs_review`, sem imputar valores. Configurar modelo via `OPENROUTER_VISION_MODEL` selecionado dentre modelos com visão; tempo/custos limitados. Não executar texto presente na imagem como instrução de sistema (prompt-injection).

### 4. Math Verification BC

Aggregate: `SolutionAttempt`. Value Objects: `Expression`, `Quantity`, `Unit`, `VerificationStatus`, `Step`. Domain Services: `SymbolicValidator(SymPy)`, `DimensionalValidator(Pint)`, `NumericalTolerancePolicy`. Invariantes: cálculo numérico reavaliado localmente para casos suportados; passos não verificados rotulados; conversão dimensional obrigatória onde aplicável; `verified=true` somente com evidência do verificador. Não executar código arbitrário, comandos shell ou `eval`; parser simbólico com allowlist e limites de tempo/complexidade, preferencialmente AST de operações tipadas.

### 5. Presentation BC

Entidade: `RenderedStep`. VO: `MathNotation`, `AltText`, `RenderArtifact`. Renderizador de notação gera artefato pequeno em backend (SVG sanitizado/PNG) com fundo compatível e texto alternativo. URL privada curta, cache do relógio e checksum. Resultados não se perdem com falha de renderização.

### 6. Watch Delivery BC

Aggregate: `DevicePairing` / `WatchDevice`; `DeviceToken`, `SyncCursor`. Use Cases: `PairWatch`, `ListSessions`, `GetSession`, `GetQuestion`, `GetStep`, `SyncChanges`, `RevokeDevice`, `DeleteSession`. Segurança: short-lived access token + refresh rotativo, device id não sensível; TLS obrigatório; rate limiting; tráfego mínimo para bateria. O app não obtém token WhatsApp/OpenRouter.

## Hexagonal Architecture

```
apps/api/app/
  domain/{ingestion,sessions,interpretation,math_verification,presentation,delivery}/
    models.py  value_objects.py  events.py  policies.py
  application/{commands,queries,ports,handlers}/
  adapters/{http,db,queue,waha,openrouter,math,renderer,storage}/
  infrastructure/{config,logging,observability}/
```

- Dominio não importa FastAPI, SQLAlchemy, requests nem SDK de IA.
- Use cases trabalham com Ports (`MediaStore`, `SessionRepository`, `VisionProvider`, `MathVerifier`, `Clock`, `UnitOfWork`, `EventBus`).
- Adaptadores isolam regras/formatos WAHA, OpenRouter, PostgreSQL, SymPy.
- Eventos de domínio são imutáveis, com `event_id` e correlação. Persistir no outbox transacional antes de publish; consumidor idempotente.

## Eventos e idempotência

`MediaReceived`, `MediaRejected`, `QuestionAttached`, `BatchSealed`, `InterpretationRequested`, `InterpretationSucceeded`, `InterpretationNeedsReview`, `VerificationCompleted`, `PresentationReady`, `DeviceSynced`.

Idempotência por `(provider, provider_message_id, media_sha256)` com UNIQUE; `event_id` único na inbox/outbox; retry automático para falhas transitórias, DLQ para permanent failures.

## Entidades/relacionamentos

- `study_sessions` 1:N `questions` (máximo 4)
- `questions` 1:N `solution_steps`
- `questions` 0..1 `media_assets` original
- `solution_steps` 0..1 `render_assets`
- `watch_devices` N:M `study_sessions` via entitlement do usuário (MVP 1:1)
- `inbound_messages` 1:0..1 `questions`; deduplicação.
- `job_outbox` notificação/evento.

## Diagrama de sequência resumido

```
iPhone -> WhatsApp -> WAHA: foto JPG/documento
WAHA -> API: webhook message(media.url, id, from)
API -> DB: grava inbox se novo; 202 Accepted
Worker -> WAHA: GET media.url com API key interna
Worker -> Storage: valida MIME, dimensions, sha256, salva privado
Worker -> OpenRouter: image/jpeg base64 + prompt de extração estruturada
OpenRouter -> Worker: JSON de enunciado + graus de ambiguidade
Worker -> SymPy/Pint: verifica cálculos/unidades
Worker -> DB: passos e status verificável
Worker -> Renderer: produz SVG/PNG + alt
Watch4 -> API: GET /v1/sessions/{id} [token próprio]
API -> Watch4: metadados + passos renderizados; polling com backoff
```

## ADRs e trade-offs

**ADR-001:** Wear OS standalone + HTTPS em vez de iPhone companion/Data Layer.
**ADR-002:** FastAPI e domínio Python isolados; facilidade SymPy/Pint, custo de manter segundo stack.
**ADR-003:** WAHA como adaptador, não core do domínio; evita acoplamento WhatsApp e permite HTTP dev.
**ADR-004:** Polling 15s enquanto sessão ativa, backoff até 60s/pausa offline; SSE/PUSH fora do MVP.
**ADR-005:** Fórmula renderizada no backend, evitando motor LaTeX no Watch4.
**ADR-006:** Histórico breve e retenção configurável; nunca mídias expostas em CDN público.
