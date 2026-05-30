# 🤖 Qwen Bridge: Claude + Local LLM Orchestration

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-Compatible-blueviolet?style=flat-square)
![Ollama](https://img.shields.io/badge/Ollama-Powered-black?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> [!NOTE]
> **PURPOSE:** A lightweight MCP (Model Context Protocol) server that connects Claude Code to a local Ollama instance — enabling a hybrid AI workflow where complex tasks are delegated to locally-hosted models to reduce cloud inference costs.

---

## 01 — 📖 Project Overview

**Qwen Bridge** acts as a transparent relay between Claude Code and a local Ollama server. It exposes MCP tools (`ask_qwen`, `list_qwen_models`, `qwen_task_log`) that Claude can call to delegate code generation, text analysis, and reasoning tasks to locally-hosted models — reducing reliance on cloud APIs for repetitive or bulk tasks.

The bridge also maintains a persistent task log for auditing delegated tasks and their outputs.

---

## 02 — ✨ Key Features

| Feature | Description |
| :--- | :--- |
| 🔌 **MCP Tool Server** | Exposes `ask_qwen`, `list_qwen_models`, and `qwen_task_log` as MCP tools |
| 🔀 **Multi-Model Routing** | Select the optimal model per task type — code, text, reasoning, multimodal |
| 📝 **Task Logging** | Persists all delegated tasks with timestamps, model used, and response to a JSONL log |
| ⚡ **Async HTTP** | Non-blocking requests to the Ollama API for fast response streaming |
| 🔁 **Transparent Fallback** | Returns `[QWEN_OFFLINE]` prefix when the server is unreachable |

---

## 03 — 🧠 Available Models (Benchmarked)

| Model | Size | Best For | Relative Speed |
| :--- | :---: | :--- | :---: |
| `qwen2.5-coder:14b` | 9 GB | Code, JS, Python, configs | Fast ✅ |
| `qwen2.5:14b` | 9 GB | Text, docs, summaries | Fast ✅ |
| `deepseek-r1:14b` | 9 GB | Reasoning, multi-step analysis | Fast ✅ |
| `gemma4:e4b` | 9.6 GB | Image / screenshot analysis | Medium |
| `qwen3-coder:latest` | 18.6 GB | High-accuracy code | Slow (CPU offload on most consumer GPUs) |

> [!TIP]
> `qwen2.5-coder:14b` is the recommended default for code tasks — at 9 GB it runs fully on-GPU for most consumer hardware, delivering the best speed/accuracy ratio for everyday workloads.

---

## 04 — 📁 Project Structure

```
qwen-bridge/
├── mcp_server.py    # MCP server — exposes tools to Claude Code
└── qwen_bridge.py   # Core HTTP client for Ollama API
```

---

## 05 — 🚀 Setup

> [!IMPORTANT]
> **Prerequisites:** A running [Ollama](https://ollama.ai) instance accessible on your network, and Claude Code with MCP support.

**1. Configure the Ollama host** in `qwen_bridge.py`:
```python
OLLAMA_HOST = "http://YOUR_OLLAMA_HOST:11434"
```

**2. Register the MCP server** in your Claude Code config (`~/.claude/settings.json`):
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

**3. Claude can now delegate tasks:**
```
ask_qwen(model="qwen2.5-coder:14b", prompt="Write a Python function that...")
```

---

## 06 — 🛠️ MCP Tools Reference

| Tool | Description |
| :--- | :--- |
| `ask_qwen` | Send a prompt to a specified Ollama model and return the response |
| `list_qwen_models` | List all models currently available on the Ollama server |
| `qwen_task_log` | View the last N entries from the task log |

---

## 07 — 🔄 Recommended Workflow

> [!NOTE]
> The hybrid workflow that gets the best results from Qwen Bridge:

1. **Plan** — Use Claude (or your preferred LLM) to design the architecture and gather full context from existing files.
2. **Generate** — Delegate boilerplate, CRUD code, templates, or documentation to Qwen Bridge.
3. **Review** — Verify field names, imports, and logic against your actual codebase before committing.

> [!CAUTION]
> Do not ask the local model to generate code that references existing project files without providing their full content in the prompt. Without context, local models will hallucinate field names, imports, and class structures.
