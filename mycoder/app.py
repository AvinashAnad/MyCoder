"""MyCoder — main application loop."""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from mycoder.client import OllamaClient
from mycoder.sandbox import Sandbox
from mycoder.session import Session
from mycoder.skills import SkillManager
from mycoder.tools import TOOL_DEFINITIONS, NEEDS_CONFIRMATION, ToolExecutor, is_safe_command
from mycoder.ui import UI

MAX_TOOL_ROUNDS = 20
MAX_EMPTY_RETRIES = 2

LOG_DIR = Path.home() / ".mycoder" / "logs"

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
- Explain what you changed and why, briefly.
- Always provide a response to the user. Never return empty."""

logger = logging.getLogger("mycoder")


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"mycoder_{datetime.now().strftime('%Y%m%d')}.log"

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    ))

    root = logging.getLogger("mycoder")
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    for mod in ("mycoder.client", "mycoder.sandbox", "mycoder.session",
                "mycoder.vector_store", "mycoder.dag"):
        logging.getLogger(mod).setLevel(logging.DEBUG)


class MyCoder:
    def __init__(self):
        self.client = OllamaClient()
        self.sandbox = None
        self.tools = ToolExecutor()
        self.skills = SkillManager()
        self.ui = UI()
        self.vector_store = None
        self.dag_executor = None
        self.session = Session()
        self.messages = []
        self.model = None
        self.options = {}
        self.auto_approve = False
        self.dag_mode = False

    def run(self):
        setup_logging()
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
        p.add_argument("--resume", action="store_true", help="Resume last session")

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

    def _save_session(self):
        self.session.model = self.model
        self.session.messages = self.messages
        self.session.metadata = {
            "sandbox_root": self.sandbox.root if self.sandbox else None,
            "dag_mode": self.dag_mode,
        }
        self.session.save()

    def _load_session(self, session_id=None):
        if session_id:
            s = Session()
            if not s.load(session_id):
                self.ui.error(f"Session not found: {session_id}")
                return False
        else:
            s = Session.latest()
            if not s:
                self.ui.error("No previous sessions found.")
                return False

        self.session = s
        self.messages = s.messages
        if s.model:
            self.model = s.model

        user_msgs = [m for m in s.messages if m.get("role") == "user"]
        self.ui.success(
            f"Resumed session {s.session_id} "
            f"({len(user_msgs)} user messages, model: {s.model})"
        )
        logger.info("Resumed session %s", s.session_id)
        return True

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

        if getattr(args, "resume", False):
            if self._load_session():
                self.ui.show_model_selected(self.model)
            else:
                self._select_model(args)
                self.ui.show_model_selected(self.model)
                self.messages = [{"role": "system", "content": self._build_system_prompt()}]
        else:
            self._select_model(args)
            self.ui.show_model_selected(self.model)
            self.messages = [{"role": "system", "content": self._build_system_prompt()}]

        self._init_dag()
        self.options = self._build_options(args)

        status_parts = []
        if self.sandbox:
            status_parts.append(f"Sandbox: {self.sandbox.root}")
        if self.vector_store:
            status_parts.append(f"FAISS: {self.vector_store.count} entries")
        status_parts.append(f"Session: {self.session.session_id}")
        self.ui.info("  ".join(status_parts))

        log_file = LOG_DIR / f"mycoder_{datetime.now().strftime('%Y%m%d')}.log"
        self.ui.info(f"Log: {log_file}")

        while True:
            user_input = self.ui.get_input()
            if not user_input:
                continue

            if user_input.startswith("/"):
                if not self._handle_command(user_input):
                    self._save_session()
                    break
                continue

            if self.dag_mode and self.dag_executor:
                self._dag_chat(user_input)
            else:
                self._chat(user_input)

            self._save_session()

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
            self.session = Session()
            self.ui.success("Conversation cleared. New session started.")

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

        elif cmd == "/save":
            self._save_session()
            self.ui.success(f"Session saved: {self.session.session_id}")

        elif cmd == "/resume":
            self._load_session(arg if arg else None)

        elif cmd == "/sessions":
            sessions = Session.list_sessions()
            if sessions:
                for s in sessions:
                    self.ui.info(
                        f"  {s['id']}  model={s['model']}  "
                        f"msgs={s['messages']}  {s['saved_at']}"
                    )
            else:
                self.ui.info("No saved sessions.")

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
        logger.info("User: %s", user_input[:200])

        for round_num in range(MAX_TOOL_ROUNDS):
            response = self._call_model_with_retry()
            if response is None:
                return

            assistant_msg = {"role": "assistant", "content": response.content}
            if response.tool_calls:
                assistant_msg["tool_calls"] = response.tool_calls
            self.messages.append(assistant_msg)

            self.ui.show_turn_metrics(response.metrics)

            if not response.tool_calls:
                if self.vector_store and response.content.strip():
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
                        logger.warning("Bad tool args: %s", args)
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
                logger.info("Tool %s -> %d chars", name, len(result))

                self.messages.append({"role": "tool", "content": result})
        else:
            self.ui.error(f"Hit tool-call limit ({MAX_TOOL_ROUNDS} rounds).")
            logger.warning("Tool-call limit reached")

    def _call_model_with_retry(self):
        for attempt in range(MAX_EMPTY_RETRIES + 1):
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
                return None
            except Exception as e:
                self.ui.end_response()
                logger.error("API error: %s", e, exc_info=True)
                self.ui.error(f"API error: {e}")
                return None

            self.ui.end_response()

            if response.error:
                logger.error("Model error: %s", response.error)
                self.ui.error(f"Model error: {response.error}")
                if attempt < MAX_EMPTY_RETRIES:
                    self.ui.info(f"Retrying ({attempt + 1}/{MAX_EMPTY_RETRIES})...")
                    continue
                return None

            if response.is_empty:
                logger.warning(
                    "Empty response (attempt %d, thinking=%d chars, done_reason=%s)",
                    attempt + 1, len(response.thinking), response.done_reason,
                )
                if attempt < MAX_EMPTY_RETRIES:
                    self.ui.info(
                        f"Model returned empty response. "
                        f"Retrying ({attempt + 1}/{MAX_EMPTY_RETRIES})..."
                    )
                    self.messages.append({
                        "role": "assistant", "content": "(empty)",
                    })
                    self.messages.append({
                        "role": "user",
                        "content": (
                            "Your previous response was empty. "
                            "Please provide a complete answer."
                        ),
                    })
                    continue
                self.ui.error(
                    "Model returned empty response after retries. "
                    "Try a different model or rephrase your query."
                )
                logger.error("Empty response after %d retries", MAX_EMPTY_RETRIES)
                return None

            return response

        return None

    def _dag_chat(self, user_input):
        from mycoder.dag.planner import parse_plan, PLANNER_PROMPT
        from mycoder.dag.graph import DAGGraph

        self.ui.info("Planning with DAG orchestrator...")
        logger.info("DAG mode: %s", user_input[:200])

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
            logger.error("Planner error: %s", e, exc_info=True)
            self.ui.error(f"Planner error: {e}")
            self._chat(user_input)
            return

        plan = parse_plan(response.content, user_input)
        self.ui.info(f"Plan: {len(plan.nodes)} nodes")
        logger.info("Plan: %d nodes", len(plan.nodes))

        graph = DAGGraph()
        for node in plan.nodes:
            graph.add_node(node)

        def on_progress(nid, state):
            self.ui.info(f"  {nid}: {state.value}")
            logger.info("DAG node %s: %s", nid, state.value)

        try:
            loop = asyncio.new_event_loop()
            result_graph = loop.run_until_complete(
                self.dag_executor.execute(graph, on_progress=on_progress)
            )
            loop.close()
        except Exception as e:
            logger.error("DAG execution error: %s", e, exc_info=True)
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
            logger.warning("DAG produced no output, falling back")
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
