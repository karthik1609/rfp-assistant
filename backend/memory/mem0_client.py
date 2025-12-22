from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from mem0 import Memory  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Memory = None  # type: ignore[misc, assignment]

_MEM0_CLIENT: Optional["Memory"] = None


def _get_mem0_client() -> Optional["Memory"]:
    global _MEM0_CLIENT
    if _MEM0_CLIENT is not None:
        return _MEM0_CLIENT

    try:
        _MEM0_CLIENT = Memory()  # type: ignore[call-arg]
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to initialize Mem0 client: %s", exc)
        _MEM0_CLIENT = None
    return _MEM0_CLIENT


def _build_messages(preprocess_payload: Dict[str, Any]) -> list[Dict[str, str]]:
    summary = preprocess_payload.get("key_requirements_summary") or "RFP preprocess summary"
    cleaned_text = preprocess_payload.get("cleaned_text") or ""
    truncated_cleaned = cleaned_text[:4000]  # prevent oversized payloads

    payload_snapshot = {
        "key_requirements_summary": summary,
        "language": preprocess_payload.get("language"),
        "removed_text_length": len(preprocess_payload.get("removed_text") or ""),
        "cleaned_text_excerpt": truncated_cleaned,
    }

    return [
        {"role": "user", "content": summary},
        {"role": "assistant", "content": json.dumps(payload_snapshot)},
    ]


def _build_requirements_messages(requirements_payload: Dict[str, Any]) -> list[Dict[str, str]]:
    sol = requirements_payload.get("solution_requirements") or []
    resp = requirements_payload.get("response_structure_requirements") or []
    notes = requirements_payload.get("notes") or ""

    def _simplify(reqs: Any, max_items: int = 100) -> list[Dict[str, str]]:
        items: list[Dict[str, str]] = []
        if not isinstance(reqs, list):
            return items
        for raw in reqs[:max_items]:
            if not isinstance(raw, dict):
                continue
            text = str(raw.get("source_text") or "")
            items.append(
                {
                    "id": str(raw.get("id") or ""),
                    "type": str(raw.get("type") or ""),
                    "category": str(raw.get("category") or ""),
                    "source_text": text[:2000],
                }
            )
        return items

    snapshot = {
        "summary": "RFP requirements snapshot",
        "solution_requirements_count": len(sol) if isinstance(sol, list) else 0,
        "response_structure_requirements_count": len(resp) if isinstance(resp, list) else 0,
        "solution_requirements": _simplify(sol),
        "response_structure_requirements": _simplify(resp),
        "notes": str(notes),
    }

    return [
        {"role": "user", "content": "RFP REQUIREMENTS SNAPSHOT"},
        {"role": "assistant", "content": json.dumps(snapshot)},
    ]


def _build_build_query_messages(build_query_payload: Dict[str, Any]) -> list[Dict[str, str]]:
    query_text = str(build_query_payload.get("query_text") or "")
    sol_summary = str(build_query_payload.get("solution_requirements_summary") or "")
    resp_summary = str(build_query_payload.get("response_structure_requirements_summary") or "")

    snapshot = {
        "summary": "RFP build query snapshot",
        "solution_requirements_summary": sol_summary[:4000],
        "response_structure_requirements_summary": resp_summary[:4000],
        "query_preview": query_text[:8000],
    }

    return [
        {"role": "user", "content": "RFP BUILD QUERY SNAPSHOT"},
        {"role": "assistant", "content": json.dumps(snapshot)},
    ]


def store_preprocess_result(source_text: str, preprocess_payload: Dict[str, Any]) -> bool:
    if not source_text:
        logger.debug("No OCR text supplied; skipping Mem0 storage")
        return False

    client = _get_mem0_client()
    if client is None:
        return False

    try:
        user_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to hash OCR text for Mem0 storage: %s", exc)
        return False

    metadata = {
        "stage": "preprocess",
        "language": preprocess_payload.get("language"),
        "source": "rfp-assistant",
    }

    messages = _build_messages(preprocess_payload)

    try:
        # Local Mem0 Memory.add; keeps all data on this machine
        client.add(messages, user_id=user_hash, metadata=metadata)
        return True
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.warning("Mem0 write failed: %s", exc)
        return False


def store_requirements_result(source_text: str, requirements_payload: Dict[str, Any]) -> bool:
    if not source_text:
        logger.debug("No essential text supplied; skipping Mem0 requirements storage")
        return False

    client = _get_mem0_client()
    if client is None:
        return False

    try:
        user_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    except Exception as exc:
        logger.warning("Failed to hash essential text for Mem0 requirements storage: %s", exc)
        return False

    metadata = {
        "stage": "requirements",
        "source": "rfp-assistant",
    }

    messages = _build_requirements_messages(requirements_payload)

    try:
        client.add(messages, user_id=user_hash, metadata=metadata)
        return True
    except Exception as exc:
        logger.warning("Mem0 requirements write failed: %s", exc)
        return False


def store_build_query_result(source_text: str, build_query_payload: Dict[str, Any]) -> bool:
    if not source_text:
        logger.debug("No essential text supplied; skipping Mem0 build query storage")
        return False

    client = _get_mem0_client()
    if client is None:
        return False

    try:
        user_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    except Exception as exc:
        logger.warning("Failed to hash essential text for Mem0 build query storage: %s", exc)
        return False

    metadata = {
        "stage": "build_query",
        "source": "rfp-assistant",
    }

    messages = _build_build_query_messages(build_query_payload)

    try:
        client.add(messages, user_id=user_hash, metadata=metadata)
        return True
    except Exception as exc:
        logger.warning("Mem0 build query write failed: %s", exc)
        return False
