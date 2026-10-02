"""Director evidence handoff, capability fallback, and artifact integrity."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent/scripts"))

from prepare_analysis import prepare, summarize
from validate_analysis import load_json, validate_document


class DirectorTests(unittest.TestCase):
    def test_evidence_manifest_routes_to_visual_review(self):
        document = load_json(ROOT / "tests/fixtures/activity-valid.json")
        manifest = summarize(document)
        self.assertEqual(manifest["status"], "ready_for_visual_review")
        self.assertTrue(manifest["machine_evidence_available"])
        self.assertTrue(manifest["editor_review_required"])
        self.assertEqual(manifest["next_state"], "INSPECT")
        self.assertEqual(manifest["evidence_counts"]["candidate_dead_time"], 1)
        self.assertEqual(manifest["analyzer_runs"][0]["status"], "success")
        self.assertEqual(document["segments"], [])

    def test_every_provider_status_is_routed_without_editorial_claims(self):
        for status in ("success", "partial", "no_results", "unavailable", "failed", "skipped"):
            document = load_json(ROOT / "tests/fixtures/unavailable-valid.json")
            document["evidence"]["runs"][0]["status"] = status
            manifest = summarize(document)
            self.assertEqual(manifest["status"], "manual_review_required")
            self.assertEqual(manifest["analyzer_runs"][0]["status"], status)
            self.assertEqual(manifest["next_state"], "INSPECT")
            self.assertTrue(manifest["sources"][0]["timing_requires_verification"])

    def test_actual_cli_without_packages_or_executables(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.mp4"
            source.write_bytes(b"original source")
            output = Path(directory) / "job"
            environment = {**os.environ, "PATH": str(Path(directory) / "no-tools"), "PYTHONPATH": ""}
            result = subprocess.run(
                [sys.executable, "-S", str(ROOT / "agent/scripts/prepare_analysis.py"),
                 str(source), "--output-dir", str(output)],
                env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            document = load_json(output / "analysis.json")
            manifest = load_json(output / "handoff.json")
            self.assertEqual(validate_document(document), [])
            self.assertEqual([run["status"] for run in manifest["analyzer_runs"]], ["unavailable"] * 3)
            self.assertEqual(manifest["status"], "manual_review_required")
            self.assertEqual(document["segments"], [])
            self.assertEqual(source.read_bytes(), b"original source")
            self.assertEqual(manifest["sources"][0]["path"], str(source.resolve()))
            result = subprocess.run(
                [sys.executable, "-S", str(ROOT / "agent/scripts/prepare_analysis.py"),
                 str(source), "--output-dir", str(output)],
                env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(load_json(output / "analysis.json"), document)

    def test_manual_duration_and_opt_out_preserve_source_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            sources = [Path(directory) / name for name in ("one.mp4", "two.mp4")]
            for source in sources:
                source.write_bytes(b"source")
            with patch("analyzers.media_probe.executable", side_effect=RuntimeError("tool failed")):
                manifest = prepare(sources, Path(directory) / "job", providers=[],
                                   supplied_metadata={"duration": 4})
            self.assertEqual(len(manifest["analyzer_runs"]), 2)
            self.assertEqual([item["source_id"] for item in manifest["sources"]], ["source-1", "source-2"])
            self.assertTrue(all(item["duration"] == 4 for item in manifest["sources"]))
            self.assertTrue(all(not item["timing_requires_verification"] for item in manifest["sources"]))
            self.assertEqual(manifest["status"], "manual_review_required")

    def test_invalid_analysis_never_publishes_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.mp4"
            source.write_bytes(b"source")
            output = Path(directory) / "job"
            with patch("prepare_analysis.analyze", return_value={}):
                with self.assertRaises(ValueError):
                    prepare([source], output)
            self.assertFalse(output.exists())

    def test_failed_second_write_cleans_created_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.mp4"
            source.write_bytes(b"source")
            output = Path(directory) / "job"
            document = load_json(ROOT / "tests/fixtures/activity-valid.json")
            with patch("prepare_analysis.analyze", return_value=document), patch(
                "prepare_analysis.json.dump", side_effect=[None, OSError("disk failure")]):
                with self.assertRaises(OSError):
                    prepare([source], output)
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), b"source")

    def test_missing_input_and_output_collision_fail_before_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.mp4"
            source.write_bytes(b"source")
            for sources, output in (([], Path(directory) / "job"),
                                    ([Path(directory) / "missing.mp4"], Path(directory) / "job"),
                                    ([source], source)):
                with patch("prepare_analysis.analyze") as analyze:
                    with self.assertRaises(ValueError):
                        prepare(sources, output)
                    analyze.assert_not_called()
            self.assertEqual(source.read_bytes(), b"source")


if __name__ == "__main__":
    unittest.main()
