"""Parallel DAG executor — runs ready nodes concurrently via asyncio."""

import asyncio
import logging
from .graph import DAGGraph
from .schemas import NodeSpec, NodeState, AgentResult
from .recovery import classify_failure, plan_recovery

logger = logging.getLogger(__name__)


class DAGExecutor:
    def __init__(self, client, model: str, tools=None, sandbox=None):
        self.client = client
        self.model = model
        self.tools = tools
        self.sandbox = sandbox
        self.prompts: dict[str, str] = {}

    def set_prompts(self, prompts: dict[str, str]):
        self.prompts = prompts

    async def execute(self, graph: DAGGraph, on_progress=None) -> DAGGraph:
        max_iterations = 20
        iteration = 0

        while not graph.is_complete() and iteration < max_iterations:
            iteration += 1
            ready = graph.ready_nodes()

            if not ready:
                if graph.failed_nodes():
                    break
                await asyncio.sleep(0.1)
                continue

            tasks = [self._run_node(graph, node) for node in ready]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for node, result in zip(ready, results):
                if isinstance(result, Exception):
                    agent_result = AgentResult(
                        node_id=node.id,
                        success=False,
                        error=str(result),
                    )
                    failure = classify_failure(str(result))
                    action = plan_recovery(failure, node)

                    if action == "retry" and node.retries < node.max_retries:
                        node.retries += 1
                        node.state = NodeState.PENDING
                        logger.info("Retrying %s (attempt %d)", node.id, node.retries)
                    elif action == "skip":
                        graph.mark(node.id, NodeState.SKIPPED, agent_result)
                    else:
                        graph.mark(node.id, NodeState.FAILED, agent_result)
                else:
                    graph.mark(node.id, NodeState.DONE, result)

                if on_progress:
                    on_progress(node.id, node.state)

        return graph

    async def _run_node(self, graph: DAGGraph, node: NodeSpec) -> AgentResult:
        graph.mark(node.id, NodeState.RUNNING)

        upstream = graph.upstream_results(node.id)
        prompt = self._build_prompt(node, upstream)

        messages = [
            {"role": "system", "content": self._system_for_skill(node.skill)},
            {"role": "user", "content": prompt},
        ]

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat_stream(
                model=self.model,
                messages=messages,
                options={"temperature": 0.3},
            ),
        )

        return AgentResult(
            node_id=node.id,
            content=response.content,
            success=True,
            metadata={"tokens": response.metrics.total_tokens},
        )

    def _build_prompt(self, node: NodeSpec, upstream: dict[str, AgentResult]) -> str:
        parts = []
        if node.prompt_template:
            parts.append(node.prompt_template)
        if upstream:
            parts.append("\n## Upstream Results")
            for uid, result in upstream.items():
                parts.append(f"\n### From {uid}:\n{result.content}")
        return "\n".join(parts)

    def _system_for_skill(self, skill: str) -> str:
        return self.prompts.get(skill, f"You are a {skill}. Be concise and precise.")
