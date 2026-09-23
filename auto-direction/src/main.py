import os
import sys
import threading
import time
import asyncio
import random
import uvicorn
from dotenv import load_dotenv
from google.adk.agents import Agent

# Add current folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import GEMINI_API_KEY, GEMINI_MODEL, has_adc, google_project_id
from src.bridges.cuez_automator_mcp import (
    app as cuez_app,
    state as cuez_state,
    cuez_get_rundown,
    cuez_set_segment,
    cuez_trigger_graphics,
)
from src.bridges.webmcp_bridge import app as shure_app, shure_state
from src.agents.foh_agent import create_foh_agent
from src.agents.director_agent import create_director_agent, director_decision_log, get_director_decision_log

# Import FastAPI packages for the FOH Web Server
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

# Global flag to control active production loop
live_production_active = False

# Initialize FastAPI app for FOH Web Server
foh_web_app = FastAPI(title="FOH Web Server")

foh_web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ControlAction(BaseModel):
    action: str

@foh_web_app.get("/api/status")
async def get_combined_status():
    return {
        "active_segment": cuez_state.active_segment,
        "camera_on_air": cuez_state.camera_on_air,
        "ptz_positions": cuez_state.ptz_positions,
        "audio_status": cuez_state.audio_status,
        "active_speaker": shure_state.active_speaker,
        "audio_levels": shure_state.audio_levels,
        "web_page_frame": shure_state.web_page_frame,
        "director_decision_log": director_decision_log,
        "live_production_active": live_production_active,
    }

@foh_web_app.post("/api/control")
async def control_show_dashboard(cmd: ControlAction):
    global live_production_active
    if cmd.action == "start":
        live_production_active = True
        cuez_state.active_segment = "Welcome and Chat"
        print("[System] >>> BROADCAST STARTED via Dashboard. <<<")
        return {"status": "success", "active_segment": cuez_state.active_segment}
    elif cmd.action == "stop":
        live_production_active = False
        print("[System] >>> BROADCAST STOPPED via Dashboard. <<<")
        return {"status": "success"}
    return {"status": "error", "message": "Invalid action"}

@foh_web_app.websocket("/api/ws")
async def websocket_proxy_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket Proxy]: Browser connected. Initializing Gemini Live Session...")
    
    # Initialize google-genai Client (uses API key if set, otherwise falls back to Application Default Credentials)
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
    else:
        client = genai.Client()
    
    # Map model ID to supported Live API model
    live_model = GEMINI_MODEL if GEMINI_MODEL else "gemini-2.0-flash-exp"
    
    system_instruction = (
        "You are 'FrontOfHouseHost', the voice-first welcoming assistant for our agentic video podcast booth. "
        "Your interface is presented as a hands-free voice terminal displaying an audio visualizer in Gemini colors. "
        "You converse with the user entirely using native audio. Keep your responses short, conversational, and "
        "professional, perfectly suited for a live voice-first experience."
    )
    
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        system_instruction=types.Content(parts=[types.Part.from_text(text=system_instruction)]),
        tools=[get_director_decision_log, cuez_get_rundown, cuez_set_segment, cuez_trigger_graphics]
    )
    
    try:
        async with client.aio.live.connect(model=live_model, config=config) as session:
            print("[WebSocket Proxy]: Gemini Live connection established.")
            
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
                    print(f"[WebSocket Proxy Client->Gemini Loop]: Stopped ({e})")
                    
            async def gemini_to_client_loop():
                try:
                    async for message in session.receive():
                        # 1. Handle Function Calls
                        if message.tool_call:
                            function_responses = []
                            for function_call in message.tool_call.function_calls:
                                name = function_call.name
                                args = function_call.args
                                call_id = function_call.id
                                
                                print(f"[WebSocket Proxy FOH Tool Call]: Executing {name} with args {args}")
                                try:
                                    if name == "get_director_decision_log":
                                        res = await get_director_decision_log()
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
                            
                        # 2. Handle Audio and Text Parts
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
                    print(f"[WebSocket Proxy Gemini->Client Loop]: Stopped ({e})")
            
            # Execute both loops concurrently
            await asyncio.gather(client_to_gemini_loop(), gemini_to_client_loop())
            
    except WebSocketDisconnect:
        print("[WebSocket Proxy]: Browser client disconnected.")
    except Exception as e:
        print(f"[WebSocket Proxy Main Error]: {e}")

# Mount static files under root after api paths
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
foh_web_app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


def run_cuez_server():
    """Runs Cuez Automator server in a separate thread."""
    uvicorn.run(cuez_app, host="127.0.0.1", port=8000, log_level="warning")

def run_shure_server():
    """Runs Shure WebMCP Bridge in a separate thread."""
    uvicorn.run(shure_app, host="127.0.0.1", port=8001, log_level="warning")

def run_foh_web_server():
    """Runs FOH Frontend Server on port 8002 in a separate thread."""
    uvicorn.run(foh_web_app, host="127.0.0.1", port=8002, log_level="warning")

def extract_text_from_events(events) -> str:
    """Helper to extract text from ADK runner events."""
    text = ""
    for event in events:
        if event.message and event.message.parts:
            for part in event.message.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
    return text

async def run_director_loop(director_runner) -> None:
    """
    Simulates the active production loop of the Director Agent using Gemini 3.1 Flash.
    It periodically gets mic levels and visual frames, sends them to the agent,
    and executes cuts/PTZ changes using the ADK Runner.
    """
    global live_production_active
    print("\n[System] Director Agent Loop Initialized.")
    
    while True:
        if live_production_active:
            try:
                # Simulate conversation switching to trigger cuts
                if random.random() < 0.35:
                    next_speaker = "mic_guest" if shure_state.active_speaker == "mic_host" else "mic_host"
                    shure_state.active_speaker = next_speaker
                    if next_speaker == "mic_host":
                        shure_state.web_page_frame = "Close-up of Speaker A (Host) presenting a slide. Speaker B (Guest) is nodding."
                    else:
                        shure_state.web_page_frame = "Close-up of Speaker B (Guest) gesturing at a diagram. Speaker A is listening."

                # Construct the sensory input for Gemini 3.1 Flash
                audio = shure_state.audio_levels
                active = shure_state.active_speaker
                frame = shure_state.web_page_frame
                current_segment = cuez_state.active_segment
                
                prompt = (
                    f"SENSORY UPDATE:\n"
                    f"- Active Segment: {current_segment}\n"
                    f"- On-Air Camera: {cuez_state.camera_on_air}\n"
                    f"- Audio Levels: Host={audio['mic_host']}dB, Guest={audio['mic_guest']}dB\n"
                    f"- Active Speaker: {active}\n"
                    f"- Current Web Page visual frame description: {frame}\n\n"
                    "Evaluate the scene. If you decide to cut cameras or adjust pan/tilt/zoom settings to follow the narrative, "
                    "use your tools to execute those. Make sure to call log_director_decision to record your reasoning!"
                )
                
                # Run the agent via the runner with a 15-second timeout to prevent blocking
                events = await asyncio.wait_for(
                    director_runner.run_debug(prompt, session_id="director_session"),
                    timeout=15.0
                )
                text = extract_text_from_events(events)
                if text.strip():
                    print(f"\n[Director Thoughts]: {text.strip()}\n")
            except asyncio.TimeoutError:
                print("[Director Error]: Agent response timed out (15s limit exceeded).")
            except Exception as e:
                print(f"[Director Error]: {e}")
                
        await asyncio.sleep(8)  # Check every 8 seconds

async def interactive_cli():
    global live_production_active
    
    # Check for authentication (API Key or Application Default Credentials)
    if not GEMINI_API_KEY and not has_adc:
        print("\n" + "="*80)
        print("ERROR: No valid authentication method found!")
        print("Please configure at least one of the following:")
        print("1. Set GEMINI_API_KEY in your environment or .env file.")
        print("2. Run 'gcloud auth application-default login' to use Application Default Credentials.")
        print("="*80 + "\n")
        return
        
    print("\n--- INITIALIZING BROADCAST DEMO ORCHESTRATOR ---")
    
    # Start mock servers in background threads
    cuez_thread = threading.Thread(target=run_cuez_server, daemon=True)
    shure_thread = threading.Thread(target=run_shure_server, daemon=True)
    foh_thread = threading.Thread(target=run_foh_web_server, daemon=True)
    cuez_thread.start()
    shure_thread.start()
    foh_thread.start()
    
    # Wait a moment for servers to start
    await asyncio.sleep(2)
    
    # Initialize ADK Agents & Runners
    print("[System] Initializing ADK Agents and Runners...")
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    foh_agent = create_foh_agent()
    foh_session_service = InMemorySessionService()
    foh_runner = Runner(
        app_name="FohApp",
        agent=foh_agent,
        session_service=foh_session_service,
    )

    director_agent = create_director_agent()
    director_session_service = InMemorySessionService()
    director_runner = Runner(
        app_name="DirectorApp",
        agent=director_agent,
        session_service=director_session_service,
    )
    
    # Start director background loop
    loop = asyncio.get_running_loop()
    loop.create_task(run_director_loop(director_runner))
    
    print("\n" + "="*60)
    print("Welcome to the Agentic Video Broadcast Booth!")
    print("Default Interface: Voice UI (Audio Visualizer Active in Gemini colors)")
    print("="*60)
    print("Type a message to talk to the Front of House (FOH) Agent.")
    print("Special Commands:")
    print("  'start show'  - Tells FOH to start the broadcast (activates Director Agent)")
    print("  'stop show'   - Tells FOH to stop the broadcast")
    print("  'status'      - View current Cuez Automator on-air and PTZ metrics")
    print("  'exit'        - Quit the session")
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input("\nAttendee: ").strip()
            if not user_input:
                continue
                
            if user_input.lower() == "exit":
                print("Exiting broadcast session. See you at the conference!")
                break
                
            elif user_input.lower() == "start show":
                live_production_active = True
                cuez_state.active_segment = "Welcome and Chat"
                print("\n[System] >>> BROADCAST STARTED. Director Agent active. <<<")
                events = await foh_runner.run_debug(
                    "The user just told you they are ready to start. Welcome them and announce that we are live!",
                    session_id="foh_session"
                )
                print(f"\nFOH (Host): {extract_text_from_events(events)}")
                
            elif user_input.lower() == "stop show":
                live_production_active = False
                print("\n[System] >>> BROADCAST STOPPED. Director Agent idle. <<<")
                events = await foh_runner.run_debug(
                    "The user has requested to stop the show. Thank them and cue out.",
                    session_id="foh_session"
                )
                print(f"\nFOH (Host): {extract_text_from_events(events)}")
                
            elif user_input.lower() == "status":
                print("\n" + "-"*40)
                print(f"CUEZ AUTOMATOR STATUS:")
                print(f"  Active Segment: {cuez_state.active_segment}")
                print(f"  Camera On-Air:  {cuez_state.camera_on_air.upper()}")
                print(f"  Active Mic:     {shure_state.active_speaker.upper()}")
                print(f"  PTZ Positions:")
                for cam, pos in cuez_state.ptz_positions.items():
                    print(f"    - {cam}: Pan={pos['pan']}, Tilt={pos['tilt']}, Zoom={pos['zoom']}")
                print(f"  Active Overlays: {cuez_state.overlays}")
                print(f"  Last 3 Director Cuts:")
                for dec in director_decision_log[-3:]:
                    print(f"    - Cut to {dec['target']} because: {dec['reason']}")
                print("-"*40)
                
            else:
                # Standard chat with FOH Agent
                # FOH is equipped with tools to query Cuez and the Director's log!
                events = await foh_runner.run_debug(user_input, session_id="foh_session")
                print(f"\nFOH (Host): {extract_text_from_events(events)}")
                
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

if __name__ == "__main__":
    asyncio.run(interactive_cli())
