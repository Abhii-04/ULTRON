import unittest

from langchain_core.messages import AIMessage

from src.subgraphs.linkedin_agent import LinkedinAgent, handle_tool_error


class LinkedinAgentTests(unittest.TestCase):
    def test_routes_to_tools_when_model_returns_tool_call(self):
        agent = LinkedinAgent()
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_jobs",
                            "args": {"keywords": "AI"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                )
            ]
        }

        self.assertEqual(agent.linkedin_agent_router(state), "tools")

    def test_routes_to_end_when_model_returns_final_answer(self):
        agent = LinkedinAgent()
        state = {
            "messages": [
                AIMessage(content="Found matching LinkedIn jobs.")
            ]
        }

        self.assertEqual(agent.linkedin_agent_router(state), "__end__")

    def test_formats_linkedin_tool_error(self):
        self.assertEqual(
            handle_tool_error(ValueError("bad input")),
            "LinkedIn MCP tool call failed: ValueError: bad input",
        )


if __name__ == "__main__":
    unittest.main()
