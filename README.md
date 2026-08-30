# AgentProof

[![CI](https://github.com/kanuwrld/agentproof/actions/workflows/ci.yml/badge.svg)](https://github.com/kanuwrld/agentproof/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Deterministic regression checks for recorded AI automation outputs.

AI workflows can change when prompts, models, retrieval data, or routing logic
change. AgentProof turns representative, sanitized responses into a CI contract:
required fields, exact values, expected phrases, regex rules, secret-pattern
guards, latency budgets, and cost budgets.

AgentProof does not call a model, upload prompts, or pretend that deterministic
checks measure subjective quality. Record results in your own controlled test
runner, remove sensitive data, then evaluate them locally.

## Quick start

Requirements: Python 3.10+.

```bash
python -m pip install -e .
agentproof check examples/support-triage.suite.json
```

Example output:

```text
AgentProof support-triage-v1 · PASS · 1/1 cases passed
PASS  billing-refund
```

CI-friendly formats:

```bash
agentproof check suite.json --format markdown --output summary.md
agentproof check suite.json --format junit --output junit.xml
agentproof check suite.json --format json
```

Exit code `0` means all cases passed, `1` means at least one assertion failed,
and `2` means the suite or CLI input is invalid.

## Suite format

Each case contains the recorded `actual` output, optional measured `metrics`, and
an `assert` contract:

```json
{
  "suite": "support-triage-v1",
  "cases": [
    {
      "id": "billing-refund",
      "actual": {
        "category": "billing",
        "draft": "We will review the duplicate charge."
      },
      "metrics": {
        "latency_ms": 438,
        "cost_usd": 0.0031
      },
      "assert": {
        "required": ["category", "draft"],
        "equals": {"category": "billing"},
        "contains": {"draft": ["review", "charge"]},
        "forbidden": ["(?i)password", "sk-[A-Za-z0-9]{12,}"],
        "max_latency_ms": 750,
        "max_cost_usd": 0.01
      }
    }
  ]
}
```

Dot paths support objects and array indexes, for example `citations.0.id`.
`contains` is case-insensitive. `matches` and `forbidden` use Python regular
expressions.

## Evidence boundary

Passing fixtures prove that the recorded outputs meet declared deterministic
contracts. They do not prove factual correctness, fairness, prompt-injection
resistance, production reliability, or business impact. Add expert review and
live-system monitoring appropriate to the risk of the workflow.

Never commit raw customer prompts, personal data, credentials, proprietary
retrieval content, or production model responses without explicit review.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## Roadmap

- [ ] Compare candidate runs with approved baselines
- [ ] JSON Schema assertions without runtime dependencies
- [ ] Aggregate latency and cost budgets across a suite
- [ ] Optional SARIF output for security-oriented failures

## License

MIT. See [LICENSE](LICENSE).
