import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentproof.cli import main


class CliTests(unittest.TestCase):
    def test_writes_junit_report_and_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = root / "suite.json"
            output = root / "report.xml"
            suite.write_text(
                json.dumps(
                    {
                        "suite": "ci",
                        "cases": [
                            {
                                "id": "wrong",
                                "actual": {"decision": "deny"},
                                "assert": {"equals": {"decision": "allow"}},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            code = main(["check", str(suite), "--format", "junit", "--output", str(output)])
            self.assertEqual(code, 1)
            self.assertIn('<testsuite name="ci" tests="1" failures="1">', output.read_text())

    def test_invalid_file_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{", encoding="utf-8")
            with patch("sys.stderr"):
                self.assertEqual(main(["check", str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
