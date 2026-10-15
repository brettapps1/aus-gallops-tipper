#!/usr/bin/env python3
"""Google Play Books spec cover: 1600x2560 PNG (2:3), for AU AI Compliance Playbook."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 1600, 2560
OUT = Path('digital_product_workforce/outputs/prod-fairdinkum-compliance/build/cover-gpb.png')

PRIMARY = (14, 77, 46)       # eucalypt green
PRIMARY_D = (8, 45, 27)
ACCENT = (200, 138, 0)        # wattle gold
CREAM = (247, 244, 238)

FONT_DIRS = ['/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/truetype/liberation',
             '/usr/share/fonts/TTF', '/usr/share/fonts']


def font(name_hint, size):
    import glob
    for d in FONT_DIRS:
        hits = sorted(glob.glob(f'{d}/**/*{name_hint}*.ttf', recursive=True))
        if hits:
            try:
                return ImageFont.truetype(hits[0], size)
            except Exception:
                pass
    return ImageFont.load_default(size)


def centered(draw, y, text, f, fill, width=W):
    bb = draw.textbbox((0, 0), text, font=f)
    draw.text(((width - (bb[2] - bb[0])) / 2 - bb[0], y), text, font=f, fill=fill)
    return bb[3] - bb[1]


img = Image.new('RGB', (W, H), PRIMARY_D)
d = ImageDraw.Draw(img)

# vertical gradient background
for y in range(H):
    t = y / H
    r = int(PRIMARY_D[0] + (PRIMARY[0] - PRIMARY_D[0]) * (1 - t) * 0.9)
    g = int(PRIMARY_D[1] + (PRIMARY[1] - PRIMARY_D[1]) * (1 - t) * 0.9)
    b = int(PRIMARY_D[2] + (PRIMARY[2] - PRIMARY_D[2]) * (1 - t) * 0.9)
    d.line([(0, y), (W, y)], fill=(r, g, b))

# subtle shield outline (compliance motif)
d.rounded_rectangle([W // 2 - 330, 300, W // 2 + 330, 960], radius=40,
                    outline=ACCENT, width=6)

f_eyebrow = font('Mono', 52)
f_title = font('DejaVuSans-Bold', 190)
f_sub = font('DejaVuSans', 74)
f_meta = font('Mono', 46)
f_pub = font('DejaVuSans-Bold', 44)

# accent bars
d.rectangle([0, 0, W, 14], fill=ACCENT)
d.rectangle([0, H - 14, W, H], fill=ACCENT)

centered(d, 400, 'AUSTRALIAN', f_eyebrow, ACCENT)
centered(d, 490, 'SMALL BUSINESS', f_eyebrow, ACCENT)

centered(d, 1080, 'AI', f_title, CREAM)
centered(d, 1290, 'COMPLIANCE', f_title, CREAM)
centered(d, 1500, 'PLAYBOOK', f_title, CREAM)

d.line([(260, 1760), (W - 260, 1760)], fill=ACCENT, width=4)

centered(d, 1820, 'Privacy Act 1988', f_sub, CREAM)
centered(d, 1920, 'for Australian', f_sub, CREAM)
centered(d, 2020, 'Small Business', f_sub, CREAM)

centered(d, 2230, '18 Australian Privacy Principles', f_meta, ACCENT)
centered(d, 2300, 'Templates - Checklists - Agent Prompts', f_meta, (170, 190, 175))

centered(d, 2420, 'FAIR DINKUM PUBLISHING', f_pub, CREAM)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, 'PNG', optimize=True)
print('wrote', OUT, img.size)
