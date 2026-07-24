import os
import sys
import asyncio
import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

# Add current folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import GEMINI_API_KEY, GEMINI_MODEL, has_adc
from src.bridges.cuez_automator_mcp import (
    cuez_get_rundown,
    cuez_set_segment,
    cuez_trigger_graphics,
)

CUEZ_API_URL = os.getenv("CUEZ_API_URL", "http://127.0.0.1:8000")
SHURE_API_URL = os.getenv("SHURE_API_URL", "http://127.0.0.1:8001")
DIRECTOR_API_URL = os.getenv("DIRECTOR_API_URL", "http://127.0.0.1:8003")

app = FastAPI(title="FOH WebSocket Proxy & Frontend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ControlAction(BaseModel):
    action: str

# Overridden tool for FOH Agent to fetch from the networked director proxy
async def foh_get_director_decision_log() -> list:
    """Returns the history of camera cuts and PTZ adjustments made by the Director Agent."""
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{DIRECTOR_API_URL}/api/director-log")
            if r.status_code == 200:
                return r.json().get("director_decision_log", [])
        except Exception as e:
            print(f"[FOH Tool Error] Failed to fetch director log from {DIRECTOR_API_URL}: {e}")
        return []

@app.get("/api/config")
async def get_config():
    # Public URL of Director Proxy for the browser websocket client
    director_public_url = os.getenv("DIRECTOR_PUBLIC_URL", "http://127.0.0.1:8003")
    return {
        "director_ws_url": director_public_url
    }

@app.get("/api/status")
async def get_combined_status():
    async with httpx.AsyncClient() as client:
        try:
            # Gather states from bridges and director proxy
            cuez_task = client.get(f"{CUEZ_API_URL}/state")
            shure_audio_task = client.get(f"{SHURE_API_URL}/audio")
            shure_frame_task = client.get(f"{SHURE_API_URL}/browser-frame")
            director_task = client.get(f"{DIRECTOR_API_URL}/api/director-log")
            
            res_cuez, res_shure_audio, res_shure_frame, res_director = await asyncio.gather(
                cuez_task, shure_audio_task, shure_frame_task, director_task,
                return_exceptions=True
            )
            
            cuez_data = res_cuez.json() if not isinstance(res_cuez, Exception) and res_cuez.status_code == 200 else {}
            shure_audio = res_shure_audio.json() if not isinstance(res_shure_audio, Exception) and res_shure_audio.status_code == 200 else {}
            shure_frame = res_shure_frame.json() if not isinstance(res_shure_frame, Exception) and res_shure_frame.status_code == 200 else {}
            director_data = res_director.json() if not isinstance(res_director, Exception) and res_director.status_code == 200 else {}
            
            return {
                "active_segment": cuez_data.get("active_segment", "Intro Bumper"),
                "camera_on_air": cuez_data.get("camera_on_air", "cam_1"),
                "ptz_positions": cuez_data.get("ptz_positions", {}),
                "audio_status": cuez_data.get("audio_status", {}),
                "active_speaker": shure_audio.get("active_speaker", "mic_host"),
                "audio_levels": shure_audio.get("levels", {"mic_host": -60.0, "mic_guest": -60.0}),
                "web_page_frame": shure_frame.get("frame_description", "No active frame."),
                "director_decision_log": director_data.get("director_decision_log", []),
                "live_production_active": director_data.get("live_production_active", False),
            }
        except Exception as e:
            print(f"[FOH Proxy Status Error]: {e}")
            return {
                "active_segment": "Intro Bumper",
                "camera_on_air": "cam_1",
                "ptz_positions": {},
                "audio_status": {},
                "active_speaker": "mic_host",
                "audio_levels": {"mic_host": -60.0, "mic_guest": -60.0},
                "web_page_frame": "System connection offline.",
                "director_decision_log": [],
                "live_production_active": False,
            }

@app.post("/api/control")
async def control_show_dashboard(cmd: ControlAction):
    async with httpx.AsyncClient() as client:
        try:
            if cmd.action == "start":
                await client.post(f"{DIRECTOR_API_URL}/api/control", json={"action": "start"})
                await client.post(f"{CUEZ_API_URL}/set-segment", params={"segment_title": "Welcome and Chat"})
                print("[FOH Proxy] >>> BROADCAST STARTED. <<<")
                return {"status": "success"}
            elif cmd.action == "stop":
                await client.post(f"{DIRECTOR_API_URL}/api/control", json={"action": "stop"})
                print("[FOH Proxy] >>> BROADCAST STOPPED. <<<")
                return {"status": "success"}
        except Exception as e:
            print(f"[FOH Proxy Control Error]: {e}")
            return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "Invalid action"}

@app.websocket("/api/ws")
async def foh_websocket_proxy_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[FOH Proxy WS]: Browser connected. Initializing Gemini Live Session...")
    
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
    else:
        client = genai.Client()
        
    system_instruction = (
        "You are 'FrontOfHouseHost', the voice-first welcoming assistant for our agentic video podcast booth. "
        "Your interface is presented as a hands-free voice terminal displaying an audio visualizer in Gemini colors. "
        "You converse with the user entirely using native audio. Keep your responses short, conversational, and "
        "professional, perfectly suited for a live voice-first experience."
    )
    
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        system_instruction=types.Content(parts=[types.Part.from_text(text=system_instruction)]),
        tools=[foh_get_director_decision_log, cuez_get_rundown, cuez_set_segment, cuez_trigger_graphics]
    )
    
    try:
        async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
            print("[FOH Proxy WS]: Gemini Live connection established.")
            
            async def client_to_gemini_loop():
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            audio_chunk = data["bytes"]
                            await session.send_realtime_input(
                                media_chunks=[types.Blob(data=audio_chunk, mime_type="audio/pcm;rate=16000")]
                            )
                        elif "text" in data:
                            import json
                            payload = json.loads(data["text"])
                            if payload.get("type") == "text":
                                text_msg = payload.get("text", "")
                                await session.send(input=text_msg, end_of_turn=True)
                except Exception as e:
                    print(f"[FOH Proxy Client->Gemini Loop]: Stopped ({e})")
                    
            async def gemini_to_client_loop():
                try:
                    async for message in session.receive():
                        if message.tool_call:
                            function_responses = []
                            for function_call in message.tool_call.function_calls:
                                name = function_call.name
                                args = function_call.args
                                call_id = function_call.id
                                
                                print(f"[FOH Proxy WS Tool Call]: Executing {name} with args {args}")
                                try:
                                    if name == "foh_get_director_decision_log" or name == "get_director_decision_log":
                                        res = await foh_get_director_decision_log()
                                    elif name == "cuez_get_rundown":
                                        res = await cuez_get_rundown()
                                    elif name == "cuez_set_segment":
                                        res = await cuez_set_segment(**args)
                                    elif name == "cuez_trigger_graphics":
                                        res = await cuez_trigger_graphics(**args)
                                    else:
                                        res = {"error": "Unknown function"}
                                except Exception as err:
                                    res = {"error": str(err)}
                                    
                                function_responses.append({
                                    "name": name,
                                    "response": {"result": res},
                                    "id": call_id,
                                })
                            await session.send_tool_response(function_responses=function_responses)
                            
                        elif message.server_content and message.server_content.model_turn:
                            text_transcript = ""
                            for part in message.server_content.model_turn.parts:
                                if part.text:
                                    text_transcript += part.text
                                    
                            if text_transcript:
                                await websocket.send_json({
                                    "type": "text",
                                    "text": text_transcript
                                })
                                
                            for part in message.server_content.model_turn.parts:
                                if part.inline_data:
                                    audio_chunk = part.inline_data.data
                                    await websocket.send_bytes(audio_chunk)
                except Exception as e:
                    print(f"[FOH Proxy Gemini->Client Loop]: Stopped ({e})")
            
            await asyncio.gather(client_to_gemini_loop(), gemini_to_client_loop())
            
    except Exception as e:
        print(f"[FOH Proxy WS Main Error]: {e}")

static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    host = "0.0.0.0" if os.getenv("K_SERVICE") else "127.0.0.1"
    print(f"[FOH Proxy] Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
