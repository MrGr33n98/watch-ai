# Threat model, privacidade, segurança e resiliência

## Atores e superfície de ataque

Atores: usuário legítimo, remetente WhatsApp não autorizado, comprometimento de webhook, provedor externo de IA, usuário com Watch4 perdido, operador backend e atacante que envia imagem adversarial.

- Spoof de webhook: segredo compartilhado no reverse proxy, allowlist de rede interna, HMAC por gateway próprio quando possível; não assumir que WAHA assina eventos nativamente. Nunca expor porta WAHA publicamente.
- SSRF por `media.url`: aceitar apenas hostname interno WAHA configurado e rota esperada; rejeitar redirects, IPs privados externos e esquemas não HTTP(S); usar API Key no header.
- Prompt injection via enunciado fotografado: tratar texto OCR como dado não confiável; sistema deve ignorar comandos encontrados na folha.
- DoS de JPEG: limite de bytes, limite de dimensão/pixels, timeout de decode; PIL safe guard; validação magic bytes e reencode para remover EXIF desnecessário.
- Upload malicioso: aceitar JPEG apenas, não confiar na extensão; bloquear SVG/HTML/ZIP mascarado.
- Parser simbólico: não executar `sympify` indiscriminadamente em entrada adversarial; usar whitelist de tokens/AST, timeouts em subprocesso isolado, limites de operações.
- Credenciais: segredos de provedores ficam no servidor; o watch recebe token próprio de baixo escopo, armazenado no Android Keystore e com expiração. O endpoint implementado revoga apenas o relógio autenticado que o chama; não existe revogação owner/admin remota para relógio perdido, portanto esse fluxo é bloqueador de produção.
- Sessões multiusuário: conferir ownership em TODA leitura de ID; usar UUID aleatório mais política de acesso, nunca confiar só no UUID.
- Replay: idempotência `provider_message_id` + nonce/token do webhook; TTL e dedupe persistente.
- Dados pessoais: não guardar telefone na forma legível se possível; HMAC com secret, acesso restrito; logs redigidos.
- IA externa: divulgar que JPGs são enviados a serviço de terceiro; opt-in e política de retenção conforme provedor/modelo; usar apenas quando permitido.
- Criptografia: HTTPS/TLS; disco/storage privado; backups cifrados, política de expurgo.

## Retenção proposta (precisa ser aprovada)

Original JPG: apagar em 24h após processo/conclusão. Renderizações e soluções: 30 dias ou conforme escolha do usuário. Mensagens webhook: preservar apenas metadados mínimos e hashes. Direito de apagar: `DELETE /v1/sessions/{id}` com expurgo do storage.

## Verificações de segurança automatizadas

- Secret scanning GitHub + gitleaks; dependabot/Renovate + pip-audit, Bandit, detekt/Android lint.
- Testes para 401, 403, SSRF, acesso cruzado entre relógios, replay, JPG malicioso, custos IA e rate limit.
- Rotação de tokens + revogação ao remover o relógio.
- Verificar segurança do dispositivo e autorização para fotografar materiais; projeto destinado a estudo e atividades permitidas.
