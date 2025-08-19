import datetime
from zoneinfo import ZoneInfo
import os
import litellm
import ssl
from typing import AsyncIterable
import types

from adk.agent import LlmAgent
from adk.runner import Runner

from shure_audio_agent.tool.get_status import get_status
from shure_audio_agent.tool.set_microphone_channel_coverage import set_microphone_channel_coverage
from shure_audio_agent.tool.load_user_preset import load_user_preset
from shure_audio_agent.tool.set_eq_setting import set_eq_setting
from shure_audio_agent.tool.start_auto_positioning import start_auto_positioning
from shure_audio_agent.tool.steer_lobe import steer_lobe

litellm._turn_on_debug()


class ShureAudioAgent:
    def __init__(self):
        self._agent = self._build_agent()
        self._runner = Runner(self._agent)
        self._user_id = "default_user"

    def _build_agent(self) -> LlmAgent:
        return LlmAgent(
            model="azure/gpt-4o-2",
            name="ShureAudioAgent",
            description=(
                "Agent to answer questions and perform actions related to Shure Audio device settings, user presets, and microphone channel coverage via GraphQL. The agent always enforces and respects all argument constraints for every tool and action."
            ),
            instruction=(
                "Above all, before performing any action, you must examine and strictly respect all constraints for the arguments of each tool. You are a helpful agent who can answer user questions and perform actions about Shure Audio device user presets and microphone channel coverage using GraphQL queries and mutations. No need to include ID in your answer. Whenever you need to set something, you need to run get_status to obtain the state of the device needed. When asked to point microphone to somewhere, you need to run get_status to list all the possible location presets, and use set user preset to change to that location. When asked to pick up audio from a particular direction, use get_status and set microphone coverage area. For loading user presets, use the preset name as input. For setting EQ, use set_eq_setting with the required arguments. For auto positioning, use start_auto_positioning with the required arguments. For lobe steering, use steer_lobe with the required arguments."
            ),
            tools=[
                get_status,  # Unified get tool for all device state
                set_microphone_channel_coverage,
                load_user_preset,  # Now expects preset_name (str) as input
                set_eq_setting,    # New tool for EQ settings
                start_auto_positioning,  # New tool for auto positioning
                steer_lobe,  # New tool for lobe steering
            ],
        )

    async def invoke(self, query: str, session_id: str) -> AsyncIterable[dict]:
        user_content = types.Content(role="user", parts=[types.Part.from_text(text=query)])

        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session_id,
            new_message=user_content
        ):
            if event.is_final_response():
                response_text = event.content.parts[-1].text if event.content and event.content.parts else ""
                yield {'is_task_complete': True, 'content': response_text}
            else:
                yield {'is_task_complete': False, 'updates': "Processing Shure Audio request..."}


def set_microphone_channel_coverage(reposition_id: str, coordinates: dict) -> dict:
    pass
