import os
import json
import requests 
from dotenv import load_dotenv
from google.adk.agents import Agent
from googlesearch import search  # Import google search functionality

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY_VALUE = os.getenv("API_KEY_VALUE")

# FILE VARAIBLES HERE

# --- Check API Key and Base URL ---
def validate_api_key_and_url() -> dict or None:
    if not API_BASE_URL or not API_KEY_VALUE:
        return {
            "status": "error",
            "error_message": "API_BASE_URL or API_KEY_VALUE not configured in .env file.",
        }
    return None

# --- Handle Request Exceptions ---
def handle_request_exceptions(func):
    """
    Decorator function to handle request exceptions for API functions.
    Wraps any function that makes API requests and handles common exceptions.
    
    Args:
        func: The function to wrap with exception handling
        
    Returns:
        A wrapped function that handles request exceptions
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as http_err:
            response = http_err.response if hasattr(http_err, 'response') else None
            return {
                "status": "error",
                "error_message": f"HTTP error occurred: {http_err} - {response.text if response else 'No response body'}",
            }
        except requests.exceptions.ConnectionError as conn_err:
            return {
                "status": "error",
                "error_message": f"Connection error occurred: {conn_err}",
            }
        except requests.exceptions.Timeout as timeout_err:
            return {
                "status": "error",
                "error_message": f"Timeout error occurred: {timeout_err}",
            }
        except requests.exceptions.RequestException as req_err:
            return {
                "status": "error",
                "error_message": f"An unexpected error occurred with the request: {req_err}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error_message": f"An unexpected error occurred: {e}",
            }
    return wrapper

# --- New Tool Definition for Searching Information ---
def search_information(query: str) -> dict:
    """
    Searches for information online and returns results.

    Args:
        query (str): The search query.

    Returns:
        dict: Contains status ('success' or 'error') and search results or error message.
    """
    try:
        # Using googlesearch to get results
        search_results = []
        for result in search(query, num_results=5):
            search_results.append(result)
            
        return {
            "status": "success",
            "results": search_results,
            "summary": f"Found {len(search_results)} results for '{query}'."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error performing search: {str(e)}"
        }

# --- Example Usage (for testing the agent, ADK style) ---
if __name__ == "__main__":
    print("Enhanced Name Updater Agent initialized.")
    print(f"Using API Base URL: {API_BASE_URL}")
    print(f"API Key Loaded: {'Yes' if API_KEY_VALUE else 'No'}")

    if not API_BASE_URL or not API_KEY_VALUE:
        print("\nERROR: Please set API_BASE_URL and API_KEY_VALUE in your .env file.")
    else:
        print("\n--- Testing the tool directly (simulating agent call) ---")
        test_name = "Alice Wonderland"
        print(f"Attempting to update name to: {test_name}")
        
        print("\n--- Direct Tool Test ---")
        # Uncomment to test:
        # direct_test_result = update_name_on_strap(person_name="Test User")
        # print(direct_test_result)
        
        # Test search tool
        # search_result = search_information("Who is the UK Prime Minister")
        # print(search_result)

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


# --- Agent Definition with correct model specification ---
root_agent = Agent(
    name="enhanced_name_updater_agent",
    model="gemini-2.0-flash-exp", # Fixed model name - remove "-latest" suffix
    description=(
        "Agent to update various broadcast components like a name on a digital strap or search for information about people or a locator with location information"
    ),
    instruction=agent_instructions,
    tools=[
        
    ],
)