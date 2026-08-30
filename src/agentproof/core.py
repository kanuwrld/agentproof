"""Deterministic assertions for recorded AI automation outputs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


class SuiteFormatError(ValueError):
    """Raised when an AgentProof suite is malformed."""


@dataclass(frozen=True)
class CheckResult:
    check: str
    passed: bool
    message: str


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    passed: bool
    checks: tuple[CheckResult, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SuiteResult:
    suite: str
    passed: bool
    cases: tuple[CaseResult, ...]

    @property
    def passed_count(self) -> int:
        return sum(case.passed for case in self.cases)


_MISSING = object()


def load_suite(path: str | Path) -> Mapping[str, Any]:
    suite_path = Path(path)
    try:
        data = json.loads(suite_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SuiteFormatError(f"cannot read {suite_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SuiteFormatError(
            f"invalid JSON in {suite_path} at line {exc.lineno}, column {exc.colno}"
        ) from exc
    _validate_suite(data)
    return data


def evaluate_suite(data: Mapping[str, Any]) -> SuiteResult:
    _validate_suite(data)
    results = tuple(_evaluate_case(case) for case in data["cases"])
    return SuiteResult(
        suite=data["suite"],
        passed=all(case.passed for case in results),
        cases=results,
    )


def _validate_suite(data: Any) -> None:
    if not isinstance(data, dict):
        raise SuiteFormatError("suite root must be a JSON object")
    if not isinstance(data.get("suite"), str) or not data["suite"].strip():
        raise SuiteFormatError("suite must contain a non-empty 'suite' string")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SuiteFormatError("suite must contain a non-empty 'cases' array")

    seen: set[str] = set()
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            raise SuiteFormatError(f"{prefix} must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise SuiteFormatError(f"{prefix}.id must be a non-empty string")
        if case_id in seen:
            raise SuiteFormatError(f"duplicate case id: {case_id}")
        seen.add(case_id)
        if "actual" not in case:
            raise SuiteFormatError(f"{prefix} must contain 'actual'")
        assertions = case.get("assert", {})
        if not isinstance(assertions, dict):
            raise SuiteFormatError(f"{prefix}.assert must be an object")
        _validate_assertions(assertions, prefix)
        metrics = case.get("metrics", {})
        if not isinstance(metrics, dict):
            raise SuiteFormatError(f"{prefix}.metrics must be an object")


def _validate_assertions(assertions: Mapping[str, Any], prefix: str) -> None:
    supported = {
        "required",
        "equals",
        "contains",
        "matches",
        "forbidden",
        "max_latency_ms",
        "max_cost_usd",
    }
    unknown = sorted(set(assertions) - supported)
    if unknown:
        raise SuiteFormatError(f"{prefix}.assert has unknown keys: {', '.join(unknown)}")

    required = assertions.get("required", [])
    forbidden = assertions.get("forbidden", [])
    if not _is_string_list(required):
        raise SuiteFormatError(f"{prefix}.assert.required must be an array of paths")
    if not _is_string_list(forbidden):
        raise SuiteFormatError(f"{prefix}.assert.forbidden must be an array of regex strings")

    for key in ("equals", "contains", "matches"):
        value = assertions.get(key, {})
        if not isinstance(value, dict) or not all(isinstance(path, str) for path in value):
            raise SuiteFormatError(f"{prefix}.assert.{key} must be a path-keyed object")

    for path, expected in assertions.get("contains", {}).items():
        values = expected if isinstance(expected, list) else [expected]
        if not values or not all(isinstance(value, str) for value in values):
            raise SuiteFormatError(
                f"{prefix}.assert.contains[{path!r}] must be a string or string array"
            )

    patterns = list(forbidden) + list(assertions.get("matches", {}).values())
    if not all(isinstance(pattern, str) for pattern in patterns):
        raise SuiteFormatError(f"{prefix} regex assertions must be strings")
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise SuiteFormatError(f"{prefix} contains invalid regex {pattern!r}: {exc}") from exc

    for key in ("max_latency_ms", "max_cost_usd"):
        value = assertions.get(key)
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            raise SuiteFormatError(f"{prefix}.assert.{key} must be a non-negative number")


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _evaluate_case(case: Mapping[str, Any]) -> CaseResult:
    actual = case["actual"]
    assertions = case.get("assert", {})
    metrics = case.get("metrics", {})
    checks: list[CheckResult] = []

    for path in assertions.get("required", []):
        value = _resolve_path(actual, path)
        checks.append(
            CheckResult(
                check=f"required:{path}",
                passed=value is not _MISSING,
                message=f"{path} is present" if value is not _MISSING else f"missing path: {path}",
            )
        )

    for path, expected in assertions.get("equals", {}).items():
        value = _resolve_path(actual, path)
        passed = value is not _MISSING and value == expected
        checks.append(
            CheckResult(
                check=f"equals:{path}",
                passed=passed,
                message=(
                    f"{path} equals {expected!r}"
                    if passed
                    else f"{path}: expected {expected!r}, got {_display(value)}"
                ),
            )
        )

    for path, expected in assertions.get("contains", {}).items():
        value = _resolve_path(actual, path)
        needles = expected if isinstance(expected, list) else [expected]
        text = value if isinstance(value, str) else ""
        missing = [needle for needle in needles if needle.casefold() not in text.casefold()]
        passed = value is not _MISSING and isinstance(value, str) and not missing
        checks.append(
            CheckResult(
                check=f"contains:{path}",
                passed=passed,
                message=(
                    f"{path} contains required text"
                    if passed
                    else f"{path} is missing: {', '.join(repr(item) for item in missing or needles)}"
                ),
            )
        )

    for path, pattern in assertions.get("matches", {}).items():
        value = _resolve_path(actual, path)
        passed = isinstance(value, str) and re.search(pattern, value) is not None
        checks.append(
            CheckResult(
                check=f"matches:{path}",
                passed=passed,
                message=(
                    f"{path} matches {pattern!r}"
                    if passed
                    else f"{path} does not match {pattern!r}"
                ),
            )
        )

    serialized = json.dumps(actual, ensure_ascii=False, sort_keys=True)
    for pattern in assertions.get("forbidden", []):
        match = re.search(pattern, serialized)
        checks.append(
            CheckResult(
                check=f"forbidden:{pattern}",
                passed=match is None,
                message=(
                    f"forbidden pattern absent: {pattern!r}"
                    if match is None
                    else f"forbidden pattern found: {pattern!r}"
                ),
            )
        )

    _append_budget_check(checks, assertions, metrics, "max_latency_ms", "latency_ms", "ms")
    _append_budget_check(checks, assertions, metrics, "max_cost_usd", "cost_usd", "USD")

    return CaseResult(
        case_id=case["id"],
        passed=all(check.passed for check in checks),
        checks=tuple(checks),
    )


def _append_budget_check(
    checks: list[CheckResult],
    assertions: Mapping[str, Any],
    metrics: Mapping[str, Any],
    assertion_key: str,
    metric_key: str,
    unit: str,
) -> None:
    if assertion_key not in assertions:
        return
    limit = assertions[assertion_key]
    value = metrics.get(metric_key, _MISSING)
    passed = isinstance(value, (int, float)) and not isinstance(value, bool) and value <= limit
    message = (
        f"{metric_key} {value:g} {unit} <= {limit:g} {unit}"
        if passed
        else f"{metric_key}: expected <= {limit:g} {unit}, got {_display(value)}"
    )
    checks.append(CheckResult(check=assertion_key, passed=passed, message=message))


def _resolve_path(value: Any, path: str) -> Any:
    if path == "" or path == ".":
        return value
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return _MISSING
    return current


def _display(value: Any) -> str:
    return "<missing>" if value is _MISSING else repr(value)
