import os
from typing import Optional
from shure_audio_agent.azure_logic_app_client import azure_logic_app_client
from shure_audio_agent.cache import cache_manager
from shure_audio_agent.query.get_status import get_status

ALLOWED_FILTER_TYPES = {"PARAMETRIC", "LOW_CUT", "LOW_SHELF", "HIGH_CUT", "HIGH_SHELF"}
ALLOWED_Q_FACTORS = [0.27, 0.4, 0.67, 0.92, 1.41, 2.14, 2.87, 4.32, 8.65, 14.42, 28.85, 57.71, 100.99]
GAIN_MIN, GAIN_MAX = -18.0, 18.0
FREQ_MIN, FREQ_MAX = 20, 20000


def set_eq_setting(
    channel_name: str,
    filter_index: int,
    enabled: Optional[bool] = None,
    filterType: Optional[str] = None,
    frequency: Optional[int] = None,
    gain: Optional[float] = None,
    qFactor: Optional[float] = None
) -> dict:
    """
    Set EQ filter settings for a given channel and filter index, enforcing constraints.

    Constraints:
        - filterType: PARAMETRIC, LOW_CUT, LOW_SHELF, HIGH_CUT, HIGH_SHELF
        - gain: float, must be between -18.0 and 18.0 (rounded to 0.1 precision)
        - frequency: int, must be between 20 and 20000
        - qFactor: float, must be one of [0.27, 0.4, 0.67, 0.92, 1.41, 2.14, 2.87, 4.32, 8.65, 14.42, 28.85, 57.71, 100.99]
    """
    # Validate constraints
    if filterType is not None and filterType not in ALLOWED_FILTER_TYPES:
        raise ValueError(f"filterType must be one of {ALLOWED_FILTER_TYPES}")
    if gain is not None:
        if not (GAIN_MIN <= gain <= GAIN_MAX):
            raise ValueError(f"gain must be between {GAIN_MIN} and {GAIN_MAX}")
        # round to 0.1 precision
        gain = round(gain, 1)
    if frequency is not None:
        if not (FREQ_MIN <= frequency <= FREQ_MAX):
            raise ValueError(f"frequency must be between {FREQ_MIN} and {FREQ_MAX}")
        frequency = int(frequency)
    if qFactor is not None:
        if qFactor not in ALLOWED_Q_FACTORS:
            raise ValueError(f"qFactor must be one of {ALLOWED_Q_FACTORS}")
    status = get_status()
    filter_id = None
    # Search all devices and channels for the matching channel name
    for device in status['data']['discoveredDevices']:
        try:
            audio_channels = device['features']['audioChannels']['audioChannels']
            for ch in audio_channels:
                if ch['features']['name']['name'] == channel_name:
                    filters = ch['features']['equalizer']['filters']
                    if 0 <= filter_index < len(filters):
                        filter_id = filters[filter_index]['id']
                        break
            if filter_id:
                break
        except (KeyError, TypeError):
            continue
    if not filter_id:
        raise ValueError(f"Filter index {filter_index} for channel '{channel_name}' not found in cached status.")
    # Build the updates payload
    updates = []
    if enabled is not None or filterType is not None:
        config = {}
        if enabled is not None:
            config['enabled'] = enabled
        if filterType is not None:
            config['filterType'] = filterType
        updates.append({
            "equalizerFilters": {
                "id": filter_id,
                "features": {"configuration": config}
            }
        })
    if frequency is not None:
        updates.append({
            "equalizerFilters": {
                "id": filter_id,
                "features": {"frequency": {"frequency": frequency}}
            }
        })
    if gain is not None:
        updates.append({
            "equalizerFilters": {
                "id": filter_id,
                "features": {"gain": {"gain": gain}}
            }
        })
    if qFactor is not None:
        updates.append({
            "equalizerFilters": {
                "id": filter_id,
                "features": {"qFactor": {"qFactor": qFactor}}
            }
        })
    if not updates:
        raise ValueError("No EQ parameters provided to update.")
    
    payload = {"updates": updates}
    result = azure_logic_app_client.send_tool_request("set_eq_setting", payload)
    # Invalidate status cache after mutation
    cache_manager.set('status', None)
    return result 