"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .core import SuiteFormatError, evaluate_suite, load_suite
from .reporters import render


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentproof",
        description="Run deterministic checks against recorded AI automation outputs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="evaluate a JSON suite")
    check.add_argument("suite", type=Path)
    check.add_argument(
        "--format",
        choices=("text", "json", "markdown", "junit"),
        default="text",
        dest="output_format",
    )
    check.add_argument("--output", type=Path, help="write the report instead of stdout")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate_suite(load_suite(args.suite))
        report = render(result, args.output_format)
        if args.output:
            args.output.write_text(report, encoding="utf-8")
        else:
            sys.stdout.write(report)
        return 0 if result.passed else 1
    except (SuiteFormatError, OSError) as exc:
        print(f"agentproof: {exc}", file=sys.stderr)
        return 2
