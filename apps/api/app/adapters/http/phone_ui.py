"""Mobile-friendly companion web page for phone upload, watch pairing, and device control."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.adapters.http.admin import MIN_ADMIN_KEY_BYTES

router = APIRouter(tags=["phone-console"])

_PHONE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Watch AI · Celular</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #050a13;
      --card: #111d30;
      --border: #23364d;
      --accent: #0b84ff;
      --text: #f8fafc;
      --muted: #a8b8cc;
      --ok: #21c778;
      --err: #f46d71;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; font-family: system-ui, -apple-system, sans-serif;
      background: var(--bg); color: var(--text); padding: 16px;
      line-height: 1.45;
    }
    main { max-width: 560px; margin: 0 auto; display: grid; gap: 14px; }
    section {
      background: var(--card); border: 1px solid var(--border);
      border-radius: 14px; padding: 14px; display: grid; gap: 10px;
    }
    h1, h2, h3 { margin: 0; font-size: 1.05rem; }
    label { font-size: .85rem; color: var(--muted); display: grid; gap: 4px; }
    input, button {
      width: 100%; padding: 11px 12px; border-radius: 10px;
      font-size: 1rem; border: 1px solid var(--border);
    }
    input { background: #091220; color: var(--text); }
    button {
      background: var(--accent); color: #fff; font-weight: 600;
      border: 0; cursor: pointer;
    }
    button.secondary { background: #1a2c47; border: 1px solid var(--border); }
    button.danger { background: #7f1d1d; }
    .code {
      font-size: 1.8rem; font-weight: 700; letter-spacing: .15em;
      color: var(--ok);
    }
    .muted { color: var(--muted); font-size: .88rem; }
    .err { color: var(--err); font-size: .9rem; }
    .item { border-top: 1px solid var(--border); padding-top: 8px; display: grid; gap: 6px; }
  </style>
</head>
<body>
<main>
  <section>
    <h1>Watch AI · Painel do Celular</h1>
    <p class="muted">
      Envie até 4 fotos JPG, gere códigos do Galaxy Watch4 e gerencie dispositivos.
    </p>
    <label>Chave de Acesso (ADMIN_API_KEY)
      <input id="adminKey" type="password" autocomplete="off" placeholder="Cole sua chave" />
    </label>
    <label>ID do Usuário (UUID)
      <input id="userId" type="text" placeholder="Crie ou cole o UUID do usuário" />
    </label>
    <button id="createUserBtn" class="secondary" type="button">Criar novo usuário</button>
    <div id="authMsg" class="muted"></div>
  </section>

  <section>
    <h2>1. Parear Galaxy Watch4</h2>
    <p class="muted">URL HTTPS para digitar no relógio: <strong id="originText"></strong></p>
    <button id="genPairBtn" type="button">Gerar código de pareamento</button>
    <div id="pairOut"></div>
  </section>

  <section>
    <h2>2. Enviar 1 a 4 fotos JPG</h2>
    <input id="jpgFiles" type="file" accept="image/jpeg,.jpg,.jpeg" multiple />
    <button id="uploadBtn" type="button">Enviar para resolução</button>
    <div id="uploadOut" class="muted"></div>
  </section>

  <section>
    <h2>3. Sessões e Soluções</h2>
    <button id="refreshSessionsBtn" class="secondary" type="button">Atualizar sessões</button>
    <div id="sessionsOut"></div>
  </section>

  <section>
    <h2>4. Relógios Pareados (Revogação Remota)</h2>
    <button id="refreshDevicesBtn" class="secondary" type="button">Listar relógios</button>
    <div id="devicesOut"></div>
  </section>
</main>
<script>
(() => {
  const $ = (id) => document.getElementById(id);
  $("originText").textContent = window.location.origin;
  $("adminKey").value = sessionStorage.getItem("watch_ai_admin_key") || "";
  $("userId").value = localStorage.getItem("watch_ai_user_id") || "";

  const headers = () => {
    const key = $("adminKey").value.trim();
    sessionStorage.setItem("watch_ai_admin_key", key);
    return { "X-Admin-Key": key };
  };
  const uid = () => {
    const val = $("userId").value.trim();
    if (val) localStorage.setItem("watch_ai_user_id", val);
    return val;
  };
  const api = async (path, opts = {}) => {
    const res = await fetch(path, {
      ...opts,
      headers: { ...headers(), ...(opts.headers || {}) },
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.message || data.detail || `HTTP ${res.status}`);
    return data;
  };

  $("createUserBtn").onclick = async () => {
    try {
      const data = await api("/v1/admin/users", { method: "POST" });
      $("userId").value = data.user_id;
      localStorage.setItem("watch_ai_user_id", data.user_id);
      $("authMsg").textContent = "Usuário criado e salvo neste navegador.";
    } catch (e) { $("authMsg").textContent = e.message; }
  };

  $("genPairBtn").onclick = async () => {
    const out = $("pairOut");
    try {
      const data = await api("/v1/admin/pairings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: uid(), ttl_minutes: 10 }),
      });
      out.innerHTML = `<div class="code"></div><div class="muted"></div>`;
      out.querySelector(".code").textContent = data.pairing_code;
      out.querySelector(".muted").textContent = `Expira em: ${data.expires_at}`;
    } catch (e) {
      out.innerHTML = `<div class="err"></div>`;
      out.querySelector(".err").textContent = e.message;
    }
  };

  $("uploadBtn").onclick = async () => {
    const out = $("uploadOut");
    const files = $("jpgFiles").files;
    if (!files.length || files.length > 4) {
      out.textContent = "Selecione entre 1 e 4 arquivos JPG.";
      return;
    }
    const form = new FormData();
    for (const f of files) form.append("files", f);
    try {
      const path = `/v1/admin/users/${uid()}/batches/upload`;
      const data = await api(path, { method: "POST", body: form });
      out.textContent = `Sessão ${data.session_id} na fila (${data.received_count} fotos).`;
      await loadSessions();
    } catch (e) { out.textContent = e.message; }
  };

  const loadSessions = async () => {
    const out = $("sessionsOut");
    try {
      const data = await api(`/v1/admin/users/${uid()}/sessions?limit=10`);
      out.innerHTML = "";
      if (!data.items.length) { out.textContent = "Nenhuma sessão ainda."; return; }
      for (const s of data.items) {
        const div = document.createElement("div");
        div.className = "item";
        const title = document.createElement("div");
        title.textContent = `${s.received_count}/${s.expected_count} · ${s.status}`;
        const detail = document.createElement("div");
        detail.className = "muted";
        const openBtn = document.createElement("button");
        openBtn.className = "secondary";
        openBtn.textContent = "Ver questões";
        openBtn.onclick = async () => {
          const base = `/v1/admin/users/${uid()}/sessions/${s.id}`;
          const full = await api(base);
          detail.textContent = "";
          for (const q of full.questions) {
            const qd = await api(`${base}/questions/${q.ordinal}`);
            const p = document.createElement("p");
            const st = qd.verified ? "Verificado" : qd.status;
            const ans = qd.final_answer || "sem resposta verificada";
            p.textContent = `Q${q.ordinal} [${st}]: ${qd.statement} -> ${ans}`;
            detail.appendChild(p);
          }
        };
        const delBtn = document.createElement("button");
        delBtn.className = "danger";
        delBtn.textContent = "Excluir sessão";
        delBtn.onclick = async () => {
          await api(`/v1/admin/users/${uid()}/sessions/${s.id}`, { method: "DELETE" });
          await loadSessions();
        };
        div.append(title, openBtn, delBtn, detail);
        out.appendChild(div);
      }
    } catch (e) { out.textContent = e.message; }
  };

  const loadDevices = async () => {
    const out = $("devicesOut");
    try {
      const data = await api(`/v1/admin/users/${uid()}/devices`);
      out.innerHTML = "";
      if (!data.items.length) { out.textContent = "Nenhum relógio pareado."; return; }
      for (const d of data.items) {
        const div = document.createElement("div");
        div.className = "item";
        const info = document.createElement("div");
        info.textContent = `${d.device_name} · ${d.active ? "Ativo" : "Revogado/Expirado"}`;
        div.appendChild(info);
        if (d.active) {
          const btn = document.createElement("button");
          btn.className = "danger";
          btn.textContent = "Revogar relógio";
          btn.onclick = async () => {
            const path = `/v1/admin/users/${uid()}/devices/${d.device_id}`;
            await api(path, { method: "DELETE" });
            await loadDevices();
          };
          div.appendChild(btn);
        }
        out.appendChild(div);
      }
    } catch (e) { out.textContent = e.message; }
  };

  $("refreshSessionsBtn").onclick = loadSessions;
  $("refreshDevicesBtn").onclick = loadDevices;
})();
</script>
</body>
</html>
"""


@router.get("/phone", response_class=HTMLResponse)
def phone_companion_console(request: Request) -> HTMLResponse:
    configured_key: str = getattr(request.app.state, "admin_api_key", "") or ""
    if len(configured_key.encode("utf-8")) < MIN_ADMIN_KEY_BYTES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return HTMLResponse(
        content=_PHONE_HTML,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": (
                "default-src 'none'; script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; connect-src 'self'; form-action 'self'"
            ),
        },
    )
