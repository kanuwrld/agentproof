import unittest

from agentproof.core import SuiteFormatError, evaluate_suite


class EvaluateSuiteTests(unittest.TestCase):
    def test_passes_supported_assertions(self) -> None:
        result = evaluate_suite(
            {
                "suite": "support",
                "cases": [
                    {
                        "id": "billing-refund",
                        "actual": {
                            "category": "billing",
                            "draft": "We can review your refund request.",
                            "citations": [{"id": "policy-7"}],
                        },
                        "metrics": {"latency_ms": 420, "cost_usd": 0.003},
                        "assert": {
                            "required": ["draft", "citations.0.id"],
                            "equals": {"category": "billing"},
                            "contains": {"draft": ["refund", "review"]},
                            "matches": {"citations.0.id": "^policy-"},
                            "forbidden": ["(?i)password", "sk-[A-Za-z0-9]+"],
                            "max_latency_ms": 500,
                            "max_cost_usd": 0.01,
                        },
                    }
                ],
            }
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.passed_count, 1)

    def test_reports_missing_path_value_and_budget(self) -> None:
        result = evaluate_suite(
            {
                "suite": "regression",
                "cases": [
                    {
                        "id": "bad-output",
                        "actual": {"category": "other", "draft": "API_KEY=secret"},
                        "metrics": {"latency_ms": 900},
                        "assert": {
                            "required": ["citations"],
                            "equals": {"category": "billing"},
                            "forbidden": ["(?i)api_key"],
                            "max_latency_ms": 500,
                            "max_cost_usd": 0.01,
                        },
                    }
                ],
            }
        )
        self.assertFalse(result.passed)
        messages = [check.message for check in result.cases[0].checks if not check.passed]
        self.assertEqual(len(messages), 5)
        self.assertTrue(any("missing path" in message for message in messages))
        self.assertTrue(any("forbidden pattern found" in message for message in messages))

    def test_rejects_duplicate_case_ids(self) -> None:
        with self.assertRaisesRegex(SuiteFormatError, "duplicate case id"):
            evaluate_suite(
                {
                    "suite": "duplicates",
                    "cases": [
                        {"id": "same", "actual": {}},
                        {"id": "same", "actual": {}},
                    ],
                }
            )

    def test_rejects_invalid_regex(self) -> None:
        with self.assertRaisesRegex(SuiteFormatError, "invalid regex"):
            evaluate_suite(
                {
                    "suite": "regex",
                    "cases": [
                        {"id": "broken", "actual": {}, "assert": {"forbidden": ["("]}}
                    ],
                }
            )


if __name__ == "__main__":
    unittest.main()
