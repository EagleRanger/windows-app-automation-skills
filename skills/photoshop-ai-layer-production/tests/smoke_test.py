from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, *arguments], check=True)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ps-ai-layer-skill-") as folder:
        temp = Path(folder)
        source = Image.new("RGB", (80, 60), (245, 245, 245))
        ImageDraw.Draw(source).rectangle((20, 15, 60, 45), fill=(20, 90, 180))
        source_path = temp / "source.png"
        source.save(source_path, dpi=(300, 300))
        layers_dir = temp / "qwen" / "layers"
        full_dir = temp / "qwen" / "full"
        layers_dir.mkdir(parents=True)
        full_dir.mkdir(parents=True)
        bottom = Image.new("RGBA", (20, 15), (245, 245, 245, 255))
        top = Image.new("RGBA", (20, 15), (0, 0, 0, 0))
        ImageDraw.Draw(top).rectangle((5, 4, 15, 11), fill=(20, 90, 180, 255))
        bottom.save(layers_dir / "layer_00001_.png")
        top.save(layers_dir / "layer_00002_.png")
        Image.alpha_composite(bottom, top).save(full_dir / "full_00001_.png")
        mapping = {
            "schema": "photoshop_ai_layer_map_v1",
            "layers": [
                {"index": 1, "name": "背景", "mode": "ai_rgba", "group": "底图", "ai_inferred": True},
                {"index": 2, "name": "前景", "mode": "original_rgb_masked", "group": "前景", "ai_inferred": False},
            ],
        }
        mapping_path = temp / "mapping.json"
        mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
        restored = temp / "restored"
        run(str(ROOT / "scripts" / "restore_original_size_layers.py"), "--source", str(source_path), "--layers-dir", str(temp / "qwen"), "--mapping", str(mapping_path), "--output-dir", str(restored))
        outputs = sorted(restored.glob("*.png"))
        assert len(outputs) == 2
        for path in outputs:
            with Image.open(path) as image:
                assert image.size == source.size
                assert image.mode == "RGBA"
        run(str(ROOT / "scripts" / "make_contact_sheet.py"), str(temp / "qwen"), str(temp / "contact.jpg"), "--thumb", "120", "--columns", "2")
        run(str(ROOT / "scripts" / "verify_recomposition.py"), str(layers_dir), str(full_dir / "full_00001_.png"), str(temp / "composite.png"))
        ocr = {"width": 80, "height": 60, "records": [{"text": "测试", "x": 10, "y": 8, "width": 20, "height": 10, "tile": 1}, {"text": "测试", "x": 11, "y": 8, "width": 20, "height": 10, "tile": 2}]}
        ocr_path = temp / "ocr.json"
        ocr_path.write_text(json.dumps(ocr, ensure_ascii=False), encoding="utf-8")
        text_manifest = temp / "text.json"
        run(str(ROOT / "scripts" / "text" / "build_text_manifest_windows.py"), str(ocr_path), str(source_path), str(text_manifest))
        manifest = json.loads(text_manifest.read_text(encoding="utf-8"))
        assert manifest["layer_count"] == 1
        model_manifest = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))
        assert sum(item["bytes"] for item in model_manifest["models"]) == model_manifest["total_download_bytes"]
    print("SMOKE_TEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
