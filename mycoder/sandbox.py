"""Sandbox enforcement — confine all file operations to a designated root directory.

External world access is only permitted through tracked MCP calls.
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

DANGEROUS_PATTERNS = [
    "rm -rf /", "sudo ", "chmod 777 /", "mkfs.", "dd if=/dev/",
    "> /dev/", "| sh", "| bash",
]


@dataclass
class MCPCall:
    tool: str
    args: dict
    timestamp: str
    result_summary: str = ""


class Sandbox:
    def __init__(self, root: str):
        self.root = os.path.realpath(os.path.abspath(root))
        self.mcp_log: list[MCPCall] = []

    def resolve(self, path: str) -> str:
        if os.path.isabs(path):
            resolved = os.path.realpath(path)
        else:
            resolved = os.path.realpath(os.path.join(self.root, path))

        if not self._is_within(resolved):
            raise PermissionError(
                f"Path '{path}' resolves outside sandbox '{self.root}'"
            )
        return resolved

    def check(self, path: str) -> bool:
        try:
            self.resolve(path)
            return True
        except PermissionError:
            return False

    def _is_within(self, resolved: str) -> bool:
        return resolved == self.root or resolved.startswith(self.root + os.sep)

    def track_mcp_call(self, tool: str, args: dict, result_summary: str = ""):
        call = MCPCall(
            tool=tool,
            args=args,
            timestamp=datetime.now().isoformat(),
            result_summary=result_summary[:200],
        )
        self.mcp_log.append(call)
        logger.info("MCP call: %s %s", tool, args)

    def get_mcp_log(self) -> list[MCPCall]:
        return list(self.mcp_log)

    def validate_command(self, command: str) -> tuple[bool, str]:
        for pattern in DANGEROUS_PATTERNS:
            if pattern in command:
                return False, f"Blocked dangerous pattern: {pattern}"
        return True, ""
