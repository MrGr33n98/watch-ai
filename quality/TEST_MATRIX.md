# QA Matrix e rastreabilidade US -> Gates

| Story | FRs | Tasks | Tests | Critério |
| --- | --- | --- | --- | --- |
| US01 fotos/ingest | FR001-003 | T003,T007-009,T028-032 | UT01-04, CT01-02, IT01-03,E2E01 | 4 mídias, 1x por msg, ordem correta |
| US02 solução | FR004-006,012 | T011,T013-019,T034 | UT05-09,CT03-04,E2E02 | sem invenções, unidades verificadas |
| US03 Wear UI | FR007-008,011 | T004,T020,T022-027 | E2E01,04,A11Y01 | 40/44mm legível e navegável |
| US04 Offline | FR008 | T025 | E2E03 | cache + retry/backoff |
| US05 Pairing | FR007,009 | T012,T021,T035 | CT05-06,E2E05,SEC01 | 401/403 e revogação |
| US06 Deletion | FR009 | T036 | IT04 | mídia e cache apagados |

## Variação de imagens

- `jpg_good`: letras de pelo menos 14pt na folha, focagem correta.
- `jpg_small`: fórmulas pequenas, índices e expoentes.
- `jpg_rotated`: 90/180 graus e EXIF rotation.
- `jpg_blurry`: desenfoque alto, precisa `needs_review`.
- `jpg_dark`: sombra/baixo contraste, precisa capturar novamente se ilegível.
- `jpg_corrupt`: bytes não JPEG -> rejeitado sem crash.
- `jpg_too_big`: > limite -> 413.
- `jpg_wrong_mime`: declaração image/jpeg com zip -> rejeitado.

## Variação de entrada WAHA

Mensagem texto `INICIAR`/`FINALIZAR`, mídia de imagem comum, documento JPEG, evento repetido, mensagem enviada pelo próprio número, remetente não autorizado, media.url ausente, MIME vazio, download lento, erro 401/403/404 do WAHA, URL host malicioso, conexão encerrada, resposta atrasada.

## Variação de OpenRouter

429 throttling, 502/503, timeout, JSON malformado, JSON válido sem unidades, confusão `0` vs `O`, 79 vs 1, resposta com tentativa de instruir API, respostas contraditórias, custo elevado, contexto de imagem recusado, modelo sem visão.

## Variação de Watch4

Sem pareamento, expirou token, token revogado, 1/2/3/4 questões, estado ready/partial/needs_review, sem internet, reconexão, letra grande, fundo escuro, brilho reduzido, tempo em background, 40mm, 44mm, screenshot.

## Evidência por PR

PR deve incluir tabela de comandos e status real, link de CI, JUnit XML, cobertura, APK SHA256 e screenshots (dados sintéticos), lista de known limitations e rollback. Nunca preencher com PASS sem resultado da ferramenta.
