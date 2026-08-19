import unittest

from src.agent import _deterministic_route_from_text


class AgentRoutingTests(unittest.TestCase):
    def test_routes_linkedin_job_prompt_to_linkedin(self):
        self.assertEqual(
            _deterministic_route_from_text("search for AI jobs in linkedin"),
            "linkedin",
        )

    def test_routes_gmail_prompt_to_gmail(self):
        self.assertEqual(
            _deterministic_route_from_text("search my gmail for invoices"),
            "gmail",
        )

    def test_leaves_general_prompt_for_llm_router(self):
        self.assertIsNone(
            _deterministic_route_from_text("write a short project update")
        )


if __name__ == "__main__":
    unittest.main()
