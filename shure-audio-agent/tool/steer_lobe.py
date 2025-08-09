import os
from typing import Optional
from shure_audio_agent.azure_logic_app_client import azure_logic_app_client
from shure_audio_agent.cache import cache_manager
from shure_audio_agent.query.get_status import get_status

ALLOWED_WIDTHS = ["NARROW", "MEDIUM", "WIDE"]
X_MIN, X_MAX = -8000, 8000
Y_MIN, Y_MAX = -8000, 8000
Z_MIN, Z_MAX = 0, 8000

def steer_lobe(
    channel_name: str,
    width: Optional[str] = None,
    xPosition: Optional[float] = None,
    yPosition: Optional[float] = None,
    zPosition: Optional[float] = None
) -> dict:
    """
    Update the lobe width and/or lobe position for a given audio channel by name.

    Constraints:
        - width: NARROW, MEDIUM, WIDE
        - xPosition: float, must be between -8000 and 8000
        - yPosition: float, must be between -8000 and 8000
        - zPosition: float, must be between 0 and 8000

    Args:
        channel_name (str): Name of the audio channel to update.
        width (str, optional): Lobe width. Allowed: NARROW, MEDIUM, WIDE.
        xPosition (float, optional): X position for lobe. Must be in [-8000, 8000].
        yPosition (float, optional): Y position for lobe. Must be in [-8000, 8000].
        zPosition (float, optional): Z position for lobe. Must be in [0, 8000].

    Returns:
        dict: The result of the mutation.

    Raises:
        ValueError: If the channel is not found, width is invalid, or any position is out of range.
    """
    if width is not None and width not in ALLOWED_WIDTHS:
        raise ValueError(f"width must be one of {ALLOWED_WIDTHS}")
    if xPosition is not None and not (X_MIN <= xPosition <= X_MAX):
        raise ValueError(f"xPosition must be in [{X_MIN}, {X_MAX}]")
    if yPosition is not None and not (Y_MIN <= yPosition <= Y_MAX):
        raise ValueError(f"yPosition must be in [{Y_MIN}, {Y_MAX}]")
    if zPosition is not None and not (Z_MIN <= zPosition <= Z_MAX):
        raise ValueError(f"zPosition must be in [{Z_MIN}, {Z_MAX}]")
    status = get_status()
    channel_id = None
    # Search all devices for audioChannels
    for device in status['data']['discoveredDevices']:
        try:
            channels = device['features']['audioChannels']['audioChannels']
            for ch in channels:
                if ch['features']['name']['name'] == channel_name:
                    channel_id = ch['id']
                    break
            if channel_id:
                break
        except (KeyError, TypeError):
            continue
    if not channel_id:
        raise ValueError(f"Audio channel with name '{channel_name}' not found in cached status.")
    features = {}
    if width is not None:
        features['lobeWidth'] = {"width": width}
    if any(v is not None for v in [xPosition, yPosition, zPosition]):
        features['lobePosition'] = {"fixed": {}}
        if xPosition is not None:
            features['lobePosition']['fixed']['xPosition'] = xPosition
        if yPosition is not None:
            features['lobePosition']['fixed']['yPosition'] = yPosition
        if zPosition is not None:
            features['lobePosition']['fixed']['zPosition'] = zPosition
    if not features:
        raise ValueError("No lobe parameters provided to update.")
    updates = [{
        "audioChannel": {
            "id": channel_id,
            "features": features
        }
    }]
    
    payload = {"updates": updates}
    result = azure_logic_app_client.send_tool_request("steer_lobe", payload)
    # Invalidate status cache after mutation
    cache_manager.set('status', None)
    return result 