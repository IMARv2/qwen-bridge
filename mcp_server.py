#!/usr/bin/env python3
"""
Ollama MCP Server — exposes Qwen/Ollama as Claude Code tools.

Tools provided:
  ask_qwen(prompt, model?, system?)  — send a task to local Qwen, get response
  list_qwen_models()                 — list available models on Ollama
  qwen_task_log(limit?)              — show recent delegated task history

Configure in ~/.claude/settings.json:
  "mcpServers": {
    "ollama": {
      "command": "python3",
      "args": ["/home/imar/qwen-bridge/mcp_server.py"]
    }
  }
"""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, UTC
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_DEFAULT_MODEL", "qwen2.5:14b")
LOG_FILE = Path(__file__).parent / "task_log.jsonl"

app = Server("ollama-qwen")


def _ollama_post(path: str, payload: dict, timeout: int = 300) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _ollama_get(path: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(f"{OLLAMA_HOST}{path}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _ollama_ping(timeout: int = 3) -> bool:
    """Quick liveness check — returns True if Ollama is reachable."""
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _log(prompt: str, model: str, response: str, elapsed: float):
    entry = {
        "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "model": model,
        "prompt_chars": len(prompt),
        "response_chars": len(response),
        "elapsed_sec": round(elapsed, 2),
        "prompt_preview": prompt[:120].replace("\n", " "),
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="ask_qwen",
            description=(
                "Delegate a task to the local Qwen LLM (running via Ollama). "
                "Use this for code generation, boilerplate, documentation, refactoring suggestions, "
                "and other tasks that don't require Claude's full capabilities — to conserve API credits. "
                "Returns the model's response as text. "
                "IMPORTANT: If the response starts with '[QWEN_OFFLINE]', the second machine is powered off. "
                "In that case, handle the task yourself directly without retrying."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task or question to send to Qwen"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use. Options: qwen2.5:14b (best quality), qwen3.5:9b (fast), llama3.2:latest (smallest)",
                        "default": DEFAULT_MODEL
                    },
                    "system": {
                        "type": "string",
                        "description": "Optional system prompt to set context/role for the model",
                        "default": ""
                    }
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="list_qwen_models",
            description="List all available models on the local Ollama instance. Shows model names, sizes, and parameter counts.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="qwen_task_log",
            description="Show recent tasks that were delegated to Qwen via this bridge. Useful to review what has been offloaded.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent tasks to return (default: 10)",
                        "default": 10
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "ask_qwen":
        prompt = arguments.get("prompt", "").strip()
        model  = arguments.get("model", DEFAULT_MODEL)
        system = arguments.get("system", "")
        if not prompt:
            return [types.TextContent(type="text", text="Error: prompt is required")]

        # Quick ping before sending heavy request
        if not _ollama_ping():
            return [types.TextContent(type="text", text=(
                "[QWEN_OFFLINE] The Ollama host is not reachable. "
                "Ollama is down — either the machine is powered off or the service has stopped. "
                "Please handle this task yourself."
            ))]

        payload = {"model": model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system

        t0 = time.time()
        try:
            result = _ollama_post("/api/generate", payload, timeout=300)
        except urllib.error.URLError as e:
            return [types.TextContent(type="text", text=(
                f"[QWEN_OFFLINE] Lost connection to Ollama mid-request: {e}. "
                "Please handle this task yourself."
            ))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {e}")]

        elapsed = time.time() - t0
        response = result.get("response", "")
        _log(prompt, model, response, elapsed)

        output = f"[Qwen — {model} — {elapsed:.1f}s]\n\n{response}"
        return [types.TextContent(type="text", text=output)]

    elif name == "list_qwen_models":
        try:
            data = _ollama_get("/api/tags")
            models = data.get("models", [])
            if not models:
                return [types.TextContent(type="text", text="No models found on Ollama.")]
            lines = [f"Available models on {OLLAMA_HOST}:\n"]
            for m in models:
                size_gb = m["size"] / 1e9
                lines.append(f"  • {m['name']:30s}  {size_gb:.1f} GB  ({m['details']['parameter_size']})")
            return [types.TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: Cannot reach Ollama — {e}")]

    elif name == "qwen_task_log":
        limit = int(arguments.get("limit", 10))
        tasks = []
        try:
            with open(LOG_FILE) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        tasks.append(json.loads(line))
        except FileNotFoundError:
            return [types.TextContent(type="text", text="No tasks logged yet.")]

        tasks = tasks[-limit:][::-1]  # newest first
        if not tasks:
            return [types.TextContent(type="text", text="No tasks logged yet.")]

        lines = [f"Last {len(tasks)} delegated tasks:\n"]
        for t in tasks:
            lines.append(
                f"  [{t.get('ts','?')}] {t.get('model','?')} — "
                f"{t.get('elapsed_sec','?')}s — "
                f"{t.get('prompt_chars',0)}→{t.get('response_chars',0)} chars\n"
                f"    {t.get('prompt_preview','')}"
            )
        return [types.TextContent(type="text", text="\n".join(lines))]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
