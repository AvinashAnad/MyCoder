"""Query decomposition — breaks complex queries into a DAG of sub-tasks."""

import json
import re
from .schemas import NodeSpec, DAGPlan

PLANNER_PROMPT = """\
You are a task planner. Given a user query, break it into sub-tasks organized as a DAG.

Output a JSON object:
{
  "tasks": [
    {
      "id": "unique-id",
      "skill": "researcher|coder|distiller",
      "description": "what this task does",
      "depends_on": ["id-of-dependency"]
    }
  ]
}

Rules:
- "researcher" for information gathering, reading files, searching
- "coder" for writing/editing code
- "distiller" for summarizing or combining results
- Tasks with no dependencies run in parallel
- Keep it minimal — don't over-decompose simple queries
- For simple queries, return a single "coder" task
- Critic and formatter nodes are added automatically"""

SKILL_PROMPTS = {
    "planner": PLANNER_PROMPT,
    "researcher": (
        "You are a researcher. Gather information by reading files and searching "
        "the codebase. Report findings with file paths and relevant code snippets."
    ),
    "coder": (
        "You are a coder. Write clean, correct, minimal code. "
        "Show changes clearly. Explain what you changed and why, briefly."
    ),
    "distiller": (
        "You are a distiller. Combine and summarize upstream results into a "
        "coherent, concise summary. Preserve key details and code snippets."
    ),
    "critic": (
        "You are a code critic. Review the work for:\n"
        "- Correctness: Does it solve the problem?\n"
        "- Completeness: Are edge cases handled?\n"
        "- Quality: Is it clean, readable, secure?\n"
        "- Bugs: Any obvious issues?\n\n"
        "Be specific about problems or confirm the work is solid."
    ),
    "formatter": (
        "You are a formatter. Take the reviewed output and produce a clear, "
        "well-structured final response. Use markdown. Be concise but complete."
    ),
}


def parse_plan(response: str, original_query: str) -> DAGPlan:
    json_match = re.search(r"\{[\s\S]*\}", response)
    if not json_match:
        return _simple_plan(original_query)

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return _simple_plan(original_query)

    tasks = data.get("tasks", [])
    if not tasks:
        return _simple_plan(original_query)

    plan = DAGPlan(query=original_query)

    for task in tasks:
        plan.nodes.append(NodeSpec(
            id=task.get("id", f"task-{len(plan.nodes)}"),
            skill=task.get("skill", "coder"),
            prompt_template=task.get("description", original_query),
            depends_on=task.get("depends_on", []),
        ))

    leaf_ids = _find_leaves(plan.nodes)
    plan.nodes.append(NodeSpec(
        id="critic",
        skill="critic",
        prompt_template="Review the outputs for correctness, completeness, and quality.",
        depends_on=leaf_ids,
    ))
    plan.nodes.append(NodeSpec(
        id="formatter",
        skill="formatter",
        prompt_template="Produce a clear, well-structured final response.",
        depends_on=["critic"],
    ))

    return plan


def _find_leaves(nodes: list[NodeSpec]) -> list[str]:
    parent_ids = set()
    for n in nodes:
        parent_ids.update(n.depends_on)
    return [n.id for n in nodes if n.id not in parent_ids]


def _simple_plan(query: str) -> DAGPlan:
    return DAGPlan(
        query=query,
        nodes=[
            NodeSpec(id="main", skill="coder", prompt_template=query),
            NodeSpec(id="critic", skill="critic",
                     prompt_template="Review the output.",
                     depends_on=["main"]),
            NodeSpec(id="formatter", skill="formatter",
                     prompt_template="Format the final response.",
                     depends_on=["critic"]),
        ],
    )
