from PIL import Image, ImageDraw
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), 'icons')
os.makedirs(OUT_DIR, exist_ok=True)

BG = (26, 26, 46)        # mörkblå, matchar header
ROOF = (224, 123, 57)    # orange accent
WALL = (255, 255, 255)   # vit
DOOR = (224, 123, 57)    # orange

def draw_icon(size):
    img = Image.new('RGB', (size, size), BG)
    d = ImageDraw.Draw(img)
    s = size
    # Hus centrerat med marginal (safe zone för maskable ikoner)
    cx = s / 2
    roof_top = s * 0.26
    roof_bottom = s * 0.46
    wall_bottom = s * 0.74
    half_w = s * 0.24

    # Tak (triangel)
    d.polygon([
        (cx, roof_top),
        (cx - half_w - s * 0.04, roof_bottom),
        (cx + half_w + s * 0.04, roof_bottom),
    ], fill=ROOF)

    # Vägg (rektangel)
    d.rectangle([
        (cx - half_w, roof_bottom),
        (cx + half_w, wall_bottom),
    ], fill=WALL)

    # Dörr
    door_w = s * 0.10
    door_h = s * 0.16
    d.rectangle([
        (cx - door_w / 2, wall_bottom - door_h),
        (cx + door_w / 2, wall_bottom),
    ], fill=DOOR)

    return img

for size in (192, 512):
    icon = draw_icon(size)
    path = os.path.join(OUT_DIR, f'icon-{size}.png')
    icon.save(path)
    print(f'Skapade {path}')

# Apple touch icon (180x180, ingen transparens behövs)
apple = draw_icon(180)
apple.save(os.path.join(OUT_DIR, 'apple-touch-icon.png'))
print('Skapade apple-touch-icon.png')
