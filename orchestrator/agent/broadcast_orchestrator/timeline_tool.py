"""A tool for updating the timeline with activity from other agents."""

import json
import uuid
from datetime import datetime, timezone
from google.adk.tools.tool_context import ToolContext
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore_async

# It's a good practice to have the model name as a constant
GEMINI_MODEL = "gemini-1.5-flash"

# The detailed prompt for the Gemini model
TRANSFORMATION_PROMPT = """
You are a data transformation specialist. Your task is to convert a raw text output from a sub-agent's tool into a structured JSON object. This JSON object will be used to populate a timeline view in a frontend application.

The raw text input will be provided to you. You must analyze this text and extract the relevant information to populate the following JSON structure.

**Target JSON Structure:**
```json
{
  "id": "A unique identifier for the event. You can generate a UUID.",
  "category": "The category of the event (e.g., 'VIDEO', 'AUDIO', 'GFX', 'REFORMATTING', 'GENERAL').",
  "title": "A concise, human-readable title for the event.",
  "subtitle": "A short, descriptive subtitle with more details.",
  "severity": "The severity of the event. Must be one of: 'critical', 'warning', 'info'.",
  "timeOffsetSec": "The time offset in seconds from now. If not specified, default to 0.",
  "status": "The status of the event. Default to 'default'."
}
```

**Instructions:**
1.  Carefully read the provided raw text input.
2.  Identify the key pieces of information.
3.  Map the extracted information to the fields in the target JSON structure.
4.  If a value for a field cannot be determined from the input, use a reasonable default or 'null'.
5.  The `id` field must be a unique identifier. Generate a UUID for it.
6.  The `severity` must be one of the specified values. Infer the severity from the input text (e.g., words like 'error', 'failed' suggest 'critical'; 'warning', 'mismatch' suggest 'warning'). Default to 'info' if unsure.
7.  Your final output must be only the JSON object, with no other text or explanations.

**Example:**
*   **Input:** "Error: The video clip 'promo_ad_123' is missing from the server. This is a critical issue."
*   **Output:**
    ```json
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "category": "VIDEO",
      "title": "Missing video clip",
      "subtitle": "promo_ad_123",
      "severity": "critical",
      "timeOffsetSec": 0,
      "status": "default"
    }
    ```
"""

# Initialize Firebase Admin SDK
# A check is included to prevent re-initialization in a hot-reload environment
if not firebase_admin._apps:
    firebase_admin.initialize_app()

async def update_timeline_activity(tool_output: str, tool_context: ToolContext) -> str:
    """
    Processes the output of a tool from a sub-agent, transforms it into a
    structured format, and saves it to the timeline.

    Args:
        tool_output: The raw string output from the sub-agent's tool.
        tool_context: The context of the tool call.

    Returns:
        A string indicating the result of the operation.
    """
    print(f"Timeline tool called with output: {tool_output}")

    try:
        # Initialize the Gemini model
        model = genai.GenerativeModel(GEMINI_MODEL)

        # Combine the prompt and the tool output
        prompt_with_input = f"{TRANSFORMATION_PROMPT}\n\n**Raw Text Input:**\n{tool_output}"

        # Generate the structured data
        response = await model.generate_content_async(prompt_with_input)

        # The response might be in a markdown block, so we need to extract it.
        json_string = response.text.strip()
        if json_string.startswith("```json"):
            json_string = json_string[7:]
        if json_string.endswith("```"):
            json_string = json_string[:-3]

        # Parse the JSON string
        structured_data = json.loads(json_string)

        # Ensure there's an ID
        if 'id' not in structured_data or not structured_data['id']:
            structured_data['id'] = str(uuid.uuid4())

        print("Successfully transformed data:")
        print(json.dumps(structured_data, indent=2))

        # Get user_id and session_id from the context
        user_id = tool_context.state.get("user_id", "unknown_user")
        session_id = tool_context.state.get("session_id", "unknown_session")

        # Add metadata to the structured data
        structured_data['user_id'] = user_id
        structured_data['session_id'] = session_id
        structured_data['timestamp'] = datetime.now(timezone.utc)

        # Save to Firestore
        db = firestore_async.client()
        doc_ref = db.collection("timeline_events").document(structured_data['id'])
        await doc_ref.set(structured_data)

        print(f"Successfully saved event {structured_data['id']} to Firestore.")

        return f"Timeline updated successfully with event: {structured_data.get('title')}"

    except Exception as e:
        print(f"Error during data transformation or Firestore save: {e}")
        return f"Failed to update timeline: {e}"
