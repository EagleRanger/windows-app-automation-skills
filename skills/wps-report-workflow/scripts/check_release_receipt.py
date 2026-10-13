"""Read-only RA-v4 receipt checks; never certify visual quality or grant authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

POLICY = "RA-20260905-v4"
BATCH_CHECKS = {"source_scope", "editability", "geometry", "protected_content", "preview_fidelity"}
DELIVERY_CHECKS = BATCH_CHECKS | {"content_inventory", "toc_pagination", "reference_fidelity", "cross_object_consistency", "reopen"}
OPTIONAL = {"toc_pagination", "reference_fidelity", "cross_object_consistency"}


class ReceiptError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReceiptError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def file_ref(value, label):
    require(isinstance(value, dict), f"{label}: missing file reference")
    raw, expected = value.get("path"), value.get("sha256")
    require(nonempty(raw), f"{label}: missing path")
    path = Path(raw)
    require(path.is_absolute() and not raw.startswith(("\\\\", "//")), f"{label}: absolute local path required")
    require(isinstance(expected, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected), f"{label}: invalid SHA256")
    require(path.is_file(), f"{label}: file missing")
    actual = digest(path)
    require(actual == expected.lower(), f"{label}: stale file fingerprint")
    return actual


def unique_list(value, label, integers=False, allow_empty=False):
    require(isinstance(value, list), f"{label}: list required")
    require(allow_empty or len(value) > 0, f"{label}: empty list")
    valid = all(type(v) is int and v > 0 for v in value) if integers else all(nonempty(v) for v in value)
    require(valid, f"{label}: invalid item")
    require(len(value) == len(set(value)), f"{label}: duplicate items")
    return set(value)


def validate(receipt, stage):
    require(stage in {"batch", "delivery"}, "invalid stage")
    require(isinstance(receipt, dict), "receipt must be an object")
    require(receipt.get("policy_version") == POLICY, "policy_version: obsolete or missing")
    require(nonempty(receipt.get("method_id")), "method_id: required")
    require(receipt.get("open_findings") == [], "open_findings: missing or unresolved")
    artifact_hash = file_ref(receipt.get("artifact"), "artifact")
    snapshot = receipt.get("snapshot")
    file_ref(snapshot, "snapshot")
    require(snapshot.get("input_sha256", "").lower() == artifact_hash, "snapshot: not bound to current artifact")
    pages = snapshot.get("page_count")
    require(type(pages) is int and 0 < pages <= 100000, "snapshot: invalid page_count")
    require(nonempty(snapshot.get("renderer")), "snapshot: renderer required")
    file_ref(receipt.get("sources"), "sources")
    reviewer = receipt.get("reviewer")
    require(isinstance(reviewer, dict) and nonempty(reviewer.get("identity")), "reviewer: identity required")
    require(reviewer.get("mode") in {"self_review", "independent_review"}, "reviewer: invalid mode")

    checks = receipt.get("checks")
    require(isinstance(checks, dict), "checks: missing")
    for key in sorted(DELIVERY_CHECKS if stage == "delivery" else BATCH_CHECKS):
        item = checks.get(key)
        require(isinstance(item, dict), f"checks.{key}: missing")
        status = item.get("status")
        if status == "not_applicable":
            require(key in OPTIONAL and nonempty(item.get("reason")), f"checks.{key}: unsupported exemption")
        else:
            require(status == "pass", f"checks.{key}: not passed")
        file_ref(item.get("evidence"), f"checks.{key}.evidence")

    samples = receipt.get("samples")
    require(isinstance(samples, dict), "samples: missing")
    required = unique_list(samples.get("required_types"), "samples.required_types")
    passed = unique_list(samples.get("passed_types"), "samples.passed_types")
    require(required == passed, "samples: incomplete or inconsistent type coverage")
    file_ref(samples.get("evidence"), "samples.evidence")

    if stage == "delivery":
        visual = receipt.get("visual")
        require(isinstance(visual, dict), "visual: missing")
        require(visual.get("normal_reading_size") is True, "visual: thumbnails cannot establish reading quality")
        reviewed = unique_list(visual.get("reviewed_pages"), "visual.reviewed_pages", integers=True)
        require(reviewed == set(range(1, pages + 1)), "visual: incomplete or out-of-range page coverage")
        file_ref(visual.get("evidence"), "visual.evidence")

        materials = receipt.get("materials")
        require(isinstance(materials, dict), "materials: missing")
        expected = unique_list(materials.get("expected_ids"), "materials.expected_ids")
        items = materials.get("items")
        require(isinstance(items, list) and all(isinstance(item, dict) for item in items), "materials.items: invalid")
        actual = unique_list([item.get("id") for item in items], "materials.items.ids")
        require(expected == actual, "materials: source inventory not fully reconciled")
        for item in items:
            label = f"materials.{item['id']}"
            require(item.get("source_checked") is True, f"{label}: source not checked")
            file_ref(item.get("evidence"), f"{label}.evidence")
            state = item.get("disposition")
            if state == "user_removed":
                require(nonempty(item.get("removal_instruction")), f"{label}: deletion instruction missing")
                require(item.get("output_pages") == [], f"{label}: removed item has output pages")
            else:
                require(state == "retained", f"{label}: unresolved disposition")
                for field in ("first_checked", "last_checked", "next_boundary_checked"):
                    require(item.get(field) is True, f"{label}: {field} missing")
                output = unique_list(item.get("output_pages"), f"{label}.output_pages", integers=True)
                require(output <= set(range(1, pages + 1)), f"{label}: output page out of range")

    return {"status": "receipt_consistent", "stage": stage, "policy_version": POLICY,
            "artifact_sha256": artifact_hash, "page_count": pages,
            "limitation": "Checks recorded evidence consistency only; not visual truth, authority, or user acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--stage", choices=("batch", "delivery"), required=True)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.receipt.read_text(encoding="utf-8-sig")), args.stage)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
