# ADR-003: WAHA como adapter isolado

**Accepted for MVP design.** Receber webhooks e baixar media `image/jpeg` / documento JPEG via adapter, seguindo media.url e secrets de WAHA. Não misturar autenticação WAHA com watch tokens; secrets no backend. Trade-off: dependência operacional de sessão WhatsApp e configuração do engine; reduzir risco com mocks em CI e sessão QA isolada.
