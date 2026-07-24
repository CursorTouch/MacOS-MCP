"""Regression tests for ax.core.ExecuteCommand process handling.

These cover the three ways the old subprocess.run(capture_output=True)
implementation misbehaved under the stdio transport:

1. The child inherited fd 0 -- the JSON-RPC request stream -- so any command
   that reads stdin swallowed the client's protocol messages.
2. A backgrounded grandchild inherited the stdout *pipe* and held it open
   after the direct child exited, so a command that finished instantly was
   reported as having timed out.
3. On a real timeout only /bin/bash was killed, leaving its descendants alive.
"""

import os
import signal
import subprocess
import time

import pytest

from macos_mcp.ax.core import ExecuteCommand


@pytest.fixture
def sentinel(tmp_path):
    """A uniquely-named script that sleeps, plus a live-process query for it.

    The name is built at runtime so that `pgrep -f` cannot match the test
    runner's own command line.
    """
    mark = "macosmcptest" + str(os.getpid())
    script = tmp_path / f"{mark}.sh"
    script.write_text("#!/bin/bash\nsleep 61\n")
    script.chmod(0o755)
    mine = {str(os.getpid()), str(os.getppid())}

    def live():
        found = subprocess.run(
            ["pgrep", "-f", mark], capture_output=True, text=True
        ).stdout.split()
        out = []
        for pid in found:
            if pid in mine:
                continue
            state = subprocess.run(
                ["ps", "-o", "state=", "-p", pid], capture_output=True, text=True
            ).stdout.strip()
            if state and not state.startswith("Z"):  # ignore unreaped zombies
                out.append(pid)
        return out

    def reap():
        for pid in live():
            try:
                os.kill(int(pid), signal.SIGKILL)
            except OSError:
                pass

    yield str(script), live, reap
    reap()


class TestExecuteCommandOutput:
    def test_stdout_and_returncode(self):
        assert ExecuteCommand("echo hello") == ("hello", 0)

    def test_nonzero_returncode(self):
        assert ExecuteCommand("exit 7")[1] == 7

    def test_stderr_used_when_stdout_empty(self):
        assert "oops" in ExecuteCommand("echo oops >&2")[0]

    def test_stdout_preferred_over_stderr(self):
        assert ExecuteCommand("echo out; echo err >&2")[0] == "out"

    def test_non_ascii_output(self):
        assert ExecuteCommand("echo '日本語 🎉'")[0] == "日本語 🎉"

    def test_osascript_mode(self):
        assert ExecuteCommand('return "ok"', mode="osascript") == ("ok", 0)


class TestExecuteCommandStdin:
    def test_stdin_is_devnull(self):
        """A command that reads stdin must get EOF, not the caller's fd 0.

        Under the stdio transport fd 0 carries JSON-RPC requests; inheriting it
        lets the child consume protocol messages the server then never sees.
        """
        assert ExecuteCommand("cat", timeout=5) == ("", 0)

    def test_stdin_reader_does_not_block(self):
        start = time.monotonic()
        ExecuteCommand('read -r line; echo "got:$line"', timeout=10)
        assert time.monotonic() - start < 3


class TestExecuteCommandProcessGroup:
    def test_backgrounded_job_does_not_trigger_timeout(self, sentinel):
        """`cmd &` must not make an instant command look like it timed out."""
        script, live, _ = sentinel
        start = time.monotonic()
        result = ExecuteCommand(f"echo done; {script} &", timeout=8)
        elapsed = time.monotonic() - start

        assert result == ("done", 0)
        assert elapsed < 3, f"returned in {elapsed:.1f}s; pipe still held open"
        time.sleep(0.3)
        assert live(), "a deliberately backgrounded job should survive"

    def test_timeout_reaps_whole_process_tree(self, sentinel):
        script, live, _ = sentinel
        result = ExecuteCommand(f"{script} &\n{script}", timeout=2)

        assert result == ("Command timed out after 2 seconds", -1)
        time.sleep(0.6)
        assert live() == [], "descendants survived the timeout"

    def test_timeout_message_and_code(self):
        assert ExecuteCommand("sleep 30", timeout=2) == (
            "Command timed out after 2 seconds",
            -1,
        )
