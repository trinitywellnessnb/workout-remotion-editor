"""Semantic contract, provider isolation, and non-destructive analysis tests."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "workout-remotion-editor/scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_video import analyze, main
from analyzers.base import Result, Unavailable, command, run_provider
from analyzers.media_probe import MediaProbe, normalize_auto_info, normalize_ffprobe
from analyzers.motion_activity import MotionActivity, dead_time_candidates, parse_levels, regions
from analyzers.scene import Scene
from validate_analysis import SCHEMA_PATH, load_json, validate_document

FIXTURES = Path(__file__).with_name("fixtures")


def fixture(name: str) -> dict:
    return load_json(FIXTURES / name)


class ValidationTests(unittest.TestCase):
    def check(self, document: dict, valid: bool) -> None:
        for basic in (False, True):
            with self.subTest(basic=basic):
                errors = validate_document(document, basic=basic)
                self.assertEqual(not errors, valid, errors)

    def test_representative_fixtures(self):
        for path in sorted(FIXTURES.glob("*.json")):
            with self.subTest(fixture=path.name):
                self.check(load_json(path), path.name.endswith("-valid.json"))

    def test_schema_is_valid(self):
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    def test_legacy_confidence_and_timeline_preserved(self):
        data = fixture("legacy-valid.json")
        data["retention_plan"] = {"viewer_promise": "Show a verified rep", "payoff_beat_id": "payoff",
                                  "beats": [{"id": "payoff", "type": "payoff", "timeline_start": 0,
                                             "timeline_end": 1, "purpose": "Completion", "confidence": "high"}]}
        self.check(data, True)
        data["retention_plan"]["payoff_beat_id"] = "missing"
        self.check(data, False)

    def test_bad_ranges_and_confidences(self):
        for start, end in [(-1, 2), (2, 2), (3, 2), (0, 11), (False, 2), (0, float("nan")),
                           (float("inf"), 4), ("1", 4)]:
            data = fixture("scene-valid.json")
            data["evidence"]["scenes"][0].update(start=start, end=end)
            with self.subTest(start=start, end=end):
                self.check(data, False)
        for confidence in [-0.1, 1.1, float("nan"), float("inf"), True, "high"]:
            data = fixture("activity-valid.json")
            data["evidence"]["activity_regions"][0]["confidence"] = confidence
            self.check(data, False)

    def test_reference_status_and_order_semantics(self):
        mutations = [
            lambda d: d["evidence"]["scenes"][0].update(source_id="missing"),
            lambda d: d["evidence"]["scenes"][0].update(run_id="missing"),
            lambda d: d["evidence"]["scenes"][1].update(id="shot-1"),
            lambda d: d["evidence"]["scenes"][1].update(start=3),
            lambda d: d["evidence"]["runs"][0].update(status="unavailable", fallback=False),
            lambda d: d["evidence"]["runs"][0].update(status="failed", fallback=True, errors=[]),
            lambda d: d["sources"][0].update(duration=None),
            lambda d: d.update(schema_version="2.3"),
            lambda d: d["evidence"].update(unknown=[]),
        ]
        for mutation in mutations:
            data = fixture("scene-valid.json")
            mutation(data)
            self.check(data, False)

    def test_candidate_must_trace_to_supporting_signal(self):
        for value in ["missing", "audio-1"]:
            data = fixture("activity-valid.json")
            data["evidence"]["candidate_dead_time"][0]["signal_ids"] = [value]
            self.check(data, False)
        data = fixture("activity-valid.json")
        data["evidence"]["candidate_dead_time"][0]["end"] = 6
        self.check(data, False)

    def test_failed_analyzer_cannot_supply_evidence(self):
        data = fixture("scene-valid.json")
        data["evidence"]["runs"][0].update(status="failed", fallback=True, errors=["decoder failed"])
        self.check(data, False)

    def test_finite_media_metadata(self):
        data = fixture("legacy-valid.json")
        data["sources"][0]["duration"] = float("inf")
        self.check(data, False)

    def test_actual_import_fallback(self):
        import builtins
        original = builtins.__import__

        def no_jsonschema(name, *args, **kwargs):
            if name == "jsonschema":
                raise ImportError("optional validator unavailable")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=no_jsonschema):
            self.assertEqual(validate_document(fixture("scene-valid.json")), [])
            self.assertTrue(validate_document(fixture("timestamps-invalid.json")))


class NormalizationTests(unittest.TestCase):
    def test_levels_format_and_signal_values(self):
        self.assertEqual(parse_levels("\n@start\n0\n0.125\n1\n\n"), [0, 0.125, 1])
        self.assertEqual(parse_levels("@start\n"), [])
        for output in ["0\n1", "@start\nnan", "@start\n-0.1", "@start\n1.1", "@start\nnoise"]:
            with self.assertRaises(ValueError):
                parse_levels(output)

    def test_sampling_time_and_threshold_semantics(self):
        data = regions([0, 0, 0, 0.5, 0.5, 0], Fraction(2), 2.75, 0.02, "motion", "s")
        self.assertEqual([(item["start"], item["end"], item["type"]) for item in data],
                         [(0.5, 1.5, "low_motion"), (1.5, 2.5, "motion_active"),
                          (2.5, 2.75, "low_motion")])
        self.assertEqual(data[1]["mean_level"], 0.5)
        self.assertNotIn("confidence", data[1])
        rate = Fraction(30000, 1001)
        data = regions([0.04, 0, 0], rate, 1, 0.04, "audio", "s")
        self.assertAlmostEqual(data[0]["end"], 1001 / 30000)
        self.assertEqual(data[0]["type"], "audio_active")

    def test_no_extrapolation_or_quiet_only_dead_time(self):
        data = regions([0, 0], Fraction(1), 10, 0.04, "audio", "s")
        self.assertEqual(data[0]["end"], 2)
        self.assertEqual(dead_time_candidates(data, 1), [])
        self.assertEqual(regions([0], Fraction(30), 1, 0.02, "motion", "s"), [])

    def test_dead_time_minimum_and_audit_link(self):
        data = regions([0] * 6, Fraction(1), 6, 0.02, "motion", "s")
        candidates = dead_time_candidates(data, 2)
        self.assertEqual(candidates[0]["signal_ids"], [data[0]["id"]])
        self.assertIn("Editor decides", candidates[0]["reason"])
        self.assertEqual(dead_time_candidates(data, 6), [])

    def test_ffprobe_media_metadata(self):
        data = {"format": {"duration": "10"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080,
             "avg_frame_rate": "30000/1001", "time_base": "1/30000", "start_time": "0",
             "side_data_list": [{"rotation": 90}]},
            {"codec_type": "audio", "codec_name": "aac", "start_time": "0"}]}
        result = normalize_ffprobe(data)
        self.assertAlmostEqual(result["fps"], 30000 / 1001)
        self.assertEqual(result["rotation"], 90)
        self.assertTrue(result["metadata"]["timestamp_origin_verified"])
        del data["streams"][1]["start_time"]
        self.assertFalse(normalize_ffprobe(data)["metadata"]["timestamp_origin_verified"])
        data["streams"][1]["start_time"] = "0.1"
        self.assertFalse(normalize_ffprobe(data)["metadata"]["timestamp_origin_verified"])
        with self.assertRaises(ValueError):
            normalize_ffprobe({"streams": []})

    def test_auto_editor_info_fallback(self):
        data = {"video.mp4": {"video": [{"duration": 10, "resolution": [640, 480],
                                        "codec": "h264", "fps": "30"}], "audio": []}}
        result = normalize_auto_info(data)
        self.assertEqual(result["duration"], 10)
        self.assertFalse(result["metadata"]["timestamp_origin_verified"])


class ProviderTests(unittest.TestCase):
    def source(self):
        return {"id": "s", "path": "/fixture.mp4", "duration": 4,
                "metadata": {"timestamp_origin_verified": True, "audio_streams": 1}}

    def test_missing_optional_tools(self):
        with patch("analyzers.motion_activity.executable", side_effect=Unavailable("missing")):
            run, result = run_provider(MotionActivity(), self.source(), 1)
        self.assertEqual(run["status"], "unavailable")
        self.assertTrue(run["fallback"])
        self.assertFalse(result.evidence)
        with patch("analyzers.scene.importlib.util.find_spec", return_value=None):
            run, _ = run_provider(Scene(), self.source(), 1)
        self.assertEqual(run["status"], "unavailable")

    def test_scene_seconds_and_all_modes(self):
        for detector, kind in [("content", "hard_cut_candidate"), ("adaptive", "hard_cut_candidate"),
                               ("threshold", "fade_candidate")]:
            with patch("analyzers.scene.importlib.util.find_spec", return_value=object()), patch(
                "analyzers.scene.command", return_value=json.dumps({"version": "0.7.1",
                                                                    "scenes": [[0, 2], [2, 4]]})):
                run, result = run_provider(Scene(detector), self.source(), 1)
            self.assertEqual(result.evidence["scene_boundaries"][0]["time"], 2)
            self.assertEqual(result.evidence["scene_boundaries"][0]["kind"], kind)
            self.assertEqual(result.evidence["scenes"][0]["run_id"], run["id"])

    def test_vfr_final_scene_estimate_is_bounded_and_reported(self):
        source = self.source()
        source["fps"] = 24
        with patch("analyzers.scene.importlib.util.find_spec", return_value=object()), patch(
            "analyzers.scene.command", return_value=json.dumps({"version": "0.7.1",
                                                                "scenes": [[0, 2], [2, 4.01]]})):
            run, result = run_provider(Scene(), source, 1)
        self.assertEqual(result.evidence["scenes"][-1]["end"], 4)
        self.assertTrue(any("bounded to probed duration" in warning for warning in run["warnings"]))

    def test_scene_no_results_and_unsupported_format(self):
        with patch("analyzers.scene.importlib.util.find_spec", return_value=object()), patch(
            "analyzers.scene.command", return_value='{"version":"0.7.1","scenes":[]}'):
            run, _ = run_provider(Scene(), self.source(), 1)
            self.assertEqual(run["status"], "no_results")
        with patch("analyzers.scene.importlib.util.find_spec", return_value=object()), patch(
            "analyzers.scene.command", side_effect=RuntimeError("unsupported codec")):
            run, result = run_provider(Scene(), self.source(), 1)
            self.assertEqual(run["status"], "failed")
            self.assertTrue(run["fallback"])
            self.assertFalse(result.evidence)

    def test_auto_editor_only_analysis_commands_and_partial_failure(self):
        calls = []

        def fake(args, timeout, *rest):
            calls.append(args)
            if "--version" in args:
                return "31.6.0"
            if "audio:stream=0" in args:
                raise RuntimeError("audio decode failure")
            return "@start\n" + "0\n" * 120

        with patch("analyzers.motion_activity.executable", return_value="/auto-editor"), patch(
            "analyzers.motion_activity.command", side_effect=fake):
            run, result = run_provider(MotionActivity(), self.source(), 1)
        self.assertEqual(run["status"], "partial")
        self.assertTrue(result.evidence["candidate_dead_time"])
        self.assertTrue(run["errors"])
        for args in calls:
            self.assertTrue("--version" in args or args[1] == "levels")
            self.assertNotIn("--export", args)
            self.assertNotIn("-o", args)
            if args[1] == "levels":
                self.assertIn("--no-cache", args)

    def test_nonzero_origin_is_skipped(self):
        source = self.source()
        source["metadata"]["timestamp_origin_verified"] = False
        with patch("analyzers.motion_activity.executable", return_value="/auto-editor"), patch(
            "analyzers.motion_activity.command", return_value="31.6.0") as invoke:
            run, _ = run_provider(MotionActivity(), source, 1)
        self.assertEqual(run["status"], "skipped")
        self.assertEqual(invoke.call_count, 1)

    def test_multitrack_audio_signals_remain_separate(self):
        source = self.source()
        source["metadata"]["audio_streams"] = 2
        with patch("analyzers.motion_activity.executable", return_value="/auto-editor"), patch(
            "analyzers.motion_activity.command", side_effect=[
                "31.6.0", "@start\n" + "0\n" * 120,
                "@start\n" + "0\n" * 120, "@start\n" + "0.5\n" * 120]):
            _, result = run_provider(MotionActivity(), source, 1)
        audio = [item for item in result.evidence["activity_regions"] if item["type"].startswith("audio")]
        self.assertEqual([(item["type"], item["stream"]) for item in audio],
                         [("audio_inactive", 0), ("audio_active", 1)])

    def test_media_probe_falls_back_to_supplied_metadata(self):
        with patch("analyzers.media_probe.executable", side_effect=Unavailable("missing")):
            run, result = run_provider(MediaProbe({"duration": 4}), self.source(), 1)
        self.assertEqual(run["provider"], "supplied-metadata")
        self.assertEqual(result.metadata["duration"], 4)
        self.assertTrue(run["fallback"])

    def test_probe_failure_is_distinct_from_missing_tool(self):
        with patch("analyzers.media_probe.executable", return_value="/tool"), patch(
            "analyzers.media_probe.command", side_effect=RuntimeError("unsupported container")):
            run, result = run_provider(MediaProbe(), self.source(), 1)
        self.assertEqual(run["status"], "failed")
        self.assertTrue(run["errors"])
        self.assertEqual(result.metadata, {})

    def test_timeout_and_crashing_provider_do_not_abort(self):
        with patch("analyzers.motion_activity.executable", return_value="/auto-editor"), patch(
            "analyzers.motion_activity.command", side_effect=subprocess.TimeoutExpired("auto-editor", 1)):
            run, _ = run_provider(MotionActivity(), self.source(), 1)
        self.assertEqual(run["status"], "failed")

        class Broken:
            name, category, upstream, version, configuration = "broken", "scene", "fixture", None, {}

            def analyze(self, source, timeout):
                raise TypeError("malformed provider data")

        run, _ = run_provider(Broken(), self.source(), 1)
        self.assertEqual(run["status"], "failed")

    def test_subprocess_has_no_shell_and_enforces_timeout(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            command([sys.executable, "-c", "import time; time.sleep(2)"], 0.02)
        with self.assertRaises(RuntimeError):
            command([sys.executable, "-c", "print('x' * 100)"], 1, 10)


class WorkflowTests(unittest.TestCase):
    def test_all_tools_absent_still_emits_valid_unknown_duration_document(self):
        with patch("analyzers.media_probe.executable", side_effect=Unavailable("missing")), patch(
            "analyzers.scene.importlib.util.find_spec", return_value=None), patch(
            "analyzers.motion_activity.executable", side_effect=Unavailable("missing")):
            data = analyze([Path("raw.mp4")])
        self.assertIsNone(data["sources"][0]["duration"])
        self.assertEqual(data["segments"], [])
        self.assertEqual([run["status"] for run in data["evidence"]["runs"]], ["unavailable"] * 3)
        self.assertEqual(validate_document(data), [])

    def test_invalid_provider_output_quarantined(self):
        class Invalid:
            name, category, upstream, version, configuration = "invalid", "scene", "fixture", "1", {}

            def analyze(self, source, timeout):
                return Result(evidence={"scenes": [{"id": "bad", "start": 3, "end": 1,
                                                    "detector": "content", "reason": "bad ordering"}]})

        with patch("analyzers.media_probe.executable", side_effect=Unavailable("missing")):
            data = analyze([Path("raw.mp4")], supplied_metadata={"duration": 10}, providers=[Invalid()])
        self.assertEqual(data["evidence"]["runs"][-1]["status"], "failed")
        self.assertNotIn("scenes", data["evidence"])
        self.assertEqual(validate_document(data), [])

    def test_cli_preserves_source_bytes_and_validates_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.mp4"
            output = Path(directory) / "analysis.json"
            source.write_bytes(b"unsupported media must remain unchanged")
            with patch("sys.argv", ["analyze_video.py", str(source), "-o", str(output)]), patch(
                "analyzers.media_probe.executable", side_effect=Unavailable("missing")), patch(
                "analyzers.scene.importlib.util.find_spec", return_value=None), patch(
                "analyzers.motion_activity.executable", side_effect=Unavailable("missing")):
                self.assertEqual(main(), 0)
            self.assertEqual(source.read_bytes(), b"unsupported media must remain unchanged")
            self.assertEqual(validate_document(load_json(output)), [])
            with patch("sys.argv", ["analyze_video.py", str(source), "-o", str(source)]):
                with self.assertRaises(SystemExit):
                    main()

    def test_multiple_sources_and_legacy_sections_untouched(self):
        with patch("analyzers.media_probe.executable", side_effect=Unavailable("missing")):
            data = analyze([Path("one.mp4"), Path("two.mp4")], providers=[])
        self.assertEqual([source["id"] for source in data["sources"]], ["source-1", "source-2"])
        self.assertEqual(validate_document(data), [])
        self.assertEqual(data["segments"], [])
        self.assertNotIn("repetitions", data)


if __name__ == "__main__":
    unittest.main()
