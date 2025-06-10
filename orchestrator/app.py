"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import gradio as gr
from typing import List, AsyncIterator, Dict, Any
from agent.broadcast_orchestrator.agent import (
    root_agent as routing_agent,
)
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.events import Event
from google.genai import types
from pprint import pformat
import asyncio
import traceback  # Import the traceback module
from datetime import datetime

APP_NAME = "routing_app"
USER_ID = "default_user"
SESSION_ID = "default_session"

SESSION_SERVICE = InMemorySessionService()
ROUTING_AGENT_RUNNER = Runner(
    agent=routing_agent,
    app_name=APP_NAME,
    session_service=SESSION_SERVICE,
)

# Global list to store debug logs
debug_logs: List[Dict[str, Any]] = []


async def get_response_from_agent(
    message: str,
    history: List[gr.ChatMessage],
) -> AsyncIterator[gr.ChatMessage]:
    """Get response from host agent."""
    try:
        events_iterator: AsyncIterator[Event] = ROUTING_AGENT_RUNNER.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=types.Content(role="user", parts=[types.Part(text=message)]),
        )

        async for event in events_iterator:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        formatted_call = f"```python\n{pformat(part.function_call.model_dump(exclude_none=True), indent=2, width=80)}\n```"
                        tool_call_content = f"🛠️ **Tool Call: {part.function_call.name}**\n{formatted_call}"
                        
                        # Add to debug logs
                        debug_logs.insert(0, {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "Agent Call",
                            "agent": part.function_call.name,
                            "content": pformat(part.function_call.model_dump(exclude_none=True), indent=2, width=80)
                        })
                        
                        yield gr.ChatMessage(
                            role="assistant",
                            content=tool_call_content,
                        )
                    elif part.function_response:
                        response_content = part.function_response.response
                        if (
                            isinstance(response_content, dict)
                            and "response" in response_content
                        ):
                            formatted_response_data = response_content["response"]
                        else:
                            formatted_response_data = response_content
                        formatted_response = f"```json\n{pformat(formatted_response_data, indent=2, width=80)}\n```"
                        tool_response_content = f"⚡ **Tool Response from {part.function_response.name}**\n{formatted_response}"
                        
                        # Add to debug logs
                        debug_logs.insert(0, {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "Agent Response",
                            "agent": part.function_response.name,
                            "content": pformat(formatted_response_data, indent=2, width=80)
                        })
                        
                        yield gr.ChatMessage(
                            role="assistant",
                            content=tool_response_content,
                        )
            if event.is_final_response():
                final_response_text = ""
                if event.content and event.content.parts:
                    final_response_text = "".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                elif event.actions and event.actions.escalate:
                    final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                if final_response_text:
                    # Add to debug logs
                    debug_logs.insert(0, {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": "Final Response",
                        "agent": "root_agent",
                        "content": final_response_text
                    })
                    
                    yield gr.ChatMessage(role="assistant", content=final_response_text)
                break
    except Exception as e:
        print(f"Error in get_response_from_agent (Type: {type(e)}): {e}")
        traceback.print_exc()  # This will print the full traceback
        yield gr.ChatMessage(
            role="assistant",
            content="An error occurred while processing your request. Please check the server logs for details.",
        )


def get_debug_logs():
    """Format debug logs for display in the table."""
    return [[log["timestamp"], log["type"], log["agent"], log["content"][:100] + "..." if len(log["content"]) > 100 else log["content"]] for log in debug_logs]


def clear_debug_logs():
    """Clear all debug logs."""
    global debug_logs
    debug_logs = []
    return []


async def main():
    """Main gradio app."""
    print("Creating ADK session...")
    await SESSION_SERVICE.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    print("ADK session created successfully.")

    with gr.Blocks(theme=gr.themes.Ocean(), title="A2A Host Agent with Logo") as demo:
        gr.Image(
            "static/a2a.png",
            width=100,
            height=100,
            scale=0,
            show_label=False,
            show_download_button=False,
            container=False,
            show_fullscreen_button=False,
        )
        
        # Chat interface
        chat_interface = gr.ChatInterface(
            get_response_from_agent,
            title="Broadcast Orchestrator Agent",
            description="",
            type="messages",  # Use the new message format
        )
        
        # Debug section
        with gr.Accordion("Debug Logs", open=True):
            with gr.Row():
                gr.Markdown("### Agent Communication Logs (Latest First)")
                clear_button = gr.Button("Clear Logs", scale=0)
            
            debug_table = gr.Dataframe(
                headers=["Timestamp", "Type", "Agent", "Content"],
                datatype=["str", "str", "str", "str"],
                value=get_debug_logs,
                every=1,  # Update every second
                wrap=True,
            )
            
            clear_button.click(
                fn=clear_debug_logs,
                outputs=debug_table
            )

    print("Launching Gradio interface...")
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=8083,
    )
    print("Gradio application has been shut down.")

if __name__ == "__main__":
    asyncio.run(main())