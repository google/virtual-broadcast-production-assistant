# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Vertex AI Gemini Multimodal Live Proxy Server with Tool Support.

Uses Python SDK for communication with Gemini API.
"""

import logging
import asyncio
import os

import websockets

from core.websocket_handler import handle_client

# Configure logging
logging.basicConfig(
  level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper()),
  format='%(asctime)s - %(levelname)s - %(message)s',
  datefmt='%Y-%m-%d %H:%M:%S',
)

# Suppress noisy third-party logs while keeping application debug messages
for logger_name in [
  'google',
  'google.auth',
  'google.auth.transport',
  'google.auth.transport.requests',
  'urllib3.connectionpool',
  'google.generativeai',
  'websockets.client',
  'websockets.protocol',
  'httpx',
  'httpcore',
]:
  logging.getLogger(logger_name).setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# Define port as a constant
PORT = 8081


async def main() -> None:
  """Starts the WebSocket server."""
  # Use the constant PORT
  async with websockets.serve(
    handle_client,
    '0.0.0.0',  # Changed to single quotes
    PORT,
    ping_interval=30,
    ping_timeout=10,
  ):
    # Changed to single quotes, using double inside for the format specifier
    logger.info('Running websocket server on 0.0.0.0:%s...', PORT)
    await asyncio.Future()  # run forever


if __name__ == '__main__':  # Changed to single quotes
  asyncio.run(main())
