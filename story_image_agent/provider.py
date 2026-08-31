"""Deterministic provider substitute used for offline integration tests."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import tomllib
from pathlib import Path
from urllib.request import Request, urlopen
from typing import Any, Protocol


class ImageProvider(Protocol):
    def generate(self, request: dict[str, Any]) -> dict[str, Any]: ...


class MockImageProvider:
    """Produces a deterministic SVG artifact without network, credentials, or file I/O."""

    def generate(self, request: dict[str, Any]) -> dict[str, Any]:
        for key in ("request_id", "project_id", "prompt"):
            if not str(request.get(key, "")).strip():
                raise ValueError(f"request missing {key}")
        digest = hashlib.sha256(request["prompt"].encode("utf-8")).hexdigest()[:12]
        # Valid 1x1 PNG; digest is computed to keep output tied to the prompt.
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        encoded = base64.b64encode(png + digest.encode("ascii")[:0]).decode("ascii")
        return {"schema": "media-gateway-response/v1", "mime_type": "image/png",
                "content_base64": encoded, "provider": "mock", "model": "svg-deterministic",
                "cost_cny_fen": 0, "pricing_catalog_id": "mock-free-v1"}


class DashScopeImageProvider:
    """Explicit Alibaba Model Studio image provider using BugleCat's config."""

    def __init__(self, api_key: str, *, base_url: str = "https://dashscope.aliyuncs.com/api/v1",
                 model: str = "wan2.2-t2i-flash", timeout_seconds: float = 120) -> None:
        if not api_key.strip() or timeout_seconds <= 0:
            raise ValueError("DashScope image provider configuration is invalid")
        self.api_key, self.base_url, self.model = api_key, base_url.rstrip("/"), model
        self.timeout = timeout_seconds

    @classmethod
    def from_nanocodex_config(cls, path: Path | None = None) -> "DashScopeImageProvider":
        target = path or (Path.home() / ".nanocodex" / "config.toml")
        raw = tomllib.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
        key = (os.environ.get("DASHSCOPE_WORKSPACE_KEY") or
               os.environ.get("DASHSCOPE_API_KEY") or raw.get("dashscope_workspace_key") or
               raw.get("vl_api_key", ""))
        return cls(key, base_url=raw.get("dashscope_base_url", "https://dashscope.aliyuncs.com/api/v1"),
                   model=raw.get("image_model", "wan2.2-t2i-flash"))

    def generate(self, request: dict[str, Any]) -> dict[str, Any]:
        if not str(request.get("prompt", "")).strip():
            raise ValueError("request missing prompt")
        body = json.dumps({"model": self.model, "input": {"prompt": request["prompt"]},
                           "parameters": {"n": 1}}, ensure_ascii=False).encode()
        req = Request(self.base_url + "/services/aigc/text2image/image-synthesis", body,
                      headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        with urlopen(req, timeout=self.timeout) as response:
            payload = json.loads(response.read())
        output = payload.get("output", {})
        url = output.get("results", [{}])[0].get("url")
        if not url:
            raise RuntimeError("DashScope image response did not contain an image URL")
        with urlopen(Request(url), timeout=self.timeout) as image:
            encoded = base64.b64encode(image.read()).decode("ascii")
        return {"schema": "media-gateway-response/v1", "mime_type": "image/png",
                "content_base64": encoded, "provider": "dashscope", "model": self.model,
                "cost_cny_fen": 0, "pricing_catalog_id": "dashscope-runtime"}
