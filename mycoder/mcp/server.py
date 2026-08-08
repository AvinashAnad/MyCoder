"""MCP server — JSON-RPC over stdin/stdout exposing MyCoder tools.

All external access is tracked through the sandbox's MCP log.
"""

import json
import sys

MCP_TOOLS = [
    {
        "name": "mycoder_read_file",
        "description": "Read a file from the MyCoder sandbox",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path within sandbox"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "mycoder_write_file",
        "description": "Write a file in the MyCoder sandbox",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "File content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "mycoder_edit_file",
        "description": "Edit a file in the MyCoder sandbox",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "mycoder_run_command",
        "description": "Run a shell command in the sandbox",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command"},
                "timeout": {"type": "integer", "description": "Timeout in seconds"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "mycoder_search_files",
        "description": "Search files by regex pattern in the sandbox",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "include": {"type": "string"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "mycoder_list_directory",
        "description": "List directory contents in the sandbox",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "recursive": {"type": "boolean"},
            },
        },
    },
    {
        "name": "mycoder_find_files",
        "description": "Find files by glob pattern in the sandbox",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["pattern"],
        },
    },
]

TOOL_MAP = {
    "mycoder_read_file": "read_file",
    "mycoder_write_file": "write_file",
    "mycoder_edit_file": "edit_file",
    "mycoder_run_command": "run_command",
    "mycoder_search_files": "search_files",
    "mycoder_list_directory": "list_directory",
    "mycoder_find_files": "find_files",
}


class MCPServer:
    def __init__(self, tool_executor, sandbox):
        self.executor = tool_executor
        self.sandbox = sandbox

    def handle_request(self, request: dict) -> dict | None:
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "notifications/initialized":
            return None

        if method == "initialize":
            return self._response(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "mycoder", "version": "0.1.0"},
            })

        if method == "tools/list":
            return self._response(req_id, {"tools": MCP_TOOLS})

        if method == "tools/call":
            return self._handle_tool_call(req_id, params)

        return self._error(req_id, -32601, f"Unknown method: {method}")

    def _handle_tool_call(self, req_id, params):
        name = params.get("name", "")
        args = params.get("arguments", {})

        internal_name = TOOL_MAP.get(name)
        if not internal_name:
            return self._error(req_id, -32602, f"Unknown tool: {name}")

        if self.sandbox:
            self.sandbox.track_mcp_call(name, args)

        result = self.executor.execute(internal_name, args)

        return self._response(req_id, {
            "content": [{"type": "text", "text": result}],
            "isError": False,
        })

    def run_stdio(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                pass

    def _response(self, req_id, result):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _error(self, req_id, code, message):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
