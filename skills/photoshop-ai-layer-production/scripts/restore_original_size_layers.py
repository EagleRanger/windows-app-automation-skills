from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def safe_name(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", value).strip(" .") or "layer"


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore Qwen RGBA layers to the original canvas size.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--layers-dir", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source_path = args.source.resolve()
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    if mapping.get("schema") != "photoshop_ai_layer_map_v1":
        raise RuntimeError("Unexpected layer map schema")
    layer_paths = sorted((args.layers_dir / "layers").glob("*.png"))
    if not layer_paths:
        layer_paths = sorted(args.layers_dir.glob("*.png"))
    if not layer_paths:
        raise RuntimeError("No Qwen layer PNG files found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as opened:
        source = opened.convert("RGB")
        size = source.size
        dpi = opened.info.get("dpi")
        icc = opened.info.get("icc_profile")
    outputs = []
    for item in mapping["layers"]:
        index = int(item["index"])
        if index < 1 or index > len(layer_paths):
            raise IndexError(f"Layer index {index} is outside 1..{len(layer_paths)}")
        with Image.open(layer_paths[index - 1]) as opened:
            model = opened.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        if item["mode"] == "original_rgb_masked":
            result = source.convert("RGBA")
            result.putalpha(model.getchannel("A"))
        elif item["mode"] == "ai_rgba":
            result = model
        else:
            raise ValueError(f"Unsupported mode: {item['mode']}")
        output = args.output_dir / f"{index:03d}_{safe_name(item['name'])}.png"
        save_args = {}
        if dpi: save_args["dpi"] = dpi
        if icc: save_args["icc_profile"] = icc
        result.save(output, **save_args)
        outputs.append({"index": index, "name": item["name"], "mode": item["mode"], "path": str(output.resolve()), "size": list(size), "bytes": output.stat().st_size, "ai_inferred": bool(item.get("ai_inferred", item["mode"] == "ai_rgba"))})
    receipt = {"schema": "original_size_layer_receipt_v1", "source": str(source_path), "canvas": list(size), "outputs": outputs}
    receipt_path = args.output_dir / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
