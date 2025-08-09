"""
This module contains the specific system instructions for different
automation systems that the orchestrator agent can control.
"""

CUEZ_CONFIG = {
    "config_name":
    "CUEZ_AGENT",
    "agent_name":
    "CUEZ Rundown Agent",
    "instructions":
    """
You are configured to interact with the CUEZ rundown system.
- Use the `CUEZ Rundown Agent` for all rundown-related tasks.
- All your responses should be tailored for an operator of CUEZ.
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

AUTOMATION_SYSTEMS = {
    "cuez": CUEZ_CONFIG,
    "sofie": SOFIE_CONFIG,
}

DEFAULT_INSTRUCTIONS = "No specific rundown system is configured. You must ask the user to select one."
