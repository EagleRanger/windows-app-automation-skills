"""Synthetic contract tests, not a real document or visual acceptance run."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from check_release_receipt import DELIVERY_CHECKS, POLICY, ReceiptError, digest, validate


class ReleaseReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="report-gate-test-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        refs = {}
        for name in ("artifact", "snapshot", "evidence"):
            path = root / f"{name}.txt"
            path.write_text(f"SYNTHETIC FIXTURE ONLY: {name}", encoding="utf8")
            refs[name] = {"path": str(path), "sha256": digest(path)}
        evidence = refs["evidence"]
        self.receipt = {
            "policy_version": POLICY, "method_id": "synthetic-test-only", "open_findings": [],
            "artifact": refs["artifact"], "sources": evidence,
            "snapshot": dict(refs["snapshot"], input_sha256=refs["artifact"]["sha256"], page_count=2, renderer="fixture"),
            "reviewer": {"identity": "test-not-human", "mode": "self_review"},
            "checks": {key: {"status": "pass", "evidence": evidence} for key in DELIVERY_CHECKS},
            "samples": {"required_types": ["long_title", "landscape"], "passed_types": ["long_title", "landscape"], "evidence": evidence},
            "visual": {"normal_reading_size": True, "reviewed_pages": [1, 2], "evidence": evidence},
            "materials": {"expected_ids": ["A"], "items": [
                {"id": "A", "disposition": "retained", "source_checked": True, "first_checked": True,
                 "last_checked": True, "next_boundary_checked": True, "output_pages": [1, 2], "evidence": evidence}]}}

    def reject(self, mutate, expected, stage="delivery"):
        value = copy.deepcopy(self.receipt)
        mutate(value)
        with self.assertRaisesRegex(ReceiptError, expected):
            validate(value, stage)

    def test_good_delivery_is_receipt_only(self):
        result = validate(self.receipt, "delivery")
        self.assertEqual(result["status"], "receipt_consistent")
        self.assertIn("not visual truth", result["limitation"])

    def test_batch_is_not_delivery(self):
        del self.receipt["materials"]
        del self.receipt["visual"]
        self.assertEqual(validate(self.receipt, "batch")["status"], "receipt_consistent")
        with self.assertRaisesRegex(ReceiptError, "visual: missing"):
            validate(self.receipt, "delivery")

    def test_old_policy(self):
        self.reject(lambda r: r.update(policy_version="RA-20260905-v3"), "policy_version")

    def test_stale_artifact(self):
        self.reject(lambda r: r["artifact"].update(sha256="0" * 64), "artifact: stale")

    def test_stale_snapshot(self):
        self.reject(lambda r: r["snapshot"].update(sha256="0" * 64), "snapshot: stale")

    def test_snapshot_bound_to_other_file(self):
        self.reject(lambda r: r["snapshot"].update(input_sha256="0" * 64), "not bound")

    def test_missing_source_evidence(self):
        self.reject(lambda r: r["sources"].update(path=str(Path(self.temp.name) / "absent")), "file missing")

    def test_missing_editability_check(self):
        self.reject(lambda r: r["checks"].pop("editability"), "editability: missing", "batch")

    def test_unpassed_sample_blocks_batch(self):
        self.reject(lambda r: r["samples"].update(passed_types=["long_title"]), "type coverage", "batch")

    def test_thumbnails_not_normal_reading(self):
        self.reject(lambda r: r["visual"].update(normal_reading_size=False), "thumbnails")

    def test_missing_visual_page(self):
        self.reject(lambda r: r["visual"].update(reviewed_pages=[1]), "page coverage")

    def test_duplicate_visual_page(self):
        self.reject(lambda r: r["visual"].update(reviewed_pages=[1, 1, 2]), "duplicate")

    def test_unreconciled_material(self):
        self.reject(lambda r: r["materials"].update(expected_ids=["A", "B"]), "not fully reconciled")

    def test_last_page_unchecked(self):
        self.reject(lambda r: r["materials"]["items"][0].update(last_checked=False), "last_checked")

    def test_next_boundary_unchecked(self):
        self.reject(lambda r: r["materials"]["items"][0].update(next_boundary_checked=False), "next_boundary_checked")

    def test_user_deletion_without_instruction(self):
        self.reject(lambda r: r["materials"]["items"][0].update(disposition="user_removed", output_pages=[]), "deletion instruction missing")

    def test_explicit_user_deletion_record(self):
        self.receipt["materials"]["items"][0].update(disposition="user_removed", output_pages=[], removal_instruction="synthetic instruction")
        self.assertEqual(validate(self.receipt, "delivery")["status"], "receipt_consistent")

    def test_open_findings(self):
        self.reject(lambda r: r.update(open_findings=["red_head_hidden"]), "unresolved")

    def test_unexplained_not_applicable(self):
        self.reject(lambda r: r["checks"]["toc_pagination"].update(status="not_applicable"), "unsupported exemption")

    def test_geometry_cannot_be_exempted(self):
        self.reject(lambda r: r["checks"]["geometry"].update(status="not_applicable", reason="want to pass"), "unsupported exemption")

    def run_cli(self, path):
        return subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("check_release_receipt.py")),
                               str(path), "--stage", "delivery"], capture_output=True, text=True, encoding="utf8")

    def test_cli_valid_receipt(self):
        path = Path(self.temp.name) / "receipt.json"
        path.write_text(json.dumps(self.receipt), encoding="utf8")
        result = self.run_cli(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "receipt_consistent")

    def test_cli_missing_file(self):
        result = self.run_cli(Path(self.temp.name) / "absent.json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def test_cli_malformed_json(self):
        path = Path(self.temp.name) / "receipt.json"
        path.write_text("not json", encoding="utf8")
        result = self.run_cli(path)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def test_cli_unchecked_last_page(self):
        self.receipt["materials"]["items"][0]["last_checked"] = False
        path = Path(self.temp.name) / "receipt.json"
        path.write_text(json.dumps(self.receipt), encoding="utf8")
        result = self.run_cli(path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("last_checked", json.loads(result.stdout)["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
