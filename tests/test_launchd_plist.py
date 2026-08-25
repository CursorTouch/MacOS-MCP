import plistlib

import macos_mcp.__main__ as server


def test_build_plist_escapes_special_characters(mocker, tmp_path):
    config_dir = tmp_path / "config & logs <local>"
    mocker.patch.object(server, "CONFIG_DIR", config_dir)
    args = ["/tmp/tool & helper", "serve", "--label=<local>", "a>b"]

    rendered = server._build_plist(args)
    parsed = plistlib.loads(rendered.encode("utf-8"))

    assert parsed == {
        "Label": "com.macos-mcp.server",
        "ProgramArguments": args,
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(config_dir / "server.log"),
        "StandardErrorPath": str(config_dir / "server.error.log"),
    }
