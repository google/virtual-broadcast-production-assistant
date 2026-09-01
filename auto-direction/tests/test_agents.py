import unittest
from google.adk.agents import Agent
from src.agents.director_agent import create_director_agent, log_director_decision, director_decision_log
from src.agents.foh_agent import create_foh_agent

class TestAgentFactories(unittest.IsolatedAsyncioTestCase):
    def test_create_director_agent(self):
        """Verifies that the Broadcast Director Agent is created with correct name, model, and registered tools."""
        agent = create_director_agent()
        self.assertIsInstance(agent, Agent)
        self.assertEqual(agent.name, "BroadcastDirector")
        # Ensure the correct tools are registered
        tool_names = [t.__name__ for t in agent.tools]
        self.assertIn("shure_get_audio_levels", tool_names)
        self.assertIn("shure_get_web_frame", tool_names)
        self.assertIn("cuez_cut_to_source", tool_names)
        self.assertIn("cuez_adjust_camera", tool_names)
        self.assertIn("log_director_decision", tool_names)

    def test_create_foh_agent(self):
        """Verifies that the Front of House Host Agent is created with correct name, model, and registered tools."""
        agent = create_foh_agent()
        self.assertIsInstance(agent, Agent)
        self.assertEqual(agent.name, "FrontOfHouseHost")
        tool_names = [t.__name__ for t in agent.tools]
        self.assertIn("get_director_decision_log", tool_names)
        self.assertIn("cuez_get_rundown", tool_names)
        self.assertIn("cuez_set_segment", tool_names)
        self.assertIn("cuez_trigger_graphics", tool_names)

    async def test_log_director_decision(self):
        """Verifies that director decisions are correctly logged and capped in memory."""
        director_decision_log.clear()
        
        # Log a single decision
        action = "Cut to cam_2"
        reason = "Acoustic spike"
        target = "cam_2"
        await log_director_decision(action, reason, target)
        
        self.assertEqual(len(director_decision_log), 1)
        self.assertEqual(director_decision_log[0]["action"], action)
        self.assertEqual(director_decision_log[0]["reason"], reason)
        self.assertEqual(director_decision_log[0]["target"], target)
        
        # Test capping of decision log to 15 items
        for i in range(20):
            await log_director_decision("Action", "Reason", "Target")
        self.assertEqual(len(director_decision_log), 15)

if __name__ == "__main__":
    unittest.main()
