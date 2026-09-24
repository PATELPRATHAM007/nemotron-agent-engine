# ⚡ Nemotron Agent Engine (`nemotron-agent-engine`)

> **High-Performance Autonomous Agent Backend for NVIDIA Nemotron 3 Ultra (550B LatentMoE) & 1M-Token Context.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic)](https://docs.pydantic.dev/)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)

---

## 🌟 Overview

`nemotron-agent-engine` is an autonomous reasoning engine and tool orchestrator built to harness **NVIDIA Nemotron 3 Ultra (550B total / 55B active parameters)**.

It executes the autonomous loop:
$$\text{Plan} \longrightarrow \text{Reason} \longrightarrow \text{Call Tool} \longrightarrow \text{Observe} \longrightarrow \text{Self-Correct} \longrightarrow \text{Generate Output}$$

It streams internal reasoning thoughts, sandboxed terminal runs, and code diffs in real time via Server-Sent Events (SSE).

---

## 🚀 Key Features

* **🧠 Dual-Engine Routing**:
  - **Primary**: NVIDIA Nemotron 3 Ultra via vLLM / NVIDIA NIM OpenAI-compatible endpoint with inference-time reasoning flags.
  - **Tier-1 Fast Filter**: Jio Gemini (Gemini 2.5 Flash / 1.5 Pro) for zero-cost rapid parsing and preprocessing.
* **🛠️ Sandboxed Tool Registry**:
  - `execute_bash`: Subprocess runner with timeout, stdout/stderr capture, and safety controls.
  - `read_file` / `write_file`: File operations with automatic unified git diff generation.
  - `list_directory`: Workspace filesystem inspection.
* **📡 Real-Time SSE Streaming**: Emits live `thought`, `token`, `tool_start`, and `tool_observation` events directly to the frontend.
* **☁️ Cloud & Checkpoint Ops (`infra/`)**:
  - `download_nemotron_to_gdrive.py`: Zero-local-disk cloud-to-drive streamer for 1.12 TB BF16 weights.
  - `setup_gdrive_rclone.sh`: Fast streaming from 4TB Google Drive to GCP Ephemeral Local NVMe RAID array.
  - `idle-watchdog.sh`: 5-minute inactivity watchdog daemon to halt GCP Spot GPU instances and protect cloud credits.

---

## 🛠️ Quickstart

### 1. Installation
```bash
git clone https://github.com/your-username/nemotron-agent-engine.git
cd nemotron-agent-engine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your endpoints:
```env
# Nemotron vLLM or NIM Endpoint
NEMOTRON_API_BASE=http://localhost:8000/v1
NEMOTRON_API_KEY=EMPTY
NEMOTRON_MODEL_NAME=nvidia/Nemotron-3-Ultra

# Optional: Jio Gemini Tier-1 Scraper ($0 cost)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** to inspect the interactive Swagger API documentation.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/agent/run` | Registers a new autonomous mission. |
| `GET` | `/api/v1/agent/stream/{id}?goal=...` | Server-Sent Events (SSE) live stream of thoughts, tools, and diffs. |
| `GET` | `/api/v1/agent/config` | Returns active runtime model configuration. |
| `GET` | `/health` | Kubernetes / Cloud Run readiness and liveness health probe. |

---

## 📁 Project Structure

```
nemotron-agent-engine/
├── app/
│   ├── agent/                 # Autonomous agent engine loop
│   ├── api/v1/endpoints/      # REST & SSE endpoints
│   ├── core/                  # LLM Gateway, config, logging
│   └── tools/                 # Terminal, filesystem, and tool registry
├── infra/                     # 1.12TB Drive downloader & GCP auto-shutdown
├── requirements.txt
└── Dockerfile
```

---

## 📜 License

Licensed under the [Apache 2.0 License](LICENSE).
