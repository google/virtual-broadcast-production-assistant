from google.adk.agents import Agent

root_agent = Agent(
    name="posture_stubzy_agent",
    model="gemini-2.0-flash",
    description=(
        "Agent to do spellchecking. Provide entity uid and text that needs checking."
    ),
    instruction=(
        "You are a helpful agent who can spellchecks, when asked to spellcheck, you will only return text if it needs correction and provide the uid of the entity with the correction. "
        "You will not ask for clarification. "
        "You will not return any other text, just the corrected text and the uid of the entity with the correction. "
        "If there is no correction needed, you will return an empty string. "
    ),
    tools=[],
)

def create_agent():
    """Create and return the agent instance."""
    return root_agent