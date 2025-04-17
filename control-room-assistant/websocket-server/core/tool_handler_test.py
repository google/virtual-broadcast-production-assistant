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
import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock

# Import necessary components from aiohttp and local modules
from aiohttp import ClientResponse
from google.cloud import secretmanager  # pylint: disable=unused-import

# Import items under test and configuration
from core.tool_handler import execute_tool
from config.config import (
  ConfigurationError,
  ApiConfig,
  get_secret,
)


# Test class for the execute_tool function
class TestExecuteTool:
  """Tests for the execute_tool function."""

  @pytest.fixture(autouse=True)
  def setup_tools(self, monkeypatch):
    """Set up a mock TOOLS dictionary for each test."""
    # Setup a TOOLS dict for testing
    test_tools = {
      'test_tool': 'http://test-tool.com/api',
      'test_tool2': 'http://test-tool2.com/api/',
    }
    # Use monkeypatch to modify the global TOOLS dictionary safely
    # Target the TOOLS dict within the config.config module
    tools_module = __import__('config.config').config.TOOLS
    monkeypatch.setitem(tools_module, 'clear', lambda: None)
    monkeypatch.setitem(tools_module, 'update',
      lambda d: test_tools.update(d)) # pylint: disable=unnecessary-lambda
    tools_module.clear()
    tools_module.update(test_tools)


  async def mock_response(self, status, text, json_data=None):
    """Create a mock aiohttp ClientResponse."""
    mock_resp = AsyncMock(spec=ClientResponse)
    mock_resp.status = status
    # Use asyncio.create_task for setting future results immediately
    mock_resp.text.return_value = asyncio.create_task(
      asyncio.sleep(0, result=text)
    )
    mock_resp.json.return_value = asyncio.create_task(
      asyncio.sleep(0, result=json_data)
    )
    # If json_data is None, make json() raise an error like aiohttp does
    if json_data is None:
      mock_resp.json.side_effect = Exception('Mocked JSON decode error')
    return mock_resp

  @pytest.mark.asyncio
  @patch('aiohttp.ClientSession.get')
  async def test_execute_tool_success(self, mock_get):
    """Test successful execution of a tool without parameters."""
    # Mock a successful response
    mock_resp = await self.mock_response(
      200, '{"success": true}', {'success': True}
    )
    mock_get.return_value.__aenter__.return_value = mock_resp

    result = await execute_tool('test_tool', {})
    assert result == {'success': True}
    mock_get.assert_called_once_with('http://test-tool.com/api')


  @pytest.mark.asyncio
  @patch('aiohttp.ClientSession.get')
  async def test_execute_tool_success_with_path_and_params(self, mock_get):
    """Test successful execution with path and query parameters."""
    # Mock a successful response
    mock_resp = await self.mock_response(
      200, '{"success": true}', {'success': True}
    )
    mock_get.return_value.__aenter__.return_value = mock_resp

    result = await execute_tool(
      'test_tool', {'path': '/resource', 'param1': 'value1'}
    )
    assert result == {'success': True}
    mock_get.assert_called_once_with(
      'http://test-tool.com/api/resource?param1=value1'
    )

  @pytest.mark.asyncio
  @patch('aiohttp.ClientSession.get')
  async def test_execute_tool_success_with_path_no_params(self, mock_get):
    """Test successful execution with only a path parameter."""
    # Mock a successful response
    mock_resp = await self.mock_response(
      200, '{"success": true}', {'success': True}
    )
    mock_get.return_value.__aenter__.return_value = mock_resp

    result = await execute_tool('test_tool', {'path': '/resource'})
    assert result == {'success': True}
    mock_get.assert_called_once_with('http://test-tool.com/api/resource')

  @pytest.mark.asyncio
  @patch('aiohttp.ClientSession.get')
  async def test_execute_tool_success_with_path_slash_and_params(
    self, mock_get
  ):
    """Test success when base URL ends with / and path/params are added."""
    # Mock a successful response
    mock_resp = await self.mock_response(
      200, '{"success": true}', {'success': True}
    )
    mock_get.return_value.__aenter__.return_value = mock_resp

    result = await execute_tool(
      'test_tool2', {'path': '/resource', 'param1': 'value1'}
    )
    assert result == {'success': True}
    mock_get.assert_called_once_with(
      'http://test-tool2.com/api/resource?param1=value1'
    )

  @pytest.mark.asyncio
  @patch('aiohttp.ClientSession.get')
  async def test_execute_tool_success_with_path_slash_no_params(
    self, mock_get
  ):
    """Test success when base URL ends with / and only path is added."""
    # Mock a successful response
    mock_resp = await self.mock_response(
      200, '{"success": true}', {'success': True}
    )
    mock_get.return_value.__aenter__.return_value = mock_resp

    result = await execute_tool('test_tool2', {'path': '/resource'})
    assert result == {'success': True}
    mock_get.assert_called_once_with('http://test-tool2.com/api/resource')

  @pytest.mark.asyncio
  @patch('aiohttp.ClientSession.get')
  async def test_execute_tool_failure_status(self, mock_get):
    """Test handling of non-200 status code from the tool endpoint."""
    # Mock a failed response
    mock_resp = await self.mock_response(500, 'Internal Server Error')
    mock_get.return_value.__aenter__.return_value = mock_resp

    result = await execute_tool('test_tool', {})
    assert result == {'error': 'Cloud function returned status 500'}

  @pytest.mark.asyncio
  @patch('aiohttp.ClientSession.get')
  async def test_execute_tool_invalid_json(self, mock_get):
    """Test handling of non-JSON response from the tool endpoint."""
    # Mock a response with invalid JSON (status 200 but bad body)
    # Pass text but no json_data to mock_response
    mock_resp = await self.mock_response(200, 'invalid json')
    mock_get.return_value.__aenter__.return_value = mock_resp

    result = await execute_tool('test_tool', {})
    # Check if the error message contains the expected substring
    assert 'Invalid JSON response' in result.get('error', '')


  @pytest.mark.asyncio
  @patch('aiohttp.ClientSession.get')
  async def test_execute_tool_connection_error(self, mock_get):
    """Test handling of network errors when calling the tool endpoint."""
    # Mock a connection error by raising an exception
    mock_get.side_effect = Exception('Connection error')

    result = await execute_tool('test_tool', {})
    assert 'Failed to call cloud function' in result.get('error', '')

  @pytest.mark.asyncio
  async def test_execute_tool_unknown_tool(self):
    """Test handling when the requested tool name is not configured."""
    result = await execute_tool('unknown_tool', {})
    assert result == {'error': 'Unknown tool: unknown_tool'}

  # --- Tests for config functions (consider moving to a separate file) ---

  @pytest.mark.asyncio
  @patch.dict(os.environ, {'PROJECT_ID': 'test-project'})
  @patch(
    'google.cloud.secretmanager.SecretManagerServiceClient'
    '.access_secret_version' # Wrapped patch target
  )
  async def test_get_secret_success(self, mock_access_secret):
    """Test successful retrieval of a secret from Secret Manager."""
    # Mock the secret manager response
    mock_payload = AsyncMock()
    mock_payload.data = b'test_secret_value'
    mock_response = AsyncMock()
    mock_response.payload = mock_payload
    # Configure the mock method to return the mock response
    mock_access_secret.return_value = mock_response

    secret = get_secret('test_secret')
    assert secret == 'test_secret_value'
    # Verify the call arguments
    expected_name = ( # Wrapped assignment
      'projects/test-project/secrets/test_secret/versions/latest'
    )
    mock_access_secret.assert_called_once_with(name=expected_name)


  @pytest.mark.asyncio
  @patch.dict(os.environ, {'PROJECT_ID': 'test-project'})
  @patch(
    'google.cloud.secretmanager.SecretManagerServiceClient'
    '.access_secret_version' # Wrapped patch target
  )
  async def test_get_secret_failure(self, mock_access_secret):
    """Test handling of errors during secret retrieval."""
    # Configure the mock method to raise an exception
    mock_access_secret.side_effect = Exception('Secret access failed')

    with pytest.raises(Exception, match='Secret access failed'):
      get_secret('test_secret')

  @pytest.mark.asyncio
  @patch.dict(os.environ, clear=True)  # Clear environment variables
  async def test_get_secret_missing_project_id(self):
    """Test that ConfigurationError is raised if PROJECT_ID is missing."""
    # Wrapped match string
    expected_error_msg = 'PROJECT_ID environment variable is not set'
    with pytest.raises(ConfigurationError, match=expected_error_msg):
      get_secret('test_secret')

  @pytest.mark.asyncio
  @patch('config.config.get_secret')
  @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key'}, clear=True)
  async def test_api_config_initialise_development_env_var(
    self, mock_get_secret
  ):
    """Test ApiConfig initialization using GOOGLE_API_KEY env var."""
    api_config = ApiConfig()
    api_config.use_vertex = False  # Explicitly set for clarity
    await api_config.initialize()
    assert api_config.api_key == 'test_api_key'
    # Ensure get_secret was NOT called when env var is present
    mock_get_secret.assert_not_called()


  @pytest.mark.asyncio
  @patch('config.config.get_secret')
  @patch.dict(os.environ, clear=True)  # Clear environment variables
  async def test_api_config_initialise_development_secret_manager(
    self, mock_get_secret
  ):
    """Test ApiConfig initialization using Secret Manager for the key."""
    # Mock get_secret to return a value
    mock_get_secret.return_value = 'test_api_key_from_secret_manager'
    api_config = ApiConfig()
    api_config.use_vertex = False  # Explicitly set for clarity
    await api_config.initialize()
    assert api_config.api_key == 'test_api_key_from_secret_manager'
    # Ensure get_secret was called with the correct key
    mock_get_secret.assert_called_once_with('GOOGLE_API_KEY')

  @pytest.mark.asyncio
  # Test case where neither env var nor secret manager provides the key
  @patch('config.config.get_secret')
  @patch.dict(os.environ, clear=True) # Ensure GOOGLE_API_KEY is not set
  async def test_api_config_initialise_development_no_key(
      self, mock_get_secret):
    """Test ApiConfig raises error if no API key is found."""
    # Mock get_secret to simulate failure (e.g., returns None or raises)
    mock_get_secret.side_effect = Exception('Secret not found') # Or return None
    api_config = ApiConfig()
    api_config.use_vertex = False
    # Wrapped match string
    expected_error_msg = (
      'No API key available from Secret Manager or environment.'
    )
    with pytest.raises(ConfigurationError, match=expected_error_msg):
      await api_config.initialize()
    # Verify get_secret was called
    mock_get_secret.assert_called_once_with('GOOGLE_API_KEY')
