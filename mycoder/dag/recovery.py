"""Failure classification and recovery strategies for DAG nodes."""

from .schemas import FailureType, NodeSpec

TRANSIENT_PATTERNS = [
    "timeout", "connection", "rate limit", "503", "502",
    "temporary", "retry", "unavailable",
]

VALIDATION_PATTERNS = [
    "invalid", "malformed", "parse error", "json",
    "missing required", "type error", "validation",
]


def classify_failure(error: str) -> FailureType:
    error_lower = error.lower()

    for pattern in TRANSIENT_PATTERNS:
        if pattern in error_lower:
            return FailureType.TRANSIENT

    for pattern in VALIDATION_PATTERNS:
        if pattern in error_lower:
            return FailureType.VALIDATION_ERROR

    return FailureType.UPSTREAM_FAILURE


def plan_recovery(failure_type: FailureType, node: NodeSpec) -> str:
    if failure_type == FailureType.TRANSIENT:
        return "retry"

    if failure_type == FailureType.VALIDATION_ERROR:
        if node.retries < node.max_retries:
            return "retry"
        return "skip"

    if node.skill in ("researcher", "distiller"):
        return "skip"

    return "fail"
