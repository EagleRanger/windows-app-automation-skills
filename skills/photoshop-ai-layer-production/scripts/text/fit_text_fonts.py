from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


FONT_CANDIDATES = {
    "SimHei": r"C:\Windows\Fonts\simhei.ttf",
    "MicrosoftYaHei": r"C:\Windows\Fonts\msyh.ttc",
    "MicrosoftYaHei-Bold": r"C:\Windows\Fonts\msyhbd.ttc",
    "DengXian": r"C:\Windows\Fonts\Deng.ttf",
    "DengXian-Bold": r"C:\Windows\Fonts\Dengb.ttf",
    "SimSun": r"C:\Windows\Fonts\simsun.ttc",
    "FangSong": r"C:\Windows\Fonts\simfang.ttf",
    "KaiTi": r"C:\Windows\Fonts\simkai.ttf",
    "ArialMT": r"C:\Windows\Fonts\arial.ttf",
    "Arial-BoldMT": r"C:\Windows\Fonts\arialbd.ttf",
    "TimesNewRomanPSMT": r"C:\Windows\Fonts\times.ttf",
    "TimesNewRomanPS-BoldMT": r"C:\Windows\Fonts\timesbd.ttf",
}

NON_TEXT_FONT_MARKERS = {
    "esri",
    "symbol",
    "wingdings",
    "webdings",
    "marlett",
    "script",
    "corsiva",
    "kunstler",
    "vladimir",
    "palace",
    "symusic",
    "music",
    "greek",
    "hazard",
    "stliti",
    "lisu",
    "chiller",
    "jokerman",
    "harlow",
    "harrington",
    "matura",
    "playbill",
    "ravie",
    "snap",
}


def reasonable_text_font(font_item: dict, text: str) -> bool:
    if any(ord(char) > 127 for char in text if not char.isspace()):
        return True
    descriptor = (
        str(font_item.get("postscript", ""))
        + " "
        + str(font_item.get("family", ""))
        + " "
        + str(font_item.get("style", ""))
    ).lower()
    return not any(marker in descriptor for marker in NON_TEXT_FONT_MARKERS)


def crop_mask(gray: np.ndarray, poly: list[list[int]]) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    points = np.asarray(poly)
    x0, y0 = points[:, 0].min(), points[:, 1].min()
    x1, y1 = points[:, 0].max(), points[:, 1].max()
    crop = gray[y0 : y1 + 1, x0 : x1 + 1]
    _, mask = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    cleaned = np.zeros_like(mask)
    min_area = max(4, int(mask.size * 0.0005))
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] >= min_area:
            cleaned[labels == label] = 255
    ys, xs = np.where(cleaned > 0)
    if not len(xs):
        return cleaned, (int(x0), int(y0), int(x1), int(y1))
    return cleaned[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1], (
        int(x0),
        int(y0),
        int(x1),
        int(y1),
    )


@lru_cache(maxsize=None)
def load_font(font_path: str, index: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path, 240, index=index)


def rendered_mask(text: str, font_path: str, index: int = 0) -> np.ndarray:
    font = load_font(font_path, index)
    box = font.getbbox(text)
    width = max(1, box[2] - box[0])
    height = max(1, box[3] - box[1])
    image = Image.new("L", (width + 32, height + 32), 0)
    draw = ImageDraw.Draw(image)
    draw.text((16 - box[0], 16 - box[1]), text, font=font, fill=255)
    mask = np.asarray(image)
    ys, xs = np.where(mask > 16)
    return mask[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]


def compare(source: np.ndarray, candidate: np.ndarray) -> float:
    resized = cv2.resize(candidate, (source.shape[1], source.shape[0]), interpolation=cv2.INTER_AREA)
    a = cv2.GaussianBlur(source.astype(np.float32) / 255.0, (3, 3), 0)
    b = cv2.GaussianBlur(resized.astype(np.float32) / 255.0, (3, 3), 0)
    return float(np.mean(np.abs(a - b)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("ocr_json", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--font-inventory", type=Path)
    args = parser.parse_args()

    gray = np.asarray(Image.open(args.image).convert("L"))
    result = json.loads(args.ocr_json.read_text(encoding="utf-8"))["results"][0]["res"]
    if args.font_inventory:
        inventory = json.loads(args.font_inventory.read_text(encoding="utf-8"))
        font_candidates = [
            item for item in inventory["fonts"]
        ]
    else:
        font_candidates = [
            {
                "postscript": postscript,
                "path": path,
                "index": 0,
                "missing_chars": [],
            }
            for postscript, path in FONT_CANDIDATES.items()
        ]
    fits = []
    for index, (text, score, poly) in enumerate(
        zip(result["rec_texts"], result["rec_scores"], result["rec_polys"])
    ):
        source, rect = crop_mask(gray, poly)
        if source.size == 0 or min(source.shape) < 4:
            continue
        ranked = []
        for font_item in font_candidates:
            if not reasonable_text_font(font_item, text):
                continue
            postscript_name = font_item["postscript"]
            font_path = font_item["path"]
            font_index = int(font_item.get("index", 0))
            missing = set(font_item.get("missing_chars", []))
            if any(char in missing for char in text if not char.isspace()):
                continue
            try:
                candidate = rendered_mask(text, font_path, font_index)
                ranked.append(
                    {
                        "font": postscript_name,
                        "font_path": font_path,
                        "font_index": font_index,
                        "font_family": font_item.get("family", ""),
                        "font_style": font_item.get("style", ""),
                        "error": compare(source, candidate),
                        "natural_ratio": candidate.shape[1] / max(1, candidate.shape[0]),
                    }
                )
            except Exception as exc:
                ranked.append({"font": postscript_name, "error": None, "reason": str(exc)})
        ranked = sorted(ranked, key=lambda item: 99 if item["error"] is None else item["error"])
        if len(ranked) < 2:
            continue
        fits.append(
            {
                "index": index,
                "text": text,
                "ocr_score": score,
                "rect": rect,
                "source_shape": [int(source.shape[1]), int(source.shape[0])],
                "source_ratio": source.shape[1] / max(1, source.shape[0]),
                "candidates": ranked,
            }
        )
    args.output.write_text(json.dumps({"fits": fits}, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in fits:
        best = item["candidates"][0]
        second = item["candidates"][1]
        print(
            f'{item["index"]:02d}\t{item["text"]}\t{best["font"]}\t'
            f'{best["error"]:.4f}\t{second["font"]}\t{second["error"]:.4f}'
        )


if __name__ == "__main__":
    main()
