# 🎯 Scraplet: The Autonomous AI Assistant

> **Scraplet** is a powerful, terminal-based Personal AI assistant designed for speed, safety, and intelligence. Built with Python, it acts as your personal pair-programmer and assistant, capable of writing code, managing files, running terminal commands, searching the web, and communicating via Voice or Telegram!

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ What Scraplet Can Do

Scraplet is designed to be an autonomous problem solver and interactive assistant. Its key capabilities include:

*   **Autonomous Agent Mode**: Reasons through complex software engineering tasks, writes code, creates/modifies files, and iteratively runs shell commands to fix its own bugs.
*   **Voice Assistant**: Talk to Scraplet using your voice! Features built-in Speech-to-Text (STT) and Text-to-Speech (TTS) for hands-free interactions.
*   **Telegram Bot Integration**: Deploy Scraplet as a Telegram bot to access your personal AI assistant on the go.
*   **Web Scraping & Search**: Built-in support for searching the web (DuckDuckGo) and scraping dynamic web pages using Playwright and BeautifulSoup4.
*   **Document Processing**: Can read and generate Word documents (`.docx`) and PowerPoint presentations (`.pptx`).
*   **Secure Docker Sandbox**: Agent terminal executions (like running untested scripts or `pip install`) happen inside a persistent, isolated Docker container (`python:3.11-slim`), protecting your host machine.
*   **Persistent Short-Term Memory**: Uses ChromaDB vector storage to remember context, codebase files, and past actions across your session.
*   **Multi-Provider LLM Support**: Works with Local LLMs (via Ollama) for privacy and free inference, or OpenRouter for top-tier models (GPT-4o, Claude 3.5, Gemini 1.5).

---

## 🚀 Getting Started

### Prerequisites

*   **Python 3.11+**
*   **[Ollama](https://ollama.com/)** (Required if you want to run local models)
*   **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (Required for the Secure Agent Execution Sandbox)
*   **[FFmpeg](https://ffmpeg.org/)** (Required for Whisper Speech-to-Text). On Windows, you can install it via `winget install "FFmpeg (Essentials Build)"`

### 1. Installation

Clone the repository and install Scraplet as a local package:

```bash
git clone https://github.com/abhisheksssss/Scraplet.git
cd Scraplet
pip install -e .
```

### 2. Download Voice Models

To use the voice assistant capabilities, you must download the Kokoro TTS model and voices. Place them in the `src/models/` directory:

1. Create the models directory:
   ```bash
   mkdir -p src/models
   ```
2. Download [kokoro-v1.0.onnx](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx) and place it in `src/models/`.
3. Download [voices-v1.0.bin](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin) and place it in `src/models/`.

*(You can also use curl inside the `src/models/` folder: `curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx` and `curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin`)*

### 3. Wake Up (Configuration & Launch)

Scraplet features an interactive setup command. Run:

```bash
scraplet wakeup
```

This will guide you through:
1.  **Choosing your LLM Provider**: Select between a Local LLM (via Ollama) or the OpenRouter API.
2.  **Setting up Credentials**: Automatically saves your preferences and API keys to a `.env` file.
3.  **Choosing a Mode**: Select how you want to interact with Scraplet (CLI, Voice, or Telegram).

### 4. Usage & Modes

Once configured, you can launch Scraplet in various modes:

*   **Interactive CLI (`scraplet wakeup` -> CLI)**: Choose between Agent Mode (autonomous coding), Plan Mode (step-by-step execution), or Ask Mode (read-only questions).
*   **Direct CLI Commands**:
    *   `scraplet agent "your goal here"`: Instantly run the autonomous agent.
    *   `scraplet plan "your goal here"`: Generate a plan and execute it step-by-step.
    *   `scraplet ask "your question"`: Ask a read-only question about your codebase.
    *   `scraplet voice`: Launch the Voice Assistant directly.
    *   `scraplet telegram`: Start the Telegram Bot server.

**Example Prompts:**
> *"Write a python script that fetches the current weather in Tokyo, run it, and fix any errors until it works."*
> *"Create a 5-slide PowerPoint presentation about the history of Artificial Intelligence."*
> *"Search the web for the latest news on SpaceX and summarize it in a Word document."*

---

## 🏗️ Architecture & Security

*   **Approval Flow**: In CLI mode, no destructive actions or file modifications are executed without your explicit consent. Visual diffs are shown for review.
*   **Mid-Conversation Execution**: The agent executes scripts mid-conversation to verify they work, making it highly autonomous.
*   **Docker Fallback**: If Docker is unavailable, Scraplet will explicitly ask for permission before running commands on your local host machine.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
