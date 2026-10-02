"""Deterministic Phase 4 taxonomy, context, fusion, lifecycle, and guard tests."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "workout-remotion-editor/scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_video import analyze
from analyzers.base import run_provider
from analyzers.exercise_recognition import (FakeActionProvider, Taxonomy, fuse,
                                             load_context, normalize_alias, propose_intervals)
from validate_analysis import validate_document


def context(label="One Arm DB Row", canonical="dumbbell_row_single_arm", scope="source"):
    return {"taxonomy_version": "1", "assertions": [{"id": "context-1", "source_id": "source-1",
        "scene_id": None, "entity_id": None, "start": None if scope == "source" else 2,
        "end": None if scope == "source" else 6, "canonical_exercise_id": canonical,
        "supplied_label": label, "source": "user_provided", "assertion_type": "explicit_identity",
        "scope": scope, "user_confirmed": True}], "ordered_plan": []}


def document():
    return {"schema_version": "2.5", "project": {"title": "x", "mode": "standard"},
            "sources": [{"id": "source-1", "path": "/x", "duration": 10}], "segments": [],
            "context": {"taxonomy_version": "1", "assertions": [], "ordered_plan": []},
            "evidence": {"runs": [], "scenes": [{"id": "scene-1", "source_id": "source-1",
                "run_id": "scene-run", "start": 0, "end": 10, "detector": "fixture", "reason": "fixture"}],
                "activity_regions": [{"id": "active-1", "source_id": "source-1", "run_id": "motion-run",
                    "start": 1, "end": 9, "type": "motion_active", "confidence": .8}]}}


class TaxonomyAndContextTests(unittest.TestCase):
    def setUp(self): self.taxonomy = Taxonomy.load()

    def test_alias_normalization_mapping_unknown_and_ambiguous(self):
        self.assertEqual(normalize_alias(" One-Arm  DB Row! "), "one arm db row")
        self.assertEqual(self.taxonomy.map_label("lawnmower row")["canonical_exercise_id"],
                         "dumbbell_row_single_arm")
        self.assertEqual(self.taxonomy.map_label("rows")["status"], "ambiguous")
        unknown = self.taxonomy.map_label("teleport press")
        self.assertEqual((unknown["status"], unknown["supplied_label"]), ("unmapped", "teleport press"))

    def test_context_file_and_cli_source_label(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "context.json"
            path.write_text(json.dumps(context()))
            parsed = load_context(path, [], ["source-1"], self.taxonomy)
        self.assertEqual(parsed["assertions"][0]["mapping_status"], "mapped")
        cli = load_context(None, ["lat pulldown"], ["source-1"], self.taxonomy)
        self.assertTrue(cli["assertions"][0]["user_confirmed"])
        with self.assertRaises(ValueError):
            load_context(None, ["curl"], ["source-1", "source-2"], self.taxonomy)

    def test_taxonomy_variants_remain_distinct_and_only_phase5_rule_active(self):
        self.assertNotEqual(self.taxonomy.entries["barbell_row"]["canonical_id"],
                            self.taxonomy.entries["dumbbell_row_single_arm"]["canonical_id"])
        active = {key: value["rep_rule_id"] for key, value in self.taxonomy.entries.items()
                  if value["rep_rule_id"] is not None}
        self.assertEqual(active, {"dumbbell_row_single_arm": "single_arm_dumbbell_row_v1"})


class ProposalFusionTests(unittest.TestCase):
    def setUp(self): self.taxonomy = Taxonomy.load()

    def test_scene_contained_interval_is_not_a_set(self):
        values = propose_intervals(document())
        self.assertEqual(values[0]["type"], "interval_candidate")
        self.assertEqual((values[0]["start"], values[0]["end"]), (1, 9))

    def test_short_motion_and_background_are_not_promoted(self):
        data = document()
        data["evidence"]["activity_regions"][0].update(start=1, end=1.5)
        self.assertEqual(propose_intervals(data), [])
        data = document()
        data["evidence"].update(tracked_entities=[{"id":"person-1","source_id":"source-1",
            "start":0,"end":10,"category":"person"}], entity_roles=[{"source_id":"source-1",
            "entity_id":"other","role":"primary_athlete_candidate"}])
        self.assertIsNone(propose_intervals(data)[0]["entity_id"])

    def test_explicit_source_and_interval_identity(self):
        for scope in ("source", "interval"):
            _, values = fuse(document(), self.taxonomy, context(scope=scope))
            self.assertTrue(values)
            self.assertEqual(values[0]["canonical_exercise_id"], "dumbbell_row_single_arm")
            self.assertTrue(values[0]["user_confirmed"])

    def test_ordered_plan_aligns_without_claiming_set(self):
        data = document()
        ctx = {"taxonomy_version":"1", "assertions":[],
            "ordered_plan":[{"canonical_exercise_id":"lat_pulldown","order":1}]}
        intervals, values = fuse(data, self.taxonomy, ctx)
        self.assertEqual(values[0]["canonical_exercise_id"], "lat_pulldown")
        self.assertEqual(intervals[0]["type"], "interval_candidate")

    def test_user_model_agreement_disagreement_top_k_and_ambiguity(self):
        action = [{"id":"model-1","source_id":"source-1","start":1,"end":9,
                   "canonical_exercise_id":"seated_cable_row","confidence":1}]
        _, values = fuse(document(), self.taxonomy, context("Row", "row_unspecified"), action)
        self.assertEqual([x["rank"] for x in values[:2]], [1, 2])
        self.assertEqual(values[0]["canonical_exercise_id"], "row_unspecified")
        self.assertEqual(values[0]["conflict_status"], "retained")
        self.assertIn("model-1", values[0]["conflicting_evidence_refs"])
        agreement = [{**action[0], "canonical_exercise_id":"row_unspecified"}]
        _, agreed = fuse(document(), self.taxonomy, context("Row", "row_unspecified"), agreement)
        self.assertEqual(agreed[0]["conflict_status"], "none")

    def test_close_scores_preserve_ambiguity(self):
        actions = [{"id":f"m-{i}","source_id":"source-1","start":1,"end":9,
                    "canonical_exercise_id":cid,"confidence":score} for i,(cid,score) in enumerate([
                        ("row_unspecified", .9), ("seated_cable_row", .8)])]
        _, values = fuse(document(), self.taxonomy, {"taxonomy_version":"1","assertions":[],"ordered_plan":[]}, actions)
        self.assertEqual(values[0]["ambiguity"]["status"], "unresolved")
        self.assertEqual(values[0]["score_type"], "fusion_score")


class LifecycleAndValidationTests(unittest.TestCase):
    def test_fake_provider_lifecycle(self):
        source = {"id":"source-1"}
        for requested, expected in [("unavailable","unavailable"),("failed","failed"),
                                    ("no_results","no_results"),("partial","partial")]:
            run, _ = run_provider(FakeActionProvider(status=requested), source, 1)
            self.assertEqual(run["status"], expected)
        run, _ = run_provider(FakeActionProvider(model=None), source, 1)
        self.assertEqual(run["status"], "unavailable")

    def test_action_provider_is_fused_and_disagreement_retained(self):
        raw = {"id":"raw-action", "source_id":"source-1", "run_id":"placeholder",
               "scene_id":None, "entity_id":None, "start":0, "end":10,
               "label":"Seated Cable Row", "canonical_exercise_id":"seated_cable_row",
               "taxonomy_version":"1", "source_type":"action_model", "provider":"fake-action-provider",
               "model":"fake-model", "rank":1, "confidence":.9, "score_type":"confidence",
               "user_confirmed":False, "ambiguity":{"status":"none","margin":None},
               "supporting_evidence_refs":[], "conflicting_evidence_refs":[], "conflict_status":"none"}
        data = analyze([Path("raw.mp4")], supplied_metadata={"duration":10},
                       providers=[FakeActionProvider(candidates=[raw])],
                       exercise_context=context("Row", "row_unspecified"))
        fused = [item for item in data["evidence"]["exercise_candidates"]
                 if item["source_type"] == "fused"]
        self.assertEqual(fused[0]["canonical_exercise_id"], "row_unspecified")
        self.assertEqual(fused[0]["conflict_status"], "retained")
        self.assertEqual(validate_document(data), [])

    def test_context_only_serializes_valid_candidate_and_no_repetitions(self):
        data = analyze([Path("raw.mp4")], supplied_metadata={"duration":10}, providers=[],
                       exercise_context=context())
        self.assertEqual(validate_document(data), [])
        self.assertTrue(data["evidence"]["exercise_candidates"])
        self.assertFalse(data.get("repetitions", []))

    def test_no_context_retains_phase_3_shape(self):
        data = analyze([Path("raw.mp4")], supplied_metadata={"duration":10}, providers=[])
        self.assertNotIn("exercise_candidates", data["evidence"])
        self.assertEqual(validate_document(data), [])

    def test_duplicate_rank_score_order_and_nonfinite_rejected(self):
        data = analyze([Path("raw.mp4")], supplied_metadata={"duration":10}, providers=[],
                       exercise_context=context())
        item = data["evidence"]["exercise_candidates"][0]
        duplicate = dict(item, id="duplicate", canonical_exercise_id="row_unspecified")
        data["evidence"]["exercise_candidates"].append(duplicate)
        self.assertTrue(any("duplicate rank" in x for x in validate_document(data)))
        data["evidence"]["exercise_candidates"].pop()
        item["confidence"] = float("nan")
        self.assertTrue(validate_document(data))

    def test_bad_taxonomy_evidence_and_bounds_rejected(self):
        data = analyze([Path("raw.mp4")], supplied_metadata={"duration":10}, providers=[],
                       exercise_context=context())
        item = data["evidence"]["exercise_candidates"][0]
        for key, value in [("taxonomy_version","999"),("supporting_evidence_refs",["missing"]),
                           ("end",11)]:
            old = item[key]
            item[key] = value
            self.assertTrue(validate_document(data), key)
            item[key] = old
