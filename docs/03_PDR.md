# PDR — Watch AI Wear OS Interface & Engineering Design

## Direção visual

Proposta premium minimalista, fundo #050A13, superfícies #111D30, borda #23364D, accent azul #0B84FF, texto primário #F8FAFC, secundário #A8B8CC, sucesso #21C778, atenção #F1B63C, erro #F46D71. Mais importante que a cor: legibilidade e contraste. Sem ícones genéricos desnecessários.

## Geometria real da tela circular

Trabalhar em dp/sp e `WindowInsets`/`ScreenScaffold`; o número de pixels varia por modelo/escala. Testar pelo menos 40 e 44 mm reais ou emuladores compatíveis. **Nunca deduzir dimensões CSS de um mock PNG como se fossem medidas de tela física.**

| Elemento | Target visual (dp) | Comportamento |
| --- | --- | --- |
| Margem/segurança | 10–18dp conforme arco | Nunca encostar no bezel |
| Badge Q1..Q4 | 26–30dp alto | Esquerda do heading |
| Heading | 14–16sp semibold | Máximo 2 linhas com rolagem apropriada |
| Corpo da questão | 12–14sp | Scroll vertical, alto contraste |
| Cartão fórmula | 48–74dp mínimo | Imagem raster/SVG com alternativa textual |
| Botão circular anterior/próximo | >=44dp área de toque | Bottom navigation, borda segura |
| Indicadores de etapas | 4–6dp | Não substituir texto “Passo N de M” |
| Botão primário | 44–48dp alto | Estado carregando/disabled/foco |
| Gaps | 4/8/12dp | Sem desperdício de área circular |

## Telas e navegação

S0 Estado não pareado -> pareamento por código temporário mostrado no backend/admin, nunca segredos em texto no watch.
S1 Sessões -> lista das últimas quatro sessões ou vazia com orientação.
S2 Questões -> 4 linhas Q1..Q4, estado de cada uma (processando/verificado/revisão).
S3 Enunciado -> texto extraído + verificação humana de legibilidade.
S4 Passos -> etapa N/M: dados, fórmula, transformação, substituição, resultado; movimentos laterais ou botões, rolagem vertical no conteúdo.
S5 Resultado -> valor final, unidade e `verified/needs_review`.
S6 Erros -> offline, arquivo ilegível, sessão expirada, resposta não verificada.
S7 Configurações -> pareamento, sincronizar, limpeza do cache.

## Microinterações

- Pressionado: escala 0.98 e destaque leve <=140ms; sem bloqueio por animação.
- Transição entre passos: 120–180ms, se movimento reduzido não ativo.
- Atualização do status: indicador discreto; `processing` sem spinner permanente consumindo bateria.
- Resultado validado: badge verde com descrição “Verificado”, nunca apenas cor.
- Ao avançar, o foco/a11y anuncia “Questão 2, passo 3 de 5”.
- Reabertura: restaurar última questão/etapa e cache local.

## Fórmulas e notação

Backend retorna `latex`, `plain_text` e opcional `render_url` privado. Renderizar em SVG ou PNG fora do relógio; watch apresenta artefato dimensionado com fallback `plain_text` caso renderização falhe. Não usar WebView, engine LaTeX completa ou execução de código no Watch4. Artefatos por etapa têm `alt_text` e máximo de tamanho configurado. Testar fórmulas com fração, raiz, integral, subíndice, sobrescrito, letras gregas.

## Sem voz

Não pedir permissão RECORD_AUDIO; não usar microfone nem TTS. Feedback somente visual/háptico leve opcional e desativado por padrão.

## Exemplos de conteúdos exibidos

Questão 1: “Uma parede com k=1,2 W/(m K), A=10 m², L=0,20 m e ΔT=40 K. Calcule Q̇.”
Passo 1: “Lei de Fourier: Q̇=kAΔT/L”.
Passo 2: “Substituindo: 1,2 × 10 × 40 / 0,20”.
Passo 3: “480 / 0,20 = 2.400”.
Resultado: “Q̇ = 2.400 W (2,4 kW)”.

As demais questões do corpus cobrem derivada, integral e conversão térmica; usar apenas valores matematicamente consistentes.

## Critérios de aceitação visual

Aprovação somente com screenshots reais em 40 e 44 mm, teste com escala de fonte elevada, sem clipping de expressão ou de controles, contraste acessível, toque com luvas/uso normal quando possível, gestos reversíveis e sem navegação oculta por cor.
