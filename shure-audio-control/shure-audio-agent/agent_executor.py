"""
Agent executor for the Shure Audio Control Agent

This module provides the executor interface for running the agent within the ADK framework.
"""

import logging
from typing import Dict, Any, AsyncIterator, Optional
from google.adk.runners import Runner
from google.adk.events import Event
from google.genai import types
from a2a.server.executor import BaseAgentExecutor, AgentResponse
from a2a.types import AgentCard, StreamingMode, TaskRequest
import asyncio

logger = logging.getLogger(__name__)


class ADKAgentExecutor(BaseAgentExecutor):
    """Agent executor that bridges A2A protocol with Google ADK."""
    
    def __init__(self, runner: Runner, agent_card: AgentCard):
        """Initialize the executor with ADK runner and agent card.
        
        Args:
            runner: The ADK runner instance
            agent_card: The agent card describing capabilities
        """
        self.runner = runner
        self.agent_card = agent_card
        
    async def execute_task(self, task_request: TaskRequest) -> AsyncIterator[AgentResponse]:
        """Execute a task using the ADK agent.
        
        Args:
            task_request: The incoming task request
            
        Yields:
            AgentResponse objects containing the agent's response
        """
        try:
            # Extract the message content
            if not task_request.messages:
                yield AgentResponse(
                    content="No message provided in task request",
                    is_complete=True,
                    error="Missing message content"
                )
                return
            
            # Get the latest user message
            user_message = task_request.messages[-1]
            message_content = user_message.content
            
            # Convert to ADK format
            adk_message = types.Content(
                role="user", 
                parts=[types.Part(text=message_content)]
            )
            
            logger.info(f"Processing task with message: {message_content}")
            
            # Run the agent
            events_iterator: AsyncIterator[Event] = self.runner.run_async(
                user_id=task_request.context_id or "default_user",
                session_id=task_request.context_id or "default_session", 
                new_message=adk_message,
            )
            
            # Process events and yield responses
            async for event in events_iterator:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.function_call:
                            # Tool call in progress
                            tool_call_msg = f"🔧 Calling tool: {part.function_call.name}"
                            yield AgentResponse(
                                content=tool_call_msg,
                                is_complete=False,
                                streaming_mode=StreamingMode.INCREMENTAL
                            )
                        elif part.function_response:
                            # Tool response received
                            tool_response_msg = f"✅ Tool completed: {part.function_response.name}"
                            yield AgentResponse(
                                content=tool_response_msg,
                                is_complete=False,
                                streaming_mode=StreamingMode.INCREMENTAL
                            )
                        elif part.text:
                            # Regular text response
                            yield AgentResponse(
                                content=part.text,
                                is_complete=False,
                                streaming_mode=StreamingMode.INCREMENTAL
                            )
                
                # Check if this is the final response
                if event.is_final_response():
                    final_content = ""
                    if event.content and event.content.parts:
                        final_content = "".join([
                            p.text for p in event.content.parts if p.text
                        ])
                    elif event.actions and event.actions.escalate:
                        final_content = f"Agent escalated: {event.error_message or 'No specific message.'}"
                    
                    if final_content:
                        yield AgentResponse(
                            content=final_content,
                            is_complete=True
                        )
                    else:
                        yield AgentResponse(
                            content="Task completed",
                            is_complete=True
                        )
                    break
                    
        except Exception as e:
            logger.error(f"Error executing task: {e}", exc_info=True)
            yield AgentResponse(
                content=f"An error occurred while processing your request: {str(e)}",
                is_complete=True,
                error=str(e)
            )
    
    async def get_agent_card(self) -> AgentCard:
        """Get the agent card describing this agent's capabilities.
        
        Returns:
            The agent card
        """
        return self.agent_card
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the agent.
        
        Returns:
            Dictionary containing health status
        """
        try:
            # Check if audio controller can be initialized
            from .audio_control import get_audio_controller
            controller = get_audio_controller()
            
            # Attempt to connect to device (this is a placeholder in our implementation)
            connection_status = await controller.connect()
            device_info = await controller.get_device_info()
            
            return {
                "status": "healthy" if connection_status else "degraded",
                "connection_status": connection_status,
                "device_info": device_info,
                "agent_name": self.agent_card.name,
                "agent_version": self.agent_card.version
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "agent_name": self.agent_card.name,
                "agent_version": self.agent_card.version
            } 