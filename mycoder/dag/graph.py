"""DAG graph backed by NetworkX."""

import networkx as nx
from .schemas import NodeSpec, NodeState, AgentResult


class DAGGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: dict[str, NodeSpec] = {}

    def add_node(self, spec: NodeSpec):
        self.nodes[spec.id] = spec
        self.graph.add_node(spec.id)
        for dep in spec.depends_on:
            if dep in self.nodes:
                self.graph.add_edge(dep, spec.id)

    def mark(self, node_id: str, state: NodeState, result: AgentResult | None = None):
        if node_id in self.nodes:
            self.nodes[node_id].state = state
            if result:
                self.nodes[node_id].result = result

    def ready_nodes(self) -> list[NodeSpec]:
        ready = []
        for nid, spec in self.nodes.items():
            if spec.state != NodeState.PENDING:
                continue
            deps = list(self.graph.predecessors(nid))
            if all(self.nodes[d].state == NodeState.DONE for d in deps):
                ready.append(spec)
        return ready

    def is_complete(self) -> bool:
        return all(
            s.state in (NodeState.DONE, NodeState.SKIPPED, NodeState.FAILED)
            for s in self.nodes.values()
        )

    def failed_nodes(self) -> list[NodeSpec]:
        return [s for s in self.nodes.values() if s.state == NodeState.FAILED]

    def get_result(self, node_id: str) -> AgentResult | None:
        spec = self.nodes.get(node_id)
        return spec.result if spec else None

    def upstream_results(self, node_id: str) -> dict[str, AgentResult]:
        results = {}
        for dep in self.graph.predecessors(node_id):
            if self.nodes[dep].result:
                results[dep] = self.nodes[dep].result
        return results

    def to_dict(self) -> dict:
        return {
            "nodes": {
                nid: {
                    "skill": s.skill,
                    "state": s.state.value,
                    "depends_on": s.depends_on,
                    "has_result": s.result is not None,
                }
                for nid, s in self.nodes.items()
            }
        }
