#!/usr/bin/env python3
"""Gera JPGs sintéticos, não simula sensor da Y3000 nem substitui ensaio real."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / 'examples' / 'synthetic_jpg'
OUT.mkdir(exist_ok=True, parents=True)
problems = [
    ('Q1 - Conducao de calor', ['k = 1.2 W/(m.K)', 'A = 10 m2', 'Delta T = 40 K', 'L = 0.20 m', 'Calcule a taxa Qdot (W).']),
    ('Q2 - Derivada', ['f(x) = x^2 + 3x', 'Calcule f\'(x).']),
    ('Q3 - Integral definida', ['Calcule a integral de 2x dx', 'no intervalo de x = 0 ate 3.']),
    ('Q4 - Potencia', ['Converta 1500 W em kW.']),
]
fontfile = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
try:
    heading = ImageFont.truetype(fontfile, 48)
    font = ImageFont.truetype(fontfile, 37)
except OSError:
    heading, font = ImageFont.load_default(), ImageFont.load_default()
for i, (title, lines) in enumerate(problems, 1):
    img = Image.new('RGB', (1800, 1200), 'white')
    draw = ImageDraw.Draw(img)
    draw.text((120,120), title, fill='black', font=heading)
    for n, line in enumerate(lines):
        draw.text((120,260+n*115), line, fill='black', font=font)
    img.save(OUT/f'Q{i}_synthetic.jpg', 'JPEG', quality=94, subsampling=0)
print(f'Generated {len(problems)} synthetic JPGs under {OUT}')
