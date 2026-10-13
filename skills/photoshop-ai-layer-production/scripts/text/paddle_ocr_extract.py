from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from paddleocr import PaddleOCR


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def result_payload(result: Any) -> Any:
    payload = getattr(result, "json", result)
    if callable(payload):
        payload = payload()
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return {"raw": payload}
    return jsonable(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local PaddleOCR and keep polygons, text, scores and word boxes.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, default=4096)
    args = parser.parse_args()

    if not args.input.is_file():
        raise FileNotFoundError(args.input)

    ocr = PaddleOCR(
        lang="ch",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_det_limit_side_len=args.limit,
        text_det_limit_type="max",
        text_rec_score_thresh=0.20,
        return_word_box=True,
        enable_mkldnn=False,
    )
    raw_results = list(
        ocr.predict(
            str(args.input),
            text_det_limit_side_len=args.limit,
            text_det_limit_type="max",
            text_rec_score_thresh=0.20,
            return_word_box=True,
        )
    )
    payload = {
        "input": str(args.input.resolve()),
        "limit": args.limit,
        "results": [result_payload(result) for result in raw_results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def find_rec(node: Any) -> tuple[list[Any], list[Any]]:
        if isinstance(node, dict):
            if "rec_texts" in node:
                return list(node.get("rec_texts", [])), list(node.get("rec_scores", []))
            for item in node.values():
                texts, scores = find_rec(item)
                if texts:
                    return texts, scores
        elif isinstance(node, list):
            for item in node:
                texts, scores = find_rec(item)
                if texts:
                    return texts, scores
        return [], []

    texts, scores = find_rec(payload)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "result_count": len(raw_results),
        "text_count": len(texts),
        "items": [
            {"text": str(text), "score": float(scores[index]) if index < len(scores) else None}
            for index, text in enumerate(texts)
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
