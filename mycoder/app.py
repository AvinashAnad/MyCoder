"""MyCoder — main application loop."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mycoder.client import OllamaClient
from mycoder.sandbox import Sandbox
from mycoder.skills import SkillManager
from mycoder.tools import TOOL_DEFINITIONS, NEEDS_CONFIRMATION, ToolExecutor, is_safe_command
from mycoder.ui import UI

MAX_TOOL_ROUNDS = 20

SYSTEM_PROMPT = """\
You are MyCoder, a local AI coding assistant with direct access to the user's filesystem.

You help with software engineering: writing code, debugging, refactoring, explaining, and running commands.

All file operations are sandboxed to the current working directory. External access is tracked.

Rules:
- Read files before modifying them.
- Make minimal, targeted changes.
- Be concise. Show code, not lectures.
- Use tools proactively — don't ask permission to read a file, just read it.
- When editing, use edit_file with the exact text to replace.
- For new files, use write_file.
- Explain what you changed and why, briefly."""


class MyCoder:
    def __init__(self):
        self.client = OllamaClient()
        self.sandbox = None
        self.tools = ToolExecutor()
        self.skills = SkillManager()
        self.ui = UI()
        self.vector_store = None
        self.dag_executor = None
        self.messages = []
        self.model = None
        self.options = {}
        self.auto_approve = False
        self.dag_mode = False

    def run(self):
        args = self._parse_args()

        if not self.client.is_running():
            self.ui.error("Ollama is not running. Start it with: ollama serve")
            sys.exit(1)

        sandbox_root = os.path.abspath(args.dir) if args.dir else os.getcwd()
        self.sandbox = Sandbox(sandbox_root)
        self.tools = ToolExecutor(sandbox_root, self.sandbox)

        self._init_vector_store()

        if args.command == "models":
            self._cmd_models()
        elif args.command == "run":
            self._cmd_run(args)
        elif args.command == "mcp":
            self._cmd_mcp()
        else:
            self._interactive(args)

    def _init_vector_store(self):
        try:
            from mycoder.vector_store import VectorStore
            store_dir = str(Path.home() / ".mycoder" / "vector_store")
            self.vector_store = VectorStore(self.client, store_dir)
            if self.vector_store.available:
                return
        except Exception:
            pass
        self.vector_store = None

    def _init_dag(self):
        try:
            from mycoder.dag.executor import DAGExecutor
            from mycoder.dag.planner import SKILL_PROMPTS
            self.dag_executor = DAGExecutor(
                self.client, self.model, self.tools, self.sandbox
            )
            self.dag_executor.set_prompts(SKILL_PROMPTS)
        except Exception:
            self.dag_executor = None

    def _parse_args(self):
        p = argparse.ArgumentParser(
            prog="mycoder",
            description="Local AI coding assistant powered by Ollama",
        )
        p.add_argument("-m", "--model", help="Model name or prefix")
        p.add_argument("-t", "--temperature", type=float, help="Sampling temperature")
        p.add_argument("--ctx", type=int, help="Context window size")
        p.add_argument("-d", "--dir", help="Working directory (sandbox root)")

        sub = p.add_subparsers(dest="command")
        sub.add_parser("models", help="List available models")
        sub.add_parser("chat", help="Interactive chat (default)")
        sub.add_parser("mcp", help="Run as MCP server (stdin/stdout)")
        run_p = sub.add_parser("run", help="Run a one-shot prompt")
        run_p.add_argument("prompt", nargs="*", help="Prompt text")
        run_p.add_argument("-y", "--yes", action="store_true",
                           help="Auto-approve tool actions")

        return p.parse_args()

    def _build_options(self, args):
        opts = {}
        if args.temperature is not None:
            opts["temperature"] = args.temperature
        if args.ctx is not None:
            opts["num_ctx"] = args.ctx
        return opts or None

    def _cmd_models(self):
        models = self.client.list_models()
        if not models:
            self.ui.error("No models found. Pull one with: ollama pull <model>")
            return
        running = self.client.running_models()
        self.ui.show_model_table(models, running)

    def _cmd_mcp(self):
        from mycoder.mcp.server import MCPServer
        server = MCPServer(self.tools, self.sandbox)
        server.run_stdio()

    def _build_system_prompt(self):
        prompt = SYSTEM_PROMPT
        additions = self.skills.system_prompt_additions()
        if additions:
            prompt += "\n\n" + additions
        return prompt

    def _cmd_run(self, args):
        prompt = " ".join(args.prompt) if args.prompt else None
        if not prompt:
            self.ui.error("Usage: mycoder run 'your prompt here'")
            return
        self._select_model(args)
        self.options = self._build_options(args)
        self.auto_approve = getattr(args, "yes", False)
        self.messages = [{"role": "system", "content": self._build_system_prompt()}]
        self._chat(prompt)

    def _select_model(self, args):
        models = self.client.list_models()
        if not models:
            self.ui.error("No models found. Pull one with: ollama pull <model>")
            sys.exit(1)

        if args.model:
            matches = [m for m in models
                       if m["name"] == args.model or m["name"].startswith(args.model)]
            if matches:
                self.model = matches[0]["name"]
                return
            self.ui.error(f"No model matching '{args.model}'")

        running = self.client.running_models()
        self.model = self.ui.prompt_model_selection(models, running)

    def _interactive(self, args):
        models = self.client.list_models()
        if not models:
            self.ui.error("No models found. Pull one with: ollama pull <model>")
            sys.exit(1)

        if args.dir:
            target = os.path.abspath(args.dir)
            if os.path.isdir(target):
                os.chdir(target)
            else:
                self.ui.error(f"Not a directory: {args.dir}")

        self.ui.show_banner(len(models))
        self._select_model(args)
        self.ui.show_model_selected(self.model)
        self._init_dag()
        self.options = self._build_options(args)
        self.messages = [{"role": "system", "content": self._build_system_prompt()}]

        status_parts = []
        if self.sandbox:
            status_parts.append(f"Sandbox: {self.sandbox.root}")
        if self.vector_store:
            status_parts.append(f"FAISS: {self.vector_store.count} entries")
        if status_parts:
            self.ui.info("  ".join(status_parts))

        while True:
            user_input = self.ui.get_input()
            if not user_input:
                continue

            if user_input.startswith("/"):
                if not self._handle_command(user_input):
                    break
                continue

            if self.dag_mode and self.dag_executor:
                self._dag_chat(user_input)
            else:
                self._chat(user_input)

    def _handle_command(self, raw):
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/exit", "/quit", "/q"):
            self.ui.info("Goodbye!")
            return False

        if cmd in ("/models", "/model"):
            models = self.client.list_models()
            running = self.client.running_models()
            if arg:
                matches = [m for m in models if m["name"].startswith(arg)]
                if matches:
                    self.model = matches[0]["name"]
                    self.ui.show_model_selected(self.model)
                else:
                    self.ui.error(f"No model matching '{arg}'")
            else:
                self.model = self.ui.prompt_model_selection(models, running)
                self.ui.show_model_selected(self.model)

        elif cmd in ("/metrics", "/stats"):
            self.ui.show_session_stats()

        elif cmd == "/clear":
            self.messages = [{"role": "system", "content": self._build_system_prompt()}]
            self.ui.success("Conversation cleared.")

        elif cmd == "/cd":
            if not arg:
                self.ui.info(f"cwd: {os.getcwd()}")
            else:
                target = os.path.abspath(arg)
                if os.path.isdir(target):
                    os.chdir(target)
                    self.sandbox = Sandbox(target)
                    self.tools = ToolExecutor(target, self.sandbox)
                    self.ui.success(f"-> {target}")
                else:
                    self.ui.error(f"Not a directory: {arg}")

        elif cmd == "/skills":
            self.ui.show_skills(self.skills.all())

        elif cmd == "/reload":
            self.skills.load()
            self.ui.success(f"Reloaded {len(self.skills.skills)} skills.")

        elif cmd == "/help":
            self.ui.show_help(self.skills.invocable())

        elif cmd == "/dag":
            self.dag_mode = not self.dag_mode
            status = "enabled" if self.dag_mode else "disabled"
            self.ui.success(f"DAG orchestration {status}.")

        elif cmd == "/search":
            if self.vector_store and arg:
                results = self.vector_store.search(arg)
                if results:
                    for entry, score in results:
                        self.ui.info(f"  [{score:.3f}] {entry.query[:80]}")
                else:
                    self.ui.info("No similar past queries found.")
            elif not self.vector_store:
                self.ui.error("Vector store not available (install faiss-cpu)")
            else:
                self.ui.error("Usage: /search <query>")

        elif cmd == "/mcp-log":
            if self.sandbox:
                log = self.sandbox.get_mcp_log()
                if log:
                    for call in log[-20:]:
                        self.ui.info(f"  {call.timestamp} {call.tool}")
                else:
                    self.ui.info("No MCP calls recorded.")

        else:
            skill = self.skills.get(cmd.lstrip("/"))
            if skill and skill.type == "prompt":
                prompt = arg if arg else f"Use the {skill.name} skill."
                augmented = f"[Skill: {skill.name}]\n{skill.body}\n\n[User request]\n{prompt}"
                self._chat(augmented)
            else:
                self.ui.error(f"Unknown command: {cmd}  (/help for list)")

        return True

    def _chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(MAX_TOOL_ROUNDS):
            self.ui.start_response()

            try:
                response = self.client.chat_stream(
                    model=self.model,
                    messages=self.messages,
                    tools=TOOL_DEFINITIONS,
                    options=self.options,
                    on_token=self.ui.stream_token,
                    on_thinking=self.ui.stream_thinking,
                )
            except KeyboardInterrupt:
                self.ui.end_response()
                self.ui.info("Interrupted.")
                return
            except Exception as e:
                self.ui.end_response()
                self.ui.error(f"API error: {e}")
                return

            self.ui.end_response()

            assistant_msg = {"role": "assistant", "content": response.content}
            if response.tool_calls:
                assistant_msg["tool_calls"] = response.tool_calls
            self.messages.append(assistant_msg)

            self.ui.show_turn_metrics(response.metrics)

            if not response.tool_calls:
                if self.vector_store:
                    try:
                        self.vector_store.add(
                            query=user_input,
                            result=response.content,
                            model=self.model,
                        )
                    except Exception:
                        pass
                break

            for tc in response.tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "unknown")
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        self.ui.error(f"Bad tool args: {args}")
                        self.messages.append({
                            "role": "tool",
                            "content": f"Invalid JSON arguments: {args}",
                        })
                        continue

                needs_confirm = name in NEEDS_CONFIRMATION and not self.auto_approve
                if needs_confirm and name == "run_command":
                    if is_safe_command(args.get("command", "")):
                        needs_confirm = False
                if needs_confirm:
                    desc = _describe_action(name, args)
                    if not self.ui.confirm(desc):
                        self.messages.append({
                            "role": "tool",
                            "content": "User denied this action.",
                        })
                        continue

                self.ui.show_tool_call(name, args)
                result = self.tools.execute(name, args)
                self.ui.show_tool_result(result)
                self.ui.stats.total_tool_calls += 1

                self.messages.append({"role": "tool", "content": result})
        else:
            self.ui.error(f"Hit tool-call limit ({MAX_TOOL_ROUNDS} rounds).")

    def _dag_chat(self, user_input):
        from mycoder.dag.planner import parse_plan, PLANNER_PROMPT
        from mycoder.dag.graph import DAGGraph

        self.ui.info("Planning with DAG orchestrator...")

        messages = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": user_input},
        ]

        try:
            response = self.client.chat_stream(
                model=self.model,
                messages=messages,
                options={"temperature": 0.2},
            )
        except Exception as e:
            self.ui.error(f"Planner error: {e}")
            self._chat(user_input)
            return

        plan = parse_plan(response.content, user_input)
        self.ui.info(f"Plan: {len(plan.nodes)} nodes")

        graph = DAGGraph()
        for node in plan.nodes:
            graph.add_node(node)

        def on_progress(nid, state):
            self.ui.info(f"  {nid}: {state.value}")

        try:
            loop = asyncio.new_event_loop()
            result_graph = loop.run_until_complete(
                self.dag_executor.execute(graph, on_progress=on_progress)
            )
            loop.close()
        except Exception as e:
            self.ui.error(f"DAG execution error: {e}")
            self._chat(user_input)
            return

        formatter_result = result_graph.get_result("formatter")
        if formatter_result and formatter_result.content:
            self.ui.start_response()
            self.ui.stream_token(formatter_result.content)
            self.ui.end_response()

            if self.vector_store:
                try:
                    self.vector_store.add(
                        query=user_input,
                        result=formatter_result.content,
                        model=self.model,
                        metadata={"mode": "dag"},
                    )
                except Exception:
                    pass
        else:
            self.ui.error("DAG produced no output — falling back to direct chat.")
            self._chat(user_input)


def _describe_action(name, args):
    if name == "write_file":
        return f"Write to {args.get('path', '?')}?"
    if name == "edit_file":
        return f"Edit {args.get('path', '?')}?"
    if name == "run_command":
        cmd = args.get("command", "?")
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        return f"Run: {cmd}?"
    return f"Execute {name}?"


def main():
    try:
        app = MyCoder()
        app.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
