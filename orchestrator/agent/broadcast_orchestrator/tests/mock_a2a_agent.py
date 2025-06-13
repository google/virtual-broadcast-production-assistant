from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import uuid

from a2a.types import AgentCard, Task, SendMessageResponse, SendMessageSuccessResponse, Message, Part

# Using Pydantic models for data validation if they were part of a2a.types
# For this mock, we'll use dataclasses for simplicity if Pydantic isn't strictly needed
# or if we want to avoid deeper dependencies in the mock.

@dataclass
class MockA2AAgent:
    agent_name: str
    agent_description: str
    agent_url: str
    received_messages: List[Dict[str, Any]] = field(default_factory=list)
    canned_responses: Dict[str, Any] = field(default_factory=dict) # To map task text to a response
    default_task_response_parts: List[Part] = field(default_factory=lambda: [Part(type="text", text="Default mock response")])

    def get_agent_card(self) -> AgentCard:
        return AgentCard(
            name=self.agent_name,
            description=self.agent_description,
            # Assuming a simplified structure for Endpoints and Methods for the mock
            # Adjust if the actual AgentCard structure is more complex and relevant here
            endpoints=[{"url": self.agent_url, "type": "A2A"}],
            methods=["send_message"], # Example method
            tools=[], # Example, adjust as needed
            id=str(uuid.uuid4()), # Example ID
            version="0.1.0" # Example version
        )

    async def handle_send_message(self, message_request_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Simulate receiving a message and storing it
        # message_request_dict is expected to be the JSON representation of SendMessageRequest
        self.received_messages.append(message_request_dict)

        # Simulate a response based on the task text or a default
        task_text = ""
        if message_request_dict.get("params", {}).get("message", {}).get("parts"):
            for part in message_request_dict["params"]["message"]["parts"]:
                if part.get("type") == "text":
                    task_text = part.get("text", "")
                    break

        response_parts = self.default_task_response_parts
        if task_text in self.canned_responses:
            # Assuming canned_responses maps task text to a list of Part dictionaries or Part objects
            canned_response_data = self.canned_responses[task_text]
            if isinstance(canned_response_data, list) and all(isinstance(p, Part) for p in canned_response_data):
                response_parts = canned_response_data
            elif isinstance(canned_response_data, str): # Simple string response
                 response_parts = [Part(type="text", text=canned_response_data)]
            # Add more sophisticated canned response logic if needed

        # Construct a SendMessageSuccessResponse-like structure
        # This needs to align with what A2AClient expects
        task_id = message_request_dict.get("params", {}).get("message", {}).get("taskId", str(uuid.uuid4()))
        context_id = message_request_dict.get("params", {}).get("message", {}).get("contextId", str(uuid.uuid4()))

        # Create a Task object. Adjust fields as necessary based on actual a2a.types.Task
        task_result = Task(
            id=task_id,
            status="completed", # Simulate task completion
            role="assistant",
            parts=response_parts, # Use the determined response parts
            context_id=context_id,
            # Add other necessary Task fields, e.g., artifacts, if the client expects them
            artifacts=[]
        )

        success_response = SendMessageSuccessResponse(
            jsonrpc="2.0",
            id=message_request_dict.get("id", str(uuid.uuid4())), # Echo back the request ID
            result=task_result
        )

        # The A2AClient will likely expect a SendMessageResponse object,
        # which wraps either SendMessageSuccessResponse or SendMessageErrorResponse.
        # We need to return a dictionary that can be parsed into SendMessageResponse.
        # Assuming SendMessageResponse has a 'root' attribute that holds the success/error response.
        return {"root": success_response.model_dump(exclude_none=True)}

    def add_canned_response(self, task_text_trigger: str, response_parts: Union[List[Part], str]):
        if isinstance(response_parts, str):
            self.canned_responses[task_text_trigger] = [Part(type="text", text=response_parts)]
        else:
            self.canned_responses[task_text_trigger] = response_parts

    def clear_received_messages(self):
        self.received_messages.clear()

# Example usage (optional, for testing the mock itself)
async def main():
    mock_agent = MockA2AAgent(
        agent_name="TestAgent",
        agent_description="A mock agent for testing.",
        agent_url="http://localhost:8001/mock"
    )

    # Get agent card
    card = mock_agent.get_agent_card()
    print(f"Agent Card: {card.model_dump_json(indent=2)}")

    # Simulate sending a message
    test_message_id = str(uuid.uuid4())
    test_task_id = str(uuid.uuid4())
    message_payload = {
        "id": test_message_id,
        "jsonrpc": "2.0",
        "method": "send_message",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Hello from orchestrator"}],
                "messageId": str(uuid.uuid4()),
                "taskId": test_task_id
            }
        }
    }

    response = await mock_agent.handle_send_message(message_payload)
    print(f"Response from mock: {json.dumps(response, indent=2)}")
    print(f"Received messages by mock: {mock_agent.received_messages}")

if __name__ == "__main__":
    import asyncio
    import json # for pretty printing the dict
    # Add Part and other necessary types from a2a.types if they are not Pydantic models
    # For this example, assuming Part is available or defined simply.
    # from a2a.types import Part
    # If Part is a Pydantic model, ensure it's imported or defined.
    # For simplicity, if Part is not a Pydantic model, its usage here is as a simple data container.

    # Example of a simple Part definition if not available from a2a.types
    if "Part" not in globals():
        @dataclass
        class Part:
            type: str
            text: Optional[str] = None
            # Add other part types like 'tool_code', 'tool_code_result' if needed by your tests

    asyncio.run(main())
