"""Deterministic provider substitute used for offline integration tests."""
from __future__ import annotations

import base64
import hashlib
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
