from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def composite(paths: list[Path], reverse: bool) -> Image.Image:
    ordered = list(reversed(paths)) if reverse else paths
    with Image.open(ordered[0]) as first:
        result = Image.new("RGBA", first.size, (0, 0, 0, 0))
    for path in ordered:
        with Image.open(path) as opened:
            layer = opened.convert("RGBA")
            if layer.size != result.size:
                raise RuntimeError(f"Size mismatch: {path}")
            result = Image.alpha_composite(result, layer)
    return result


def error(a: Image.Image, b: Image.Image) -> float:
    aa = np.asarray(a.convert("RGBA"), dtype=np.float32)
    bb = np.asarray(b.convert("RGBA"), dtype=np.float32)
    return float(np.mean(np.abs(aa - bb)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("layers_dir", type=Path)
    parser.add_argument("full_image", type=Path)
    parser.add_argument("output_composite", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    paths = sorted(args.layers_dir.glob("*.png"))
    if not paths:
        raise RuntimeError("No layer PNG files found")
    with Image.open(args.full_image) as opened:
        full = opened.convert("RGBA")
    forward = composite(paths, False)
    backward = composite(paths, True)
    forward_error = error(forward, full)
    reverse_error = error(backward, full)
    best = forward if forward_error <= reverse_error else backward
    order = "filename_ascending_bottom_to_top" if forward_error <= reverse_error else "filename_descending_bottom_to_top"
    args.output_composite.parent.mkdir(parents=True, exist_ok=True)
    best.save(args.output_composite)
    report = {"schema": "qwen_recomposition_check_v1", "layer_count": len(paths), "forward_mae": forward_error, "reverse_mae": reverse_error, "selected_order": order, "composite": str(args.output_composite.resolve())}
    report_path = args.report or args.output_composite.with_suffix(".json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
