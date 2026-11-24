# ADR-002: Vision AI assíncrono com verificação e sinalização de incerteza

**Accepted for MVP design.** API persiste e enfileira, worker OpenRouter extrai structured JSON, verificador SymPy/Pint checa matemática/unidades. Erro/ambiguidade -> `needs_review`, não resposta inventada. Trade-off: não cobre exercícios arbitrários e pode aumentar latência; transparência é requisito.
