from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the pinned ComfyUI/Qwen layered environment.")
    parser.add_argument("--comfy-root", type=Path, required=True)
    parser.add_argument("--server", default=None, help="Optional running ComfyUI URL, e.g. http://127.0.0.1:8188")
    parser.add_argument("--skip-hash", action="store_true")
    args = parser.parse_args()

    comfy = args.comfy_root.resolve()
    models = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "config" / "runtime-lock.json").read_text(encoding="utf-8"))
    checks: list[dict] = []

    main_py = comfy / "main.py"
    checks.append({"name": "comfy_main", "ok": main_py.is_file(), "path": str(main_py)})
    try:
        head = subprocess.check_output(["git", "-C", str(comfy), "rev-parse", "HEAD"], text=True).strip()
        checks.append({"name": "comfy_commit", "ok": head == lock["comfyui"]["commit"], "actual": head, "expected": lock["comfyui"]["commit"]})
    except Exception as exc:
        checks.append({"name": "comfy_commit", "ok": False, "error": str(exc)})

    for entry in models["models"]:
        path = comfy / Path(entry["relative_path"])
        row = {"name": entry["role"], "path": str(path), "exists": path.is_file(), "ok": False}
        if path.is_file():
            row["bytes"] = path.stat().st_size
            row["size_ok"] = row["bytes"] == entry["bytes"]
            if args.skip_hash:
                row["hash_ok"] = None
                row["ok"] = row["size_ok"]
            else:
                row["sha256"] = sha256(path)
                row["hash_ok"] = row["sha256"].lower() == entry["sha256"].lower()
                row["ok"] = row["size_ok"] and row["hash_ok"]
        checks.append(row)

    try:
        import torch

        checks.append({
            "name": "torch_cuda",
            "ok": bool(torch.cuda.is_available()),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        })
    except Exception as exc:
        checks.append({"name": "torch_cuda", "ok": False, "error": str(exc)})

    if args.server:
        try:
            with urllib.request.urlopen(args.server.rstrip("/") + "/object_info", timeout=30) as response:
                node_info = json.loads(response.read().decode("utf-8"))
            missing = [name for name in lock["required_nodes"] if name not in node_info]
            checks.append({"name": "required_nodes", "ok": not missing, "missing": missing})
        except Exception as exc:
            checks.append({"name": "required_nodes", "ok": False, "error": str(exc)})

    ok = all(item["ok"] for item in checks)
    print(json.dumps({"status": "success" if ok else "failed", "python": sys.version, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
