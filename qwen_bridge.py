#!/usr/bin/env python3
"""
Qwen Bridge — delegates tasks from Claude to local Ollama (10.22.11.11)
Usage:
  python3 qwen_bridge.py "your prompt here"
  python3 qwen_bridge.py "your prompt" --model qwen2.5:14b
  python3 qwen_bridge.py "your prompt" --system "you are a coding assistant"
  cat file.py | python3 qwen_bridge.py "review this code" --stdin
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

OLLAMA_HOST = "http://10.22.11.11:11434"
DEFAULT_MODEL = "qwen2.5:14b"
LOG_FILE = Path(__file__).parent / "task_log.jsonl"


def call_ollama(prompt: str, model: str, system: str = "") -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"[qwen-bridge] ERROR: Cannot reach Ollama — {e}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.time() - t0
    return result, elapsed


def log_task(prompt: str, model: str, response: str, elapsed: float):
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "model": model,
        "prompt_chars": len(prompt),
        "response_chars": len(response),
        "elapsed_sec": round(elapsed, 2),
        "prompt_preview": prompt[:120].replace("\n", " "),
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Delegate a task to local Qwen via Ollama")
    parser.add_argument("prompt", nargs="?", help="Prompt to send")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--system", default="", help="System prompt")
    parser.add_argument("--stdin", action="store_true", help="Append stdin to prompt")
    parser.add_argument("--no-log", action="store_true", help="Do not write to task log")
    parser.add_argument("--list-models", action="store_true", help="List available models and exit")
    args = parser.parse_args()

    if args.list_models:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            for m in data.get("models", []):
                size_gb = m["size"] / 1e9
                print(f"  {m['name']:30s}  {size_gb:.1f} GB  ({m['details']['parameter_size']})")
        except urllib.error.URLError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        return

    prompt = args.prompt or ""
    if args.stdin:
        stdin_data = sys.stdin.read()
        prompt = (prompt + "\n\n" + stdin_data).strip() if prompt else stdin_data

    if not prompt:
        parser.print_help()
        sys.exit(1)

    print(f"[qwen-bridge] Using model: {args.model}", file=sys.stderr)
    print(f"[qwen-bridge] Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}", file=sys.stderr)
    print("[qwen-bridge] Waiting for response...", file=sys.stderr)

    result, elapsed = call_ollama(prompt, args.model, args.system)
    response = result.get("response", "")

    if not args.no_log:
        log_task(prompt, args.model, response, elapsed)

    print(f"[qwen-bridge] Done in {elapsed:.1f}s", file=sys.stderr)
    print()
    print(response)


if __name__ == "__main__":
    main()
