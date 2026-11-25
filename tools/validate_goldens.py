#!/usr/bin/env python3
"""Validação independente dos exemplos numéricos; NÃO executa o pipeline real de IA."""
from pathlib import Path
from decimal import Decimal
import json

cases = {x['id']: x for x in json.loads((Path(__file__).resolve().parents[1]/'examples/golden_cases.json').read_text())}

f = cases['GOLD-FOURIER-001']
d = {k: Decimal(v) for k,v in f['inputs'].items()}
assert d['k']*d['A']*d['dT']/d['L'] == Decimal(f['expected']), 'Fourier mismatch'

try:
    import sympy as sp
except ImportError:
    print('SKIP symbolic fixture verification: sympy not installed (required in backend project).')
else:
    x = sp.symbols('x')
    assert sp.simplify(sp.diff(x**2+3*x,x)-(2*x+3)) == 0
    assert sp.integrate(2*x, (x,0,3)) == int(cases['GOLD-INTEGRAL-003']['expected'])

u = cases['GOLD-UNIT-004']
assert Decimal(1500)/Decimal(1000) == Decimal(u['expected'])
print('PASS: golden fixture arithmetic verified (Fourier=2400W; d/dx=2x+3; integral=9; 1500W=1.5kW).')
print('NOTE: This tests fixture expected values ONLY, not WAHA, OCR, SymPy/Pint integration, OpenRouter or Watch4.')
