"""
macOS-MCP: MCP Server for macOS Desktop Interaction.

Provides tools to interact with the macOS desktop for automation.
"""

from macos_mcp.desktop.service import Desktop
from macos_mcp.desktop.views import Size
from macos_mcp.watchdog import WatchDog
from macos_mcp.permissions import validate_permissions
from macos_mcp.infrastructure import (
    AuthKeyMiddleware,
    OAuthOnlyMiddleware,
    IPAllowlistMiddleware,
    PostHogAnalytics,
    Analytics,
    is_loopback_host,
    parse_ip_allowlist,
    validate_url,
    CONFIG_DIR,
    CONFIG_FILE,
    MacOSMCPConfig,
    discover_config_path,
    load_config,
    write_config,
    OAuthStore,
    build_oauth_routes,
    validate_oauth_token,
)
from click.core import ParameterSource
from contextlib import asynccontextmanager
from fastmcp.utilities.types import Image
from mcp.types import ToolAnnotations
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from typing import Any, Literal, Optional
from fastmcp import FastMCP, Context
from textwrap import dedent
import asyncio
import logging
import os
import secrets
import signal
import subprocess
import sys
from threading import Lock
import click

logger = logging.getLogger(__name__)

desktop: Optional[Desktop] = None
screen_size: Optional[Size] = None
watchdog: Optional[WatchDog] = None
analytics: Optional[Analytics] = None
_shutdown_lock = Lock()
_shutdown_started = False

MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = 1920, 1080

instructions = dedent("""
macOS MCP server provides tools to interact directly with the macOS desktop, 
enabling operation of the desktop on the user's behalf.
""")


def _stop_watchdog() -> None:
    """Stop the watchdog once, even if shutdown paths race."""
    global watchdog, _shutdown_started

    with _shutdown_lock:
        if _shutdown_started:
            return
        _shutdown_started = True

    if watchdog:
        try:
            if watchdog.is_running:
                watchdog.stop()
        except Exception:
            logger.debug(
                "Failed to stop watchdog during shutdown (may have already crashed)"
            )
        finally:
            watchdog = None


def _force_exit(exit_code: int = 130) -> None:
    """Flush stdio and exit immediately to avoid daemon-thread shutdown hangs."""
    _stop_watchdog()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass

    os._exit(exit_code)


class OptionsMiddleware:
    """ASGI middleware that intercepts OPTIONS requests and returns 200 OK."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http" and scope["method"] == "OPTIONS":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        [b"content-length", b"0"],
                        [b"access-control-allow-origin", b"*"],
                        [b"access-control-allow-methods", b"*"],
                        [b"access-control-allow-headers", b"*"],
                    ],
                }
            )
            await send({"type": "http.response.body", "body": b""})
        else:
            await self.app(scope, receive, send)


def _http_middleware(
    auth_key: str | None = None,
    ip_allowlist: list | None = None,
    oauth_validator=None,
) -> list:
    """Return ASGI middleware for HTTP transports including CORS and OPTIONS handling."""
    middleware = [
        Middleware(OptionsMiddleware),
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    ]
    if ip_allowlist:
        middleware.append(Middleware(IPAllowlistMiddleware, allowlist=ip_allowlist))
    if auth_key:
        middleware.append(Middleware(AuthKeyMiddleware, auth_key=auth_key, oauth_validator=oauth_validator))
    elif oauth_validator:
        middleware.append(Middleware(OAuthOnlyMiddleware, oauth_validator=oauth_validator))
    return middleware


@asynccontextmanager
async def lifespan(app: FastMCP):
    """Runs initialization code before the server starts and cleanup code after it shuts down."""
    global desktop, screen_size, watchdog, analytics, _shutdown_started

    if os.getenv("ANONYMIZED_TELEMETRY", "true").lower() != "false":
        analytics = PostHogAnalytics()

    desktop = Desktop()
    screen_size = desktop.get_screen_size()
    _shutdown_started = False

    watchdog = WatchDog()
    watchdog.set_focus_callback(desktop.tree.on_focus_changed)
    try:
        watchdog.start()
    except Exception as e:
        logger.warning(
            f"Watchdog failed to start (non-fatal): {e}. Continuing without event monitoring."
        )

    try:
        await asyncio.sleep(0.5)  # Brief startup delay
        yield
    finally:
        _stop_watchdog()
        if analytics:
            await analytics.close()


mcp = FastMCP(name="macos-mcp", instructions=instructions, lifespan=lifespan)


@mcp.tool(
    name="App",
    description="Manages macOS applications with four modes: 'launch' (opens the application), 'resize' (adjusts active window size), 'move' (repositions active window), 'switch' (brings specific app into focus).",
    annotations=ToolAnnotations(
        title="App",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
def app_tool(
    mode: Literal["launch", "resize", "move", "switch"] = "launch",
    name: str | None = None,
    window_loc: list[int] | None = None,
    window_size: list[int] | None = None,
    ctx: Context = None,
):
    return desktop.app(
        mode,
        name,
        tuple(window_loc) if window_loc else None,
        tuple(window_size) if window_size else None,
    )


@mcp.tool(
    name="Shell",
    description="Execute commands on macOS. Modes: 'shell' (default) for bash/zsh commands, 'osascript' for AppleScript. Use for file system, process management, system operations, and automation scripts. SECURITY WARNING: Commands are executed with the same permissions as the terminal/application running this server. Review and understand all actions before execution, especially those involving file operations, system modifications, or external processes.",
    annotations=ToolAnnotations(
        title="Shell",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
def shell_tool(
    command: str,
    mode: Literal["shell", "osascript"] = "shell",
    timeout: int = 10,
    ctx: Context = None,
) -> str:
    response, status_code = desktop.execute_command(command, mode=mode, timeout=timeout)
    mode_label = "AppleScript" if mode == "osascript" else "Shell"
    return f"{mode_label} Response: {response}\nStatus Code: {status_code}"


@mcp.tool(
    name="Snapshot",
    description="Captures complete desktop state including: focused window, open applications, interactive elements (buttons, text fields, links, menus with coordinates), and scrollable areas. Set use_vision=True to include screenshot with numbered annotations on interactive elements. Always call this first to understand the current desktop state before taking actions.",
    annotations=ToolAnnotations(
        title="Snapshot",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def state_tool(use_vision: bool = False, ctx: Context = None):
    # Calculate scale factor to cap resolution at 1080p
    scale = 1.0
    if screen_size and screen_size.width > 0 and screen_size.height > 0:
        scale_width = (
            MAX_IMAGE_WIDTH / screen_size.width
            if screen_size.width > MAX_IMAGE_WIDTH
            else 1.0
        )
        scale_height = (
            MAX_IMAGE_HEIGHT / screen_size.height
            if screen_size.height > MAX_IMAGE_HEIGHT
            else 1.0
        )
        scale = min(scale_width, scale_height)

    desktop_state = desktop.get_state(use_vision=use_vision, as_bytes=True, scale=scale)
    interactive_elements = desktop_state.tree_state.interactive_elements_to_string()
    scrollable_elements = desktop_state.tree_state.scrollable_elements_to_string()
    windows = desktop_state.windows_to_string()
    active_window = desktop_state.active_window_to_string()

    return [
        dedent(f"""
    Focused Window:
    {active_window}

    Open Applications:
    {windows}

    List of Interactive Elements:
    {interactive_elements or "No interactive elements found."}

    List of Scrollable Elements:
    {scrollable_elements or "No scrollable elements found."}
    """)
    ] + (
        [Image(data=desktop_state.screenshot, format="png")]
        if use_vision and desktop_state.screenshot
        else []
    )


@mcp.tool(
    name="Click",
    description="Performs mouse clicks at specified coordinates [x, y]. Supports button types: 'left' for selection/activation, 'right' for context menus, 'middle'. Supports clicks: 0=hover only, 1=single click, 2=double click.",
    annotations=ToolAnnotations(
        title="Click",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
def click_tool(
    loc: list[int],
    button: Literal["left", "right", "middle"] = "left",
    clicks: int = 1,
    ctx: Context = None,
) -> str:
    if len(loc) != 2:
        raise ValueError("Location must be a list of exactly 2 integers [x, y]")
    x, y = loc[0], loc[1]
    desktop.click(loc=(x, y), button=button, clicks=clicks)
    num_clicks = {0: "Hover", 1: "Single", 2: "Double"}
    return f"{num_clicks.get(clicks)} {button} clicked at ({x},{y})."


@mcp.tool(
    name="Type",
    description="Types text at specified coordinates [x, y]. Set clear=True to clear existing text first. Set press_enter=True to submit after typing. Set caret_position to 'start', 'end', or 'idle' (default).",
    annotations=ToolAnnotations(
        title="Type",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
def type_tool(
    loc: list[int],
    text: str,
    clear: bool = False,
    caret_position: Literal["start", "idle", "end"] = "idle",
    press_enter: bool = False,
    ctx: Context = None,
) -> str:
    if len(loc) != 2:
        raise ValueError("Location must be a list of exactly 2 integers [x, y]")
    x, y = loc[0], loc[1]
    desktop.type(
        loc=(x, y),
        text=text,
        caret_position=caret_position,
        clear=clear,
        press_enter=press_enter,
    )
    return f"Typed {text} at ({x},{y})."


@mcp.tool(
    name="Scroll",
    description="Scrolls at coordinates [x, y] or current mouse position if loc=None. Type: vertical (default) or horizontal. Direction: up/down for vertical, left/right for horizontal. wheel_times controls scroll amount.",
    annotations=ToolAnnotations(
        title="Scroll",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def scroll_tool(
    loc: list[int] = None,
    type: Literal["horizontal", "vertical"] = "vertical",
    direction: Literal["up", "down", "left", "right"] = "down",
    wheel_times: int = 1,
    ctx: Context = None,
) -> str:
    if loc and len(loc) != 2:
        raise ValueError("Location must be a list of exactly 2 integers [x, y]")
    response = desktop.scroll(tuple(loc) if loc else None, type, direction, wheel_times)
    if response:
        return response
    return f"Scrolled {type} {direction} by {wheel_times} wheel times" + (
        f" at ({loc[0]},{loc[1]})." if loc else "."
    )


@mcp.tool(
    name="Move",
    description="Moves mouse cursor to coordinates [x, y]. Set drag=True to perform a drag-and-drop operation from current position to target coordinates.",
    annotations=ToolAnnotations(
        title="Move",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def move_tool(loc: list[int], drag: bool = False, ctx: Context = None) -> str:
    if len(loc) != 2:
        raise ValueError("loc must be a list of exactly 2 integers [x, y]")
    x, y = loc[0], loc[1]
    if drag:
        desktop.drag((x, y))
        return f"Dragged to ({x},{y})."
    else:
        desktop.move((x, y))
        return f"Moved the mouse pointer to ({x},{y})."


@mcp.tool(
    name="Shortcut",
    description='Executes keyboard shortcuts using key combinations separated by +. Examples: "command+c" (copy), "command+v" (paste), "command+tab" (switch apps), "command+space" (Spotlight). Note: Use "command" instead of "ctrl" on macOS.',
    annotations=ToolAnnotations(
        title="Shortcut",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
def shortcut_tool(shortcut: str, ctx: Context = None):
    desktop.shortcut(shortcut)
    return f"Pressed {shortcut}."


@mcp.tool(
    name="Wait",
    description="Pauses execution for specified duration in seconds. Use when waiting for: applications to launch, UI animations to complete, content to load. Helps ensure UI is ready before next interaction.",
    annotations=ToolAnnotations(
        title="Wait",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def wait_tool(duration: int, ctx: Context = None) -> str:
    desktop.wait(duration)
    return f"Waited for {duration} seconds."


@mcp.tool(
    name="Scrape",
    description="Fetch content from a URL. Performs a lightweight HTTP request and returns the page content as text.",
    annotations=ToolAnnotations(
        title="Scrape",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
def scrape_tool(url: str, ctx: Context = None) -> str:
    validate_url(url)
    content = desktop.scrape(url)
    return f"URL:{url}\nContent:\n{content}"


@mcp.tool(
    name="Notification",
    description="Sends a macOS notification banner with a message, title, optional subtitle, and optional sound.",
    annotations=ToolAnnotations(
        title="Notification",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
def notification_tool(
    message: str,
    title: str = "Notification",
    subtitle: str | None = None,
    sound: Literal[
        "Glass",
        "Ping",
        "Basso",
        "Tink",
        "Funk",
        "Bottle",
        "Frog",
        "Hero",
        "Morse",
        "Pop",
        "Purr",
        "Sosumi",
        "Submarine",
    ]
    | None = None,
    ctx: Context = None,
) -> str:
    return desktop.notify(message, title, subtitle, sound)


def _param_explicit(ctx: click.Context, name: str) -> bool:
    src = ctx.get_parameter_source(name)
    return src in {ParameterSource.COMMANDLINE, ParameterSource.ENVIRONMENT}


def _choose_value(ctx: click.Context, name: str, cli_value, config_value, default_value):
    if _param_explicit(ctx, name):
        return cli_value
    if config_value is not None:
        return config_value
    return default_value


@click.group()
def main():
    """macOS-MCP: MCP server for macOS desktop automation."""


@main.command()
@click.pass_context
@click.option(
    "--transport",
    help="The transport layer used by the MCP server.",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
)
@click.option(
    "--host",
    help="Host to bind the SSE/Streamable HTTP server.",
    default="127.0.0.1",
    type=str,
    show_default=True,
)
@click.option(
    "--port",
    help="Port to bind the SSE/Streamable HTTP server.",
    default=8000,
    type=int,
    show_default=True,
)
@click.option(
    "--debug",
    help="Enable debug mode to provide verbose logging for troubleshooting.",
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "--config",
    help="Path to macos-mcp.toml config file.",
    default=None,
    type=click.Path(dir_okay=False),
    show_default=False,
)
@click.option(
    "--auth-key",
    help="Bearer token required on all HTTP requests. Can also be set via MACOS_MCP_AUTH_KEY.",
    default=None,
    envvar="MACOS_MCP_AUTH_KEY",
    type=str,
    show_default=False,
)
@click.option(
    "--allow-insecure-remote",
    help="Allow binding to non-loopback addresses without authentication (not recommended).",
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "--ip-allowlist",
    help="Comma-separated list of allowed client IPs or CIDR ranges (e.g. '10.0.0.0/8,192.168.1.5'). IPv4 and IPv6 supported.",
    default=None,
    envvar="MACOS_MCP_IP_ALLOWLIST",
    type=str,
    show_default=False,
)
@click.option(
    "--ssl-certfile",
    help="Path to TLS certificate file (.pem) for HTTPS. Requires --ssl-keyfile.",
    default=None,
    envvar="MACOS_MCP_SSL_CERTFILE",
    type=str,
    show_default=False,
)
@click.option(
    "--ssl-keyfile",
    help="Path to TLS private key file (.pem) for HTTPS. Requires --ssl-certfile.",
    default=None,
    envvar="MACOS_MCP_SSL_KEYFILE",
    type=str,
    show_default=False,
)
@click.option(
    "--oauth-client-id",
    help="OAuth client ID (pre-provisioned confidential client). Requires --oauth-client-secret.",
    default=None,
    envvar="MACOS_MCP_OAUTH_CLIENT_ID",
    type=str,
    show_default=False,
)
@click.option(
    "--oauth-client-secret",
    help="OAuth client secret. Requires --oauth-client-id.",
    default=None,
    envvar="MACOS_MCP_OAUTH_CLIENT_SECRET",
    type=str,
    show_default=False,
)
def serve(ctx, transport, host, port, debug, config, auth_key, allow_insecure_remote, ip_allowlist, ssl_certfile, ssl_keyfile, oauth_client_id, oauth_client_secret):
    # Validate required permissions before starting server
    validate_permissions()

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastmcp"]:
            logging.getLogger(name).setLevel(logging.DEBUG)

    # Load config file and merge with CLI flags (CLI wins)
    config_path = discover_config_path(config)
    try:
        cfg = load_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc))

    transport = _choose_value(ctx, "transport", transport, cfg.server.transport, "stdio")
    host = _choose_value(ctx, "host", host, cfg.server.host, "127.0.0.1")
    port = int(_choose_value(ctx, "port", port, cfg.server.port, 8000))
    auth_key = _choose_value(ctx, "auth_key", auth_key, cfg.server.auth_key, None)
    allow_insecure_remote = bool(
        _choose_value(ctx, "allow_insecure_remote", allow_insecure_remote, cfg.server.allow_insecure_remote, False)
    )
    ssl_certfile = _choose_value(ctx, "ssl_certfile", ssl_certfile, cfg.server.ssl_certfile, None)
    ssl_keyfile = _choose_value(ctx, "ssl_keyfile", ssl_keyfile, cfg.server.ssl_keyfile, None)
    oauth_client_id = _choose_value(ctx, "oauth_client_id", oauth_client_id, cfg.security.oauth_client_id, None)
    oauth_client_secret = _choose_value(
        ctx, "oauth_client_secret", oauth_client_secret, cfg.security.oauth_client_secret, None
    )

    cli_allowlist = [e.strip() for e in ip_allowlist.split(",")] if ip_allowlist else None
    allowlist_entries = cli_allowlist if _param_explicit(ctx, "ip_allowlist") else cfg.security.ip_allowlist

    if bool(ssl_certfile) != bool(ssl_keyfile):
        raise click.ClickException("--ssl-certfile and --ssl-keyfile must be provided together.")

    if bool(oauth_client_id) != bool(oauth_client_secret):
        raise click.ClickException("OAuth requires both --oauth-client-id and --oauth-client-secret.")

    parsed_allowlist = None
    if allowlist_entries:
        try:
            parsed_allowlist = parse_ip_allowlist(allowlist_entries)
        except ValueError as exc:
            raise click.ClickException(f"Invalid ip_allowlist: {exc}")

    configured_oauth = bool(oauth_client_id and oauth_client_secret)

    if (
        transport != "stdio"
        and not is_loopback_host(host)
        and not auth_key
        and not configured_oauth
        and not allow_insecure_remote
    ):
        raise click.ClickException(
            f"Refusing to bind HTTP transport to '{host}' without authentication.\n"
            "  Use --auth-key <token> or --oauth-client-id/--oauth-client-secret.\n"
            "  Or pass --allow-insecure-remote to explicitly allow unauthenticated access (not recommended)."
        )

    if (auth_key or allowlist_entries) and transport == "stdio":
        logger.warning("auth_key / ip_allowlist have no effect on stdio transport")

    # Set up OAuth routes if configured (HTTP transports only)
    oauth_validator = None
    if configured_oauth and transport != "stdio":
        oauth_store = OAuthStore()
        scheme = "https" if (ssl_certfile and ssl_keyfile) else "http"
        issuer = f"{scheme}://{host}:{port}"
        routes = build_oauth_routes(
            store=oauth_store,
            issuer=issuer,
            configured_client_id=oauth_client_id,
            configured_client_secret=oauth_client_secret,
        )
        for path, (handler, methods) in routes.items():
            mcp.custom_route(path, methods=methods)(handler)
        oauth_validator = lambda tok: validate_oauth_token(oauth_store, tok)  # noqa: E731

    for tool_name in cfg.tools.exclude:
        try:
            mcp.remove_tool(tool_name)
            logger.debug(f"Excluded tool: {tool_name}")
        except Exception:
            logger.warning(f"Could not exclude tool '{tool_name}' — not found")

    previous_sigint_handler = None

    if transport == "stdio":
        previous_sigint_handler = signal.getsignal(signal.SIGINT)

        def _handle_sigint(signum, frame):
            _force_exit(130)

        signal.signal(signal.SIGINT, _handle_sigint)

    match transport:
        case "stdio":
            try:
                mcp.run(transport=transport, show_banner=False)
            except (KeyboardInterrupt, click.Abort):
                _force_exit(130)
            finally:
                if previous_sigint_handler is not None:
                    signal.signal(signal.SIGINT, previous_sigint_handler)
        case "sse" | "streamable-http":
            uvicorn_config: dict = {}
            if ssl_certfile and ssl_keyfile:
                uvicorn_config["ssl_certfile"] = ssl_certfile
                uvicorn_config["ssl_keyfile"] = ssl_keyfile
            mcp.run(
                transport=transport,
                host=host,
                port=port,
                show_banner=False,
                middleware=_http_middleware(auth_key=auth_key, ip_allowlist=parsed_allowlist, oauth_validator=oauth_validator),
                uvicorn_config=uvicorn_config or None,
            )
        case _:
            raise ValueError(f"Invalid transport: {transport}")


@main.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="sse",
    show_default=True,
    help="Transport mode to configure. Saves the choice to config.toml.",
)
@click.option(
    "--host",
    default="0.0.0.0",
    show_default=True,
    help="Host to bind the server to.",
)
@click.option(
    "--port",
    default=8000,
    show_default=True,
    type=int,
    help="Port to bind the server to.",
)
@click.option("--with-tls", is_flag=True, help="Generate a self-signed TLS certificate and key.")
@click.option("--force", is_flag=True, help="Overwrite existing credentials without prompting.")
def auth(transport: str, host: str, port: int, with_tls: bool, force: bool) -> None:
    """Generate an auth key (and optionally TLS certs) and save to ~/.macos-mcp/config.toml."""
    config_path = CONFIG_FILE

    cfg = load_config(config_path) if config_path.exists() else MacOSMCPConfig()

    if cfg.server.auth_key and not force:
        click.echo(f"Auth key already set in {config_path}. Use --force to regenerate.")
        return

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    new_key = secrets.token_urlsafe(32)
    cfg.server.auth_key = new_key
    cfg.server.transport = transport
    cfg.server.host = host
    cfg.server.port = port
    click.echo(f"Generated auth key: {new_key}")

    if with_tls:
        if transport == "stdio":
            raise click.ClickException("TLS has no effect on stdio transport.")
        cert_path = CONFIG_DIR / "cert.pem"
        key_path = CONFIG_DIR / "key.pem"
        click.echo("Generating self-signed TLS certificate (4096-bit RSA, 365 days)...")
        result = subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:4096",
                "-keyout", str(key_path),
                "-out", str(cert_path),
                "-days", "365", "-nodes",
                "-subj", "/CN=macos-mcp",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise click.ClickException(f"openssl failed:\n{result.stderr.strip()}")
        cfg.server.ssl_certfile = str(cert_path)
        cfg.server.ssl_keyfile = str(key_path)
        click.echo(f"  cert → {cert_path}")
        click.echo(f"  key  → {key_path}")

    write_config(cfg, config_path)
    click.echo(f"\nSaved to {config_path}")

    if transport == "stdio":
        click.echo("\n─── Claude Desktop config (stdio) ───")
        click.echo(
            """\
{
  "mcpServers": {
    "macos-mcp": {
      "command": "uvx",
      "args": ["macos-mcp", "serve"]
    }
  }
}"""
        )
        return

    scheme = "https" if with_tls else "http"
    mcp_url = f"{scheme}://{host}:{port}/mcp/"
    sse_url = f"{scheme}://{host}:{port}/sse"

    click.echo("\n─── Start the server ───")
    click.echo(f"  macos-mcp serve")

    if transport == "sse":
        click.echo("\n─── Claude Desktop config (SSE) ───")
        click.echo(
            f"""\
{{
  "mcpServers": {{
    "macos-mcp": {{
      "type": "sse",
      "url": "{sse_url}",
      "headers": {{ "Authorization": "Bearer {new_key}" }}
    }}
  }}
}}"""
        )
    else:
        click.echo("\n─── Claude Desktop config (Streamable HTTP) ───")
        click.echo(
            f"""\
{{
  "mcpServers": {{
    "macos-mcp": {{
      "type": "http",
      "url": "{mcp_url}",
      "headers": {{ "Authorization": "Bearer {new_key}" }}
    }}
  }}
}}"""
        )


if __name__ == "__main__":
    main()
