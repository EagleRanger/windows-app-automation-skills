from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def iou(a: dict, b: dict) -> float:
    ax1, ay1, ax2, ay2 = a["x"], a["y"], a["x"] + a["width"], a["y"] + a["height"]
    bx1, by1, bx2, by2 = b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"]
    area = max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))
    union = a["width"] * a["height"] + b["width"] * b["height"] - area
    return area / union if union else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ocr_json", type=Path)
    parser.add_argument("target_image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--font", default="MicrosoftYaHei")
    parser.add_argument("--dpi", type=float)
    parser.add_argument("--group", default="OCR文字_需人工校对")
    args = parser.parse_args()
    ocr = json.loads(args.ocr_json.read_text(encoding="utf-8-sig"))
    records = []
    for item in ocr["records"]:
        if not item["text"].strip():
            continue
        duplicate = next((old for old in records if old["text"] == item["text"] and iou(old, item) >= 0.55), None)
        if duplicate is None:
            records.append(item)
    with Image.open(args.target_image) as image:
        width, height = image.size
        dpi = args.dpi or (image.info.get("dpi") or (72.0, 72.0))[0]
    sx = width / ocr["width"]
    sy = height / ocr["height"]
    layers = []
    for index, item in enumerate(records):
        x = item["x"] * sx
        y = item["y"] * sy
        w = item["width"] * sx
        h = item["height"] * sy
        size_pt = max(1.0, h * 72.0 / dpi * 0.9)
        text = item["text"].strip()
        layers.append({
            "name": f"{args.group}_{index:04d}_{text[:24]}",
            "group": args.group,
            "text": text,
            "font": args.font,
            "size_pt": round(size_pt, 4),
            "horizontal_scale": 100,
            "vertical_scale": 100,
            "tracking": 0,
            "color_rgb": [0, 0, 0],
            "position_px": [round(x, 2), round(y + h, 2)],
            "bbox_px": [round(x, 2), round(y, 2), round(x + w, 2), round(y + h, 2)],
            "status": "windows_ocr_requires_manual_review",
        })
    payload = {
        "schema": "photoshop_editable_text_manifest_v1",
        "document": {"width_px": width, "height_px": height, "resolution_dpi": dpi},
        "layer_count": len(layers),
        "notes": ["Windows OCR does not provide a calibrated confidence score here.", "Font and color are defaults until manually reviewed."],
        "layers": layers,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "layer_count": len(layers)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
