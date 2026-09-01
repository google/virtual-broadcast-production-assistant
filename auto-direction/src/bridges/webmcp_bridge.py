import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import random
import httpx

app = FastAPI(title="Browser-to-ADK WebMCP Bridge (Shure Simulator)")

# --- STATE ---
class ShureWebState:
    def __init__(self):
        # Simulated decibel audio levels for the mics
        self.audio_levels: Dict[str, float] = {"mic_host": -15.0, "mic_guest": -40.0}
        self.active_speaker: str = "mic_host"
        self.web_page_frame: str = "A podcast studio wide shot. Speaker A (Host) is gesturing happily. Speaker B (Guest) is nodding and smiling."

shure_state = ShureWebState()

# --- SCHEMAS ---
class AudioLevelUpdate(BaseModel):
    levels: Dict[str, float]
    active_speaker: str

# --- ENDPOINTS ---
@app.get("/audio")
async def get_audio_levels():
    # Add a bit of realistic jitter/dynamics to simulated audio levels
    shure_state.audio_levels["mic_host"] = round(random.uniform(-25.0, -5.0) if shure_state.active_speaker == "mic_host" else random.uniform(-60.0, -40.0), 1)
    shure_state.audio_levels["mic_guest"] = round(random.uniform(-25.0, -5.0) if shure_state.active_speaker == "mic_guest" else random.uniform(-60.0, -40.0), 1)
    return {
        "levels": shure_state.audio_levels,
        "active_speaker": shure_state.active_speaker,
    }

@app.post("/set-active-speaker")
async def set_active_speaker(speaker_id: str):
    if speaker_id not in ["mic_host", "mic_guest"]:
        raise HTTPException(status_code=400, detail="Invalid speaker ID")
    shure_state.active_speaker = speaker_id
    if speaker_id == "mic_host":
        shure_state.web_page_frame = "Close-up of Speaker A (Host) talking animatedly about Agentic workflows. Speaker B (Guest) is in the background listening."
    else:
        shure_state.web_page_frame = "Close-up of Speaker B (Guest) passionately describing how Norsk streaming works. Speaker A (Host) is smiling and taking notes."
    return {"status": "success", "active_speaker": shure_state.active_speaker}

@app.get("/browser-frame")
async def get_browser_frame():
    """Simulates capturing the active browser frame for Gemini 3.1 Flash's vision loop."""
    return {
        "frame_description": shure_state.web_page_frame,
        "browser_tab_title": "Shure Agentic Podcast Mixer",
        "url": "https://shure.web-mcp.studio/live"
    }

# --- CLIENT PYTHON FUNCTIONS FOR AGENT ---
# These functions will be imported by our Director Agent as tools.
import os
BASE_URL = os.getenv("SHURE_API_URL", "http://localhost:8001")

async def shure_get_audio_levels() -> dict:
    """Queries Shure's live audio level monitors and returns DB values and the current loudest speaker."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/audio")
        return r.json()

async def shure_set_speaker_focus(speaker_id: str) -> dict:
    """Tells the Shure WebMCP app to focus audio mixing on host or guest."""
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/set-active-speaker", params={"speaker_id": speaker_id})
        return r.json()

async def shure_get_web_frame() -> dict:
    """Captures the shared web page frame (screenshot simulation) and page metadata from Shure WebMCP tab."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/browser-frame")
        return r.json()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
