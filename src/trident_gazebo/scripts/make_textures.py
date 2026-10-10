#!/usr/bin/env python3
"""Regenerate the arena textures in trident_gazebo/textures.

  python3 scripts/make_textures.py

Writes one QR code per coin colour and a set of busy wall panels. The panels exist only to
give visual SLAM something to track: plain walls have no features at all.
The output is committed, so this only needs to run again when the design changes.
"""
import random
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw

TEXTURES = Path(__file__).resolve().parent.parent / 'textures'
COLOURS = ('red', 'green', 'blue')
WALL_PANELS = 6
WALL_SIZE = (2048, 256)   # px, stretched over a wall 0.3 m high


def make_qr(text: str) -> Image.Image:
    # High error correction and a wide quiet zone keep it readable at a slant
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=20, border=4)
    code.add_data(text)
    code.make(fit=True)
    return code.make_image(fill_color='black', back_color='white').convert('RGB')


def make_wall(seed: int) -> Image.Image:
    """Random blocks, discs and strokes in muted colours. Each seed gives a different wall,
    so two walls never look alike to the loop closure detector."""
    rng = random.Random(seed)
    width, height = WALL_SIZE
    image = Image.new('RGB', WALL_SIZE, (205, 200, 190))
    draw = ImageDraw.Draw(image)

    def colour():
        return tuple(rng.randint(30, 225) for _ in range(3))

    for _ in range(90):
        x, y = rng.randint(0, width), rng.randint(0, height)
        w, h = rng.randint(20, 140), rng.randint(20, 110)
        shape = rng.choice(('box', 'disc', 'stroke'))
        if shape == 'box':
            draw.rectangle((x, y, x + w, y + h), fill=colour())
        elif shape == 'disc':
            draw.ellipse((x, y, x + h, y + h), fill=colour())
        else:
            draw.line((x, y, x + w, y + rng.randint(-h, h)), fill=colour(), width=rng.randint(4, 12))
    return image


def main():
    TEXTURES.mkdir(exist_ok=True)
    for name in COLOURS:
        make_qr(name).save(TEXTURES / f'qr_{name}.png')
    for index in range(WALL_PANELS):
        make_wall(seed=index).save(TEXTURES / f'wall_{index}.png')
    print(f'Wrote {len(COLOURS)} QR codes and {WALL_PANELS} wall panels to {TEXTURES}')


if __name__ == '__main__':
    main()
