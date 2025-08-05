import os
from typing import Optional
from shure_audio_agent.azure_logic_app_client import azure_logic_app_client
from shure_audio_agent.cache import cache_manager
from shure_audio_agent.query.get_status import get_status

def load_user_preset(preset_name: str) -> dict:
    """
    Args:
        preset_name (str): The name of the user preset to load.
    Returns:
        dict: The result of the mutation.
    """
    status = get_status()
    # Search all devices for the preset by name
    preset_id = None
    for device in status['data']['discoveredDevices']:
        try:
            user_presets = device['features']['userPresets']['userPresets']
            for p in user_presets:
                if p['features']['preset']['name'] == preset_name:
                    preset_id = p['id']
                    break
            if preset_id:
                break
        except (KeyError, TypeError):
            continue
    if not preset_id:
        raise ValueError(f"Preset '{preset_name}' not found in cached status.")
    
    payload = {
        "presetId": preset_id
    }
    result = azure_logic_app_client.send_tool_request("load_user_preset", payload)
    # Invalidate status cache after mutation
    cache_manager.set('status', None)
    return result 