# Discovery e Gap Analysis — Watch AI

**Data-base:** 23/11/2026. Fatos conferidos do repositório `MrGr33n98/watch-ai`: branch default `main`, commit `7b8cc95fb43a95ea64d0fadcb82c1f9f67e6e364`, árvore raiz apenas `README.md` com `# watch-ai`. Não há código de implementação, CI, testes ou contratos.

## Contexto consolidado a partir das decisões do projeto

- Hardware de entrada escolhido: minicâmera Y3000 tipo chaveiro, com modo fotografia anunciado e JPG como formato de saída pretendido.
- Armazenamento: cartão microSD 32 GB, comprado separadamente.
- Fluxo manual: retirar cartão -> leitor Lightning -> iPhone 14 -> WhatsApp como Documento para reduzir compressão.
- Saída: Samsung Galaxy Watch4 com aplicativo nativo; sem voz; quatro exercícios em sequência; cálculos explicados etapa a etapa; notação matemática legível.
- Gateway de modelos: OpenRouter; WAHA para recebimento de mensagens.
- Execução: desenvolvimento no Ubuntu via Antigravity e Codex; repository GitHub `MrGr33n98/watch-ai`.

## Fatos confirmados por documentação pública

1. Android recomenda Jetpack Compose for Wear OS Material3 e componentes de relógio específicos.
2. Wear OS pode se comunicar diretamente por HTTPS pela rede; não exige aplicativo iPhone parceiro.
3. Samsung Watch4 deve ser inicialmente configurado via Android compatível; não emparelha oficialmente com iPhone.
4. OpenRouter suporta imagens JPEG como URL assinada ou data URL base64 em endpoint multimodal.
5. WAHA webhook de mensagem informa anexo (`media.url`) quando download de mídia está habilitado.
6. Spec Kit recomenda fluxo Constitution -> Specify -> Clarify -> Plan -> Tasks -> Analyze -> Implement; nomes variam conforme agente/integração.

## Hipóteses NÃO confirmadas

- Y3000 realmente entrega JPG nítido em close-up e salva todas as fotos em uma pasta reconhecida pelo iOS.
- Leitor Lightning específico funciona com iPhone 14 e o filesystem do cartão da câmera sem aplicativo proprietário.
- Watch4 já está ativado/emparelhado com Android e permite ADB Wi-Fi.
- WAHA da infraestrutura Avalia Solar pode ser reutilizado sem risco operacional e respeitando isolamento de sessões.
- Um único modelo multimodal resolve corretamente exercícios de física/matemática sem supervisão.
- OpenRouter/WAHA dispõem de credenciais funcionais no ambiente de teste.

## Gaps bloqueantes / protótipos de prova

| ID | Gap | Critério para sair do risco | Responsável sugerido |
|---|---|---|---|
| G01 | Captura legível de fórmulas pela Y3000 | 4 JPG reais legíveis, sem perda em expoentes, índices e frações | Hardware |
| G02 | Importação iPhone 14 | Importar JPG original sem transcodificação; EXIF/orientação verificada | Hardware |
| G03 | Galaxy Watch4 preparado | Instalar APK de teste via adb, Wi-Fi HTTPS funcional | Wear OS |
| G04 | Pipeline de imagem | Ingest -> status -> resposta de teste com mock do OpenRouter | Backend |
| G05 | WAHA webhook seguro | Receber JPG/documento e ignorar eventos repetidos | Integração |
| G06 | Precisão matemática | 4 golden cases e matriz negativa para `needs_review` | Math |
| G07 | Renderização notação | SVG/PNG de fórmulas cabem em tela circular; fallback textual | UI |
| G08 | Orçamento/infra | Sem aumento de OOM no Avalia Solar; não usar infraestrutura produtiva como teste | DevOps |

## Decisões

- Abordagem incremental: mock local -> upload HTTP opcional de desenvolvimento -> WhatsApp real -> relógio real.
- Não construir aplicativo iOS no MVP: importação feita pelo app Fotos/Arquivos e WhatsApp.
- Não processar imagem no Watch4: só consumir dados e artefatos compactos.
- Não utilizar Data Layer WearOS<->Android, pois o iPhone não é o companion Android emparelhado.
- Evitar integração direta entre WAHA e watch: backend aplica autenticação e persistência.
- Não implantar nas mesmas instâncias congestionadas do Avalia Solar sem capacidade comprovada.

## Fora do escopo do MVP

Captura remota da Y3000, câmera sempre ligada, reconhecimento de vídeo ao vivo, streaming, notificações em tempo real garantidas, sincronização bidirecional com iPhone, resolução perfeita, cálculos numéricos avançados arbitrários, atualização automática do APK por OTA, lançamento na Play Store.

## Critério geral de GO/NO-GO

GO somente se: G01-G03 comprovados, backend/mock E2E verde, pelo menos quatro problemas verificados, nenhuma exposição de credenciais, APK debug instalável; produção só após segurança, confiabilidade e testes em dispositivo físico.
