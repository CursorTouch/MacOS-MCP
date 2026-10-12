"""Tool argument schemas must accept the defaults they advertise."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Client

import macos_mcp.__main__ as server


@pytest.fixture
def desktop(mocker, monkeypatch):
    """Stub what the server lifespan builds so no test touches the real desktop."""
    monkeypatch.setenv("ANONYMIZED_TELEMETRY", "false")
    desktop = MagicMock()
    desktop.async_scroll = AsyncMock(return_value=None)
    mocker.patch.object(server, "Desktop", return_value=desktop)
    mocker.patch.object(server, "desktop", desktop)
    mocker.patch.object(server, "WatchDog")
    return desktop


def _accepts_null(schema: dict) -> bool:
    if schema.get("type") == "null":
        return True
    if isinstance(schema.get("type"), list) and "null" in schema["type"]:
        return True
    return any(_accepts_null(option) for option in schema.get("anyOf", []))


async def test_null_defaults_are_accepted_by_their_schema(desktop):
    """An argument advertising a null default must also allow null as a value."""
    async with Client(server.mcp) as client:
        tools = await client.list_tools()

    offenders = [
        f"{tool.name}.{name}"
        for tool in tools
        for name, prop in tool.inputSchema.get("properties", {}).items()
        if "default" in prop and prop["default"] is None and not _accepts_null(prop)
    ]
    assert offenders == []


async def test_scroll_accepts_explicit_null_loc(desktop):
    """Sending Scroll's advertised default (loc=null) scrolls at the mouse position."""
    async with Client(server.mcp) as client:
        result = await client.call_tool("Scroll", {"loc": None})

    desktop.async_scroll.assert_awaited_once_with(None, "vertical", "down", 1)
    assert result.content[0].text == "Scrolled vertical down by 1 wheel times."
