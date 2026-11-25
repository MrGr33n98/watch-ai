# Research — decisões validadas versus hipóteses

| Pergunta | Evidência / fonte | Resultado |
|---|---|---|
| Estado repositório? | GitHub `MrGr33n98/watch-ai` main, commit 7b8cc95 | Apenas README; iniciar do zero |
| Plataforma relógio? | Android developers Wear Compose Material3 | Kotlin + Compose Wear M3 |
| Conexão Watch4 com iPhone? | Samsung suporte compatibilidade Watch4 | iOS não compatível para pairing; configurar com Android |
| Rede do relógio? | Wear OS network communication | App pode usar HTTPS direto por Wi-Fi |
| Input OpenRouter? | docs OpenRouter image understanding | JPEG como base64 data URL ou URL acessível |
| WAHA media? | WAHA docs receive messages | `payload.media.url`, usar chave no backend |
| Core math? | repos SymPy e Pint | Verificação simbólica/dimensional |
| Spec Kit CLI? | github/spec-kit docs/installation | `specify init` e `--integration codex`; verificar versão |
| Y3000 captura? | anúncio enviado pelo usuário | JPG anunciado, ainda sem teste real |
| Leitor Lightning? | captura de tela de ofertas do usuário | há leitores; compatibilidade modelo específico ainda a comprovar |

## URLs de referência

- https://github.github.com/spec-kit/
- https://github.com/github/spec-kit/blob/main/docs/installation.md
- https://github.com/github/spec-kit/blob/main/docs/integrations/cli.md
- https://developer.android.com/training/wearables/compose
- https://developer.android.com/training/wearables/data/network-communication
- https://developer.android.com/training/wearables/get-started/debug-wifi
- https://www.samsung.com/br/support/mobile-devices/devices-and-operating-systems-that-work-with-samsung-galaxy-watch/
- https://waha.devlike.pro/docs/how-to/receive-messages/
- https://openrouter.ai/blog/tutorials/send-image-to-llm/
- https://github.com/android/wear-os-samples
- https://github.com/google/horologist
- https://github.com/sympy/sympy
- https://github.com/hgrecco/pint

## Conclusões

A única forma de validar nitidez Y3000 é fotografar folhas reais; 1080p anunciado não atesta qualidade óptica. Integração com o relógio por API é tecnicamente suportada, mas deve ser demonstrada após setup Android. WAHA/OpenRouter são componentes externos substituíveis. A acurácia e a proteção de segredos são os maiores riscos de produto.

## Verificação de documentação oficial (2026-11-23)

Esta consulta valida decisões de arquitetura e não comprova integração física ou disponibilidade de credenciais.

| Fonte oficial | Evidência consultada | Decisão / limite |
|---|---|---|
| [Android: Compose for Wear OS](https://developer.android.com/training/wearables/compose) | A documentação recomenda Compose para interfaces Wear OS, orienta usar as dependências `androidx.wear.compose` e consultar os mapas de compatibilidade Compose/Kotlin. | Usar Wear Material 3, evitar misturar os componentes Material mobile e fixar versões após conferir a matriz atual do toolchain. |
| [Android: rede em dispositivos standalone](https://developer.android.com/training/wearables/data/network-communication) | Um relógio Wear OS pode comunicar diretamente pela rede sem telefone; a documentação orienta não usar Data Layer para acessar a rede e menciona WorkManager para tarefas assíncronas. | A API do relógio usa HTTPS/Wi-Fi diretamente; o iPhone não é ponte para a rede nem para a Data Layer. |
| [Samsung: compatibilidade de telefone e Galaxy Watch](https://www.samsung.com/us/support/answer/ANS10004668/) | A Samsung lista Galaxy Watch4 como incompatível com iOS e indica Android compatível para setup. | Configuração inicial requer telefone Android; prova do setup, ADB Wi-Fi e tráfego real permanece pendente. |
| [OpenRouter: envio de imagem a um LLM](https://openrouter.ai/blog/tutorials/send-image-to-llm/) | Chat Completions aceita texto seguido por parte `image_url` com URL HTTP(S) ou data URL base64. O catálogo identifica suporte por `image` em `input_modalities`. | Usar bytes privados em data URL para imagens locais, escolher modelo por configuração e verificar capacidade de visão antes de cada ativação. Modelos, preços e limites mudam; nenhum modelo/budget real foi aprovado. |
| [WAHA: recebimento de mensagens](https://waha.devlike.pro/docs/how-to/receive-messages/) | Webhook `message` contém dados de mídia em `payload.media`; `media.url` pode ser nula quando download está desativado. O download autenticado recomenda `X-Api-Key`; o evento depende de configuração/engine. | Normalizar payload por ACL, baixar só do host WAHA configurado e testar eventos reais somente com sessão isolada. Não presumir assinatura HMAC nativa. |
| [GitHub Spec Kit: quickstart SDD](https://github.github.com/spec-kit/quickstart) | A sequência completa usa skills separadas no agente; `.specify/feature.json` aponta o diretório de feature ativo. CLI e setup são operações de terminal. | `specify` 1.0.11 já está instalado e inicializado para Codex skills neste checkout. Não executar `init --force`; registrar a feature ativa explicitamente e seguir Constitution → Specify → Clarify → Plan → Tasks → Analyze → Implement. |

### Estado local durante a pesquisa

- `main` estava em `7b8cc95fb43a95ea64d0fadcb82c1f9f67e6e364`, com apenas `README.md` rastreado.
- O workspace tinha `.agents/` e `.specify/` não rastreados antes da implementação; o CLI/configuração local apontam Codex skills e Spec Kit 1.0.11.
- O validador documental do pacote passou: 18 arquivos obrigatórios, JSONs, YAML OpenAPI 3.1 e IDs T001–T041.
- Os valores aritméticos golden passaram; a checagem simbólica foi `SKIP` porque SymPy não está instalado no ambiente inicial.
- As quatro JPGs sintéticas são 1800×1200 e não substituem imagens da Y3000, importação Lightning/iPhone ou teste no Galaxy Watch4.
