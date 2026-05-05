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
"""Tool execution and handling for Gemini Multimodal Live Proxy Server."""

import logging
import aiohttp
from typing import Dict, Any
from urllib.parse import urlencode

from config.config import TOOLS

logger = logging.getLogger(__name__)


async def execute_tool(
  tool_name: str, params: Dict[str, Any]
) -> Dict[str, Any]:
  """Execute a tool by calling the corresponding cloud function."""
  logger.debug('Executing tool %s with params: %s', tool_name, params)

  try:
    if tool_name not in TOOLS:
      logger.error('Tool not found: %s', tool_name)
      return {'error': f'Unknown tool: {tool_name}'}  # f-string ok here

    base_url = TOOLS[tool_name]
    function_url = base_url

    if 'path' in params:
      path = params['path']
      # If the path starts with a slash, remove it
      if path.startswith('/'):
        path = path[1:]
        params['path'] = path

      # If 'path' is present, append it to the base URL
      function_url += params['path']

      # Remove 'path' from params so it's not included in query string
      del params['path']

    # Add any remaining parameters as query string
    query_string = urlencode(params)
    if params:
      function_url = f'{function_url}?{query_string}'  # f-string ok here

    logger.info('Calling cloud function for %s', tool_name)
    logger.info('URL with params: %s', function_url)

    async with aiohttp.ClientSession() as session:
      async with session.get(function_url) as response:
        response_text = await response.text()
        logger.debug('Response status: %s', response.status)
        logger.debug('Response headers: %s', dict(response.headers))
        logger.debug('Response body: %s', response_text)

        if response.status != 200:
          logger.error('Cloud function error: %s', response_text)
          # f-string ok here
          return {'error': f'Cloud function returned status {response.status}'}

        try:
          return await response.json()
        except Exception as e:  # Keep broad except for JSON parsing
          logger.error('Failed to parse JSON response: %s', response_text)
          # f-string ok here, split for length
          error_msg = (
            f'Invalid JSON response from cloud function: {str(e)}'
          )
          return {'error': error_msg}

  except aiohttp.ClientError as e:
    logger.error(
      'Network error calling cloud function for %s: %s', tool_name, str(e)
    )
    # f-string ok here
    return {'error': f'Failed to call cloud function: {str(e)}'}
  except Exception as e:
    # Consider if more specific exceptions can be caught upstream
    logger.error('Error executing tool %s: %s', tool_name, str(e))
    # f-string ok here
    return {'error': f'Tool execution failed: {str(e)}'}
