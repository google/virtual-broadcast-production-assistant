"""
Shure Audio Control Agent

This agent provides control capabilities for Shure audio equipment in broadcast environments.
It uses Azure OpenAI for natural language understanding and Google ADK for agent framework.
"""

import os
from typing import Dict, Any, Optional
import logging
from google.adk.core import Agent, Tool
from google.adk.llm import BaseLanguageModel
from google.genai import types
import openai
from .audio_control import get_audio_controller
import json
import asyncio

logger = logging.getLogger(__name__)


class AzureOpenAIModel(BaseLanguageModel):
    """Azure OpenAI integration for Google ADK."""
    
    def __init__(self):
        self.client = openai.AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
    
    async def generate_content(self, prompt: str, **kwargs) -> types.GenerateContentResponse:
        """Generate content using Azure OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", 1000),
                temperature=kwargs.get("temperature", 0.7)
            )
            
            content = response.choices[0].message.content
            return types.GenerateContentResponse(
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=content)]
                )
            )
        except Exception as e:
            logger.error(f"Error generating content with Azure OpenAI: {e}")
            raise


class AudioControlTools:
    """Tools for controlling Shure audio equipment."""
    
    @staticmethod
    def get_channel_status_tool() -> Tool:
        """Tool to get status of audio channels."""
        async def get_channel_status(channel_id: Optional[int] = None) -> Dict[str, Any]:
            """Get status of audio channels.
            
            Args:
                channel_id: Specific channel ID to query (1-8), or None for all channels
            
            Returns:
                Dictionary containing channel status information
            """
            controller = get_audio_controller()
            
            if channel_id is not None:
                # Get specific channel info
                channel_info = await controller.get_channel_info(channel_id)
                if channel_info:
                    return {
                        "channel_id": channel_info.channel_id,
                        "name": channel_info.name,
                        "gain_db": channel_info.gain,
                        "muted": channel_info.muted,
                        "phantom_power": channel_info.phantom_power,
                        "eq_settings": channel_info.eq_settings
                    }
                else:
                    return {"error": f"Channel {channel_id} not found"}
            else:
                # Get all channels status
                return await controller.get_all_channels_status()
        
        return Tool(
            name="get_channel_status",
            description="Get the current status of audio channels including gain, mute status, and phantom power",
            function=get_channel_status
        )
    
    @staticmethod
    def set_channel_gain_tool() -> Tool:
        """Tool to set channel gain."""
        async def set_channel_gain(channel_id: int, gain_db: float) -> Dict[str, Any]:
            """Set the gain for a specific audio channel.
            
            Args:
                channel_id: Channel ID (1-8)
                gain_db: Gain in decibels (-60 to +60)
            
            Returns:
                Dictionary with operation result
            """
            controller = get_audio_controller()
            success = await controller.set_channel_gain(channel_id, gain_db)
            
            return {
                "success": success,
                "channel_id": channel_id,
                "gain_db": gain_db,
                "message": f"Successfully set channel {channel_id} gain to {gain_db} dB" if success 
                          else f"Failed to set channel {channel_id} gain"
            }
        
        return Tool(
            name="set_channel_gain",
            description="Set the gain level for a specific audio channel",
            function=set_channel_gain
        )
    
    @staticmethod
    def mute_channel_tool() -> Tool:
        """Tool to mute/unmute channels."""
        async def mute_channel(channel_id: int, muted: bool = True) -> Dict[str, Any]:
            """Mute or unmute a specific audio channel.
            
            Args:
                channel_id: Channel ID (1-8)
                muted: True to mute, False to unmute
            
            Returns:
                Dictionary with operation result
            """
            controller = get_audio_controller()
            success = await controller.mute_channel(channel_id, muted)
            
            action = "muted" if muted else "unmuted"
            return {
                "success": success,
                "channel_id": channel_id,
                "muted": muted,
                "message": f"Successfully {action} channel {channel_id}" if success 
                          else f"Failed to {action.replace('ed', 'e')} channel {channel_id}"
            }
        
        return Tool(
            name="mute_channel",
            description="Mute or unmute a specific audio channel",
            function=mute_channel
        )
    
    @staticmethod
    def set_phantom_power_tool() -> Tool:
        """Tool to control phantom power."""
        async def set_phantom_power(channel_id: int, enabled: bool) -> Dict[str, Any]:
            """Enable or disable phantom power for a channel.
            
            Args:
                channel_id: Channel ID (1-8)
                enabled: True to enable, False to disable
            
            Returns:
                Dictionary with operation result
            """
            controller = get_audio_controller()
            success = await controller.set_phantom_power(channel_id, enabled)
            
            action = "enabled" if enabled else "disabled"
            return {
                "success": success,
                "channel_id": channel_id,
                "phantom_power": enabled,
                "message": f"Successfully {action} phantom power for channel {channel_id}" if success 
                          else f"Failed to {action.replace('ed', 'e')} phantom power for channel {channel_id}"
            }
        
        return Tool(
            name="set_phantom_power",
            description="Enable or disable phantom power for a specific audio channel",
            function=set_phantom_power
        )
    
    @staticmethod
    def apply_preset_tool() -> Tool:
        """Tool to apply audio presets."""
        async def apply_preset(preset_name: str) -> Dict[str, Any]:
            """Apply a predefined audio preset configuration.
            
            Args:
                preset_name: Name of the preset (broadcast_news, live_sports, reset_all)
            
            Returns:
                Dictionary with operation result
            """
            controller = get_audio_controller()
            success = await controller.apply_preset(preset_name)
            
            return {
                "success": success,
                "preset_name": preset_name,
                "message": f"Successfully applied preset: {preset_name}" if success 
                          else f"Failed to apply preset: {preset_name}"
            }
        
        return Tool(
            name="apply_preset",
            description="Apply a predefined audio configuration preset",
            function=apply_preset
        )
    
    @staticmethod
    def get_device_info_tool() -> Tool:
        """Tool to get device information."""
        async def get_device_info() -> Dict[str, Any]:
            """Get information about the Shure audio device.
            
            Returns:
                Dictionary containing device information
            """
            controller = get_audio_controller()
            return await controller.get_device_info()
        
        return Tool(
            name="get_device_info",
            description="Get information about the connected Shure audio device",
            function=get_device_info
        )


def create_agent() -> Agent:
    """Create the Shure Audio Control Agent."""
    
    # Initialize Azure OpenAI model
    llm = AzureOpenAIModel()
    
    # Create tools
    audio_tools = AudioControlTools()
    tools = [
        audio_tools.get_channel_status_tool(),
        audio_tools.set_channel_gain_tool(),
        audio_tools.mute_channel_tool(),
        audio_tools.set_phantom_power_tool(),
        audio_tools.apply_preset_tool(),
        audio_tools.get_device_info_tool()
    ]
    
    # Create agent with system prompt
    system_prompt = """You are a Shure Audio Control Agent for broadcast production environments.

Your role is to assist broadcast engineers and production staff with controlling Shure audio equipment. You can:

1. Check the status of audio channels (gain, mute, phantom power)
2. Adjust channel gain levels
3. Mute/unmute channels
4. Control phantom power for condenser microphones
5. Apply predefined presets for different broadcast scenarios
6. Provide device information and status

When users ask about audio control, be helpful and specific. Always confirm actions before making changes that could affect live broadcasts. If asked about channel numbers, remember that channels are numbered 1-8.

Available presets:
- broadcast_news: Optimized for news broadcast
- live_sports: Optimized for live sports commentary  
- reset_all: Reset all channels to default settings

Be concise but informative in your responses, and always prioritize broadcast safety.
"""
    
    return Agent(
        name="Shure Audio Control Agent",
        instructions=system_prompt,
        model=llm,
        tools=tools
    ) 