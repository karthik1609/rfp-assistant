from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from backend.agents.extraction_agent import run_extraction_agent, ExtractionResult
from backend.agents.scope_agent import run_scope_agent, ScopeResult
from backend.agents.requirements_agent import (
    run_requirements_agent,
    RequirementsResult,
)


logger = logging.getLogger(__name__)


@dataclass
class RFPPipelineOutput:
    extraction: ExtractionResult
    scope: ScopeResult
    requirements: RequirementsResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "extraction": self.extraction.to_dict(),
            "scope": self.scope.to_dict(),
            "requirements": self.requirements.to_dict(),
        }


def run_rfp_pipeline(rfp_text: str, request_id: Optional[str] = None) -> RFPPipelineOutput:
    rid = request_id or "no-request-id"

    logger.info("REQUEST %s: step 1/3 – extraction agent", rid)
    extraction_res = run_extraction_agent(rfp_text)
    logger.info(
        "REQUEST %s: extraction complete (lang=%s, cpv=%d, other_codes=%d)",
        rid,
        extraction_res.language,
        len(extraction_res.cpv_codes),
        len(extraction_res.other_codes),
    )

    logger.info("REQUEST %s: step 2/3 – scope agent", rid)
    # Pass only the plain OCR text to the scope agent (no structured info)
    scope_res = run_scope_agent(translated_text=rfp_text)
    logger.info(
        "REQUEST %s: scope complete (essential_chars=%d, removed_chars=%d)",
        rid,
        len(scope_res.essential_text or ""),
        len(scope_res.removed_text or ""),
    )

    # NOTE (human-in-the-loop):
    # In a real application you would persist `scope_res` and present it to a user
    # who can approve or edit `scope_res.essential_text` before moving to the next step.
    # For now we assume automatic approval.

    logger.info("REQUEST %s: step 3/3 – requirements agent", rid)
    # Requirements agent only receives the scoped essential text (no structured info)
    requirements_res = run_requirements_agent(
        essential_text=scope_res.essential_text,
        structured_info={},
    )
    logger.info(
        "REQUEST %s: requirements complete (solution=%d, response_structure=%d)",
        rid,
        len(requirements_res.solution_requirements),
        len(requirements_res.response_structure_requirements),
    )

    return RFPPipelineOutput(
        extraction=extraction_res,
        scope=scope_res,
        requirements=requirements_res,
    )


