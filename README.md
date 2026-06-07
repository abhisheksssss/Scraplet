# 🎯 Scraplet: The Autonomous AI Coding Assistant

> **Scraplet** is a powerful, terminal-based Personal AI assistant designed for speed, safety, and intelligence. Built with Python and FastAPI, it acts as your personal pair-programmer, capable of writing code, managing files, and iteratively running terminal commands to solve complex software engineering tasks autonomously.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ Key Features

*   **Autonomous Agent Mode**: An interactive terminal agent that can reason through problems, write code, create/modify files, and run shell commands iteratively.
*   **Iterative Execution Loop**: The agent writes code, asks for your approval, runs it, reads the `stdout` results, and fixes its own bugs automatically in a single fluid conversation turn.
*   **Secure Docker Sandbox**: All agent shell executions (like `pip install` or running untested scripts) happen inside a persistent, isolated Docker container (`python:3.11-slim`), protecting your host OS from malicious code or accidental system damage.
*   **Multi-Provider LLM Support**:
    *   **Local LLMs**: Seamless out-of-the-box integration with Ollama (Qwen, Llama 3, Mistral, etc.) for completely free and private inference.
    *   **OpenRouter**: Access to top-tier commercial models (GPT-4o, Claude 3.5, Gemini 1.5).
*   **Persistent Short-Term Memory**: Utilizes ChromaDB vector storage to remember context, codebase files, and actions across your current session.

---

## 🚀 Getting Started

### Prerequisites

*   Python 3.11+
*   [Ollama](https://ollama.com/) (Required if using Local LLMs)
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Required for the Agent Execution Sandbox)

### 1. Installation

Clone the repository and install the package:
```bash
git clone https://github.com/abhisheksssss/Scraplet.git
cd Scraplet
pip install -e .
```

### 2. Wake Up (Configuration)

Before using Scraplet, you must configure your AI providers and environment. 

```bash
scraplet wakeup
```

Follow the interactive rich-text prompts to:
1.  Choose your LLM provider (Local or OpenRouter).
2.  Select **Agent Mode**.

### 3. Usage

Run `scraplet wakeup` and enter **Agent Mode**. You can then prompt the agent with natural language to perform coding tasks!

Example Prompts:
> *"Write a python script that fetches the current weather in Tokyo, run it, and fix any errors until it works."*
> *"Refactor my orchestrator.py file to support mid-conversation execution."*

---

## 🏗️ Architecture & Security

Scraplet is built to be robust and incredibly secure:

*   **Approval Flow**: No destructive actions or file modifications are ever executed without explicit user consent. You will be prompted to review visual diffs before any changes hit your disk.
*   **Mid-Conversation Execution**: The agent doesn't just write scripts and stop. It actively executes them mid-conversation to verify they work, making it highly autonomous.
*   **Docker Fallback**: If the Docker daemon is unavailable, Scraplet pauses and asks for explicit permission before dangerously falling back to executing code on your local host machine.

---

## 🤝 Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📚 Project Structure

* **Root Directory**: Configuration and core dependencies (`.env`, `pyproject.toml`).
* **Source Code (`src/`)**:
    * `agent/`: Core LLM orchestration, Docker execution sandbox, and approval flows.
    * `memory/`: ChromaDB vector database integration for context retention.
    * `ui/`: Rich CLI interfaces and `wakeup` routines.
    * `plan/` & `ask/`: Feature-specific logic modules.
* **Data Storage (`.scraplet/`)**: Ephemeral vector embeddings and history tracking.