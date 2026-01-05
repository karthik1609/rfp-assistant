import asyncio
import base64
import logging
import os
from typing import Optional

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


async def render_mermaid_to_png(
    mermaid_code: str,
    theme: str = "default",
    background_color: str = "white",
) -> Optional[bytes]:
    if not mermaid_code or not mermaid_code.strip():
        logger.warning("Empty Mermaid code provided")
        return None

    code = mermaid_code.strip()
    if code.startswith("```mermaid"):
        code = code[10:].strip()
    elif code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@peng-shawn/mermaid-mcp-server"],
        env={
            **os.environ,
            "CONTENT_IMAGE_SUPPORTED": "true",
            # Help Puppeteer/Playwright find Chromium
            "PUPPETEER_SKIP_CHROMIUM_DOWNLOAD": "true",
            "PUPPETEER_EXECUTABLE_PATH": "/usr/bin/chromium",
            "PLAYWRIGHT_BROWSERS_PATH": "/usr/bin",
            "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1",
        },
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                tool_names = {t.name for t in tools.tools}
                if "generate" not in tool_names:
                    logger.error(
                        f"'generate' tool not found. Available tools: {sorted(tool_names)}"
                    )
                    return None

                logger.debug(
                    f"Rendering Mermaid diagram via MCP (code length: {len(code)} chars)"
                )
                result = await session.call_tool(
                    "generate",
                    arguments={
                        "code": code,
                        "theme": theme,
                        "backgroundColor": background_color,
                        "outputFormat": "png",
                    },
                )

                png_bytes: Optional[bytes] = None

                for block in result.content:
                    if (
                        isinstance(block, types.ImageContent)
                        and (block.mimeType or "").lower() == "image/png"
                    ):
                        data = block.data
                        if isinstance(data, bytes):
                            png_bytes = data
                        else:
                            try:
                                png_bytes = base64.b64decode(data)
                            except Exception as e:
                                logger.error(f"Failed to decode base64 PNG data: {e}")
                                continue
                        break

                if png_bytes is None:
                    got = []
                    for b in result.content:
                        if isinstance(b, types.TextContent):
                            got.append(("text", b.text[:200]))
                        elif isinstance(b, types.ImageContent):
                            got.append(("image", b.mimeType))
                        else:
                            got.append((type(b).__name__, str(b)[:200]))
                    logger.error(f"No image/png returned from MCP server. Got: {got}")
                    return None

                logger.info(
                    f"Successfully rendered Mermaid diagram to PNG ({len(png_bytes)} bytes)"
                )
                return png_bytes

    except Exception as e:
        logger.exception(f"Failed to render Mermaid diagram via MCP: {e}")
        return None


def render_mermaid_to_png_sync(
    mermaid_code: str,
    theme: str = "default",
    background_color: str = "white",
) -> Optional[bytes]:
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures

            def run_in_thread():
                return asyncio.run(
                    render_mermaid_to_png(mermaid_code, theme, background_color)
                )

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=60)
        except RuntimeError:
            return asyncio.run(
                render_mermaid_to_png(mermaid_code, theme, background_color)
            )
    except Exception as e:
        logger.exception(f"Failed to render Mermaid diagram synchronously: {e}")
        return None
