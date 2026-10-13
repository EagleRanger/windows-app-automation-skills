from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps


EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".psd"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect(inputs: list[Path], recursive: bool) -> list[Path]:
    files: set[Path] = set()
    for item in inputs:
        resolved = item.resolve()
        if resolved.is_file() and resolved.suffix.lower() in EXTENSIONS:
            files.add(resolved)
        elif resolved.is_dir():
            iterator = resolved.rglob("*") if recursive else resolved.glob("*")
            files.update(path.resolve() for path in iterator if path.is_file() and path.suffix.lower() in EXTENSIONS)
    return sorted(files, key=lambda path: str(path).casefold())


def inspect(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        transposed = ImageOps.exif_transpose(image)
        dpi = image.info.get("dpi")
        icc = image.info.get("icc_profile", b"")
        return {
            "path": str(path),
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "format": image.format,
            "stored_size": list(image.size),
            "oriented_size": list(transposed.size),
            "mode": transposed.mode,
            "dpi": [float(value) for value in dpi] if dpi else None,
            "icc_bytes": len(icc),
            "icc_sha256": hashlib.sha256(icc).hexdigest() if icc else None,
            "exif_bytes": len(image.info.get("exif", b"")),
            "has_alpha": "A" in transposed.getbands() or "transparency" in image.info,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a read-only image source inventory.")
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--recursive", action="store_true")
    args = parser.parse_args()

    files = collect(args.inputs, args.recursive)
    if not files:
        raise SystemExit("No supported image files found.")
    manifest = {
        "schema": "photoshop_source_inventory_v1",
        "count": len(files),
        "files": [inspect(path) for path in files],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "success", "count": len(files), "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
