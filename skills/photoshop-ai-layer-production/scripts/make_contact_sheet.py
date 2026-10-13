from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(220, 220, 220))
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("layers_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--thumb", type=int, default=420)
    parser.add_argument("--columns", type=int, default=3)
    args = parser.parse_args()
    paths = sorted(args.layers_dir.rglob("*.png"))
    if not paths:
        raise RuntimeError("No PNG outputs found")
    tiles = []
    for path in paths:
        with Image.open(path) as opened:
            rgba = opened.convert("RGBA")
            rgba.thumbnail((args.thumb, args.thumb), Image.Resampling.LANCZOS)
            bg = checker((args.thumb, args.thumb))
            x = (args.thumb - rgba.width) // 2
            y = (args.thumb - rgba.height) // 2
            bg.paste(rgba, (x, y), rgba)
            tile = Image.new("RGB", (args.thumb, args.thumb + 44), "white")
            tile.paste(bg, (0, 0))
            ImageDraw.Draw(tile).text((8, args.thumb + 10), path.name, fill="black", font=ImageFont.load_default())
            tiles.append(tile)
    rows = math.ceil(len(tiles) / args.columns)
    sheet = Image.new("RGB", (args.columns * args.thumb, rows * (args.thumb + 44)), "white")
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % args.columns) * args.thumb, (index // args.columns) * (args.thumb + 44)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, quality=92, subsampling=0)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
