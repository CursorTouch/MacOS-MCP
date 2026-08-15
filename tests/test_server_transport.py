from click.testing import CliRunner

import macos_mcp.__main__ as server


def _run_serve(mocker, tmp_path, transport: str):
    """Invoke the serve command with FastMCP execution mocked."""
    config = tmp_path / "macos-mcp.toml"
    config.write_text("")
    mocker.patch.object(server, "validate_permissions")
    run = mocker.patch.object(server.mcp, "run")

    result = CliRunner().invoke(
        server.main,
        [
            "serve",
            "--transport",
            transport,
            "--host",
            "127.0.0.1",
            "--port",
            "18199",
            "--config",
            str(config),
        ],
    )

    assert result.exit_code == 0, result.output
    return run.call_args.kwargs


def test_streamable_http_runs_stateless(mocker, tmp_path):
    """Streamable HTTP must use stateless sessions to bound retained resources."""
    kwargs = _run_serve(mocker, tmp_path, "streamable-http")

    assert kwargs["transport"] == "streamable-http"
    assert kwargs["stateless_http"] is True


def test_sse_keeps_stateful_transport_default(mocker, tmp_path):
    """SSE must retain its existing stateful transport behavior."""
    kwargs = _run_serve(mocker, tmp_path, "sse")

    assert kwargs["transport"] == "sse"
    assert kwargs["stateless_http"] is False
