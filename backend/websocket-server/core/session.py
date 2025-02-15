"""
Session management for Gemini Multimodal Live Proxy Server
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import asyncio

@dataclass
class SessionState:
    """Tracks the state of a client session"""
    is_receiving_response: bool = False
    interrupted: bool = False
    current_tool_execution: Optional[asyncio.Task] = None
    current_audio_stream: Optional[Any] = None
    genai_session: Optional[Any] = None
    received_model_response: bool = False  # Track if we've received a model response in current turn

# Global session storage
active_sessions: Dict[str, SessionState] = {}

def create_session(session_id: str) -> SessionState:
    """Create and store a new session"""
    session = SessionState()
    active_sessions[session_id] = session
    return session

def get_session(session_id: str) -> Optional[SessionState]:
    """Get an existing session"""
    return active_sessions.get(session_id)

def remove_session(session_id: str) -> None:
    """Remove a session"""
    if session_id in active_sessions:
        del active_sessions[session_id] 