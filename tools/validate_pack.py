#!/usr/bin/env python3
"""Verifica estrutura e contratos do pack, não testa o produto Watch AI."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
files = [
    'README.md', '.specify/memory/constitution.md', 'docs/01_DISCOVERY.md',
    'docs/02_PRD.md', 'docs/03_PDR.md', 'docs/04_ARCHITECTURE_DDD.md',
    'docs/06_TEST_STRATEGY.md', 'docs/07_SECURITY_PRIVACY.md',
    'specs/001-watch-ai-mvp/spec.md', 'specs/001-watch-ai-mvp/plan.md',
    'specs/001-watch-ai-mvp/tasks.md', 'specs/001-watch-ai-mvp/data-model.md',
    'specs/001-watch-ai-mvp/contracts/openapi.yaml',
    'prompts/01_ANTIGRAVITY_CODEX_MASTER.md',
    'examples/waha_webhook_normalized.json', 'examples/watch_session_response.json',
    'examples/question_detail_response.json', 'examples/golden_cases.json',
]
errors = []
for f in files:
    p = ROOT / f
    if not p.exists() or p.stat().st_size == 0:
        errors.append(f'Missing/empty: {f}')
for f in ROOT.glob('examples/*.json'):
    try:
        json.loads(f.read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'Invalid JSON {f}: {e}')
try:
    import yaml
    spec = yaml.safe_load((ROOT/'specs/001-watch-ai-mvp/contracts/openapi.yaml').read_text())
    assert spec.get('openapi') == '3.1.0'
    assert {'/v1/sessions','/v1/device-pairings','/internal/waha/events'} <= set(spec.get('paths', {}))
except Exception as e:
    errors.append(f'OpenAPI YAML invalid/incomplete: {e}')
assert all((ROOT/'specs/001-watch-ai-mvp/tasks.md').read_text().count(f'T{i:03}') >= 1 for i in range(1,42)), 'Task gap'
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'PASS: pack content structure, {len(files)} required files, example JSON, OpenAPI syntax and tasks T001..T041.')
print('NOTE: This is NOT evidence that backend, Wear OS, WAHA, OpenRouter, hardware or E2E are implemented or passing.')
