import os
from typing import Optional
from shure_audio_agent.azure_logic_app_client import azure_logic_app_client
from shure_audio_agent.cache import cache_manager
from shure_audio_agent.query.get_status import get_status

COVERAGE_SIZE = 6096
CENTER_RANGE_MIN = -1219.2
CENTER_RANGE_MAX = 1219.2

def set_microphone_channel_coverage(area_name: Optional[str] = None, area_index: int = 0, center_x: float = 0.0, center_y: float = 0.0) -> dict:
    """
    Args:
        area_name (str, optional): The name of the audio coverage area to reposition. If not provided, area_index is used.
        area_index (int, optional): The index of the audio coverage area to reposition (default 0).
        center_x (float): The x coordinate of the center of the coverage area. Must be in [-1219.2, 1219.2].
        center_y (float): The y coordinate of the center of the coverage area. Must be in [-1219.2, 1219.2].
    Returns:
        dict: The result of the mutation.
    Raises:
        ValueError: If center_x or center_y is out of the allowed range, or area not found.
    """
    if not (CENTER_RANGE_MIN <= center_x <= CENTER_RANGE_MAX):
        raise ValueError(f"center_x must be in [{CENTER_RANGE_MIN}, {CENTER_RANGE_MAX}]")
    if not (CENTER_RANGE_MIN <= center_y <= CENTER_RANGE_MAX):
        raise ValueError(f"center_y must be in [{CENTER_RANGE_MIN}, {CENTER_RANGE_MAX}]")
    status = get_status()
    area_id = None
    # Search all devices for audioCoverageAreas
    for device in status['data']['discoveredDevices']:
        try:
            areas = device['features']['audioCoverageAreas']['audioCoverageAreas']
            if area_name:
                for area in areas:
                    # If area_name matches id or a known name field, use it
                    if area.get('id') == area_name or area.get('features', {}).get('name', {}).get('name') == area_name:
                        area_id = area['id']
                        break
            else:
                if 0 <= area_index < len(areas):
                    area_id = areas[area_index]['id']
            if area_id:
                break
        except (KeyError, TypeError):
            continue
    if not area_id:
        raise ValueError("Audio coverage area not found in cached status.")
    half_size = COVERAGE_SIZE / 2
    coordinates = {
        "xMin": center_x - half_size,
        "xMax": center_x + half_size,
        "yMin": center_y - half_size,
        "yMax": center_y + half_size,
    }
    
    payload = {
        "repositionAudioCoverageAreaId": area_id,
        "coordinates": coordinates
    }
    result = azure_logic_app_client.send_tool_request("set_microphone_channel_coverage", payload)
    # Invalidate status cache after mutation
    cache_manager.set('status', None)
    return result