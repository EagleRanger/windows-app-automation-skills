from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify file evidence after Photoshop assembly.")
    parser.add_argument("job_json", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    job = json.loads(args.job_json.read_text(encoding="utf-8"))
    output = Path(job["output_document"]).resolve()
    source = Path(job["source_image"]).resolve()
    receipt_path = args.receipt or Path(str(output) + ".receipt.json")
    checks = []
    checks.append({"name": "source_exists", "ok": source.is_file()})
    checks.append({"name": "output_exists", "ok": output.is_file(), "bytes": output.stat().st_size if output.is_file() else None})
    checks.append({"name": "receipt_exists", "ok": receipt_path.is_file()})
    for item in job["layers"]:
        path = Path(item["file"]).resolve()
        row = {"name": "asset:" + item["name"], "ok": path.is_file(), "path": str(path)}
        if path.is_file():
            with Image.open(path) as image:
                row["mode"] = image.mode
                row["size"] = list(image.size)
                row["ok"] = image.mode == "RGBA"
        checks.append(row)
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        checks.append({"name": "receipt_success", "ok": receipt.get("status") == "success"})
        checks.append({"name": "source_unchanged", "ok": receipt.get("source_unchanged") is True and receipt.get("source_sha256_after", "").lower() == digest(source).lower()})
        checks.append({"name": "layer_count", "ok": int(receipt.get("layer_count", -1)) == len(job["layers"])})
    ok = all(row["ok"] for row in checks)
    result = {"schema": "photoshop_delivery_verification_v1", "status": "success" if ok else "failed", "checks": checks, "visual_review": "required_separately"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
