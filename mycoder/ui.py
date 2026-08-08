"""Terminal UI — display, metrics, streaming output."""

import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

THEME = Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red bold",
    "tool.name": "bold blue",
    "tool.arg": "dim",
    "metric": "bright_cyan",
    "prompt": "bold green",
    "model": "bold magenta",
    "dim": "dim",
})

DIM_ON = "\033[2;3m"
DIM_OFF = "\033[0m"
CYAN = "\033[36m"
RESET = "\033[0m"


@dataclass
class SessionStats:
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_requests: int = 0
    total_tool_calls: int = 0
    started: str = ""

    @property
    def total_tokens(self):
        return self.total_prompt_tokens + self.total_completion_tokens


class UI:
    def __init__(self):
        self.console = Console(theme=THEME)
        self.stats = SessionStats(started=datetime.now().strftime("%H:%M:%S"))
        self._in_thinking = False
        self._has_thinking = False
        self._has_content = False
        self._is_tty = sys.stdout.isatty()

    def show_banner(self, model_count):
        self.console.print()
        self.console.print(Panel(
            "[bold]MyCoder[/bold]  ·  Local AI Coding Assistant\n"
            f"[dim]{model_count} model{'s' if model_count != 1 else ''} available  ·  /help for commands[/dim]",
            border_style="cyan",
            padding=(0, 2),
        ))

    def show_model_table(self, models, running=None):
        running_names = {m.get("name", "") for m in (running or [])}

        table = Table(show_header=True, header_style="bold", border_style="dim",
                      padding=(0, 1))
        table.add_column("#", style="dim", width=3, justify="right")
        table.add_column("Model", style="bold")
        table.add_column("Size", justify="right")
        table.add_column("Quant", style="dim")
        table.add_column("Modified", style="dim")
        table.add_column("", width=3)

        for i, m in enumerate(models, 1):
            name = m.get("name", "")
            size = _format_size(m.get("size", 0))
            quant = m.get("details", {}).get("quantization_level", "")
            modified = _relative_time(m.get("modified_at", ""))
            loaded = "[green]●[/green]" if name in running_names else ""
            table.add_row(str(i), name, size, quant, modified, loaded)

        self.console.print(table)

    def prompt_model_selection(self, models, running=None):
        self.show_model_table(models, running)
        self.console.print()
        while True:
            try:
                choice = self.console.input("[prompt]Select model (#, name, or prefix): [/prompt]")
                choice = choice.strip()
                if not choice:
                    continue
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(models):
                        return models[idx]["name"]
                    self.console.print(f"[error]Pick 1–{len(models)}[/error]")
                    continue
                except ValueError:
                    pass
                matches = [m for m in models if m["name"].startswith(choice)]
                if len(matches) == 1:
                    return matches[0]["name"]
                if len(matches) > 1:
                    self.console.print(
                        f"[warning]Ambiguous: {', '.join(m['name'] for m in matches)}[/warning]")
                else:
                    self.console.print(f"[error]No model matching '{choice}'[/error]")
            except (KeyboardInterrupt, EOFError):
                sys.exit(0)

    def show_model_selected(self, name):
        self.console.print(f"\n  [success]Model:[/success] [model]{name}[/model]\n")

    def get_input(self):
        try:
            line = self.console.input("[prompt]you ›[/prompt] ")
            text = line.strip()
            if text == '"""':
                lines = []
                while True:
                    try:
                        ml = self.console.input("[prompt]  ⋮ [/prompt]")
                    except (KeyboardInterrupt, EOFError):
                        break
                    if ml.strip() == '"""':
                        break
                    lines.append(ml)
                return "\n".join(lines)
            return text
        except KeyboardInterrupt:
            self.console.print()
            return ""
        except EOFError:
            return "/exit"

    # --- Streaming ---

    def start_response(self):
        self._in_thinking = False
        self._has_thinking = False
        self._has_content = False

    def stream_thinking(self, token):
        if not self._has_thinking:
            if self._is_tty:
                sys.stdout.write(f"\n  {DIM_ON}thinking ···\n  ")
            else:
                sys.stdout.write("\n<thinking>\n")
            self._has_thinking = True
        if self._is_tty:
            sys.stdout.write(f"{DIM_ON}{token}")
        else:
            sys.stdout.write(token)
        sys.stdout.flush()

    def stream_token(self, token):
        if self._has_thinking and not self._has_content:
            if self._is_tty:
                sys.stdout.write(f"{DIM_OFF}\n\n")
            else:
                sys.stdout.write("\n</thinking>\n\n")
            self._has_content = True
        elif not self._has_content:
            sys.stdout.write("\n")
            self._has_content = True
        sys.stdout.write(token)
        sys.stdout.flush()

    def end_response(self):
        if self._is_tty:
            sys.stdout.write(DIM_OFF)
        if self._has_content or self._has_thinking:
            sys.stdout.write("\n")
        sys.stdout.flush()

    # --- Tool display ---

    def show_tool_call(self, name, args):
        args_parts = []
        for k, v in args.items():
            val = repr(v)
            if len(val) > 80:
                val = val[:77] + "..."
            args_parts.append(f"{k}={val}")
        args_str = ", ".join(args_parts)
        self.console.print(f"  [tool.name]▸ {name}[/tool.name]([tool.arg]{args_str}[/tool.arg])")

    def show_tool_result(self, result, max_lines=25):
        lines = result.split("\n")
        if len(lines) > max_lines:
            display = "\n".join(lines[:max_lines]) + f"\n  ··· ({len(lines) - max_lines} more lines)"
        else:
            display = result
        self.console.print(Panel(
            display, border_style="dim", padding=(0, 1), expand=False,
        ))

    # --- Metrics ---

    def show_turn_metrics(self, metrics):
        self.stats.total_prompt_tokens += metrics.prompt_tokens
        self.stats.total_completion_tokens += metrics.completion_tokens
        self.stats.total_requests += 1

        parts = []
        if metrics.completion_tokens > 0:
            parts.append(f"[metric]{metrics.completion_tokens:,}[/metric] tokens")
        if metrics.tokens_per_second > 0:
            parts.append(f"[metric]{metrics.tokens_per_second:.1f}[/metric] tok/s")
        if metrics.total_duration > 0:
            parts.append(f"[metric]{metrics.total_duration:.1f}[/metric]s")
        if metrics.prompt_tokens > 0:
            parts.append(f"ctx [metric]{metrics.prompt_tokens:,}[/metric]")
        if metrics.prompt_tokens_per_second > 0:
            parts.append(f"prompt [metric]{metrics.prompt_tokens_per_second:.0f}[/metric] tok/s")

        if parts:
            self.console.print(f"  [dim]{'  ·  '.join(parts)}[/dim]")
        self.console.print()

    def show_session_stats(self):
        s = self.stats
        table = Table(title="Session Stats", border_style="cyan", show_header=False,
                      padding=(0, 2))
        table.add_column("", style="bold")
        table.add_column("", justify="right", style="metric")
        table.add_row("Started", s.started)
        table.add_row("Requests", str(s.total_requests))
        table.add_row("Prompt tokens", f"{s.total_prompt_tokens:,}")
        table.add_row("Completion tokens", f"{s.total_completion_tokens:,}")
        table.add_row("Total tokens", f"{s.total_tokens:,}")
        table.add_row("Tool calls", str(s.total_tool_calls))
        self.console.print(table)

    # --- Commands ---

    def show_skills(self, skills):
        if not skills:
            self.console.print("  [dim]No skills loaded.[/dim]")
            return
        table = Table(show_header=True, header_style="bold", border_style="dim",
                      padding=(0, 1))
        table.add_column("Skill", style="bold cyan")
        table.add_column("Type", style="dim", width=8)
        table.add_column("Description")
        table.add_column("Source", style="dim", width=8)
        for s in skills:
            table.add_row(f"/{s.name}" if s.type == "prompt" else s.name,
                          s.type, s.description, s.source)
        self.console.print(table)

    def show_help(self, invocable_skills=None):
        skill_lines = ""
        if invocable_skills:
            skill_lines = "\n[bold]Skills[/bold]  [dim](use /skillname [request])[/dim]\n"
            for s in invocable_skills:
                skill_lines += f"  /{s.name:<14s} {s.description}\n"

        self.console.print(Panel(
            '[bold]Commands[/bold]\n'
            '  /models          List models or switch (/model <name>)\n'
            '  /skills          List all loaded skills\n'
            '  /reload          Reload skills from disk\n'
            '  /metrics         Session statistics\n'
            '  /clear           Clear conversation\n'
            '  /cd <path>       Change working directory\n'
            '  /help            This help\n'
            '  /exit            Quit\n'
            + skill_lines +
            '\n'
            '[bold]Input[/bold]\n'
            '  Type [bold]"""[/bold] to enter multi-line mode, [bold]"""[/bold] again to submit\n'
            '\n'
            '[bold]Tools[/bold]\n'
            '  The model can autonomously read/write/edit files,\n'
            '  run shell commands, and search your codebase.\n'
            '  Write/edit/run require your confirmation.\n'
            '\n'
            '[bold]Custom skills[/bold]\n'
            '  Drop .md files in ~/.mycoder/skills/ — they load on next /reload or restart.\n'
            '\n'
            '[bold]DAG & Search[/bold]\n'
            '  /dag             Toggle DAG orchestration mode\n'
            '  /search <query>  Search past queries (FAISS)\n'
            '  /mcp-log         Show tracked MCP calls',
            title="Help", border_style="cyan", padding=(0, 2),
        ))

    # --- Messages ---

    def error(self, msg):
        self.console.print(f"  [error]{msg}[/error]")

    def info(self, msg):
        self.console.print(f"  [info]{msg}[/info]")

    def success(self, msg):
        self.console.print(f"  [success]{msg}[/success]")

    def confirm(self, msg):
        try:
            resp = self.console.input(f"  [warning]{msg} [dim](y/n)[/dim]: [/warning]")
            return resp.strip().lower() in ("y", "yes", "")
        except (KeyboardInterrupt, EOFError):
            return False


def _format_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _relative_time(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = (now - dt).days
        if days == 0:
            return "today"
        if days < 7:
            return f"{days}d ago"
        weeks = days // 7
        if weeks < 5:
            return f"{weeks}w ago"
        months = days // 30
        return f"{months}mo ago"
    except Exception:
        return ""
