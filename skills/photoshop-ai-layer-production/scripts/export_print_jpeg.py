from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PIL import Image


def save_candidate(image: Image.Image, path: Path, quality: int) -> int:
    options: dict = {
        "format": "JPEG",
        "quality": quality,
        "subsampling": 2,
        "optimize": True,
    }
    if image.info.get("dpi"):
        options["dpi"] = image.info["dpi"]
    if image.info.get("icc_profile"):
        options["icc_profile"] = image.info["icc_profile"]
    if image.info.get("exif"):
        options["exif"] = image.info["exif"]
    image.save(path, **options)
    return path.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--target-mb", type=float, default=15.0)
    parser.add_argument("--minimum-quality", type=int, default=60)
    parser.add_argument("--maximum-quality", type=int, default=82)
    args = parser.parse_args()

    source = args.source.resolve()
    destination = args.destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    target = int(args.target_mb * 1_000_000)
    Image.MAX_IMAGE_PIXELS = None

    with Image.open(source) as image:
        image.load()
        original_size = image.size
        candidates: list[tuple[int, int, Path]] = []
        low = args.minimum_quality
        high = args.maximum_quality
        while low <= high:
            quality = (low + high) // 2
            candidate = destination.with_name(
                destination.stem + f".q{quality}.tmp.jpg"
            )
            size = save_candidate(image, candidate, quality)
            candidates.append((abs(size - target), size, candidate))
            if size < target:
                low = quality + 1
            elif size > target:
                high = quality - 1
            else:
                break

    _, final_size, best = min(candidates, key=lambda item: item[0])
    best_quality = int(best.stem.rsplit(".q", 1)[1].split(".", 1)[0])
    os.replace(best, destination)
    for _, _, candidate in candidates:
        if candidate.exists():
            candidate.unlink()

    with Image.open(destination) as check:
        result = {
            "source": str(source),
            "destination": str(destination),
            "quality": best_quality,
            "subsampling": "4:2:0",
            "target_bytes": target,
            "actual_bytes": final_size,
            "dimensions": check.size,
            "dimensions_match": check.size == original_size,
            "dpi": check.info.get("dpi"),
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["dimensions_match"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
