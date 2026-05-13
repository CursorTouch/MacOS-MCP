"""Configuration loading and merge utilities for macos-mcp."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServerConfig:
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    allow_insecure_remote: bool = False
    auth_key: str | None = None
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None


@dataclass
class SecurityConfig:
    ip_allowlist: list[str] = field(default_factory=list)
    oauth_client_id: str | None = None
    oauth_client_secret: str | None = None


@dataclass
class ToolsConfig:
    exclude: list[str] = field(default_factory=list)


@dataclass
class MacOSMCPConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    source_path: Path | None = None


CONFIG_DIR = Path("~/.macos-mcp").expanduser()
CONFIG_FILE = CONFIG_DIR / "config.toml"


def discover_config_path(explicit_path: str | None) -> Path | None:
    """Find config path using precedence: explicit > ~/.macos-mcp/config.toml."""
    if explicit_path:
        return Path(explicit_path).expanduser()

    if CONFIG_FILE.exists():
        return CONFIG_FILE

    return None


def _list_of_strings(raw: object, key: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(i, str) for i in raw):
        raise ValueError(f"{key} must be an array of strings")
    return raw


def _strict_bool(raw: object, key: str) -> bool:
    if isinstance(raw, bool):
        return raw
    raise ValueError(f"{key} must be a TOML boolean, not {type(raw).__name__}")


def load_config(path: Path | None) -> MacOSMCPConfig:
    """Load and validate TOML config file. Returns defaults when path is None."""
    cfg = MacOSMCPConfig()
    if path is None:
        return cfg

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = tomllib.loads(path.read_text(encoding="utf-8"))

    server = data.get("server", {})
    security = data.get("security", {})

    _VALID_TRANSPORTS = {"stdio", "sse", "streamable-http"}
    if "transport" in server:
        t = str(server["transport"])
        if t not in _VALID_TRANSPORTS:
            raise ValueError(f"server.transport must be one of {_VALID_TRANSPORTS}, got {t!r}")
        cfg.server.transport = t
    if "host" in server:
        cfg.server.host = str(server["host"])
    if "port" in server:
        cfg.server.port = int(server["port"])
    if "allow_insecure_remote" in server:
        cfg.server.allow_insecure_remote = _strict_bool(
            server["allow_insecure_remote"], "server.allow_insecure_remote"
        )
    if "auth_key" in server:
        cfg.server.auth_key = str(server["auth_key"]) or None
    if "ssl_certfile" in server:
        raw = str(server["ssl_certfile"]) or None
        if raw:
            resolved = (path.parent / raw).resolve()
            cfg.server.ssl_certfile = str(resolved)
    if "ssl_keyfile" in server:
        raw = str(server["ssl_keyfile"]) or None
        if raw:
            resolved = (path.parent / raw).resolve()
            cfg.server.ssl_keyfile = str(resolved)

    if "ip_allowlist" in security:
        cfg.security.ip_allowlist = _list_of_strings(security["ip_allowlist"], "security.ip_allowlist")
    if "oauth_client_id" in security:
        cfg.security.oauth_client_id = str(security["oauth_client_id"]) or None
    if "oauth_client_secret" in security:
        cfg.security.oauth_client_secret = str(security["oauth_client_secret"]) or None

    tools = data.get("tools", {})
    if "exclude" in tools:
        cfg.tools.exclude = _list_of_strings(tools["exclude"], "tools.exclude")

    cfg.source_path = path
    return cfg
