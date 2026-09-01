import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import httpx

app = FastAPI(title="Cuez Automator Simulator")

# --- STATE ---
class CuezState:
    def __init__(self):
        self.active_segment: str = "Intro Bumper"
        self.overlays: Dict[str, str] = {}
        self.camera_on_air: str = "cam_1"
        self.ptz_positions: Dict[str, Dict[str, float]] = {
            "cam_1": {"pan": 0.0, "tilt": 0.0, "zoom": 1.0},
            "cam_2": {"pan": 0.0, "tilt": 0.0, "zoom": 1.0},
            "pixel_11": {"pan": 0.0, "tilt": 0.0, "zoom": 1.0},
        }
        self.audio_status: Dict[str, Dict[str, float]] = {
            "mic_host": {"volume": 0.5, "active": True},
            "mic_guest": {"volume": 0.5, "active": True},
        }
        self.rundown: List[Dict[str, str]] = [
            {"id": "seg_1", "title": "Intro Bumper", "duration": "30s", "notes": "FOH starts, count down, then play intro package."},
            {"id": "seg_2", "title": "Welcome and Chat", "duration": "2m", "notes": "Host and Guest chat, camera transitions between wide and dual split."},
            {"id": "seg_3", "title": "Deep Dive & Tension", "duration": "2m", "notes": "Pick up conversation tension, do close-ups using Pixel 11 phone mount."},
            {"id": "seg_4", "title": "Wrap-up & Outro", "duration": "30s", "notes": "Wrap up and cue outro overlay graphics."},
        ]

state = CuezState()

# --- SCHEMAS ---
class GraphicOverlay(BaseModel):
    overlay_id: str
    text_title: str
    text_subtitle: str

class PTZCommand(BaseModel):
    camera_id: str
    pan: float = Field(..., ge=-180.0, le=180.0, description="Pan angle in degrees, must be between -180.0 and 180.0")
    tilt: float = Field(..., ge=-90.0, le=90.0, description="Tilt angle in degrees, must be between -90.0 and 90.0")
    zoom: float = Field(..., ge=1.0, le=20.0, description="Zoom factor, must be between 1.0 and 20.0")

# --- ENDPOINTS ---
@app.get("/state")
async def get_state():
    return {
        "active_segment": state.active_segment,
        "camera_on_air": state.camera_on_air,
        "ptz_positions": state.ptz_positions,
        "audio_status": state.audio_status,
    }

@app.get("/rundown")
async def get_rundown():
    return state.rundown

@app.post("/set-segment")
async def set_segment(segment_title: str):
    valid_titles = [seg["title"] for seg in state.rundown]
    if segment_title not in valid_titles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid segment title '{segment_title}'. Must be one of: {valid_titles}"
        )
    state.active_segment = segment_title
    return {"status": "success", "active_segment": state.active_segment}

@app.post("/trigger-graphics")
async def trigger_graphics(overlay: GraphicOverlay):
    state.overlays[overlay.overlay_id] = f"{overlay.text_title} - {overlay.text_subtitle}"
    return {"status": "success", "active_overlays": state.overlays}

@app.post("/cut-to-source")
async def cut_to_source(source_id: str):
    if source_id not in ["cam_1", "cam_2", "pixel_11"]:
        raise HTTPException(status_code=400, detail="Invalid camera source")
    state.camera_on_air = source_id
    print(f"[Cuez Automator HW] >>> ON AIR CUT TO: {source_id} <<<")
    return {"status": "success", "camera_on_air": state.camera_on_air}

@app.post("/ptz")
async def ptz_camera(cmd: PTZCommand):
    if cmd.camera_id not in state.ptz_positions:
        raise HTTPException(status_code=400, detail="Invalid camera ID")
        
    # Secure Parameter Validation (AppSec Protocol)
    if not (-180.0 <= cmd.pan <= 180.0):
        raise HTTPException(status_code=400, detail="Pan coordinate out of bounds [-180.0, 180.0]")
    if not (-90.0 <= cmd.tilt <= 90.0):
        raise HTTPException(status_code=400, detail="Tilt coordinate out of bounds [-90.0, 90.0]")
    if not (1.0 <= cmd.zoom <= 20.0):
        raise HTTPException(status_code=400, detail="Zoom level out of bounds [1.0, 20.0]")
        
    state.ptz_positions[cmd.camera_id] = {"pan": cmd.pan, "tilt": cmd.tilt, "zoom": cmd.zoom}
    print(f"[Cuez Automator HW] >>> ADJUST PTZ [{cmd.camera_id}] Pan={cmd.pan}, Tilt={cmd.tilt}, Zoom={cmd.zoom} <<<")
    return {"status": "success", "positions": state.ptz_positions[cmd.camera_id]}

# --- CLIENT PYTHON FUNCTIONS FOR AGENT ---
# These functions will be imported by our ADK Agent as tools.
import os
BASE_URL = os.getenv("CUEZ_API_URL", "http://localhost:8000")

async def cuez_get_rundown() -> List[dict]:
    """Retrieves the full script rundown of segments from Cuez Automator."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/rundown")
        return r.json()

async def cuez_set_segment(segment_title: str) -> dict:
    """Sets the active segment in the Cuez show flow."""
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/set-segment", params={"segment_title": segment_title})
        return r.json()

async def cuez_trigger_graphics(overlay_id: str, title: str, subtitle: str) -> dict:
    """Triggers and overlays lower-third text graphics on the screen via Cuez Automator."""
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/trigger-graphics", json={
            "overlay_id": overlay_id,
            "text_title": title,
            "text_subtitle": subtitle
        })
        return r.json()

async def cuez_cut_to_source(source_id: str) -> dict:
    """Cuts the live broadcast stream to the specified camera source (cam_1, cam_2, or pixel_11)."""
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/cut-to-source", params={"source_id": source_id})
        return r.json()

async def cuez_adjust_camera(camera_id: str, pan: float, tilt: float, zoom: float) -> dict:
    """Adjusts the Pan, Tilt, or Zoom parameters of a physical PTZ camera or Pixel 11 phone mount."""
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/ptz", json={
            "camera_id": camera_id,
            "pan": pan,
            "tilt": tilt,
            "zoom": zoom
        })
        return r.json()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
