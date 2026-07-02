from google.adk.agents import Agent
from src.config import GEMINI_MODEL
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

# Shared memory of decisions the Director Agent made.
# The FOH agent can read this list to explain things to the user!
director_decision_log = []

async def get_director_decision_log() -> list:
    """Returns the history of camera cuts and PTZ adjustments made by the Director Agent."""
    return director_decision_log

async def log_director_decision(action: str, reason: str, target: str) -> str:
    """Logs a directing decision so that the FOH Agent and control room attendees can view it."""
    entry = {"action": action, "target": target, "reason": reason}
    director_decision_log.append(entry)
    # Maintain a cap of the last 15 decisions
    if len(director_decision_log) > 15:
        director_decision_log.pop(0)
    print(f"[Director Log] >>> {action} on {target} because {reason} <<<")
    return f"Logged: {action}"

def create_director_agent() -> Agent:
    """Creates and returns the Broadcast Director Agent using Google Cloud ADK."""
    
    tools = [
        shure_get_audio_levels,
        shure_get_web_frame,
        shure_set_speaker_focus,
        cuez_cut_to_source,
        cuez_adjust_camera,
        cuez_get_rundown,
        log_director_decision,
    ]
    
    instruction = (
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
    
    agent = Agent(
        name="BroadcastDirector",
        model=GEMINI_MODEL,
        instruction=instruction,
        tools=tools,
    )
    
    return agent
