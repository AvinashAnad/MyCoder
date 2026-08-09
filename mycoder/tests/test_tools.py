"""Tests for tool execution with sandbox enforcement."""

import os
import pytest

from mycoder.sandbox import Sandbox
from mycoder.tools import ToolExecutor


@pytest.fixture
def sandboxed_env(tmp_path):
    sandbox = Sandbox(str(tmp_path))
    executor = ToolExecutor(str(tmp_path), sandbox)
    return executor, tmp_path


class TestReadFile:
    def test_read_existing_file(self, sandboxed_env):
        executor, root = sandboxed_env
        test_file = root / "hello.txt"
        test_file.write_text("line one\nline two\n")
        result = executor.execute("read_file", {"path": "hello.txt"})
        assert "line one" in result
        assert "line two" in result

    def test_read_missing_file(self, sandboxed_env):
        executor, _ = sandboxed_env
        result = executor.execute("read_file", {"path": "missing.txt"})
        assert "not found" in result.lower()

    def test_read_outside_sandbox_blocked(self, sandboxed_env):
        executor, _ = sandboxed_env
        result = executor.execute("read_file", {"path": "/etc/hosts"})
        assert "outside sandbox" in result.lower() or "error" in result.lower()


class TestWriteFile:
    def test_write_new_file(self, sandboxed_env):
        executor, root = sandboxed_env
        result = executor.execute("write_file", {"path": "new.txt", "content": "hello"})
        assert "wrote" in result.lower()
        assert (root / "new.txt").read_text() == "hello"

    def test_write_creates_parent_dirs(self, sandboxed_env):
        executor, root = sandboxed_env
        result = executor.execute("write_file", {"path": "a/b/c.txt", "content": "deep"})
        assert "wrote" in result.lower()
        assert (root / "a" / "b" / "c.txt").read_text() == "deep"


class TestEditFile:
    def test_edit_replaces_text(self, sandboxed_env):
        executor, root = sandboxed_env
        test_file = root / "edit_me.txt"
        test_file.write_text("foo bar baz")
        result = executor.execute("edit_file", {
            "path": "edit_me.txt",
            "old_string": "bar",
            "new_string": "qux",
        })
        assert "replaced" in result.lower()
        assert test_file.read_text() == "foo qux baz"

    def test_edit_missing_string(self, sandboxed_env):
        executor, root = sandboxed_env
        (root / "edit_me.txt").write_text("hello")
        result = executor.execute("edit_file", {
            "path": "edit_me.txt",
            "old_string": "missing",
            "new_string": "x",
        })
        assert "not found" in result.lower()


class TestRunCommand:
    def test_run_echo(self, sandboxed_env):
        executor, _ = sandboxed_env
        result = executor.execute("run_command", {"command": "echo hello"})
        assert "hello" in result

    def test_sandbox_blocks_dangerous(self, sandboxed_env):
        executor, _ = sandboxed_env
        result = executor.execute("run_command", {"command": "sudo rm -rf /"})
        assert "blocked" in result.lower() or "sandbox" in result.lower()


class TestSearchFiles:
    def test_search_finds_pattern(self, sandboxed_env):
        executor, root = sandboxed_env
        (root / "code.py").write_text("def hello():\n    return 42\n")
        result = executor.execute("search_files", {"pattern": "hello", "path": "."})
        assert "hello" in result

    def test_search_no_match(self, sandboxed_env):
        executor, root = sandboxed_env
        (root / "empty.txt").write_text("nothing here")
        result = executor.execute("search_files", {"pattern": "zzzzz", "path": "."})
        assert "no match" in result.lower()


class TestListDirectory:
    def test_list_shows_files(self, sandboxed_env):
        executor, root = sandboxed_env
        (root / "a.txt").write_text("a")
        (root / "b.txt").write_text("b")
        result = executor.execute("list_directory", {"path": "."})
        assert "a.txt" in result
        assert "b.txt" in result
