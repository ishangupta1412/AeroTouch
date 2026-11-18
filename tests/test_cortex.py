import unittest
from src.cortex.tools import CortexOSTools
from src.cortex.ollama_bridge import OllamaCortexAgent


class TestCortexSubsystem(unittest.TestCase):
    def setUp(self):
        self.tools = CortexOSTools()
        self.agent = OllamaCortexAgent()

    def test_tool_signatures_valid(self):
        # Media command validation
        res = self.tools.execute_tool_call("media_control", {"action": "volume_up"})
        self.assertEqual(res["status"], "success")

        # Unknown tool handling
        res_unknown = self.tools.execute_tool_call("fake_tool", {})
        self.assertEqual(res_unknown["status"], "error")

    def test_ollama_agent_online(self):
        online = self.agent.is_online()
        print(f"\n[Cortex Test]: Ollama Server Online = {online} | Active Model = {self.agent.active_model}")
        self.assertTrue(online)

    def test_natural_language_intent_resolution(self):
        # Send a Hinglish command to the local aerotouch-qwen model
        cmd = "bhai volume thoda badha do"
        result = self.agent.process_command(cmd)
        print(f"[Cortex Intent Test]: Prompt: '{cmd}' -> Result: {result}")
        self.assertEqual(result["status"], "success")


if __name__ == '__main__':
    unittest.main()
