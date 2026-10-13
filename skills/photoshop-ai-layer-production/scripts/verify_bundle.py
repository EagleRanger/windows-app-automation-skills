from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    manifest_path = ROOT / "PACKAGE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = []
    for item in manifest["files"]:
        path = ROOT / Path(item["path"])
        row = {"path": item["path"], "exists": path.is_file(), "ok": False}
        if path.is_file():
            row["bytes_ok"] = path.stat().st_size == item["bytes"]
            row["sha256_ok"] = digest(path).lower() == item["sha256"].lower()
            row["ok"] = row["bytes_ok"] and row["sha256_ok"]
        checks.append(row)
    ok = len(checks) == manifest["file_count"] and all(item["ok"] for item in checks)
    print(json.dumps({"status": "success" if ok else "failed", "checked": len(checks), "failures": [item for item in checks if not item["ok"]]}, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
