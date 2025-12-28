from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

from backend.llm.client import chat_completion
from backend.models import BuildQuery, ResponseResult
from backend.knowledge_base import FusionAIxKnowledgeBase
from backend.agents.prompts import RESPONSE_SYSTEM_PROMPT
from backend.memory.mem0_client import search_memories

logger = logging.getLogger(__name__)

RESPONSE_MODEL = "gpt-5-chat"

#function to run a clarity check on a requirement and return clarifying questions if needed
def _clarity_check(requirement_text: str, structure_text: Optional[str] = None) -> dict:
    if not requirement_text:
        return {"clarity": "unclear", "questions": ["Requirement text is empty"], "raw": ""}

    prompt_parts = [
        "You are an assistant whose job is ONLY to check clarity of an RFP requirement for the purpose of deciding whether to fetch additional local context.",
        "Do NOT attempt to answer the requirement or search for answers. Instead, analyze the provided requirement text and determine whether it is sufficiently clear to write a complete, detailed response.",
        "Respond with a JSON object only, with keys: `clarity` (either \"clear\" or \"unclear\"), `questions` (an array of concise clarifying questions if unclear, otherwise an empty array), and `explanation` (one-sentence rationale).",
        "Be brief and precise."
    ]
    prompt_parts.append("REQUIREMENT_TEXT:\n" + (requirement_text or ""))
    if structure_text:
        prompt_parts.append("RESPONSE_STRUCTURE_GUIDANCE:\n" + structure_text)

    user_prompt = "\n\n".join(prompt_parts)

    try:
        resp = chat_completion(
            model=RESPONSE_MODEL,
            messages=[
                {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=300,
        )
    except Exception as e:
        logger.warning("Clarity check LLM call failed: %s", e)
        return {"clarity": "unclear", "questions": [], "raw": ""}

    parsed = {"clarity": "unclear", "questions": [], "raw": resp}
    try:
        import json

        j = json.loads(resp)
        if isinstance(j, dict):
            clarity = j.get("clarity") or j.get("status") or "unclear"
            clarity = str(clarity).strip().lower()
            if clarity not in ("clear", "unclear"):
                if "yes" in clarity or "clear" in clarity:
                    clarity = "clear"
                else:
                    clarity = "unclear"
            questions = j.get("questions") or j.get("clarifying_questions") or []
            if isinstance(questions, str):
                questions = [questions]
            parsed = {"clarity": clarity, "questions": list(questions), "raw": resp}
            return parsed
    except Exception:
        pass

    low = (resp or "").lower()
    if any(k in low for k in ("unclear", "not clear", "need", "clarif", "missing", "ambigu")):
        qs = [l.strip() for l in resp.splitlines() if l.strip().endswith("?")][:6]
        parsed = {"clarity": "unclear", "questions": qs, "raw": resp}
    else:
        parsed = {"clarity": "clear", "questions": [], "raw": resp}

    return parsed


#function to generate a detailed response for a single build query using LLM
def run_response_agent(
    build_query: BuildQuery,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    knowledge_base: Optional[FusionAIxKnowledgeBase] = None,
    qa_context: Optional[str] = None,
) -> ResponseResult:
    if not build_query.confirmed:
        raise ValueError("Build query must be confirmed before generating response")

    logger.info(
        "Response agent: starting (query_length=%d)",
        len(build_query.query_text),
    )
    
    fusionaix_context = ""
    if knowledge_base is not None:
        try:
            requirement_text = build_query.solution_requirements_summary[:300]
            fusionaix_context = knowledge_base.format_for_prompt(requirement_text)
            if len(fusionaix_context) > 600:
                fusionaix_context = fusionaix_context[:600] + "..."
            logger.info("Included fusionAIx knowledge base context in prompt (%d chars)", len(fusionaix_context))
        except Exception as kb_exc:
            logger.warning("Failed to format knowledge base context: %s", kb_exc)
            fusionaix_context = ""

    req_summary = build_query.solution_requirements_summary
    struct_summary = build_query.response_structure_requirements_summary
    
    structure_detection = build_query.extraction_data.get("structure_detection")
    if structure_detection:
        is_implicit_structure = not structure_detection.get("has_explicit_structure", False)
        logger.info(
            "Using structure detection from extraction_data: has_explicit_structure=%s, type=%s",
            structure_detection.get("has_explicit_structure"),
            structure_detection.get("structure_type"),
        )
    else:
        struct_lower = (struct_summary or "").lower()
        explicit_keywords = [
            "executive summary", "technical approach", "implementation plan", 
            "project plan", "methodology", "solution overview", "company overview",
            "chapter", "part", "appendix"
        ]
        has_explicit_sections = any(keyword in struct_lower for keyword in explicit_keywords)
        
        is_implicit_structure = (
            not struct_summary or 
            struct_summary == "No response structure requirements found." or
            not has_explicit_sections
        )
        logger.info(
            "Detected structure from struct_summary: is_implicit=%s, has_explicit_sections=%s, summary_length=%d",
            is_implicit_structure,
            has_explicit_sections,
            len(struct_summary or ""),
        )
    
    if is_implicit_structure:
        target_chars_min = 200
        target_chars_max = 500
        target_words = "3-5 sentences"
        max_response_length = 500
    else:
        target_chars_min = 5000
        target_chars_max = 10000
        target_words = "800-1500"
        max_response_length = 10000

    retrieved_memories: List[Dict[str, Any]] = []
    retrieved_edit_memories: List[Dict[str, Any]] = []
    
    try:
        clarity = _clarity_check(req_summary or "", struct_summary or None)
        logger.info("Clarity check result: %s (questions=%d)", clarity.get("clarity"), len(clarity.get("questions") or []))
        logger.debug("Clarity check raw output: %s", (clarity.get("raw") or "")[:2000])
        if clarity.get("questions"):
            try:
                logger.info("Clarity check questions: %s", clarity.get("questions"))
            except Exception:
                logger.debug("Clarity questions logging failed")

        if clarity.get("clarity") == "unclear":
            try:
                retrieved_memories = search_memories(req_summary or "", max_results=3, stage="requirements")
                if retrieved_memories:
                    ids_scores = []
                    for m in retrieved_memories:
                        uid = (m.get("user_id") or "")[:12]
                        score = m.get("score") or 0.0
                        ids_scores.append(f"{uid}:{score:.3f}")
                    logger.info("Included %d local memory snippets in prompt due to clarity check (ids/scores=%s)", len(retrieved_memories), ",".join(ids_scores))
            except Exception as mem_exc:
                logger.warning("Local memory search failed: %s", mem_exc)
        else:
            logger.debug("Skipping local memory retrieval; requirement considered clear by LLM")
    except Exception as e:
        logger.warning("Clarity check failed, falling back to retrieving local memories: %s", e)
        try:
            retrieved_memories = search_memories(req_summary or "", max_results=3, stage="requirements")
            if retrieved_memories:
                logger.info("Included %d local memory snippets in prompt (fallback)", len(retrieved_memories))
        except Exception as mem_exc:
            logger.warning("Local memory search failed (fallback): %s", mem_exc)
    
    try:
        search_query = req_summary or build_query.query_text or ""
        if search_query:
            retrieved_edit_memories = search_memories(search_query, max_results=3, stage="edit_memory")
            if retrieved_edit_memories:
                ids_scores = []
                for m in retrieved_edit_memories:
                    uid = (m.get("user_id") or "")[:12]
                    score = m.get("score") or 0.0
                    ids_scores.append(f"{uid}:{score:.3f}")
                logger.info("Included %d edit memory snippets in prompt (ids/scores=%s)", len(retrieved_edit_memories), ",".join(ids_scores))
    except Exception as edit_mem_exc:
        logger.warning("Edit memory search failed: %s", edit_mem_exc)
    
    user_prompt_parts = [
        f"REQUIREMENT TO ADDRESS:",
        req_summary,
        "",
    ]
    
    if struct_summary and struct_summary != "No response structure requirements found.":
        user_prompt_parts.extend([
            "NOTE: Response structure requirements (formatting/style guidance only):",
            struct_summary,
            "These are for overall document formatting - do NOT add sections like 'Executive Summary' to individual requirement responses.",
            "",
        ])
    
    if fusionaix_context:
        user_prompt_parts.append(f"FUSIONAIX CONTEXT: {fusionaix_context}")
        user_prompt_parts.append("")

    if retrieved_memories:
        user_prompt_parts.extend([
            "=" * 80,
            "LOCAL MEMORY (mem0) - Relevant snippets (use as additional context):",
            "=" * 80,
        ])
        for mem in retrieved_memories:
            score = mem.get("score")
            snippet = mem.get("snippet") or ""
            messages = mem.get("messages") or []
            msg_content = "".join([str(m.get("content") or "") for m in messages[:2]])
            piece = snippet or (msg_content[:1000])
            user_prompt_parts.append(f"MEMORY (score={score:.3f}): {piece}")
            user_prompt_parts.append("")
    
    if retrieved_edit_memories:
        user_prompt_parts.extend([
            "=" * 80,
            "USER EDIT MEMORIES - Learn from past corrections (CRITICAL - apply these patterns):",
            "=" * 80,
        ])
        for mem in retrieved_edit_memories:
            score = mem.get("score")
            messages = mem.get("messages") or []
            msg_content = "".join([str(m.get("content") or "") for m in messages])
            try:
                import json
                content_str = str(messages[1].get("content", "") if len(messages) > 1 else "")
                if content_str:
                    edit_data = json.loads(content_str)
                    sentence_changes = edit_data.get("sentence_changes", [])
                    if sentence_changes:
                        user_prompt_parts.append(f"EDIT MEMORY (score={score:.3f}):")
                        user_prompt_parts.append("The user previously corrected these sentences:")
                        for sent_change in sentence_changes[:10]:
                            original = sent_change.get("original", "")
                            edited = sent_change.get("edited", "")
                            if original and edited:
                                user_prompt_parts.append(f"  Original: {original}")
                                user_prompt_parts.append(f"  Corrected: {edited}")
                                user_prompt_parts.append("")
                        user_prompt_parts.append("IMPORTANT: Apply similar corrections in your response. Pay attention to:")
                        user_prompt_parts.append("  - Capitalization of names, terms, and proper nouns")
                        user_prompt_parts.append("  - Specific terminology the user prefers")
                        user_prompt_parts.append("  - Content additions or modifications the user made")
                        user_prompt_parts.append("")
            except Exception:
                piece = msg_content[:1500]
                user_prompt_parts.append(f"EDIT MEMORY (score={score:.3f}): {piece}")
                user_prompt_parts.append("")
    
    if qa_context:
        user_prompt_parts.extend([
            "=" * 80,
            "USER-PROVIDED INFORMATION (CRITICAL - MUST USE FULL DETAILS):",
            "=" * 80,
            qa_context,
            "",
            "CRITICAL INSTRUCTIONS FOR USING Q&A INFORMATION:",
            "- The Q&A above contains SPECIFIC, DETAILED information that the user provided about their solution.",
            "- You MUST use the FULL, COMPLETE answers from the Q&A - do NOT summarize or condense them.",
            "- If a question asks about previous projects, use the FULL project details provided in the answer.",
            "- If a question asks about certifications, use the FULL list of certifications provided.",
            "- If a question asks about team structure, use the FULL team details provided.",
            "- If a question asks about capabilities, use the FULL capability descriptions provided.",
            "- Integrate the COMPLETE information naturally throughout your response - do NOT reduce it to one sentence.",
            "- The user provided detailed answers for a reason - they want those details in the response.",
            "- Match the depth and detail level of the Q&A answers in your response.",
            "",
        ])
    
    if is_implicit_structure:
        user_prompt_parts.extend([
            "TASK: Write a brief, direct response to the requirement above (approximately 5 sentences).",
            "",
            "YOUR RESPONSE SHOULD:",
            "1. Directly answer the requirement - be specific and concrete",
            "2. Use Q&A information if provided - include relevant details but keep it concise",
            "3. Reference fusionAIx capabilities where relevant - one brief example is sufficient",
            f"4. Be brief: Write approximately {target_words} ({target_chars_min}-{target_chars_max} characters total)",
            "",
            "DO NOT INCLUDE:",
            "- Long explanations or elaborations",
            "- Multiple examples or case studies",
            "- Section headers or formatting",
            "- Unnecessary background information",
            "",
            f"Write your brief response now ({target_chars_min}-{target_chars_max} characters, ~5 sentences):",
        ])
    else:
        user_prompt_parts.extend([
            "TASK: Write a comprehensive, detailed response to the requirement above.",
            "",
            "YOUR RESPONSE SHOULD:",
            "1. Show understanding: Briefly acknowledge what the requirement asks for",
            "2. Comprehensive answer: Provide a detailed, thorough response addressing ALL aspects of the requirement",
            "3. Use Q&A information FULLY: If Q&A context is provided above, use the COMPLETE, FULL answers - do not summarize them. If the user provided detailed project information, include those full details. If they provided a list of certifications, include the full list. Match the depth of detail provided in the Q&A.",
            "4. Be specific: Include concrete details, metrics, capabilities, and examples",
            "5. Be relevant: Use fusionAIx capabilities, case studies, or accelerators where applicable",
            "6. Be detailed: Write 800-1500 words (5000-10000 characters) - match the depth of the questions asked",
            "",
            "DO NOT INCLUDE:",
            "- Executive summaries",
            "- Solution overviews",
            "- Generic introductions or conclusions",
            "- Unnecessary section headers - just answer the requirement directly",
            "",
            "Write your comprehensive response now (detailed, 5000-10000 characters):",
        ])

    user_prompt = "\n".join(user_prompt_parts)
    
    system_tokens = len(RESPONSE_SYSTEM_PROMPT) // 4
    user_tokens = len(user_prompt) // 4
    total_input_tokens = system_tokens + user_tokens + 100
    logger.info(
        "Prompt tokens: system=%d, user=%d, total_input=%d",
        system_tokens,
        user_tokens,
        total_input_tokens,
    )

    if max_tokens is None:
        estimated_input_tokens = total_input_tokens
        if is_implicit_structure:
            max_tokens = min(200, 32769 - estimated_input_tokens - 1000)  # ~500 chars for 5 sentences
        else:
            max_tokens = min(2500, 32769 - estimated_input_tokens - 1000)  # ~10000 chars
        logger.info(
            "Response max_tokens set to %d (target: ~%d-%d characters, ~%s, structure=%s)",
            max_tokens,
            target_chars_min,
            target_chars_max,
            target_words,
            "implicit" if is_implicit_structure else "explicit",
        )

    logger.info(
        "Response agent: calling LLM (model=%s, temperature=%s, max_tokens=%s)",
        RESPONSE_MODEL,
        temperature,
        max_tokens,
    )

    response_text = chat_completion(
        model=RESPONSE_MODEL,
        messages=[
            {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    if len(response_text) > max_response_length:
        logger.warning(
            "Response too long (%d chars), truncating to %d chars",
            len(response_text),
            max_response_length,
        )
        truncated = response_text[:max_response_length]
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        cut_point = max(last_period, last_newline)
        if cut_point > max_response_length * 0.8:
            response_text = truncated[:cut_point + 1] + "\n\n[Response truncated for length]"
        else:
            response_text = truncated + "\n\n[Response truncated for length]"

    logger.info(
        "Response agent: finished (response_length=%d, max_allowed=%d, structure=%s)",
        len(response_text),
        max_response_length,
        "implicit" if is_implicit_structure else "explicit",
    )

    return ResponseResult(
        response_text=response_text,
        build_query_used=build_query.query_text,
        num_retrieved_chunks=len(retrieved_memories or []),
        notes="Generated response",
    )

