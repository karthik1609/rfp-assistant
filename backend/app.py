from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.pipeline.text_extraction import extract_text_from_file
from backend.pipeline.rfp_pipeline import run_rfp_pipeline


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


app = FastAPI(title="RFP Assistant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    index_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.post("/process-rfp")
async def process_rfp(file: UploadFile = File(...)) -> Dict[str, Any]:
    request_id = str(uuid.uuid4())
    logger.info("REQUEST %s: /process-rfp file=%s", request_id, file.filename)

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".doc"}:
        logger.warning("REQUEST %s: unsupported file type %s", request_id, suffix)
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a PDF or DOCX/DOC file.",
        )

    temp_path = Path("/tmp") / f"{request_id}_{file.filename}"
    content = await file.read()
    temp_path.write_bytes(content)
    logger.info(
        "REQUEST %s: wrote temp file %s (%d bytes)",
        request_id,
        temp_path,
        len(content),
    )

    t0 = time.time()
    try:
        text = extract_text_from_file(temp_path)
        logger.info(
            "REQUEST %s: extracted %d characters of text", request_id, len(text)
        )
    finally:
        try:
            temp_path.unlink(missing_ok=True)
            logger.debug("REQUEST %s: removed temp file %s", request_id, temp_path)
        except Exception:
            logger.exception(
                "REQUEST %s: failed to remove temp file %s", request_id, temp_path
            )

    if not text.strip():
        logger.warning("REQUEST %s: no text extracted from file", request_id)
        raise HTTPException(status_code=400, detail="No text could be extracted from file.")

    try:
        pipeline_output = run_rfp_pipeline(text, request_id=request_id)
    except Exception as exc:
        elapsed = time.time() - t0
        logger.exception(
            "REQUEST %s: pipeline failed after %.2fs: %s", request_id, elapsed, exc
        )
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed for request {request_id}. Check server logs.",
        ) from exc

    elapsed = time.time() - t0
    logger.info("REQUEST %s: pipeline completed in %.2fs", request_id, elapsed)

    # Include the raw OCR text from Qwen in the response so the frontend can display it.
    response = pipeline_output.to_dict()
    response["ocr_source_text"] = text
    return response


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok"}


