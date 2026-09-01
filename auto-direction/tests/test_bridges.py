import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.bridges.cuez_automator_mcp import app as cuez_app, state as cuez_state
from src.bridges.webmcp_bridge import app as shure_app, shure_state
import src.bridges.cuez_automator_mcp as cuez_bridge
import src.bridges.webmcp_bridge as shure_bridge

class TestCuezBridgeEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(cuez_app)
        # Reset state before each test
        cuez_state.active_segment = "Intro Bumper"
        cuez_state.camera_on_air = "cam_1"
        cuez_state.overlays = {}
        cuez_state.ptz_positions = {
            "cam_1": {"pan": 0.0, "tilt": 0.0, "zoom": 1.0},
            "cam_2": {"pan": 0.0, "tilt": 0.0, "zoom": 1.0},
            "pixel_11": {"pan": 0.0, "tilt": 0.0, "zoom": 1.0},
        }

    def test_get_state(self):
        response = self.client.get("/state")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["active_segment"], "Intro Bumper")
        self.assertEqual(data["camera_on_air"], "cam_1")

    def test_get_rundown(self):
        response = self.client.get("/rundown")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(seg["title"] == "Welcome and Chat" for seg in data))

    def test_set_segment(self):
        response = self.client.post("/set-segment", params={"segment_title": "Deep Dive & Tension"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(cuez_state.active_segment, "Deep Dive & Tension")

    def test_trigger_graphics(self):
        payload = {
            "overlay_id": "lower_third_1",
            "text_title": "Guest Name",
            "text_subtitle": "Norsk Streaming Expert"
        }
        response = self.client.post("/trigger-graphics", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("lower_third_1", cuez_state.overlays)
        self.assertEqual(cuez_state.overlays["lower_third_1"], "Guest Name - Norsk Streaming Expert")

    def test_cut_to_source_valid(self):
        response = self.client.post("/cut-to-source", params={"source_id": "pixel_11"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(cuez_state.camera_on_air, "pixel_11")

    def test_cut_to_source_invalid(self):
        response = self.client.post("/cut-to-source", params={"source_id": "invalid_cam"})
        self.assertEqual(response.status_code, 400)

    def test_ptz_valid(self):
        payload = {"camera_id": "cam_2", "pan": 45.0, "tilt": -10.0, "zoom": 2.5}
        response = self.client.post("/ptz", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(cuez_state.ptz_positions["cam_2"], {"pan": 45.0, "tilt": -10.0, "zoom": 2.5})

    def test_ptz_invalid(self):
        payload = {"camera_id": "invalid_cam", "pan": 45.0, "tilt": -10.0, "zoom": 2.5}
        response = self.client.post("/ptz", json=payload)
        self.assertEqual(response.status_code, 400)


class TestShureBridgeEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(shure_app)
        # Reset state before each test
        shure_state.active_speaker = "mic_host"
        shure_state.web_page_frame = "A podcast studio wide shot."

    def test_get_audio_levels(self):
        response = self.client.get("/audio")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("levels", data)
        self.assertIn("mic_host", data["levels"])
        self.assertIn("mic_guest", data["levels"])
        self.assertEqual(data["active_speaker"], "mic_host")

    def test_set_active_speaker_valid(self):
        response = self.client.post("/set-active-speaker", params={"speaker_id": "mic_guest"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(shure_state.active_speaker, "mic_guest")
        self.assertIn("Speaker B (Guest)", shure_state.web_page_frame)

    def test_set_active_speaker_invalid(self):
        response = self.client.post("/set-active-speaker", params={"speaker_id": "invalid_speaker"})
        self.assertEqual(response.status_code, 400)

    def test_get_browser_frame(self):
        response = self.client.get("/browser-frame")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["browser_tab_title"], "Shure Agentic Podcast Mixer")
        self.assertEqual(data["url"], "https://shure.web-mcp.studio/live")


class TestClientHelperFunctions(unittest.IsolatedAsyncioTestCase):
    """
    Tests the client functions imported as tools by the ADK Agents.
    Uses patching to guarantee zero network/socket I/O occurs.
    """
    @patch("httpx.AsyncClient.get")
    async def test_cuez_get_rundown(self, mock_get):
        mock_resp = MagicMockResponse([{"id": "seg_1", "title": "Intro"}])
        mock_get.return_value = mock_resp
        
        result = await cuez_bridge.cuez_get_rundown()
        self.assertEqual(result, [{"id": "seg_1", "title": "Intro"}])
        mock_get.assert_called_once_with("http://localhost:8000/rundown")

    @patch("httpx.AsyncClient.post")
    async def test_cuez_set_segment(self, mock_post):
        mock_resp = MagicMockResponse({"status": "success", "active_segment": "Welcome"})
        mock_post.return_value = mock_resp
        
        result = await cuez_bridge.cuez_set_segment("Welcome")
        self.assertEqual(result["active_segment"], "Welcome")
        mock_post.assert_called_once_with("http://localhost:8000/set-segment", params={"segment_title": "Welcome"})

    @patch("httpx.AsyncClient.post")
    async def test_cuez_trigger_graphics(self, mock_post):
        mock_resp = MagicMockResponse({"status": "success"})
        mock_post.return_value = mock_resp
        
        result = await cuez_bridge.cuez_trigger_graphics("overlay1", "Title", "Subtitle")
        self.assertEqual(result["status"], "success")
        mock_post.assert_called_once()

    @patch("httpx.AsyncClient.post")
    async def test_cuez_cut_to_source(self, mock_post):
        mock_resp = MagicMockResponse({"status": "success", "camera_on_air": "cam_2"})
        mock_post.return_value = mock_resp
        
        result = await cuez_bridge.cuez_cut_to_source("cam_2")
        self.assertEqual(result["camera_on_air"], "cam_2")
        mock_post.assert_called_once_with("http://localhost:8000/cut-to-source", params={"source_id": "cam_2"})

    @patch("httpx.AsyncClient.post")
    async def test_cuez_adjust_camera(self, mock_post):
        mock_resp = MagicMockResponse({"status": "success"})
        mock_post.return_value = mock_resp
        
        result = await cuez_bridge.cuez_adjust_camera("cam_1", 10.0, -5.0, 1.5)
        self.assertEqual(result["status"], "success")
        mock_post.assert_called_once()

    @patch("httpx.AsyncClient.get")
    async def test_shure_get_audio_levels(self, mock_get):
        mock_resp = MagicMockResponse({"levels": {"mic_host": -12.0}})
        mock_get.return_value = mock_resp
        
        result = await shure_bridge.shure_get_audio_levels()
        self.assertEqual(result["levels"]["mic_host"], -12.0)
        mock_get.assert_called_once_with("http://localhost:8001/audio")

    @patch("httpx.AsyncClient.post")
    async def test_shure_set_speaker_focus(self, mock_post):
        mock_resp = MagicMockResponse({"status": "success"})
        mock_post.return_value = mock_resp
        
        result = await shure_bridge.shure_set_speaker_focus("mic_guest")
        self.assertEqual(result["status"], "success")
        mock_post.assert_called_once_with("http://localhost:8001/set-active-speaker", params={"speaker_id": "mic_guest"})

    @patch("httpx.AsyncClient.get")
    async def test_shure_get_web_frame(self, mock_get):
        mock_resp = MagicMockResponse({"frame_description": "test frame"})
        mock_get.return_value = mock_resp
        
        result = await shure_bridge.shure_get_web_frame()
        self.assertEqual(result["frame_description"], "test frame")
        mock_get.assert_called_once_with("http://localhost:8001/browser-frame")


class MagicMockResponse:
    """Helper class to mock httpx.Response objects."""
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

if __name__ == "__main__":
    unittest.main()
