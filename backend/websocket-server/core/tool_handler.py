"""
Tool execution and handling for Gemini Multimodal Live Proxy Server
"""

import logging
import aiohttp
from typing import Dict, Any
from config.config import CLOUD_FUNCTIONS
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool based on name and parameters by calling the corresponding cloud function"""
    try:
        if tool_name not in CLOUD_FUNCTIONS:
            logger.error(f"Tool not found: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

        base_url = CLOUD_FUNCTIONS[tool_name]
        # Convert params to URL query parameters
        query_string = urlencode(params)
        function_url = f"{base_url}?{query_string}" if params else base_url
        
        logger.debug(f"Calling cloud function for {tool_name}")
        logger.debug(f"URL with params: {function_url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(function_url) as response:
                response_text = await response.text()
                logger.debug(f"Response status: {response.status}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response body: {response_text}")
                
                if response.status != 200:
                    logger.error(f"Cloud function error: {response_text}")
                    return {"error": f"Cloud function returned status {response.status}"}
                
                try:
                    return await response.json()
                except Exception as e:
                    logger.error(f"Failed to parse JSON response: {response_text}")
                    return {"error": f"Invalid JSON response from cloud function: {str(e)}"}

    except aiohttp.ClientError as e:
        logger.error(f"Network error calling cloud function for {tool_name}: {str(e)}")
        return {"error": f"Failed to call cloud function: {str(e)}"}
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        return {"error": f"Tool execution failed: {str(e)}"} 