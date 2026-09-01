from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import uuid4

from .capability import MediaProjectRepository
from .quality import assess_image_quality


@dataclass(frozen=True)
class PromptRevision:
    revision_id: str
    project_id: str
    prompt: str
    parent_revision_id: str | None
    source_spans: tuple[str, ...]


class ImagePromptWorkflow:
    """Build and revise prompts; provider execution is an explicit separate step."""

    def __init__(
        self, project_id: str, repository: MediaProjectRepository | None = None
    ) -> None:
        if not project_id.strip():
            raise ValueError("project_id must not be blank")
        self.project_id = project_id
        self._repository = repository
        self._revisions: list[PromptRevision] = []
        self._requests: list[dict[str, Any]] = []

    @property
    def revisions(self) -> tuple[PromptRevision, ...]:
        return tuple(self._revisions)

    @property
    def requests(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._requests)

    def create_prompt(self, scene: dict[str, Any], source_spans: list[str]) -> PromptRevision:
        prompt = self._compose(scene)
        return self._append(prompt, source_spans, None)

    def revise_prompt(self, revision_id: str, prompt: str) -> PromptRevision:
        parent = self._find(revision_id)
        if not prompt.strip():
            raise ValueError("prompt must not be blank")
        return self._append(prompt.strip(), list(parent.source_spans), parent.revision_id)

    def build_generation_request(self, revision_id: str) -> dict[str, Any]:
        revision = self._find(revision_id)
        request = {
            "schema": "image-generation-request/v1",
            "project_id": self.project_id,
            "prompt_revision_id": revision.revision_id,
            "prompt": revision.prompt,
            "source_spans": list(revision.source_spans),
            "request_id": f"img_{uuid4().hex}",
        }
        self._requests.append(request)
        if self._repository is not None:
            try:
                self._repository.append_generation_request(request)
            except Exception:
                self._requests.pop()
                raise
        return dict(request)

    def build_production_plan(self, scene: dict[str, Any], source_spans: list[str],
                              candidate_count: int = 3) -> dict[str, Any]:
        """Create a storyboard prompt, candidate batch, evaluation gate and final request."""
        if candidate_count < 1 or candidate_count > 8:
            raise ValueError("candidate_count must be between 1 and 8")
        revision = self.create_prompt(scene, source_spans)
        candidates = [self.build_generation_request(revision.revision_id)
                      for _ in range(candidate_count)]
        return {"schema": "image-production-plan/v1", "project_id": self.project_id,
                "prompt_revision_id": revision.revision_id, "candidates": candidates,
                "evaluation": {"stage": "quality_assessment", "required": True,
                                "criteria": ["story_alignment", "composition", "identity_consistency",
                                              "artifact_free"]},
                "final_request": None}

    def finalize_candidate(self, plan: dict[str, Any], candidate_request_id: str,
                           evaluation: dict[str, Any]) -> dict[str, Any]:
        """Accept a candidate only when the evaluation gate passes, then create a new revision."""
        candidates = {item["request_id"] for item in plan.get("candidates", [])}
        if candidate_request_id not in candidates:
            raise KeyError("candidate request is not part of this plan")
        gate = assess_image_quality(evaluation.get("metrics", evaluation))
        if not gate["passed"]:
            plan["evaluation"] = {**gate, "review": dict(evaluation)}
            raise ValueError("image quality gate did not pass")
        revision_id = plan.get("prompt_revision_id")
        revision = self._find(revision_id)
        final = self.build_generation_request(revision.revision_id)
        plan["evaluation"] = {**gate, "review": dict(evaluation)}
        plan["final_request"] = final
        return dict(final)

    def _append(self, prompt: str, spans: list[str], parent: str | None) -> PromptRevision:
        if not spans or any(not span.strip() for span in spans):
            raise ValueError("source_spans must contain at least one non-blank span")
        revision = PromptRevision(
            f"prompt_{sha256(f'{self.project_id}:{len(self._revisions)}'.encode()).hexdigest()[:16]}",
            self.project_id, prompt, parent, tuple(spans),
        )
        if self._repository is not None:
            self._repository.append_prompt_revision(
                {
                    "schema": "image-prompt-revision/v1",
                    "project_id": revision.project_id,
                    "revision_id": revision.revision_id,
                    "parent_revision_id": revision.parent_revision_id,
                    "prompt": revision.prompt,
                    "source_spans": list(revision.source_spans),
                }
            )
        self._revisions.append(revision)
        return revision

    def _find(self, revision_id: str) -> PromptRevision:
        for revision in self._revisions:
            if revision.revision_id == revision_id:
                return revision
        raise KeyError(f"unknown prompt revision: {revision_id}")

    @staticmethod
    def _compose(scene: dict[str, Any]) -> str:
        location = str(scene.get("location", "具体室内空间"))
        action = str(scene.get("action", "人物作出关键选择"))
        mood = str(scene.get("mood", "克制而有张力"))
        characters = str(scene.get("characters", "保持角色外观与既有设定一致"))
        framing = str(scene.get("framing", "中近景，主体清晰，竖屏 9:16"))
        lighting = str(scene.get("lighting", "符合场景时间的自然光"))
        continuity = str(scene.get("continuity", "服装、发型、道具位置与上一镜头连续"))
        negative = str(scene.get("negative", "无文字水印、无畸形手指、无多余人物、无闪烁"))
        return (f"竖屏短剧画面；地点：{location}；人物：{characters}；动作：{action}；"
                f"构图：{framing}；光线：{lighting}；氛围：{mood}；连续性：{continuity}；"
                f"负面约束：{negative}。")
