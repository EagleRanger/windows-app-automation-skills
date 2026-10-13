from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ALLOWED_ROLES = {
    "source_pixels",
    "ai_completion",
    "upper_element",
    "text_reference",
    "mask",
    "calibration",
    "original_reference",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(base: Path, raw: str) -> Path:
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Photoshop AI layer production manifest.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    base = manifest_path.parent
    errors: list[str] = []
    warnings: list[str] = []

    if data.get("schema") != "photoshop_ai_layer_production_v1":
        errors.append("schema must be photoshop_ai_layer_production_v1")

    source = data.get("source") or {}
    output = data.get("output") or {}
    permissions = data.get("permissions") or {}
    assets = data.get("assets") or []
    acceptance = data.get("acceptance") or {}

    source_path = resolve(base, str(source.get("path", "")))
    output_path = resolve(base, str(output.get("path", "")))
    expected_size = (int(source.get("width", 0)), int(source.get("height", 0)))
    if not source_path.is_file():
        errors.append(f"source is missing: {source_path}")
    else:
        actual_hash = sha256_file(source_path)
        if source.get("sha256") and actual_hash.lower() != str(source["sha256"]).lower():
            errors.append("source sha256 does not match")
        with Image.open(source_path) as image:
            if image.size != expected_size:
                errors.append(f"source dimensions {image.size} do not match {expected_size}")
            if source.get("mode") and image.mode != source["mode"]:
                errors.append(f"source mode {image.mode} does not match {source['mode']}")

    if source_path == output_path and not output.get("overwrite_authorized", False):
        errors.append("output resolves to source without overwrite authorization")
    expected_format = str(output.get("format", "")).upper()
    if expected_format not in {"PSD", "PSB"}:
        errors.append("output format must be PSD or PSB")
    if output_path.suffix.lower() != "." + expected_format.lower():
        errors.append("output extension does not match output format")

    names: set[str] = set()
    paths: set[Path] = set()
    for index, asset in enumerate(assets):
        prefix = f"asset[{index}]"
        name = str(asset.get("name", "")).strip()
        role = str(asset.get("role", ""))
        if not name:
            errors.append(f"{prefix} has no layer name")
        elif name in names:
            errors.append(f"duplicate layer name: {name}")
        names.add(name)
        if role not in ALLOWED_ROLES:
            errors.append(f"{prefix} has unknown role: {role}")
        if role == "ai_completion" and asset.get("inferred") is not True:
            errors.append(f"{prefix} AI completion must be marked inferred=true")
        asset_path = resolve(base, str(asset.get("path", "")))
        if asset_path in paths:
            errors.append(f"duplicate asset path: {asset_path}")
        paths.add(asset_path)
        if not asset_path.is_file():
            errors.append(f"{prefix} is missing: {asset_path}")
            continue
        if asset.get("sha256") and sha256_file(asset_path).lower() != str(asset["sha256"]).lower():
            errors.append(f"{prefix} sha256 does not match")
        with Image.open(asset_path) as image:
            if image.size != expected_size:
                errors.append(f"{prefix} dimensions {image.size} do not match {expected_size}")
            has_alpha = "A" in image.getbands() or "transparency" in image.info
            if asset.get("alpha_required") and not has_alpha:
                errors.append(f"{prefix} requires an alpha channel")

    if not assets:
        warnings.append("manifest has no external layer assets")
    if permissions.get("external_upload") not in {True, False}:
        errors.append("permissions.external_upload must be explicit")
    if permissions.get("restart_photoshop") is True:
        warnings.append("restart_photoshop is authorized; verify unsaved documents immediately before use")

    if args.require_complete:
        for key in ("connected", "readable", "written", "saved", "reopened", "source_unchanged", "visually_accepted"):
            if acceptance.get(key) is not True:
                errors.append(f"acceptance.{key} must be true for a complete run")
        if not output_path.is_file():
            errors.append(f"completed output is missing: {output_path}")

    result = {
        "status": "passed" if not errors else "failed",
        "manifest": str(manifest_path),
        "errors": errors,
        "warnings": warnings,
        "asset_count": len(assets),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
