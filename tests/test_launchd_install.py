from types import SimpleNamespace

import macos_mcp.__main__ as server


def _completed(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_launchctl_field_parses_launchd_status():
    output = """
        state = not running
        runs = 1
        last exit code = 78: EX_CONFIG
    """

    assert server._launchctl_field(output, "state") == "not running"
    assert server._launchctl_field(output, "last exit code") == "78: EX_CONFIG"


def test_wait_for_launch_agent_reports_immediate_exit(mocker):
    mocker.patch.object(server, "_server_accepting_connections", return_value=False)
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(
            stdout="state = not running\nlast exit code = 78: EX_CONFIG\n"
        ),
    )

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=0
    )

    assert started is False
    assert detail == "state=not running, last exit code=78: EX_CONFIG"


def test_wait_for_launch_agent_reports_signal_termination(mocker):
    mocker.patch.object(server, "_server_accepting_connections", return_value=False)
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(
            stdout="state = not running\nlast terminating signal = Terminated: 15\n"
        ),
    )

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=0
    )

    assert started is False
    assert detail == "state=not running, last terminating signal=Terminated: 15"


def test_wait_for_launch_agent_rejects_restart_after_failed_exit(mocker):
    mocker.patch.object(server, "_server_accepting_connections", return_value=False)
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(
            stdout="state = running\nlast exit code = 78: EX_CONFIG\n"
        ),
    )

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=0
    )

    assert started is False
    assert detail == "state=running, last exit code=78: EX_CONFIG"


def test_wait_for_launch_agent_accepts_running_process_during_slow_start(mocker):
    mocker.patch.object(server, "_server_accepting_connections", return_value=False)
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(stdout="state = running\nlast exit code = (never exited)\n"),
    )

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=0
    )

    assert started is True
    assert detail == "process is running; endpoint is still starting"


def test_wait_for_launch_agent_accepts_listening_running_agent(mocker):
    mocker.patch.object(server, "_server_accepting_connections", return_value=True)
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(stdout="state = running\nlast exit code = (never exited)\n"),
    )

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=0
    )

    assert started is True
    assert detail == "accepting connections"


def test_wait_for_launch_agent_does_not_accept_unrelated_listener(mocker):
    listener = mocker.patch.object(
        server, "_server_accepting_connections", return_value=True
    )
    mocker.patch.object(
        server,
        "_launchctl",
        return_value=_completed(
            stdout="state = not running\nlast exit code = 78: EX_CONFIG\n"
        ),
    )

    started, detail = server._wait_for_launch_agent_start(
        "gui/501", "127.0.0.1", 8000, timeout=0
    )

    assert started is False
    assert detail == "state=not running, last exit code=78: EX_CONFIG"
    listener.assert_not_called()
