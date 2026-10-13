"""Render the integration icon: Sarawak flag colours, tariff bars, bolt and a hornbill.

Usage (needs Pillow):
    python scripts/make_icon.py [preview.png]

Writes icon.png (256px) and icon@2x.png (512px) into the integration's brand/
folder, and optionally a light/dark preview sheet. Shapes are drawn on a
1024px design grid, supersampled 4x, then downscaled for anti-aliasing.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

out_dir = Path(__file__).parents[1] / "custom_components" / "sarawak_energy_tariffs" / "brand"
preview = Path(sys.argv[1]) if len(sys.argv) > 1 else None
S = 4
W = 1024 * S
YELLOW, RED, BLACK = "#FCD116", "#CE1126", "#111111"

def p(points):
    return [(x * S, y * S) for x, y in points]

img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([0, 0, W - 1, W - 1], radius=210 * S, fill=YELLOW)

# Tariff bands, rising left to right.
for x, top, colour in ((140, 650, BLACK), (370, 510, RED), (600, 370, BLACK)):
    d.rounded_rectangle([x * S, top * S, (x + 190) * S, 890 * S], radius=36 * S, fill=colour)

# Lightning bolt above the cheaper bands.
d.polygon(p([(270, 110), (150, 360), (250, 360), (195, 560), (395, 290), (290, 290), (370, 110)]), fill=BLACK)

# Rhinoceros hornbill sitting on the top band, facing left.
d.polygon(p([(790, 300), (905, 470), (862, 492), (755, 350)]), fill=BLACK)      # tail
d.ellipse(p([(640, 250), (830, 385)]), fill=BLACK)                               # body
d.ellipse(p([(555, 190), (672, 305)]), fill=BLACK)                               # head
d.polygon(p([(585, 285), (650, 225), (720, 280), (660, 340)]), fill=BLACK)      # neck
d.polygon(p([(590, 212), (520, 220), (462, 248), (418, 310), (468, 290), (525, 276), (592, 276)]), fill=RED)  # bill
d.polygon(p([(606, 206), (588, 168), (530, 150), (468, 152), (440, 176), (478, 200), (505, 226), (590, 214)]), fill=RED)  # casque
d.line(p([(588, 216), (512, 228), (470, 250)]), fill=BLACK, width=7 * S)         # bill/casque seam
d.ellipse(p([(612, 222), (634, 244)]), fill=YELLOW)                              # eye

for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
    img.resize((size, size), Image.LANCZOS).save(out_dir / name, optimize=True)

if preview is None:
    sys.exit()

sheet = Image.new("RGB", (640, 300), "#FFFFFF")
sheet.paste("#111827", (320, 0, 640, 300))
big = img.resize((256, 256), Image.LANCZOS)
small = img.resize((40, 40), Image.LANCZOS)
for x in (10, 330):
    sheet.paste(big, (x, 22), big)
    sheet.paste(small, (x + 266, 130), small)
sheet.save(preview)
