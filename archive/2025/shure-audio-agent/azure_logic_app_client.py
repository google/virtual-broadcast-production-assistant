import requests
import json
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AzureLogicAppClient:
    """
    Client for sending tool requests to Azure Logic App.
    The Logic App will handle the actual GQL queries and relay them to the on-premise endpoint.
    """
    
    def __init__(self, webhook_url: str = None):
        # Use provided webhook_url or get from environment variable
        self.webhook_url = webhook_url or os.getenv('AZURE_LOGIC_APP_WEBHOOK_URL')
        if not self.webhook_url:
            raise ValueError("Webhook URL must be provided either as parameter or via AZURE_LOGIC_APP_WEBHOOK_URL environment variable")
        
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "ShureAudioAgent/1.0"
        }
    
    def send_tool_request(self, tool_name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a tool request to Azure Logic App.
        
        Args:
            tool_name (str): The name of the tool/query to execute
            payload (Optional[Dict[str, Any]]): The payload for mutations (None for queries)
            
        Returns:
            Dict[str, Any]: The response from the Azure Logic App
            
        Raises:
            requests.RequestException: If the request fails
        """
        # Uniform JSON schema for all requests
        request_body = {
            "tool_name": tool_name,
            "payload": payload or {}
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=request_body,
                headers=self.headers,
                timeout=30
            )
            
            # Handle different response status codes
            if response.status_code in [200, 202]:
                # Try to parse JSON response
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # If response is not JSON, return the text
                    return {"response": response.text, "status_code": response.status_code}
            else:
                # Handle error responses
                error_msg = f"Azure Logic App returned status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data}"
                except json.JSONDecodeError:
                    error_msg += f": {response.text}"
                
                raise requests.RequestException(error_msg)
                
        except requests.RequestException as e:
            raise e
        except Exception as e:
            raise requests.RequestException(f"Unexpected error: {str(e)}")

# Create a global instance using environment variable
azure_logic_app_client = AzureLogicAppClient() 