# Security Policy

## Data boundary

AgentProof reads local JSON suites and does not make network requests. Test
fixtures can still expose prompts, customer data, credentials, or proprietary
outputs. Commit fictional or explicitly sanitized fixtures only.

Run `python scripts/public_safety.py` before every public push. CI scans tracked
files and the full Git history and hides any matched value from its output.

## Reporting a vulnerability

Do not open a public issue for an unpatched vulnerability. Repository
collaborators should create a private draft advisory under **Security →
Advisories**. If this repository becomes public, enable GitHub private
vulnerability reporting before launch so external reporters have a confidential
channel. Include affected versions, reproduction steps, impact, and any suggested
fix. Expect acknowledgement within five business days.
