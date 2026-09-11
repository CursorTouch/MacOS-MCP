from types import SimpleNamespace

from click.testing import CliRunner

import macos_mcp.__main__ as server


def _completed(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _launchd_output(state="running", last_exit="(never exited)", signal=None):
    lines = [
        "gui/501/com.macos-mcp.server = {",
        f"    state = {state}",
        f"    last exit code = {last_exit}",
    ]
    if signal is not None:
        lines.append(f"    last terminating signal = {signal}")
    lines.append("}")
    return "\n".join(lines)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, duration):
        self.now += duration


def _patch_clock(mocker):
    clock = FakeClock()
    mocker.patch.object(server.time, "monotonic", side_effect=clock.monotonic)
    mocker.patch.object(server.time, "sleep", side_effect=clock.sleep)
    return clock


def _patch_install_paths(mocker, tmp_path, previous=None):
    config_dir = tmp_path / "config"
    agents_dir = tmp_path / "LaunchAgents"
    plist_path = agents_dir / "com.macos-mcp.server.plist"
    agents_dir.mkdir(parents=True)
    if previous is not None:
        plist_path.write_bytes(previous)
    mocker.patch.object(server, "CONFIG_DIR", config_dir)
    mocker.patch.object(server, "_LAUNCH_AGENTS_DIR", agents_dir)
    mocker.patch.object(server, "_PLIST_PATH", plist_path)
    mocker.patch.object(server, "_resolve_program", return_value=["/tmp/macos-mcp"])
    return plist_path


def test_launchctl_field_ignores_nested_state():
    output = """gui/501/com.macos-mcp.server = {
    state = running
    endpoints = {
        state = active
    }
    last exit code = (never exited)
}
"""

    assert server._launchctl_field(output, "state") == "running"
    assert server._launchctl_field(output, "last exit code") == "(never exited)"


def test_wait_for_launch_agent_accepts_delayed_healthy_endpoint(mocker):
    clock = _patch_clock(mocker)
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(stdout=_launchd_output()),
    )
    mocker.patch.object(
        server,
        "_server_accepting_connections",
        side_effect=lambda host, port: clock.now >= 3.4,
    )

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=10.0
    )

    assert started is True
    assert detail == "accepting connections"
    assert 3.4 <= clock.now < 3.6


def test_wait_for_launch_agent_reports_delayed_exit(mocker):
    clock = _patch_clock(mocker)

    def launchctl(*args):
        if clock.now < 3.8:
            return _completed(stdout=_launchd_output())
        return _completed(stdout=_launchd_output("spawn scheduled", "3"))

    mocker.patch.object(server, "_launchctl", side_effect=launchctl)
    mocker.patch.object(server, "_server_accepting_connections", return_value=False)

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=10.0
    )

    assert started is False
    assert "last exit code=3" in detail
    assert 3.8 <= clock.now < 4.0


def test_wait_for_launch_agent_times_out_without_endpoint(mocker):
    clock = _patch_clock(mocker)
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(stdout=_launchd_output()),
    )
    mocker.patch.object(server, "_server_accepting_connections", return_value=False)

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=0.5
    )

    assert started is False
    assert detail == "process ran but endpoint did not accept connections before timeout"
    assert clock.now == 0.5


def test_wait_for_launch_agent_retries_transient_print_failure(mocker):
    clock = _patch_clock(mocker)
    launchctl = mocker.patch.object(
        server,
        "_launchctl",
        side_effect=[
            _completed(returncode=1, stderr="temporary launchctl failure"),
            _completed(stdout=_launchd_output()),
        ],
    )
    mocker.patch.object(server, "_server_accepting_connections", return_value=True)

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=1.0
    )

    assert started is True
    assert detail == "accepting connections"
    assert launchctl.call_count == 2
    assert clock.now == 0.1


def test_launch_agent_loaded_retries_transient_print_failure(mocker):
    clock = _patch_clock(mocker)
    launchctl = mocker.patch.object(
        server,
        "_launchctl",
        side_effect=[
            _completed(returncode=1, stderr="temporary launchctl failure"),
            _completed(stdout=_launchd_output()),
        ],
    )

    loaded = server._launch_agent_loaded("gui/501", timeout=0.5)

    assert loaded is True
    assert launchctl.call_count == 2
    assert clock.now == 0.1


def test_wait_for_launch_agent_reports_signal_termination(mocker):
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(
            stdout=_launchd_output("spawn scheduled", signal="Terminated: 15")
        ),
    )
    listener = mocker.patch.object(
        server, "_server_accepting_connections", return_value=False
    )

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=0
    )

    assert started is False
    assert "last terminating signal=Terminated: 15" in detail
    listener.assert_not_called()


def test_wait_for_launch_agent_does_not_accept_unrelated_listener(mocker):
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(stdout=_launchd_output("not running")),
    )
    listener = mocker.patch.object(
        server, "_server_accepting_connections", return_value=True
    )

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=0
    )

    assert started is False
    assert detail == "state=not running"
    listener.assert_not_called()


def test_wait_for_launch_agent_unloaded_waits_through_sigtermed(mocker):
    clock = _patch_clock(mocker)
    launchctl = mocker.patch.object(
        server,
        "_launchctl",
        side_effect=[
            _completed(stdout=_launchd_output("SIGTERMed")),
            _completed(returncode=1, stderr="Could not find service"),
        ],
    )

    unloaded, detail = server._wait_for_launch_agent_unloaded(
        "gui/501", timeout=1.0
    )

    assert unloaded is True
    assert detail == "unloaded"
    assert launchctl.call_count == 2
    assert clock.now == 0.1


def test_install_rejects_explicit_port_conflict(mocker, tmp_path):
    plist_path = _patch_install_paths(mocker, tmp_path)
    mocker.patch.object(server, "_port_available", return_value=False)
    launchctl = mocker.patch.object(server, "_launchctl")

    result = CliRunner().invoke(server.main, ["install", "--port", "18133"])

    assert result.exit_code != 0
    assert "Port 18133 is already in use on 127.0.0.1." in result.output
    assert not plist_path.exists()
    launchctl.assert_not_called()


def test_fresh_install_failure_cleans_up_job_and_plist(mocker, tmp_path):
    plist_path = _patch_install_paths(mocker, tmp_path)
    mocker.patch.object(server, "_port_available", return_value=True)
    mocker.patch.object(
        server,
        "_wait_for_launch_agent_start",
        return_value=(False, "state=spawn scheduled, last exit code=3"),
    )
    mocker.patch.object(
        server, "_wait_for_launch_agent_unloaded", return_value=(True, "unloaded")
    )
    launchctl = mocker.patch.object(server, "_launchctl", return_value=_completed())

    result = CliRunner().invoke(server.main, ["install", "--port", "18133"])

    assert result.exit_code != 0
    assert not plist_path.exists()
    assert any(call.args[0] == "bootout" for call in launchctl.call_args_list)


def test_force_same_port_waits_for_old_listener_to_release(mocker, tmp_path):
    _patch_install_paths(mocker, tmp_path, previous=b"old plist")
    mocker.patch.object(server, "_launch_agent_loaded", return_value=True)
    mocker.patch.object(
        server, "_wait_for_launch_agent_unloaded", return_value=(True, "unloaded")
    )
    wait_port = mocker.patch.object(
        server, "_wait_for_port_available", return_value=True
    )
    mocker.patch.object(server, "_port_available", return_value=True)
    mocker.patch.object(
        server,
        "_wait_for_launch_agent_start",
        return_value=(True, "accepting connections"),
    )
    mocker.patch.object(server, "_launchctl", return_value=_completed())

    result = CliRunner().invoke(
        server.main, ["install", "--force", "--port", "18134"]
    )

    assert result.exit_code == 0
    wait_port.assert_called_once_with("127.0.0.1", 18134)


def test_force_failure_restores_old_plist_without_loading(mocker, tmp_path):
    previous = b"old plist bytes"
    plist_path = _patch_install_paths(mocker, tmp_path, previous=previous)
    mocker.patch.object(server, "_launch_agent_loaded", return_value=False)
    mocker.patch.object(server, "_port_available", return_value=True)
    mocker.patch.object(
        server,
        "_wait_for_launch_agent_start",
        return_value=(False, "state=spawn scheduled, last exit code=3"),
    )
    mocker.patch.object(
        server, "_wait_for_launch_agent_unloaded", return_value=(True, "unloaded")
    )
    launchctl = mocker.patch.object(server, "_launchctl", return_value=_completed())

    result = CliRunner().invoke(
        server.main, ["install", "--force", "--port", "18134"]
    )

    assert result.exit_code != 0
    assert plist_path.read_bytes() == previous
    bootstrap_calls = [
        call for call in launchctl.call_args_list if call.args[0] == "bootstrap"
    ]
    assert len(bootstrap_calls) == 1


def test_force_failure_restores_and_restarts_loaded_service(mocker, tmp_path):
    previous = b"old loaded plist bytes"
    plist_path = _patch_install_paths(mocker, tmp_path, previous=previous)
    mocker.patch.object(server, "_launch_agent_loaded", return_value=True)
    mocker.patch.object(server, "_wait_for_port_available", return_value=True)
    mocker.patch.object(server, "_port_available", return_value=True)
    mocker.patch.object(
        server, "_wait_for_launch_agent_unloaded", return_value=(True, "unloaded")
    )
    mocker.patch.object(
        server,
        "_wait_for_launch_agent_start",
        return_value=(False, "state=spawn scheduled, last exit code=3"),
    )
    running = mocker.patch.object(
        server, "_wait_for_launch_agent_running", return_value=(True, "running")
    )
    launchctl = mocker.patch.object(server, "_launchctl", return_value=_completed())

    result = CliRunner().invoke(
        server.main, ["install", "--force", "--port", "18134"]
    )

    assert result.exit_code != 0
    assert plist_path.read_bytes() == previous
    bootstrap_calls = [
        call for call in launchctl.call_args_list if call.args[0] == "bootstrap"
    ]
    assert len(bootstrap_calls) == 2
    running.assert_called_once()
