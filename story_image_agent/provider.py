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
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="456">'
               f'<rect width="100%" height="100%" fill="#20242c"/>'
               f'<text x="16" y="228" fill="white" font-size="14">mock:{digest}</text></svg>')
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return {"schema": "media-gateway-response/v1", "mime_type": "image/svg+xml",
                "content_base64": encoded, "provider": "mock", "model": "svg-deterministic",
                "cost_cny_fen": 0, "pricing_catalog_id": "mock-free-v1"}
