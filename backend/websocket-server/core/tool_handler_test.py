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
from unittest.mock import patch, AsyncMock
from aiohttp import ClientSession, ClientResponse
from core.tool_handler import execute_tool
from config.config import TOOLS, ConfigurationError, ApiConfig, get_secret
import os
from google.cloud import secretmanager
import logging

logger = logging.getLogger(__name__)

class TestExecuteTool:
    @pytest.fixture(autouse=True)
    def setup_tools(self):
        # Setup a TOOLS dict for testing
        self.tools = {
            "test_tool": "http://test-tool.com/api",
            "test_tool2": "http://test-tool2.com/api/",
        }
        TOOLS.clear()
        TOOLS.update(self.tools)
        yield
        TOOLS.clear()

    @pytest.mark.asyncio
    async def mock_response(self, status, text, json_data=None):
        mock_resp = AsyncMock(spec=ClientResponse)
        mock_resp.status = status
        mock_resp.text.return_value = asyncio.Future()
        mock_resp.text.return_value.set_result(text)
        mock_resp.json.return_value = asyncio.Future()
        if json_data:
            mock_resp.json.return_value.set_result(json_data)
        return mock_resp

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_success(self, mock_get):
        # Mock a successful response
        mock_resp = await self.mock_response(200, '{"success": true}', {"success": True})
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await execute_tool("test_tool", {})
        assert result == {"success": True}

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_success_with_path_and_params(self, mock_get):
        # Mock a successful response
        mock_resp = await self.mock_response(200, '{"success": true}', {"success": True})
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await execute_tool("test_tool", {"path": "/resource", "param1": "value1"})
        assert result == {"success": True}
        mock_get.assert_called_once_with("http://test-tool.com/api/resource?param1=value1")

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_success_with_path_no_params(self, mock_get):
        # Mock a successful response
        mock_resp = await self.mock_response(200, '{"success": true}', {"success": True})
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await execute_tool("test_tool", {"path": "/resource"})
        assert result == {"success": True}
        mock_get.assert_called_once_with("http://test-tool.com/api/resource")

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_success_with_path_slash_and_params(self, mock_get):
        # Mock a successful response
        mock_resp = await self.mock_response(200, '{"success": true}', {"success": True})
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await execute_tool("test_tool2", {"path": "/resource", "param1": "value1"})
        assert result == {"success": True}
        mock_get.assert_called_once_with("http://test-tool2.com/api/resource?param1=value1")

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_success_with_path_slash_no_params(self, mock_get):
        # Mock a successful response
        mock_resp = await self.mock_response(200, '{"success": true}', {"success": True})
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await execute_tool("test_tool2", {"path": "/resource"})
        assert result == {"success": True}
        mock_get.assert_called_once_with("http://test-tool2.com/api/resource")

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_failure_status(self, mock_get):
        # Mock a failed response
        mock_resp = await self.mock_response(500, 'Internal Server Error')
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await execute_tool("test_tool", {})
        assert result == {"error": "Cloud function returned status 500"}

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_invalid_json(self, mock_get):
        # Mock a response with invalid JSON
        mock_resp = await self.mock_response(200, 'invalid json')
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await execute_tool("test_tool", {})
        assert "Invalid JSON response from cloud function" in result["error"]

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_tool_connection_error(self, mock_get):
        # Mock a connection error
        mock_get.side_effect = Exception("Connection error")

        result = await execute_tool("test_tool", {})
        assert "Failed to call cloud function" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_tool(self):
        result = await execute_tool("unknown_tool", {})
        assert result == {"error": "Unknown tool: unknown_tool"}

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"PROJECT_ID": "test-project"})
    @patch("google.cloud.secretmanager.SecretManagerServiceClient.access_secret_version")
    async def test_get_secret_success(self, mock_access_secret):
        mock_response = AsyncMock()
        mock_response.payload.data = b"test_secret_value"
        mock_access_secret.return_value = mock_response
        secret = get_secret("test_secret")
        assert secret == "test_secret_value"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"PROJECT_ID": "test-project"})
    @patch("google.cloud.secretmanager.SecretManagerServiceClient.access_secret_version")
    async def test_get_secret_failure(self, mock_access_secret):
        mock_access_secret.side_effect = Exception("Secret access failed")
        with pytest.raises(Exception, match="Secret access failed"):
            get_secret("test_secret")

    @pytest.mark.asyncio
    @patch.dict(os.environ, clear=True)  # Clear environment variables
    async def test_get_secret_missing_project_id(self):
        with pytest.raises(ConfigurationError, match="PROJECT_ID environment variable is not set"):
            get_secret("test_secret")

    @pytest.mark.asyncio
    @patch("config.config.get_secret")
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_api_key"}, clear=True)
    async def test_api_config_initialise_development_env_var(self, mock_get_secret):
        api_config = ApiConfig()
        api_config.use_vertex = False
        await api_config.initialize()
        assert api_config.api_key == "test_api_key"

    @pytest.mark.asyncio
    @patch("config.config.get_secret")
    @patch.dict(os.environ, clear=True)  # Clear environment variables
    async def test_api_config_initialise_development_secret_manager(self, mock_get_secret):
        mock_get_secret.return_value = "test_api_key_from_secret_manager"
        api_config = ApiConfig()
        api_config.use_vertex = False
        await api_config.initialize()
        assert api_config.api_key == "test_api_key_from_secret_manager"
        mock_get_secret.assert_called_once_with("GOOGLE_API_KEY")

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_api_key"}, clear=True)
    async def test_api_config_initialise_development_no_key(self):
      api_config = ApiConfig()
      api_config.use_vertex = False
      with pytest.raises(ConfigurationError, match="No API key available from Secret Manager or environment."):
          await api_config.initialize()
