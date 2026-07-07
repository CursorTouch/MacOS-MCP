"""Tau extension that bridges to the macOS-MCP server over stdio.

Starts `uv run macos-mcp` lazily on first tool call and forwards a small set
of Tau-native tools to the existing macOS-MCP MCP tools. Mirrors the Pi
extension at extensions/macos-mcp.ts — same tool set, same server, no
changes to the macOS-MCP server internals.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from tau.tool.types import Tool, ToolContext, ToolExecutionMode, ToolInvocation, ToolKind, ToolResult


def _is_macos_mcp_root(path: Path) -> bool:
    return (path / "src" / "macos_mcp" / "__main__.py").exists() and (path / "pyproject.toml").exists()


def _find_project_root() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        os.environ.get("MACOS_MCP_ROOT"),
        str(Path.cwd()),
        str(Path.cwd() / "MacOS-MCP"),
        str(here.parents[2]) if len(here.parents) >= 3 else None,
        str(here.parents[3]) if len(here.parents) >= 4 else None,
    ]
    for candidate in candidates:
        if candidate and _is_macos_mcp_root(Path(candidate)):
            return Path(candidate)
    raise RuntimeError(
        "Could not find the macOS-MCP project root. Run tau from the MacOS-MCP checkout, "
        "install this package via `tau install git+https://github.com/CursorTouch/MacOS-MCP`, "
        "or set MACOS_MCP_ROOT=/path/to/MacOS-MCP."
    )


def _result_to_text(result: Any) -> str:
    parts: list[str] = []
    for item in result.content or []:
        item_type = getattr(item, "type", None)
        if item_type == "text":
            text = getattr(item, "text", "") or ""
            if text:
                parts.append(text)
        elif item_type == "image":
            mime_type = getattr(item, "mimeType", "image")
            parts.append(f"[image omitted: {mime_type}]")
        else:
            parts.append(repr(item))
    return "\n".join(parts) if parts else str(result)


class _McpBridge:
    """Owns a single long-lived MCP stdio session, serialized behind a queue.

    The MCP SDK's stdio_client/ClientSession are anyio task-group-backed
    context managers that must enter/exit in the same asyncio task, so the
    session is owned by one background task and calls are forwarded to it.
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._task: asyncio.Task | None = None
        self._requests: asyncio.Queue = asyncio.Queue()
        self._ready = asyncio.Event()
        self._error: Exception | None = None

    async def _run(self) -> None:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(
            command="uv",
            args=["run", "--quiet", "macos-mcp"],
            cwd=str(self._project_root),
        )
        log_dir = self._project_root / ".tau" / "extensions" / "macos-mcp"
        log_dir.mkdir(parents=True, exist_ok=True)
        try:
            # `uv`'s own build/progress output and the server's own stderr
            # logging default to the parent's stderr fd. Tau owns the real
            # terminal for full-screen TUI rendering, so anything writing to
            # that fd outside Tau's render loop corrupts the display. Redirect
            # to a log file instead of letting the child inherit our stderr.
            with open(log_dir / "server.log", "a", encoding="utf-8") as errlog:
                async with stdio_client(params, errlog=errlog) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self._ready.set()
                        while True:
                            item = await self._requests.get()
                            if item is None:
                                break
                            tool_name, arguments, future = item
                            try:
                                result = await session.call_tool(tool_name, arguments)
                                if not future.done():
                                    future.set_result(result)
                            except Exception as exc:  # noqa: BLE001
                                if not future.done():
                                    future.set_exception(exc)
        except Exception as exc:  # noqa: BLE001
            self._error = exc
            self._ready.set()

    async def _ensure_started(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())
        await self._ready.wait()
        if self._error is not None:
            raise RuntimeError(f"Failed to start macos-mcp: {self._error}") from self._error

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        await self._ensure_started()
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        await self._requests.put((name, arguments, future))
        return await future

    async def close(self) -> None:
        if self._task is not None:
            await self._requests.put(None)
            await self._task
            self._task = None


class _McpTool(Tool):
    """Base for tools that forward one call to the macos-mcp MCP server."""

    mcp_tool_name: str

    def __init__(self, bridge: _McpBridge, name: str, description: str, schema: type[BaseModel]) -> None:
        super().__init__(
            name=name,
            description=description,
            schema=schema,
            kind=ToolKind.Execute,
            execution_mode=ToolExecutionMode.Sequential,
        )
        self._bridge = bridge

    def _build_arguments(self, params: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in params.items() if v is not None}

    async def execute(
        self,
        invocation: ToolInvocation,
        tool_execution_update_callback=None,
        signal=None,
        context: ToolContext | None = None,
    ) -> ToolResult:
        arguments = self._build_arguments(invocation.params)
        try:
            result = await self._bridge.call_tool(self.mcp_tool_name, arguments)
        except Exception as exc:  # noqa: BLE001
            return ToolResult.error(invocation.id, str(exc))
        text = _result_to_text(result)
        if getattr(result, "isError", False):
            return ToolResult.error(invocation.id, text)
        return ToolResult.ok(invocation.id, text)


class _SnapshotSchema(BaseModel):
    use_vision: bool = Field(default=False, description="Use an annotated screenshot instead of AX data.")


class _AppSchema(BaseModel):
    mode: str = Field(..., description="One of: launch, switch, resize.")
    name: str | None = Field(default=None, description="Application name.")
    window_loc: list[float] | None = Field(default=None, description="[x, y] window location.")
    window_size: list[float] | None = Field(default=None, description="[width, height] window size.")


class _ClickSchema(BaseModel):
    loc: list[float] = Field(..., description="Screen coordinates [x, y].")
    button: str = Field(default="left", description="One of: left, right, middle.")
    clicks: int = Field(default=1, description="0=hover, 1=single click, 2=double click.")


class _TypeSchema(BaseModel):
    loc: list[float] = Field(..., description="Screen coordinates [x, y].")
    text: str = Field(..., description="Text to type.")
    clear: bool = Field(default=False, description="Clear existing text first.")
    caret_position: str = Field(default="idle", description="One of: start, idle, end.")
    press_enter: bool = Field(default=False, description="Press Enter after typing.")


class _ShortcutSchema(BaseModel):
    shortcut: str = Field(..., description="Keyboard shortcut, e.g. command+c.")


class _ScrollSchema(BaseModel):
    loc: list[float] | None = Field(default=None, description="Screen coordinates [x, y].")
    type: str = Field(default="vertical", description="One of: horizontal, vertical.")
    direction: str = Field(default="down", description="One of: up, down, left, right.")
    wheel_times: int = Field(default=1, description="Number of scroll wheel ticks.")


class _WaitSchema(BaseModel):
    duration: float = Field(..., description="Seconds to wait.")


def register(tau) -> None:
    project_root = _find_project_root()
    bridge = _McpBridge(project_root)

    def mcp_tool(name: str, mcp_name: str, description: str, schema: type[BaseModel]) -> _McpTool:
        tool = _McpTool(bridge, name, description, schema)
        tool.mcp_tool_name = mcp_name
        return tool

    tau.register_tool(
        mcp_tool(
            "mac_snapshot",
            "Snapshot",
            "Read macOS UI state through macOS-MCP. Returns interactive elements and "
            "coordinates; set use_vision=true only when an annotated screenshot is needed.",
            _SnapshotSchema,
        )
    )
    tau.register_tool(
        mcp_tool(
            "mac_app",
            "App",
            "Launch, switch, or resize macOS applications/windows through macOS-MCP.",
            _AppSchema,
        )
    )
    tau.register_tool(
        mcp_tool(
            "mac_click",
            "Click",
            "Click macOS screen coordinates through macOS-MCP. Get coordinates from "
            "mac_snapshot first.",
            _ClickSchema,
        )
    )
    tau.register_tool(
        mcp_tool(
            "mac_type",
            "Type",
            "Type text at macOS screen coordinates through macOS-MCP. Get coordinates "
            "from mac_snapshot first.",
            _TypeSchema,
        )
    )
    tau.register_tool(
        mcp_tool(
            "mac_shortcut",
            "Shortcut",
            "Run a macOS keyboard shortcut through macOS-MCP, e.g. command+c, "
            "command+l, command+space.",
            _ShortcutSchema,
        )
    )
    tau.register_tool(
        mcp_tool(
            "mac_scroll",
            "Scroll",
            "Scroll vertically or horizontally through macOS-MCP. Coordinates are "
            "optional but recommended from mac_snapshot.",
            _ScrollSchema,
        )
    )
    tau.register_tool(
        mcp_tool(
            "mac_wait",
            "Wait",
            "Wait for UI loading/animations through macOS-MCP.",
            _WaitSchema,
        )
    )

    @tau.on("runtime_stop")
    async def _on_runtime_stop(event, ctx) -> None:
        await bridge.close()
