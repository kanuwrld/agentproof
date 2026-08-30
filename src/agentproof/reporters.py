"""Output renderers for local use and CI systems."""

from __future__ import annotations

import json
from dataclasses import asdict
from xml.etree import ElementTree

from .core import SuiteResult


def render(result: SuiteResult, output_format: str) -> str:
    renderers = {
        "text": render_text,
        "json": render_json,
        "markdown": render_markdown,
        "junit": render_junit,
    }
    return renderers[output_format](result)


def render_text(result: SuiteResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    lines = [
        f"AgentProof {result.suite} · {status} · {result.passed_count}/{len(result.cases)} cases passed"
    ]
    for case in result.cases:
        lines.append(f"{'PASS' if case.passed else 'FAIL'}  {case.case_id}")
        for check in case.checks:
            if not check.passed:
                lines.append(f"  - {check.message}")
    return "\n".join(lines) + "\n"


def render_json(result: SuiteResult) -> str:
    return json.dumps(asdict(result), indent=2, ensure_ascii=False) + "\n"


def render_markdown(result: SuiteResult) -> str:
    icon = "✅" if result.passed else "❌"
    lines = [
        f"## AgentProof: {result.suite}",
        "",
        f"{icon} **{result.passed_count}/{len(result.cases)} cases passed**",
        "",
        "| Case | Result | Failed checks |",
        "| --- | --- | --- |",
    ]
    for case in result.cases:
        failures = [check.message.replace("|", "\\|") for check in case.checks if not check.passed]
        lines.append(
            f"| `{case.case_id}` | {'PASS' if case.passed else 'FAIL'} | "
            f"{'<br>'.join(failures) if failures else '—'} |"
        )
    return "\n".join(lines) + "\n"


def render_junit(result: SuiteResult) -> str:
    failures = sum(not case.passed for case in result.cases)
    root = ElementTree.Element(
        "testsuite",
        name=result.suite,
        tests=str(len(result.cases)),
        failures=str(failures),
    )
    for case in result.cases:
        node = ElementTree.SubElement(root, "testcase", name=case.case_id, classname="agentproof")
        failed = [check.message for check in case.checks if not check.passed]
        if failed:
            failure = ElementTree.SubElement(node, "failure", message=f"{len(failed)} checks failed")
            failure.text = "\n".join(failed)
    ElementTree.indent(root)
    return ElementTree.tostring(root, encoding="unicode", xml_declaration=True) + "\n"
