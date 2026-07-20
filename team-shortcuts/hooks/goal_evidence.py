#!/usr/bin/env python3
"""Evidence checks for visual work tied to one active goal."""

from __future__ import annotations

from typing import Any


def validate_visual_evidence(value: dict[str, Any]) -> dict[str, Any]:
    if int(value.get("url_status") or 0) != 200:
        return {"ok": False, "code": "VISUAL_URL_NOT_READY"}
    if value.get("css_route_match") is not True:
        return {"ok": False, "code": "VISUAL_CSS_ROUTE_MISMATCH"}
    if not str(value.get("reference_image") or "").strip() or not str(
        value.get("actual_image") or ""
    ).strip():
        return {"ok": False, "code": "VISUAL_IMAGE_EVIDENCE_MISSING"}
    try:
        difference = float(value.get("visual_diff_percent"))
        threshold = float(value.get("visual_diff_threshold"))
    except (TypeError, ValueError):
        return {"ok": False, "code": "VISUAL_DIFF_MISSING"}
    if difference > threshold:
        return {
            "ok": False,
            "code": "VISUAL_REFERENCE_MISMATCH",
            "difference": difference,
            "threshold": threshold,
        }
    if value.get("data_complete") is not True:
        if value.get("structure_preserved") is not True or not value.get("missing_data"):
            return {"ok": False, "code": "VISUAL_MISSING_DATA_UNACCOUNTED"}
    build_port = str(value.get("build_port") or "")
    capture_port = str(value.get("capture_port") or "")
    if not build_port or not capture_port or build_port == capture_port:
        return {"ok": False, "code": "VISUAL_PORT_COLLISION"}
    if not str(value.get("current_page") or "").strip() or not str(
        value.get("next_prompt") or ""
    ).strip():
        return {"ok": False, "code": "VISUAL_HANDOFF_INCOMPLETE"}
    return {
        "ok": True,
        "code": "VISUAL_GOAL_EVIDENCE_OK",
        "difference": difference,
        "threshold": threshold,
    }
