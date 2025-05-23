import os
from google.adk.agents import Agent
from google.adk.tools import google_search  # Import the tool

def load_instructions_from_file(filename):
    """
    Load agent instructions from a markdown file.
    
    Args:
        filename (str): Path to the markdown file containing instructions.
        
    Returns:
        str: The instruction text from the file.
    """
    possible_paths = [
        filename,  # Direct filename
        os.path.join(os.path.dirname(__file__), filename),  # Same directory as script
        os.path.abspath(filename),  # Absolute path
        os.path.join(os.getcwd(), filename)  # Current working directory
    ]
    
    # Try each path
    for path in possible_paths:
        try:
            print(f"Trying to load instructions from: {path}")
            if os.path.exists(path):
                with open(path, 'r') as file:
                    instructions = file.read()
                print(f"Successfully loaded instructions from {path}")
                return instructions
        except Exception as e:
            print(f"Error loading instructions from {path}: {e}")
            return "Your instructions are not available at the moment. Tell the user they haven't loaded"

# Load instructions from external file
agent_instructions = load_instructions_from_file('agent_instructions.md')

root_agent = Agent(
   # A unique name for the agent.
   name="basic_search_agent",
   # The Large Language Model (LLM) that agent will use.
   model="gemini-2.0-flash",
   # model="gemini-2.0-flash-live-001",  # New streaming model version as of Feb 2025
   # A short description of the agent's purpose.
   description="Agent to answer questions using Google Search.",
   # Instructions to set the agent's behavior.
   instruction=agent_instructions,
   # Add google_search tool to perform grounding with Google search.
   tools=[google_search]
)
