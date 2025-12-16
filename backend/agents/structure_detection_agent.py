from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from backend.llm.client import chat_completion
from backend.models import RequirementItem
from backend.agents.prompts import STRUCTURE_DETECTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
STRUCTURE_DETECTION_MODEL = "gpt-5-chat"

def detect_structure(
    response_structure_requirements: List[RequirementItem],
) -> Dict[str, Any]:
    if not response_structure_requirements:
        logger.info("Structure detection: No response structure requirements found")
        return {
            "has_explicit_structure": False,
            "structure_type": "none",
            "detected_sections": [],
            "structure_description": "No response structure requirements found in RFP.",
            "confidence": 1.0,
        }
    
    # Combine all response structure requirements into a single text
    structure_text = "\n\n".join([
        f"[{req.type.upper()}] {req.normalized_text}\nSource: {req.source_text}"
        for req in response_structure_requirements
    ])
    
    user_prompt = f"""Analyze the following response structure requirements from an RFP:

{structure_text}

Determine if these requirements specify an EXPLICIT response structure with mandatory sections/chapters, or if they are just formatting/style guidelines.

Output JSON with:
- has_explicit_structure: boolean
- structure_type: "explicit" | "implicit" | "none"
- detected_sections: array of section names (if explicit, e.g., ["Executive Summary", "Technical Approach"])
- structure_description: string describing the structure
- confidence: float between 0.0 and 1.0
"""
    
    logger.info(
        "Structure detection: analyzing %d response structure requirements",
        len(response_structure_requirements),
    )
    
    try:
        content = chat_completion(
            model=STRUCTURE_DETECTION_MODEL,
            messages=[
                {"role": "system", "content": STRUCTURE_DETECTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=1000,
        )
        
        cleaned = content.replace("```json", "").replace("```", "").strip()
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                raise ValueError("Could not parse JSON from structure detection response")
        
        has_explicit = result.get("has_explicit_structure", False)
        structure_type = result.get("structure_type", "none")
        detected_sections = result.get("detected_sections", [])
        structure_description = result.get("structure_description", "")
        confidence = float(result.get("confidence", 0.5))
        
        if has_explicit and structure_type != "explicit":
            structure_type = "explicit"
        elif not has_explicit and structure_type == "explicit":
            has_explicit = False
            structure_type = "implicit" if detected_sections else "none"
        
        logger.info(
            "Structure detection: result - explicit=%s, type=%s, sections=%d, confidence=%.2f",
            has_explicit,
            structure_type,
            len(detected_sections),
            confidence,
        )
        
        return {
            "has_explicit_structure": has_explicit,
            "structure_type": structure_type,
            "detected_sections": detected_sections if isinstance(detected_sections, list) else [],
            "structure_description": structure_description or "No explicit structure detected.",
            "confidence": max(0.0, min(1.0, confidence)),
        }
        
    except Exception as e:
        logger.error("Structure detection failed: %s", e)
        logger.exception("Full traceback:")
        return {
            "has_explicit_structure": False,
            "structure_type": "none",
            "detected_sections": [],
            "structure_description": f"Structure detection failed: {str(e)}",
            "confidence": 0.0,
        }

