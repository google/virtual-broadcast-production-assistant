# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Session management for Gemini Multimodal Live Proxy Server."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import asyncio


@dataclass
class SessionState:
  """Tracks the state of a client WebSocket session.

  Attributes:
    is_receiving_response: Flag indicating if the server is currently
      streaming a response to the client.
    interrupted: Flag indicating if the client requested an interruption.
    current_tool_execution: An asyncio Task handling the current tool call,
      if any.
    current_audio_stream: Reference to the current audio stream object, if any.
    genai_session: Reference to the underlying Gemini API session object.
    received_model_response: Tracks if a model response was received in the
      current interaction turn.
  """
  is_receiving_response: bool = False
  interrupted: bool = False
  current_tool_execution: Optional[asyncio.Task] = None
  current_audio_stream: Optional[Any] = None  # Consider more specific type
  genai_session: Optional[Any] = None  # Consider more specific type
  # Track if we've received a model response in current turn
  received_model_response: bool = False


# Global session storage (Consider alternatives if scaling/testing
# becomes complex)
active_sessions: Dict[str, SessionState] = {}


def create_session(session_id: str) -> SessionState:
  """Creates, stores, and returns a new session state for a given ID.

  Args:
    session_id: The unique identifier for the session.

  Returns:
    The newly created SessionState object.
  """
  session = SessionState()
  active_sessions[session_id] = session
  return session


def get_session(session_id: str) -> Optional[SessionState]:
  """Retrieves an existing session state by its ID.

  Args:
    session_id: The unique identifier for the session.

  Returns:
    The SessionState object if found, otherwise None.
  """
  return active_sessions.get(session_id)


def remove_session(session_id: str) -> None:
  """Removes a session state from the active sessions.

  Args:
    session_id: The unique identifier for the session to remove.
  """
  if session_id in active_sessions:
    del active_sessions[session_id]
