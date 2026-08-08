"""Tests for the MCP server."""

import pytest
from unittest.mock import MagicMock

from mycoder.mcp.server import MCPServer
from mycoder.sandbox import Sandbox


@pytest.fixture
def server(tmp_path):
    from mycoder.tools import ToolExecutor
    sandbox = Sandbox(str(tmp_path))
    executor = ToolExecutor(str(tmp_path), sandbox)
    return MCPServer(executor, sandbox), tmp_path


class TestMCPServer:
    def test_initialize(self, server):
        srv, _ = server
        resp = srv.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        assert resp["result"]["serverInfo"]["name"] == "mycoder"

    def test_tools_list(self, server):
        srv, _ = server
        resp = srv.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        assert "mycoder_read_file" in names
        assert "mycoder_write_file" in names

    def test_tool_call_read_file(self, server):
        srv, root = server
        (root / "test.txt").write_text("hello world")
        resp = srv.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "mycoder_read_file",
                "arguments": {"path": "test.txt"},
            },
        })
        assert "hello world" in resp["result"]["content"][0]["text"]

    def test_tool_call_unknown_tool(self, server):
        srv, _ = server
        resp = srv.handle_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        })
        assert "error" in resp

    def test_unknown_method(self, server):
        srv, _ = server
        resp = srv.handle_request({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "nonexistent/method",
            "params": {},
        })
        assert "error" in resp

    def test_mcp_call_tracked(self, server):
        srv, root = server
        (root / "tracked.txt").write_text("data")
        srv.handle_request({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "mycoder_read_file",
                "arguments": {"path": "tracked.txt"},
            },
        })
        log = srv.sandbox.get_mcp_log()
        assert len(log) == 1
        assert log[0].tool == "mycoder_read_file"

    def test_notification_returns_none(self, server):
        srv, _ = server
        resp = srv.handle_request({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        assert resp is None
