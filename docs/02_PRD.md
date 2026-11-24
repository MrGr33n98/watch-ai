# PRD — Watch AI Math Study Companion v1.0

**Produto:** Watch AI | **Público:** estudante em estudo individual autorizado | **MVP:** até 4 questões por lote | **Idioma:** pt-BR | **Hardware:** Y3000 JPG, iPhone 14, Galaxy Watch4.

## Problema / Job-to-be-done

Ao estudar a partir de uma folha impressa, quero fotografar exercícios, obter soluções explicadas e consultar cada etapa no relógio sem áudio, de modo a revisar fórmulas e cálculos independentemente do smartphone no momento da consulta.

## Metas SMART de piloto (a validar, não são medições)

- 4 imagens JPG importadas e recebidas em um lote associado a uma sessão.
- 100% dos eventos duplicados processados uma única vez.
- >= 95% das transições de UI livres de corte, scroll horizontal indesejado ou controles fora da tela nas duas dimensões de Watch4.
- 100% dos exercícios matemáticos do corpus 'golden' devem passar verificação simbólica/dimensional; enunciado ambíguo deve resultar em `needs_review`.
- P95 de retorno de status API < 1s em ambiente controlado; processamento IA depende do provedor e deve ter estado `processing`.
- 0 segredos no APK e 0 rotas de mídia abertas.

## Personas / Stories

US01 — Como estudante, importo quatro JPGs originais da câmera ao iPhone para manter legibilidade.
US02 — Como estudante, envio cada imagem por WhatsApp ao número autorizado do sistema, preferencialmente como documento.
US03 — Como estudante, vejo lote pendente/processando/precisando de revisão/concluído no relógio.
US04 — Como estudante, alterno Q1..Q4 sem esperar por novos cálculos em cada toque.
US05 — Como estudante, consulto enunciado, dados, fórmula, substituição, cálculo e resultado em etapas numeradas.
US06 — Como estudante, vejo notação matemática renderizada, com fallback textual acessível se imagem da fórmula falhar.
US07 — Como estudante, não recebo resultados inventados quando o JPG está borrado ou o OCR é ambíguo.
US08 — Como estudante, posso reabrir respostas previamente sincronizadas offline.
US09 — Como operador, posso auditar status, custo e erros sem armazenar dados pessoais excessivos.
US10 — Como operador, consigo configurar e revogar o pareamento do relógio sem digitar segredos de API nele.
US11 — Como estudante, recupero uma sessão após falha de rede, sem perder a ordem original das questões.
US12 — Como usuário, removo imagens e sessões após conclusão e retenção definida.

## Jornada principal

Captura autorizada -> microSD 32GB -> leitor Lightning -> importação iOS -> envio WhatsApp -> webhook validado -> download privado do JPG -> verificação de imagem -> OCR/extração estruturada -> validação -> resolução -> verificação -> renderização -> API persistida -> watch consulta status -> lista de 4 -> seleção -> passos -> resposta -> próxima.

## Jornada alternativa de desenvolvimento

Fixtures JPG sintéticas -> POST /dev/ingest (SOMENTE LOCAL, DESABILITADO NA PRODUÇÃO) -> mesmo pipeline -> watch emulator -> E2E verde. Este caminho reduz dependências do WAHA e da Y3000 nos primeiros sprints.

## Funcionalidades P0

- F01 Ingestão e normalização de `image/jpeg` via WAHA (media como `image` ou `document`).
- F02 Agrupamento explícito em até quatro questões, com ordens indexadas, idempotência e confirmação de conclusão do lote.
- F03 Estado durável das sessões e questões, consultável por HTTP.
- F04 Interpretação do enunciado com modelo multimodal de visão e schema validado.
- F05 Detecção de baixo grau de confiança/ambiguidade, sem adivinhação.
- F06 Solução em passos com verificação SymPy/Pint quando aplicável.
- F07 Exibição offline-first das últimas sessões no Watch4, incluindo fórmula e texto alternativo.
- F08 Pareamento da instância do Watch4 por código temporário, token revogável e TLS.
- F09 Observabilidade/custos/erros sem logs de imagens ou mensagens integrais.
- F10 Testes unitários, contratos, integração, E2E, segurança e acessibilidade.

## P1 após MVP

- Ajuste de enquadramento no iPhone (sem desenvolver app iOS), tratamento de imagem antes de OCR.
- Seleção de modelo OpenRouter configurável/feature-flag; fallback secundário após timeout.
- Busca no histórico, exportação de solução como PDF opcional, notificações leves.
- Processamento mais de quatro imagens apenas em nova sessão.

## Regras / NFRs

- Tamanho máximo de arquivo configurável (proposta 8 MB); 1-4 JPGs; rejeitar GIF/PDF/HTML/arquivos executáveis.
- Aceitar apenas remetentes autorizados; não converter telefones em tokens de acesso ou expor IDs no relógio.
- Retenção default proposta: arquivos brutos 24h; soluções 30 dias; configurar antes de deploy.
- Todos os tempos UTC no banco e apresentação local no relógio.
- Retries: max 3 com jitter para erros transitórios; nunca duplicar trabalho por redelivery.
- Limitar consumo de IA por sessão e budget mensal; rate limits por remetente e dispositivo.
- Erros explicativos (`needs_review`, `no_network`, `session_expired`) e nenhuma tela vazia.
- Material3 para Wear OS, área segura circular; fonte 12-18sp, contraste >=4.5:1 para texto normal.
- Reduzir animações quando `reduce motion` estiver ativo; estados de carregamento sem polling agressivo.

## Estados de sessão

`created` -> `collecting` -> `queued` -> `processing` -> (`ready` | `partial` | `needs_review` | `failed`); `cancelled` e `expired` finais. Perguntas podem ter estados independentes.

## Métricas e eventos

`image_received`, `image_rejected`, `batch_created`, `batch_completed`, `solution_started`, `solution_verified`, `solution_needs_review`, `model_error`, `watch_paired`, `watch_sync`, `step_viewed`, `session_deleted`. Não transmitir enunciados brutos a analytics.

## Critérios de aceite GO

- Quatro fotos de exemplo passam pelo pipeline mockado e retornam contrato consistente.
- O watch mostra Q1-Q4 e passos numerados em 40/44mm, com botão próximo/anterior.
- Uma foto borrada não recebe resposta factual inventada.
- Não existem credenciais OpenRouter/WAHA no app Wear OS.
- Testes executados em CI + dispositivo físico e evidências arquivadas.
