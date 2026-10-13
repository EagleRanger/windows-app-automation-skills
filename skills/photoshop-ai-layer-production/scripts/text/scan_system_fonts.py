from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont
from PIL import ImageFont


def font_name(font: TTFont, name_id: int) -> str:
    records = font["name"].names
    preferred = [record for record in records if record.nameID == name_id]
    preferred.sort(key=lambda record: (record.platformID != 3, record.langID != 0x409))
    for record in preferred:
        try:
            value = record.toUnicode().strip()
            if value:
                return value
        except Exception:
            continue
    return ""


def iter_faces(path: Path):
    if path.suffix.lower() in {".ttc", ".otc"}:
        collection = TTCollection(str(path), lazy=True)
        for index, font in enumerate(collection.fonts):
            yield index, font
        return
    yield 0, TTFont(str(path), lazy=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--ocr-json", type=Path, required=True)
    parser.add_argument("--roots", type=Path, nargs="*")
    args = parser.parse_args()

    roots = args.roots or [
        Path(r"C:\Windows\Fonts"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
        Path(r"C:\Program Files\Common Files\Adobe\Fonts"),
    ]
    ocr = json.loads(args.ocr_json.read_text(encoding="utf-8"))["results"][0]["res"]
    task_chars = sorted({char for text in ocr["rec_texts"] for char in text if not char.isspace()})

    files = []
    for root in roots:
        if root.is_dir():
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in {".ttf", ".otf", ".ttc", ".otc"}
            )

    fonts = []
    failures = []
    seen = set()
    for path in sorted(set(files), key=lambda item: str(item).lower()):
        try:
            for index, font in iter_faces(path):
                try:
                    postscript = font_name(font, 6)
                    family = font_name(font, 1)
                    style = font_name(font, 2)
                    if not postscript or postscript in seen:
                        continue
                    cmap = font.getBestCmap() or {}
                    missing = [char for char in task_chars if ord(char) not in cmap]
                    ImageFont.truetype(str(path), 64, index=index)
                    fonts.append(
                        {
                            "postscript": postscript,
                            "family": family,
                            "style": style,
                            "path": str(path),
                            "index": index,
                            "missing_chars": missing,
                        }
                    )
                    seen.add(postscript)
                finally:
                    try:
                        font.close()
                    except Exception:
                        pass
        except Exception as exc:
            failures.append({"path": str(path), "reason": str(exc)})

    payload = {
        "schema": "local_font_inventory_v1",
        "roots": [str(root) for root in roots],
        "task_characters": task_chars,
        "font_count": len(fonts),
        "file_count": len(set(files)),
        "failure_count": len(failures),
        "fonts": fonts,
        "failures": failures,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output.resolve()),
        "font_count": len(fonts),
        "file_count": len(set(files)),
        "failure_count": len(failures),
        "fully_support_task": sum(1 for font in fonts if not font["missing_chars"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
