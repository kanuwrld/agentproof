import json
import unittest
from xml.etree import ElementTree

from agentproof.core import evaluate_suite
from agentproof.reporters import render_json, render_junit, render_markdown


class ReporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = evaluate_suite(
            {
                "suite": "reports",
                "cases": [{"id": "ok", "actual": {"ready": True}, "assert": {"equals": {"ready": True}}}],
            }
        )

    def test_json_is_machine_readable(self) -> None:
        self.assertTrue(json.loads(render_json(self.result))["passed"])

    def test_markdown_contains_table(self) -> None:
        self.assertIn("| `ok` | PASS |", render_markdown(self.result))

    def test_junit_is_valid_xml(self) -> None:
        root = ElementTree.fromstring(render_junit(self.result))
        self.assertEqual(root.attrib["failures"], "0")


if __name__ == "__main__":
    unittest.main()
