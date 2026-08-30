import json
import sys
import unittest
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).parents[1]))

from story_image_agent import ImagePromptWorkflow
from story_image_agent.quality import assess_image_quality


class ImageWorkflowTests(unittest.TestCase):
    def test_quality_evaluation_versions_failure_evidence_and_retry_stage(self):
        result = assess_image_quality({"story_alignment": 0.4})
        self.assertEqual(result["schema"], "image-quality-evaluation/v1")
        self.assertEqual(result["retry_stage"], "prompt_revision")
        failures = {item["metric"]: item for item in result["failures"]}
        self.assertEqual(failures["story_alignment"]["actual"], 0.4)
        self.assertEqual(failures["composition"]["reason"], "missing_or_invalid")

    def test_revision_and_regeneration_are_append_only(self):
        workflow = ImagePromptWorkflow("image-project-1")
        first = workflow.create_prompt({"location": "厨房", "action": "递出钥匙"}, ["scene:ep-1:sc-2"])
        second = workflow.revise_prompt(first.revision_id, "厨房夜景，母女隔桌对视，钥匙位于画面前景。")
        old_request = workflow.build_generation_request(first.revision_id)
        new_request = workflow.build_generation_request(second.revision_id)

        self.assertEqual(len(workflow.revisions), 2)
        self.assertEqual(len(workflow.requests), 2)
        self.assertNotEqual(old_request["request_id"], new_request["request_id"])
        self.assertEqual(second.parent_revision_id, first.revision_id)
        self.assertEqual(old_request["prompt_revision_id"], first.revision_id)
        self.assertEqual(new_request["prompt_revision_id"], second.revision_id)
        schema_path = Path(__file__).parents[1] / "contracts/media-agent/image-generation-request-v1.json"
        jsonschema.Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(new_request)

    def test_invalid_revision_and_source_fail_closed(self):
        workflow = ImagePromptWorkflow("image-project-1")
        with self.assertRaises(ValueError):
            workflow.create_prompt({}, [])
        with self.assertRaises(KeyError):
            workflow.build_generation_request("missing")

    def test_prompt_carries_identity_composition_continuity_and_negative_constraints(self):
        prompt = ImagePromptWorkflow("image-project-1").create_prompt(
            {"characters": "林夏，红色风衣", "framing": "低机位全景", "continuity": "钥匙在右手",
             "negative": "无文字，无多余手指"}, ["scene:1"]
        ).prompt
        for expected in ("林夏，红色风衣", "低机位全景", "钥匙在右手", "无文字，无多余手指"):
            self.assertIn(expected, prompt)

    def test_repository_receives_revision_before_request_and_failure_is_not_hidden(self):
        class RecordingRepository:
            def __init__(self):
                self.records = []
                self.fail_request = False

            def append_prompt_revision(self, revision):
                self.records.append(("revision", revision))

            def append_generation_request(self, request):
                if self.fail_request:
                    raise RuntimeError("durable store unavailable")
                self.records.append(("request", request))

        repository = RecordingRepository()
        workflow = ImagePromptWorkflow("image-project-1", repository)
        revision = workflow.create_prompt({"location": "厨房"}, ["scene:1"])
        workflow.build_generation_request(revision.revision_id)
        self.assertEqual([kind for kind, _ in repository.records], ["revision", "request"])
        repository.fail_request = True
        with self.assertRaisesRegex(RuntimeError, "durable store unavailable"):
            workflow.build_generation_request(revision.revision_id)
        self.assertEqual(len(workflow.requests), 1)

    def test_production_plan_requires_quality_before_final_generation(self):
        workflow = ImagePromptWorkflow("image-project-1")
        plan = workflow.build_production_plan(
            {"location": "天台", "action": "女主回头", "mood": "紧张"}, ["scene:2"], 3
        )
        self.assertEqual(len(plan["candidates"]), 3)
        self.assertIsNone(plan["final_request"])
        with self.assertRaises(ValueError):
            workflow.finalize_candidate(plan, plan["candidates"][0]["request_id"], {"passed": False})
        final = workflow.finalize_candidate(
            plan, plan["candidates"][1]["request_id"], {"story_alignment": .9,
            "composition": .9, "identity_consistency": .9, "artifact_free": .9}
        )
        self.assertEqual(final["prompt_revision_id"], plan["prompt_revision_id"])
        self.assertEqual(len(workflow.requests), 4)
        schema_path = Path(__file__).parents[1] / "contracts/media-agent/image-production-plan-v1.json"
        jsonschema.Draft202012Validator(
            json.loads(schema_path.read_text(encoding="utf-8"))
        ).validate(plan)

    def test_failed_quality_gate_records_deterministic_retry_stage(self):
        workflow = ImagePromptWorkflow("image-project-1")
        plan = workflow.build_production_plan({"location": "天台"}, ["scene:2"], 2)
        with self.assertRaises(ValueError):
            workflow.finalize_candidate(
                plan, plan["candidates"][0]["request_id"],
                {"story_alignment": .9, "composition": .9,
                 "identity_consistency": .5, "artifact_free": .9},
            )
        self.assertEqual(plan["evaluation"]["retry_stage"], "prompt_revision")
        self.assertFalse(plan["evaluation"]["passed"])
        self.assertEqual(plan["evaluation"]["schema"], "image-quality-evaluation/v1")
