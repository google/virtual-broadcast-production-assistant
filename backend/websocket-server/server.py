"""
Vertex AI Gemini Multimodal Live Proxy Server with Tool Support
Uses Python SDK for communication with Gemini API
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
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Suppress Google API client logs while keeping application debug messages
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

async def main() -> None:
    """Starts the WebSocket server."""
    port = 8081


    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        port,
        ping_interval=30,
        ping_timeout=10,
    ):
        logger.info("Running websocket server on 0.0.0.0:%s...", port)
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
