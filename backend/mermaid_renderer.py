from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def find_mmdc() -> Optional[str]:
    env_path = os.environ.get("MERMAID_CLI_PATH")
    if env_path:
        if Path(env_path).exists():
            logger.info("MERMAID_CLI_PATH set and found: %s", env_path)
            return env_path
        resolved = shutil.which(env_path)
        if resolved:
            logger.info("Resolved MERMAID_CLI_PATH via PATH: %s", resolved)
            return resolved

    bin_path = shutil.which("mmdc")
    if bin_path:
        logger.info("Found mmdc on PATH: %s", bin_path)
    else:
        logger.info("mmdc not found on PATH")
    return bin_path


def render_mermaid_to_bytes(diagram: str, fmt: str = "png", timeout: int = 30) -> bytes:
    fmt = (fmt or "png").lower()
    if fmt not in ("png", "svg"):
        raise ValueError("fmt must be 'png' or 'svg'")

    mmdc = find_mmdc()
    if not mmdc:
        raise FileNotFoundError("mmdc (Mermaid CLI) not found. Install with: npm install -g @mermaid-js/mermaid-cli")

    logger.info("Rendering mermaid diagram to %s using mmdc", fmt)
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = Path(tmpdir) / "diagram.mmd"
        out_path = Path(tmpdir) / ("diagram." + fmt)

        in_path.write_text(diagram, encoding="utf-8")

        cmd = [mmdc, "-i", str(in_path), "-o", str(out_path)]

        try:
            euid = getattr(os, "geteuid", lambda: None)()
        except Exception:
            euid = None

        force_no_sandbox = os.environ.get("MERMAID_CLI_NO_SANDBOX", "").lower() in ("1", "true", "yes")

        needs_no_sandbox = force_no_sandbox or (euid is not None and euid == 0)

        puppeteer_cfg_path = None
        if needs_no_sandbox:
            logger.info("Mermaid rendering requested no-sandbox (root or MERMAID_CLI_NO_SANDBOX). Creating Puppeteer config file.")
            puppeteer_cfg_path = Path(tmpdir) / "puppeteer-config.json"
            puppeteer_cfg = {"args": ["--no-sandbox", "--disable-setuid-sandbox"]}
            puppeteer_cfg_path.write_text(json.dumps(puppeteer_cfg), encoding="utf-8")

        logger.debug("Running mmdc base command: %s", " ".join(cmd))


        def _run(cmd_to_run):
            try:
                p = subprocess.run(cmd_to_run, capture_output=True, check=False, timeout=timeout)
            except subprocess.TimeoutExpired as e:
                logger.exception("mmdc timed out: %s", e)
                raise RuntimeError(f"mmdc timed out after {timeout}s") from e
            out = p.stdout.decode("utf-8", errors="replace") if p.stdout else ""
            err = p.stderr.decode("utf-8", errors="replace") if p.stderr else ""
            return p.returncode, out, err

        if puppeteer_cfg_path:
            cmd_with_cfg = cmd + ["--puppeteerConfigFile", str(puppeteer_cfg_path)]
            returncode, stdout, stderr = _run(cmd_with_cfg)

            if returncode != 0 and ("unknown option" in (stderr or "").lower() or "unrecognized option" in (stderr or "").lower()):
                logger.info("mmdc did not recognize --puppeteerConfigFile; retrying with -p")
                cmd_with_cfg = cmd + ["-p", str(puppeteer_cfg_path)]
                returncode, stdout, stderr = _run(cmd_with_cfg)

            if returncode != 0 and euid is not None and euid == 0:
                logger.error("mmdc with Puppeteer config failed while running as root; not retrying without config to avoid Chromium launch failure.")
        else:
            returncode, stdout, stderr = _run(cmd)

        if returncode != 0:
            logger.error("mmdc failed (code=%s). stdout: %s stderr: %s", returncode, stdout[:200], stderr[:200])
            raise RuntimeError(f"mmdc rendering failed: {stderr or stdout}")
        else:
            logger.info("mmdc completed successfully; stdout: %s", stdout[:200])

        if not out_path.exists():
            raise RuntimeError("mmdc did not produce an output file")

        data = out_path.read_bytes()
        return data
