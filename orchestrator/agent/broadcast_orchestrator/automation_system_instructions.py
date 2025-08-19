"""
This module contains the specific system instructions for different
automation systems that the orchestrator agent can control.
"""

CUEZ_CONFIG = {
    "config_name":
    "CUEZ_AGENT",
    "agent_name":
    "Cuez Rundown Agent",
    "instructions":
    """
You are configured to interact with the Cuez rundown system.
- Use the `Cuez Rundown Agent` for all rundown-related tasks.
- All your responses should be tailored for an operator of Cuez.
"""
}

SOFIE_CONFIG = {
    "config_name":
    "SOFIE_AGENT",
    "agent_name":
    "Sofie Rundown Agent",
    "instructions":
    """
You are configured to interact with the Sofie Automation system.
- Use the `Sofie Agent` for all rundown-related tasks.
- All your responses should be tailored for an operator of Sofie.
"""
}

CUEPILOT_CONFIG = {
    "config_name":
    "CUEPILOT_AGENT",
    "agent_name":
    "CuePilot OSC Agent",
    "instructions":
    """
You are configured to interact with the CuePilot Software:
- Pick a single CuePilot OSC command and return it.
"""
}

AUTOMATION_SYSTEMS = {
    "cuez": CUEZ_CONFIG,
    "sofie": SOFIE_CONFIG,
    "cuepilot": CUEPILOT_CONFIG,
}

DEFAULT_INSTRUCTIONS = "No specific rundown system is configured. You must ask the user to select one."
