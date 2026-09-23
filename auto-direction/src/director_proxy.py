import os
import sys
import asyncio
import base64
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

# Add current folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import GEMINI_API_KEY, GEMINI_MODEL, has_adc
from src.bridges.webmcp_bridge import (
    shure_get_audio_levels,
    shure_get_web_frame,
    shure_set_speaker_focus,
)
from src.bridges.cuez_automator_mcp import (
    cuez_cut_to_source,
    cuez_adjust_camera,
    cuez_get_rundown,
)
from src.agents.director_agent import log_director_decision, director_decision_log

app = FastAPI(title="Director WebSocket Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global flag to control active production
live_production_active = False

class ControlAction(BaseModel):
    action: str

@app.get("/api/director-log")
async def get_director_log():
    return {
        "director_decision_log": director_decision_log,
        "live_production_active": live_production_active,
    }

@app.post("/api/control")
async def control_director(cmd: ControlAction):
    global live_production_active
    if cmd.action == "start":
        live_production_active = True
        print("[Director Proxy] >>> BROADCAST STARTED. <<<")
        return {"status": "success", "live_production_active": live_production_active}
    elif cmd.action == "stop":
        live_production_active = False
        print("[Director Proxy] >>> BROADCAST STOPPED. <<<")
        return {"status": "success", "live_production_active": live_production_active}
    raise HTTPException(status_code=400, detail="Invalid action")

@app.websocket("/api/ws/director")
async def director_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[Director Proxy WS]: Client connected. Initializing Gemini Live Session...")
    
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
    else:
        client = genai.Client()
        
    system_instruction = (
        "You are 'The Broadcast Director', an automated video podcast production agent. "
        "Your role is to orchestrate cameras and audio to produce a high-quality live podcast. "
        "You are equipped with tools to monitor Shure mic levels, watch the web page preview, "
        "and command Cuez Automator to cut cameras or adjust physical/virtual PTZ mounts. "
        "\n\n"
        "Guidelines:\n"
        "1. Check the audio levels periodically. If a speaker is talking loudly (-25dB to -5dB), "
        "ensure the camera is focused on them or cut to their feed (cam_2 for Host, pixel_11 for Guest).\n"
        "2. If both mics are active, cut to the wide studio camera (cam_1).\n"
        "3. Every time you make a change (e.g. cutting to a camera or panning/zooming a phone mount), "
        "you MUST call the 'log_director_decision' tool to record your reasoning (e.g. 'Cut to cam_2', 'Acoustic spike on host mic').\n"
        "This decision log is critical so that the Front of House agent can explain your actions to humans!\n"
        "4. Be dynamic. Do not let a single camera shot stay active for too long if the conversation shifts."
    )
    
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.TEXT],
        system_instruction=types.Content(parts=[types.Part.from_text(text=system_instruction)]),
        tools=[
            shure_get_audio_levels,
            shure_get_web_frame,
            shure_set_speaker_focus,
            cuez_cut_to_source,
            cuez_adjust_camera,
            cuez_get_rundown,
            log_director_decision,
        ]
    )
    
    try:
        async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
            print("[Director Proxy WS]: Gemini Live session established.")
            
            async def client_to_gemini():
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            if live_production_active:
                                audio_chunk = data["bytes"]
                                await session.send_realtime_input(
                                    media_chunks=[types.Blob(data=audio_chunk, mime_type="audio/pcm;rate=16000")]
                                )
                        elif "text" in data:
                            payload = json.loads(data["text"])
                            if payload.get("type") == "image" and live_production_active:
                                img_b64 = payload.get("data", "")
                                if img_b64:
                                    img_data = base64.b64decode(img_b64)
                                    await session.send_realtime_input(
                                        media_chunks=[types.Blob(data=img_data, mime_type="image/jpeg")]
                                    )
                except Exception as e:
                    print(f"[Director Proxy WS Client->Gemini]: Stopped ({e})")
                    
            async def gemini_to_client():
                try:
                    async for message in session.receive():
                        if message.tool_call:
                            function_responses = []
                            for function_call in message.tool_call.function_calls:
                                name = function_call.name
                                args = function_call.args
                                call_id = function_call.id
                                
                                print(f"[Director Proxy WS Tool Call]: Executing {name} with args {args}")
                                try:
                                    if name == "shure_get_audio_levels":
                                        res = await shure_get_audio_levels()
                                    elif name == "shure_get_web_frame":
                                        res = await shure_get_web_frame()
                                    elif name == "shure_set_speaker_focus":
                                        res = await shure_set_speaker_focus(**args)
                                    elif name == "cuez_cut_to_source":
                                        res = await cuez_cut_to_source(**args)
                                    elif name == "cuez_adjust_camera":
                                        res = await cuez_adjust_camera(**args)
                                    elif name == "cuez_get_rundown":
                                        res = await cuez_get_rundown()
                                    elif name == "log_director_decision":
                                        res = await log_director_decision(**args)
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
                            if text_transcript.strip():
                                print(f"[Director Thoughts]: {text_transcript.strip()}")
                                
                except Exception as e:
                    print(f"[Director Proxy WS Gemini->Client]: Stopped ({e})")
                    
            await asyncio.gather(client_to_gemini(), gemini_to_client())
            
    except WebSocketDisconnect:
        print("[Director Proxy WS]: Client disconnected.")
    except Exception as e:
        print(f"[Director Proxy WS Error]: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8003))
    host = "0.0.0.0" if os.getenv("K_SERVICE") else "127.0.0.1"
    print(f"[Director Proxy] Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
