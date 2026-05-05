# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""WebSocket message handling for Gemini Multimodal Live Proxy Server."""

import logging
import json
import asyncio
import base64
from typing import Dict, Any, Optional

# Third-party imports
import websockets
from google.genai import types
from google.api_core import exceptions as google_exceptions

# Local imports
from core.tool_handler import execute_tool
from core.session import create_session, remove_session, SessionState
from core.gemini_client import create_gemini_session

logger = logging.getLogger(__name__)

# --- Constants for Message Types and Keys ---
MSG_TYPE = 'type'
MSG_DATA = 'data'
MSG_READY = 'ready'
MSG_ERROR = 'error'
MSG_AUDIO = 'audio'
MSG_IMAGE = 'image'
MSG_TEXT = 'text'
MSG_END = 'end'
MSG_TURN_COMPLETE = 'turn_complete'
MSG_FUNCTION_CALL = 'function_call'
MSG_FUNCTION_RESPONSE = 'function_response'
MSG_INTERRUPTED = 'interrupted'

# --- Constants for Error Types ---
ERROR_TYPE_QUOTA = 'quota_exceeded'
ERROR_TYPE_TIMEOUT = 'timeout'
ERROR_TYPE_CONNECTION = 'connection_closed'
ERROR_TYPE_GENERAL = 'general'

# --- Constants for Mime Types ---
MIME_TYPE_AUDIO = 'audio/pcm'
MIME_TYPE_IMAGE_JPEG = 'image/jpeg'


async def send_error_message(
  websocket: websockets.WebSocketServerProtocol, error_data: Dict[str, Any]
) -> None:
  """Send formatted error message to client."""
  try:
    # Adjusted indentation for the dictionary
    await websocket.send(json.dumps({
      MSG_TYPE: MSG_ERROR,
      MSG_DATA: error_data
    }))
  except websockets.exceptions.ConnectionClosed:
    logger.info('Attempted to send error, but connection already closed.')
  except Exception as e: # pylint: disable=broad-except
    # Keep broad except here as we don't want send_error to crash the server
    logger.error('Failed to send error message: %s', e)


async def cleanup_session(
  session: Optional[SessionState], session_id: str
) -> None:
  """Clean up session resources."""
  if not session:
    logger.warning('Cleanup called for non-existent session: %s', session_id)
    return

  try:
    # Cancel any running tool execution task
    # Adjusted indentation for the condition lines
    if (
      session.current_tool_execution
      and not session.current_tool_execution.done()
    ):
      logger.debug('Cancelling tool execution task for session %s', session_id)
      session.current_tool_execution.cancel()
      try:
        await session.current_tool_execution
      except asyncio.CancelledError:
        logger.debug('Tool execution task cancelled for session %s', session_id)
      except Exception as task_err: # pylint: disable=broad-except
        # Log error during task cancellation/awaiting
        logger.error(
          'Error awaiting cancelled tool task for session %s: %s',
          session_id,
          task_err,
        )
      finally:
        session.current_tool_execution = None # Ensure it's cleared

    # Close Gemini session
    if session.genai_session:
      logger.debug('Closing Gemini session for %s', session_id)
      try:
        # Assuming genai_session has an async close method
        await session.genai_session.close()
        logger.debug('Gemini session closed for %s', session_id)
      except Exception as e: # pylint: disable=broad-except
        # Log error during Gemini session close
        logger.error('Error closing Gemini session %s: %s', session_id, e)

    # Remove session from active sessions
    remove_session(session_id)
    logger.info('Session %s cleaned up and ended', session_id)
  except Exception as cleanup_error: # pylint: disable=broad-except
    # Log any unexpected error during the cleanup process itself
    # Adjusted indentation for the continued log message
    logger.error(
      'Error during session cleanup for %s: %s', session_id, cleanup_error
    )


async def handle_messages(
  websocket: websockets.WebSocketServerProtocol, session: SessionState
) -> None:
  """Handles bidirectional message flow between client and Gemini."""
  client_task = None
  gemini_task = None

  try:
    async with asyncio.TaskGroup() as tg:
      # Task 1: Handle incoming messages from client
      client_task = tg.create_task(handle_client_messages(websocket, session))
      # Task 2: Handle responses from Gemini
      gemini_task = tg.create_task(handle_gemini_responses(websocket, session))
  # Adjusted indentation for except* lines
  except* (websockets.exceptions.ConnectionClosed,
          asyncio.CancelledError) as eg:
    # Handle expected closures gracefully
    # Adjusted indentation for the continued log message
    logger.info(
      'Connection closed or task cancelled in handle_messages: %s', eg
    )
    # Exceptions are logged within the tasks or finally block handles
    # cancellation
  except* google_exceptions.ResourceExhausted as eg:
    logger.warning('Quota exceeded during message handling: %s', eg)
    try:
      # Send error message for UI handling
      await send_error_message(
        websocket,
        {
          'message': 'Quota exceeded.',
          'action': 'Please wait a moment and try again in a few minutes.',
          'error_type': ERROR_TYPE_QUOTA,
        },
      )
      # Send text message to show in chat
      await websocket.send(
        json.dumps({
          MSG_TYPE: MSG_TEXT,
          MSG_DATA: (
            '⚠️ Quota exceeded. Please wait a moment and try again in a few'
            ' minutes.'
          ),
        })
      )
    except websockets.exceptions.ConnectionClosed:
      logger.info('Connection closed before quota message could be sent.')
    except Exception as send_err: # pylint: disable=broad-except
      logger.error('Failed to send quota error message: %s', send_err)
  except* Exception as eg: # Catch any other unexpected exceptions from tasks
    logger.error('Unhandled exception group in handle_messages: %s', eg)
    for exc in eg.exceptions:
      # Adjusted indentation for the logger call
      logger.error('Individual exception: %s', exc, exc_info=exc)
    # Optionally send a generic error message if connection is still open
    if websocket.open:
      # Adjusted indentation for the send_error_message call
      await send_error_message(
        websocket,
        {
          'message': 'An unexpected error occurred during processing.',
          'action': 'Please try restarting the connection.',
          'error_type': ERROR_TYPE_GENERAL,
        },
      )
    raise # Re-raise the group to be handled by the caller (handle_client)
  finally:
    # Ensure tasks are cancelled on exit
    for task in (client_task, gemini_task):
      if task and not task.done():
        task.cancel()
        try:
          await task
        except asyncio.CancelledError:
          pass # Expected cancellation
        except Exception as final_cancel_err: # pylint: disable=broad-except
          # Log errors during final cancellation attempt
          # Adjusted indentation for the continued log message
          logger.error(
            'Error during final task cancellation: %s', final_cancel_err
          )


async def handle_client_messages(
  websocket: websockets.WebSocketServerProtocol, session: SessionState
) -> None:
  """Handle incoming messages from the client."""
  try:
    async for message in websocket:
      try:
        data = json.loads(message)
        msg_type = data.get(MSG_TYPE)

        # Debug logging (mask audio data)
        if msg_type == MSG_AUDIO:
          logger.debug('Client -> Gemini: Sending audio data...')
        elif msg_type == MSG_IMAGE:
          logger.debug('Client -> Gemini: Sending image data...')
        else:
          debug_data_str = json.dumps(data, indent=2)
          logger.debug('Client -> Gemini: %s', debug_data_str)

        # --- Message Handling Logic ---
        if not session.genai_session:
          logger.warning('Gemini session not available, cannot send message.')
          continue

        if msg_type == MSG_AUDIO:
          logger.debug('Sending audio to Gemini...')
          await session.genai_session.send(
            input={'data': data.get(MSG_DATA), 'mime_type': MIME_TYPE_AUDIO},
            end_of_turn=True,
          )
          logger.debug('Audio sent to Gemini')
        elif msg_type == MSG_IMAGE:
          logger.info('Sending image to Gemini...')
          await session.genai_session.send(
            input={
              'data': data.get(MSG_DATA),
              'mime_type': MIME_TYPE_IMAGE_JPEG
            } # Adjusted indentation
          )
          logger.info('Image sent to Gemini')
        elif msg_type == MSG_TEXT:
          logger.info('Sending text to Gemini...')
          await session.genai_session.send(
            input=data.get(MSG_DATA), end_of_turn=True
          )
          logger.info('Text sent to Gemini')
        elif msg_type == MSG_END:
          logger.info('Received end signal from client (no action needed)')
        else:
          logger.warning('Unsupported message type received: %s', msg_type)

      except json.JSONDecodeError as e:
        logger.error('Failed to decode JSON message: %s', e)
        await send_error_message(
          websocket,
          {
            'message': 'Invalid message format received.',
            'error_type': ERROR_TYPE_GENERAL,
          },
        )
      except Exception as e: # Catch errors during individual message processing
        logger.error('Error handling client message: %s', e, exc_info=True)
        # Decide if we should send an error or just log and continue
        await send_error_message(
          websocket,
          {
            'message': 'Error processing your message.',
            'error_type': ERROR_TYPE_GENERAL,
          },
        )

  except websockets.exceptions.ConnectionClosedOK:
    logger.info('Client connection closed normally.')
  except websockets.exceptions.ConnectionClosedError as e:
    logger.warning('Client connection closed with error: %s', e)
  except asyncio.CancelledError:
    logger.info('Client message handler cancelled.')
    raise # Propagate cancellation
  except Exception as e: # Catch errors in the message iteration loop itself
    # Adjusted indentation for the continued log message
    logger.error(
      'WebSocket connection error in client handler: %s', e, exc_info=True
    )
    raise # Re-raise to be caught by handle_messages


async def handle_gemini_responses(
  websocket: websockets.WebSocketServerProtocol, session: SessionState
) -> None:
  """Handle responses from Gemini and manage tool calls."""
  tool_queue = asyncio.Queue() # Queue for tool responses

  # Start a background task to process tool calls
  tool_processor = asyncio.create_task(
    process_tool_queue(tool_queue, websocket, session)
  )

  try:
    if not session.genai_session:
      logger.error('Gemini session not available in handle_gemini_responses.')
      return # Cannot proceed without a session

    while True:
      # Assuming genai_session.receive() is an async iterator
      async for response in session.genai_session.receive():
        try:
          # Debug logging (mask audio data)
          debug_response_str = str(response)
          # Adjusted indentation for the condition lines
          if (
            'data=' in debug_response_str
            and f"mime_type='{MIME_TYPE_AUDIO}'" in debug_response_str
          ):
            parts = debug_response_str.split('data=', 1)
            if len(parts) == 2:
              data_part = parts[1]
              end_data_index = data_part.find(" mime_type='")
              if end_data_index != -1:
                # Adjusted indentation for the assignment
                debug_response_str = (
                  parts[0] + 'data=<audio data>' + data_part[end_data_index:]
                )

          logger.debug('Received response from Gemini: %s', debug_response_str)

          # If there's a tool call, add it to the queue and continue
          if response.tool_call:
            await tool_queue.put(response.tool_call)
            continue # Continue processing other responses while tool executes

          # Process server content (including audio/text) immediately
          if response.server_content:
            await process_server_content(
              websocket, session, response.server_content
            )

        except Exception as e: # Catch errors during individual response
          logger.error('Error handling Gemini response: %s', e, exc_info=True)
          # Optionally send an error message to the client
          await send_error_message(
            websocket,
            {
              'message': 'Error processing response from AI.',
              'error_type': ERROR_TYPE_GENERAL,
            },
          )
  except websockets.exceptions.ConnectionClosed:
    logger.info('Connection closed while receiving Gemini responses.')
  except asyncio.CancelledError:
    logger.info('Gemini response handler cancelled.')
    # No need to raise, finally block handles cleanup
  except Exception as e: # Catch errors in the response iteration loop
    logger.error('Error receiving from Gemini session: %s', e, exc_info=True)
    # Propagate unexpected errors
    raise
  finally:
    # Signal tool processor to finish pending items and exit
    await tool_queue.put(None) # Sentinel value to stop the processor
    if tool_processor and not tool_processor.done():
      try:
        await tool_processor # Wait for it to finish processing
      except asyncio.CancelledError:
        logger.info('Tool processor cancelled during final wait.')
      except Exception as tool_proc_err: # pylint: disable=broad-except
        logger.error('Error waiting for tool processor: %s', tool_proc_err)


async def process_tool_queue(
  queue: asyncio.Queue,
  websocket: websockets.WebSocketServerProtocol,
  session: SessionState,
):
  """Process tool calls from the queue until a None sentinel is received."""
  while True:
    tool_call = await queue.get()
    if tool_call is None: # Sentinel check
      logger.info('Tool processor received sentinel, exiting.')
      queue.task_done()
      break

    logger.debug('Processing tool call: %s', tool_call)
    original_task = asyncio.current_task() # Reference to this task
    try:
      function_responses = []
      for function_call in tool_call.function_calls:
        # Store the tool execution task in session state
        session.current_tool_execution = original_task

        try:
          # Send function call to client (for UI feedback)
          await websocket.send(
            json.dumps({
              MSG_TYPE: MSG_FUNCTION_CALL,
              MSG_DATA: {
                'name': function_call.name,
                'args': function_call.args,
              },
            })
          )
          logger.debug(
            'Calling execute_tool with name: %s args: %s',
            function_call.name,
            function_call.args,
          )
          # --- Execute the actual tool ---
          tool_result = await execute_tool(
            function_call.name, function_call.args
          )
          # --- Tool execution finished ---

          # Send function response back to client
          await websocket.send(
            json.dumps({
              MSG_TYPE: MSG_FUNCTION_RESPONSE,
              MSG_DATA: tool_result,
            })
          )

          # Prepare response for Gemini
          function_responses.append(
            types.FunctionResponse(
              name=function_call.name, id=function_call.id, response=tool_result
            )
          )
        except asyncio.CancelledError:
          logger.info('Tool execution cancelled for %s', function_call.name)
          # If cancelled, we might not want to send a response to Gemini
          # Or send a specific error response
          raise # Re-raise cancellation
        except Exception as exec_err: # Catch errors during single func call
          # Adjusted indentation for the continued log message
          logger.error(
            'Error executing tool %s: %s',
            function_call.name,
            exec_err,
            exc_info=True,
          )
          # Send error back to client
          await send_error_message(
            websocket,
            {
              'message': f'Error executing tool: {function_call.name}',
              'details': str(exec_err),
              'error_type': ERROR_TYPE_GENERAL,
            },
          )
          # Prepare an error response for Gemini? Or skip?
          # For now, let's skip sending a FunctionResponse on error.
          # function_responses.append(types.FunctionResponse(... error
          # indicator ...))
        finally:
          # Clear the reference once this function call is done or cancelled
          # Adjusted indentation for the condition
          if session.current_tool_execution is original_task:
            session.current_tool_execution = None


      # Send collected responses back to Gemini if any were successful
      if function_responses and session.genai_session:
        tool_response = types.LiveClientToolResponse(
          function_responses=function_responses
        )
        logger.debug('Sending tool response to Gemini: %s', tool_response)
        await session.genai_session.send(input=tool_response)

    except asyncio.CancelledError:
      logger.info('Tool processing task cancelled.')
      # Ensure session state is cleared if cancelled mid-processing
      # Adjusted indentation for the condition
      if session.current_tool_execution is original_task:
        session.current_tool_execution = None
      break # Exit loop on cancellation
    except Exception as e: # Catch errors in the overall tool_call processing
      logger.error('Error processing tool call batch: %s', e, exc_info=True)
      # Ensure session state is cleared on unexpected error
      # Adjusted indentation for the condition
      if session.current_tool_execution is original_task:
        session.current_tool_execution = None
    finally:
      queue.task_done() # Mark the item (tool_call or None) as processed


async def process_server_content(
  websocket: websockets.WebSocketServerProtocol,
  session: SessionState,
  server_content: types.GenerateContentResponse, # More specific type
):
  """Process server content including audio, text, and interruption."""
  # Check for interruption first (using direct attribute access)
  if server_content.interrupted:
    logger.info('Interruption detected from Gemini')
    await websocket.send(
      json.dumps({
        MSG_TYPE: MSG_INTERRUPTED,
        MSG_DATA: {'message': 'Response interrupted by user input'},
      })
    )
    session.is_receiving_response = False
    return

  if server_content.model_turn:
    # Adjusted indentation for the continued log message
    logger.debug(
      'Processing model turn response from Gemini: %s',
      server_content.model_turn,
    )
    session.received_model_response = True
    session.is_receiving_response = True

    if server_content.model_turn.parts: # Check parts list is not empty/None
      for part in server_content.model_turn.parts:
        # Adjusted indentation for the condition
        if part.inline_data and part.inline_data.mime_type == MIME_TYPE_AUDIO:
          # Send audio data
          # Adjusted indentation for the assignment
          audio_base64 = base64.b64encode(
            part.inline_data.data
          ).decode('utf-8')
          await websocket.send(
            json.dumps({MSG_TYPE: MSG_AUDIO, MSG_DATA: audio_base64})
          )
        elif part.text:
          # Send text data
          await websocket.send(
            json.dumps({MSG_TYPE: MSG_TEXT, MSG_DATA: part.text})
          )
        # Add handling for other part types if necessary

  if server_content.turn_complete:
    logger.debug('Received turn_complete from Gemini')
    await websocket.send(json.dumps({MSG_TYPE: MSG_TURN_COMPLETE}))
    session.received_model_response = False
    session.is_receiving_response = False


async def handle_client(websocket: websockets.WebSocketServerProtocol) -> None:
  """Handles a new client connection, session creation, and cleanup."""
  session_id = str(id(websocket))
  session: Optional[SessionState] = None # Initialize session as None

  try:
    session = create_session(session_id)
    logger.info('Created new session state for ID: %s', session_id)

    # Create and initialize Gemini session (using async context manager)
    # Assuming create_gemini_session returns an async context manager
    async with await create_gemini_session() as gemini_session:
      session.genai_session = gemini_session
      logger.info('Gemini session initialized for session ID: %s', session_id)

      # Send ready message to client
      await websocket.send(json.dumps({MSG_READY: True}))
      logger.info('Sent ready message to client for session: %s', session_id)

      # Start the main message handling loop
      await handle_messages(websocket, session)

  except websockets.exceptions.ConnectionClosedOK:
    logger.info('Client %s disconnected normally.', session_id)
  except websockets.exceptions.ConnectionClosedError as e:
    logger.warning('Client %s connection closed with error: %s', session_id, e)
  except asyncio.CancelledError:
    logger.info('handle_client task cancelled for session %s.', session_id)
  except asyncio.TimeoutError:
    # This might occur if create_gemini_session times out
    # Adjusted indentation for the continued log message
    logger.warning(
      'Timeout occurred during client handling (session %s)', session_id
    )
    await send_error_message(
      websocket,
      {
        'message': 'Session setup timed out.',
        'action': 'Please try reconnecting.',
        'error_type': ERROR_TYPE_TIMEOUT,
      },
    )
  except google_exceptions.ResourceExhausted as e:
    # Catch quota errors specifically during initial session setup if possible
    # Adjusted indentation for the continued log message
    logger.warning(
      'Quota exceeded during session setup for %s: %s', session_id, e
    )
    await send_error_message(
      websocket,
      {
        'message': 'Quota exceeded during setup.',
        'action': 'Please wait and try again.',
        'error_type': ERROR_TYPE_QUOTA,
      },
    )
  except Exception as e:
    # Catch-all for unexpected errors during setup or
    # handle_messages propagation
    # Adjusted indentation for the continued log message
    logger.error(
      'Unhandled error in handle_client for session %s: %s',
      session_id,
      e,
      exc_info=True,
    )
    # Send generic error if connection is still open
    if websocket.open:
      await send_error_message(
        websocket,
        {
          'message': 'An unexpected server error occurred.',
          'action': 'Please try reconnecting or contact support.',
          'error_type': ERROR_TYPE_GENERAL,
        },
      )
  finally:
    # Always ensure cleanup happens, passing the potentially None session
    logger.info('Initiating cleanup for session: %s', session_id)
    await cleanup_session(session, session_id)
