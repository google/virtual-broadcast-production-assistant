# Agentic Video Broadcast Studio — Front of House Voice Terminal & Director Orchestrator

An elite, ultra-low-latency, real-time agentic system that automates video podcast production, active speaker tracking, camera switching, and PTZ (Pan-Tilt-Zoom) coordinates. Built with **FastAPI**, **Uvicorn**, the **Google Cloud Agent Development Kit (ADK)**, and **Gemini 3.1 Flash Live** (via high-speed bidirectional WebSocket audio-to-audio streaming).

---

## 1. System Overview

This system coordinates two specialized AI agents to automate live podcast broadcasts in a conference booth terminal environment:

1. **Front of House (FOH) Host Agent**: The voice-first welcoming assistant. Attendees talk directly to the terminal using natural voice. The FOH Agent responds with an on-brand synthesized voice, answers questions, shows show rundown segments, and coordinates live updates on the glassmorphic terminal dashboard.
2. **Director Agent**: The autonomous live production orchestrator. It constantly receives sensory feeds (microphone dB audio levels, mock camera visual frame descriptions) and uses tools to trigger camera cuts (including mobile mounts like **Pixel 11**) and adjust PTZ presets in real time.

```
       ┌─────────────────────────────────────────────────────────────┐
       │                 FRONT OF HOUSE TERMINAL                     │
       │                                                             │
       │  ┌─────────────────────────┐     ┌───────────────────────┐  │
       │  │    Voice Visualizer     │     │   Telemetry Monitor   │  │
       │  │     (Gemini Colors)     │     │     (Live Video)      │  │
       │  └────────────┬────────────┘     └───────────▲───────────┘  │
       │               │ (PCM Stream)                 │ (Telemetry)  │
       └───────────────┼──────────────────────────────┼──────────────┘
                       │                              │
                       ▼                              │
       ┌──────────────────────────────────────────────┴──────────────┐
       │                   FASTAPI MIDDLEWARE & PROXY                │
       │                                                             │
       │               ┌──────────────────────────────┐              │
       │               │     Gemini Live WS Proxy     │              │
       │               └──────────────┬───────────────┘              │
       └──────────────────────────────┼──────────────────────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │  Gemini 3.1 Flash Live API   │
                       └──────────────────────────────┘
```

---

## 2. Architecture & Pipeline Flow

The system runs locally on three distinct ports to sandbox and mock device communication, with a fast WebSocket proxy acting as the low-latency bridge to Google Gemini.

```mermaid
graph TD
    subgraph Browser Terminal Client (Port 8002)
        Mic[User Microphone Input] -->|Captures Float32 stream| AudioCtx[Web Audio Context]
        AudioCtx -->|Decimation Downsampling| Down[16kHz Int16 PCM]
        Down -->|WebSocket binary stream| WSProxy[FastAPI WS Proxy: /api/ws]
        
        WSProxy -->|24kHz Int16 PCM bytes| Queue[Scheduled Playback Queue]
        Queue -->|Render audio| Speaker[Speakers / Headphones]
        Queue -.->|AnalyserNode| Waves[Gemini Colored Wave Visualizer]
        
        Dashboard[Glassmorphic Dashboard] -->|Continuous JSON Polling| StatusAPI[/api/status]
    end

    subgraph FastAPI Local Server (Port 8002)
        WSProxy <-->|google-genai Client| GeminiLive[Gemini Live API WebSocket]
        StatusAPI -->|Serves mock state| Dashboard
    end

    subgraph Mock Hardware Bridges
        Cuez[Cuez Automator Server: Port 8000] <-->|Rest State| StatusAPI
        Shure[Shure WebMCP Bridge: Port 8001] <-->|Rest State| StatusAPI
    end

    subgraph Agentic Orchestration Layer
        ADK[ADK Director Loop] -->|Polls levels & visual frames| Shure
        ADK -->|Gemini 3.1 Flash| Decisions[Cuts & Camera Controls]
        Decisions -->|Executes API calls| Cuez
    end
```

### Key Architectural Components

*   **Low-Latency WebSocket Proxy**: Bridges the user's browser directly to the Gemini Live API over WebSockets. It handles bidirectional streaming:
    *   **Upstream**: Browser captures microphone input (32-bit Float PCM), downsamples it to **16kHz 16-bit Mono Int16 PCM**, and streams binary chunks to the server.
    *   **Downstream**: Server receives **24kHz Mono Int16 PCM** from Gemini and pipes it to the browser.
*   **Audio Playback Queue Scheduler**: Prevents choppy or overlapping audio on the client. The browser queues incoming PCM chunks and schedules them sequentially on the Web Audio timeline using precise timestamps.
*   **Gemini Canvas Visualizer**: Uses an `AnalyserNode` to read frequency and time-domain data, rendering dynamic fluid waves in signature Google Gemini colors (blue, purple, pink, red).
*   **Hardware Mock Sandboxes**:
    *   **Cuez Automator (`:8000`)**: Simulates the production rundown and PTZ coordinates. Exposes REST tools for switching cameras and positioning PTZ mounts.
    *   **Shure WebMCP (`:8001`)**: Simulates active microphone volume meters and visual frames.

---

## 3. Developer Guide

Follow this guide to set up, configure, run, and test the project.

### Prerequisites

*   **Python 3.10+** (Tested on Python 3.14)
*   **Google Gemini API Key** (Fetch from [Google AI Studio](https://aistudio.google.com/app/api-keys))
*   A modern web browser with microphone access enabled for `http://127.0.0.1:8002`

### Setup & Installation

1.  **Clone the repository and enter the directory**:
    ```bash
    git clone https://github.com/google/virtual-broadcast-production-assistant.git
    cd virtual-broadcast-production-assistant/auto-direction
    ```

2.  **Activate the virtual environment**:
    ```bash
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the project root:
    ```env
    GEMINI_API_KEY="your_actual_gemini_api_key_here"
    ```

---

### Running the Orchestrator

Start the main orchestrator script:
```bash
python src/main.py
```

This launches the complete broadcast environment:
*   **Cuez Automator Mock Server** on `http://127.0.0.1:8000`
*   **Shure WebMCP Mock Bridge** on `http://127.0.0.1:8001`
*   **FOH Web Server & Dashboard** on `http://127.0.0.1:8002`
*   **ADK Director Agent loop** (Active background orchestrator checking sensory state every 8 seconds)
*   **Interactive CLI Console** for direct offline text-based testing

---

### Operating the Front of House Terminal

1.  Open your browser and navigate to `http://127.0.0.1:8002`.
2.  **Speak directly to the host**:
    *   Click the central **Microphone Button** to transition the state to `LISTENING`.
    *   Ask: *"Are you ready to start?"* or type it via the collapsible **Conversation History Drawer** (toggled by the keyboard icon).
3.  **Start the Show**:
    *   Click **START SHOW** on the dashboard or tell the voice assistant to *"start the show"*.
    *   The Director Agent loop will awaken. You will see cuts, camera coordinates, and speaker audio levels update dynamically on the dashboard and the scrollable terminal console in real-time.

---

## 4. Verification & Testing

### Automated Unit Tests

Run the full Python test suite to verify mocking, endpoints, and agent factory parameters:
```bash
.venv/bin/python -m unittest discover -s tests
```

### Mandatory Sub-Agent Quality Gates

Before merging any feature or pull request, you must execute the dual-agent review protocol outlined in `gemini.md`:

1.  **Test & Eval Engineer**: Verifies 100% mocked hardware coverage, test accuracy, PEP 8 structure, and async error isolation.
    *   *Command to run*: `.venv/bin/python -m unittest discover -s tests`
2.  **Security & Hardening Reviewer**: Assures strict bound validations for PTZ controls, sandboxed WebMCP connectivity, and zero API credential leaks.

> [!IMPORTANT]
> Both audits must report a **Pass** before any feature branch is merged into the main development branch.
