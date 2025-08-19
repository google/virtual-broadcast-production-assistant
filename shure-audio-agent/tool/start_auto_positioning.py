import os
from typing import Optional
from shure_audio_agent.azure_logic_app_client import azure_logic_app_client
from shure_audio_agent.cache import cache_manager
from shure_audio_agent.query.get_status import get_status

def start_auto_positioning(channel_name: Optional[str] = None, channel_index: int = 0) -> dict:
    """
    Start auto positioning for a given audio channel.

    Args:
        channel_name (str, optional): Name of the audio channel to auto position (e.g., "Output", "Channel 1"). If not provided, channel_index is used.
        channel_index (int, optional): Index of the audio channel to auto position (default 0).

    Returns:
        dict: The result of the mutation.

    Raises:
        ValueError: If the channel is not found.
    """
    status = get_status()
    channel_id = None
    # Search all devices for audioChannels
    for device in status['data']['discoveredDevices']:
        try:
            channels = device['features']['audioChannels']['audioChannels']
            if channel_name:
                for ch in channels:
                    if ch['features']['name']['name'] == channel_name:
                        channel_id = ch['id']
                        break
            else:
                if 0 <= channel_index < len(channels):
                    channel_id = channels[channel_index]['id']
            if channel_id:
                break
        except (KeyError, TypeError):
            continue
    if not channel_id:
        raise ValueError("Audio channel not found in cached status.")
    
    payload = {
        "startAudioChannelAutoPositioningId": channel_id
    }
    result = azure_logic_app_client.send_tool_request("start_auto_positioning", payload)
    # Invalidate status cache after mutation
    cache_manager.set('status', None)
    return result 