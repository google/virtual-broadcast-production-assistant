"""A tool for transforming and saving timeline events in a single step."""

import json
import uuid
from datetime import datetime, timezone
from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext
import firebase_admin
from firebase_admin import firestore_async
from google.genai.types import Content, Part

# It's a good practice to have the model name as a constant
GEMINI_MODEL = "gemini-1.5-flash"

# The detailed prompt for the TimelineAgent
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
"""

# Define the transformation agent. It's defined here as it's only used by this tool.
timeline_transformer_agent = LlmAgent(
    name="TimelineTransformerAgent",
    model=GEMINI_MODEL,
    instruction=TRANSFORMATION_PROMPT,
)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_admin.initialize_app()

async def log_event_to_timeline(raw_text: str, tool_context: ToolContext) -> str:
    """
    Takes raw text from a tool, transforms it into a structured timeline event
    using a dedicated agent, and saves it to Firestore.

    Args:
        raw_text: The raw string output from the sub-agent's tool.
        tool_context: The context of the tool call.

    Returns:
        A string indicating the result of the operation.
    """
    print(f"Log event to timeline tool called with text: {raw_text}")

    try:
        # --- Step 1: Transform the data using the TimelineTransformerAgent ---

        # We need to run the agent in-process. The simplest way is to call its
        # underlying model directly, since it's a simple LlmAgent with no tools.
        model = timeline_transformer_agent.model
        response = await model.generate_content_async(
            f"{TRANSFORMATION_PROMPT}\n\n**Raw Text Input:**\n{raw_text}"
        )

        json_string = response.text.strip()
        if json_string.startswith("```json"):
            json_string = json_string[7:]
        if json_string.endswith("```"):
            json_string = json_string[:-3]

        structured_data = json.loads(json_string)

        if 'id' not in structured_data or not structured_data['id']:
            structured_data['id'] = str(uuid.uuid4())

        print("Successfully transformed data:")
        print(json.dumps(structured_data, indent=2))

        # --- Step 2: Save the structured data to Firestore ---

        user_id = tool_context.state.get("user_id", "unknown_user")
        session_id = tool_context.state.get("session_id", "unknown_session")

        structured_data['user_id'] = user_id
        structured_data['session_id'] = session_id
        structured_data['timestamp'] = datetime.now(timezone.utc)

        db = firestore_async.client()
        doc_ref = db.collection("timeline_events").document(structured_data['id'])
        await doc_ref.set(structured_data)

        print(f"Successfully saved event {structured_data['id']} to Firestore.")

        return f"Event '{structured_data.get('title')}' was successfully logged to the timeline."

    except Exception as e:
        print(f"Error in log_event_to_timeline: {e}")
        return f"Failed to log event to timeline: {e}"
