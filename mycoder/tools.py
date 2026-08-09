"""Tool definitions and execution for the coding assistant."""

import os
import subprocess

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file with line numbers. For large files, use offset/limit to read a section. Files over 300 lines are auto-truncated — use offset to read further.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "offset": {"type": "integer", "description": "Starting line number (1-based, default: 1)"},
                    "limit": {"type": "integer", "description": "Max lines to return (default: 300)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Full file content"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace an exact string in a file. The old_string must match exactly (including whitespace).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "old_string": {"type": "string", "description": "Exact text to find and replace"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command and return stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Grep for a pattern across files. Returns matching lines with paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex)"},
                    "path": {"type": "string", "description": "Directory to search (default: current dir)"},
                    "include": {"type": "string", "description": "File glob pattern, e.g. '*.py'"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories at a path with sizes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: current dir)"},
                    "recursive": {"type": "boolean", "description": "List recursively (default: false)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files by name pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Filename glob pattern, e.g. '*.py' or 'test_*'"},
                    "path": {"type": "string", "description": "Search root (default: current dir)"},
                },
                "required": ["pattern"],
            },
        },
    },
]

NEEDS_CONFIRMATION = {"write_file", "edit_file", "run_command"}
READ_ONLY_TOOLS = {"read_file", "search_files", "list_directory", "find_files"}

SAFE_COMMANDS = {
    "date", "whoami", "uname", "pwd", "hostname", "uptime", "which", "where",
    "echo", "cat", "head", "tail", "wc", "sort", "uniq", "diff", "file",
    "ls", "tree", "find", "grep", "rg", "fd", "ag",
    "git status", "git log", "git diff", "git branch", "git show", "git blame",
    "python --version", "python3 --version", "node --version", "go version",
    "rustc --version", "cargo --version", "uv --version", "pip --version",
}


def is_safe_command(command: str) -> bool:
    cmd = command.strip()
    for safe in SAFE_COMMANDS:
        if cmd == safe or cmd.startswith(safe + " "):
            return True
    return False


def _format_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


class ToolExecutor:
    def __init__(self, working_dir=None, sandbox=None):
        self.working_dir = working_dir or os.getcwd()
        self.sandbox = sandbox

    def execute(self, name, arguments):
        handlers = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "edit_file": self._edit_file,
            "run_command": self._run_command,
            "search_files": self._search_files,
            "list_directory": self._list_directory,
            "find_files": self._find_files,
        }

        handler = handlers.get(name)
        if not handler:
            return f"Unknown tool: {name}"

        try:
            return handler(**arguments)
        except TypeError as e:
            return f"Invalid arguments: {e}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    def _resolve(self, path):
        if self.sandbox:
            return self.sandbox.resolve(path)
        if os.path.isabs(path):
            return path
        return os.path.normpath(os.path.join(self.working_dir, path))

    def _read_file(self, path, offset=1, limit=300):
        path = self._resolve(path)
        if not os.path.exists(path):
            return f"File not found: {path}"
        if os.path.isdir(path):
            return f"Is a directory: {path}. Use list_directory instead."
        size = os.path.getsize(path)
        if size > 1_000_000:
            return f"File too large ({_format_size(size)}). Use search_files to find relevant sections."
        try:
            with open(path, "r", errors="replace") as f:
                all_lines = f.readlines()
        except UnicodeDecodeError:
            return f"Binary file: {path}"

        total = len(all_lines)
        offset = max(1, int(offset or 1))
        limit = min(int(limit or 300), 500)
        start = offset - 1
        end = min(start + limit, total)
        selected = all_lines[start:end]

        numbered = [f"{start + i + 1:4d} | {line.rstrip()}" for i, line in enumerate(selected)]
        result = "\n".join(numbered)

        if end < total:
            result += f"\n... ({total - end} more lines. Use offset={end + 1} to continue reading.)"
        if start > 0:
            result = f"(showing lines {offset}-{end} of {total})\n" + result

        return result

    def _write_file(self, path, content):
        path = self._resolve(path)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        return f"Wrote {lines} lines to {path}"

    def _edit_file(self, path, old_string, new_string):
        path = self._resolve(path)
        if not os.path.exists(path):
            return f"File not found: {path}"
        with open(path, "r") as f:
            content = f.read()
        if old_string not in content:
            return f"old_string not found in {path}. Read the file first to get the exact text."
        count = content.count(old_string)
        content = content.replace(old_string, new_string, 1)
        with open(path, "w") as f:
            f.write(content)
        extra = f" ({count - 1} more occurrences remain)" if count > 1 else ""
        return f"Replaced in {path}{extra}"

    def _run_command(self, command, timeout=30):
        if self.sandbox:
            ok, reason = self.sandbox.validate_command(command)
            if not ok:
                return f"Sandbox blocked: {reason}"
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.working_dir,
            )
            parts = []
            if result.stdout:
                parts.append(result.stdout)
            if result.stderr:
                parts.append(result.stderr)
            output = "\n".join(parts).strip()
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"

    def _search_files(self, pattern, path=".", include=""):
        path = self._resolve(path)
        cmd = ["grep", "-rn", "--color=never", "-I"]
        if include:
            cmd.extend(["--include", include])
        cmd.extend(["--", pattern, path])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15, cwd=self.working_dir
            )
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 80:
                    return "\n".join(lines[:80]) + f"\n... ({len(lines) - 80} more matches)"
                return result.stdout.strip()
            return "No matches found."
        except subprocess.TimeoutExpired:
            return "Search timed out."

    def _list_directory(self, path=".", recursive=False):
        path = self._resolve(path)
        if not os.path.exists(path):
            return f"Path not found: {path}"
        if not os.path.isdir(path):
            return f"Not a directory: {path}"

        if recursive:
            entries = []
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                rel = os.path.relpath(root, path)
                prefix = "" if rel == "." else rel + "/"
                for d in sorted(dirs):
                    entries.append(f"  {prefix}{d}/")
                for f in sorted(files):
                    if f.startswith("."):
                        continue
                    full = os.path.join(root, f)
                    entries.append(f"  {prefix}{f}  ({_format_size(os.path.getsize(full))})")
                if len(entries) > 200:
                    entries.append(f"  ... (truncated)")
                    break
            return "\n".join(entries) or "(empty)"

        entries = []
        for name in sorted(os.listdir(path)):
            if name.startswith("."):
                continue
            full = os.path.join(path, name)
            if os.path.isdir(full):
                entries.append(f"  {name}/")
            else:
                entries.append(f"  {name}  ({_format_size(os.path.getsize(full))})")
        return "\n".join(entries) or "(empty directory)"

    def _find_files(self, pattern, path="."):
        path = self._resolve(path)
        cmd = ["find", path, "-name", pattern, "-not", "-path", "*/.*", "-type", "f"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10, cwd=self.working_dir
            )
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 100:
                    return "\n".join(lines[:100]) + f"\n... ({len(lines) - 100} more)"
                return result.stdout.strip()
            return "No files found."
        except subprocess.TimeoutExpired:
            return "Search timed out."
