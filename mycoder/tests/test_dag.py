"""Tests for the DAG orchestrator."""

import pytest
from mycoder.dag.schemas import NodeSpec, NodeState, AgentResult, FailureType, DAGPlan
from mycoder.dag.graph import DAGGraph
from mycoder.dag.recovery import classify_failure, plan_recovery
from mycoder.dag.planner import parse_plan, _find_leaves


class TestDAGGraph:
    def test_add_node(self):
        g = DAGGraph()
        g.add_node(NodeSpec(id="a", skill="coder"))
        assert "a" in g.nodes

    def test_ready_nodes_no_deps(self):
        g = DAGGraph()
        g.add_node(NodeSpec(id="a", skill="coder"))
        g.add_node(NodeSpec(id="b", skill="coder"))
        ready = g.ready_nodes()
        assert len(ready) == 2

    def test_ready_nodes_with_deps(self):
        g = DAGGraph()
        g.add_node(NodeSpec(id="a", skill="researcher"))
        g.add_node(NodeSpec(id="b", skill="coder", depends_on=["a"]))
        ready = g.ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "a"

    def test_deps_unlock_after_done(self):
        g = DAGGraph()
        g.add_node(NodeSpec(id="a", skill="researcher"))
        g.add_node(NodeSpec(id="b", skill="coder", depends_on=["a"]))
        g.mark("a", NodeState.DONE, AgentResult(node_id="a", content="done"))
        ready = g.ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "b"

    def test_is_complete(self):
        g = DAGGraph()
        g.add_node(NodeSpec(id="a", skill="coder"))
        assert not g.is_complete()
        g.mark("a", NodeState.DONE)
        assert g.is_complete()

    def test_is_complete_with_skipped(self):
        g = DAGGraph()
        g.add_node(NodeSpec(id="a", skill="coder"))
        g.mark("a", NodeState.SKIPPED)
        assert g.is_complete()

    def test_upstream_results(self):
        g = DAGGraph()
        g.add_node(NodeSpec(id="a", skill="researcher"))
        g.add_node(NodeSpec(id="b", skill="coder", depends_on=["a"]))
        result_a = AgentResult(node_id="a", content="findings")
        g.mark("a", NodeState.DONE, result_a)
        upstream = g.upstream_results("b")
        assert "a" in upstream
        assert upstream["a"].content == "findings"

    def test_failed_nodes(self):
        g = DAGGraph()
        g.add_node(NodeSpec(id="a", skill="coder"))
        g.mark("a", NodeState.FAILED)
        assert len(g.failed_nodes()) == 1

    def test_to_dict(self):
        g = DAGGraph()
        g.add_node(NodeSpec(id="a", skill="coder"))
        d = g.to_dict()
        assert "a" in d["nodes"]
        assert d["nodes"]["a"]["skill"] == "coder"


class TestRecovery:
    def test_classify_timeout(self):
        assert classify_failure("Connection timeout") == FailureType.TRANSIENT

    def test_classify_validation(self):
        assert classify_failure("Invalid JSON response") == FailureType.VALIDATION_ERROR

    def test_classify_unknown(self):
        assert classify_failure("Something weird") == FailureType.UPSTREAM_FAILURE

    def test_recovery_transient_retries(self):
        node = NodeSpec(id="x", skill="coder", retries=0, max_retries=2)
        assert plan_recovery(FailureType.TRANSIENT, node) == "retry"

    def test_recovery_researcher_skips(self):
        node = NodeSpec(id="x", skill="researcher")
        assert plan_recovery(FailureType.UPSTREAM_FAILURE, node) == "skip"

    def test_recovery_coder_fails(self):
        node = NodeSpec(id="x", skill="coder")
        assert plan_recovery(FailureType.UPSTREAM_FAILURE, node) == "fail"


class TestPlanner:
    def test_parse_valid_json(self):
        response = '''Here's the plan:
        {
            "tasks": [
                {"id": "read", "skill": "researcher", "description": "Read the file"},
                {"id": "fix", "skill": "coder", "description": "Fix the bug", "depends_on": ["read"]}
            ]
        }'''
        plan = parse_plan(response, "fix the bug")
        assert plan.query == "fix the bug"
        assert len(plan.nodes) == 4  # 2 tasks + critic + formatter

    def test_parse_invalid_json_falls_back(self):
        plan = parse_plan("no json here", "do something")
        assert len(plan.nodes) == 3  # simple plan: main + critic + formatter
        assert plan.nodes[0].skill == "coder"

    def test_parse_empty_tasks_falls_back(self):
        plan = parse_plan('{"tasks": []}', "do something")
        assert len(plan.nodes) == 3

    def test_critic_and_formatter_added(self):
        response = '{"tasks": [{"id": "a", "skill": "coder", "description": "do it"}]}'
        plan = parse_plan(response, "test")
        node_ids = [n.id for n in plan.nodes]
        assert "critic" in node_ids
        assert "formatter" in node_ids

    def test_find_leaves(self):
        nodes = [
            NodeSpec(id="a", skill="researcher"),
            NodeSpec(id="b", skill="coder", depends_on=["a"]),
            NodeSpec(id="c", skill="coder", depends_on=["a"]),
        ]
        leaves = _find_leaves(nodes)
        assert set(leaves) == {"b", "c"}
