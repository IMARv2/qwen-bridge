# 🤖 Qwen Bridge: Claude + Local LLM Orchestration

> [!NOTE]
> **PURPOSE:** A lightweight MCP (Model Context Protocol) server that connects Claude Code to a local Ollama instance — enabling a hybrid AI workflow where complex tasks are delegated to local models to conserve Anthropic API credits.

---

## 01 - Project Overview

**Qwen Bridge** acts as a transparent relay between Claude Code and a local Ollama server running on the homelab network. It exposes an MCP tool (`ask_qwen`) that Claude can call to delegate code generation, text analysis, and reasoning tasks to locally-hosted models — avoiding unnecessary API credit consumption for repetitive or bulk tasks.

The bridge also maintains a persistent task log for auditing delegated tasks and their outputs.

---

## 02 - Key Features

* **MCP Tool Server:** Exposes `ask_qwen`, `list_qwen_models`, and `qwen_task_log` as MCP tools consumable by Claude Code.
* **Multi-Model Routing:** Supports model selection per task type — code, text, reasoning, multimodal.
* **Task Logging:** Persists all delegated tasks with timestamps, model used, and response to a JSONL log.
* **Async HTTP:** Non-blocking requests to the Ollama API for fast response streaming.
* **Transparent Fallback:** Returns `[QWEN_OFFLINE]` prefix when the Ollama server is unreachable, allowing Claude to handle the task itself.

---

## 03 - Available Models (Benchmarked)

| Model | Size | Best For | Speed |
| :--- | :--- | :--- | :--- |
| `qwen2.5-coder:14b` | 9GB | Code, JS, Python, configs | ~28s ✅ |
| `qwen2.5:14b` | 9GB | Text, docs, summaries | ~20s ✅ |
| `deepseek-r1:14b` | 9GB | Reasoning, multi-step analysis | ~15-25s ✅ |
| `gemma4:e4b` | 9.6GB | Image / screenshot analysis | ~47s |
| `qwen3-coder:latest` | 18.6GB | High-accuracy code (slower) | ~53s |

> [!TIP]
> `qwen2.5-coder:14b` is the default recommendation for code tasks — it fits fully in VRAM (RTX 3060 12GB) and delivers the best speed/accuracy ratio.

---

## 04 - Project Structure

```
qwen-bridge/
├── mcp_server.py    # MCP server — exposes tools to Claude Code
└── qwen_bridge.py   # Core HTTP client for Ollama API
```

---

## 05 - Setup

> [!IMPORTANT]
> **Prerequisites:** A running [Ollama](https://ollama.ai) instance accessible on your network, and Claude Code with MCP support.

1. **Configure the Ollama host** in `qwen_bridge.py`:
   ```python
   OLLAMA_HOST = "http://10.22.11.11:11434"
   ```

2. **Register the MCP server** in your Claude Code config (`~/.claude/settings.json`):
   ```json
   {
     "mcpServers": {
       "ollama": {
         "command": "python3",
         "args": ["/path/to/qwen-bridge/mcp_server.py"]
       }
     }
   }
   ```

3. **Claude can now delegate tasks:**
   ```
   ask_qwen(model="qwen2.5-coder:14b", prompt="Write a Python function that...")
   ```

---

## 06 - MCP Tools Reference

| Tool | Description |
| :--- | :--- |
| `ask_qwen` | Send a prompt to a specified Ollama model and return the response |
| `list_qwen_models` | List all models currently available on the Ollama server |
| `qwen_task_log` | View the last N entries from the task log |

---

## 07 - Workflow Pattern

> [!NOTE]
> The recommended hybrid workflow for Claude Code + Qwen Bridge:

1. **Claude** plans the architecture and reviews existing code for context.
2. **Qwen Bridge** generates boilerplate, CRUD code, templates, or documentation.
3. **Claude** reviews the output, corrects field names, and writes the final result to disk.

> [!CAUTION]
> Do not ask Qwen to generate code that references existing project files without providing full file content. Without context, local models will hallucinate field names, imports, and class structures.
