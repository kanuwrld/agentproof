"""AgentProof public package interface."""

from .core import SuiteFormatError, evaluate_suite, load_suite

__all__ = ["SuiteFormatError", "evaluate_suite", "load_suite"]
__version__ = "0.1.0"
