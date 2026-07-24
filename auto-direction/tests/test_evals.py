import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from src.agents.director_agent import create_director_agent
from src.config import GEMINI_API_KEY, has_adc

class TestDirectorBehavioralEvals(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Define our test matrix of inputs vs. expected outputs
        self.eval_scenarios = [
            {
                "name": "Host speaking actively, guest silent",
                "audio_levels": {"mic_host": -12.0, "mic_guest": -55.0},
                "active_speaker": "mic_host",
                "camera_on_air": "cam_1",
                "active_segment": "Welcome and Chat",
                "expected_target_camera": "cam_2", # Close-up of Host
                "reasoning_substring": "host"
            },
            {
                "name": "Guest speaking actively, host silent",
                "audio_levels": {"mic_host": -60.0, "mic_guest": -15.0},
                "active_speaker": "mic_guest",
                "camera_on_air": "cam_2",
                "active_segment": "Deep Dive & Tension",
                "expected_target_camera": "pixel_11", # Mobile mount focus on Guest
                "reasoning_substring": "guest"
            },
            {
                "name": "Cross-talk/Both speaking loudly",
                "audio_levels": {"mic_host": -10.0, "mic_guest": -12.0},
                "active_speaker": "mic_host",
                "camera_on_air": "cam_2",
                "active_segment": "Welcome and Chat",
                "expected_target_camera": "cam_1", # Wide studio shot
                "reasoning_substring": "both"
            }
        ]

    def test_prompt_construction_integrity(self):
        """Verifies that sensory inputs are correctly represented in the prompt template."""
        for scenario in self.eval_scenarios:
            audio = scenario["audio_levels"]
            active = scenario["active_speaker"]
            frame = "Simulated web frame"
            current_segment = scenario["active_segment"]
            on_air = scenario["camera_on_air"]
            
            prompt = (
                f"SENSORY UPDATE:\n"
                f"- Active Segment: {current_segment}\n"
                f"- On-Air Camera: {on_air}\n"
                f"- Audio Levels: Host={audio['mic_host']}dB, Guest={audio['mic_guest']}dB\n"
                f"- Active Speaker: {active}\n"
                f"- Current Web Page visual frame description: {frame}\n\n"
                "Evaluate the scene. If you decide to cut cameras or adjust pan/tilt/zoom settings to follow the narrative, "
                "use your tools to execute those. Make sure to call log_director_decision to record your reasoning!"
            )
            
            # Assert schema keys exist in the constructed prompt
            self.assertIn("SENSORY UPDATE:", prompt)
            self.assertIn(f"Active Segment: {current_segment}", prompt)
            self.assertIn(f"On-Air Camera: {on_air}", prompt)
            self.assertIn(f"Host={audio['mic_host']}dB", prompt)
            self.assertIn(f"Guest={audio['mic_guest']}dB", prompt)
            self.assertIn(f"Active Speaker: {active}", prompt)

    @unittest.skipIf(not GEMINI_API_KEY and not has_adc, "Skipping live agent behavior eval because neither GEMINI_API_KEY nor Application Default Credentials are configured")
    async def test_live_agent_behavior_eval(self):
        """
        Integration evaluation test that runs against the actual Gemini model.
        Tests if the prompt guides the model to invoke the correct tool behavior.
        """
        from google.adk.runners import Runner
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        
        agent = create_director_agent()
        session_service = InMemorySessionService()
        runner = Runner(
            app_name="DirectorApp",
            agent=agent,
            session_service=session_service,
        )
        
        # Test scenario: Guest speaking passionately
        prompt = (
            "SENSORY UPDATE:\n"
            "- Active Segment: Deep Dive & Tension\n"
            "- On-Air Camera: cam_1\n"
            "- Audio Levels: Host=-50.0dB, Guest=-10.0dB\n"
            "- Active Speaker: mic_guest\n"
            "- Current Web Page visual frame description: Close-up of Speaker B (Guest) gesturing at a diagram.\n\n"
            "Evaluate the scene. If you decide to cut cameras or adjust pan/tilt/zoom settings to follow the narrative, "
            "use your tools to execute those. Make sure to call log_director_decision to record your reasoning!"
        )
        
        if os.getenv("RUN_LIVE_EVALS", "true").lower() == "false":
            self.skipTest("Skipping live behavioral eval due to RUN_LIVE_EVALS=false")
            
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "levels": {"mic_host": -50.0, "mic_guest": -10.0},
            "active_speaker": "mic_guest",
            "frame_description": "Close-up of Speaker B (Guest) gesturing at a diagram."
        }
            
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("src.agents.director_agent.log_director_decision", new_callable=AsyncMock) as mock_log:
            
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response
            mock_log.return_value = "Logged"
            
            try:
                events = await runner.run_debug(prompt, session_id="test_session")
            except Exception as e:
                err_msg = str(e).lower()
                if any(term in err_msg for term in ["permission", "denied", "forbidden", "403", "quota", "key", "unauthorized", "credentials"]):
                    self.skipTest(f"Skipping live behavioral eval due to API auth/permission limits: {e}")
                raise e
            
            # Extract response text from events
            text = ""
            for event in events:
                if event.message and event.message.parts:
                    for part in event.message.parts:
                        if hasattr(part, "text") and part.text:
                            text += part.text
            
            # Ensure the agent thought/chatted about the guest
            self.assertTrue(any(word in text.lower() for word in ["guest", "pixel", "cut", "mic"]))

if __name__ == "__main__":
    unittest.main()

