"""Data models for the DAG orchestrator."""

from dataclasses import dataclass, field
from enum import Enum


class NodeState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class FailureType(Enum):
    TRANSIENT = "transient"
    VALIDATION_ERROR = "validation_error"
    UPSTREAM_FAILURE = "upstream_failure"


@dataclass
class AgentResult:
    node_id: str
    content: str = ""
    success: bool = True
    error: str = ""
    metadata: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)


@dataclass
class NodeSpec:
    id: str
    skill: str
    prompt_template: str = ""
    depends_on: list[str] = field(default_factory=list)
    state: NodeState = NodeState.PENDING
    result: AgentResult | None = None
    retries: int = 0
    max_retries: int = 2


@dataclass
class DAGPlan:
    query: str
    nodes: list[NodeSpec] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
