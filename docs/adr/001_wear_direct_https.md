# ADR-001: Watch4 standalone via HTTPS

**Accepted for MVP design.** O iPhone 14 não emparelha oficialmente com Watch4; construir aplicativo Wear OS independente com HTTPS direto Wi-Fi e cache. Não usar iOS companion, Android Data Layer nem Bluetooth como ponte. Trade-off: requer configuração inicial com Android compatível e conexão de rede disponível; polling com backoff para bateria.
