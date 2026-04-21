"""
macOS-MCP: MCP Server for macOS Desktop Interaction.

Provides tools to interact with the macOS desktop for automation.
"""
from macos_mcp.desktop.service import Desktop
from macos_mcp.desktop.views import Size
from macos_mcp.watchdog import WatchDog
from macos_mcp.permissions import validate_permissions
from contextlib import asynccontextmanager
from fastmcp.utilities.types import Image
from mcp.types import ToolAnnotations
from typing import Literal, Optional
from fastmcp import FastMCP, Context
from textwrap import dedent
import asyncio
import logging
import os
import signal
import sys
from threading import Lock
import click

logger = logging.getLogger(__name__)

desktop: Optional[Desktop] = None
screen_size: Optional[Size] = None
watchdog: Optional[WatchDog] = None
_shutdown_lock = Lock()
_shutdown_started = False

MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = 1920, 1080

instructions = dedent('''
macOS MCP server provides tools to interact directly with the macOS desktop, 
enabling operation of the desktop on the user's behalf.
''')


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
            logger.debug("Failed to stop watchdog during shutdown (may have already crashed)")
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

@asynccontextmanager
async def lifespan(app: FastMCP):
    """Runs initialization code before the server starts and cleanup code after it shuts down."""
    global desktop, screen_size, watchdog, _shutdown_started
    
    desktop = Desktop()
    screen_size = desktop.get_screen_size()
    _shutdown_started = False
    
    watchdog = WatchDog()
    watchdog.set_focus_callback(desktop.tree.on_focus_changed)
    try:
        watchdog.start()
    except Exception as e:
        logger.warning(f"Watchdog failed to start (non-fatal): {e}. Continuing without event monitoring.")
    
    try:
        await asyncio.sleep(0.5)  # Brief startup delay
        yield
    finally:
        _stop_watchdog()


mcp = FastMCP(name='macos-mcp', instructions=instructions, lifespan=lifespan)


@mcp.tool(
    name="App",
    description="Manages macOS applications with three modes: 'launch' (opens the application), 'resize' (adjusts active window size/position), 'switch' (brings specific app into focus).",
    annotations=ToolAnnotations(
        title="App",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False
    )
)
def app_tool(
    mode: Literal['launch', 'resize', 'switch']='launch',
    name: str | None = None,
    window_loc: list[int] | None = None,
    window_size: list[int] | None = None,
    ctx: Context = None
):
    return desktop.app(
        mode,
        name,
        tuple(window_loc) if window_loc else None,
        tuple(window_size) if window_size else None
    )


@mcp.tool(
    name='Shell',
    description="Execute commands on macOS. Modes: 'shell' (default) for bash/zsh commands, 'osascript' for AppleScript. Use for file system, process management, system operations, and automation scripts. SECURITY WARNING: Commands are executed with the same permissions as the terminal/application running this server. Review and understand all actions before execution, especially those involving file operations, system modifications, or external processes.",
    annotations=ToolAnnotations(
        title="Shell",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True
    )
)
def shell_tool(command: str, mode: Literal['shell', 'osascript'] = 'shell', timeout: int = 10, ctx: Context = None) -> str:
    response, status_code = desktop.execute_command(command, mode=mode, timeout=timeout)
    mode_label = 'AppleScript' if mode == 'osascript' else 'Shell'
    return f'{mode_label} Response: {response}\nStatus Code: {status_code}'


@mcp.tool(
    name='Snapshot',
    description='Captures complete desktop state including: focused window, open applications, interactive elements (buttons, text fields, links, menus with coordinates), and scrollable areas. Set use_vision=True to include screenshot with numbered annotations on interactive elements. Always call this first to understand the current desktop state before taking actions.',
    annotations=ToolAnnotations(
        title="Snapshot",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
def state_tool(use_vision: bool = False, ctx: Context = None):
    # Calculate scale factor to cap resolution at 1080p
    scale = 1.0
    if screen_size and screen_size.width > 0 and screen_size.height > 0:
        scale_width = MAX_IMAGE_WIDTH / screen_size.width if screen_size.width > MAX_IMAGE_WIDTH else 1.0
        scale_height = MAX_IMAGE_HEIGHT / screen_size.height if screen_size.height > MAX_IMAGE_HEIGHT else 1.0
        scale = min(scale_width, scale_height)
    
    desktop_state = desktop.get_state(use_vision=use_vision, as_bytes=True, scale=scale)
    interactive_elements = desktop_state.tree_state.interactive_elements_to_string()
    scrollable_elements = desktop_state.tree_state.scrollable_elements_to_string()
    windows = desktop_state.windows_to_string()
    active_window = desktop_state.active_window_to_string()
    
    return [dedent(f'''
    Focused Window:
    {active_window}

    Open Applications:
    {windows}

    List of Interactive Elements:
    {interactive_elements or 'No interactive elements found.'}

    List of Scrollable Elements:
    {scrollable_elements or 'No scrollable elements found.'}
    ''')] + ([Image(data=desktop_state.screenshot, format='png')] if use_vision and desktop_state.screenshot else [])


@mcp.tool(
    name='Click',
    description="Performs mouse clicks at specified coordinates [x, y]. Supports button types: 'left' for selection/activation, 'right' for context menus, 'middle'. Supports clicks: 0=hover only, 1=single click, 2=double click.",
    annotations=ToolAnnotations(
        title="Click",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False
    )
)
def click_tool(
    loc: list[int],
    button: Literal['left', 'right', 'middle'] = 'left',
    clicks: int = 1,
    ctx: Context = None
) -> str:
    if len(loc) != 2:
        raise ValueError("Location must be a list of exactly 2 integers [x, y]")
    x, y = loc[0], loc[1]
    desktop.click(loc=(x, y), button=button, clicks=clicks)
    num_clicks = {0: 'Hover', 1: 'Single', 2: 'Double'}
    return f'{num_clicks.get(clicks)} {button} clicked at ({x},{y}).'


@mcp.tool(
    name='Type',
    description="Types text at specified coordinates [x, y]. Set clear=True to clear existing text first. Set press_enter=True to submit after typing. Set caret_position to 'start', 'end', or 'idle' (default).",
    annotations=ToolAnnotations(
        title="Type",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False
    )
)
def type_tool(
    loc: list[int],
    text: str,
    clear: bool = False,
    caret_position: Literal['start', 'idle', 'end'] = 'idle',
    press_enter: bool = False,
    ctx: Context = None
) -> str:
    if len(loc) != 2:
        raise ValueError("Location must be a list of exactly 2 integers [x, y]")
    x, y = loc[0], loc[1]
    desktop.type(loc=(x, y), text=text, caret_position=caret_position, clear=clear, press_enter=press_enter)
    return f'Typed {text} at ({x},{y}).'


@mcp.tool(
    name='Scroll',
    description='Scrolls at coordinates [x, y] or current mouse position if loc=None. Type: vertical (default) or horizontal. Direction: up/down for vertical, left/right for horizontal. wheel_times controls scroll amount.',
    annotations=ToolAnnotations(
        title="Scroll",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
def scroll_tool(
    loc: list[int] = None,
    type: Literal['horizontal', 'vertical'] = 'vertical',
    direction: Literal['up', 'down', 'left', 'right'] = 'down',
    wheel_times: int = 1,
    ctx: Context = None
) -> str:
    if loc and len(loc) != 2:
        raise ValueError("Location must be a list of exactly 2 integers [x, y]")
    response = desktop.scroll(tuple(loc) if loc else None, type, direction, wheel_times)
    if response:
        return response
    return f'Scrolled {type} {direction} by {wheel_times} wheel times' + (f' at ({loc[0]},{loc[1]}).' if loc else '.')


@mcp.tool(
    name='Move',
    description='Moves mouse cursor to coordinates [x, y]. Set drag=True to perform a drag-and-drop operation from current position to target coordinates.',
    annotations=ToolAnnotations(
        title="Move",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
def move_tool(loc: list[int], drag: bool = False, ctx: Context = None) -> str:
    if len(loc) != 2:
        raise ValueError("loc must be a list of exactly 2 integers [x, y]")
    x, y = loc[0], loc[1]
    if drag:
        desktop.drag((x, y))
        return f'Dragged to ({x},{y}).'
    else:
        desktop.move((x, y))
        return f'Moved the mouse pointer to ({x},{y}).'


@mcp.tool(
    name='Shortcut',
    description='Executes keyboard shortcuts using key combinations separated by +. Examples: "command+c" (copy), "command+v" (paste), "command+tab" (switch apps), "command+space" (Spotlight). Note: Use "command" instead of "ctrl" on macOS.',
    annotations=ToolAnnotations(
        title="Shortcut",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False
    )
)
def shortcut_tool(shortcut: str, ctx: Context = None):
    desktop.shortcut(shortcut)
    return f"Pressed {shortcut}."


@mcp.tool(
    name='Wait',
    description='Pauses execution for specified duration in seconds. Use when waiting for: applications to launch, UI animations to complete, content to load. Helps ensure UI is ready before next interaction.',
    annotations=ToolAnnotations(
        title="Wait",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
def wait_tool(duration: int, ctx: Context = None) -> str:
    desktop.wait(duration)
    return f'Waited for {duration} seconds.'


@mcp.tool(
    name='Scrape',
    description='Fetch content from a URL. Performs a lightweight HTTP request and returns the page content as text.',
    annotations=ToolAnnotations(
        title="Scrape",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True
    )
)
def scrape_tool(url: str, ctx: Context = None) -> str:
    content = desktop.scrape(url)
    return f'URL:{url}\nContent:\n{content}'


@click.command()
@click.option(
    "--transport",
    help="The transport layer used by the MCP server.",
    type=click.Choice(['stdio', 'sse', 'streamable-http']),
    default='stdio'
)
@click.option(
    "--host",
    help="Host to bind the SSE/Streamable HTTP server.",
    default="localhost",
    type=str,
    show_default=True
)
@click.option(
    "--port",
    help="Port to bind the SSE/Streamable HTTP server.",
    default=8000,
    type=int,
    show_default=True
)
def main(transport, host, port):
    # Validate required permissions before starting server
    validate_permissions()

    previous_sigint_handler = None

    if transport == 'stdio':
        previous_sigint_handler = signal.getsignal(signal.SIGINT)

        def _handle_sigint(signum, frame):
            _force_exit(130)

        signal.signal(signal.SIGINT, _handle_sigint)

    match transport:
        case 'stdio':
            try:
                mcp.run(transport=transport, show_banner=False)
            except (KeyboardInterrupt, click.Abort):
                _force_exit(130)
            finally:
                if previous_sigint_handler is not None:
                    signal.signal(signal.SIGINT, previous_sigint_handler)
        case 'sse' | 'streamable-http':
            mcp.run(transport=transport, host=host, port=port, show_banner=False)
        case _:
            raise ValueError(f"Invalid transport: {transport}")


if __name__ == "__main__":
    main()
