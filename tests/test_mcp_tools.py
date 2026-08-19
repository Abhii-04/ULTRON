import json
import unittest

from src.tools.mcp import LINKEDIN_JOB_TEXT_LIMIT, trim_linkedin_search_output


class MCPToolTests(unittest.TestCase):
    def test_trims_each_linkedin_search_job_to_80_characters(self):
        result = {
            "job_ids": ["1", "2"],
            "references": {
                "search_results": [
                    {
                        "kind": "job",
                        "text": "Senior Artificial Intelligence Engineer",
                        "url": "https://www.linkedin.com/jobs/view/123456789",
                    },
                    {
                        "kind": "job",
                        "text": "Machine Learning Intern",
                        "url": "https://www.linkedin.com/jobs/view/987654321",
                    },
                ]
            },
        }

        trimmed = trim_linkedin_search_output(result)

        self.assertEqual(trimmed["job_ids"], ["1", "2"])
        self.assertEqual(len(trimmed["jobs"]), 2)
        for job in trimmed["jobs"]:
            self.assertLessEqual(len(job["job"]), LINKEDIN_JOB_TEXT_LIMIT)

    def test_trims_text_content_blocks_from_mcp_results(self):
        result = [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "references": {
                            "search_results": [
                                {
                                    "kind": "job",
                                    "text": "Entry Level AI Research Assistant",
                                    "url": "https://www.linkedin.com/jobs/view/123",
                                }
                            ]
                        }
                    }
                ),
            }
        ]

        trimmed = trim_linkedin_search_output(result)

        self.assertEqual(len(trimmed["jobs"]), 1)
        self.assertLessEqual(
            len(trimmed["jobs"][0]["job"]),
            LINKEDIN_JOB_TEXT_LIMIT,
        )

    def test_trims_direct_jobs_array(self):
        result = {
            "jobs": [
                {
                    "title": "Very Long Entry Level Artificial Intelligence Role",
                    "job_url": "https://www.linkedin.com/jobs/view/123456789",
                }
            ]
        }

        trimmed = trim_linkedin_search_output(result)

        self.assertEqual(len(trimmed["jobs"]), 1)
        self.assertLessEqual(
            len(trimmed["jobs"][0]["job"]),
            LINKEDIN_JOB_TEXT_LIMIT,
        )


if __name__ == "__main__":
    unittest.main()
