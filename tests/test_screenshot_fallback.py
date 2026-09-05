import errno
import logging
import tempfile

from PIL import UnidentifiedImageError

import macos_mcp.__main__ as server
from macos_mcp.ax import core
from macos_mcp.desktop.service import Desktop


def test_screencapture_tempfile_enospc_is_capture_failure(mocker, caplog):
    """Treat tempfile ENOSPC as a diagnosed capture failure instead of raising."""
    mocker.patch.object(
        tempfile,
        "mkstemp",
        side_effect=OSError(errno.ENOSPC, "No space left on device"),
    )

    with caplog.at_level(logging.ERROR, logger="macos_mcp.ax.core"):
        result = core._capture_screen_via_screencapture()

    assert result is None
    assert "no space left on device" in caplog.text.lower()
    assert "temporary capture file" in caplog.text.lower()


def test_undecodable_capture_returns_no_screenshot(mocker, caplog):
    """A screencapture failure leaves an unreadable PNG; report it, don't raise."""
    mocker.patch(
        "macos_mcp.desktop.service.ImageGrab.grab",
        side_effect=UnidentifiedImageError("cannot identify image file '/tmp/tmpx9mtq.png'"),
    )

    with caplog.at_level(logging.ERROR, logger="macos_mcp.desktop.service"):
        result = Desktop().get_screenshot()

    assert result is None
    assert "screenshot capture failed" in caplog.text.lower()


def test_annotated_screenshot_skipped_when_capture_fails(mocker):
    """Annotation must not run against a screenshot that was never captured."""
    mocker.patch.object(Desktop, "get_screenshot", return_value=None)

    assert Desktop().get_annotated_screenshot(nodes=[]) is None


async def test_snapshot_reports_missing_screenshot_to_the_caller(mocker):
    """use_vision with a failed capture returns a text snapshot that says so."""
    state = mocker.MagicMock()
    state.screenshot = None
    state.tree_state.interactive_elements_to_string.return_value = "Label: 0 Button"
    state.tree_state.scrollable_elements_to_string.return_value = ""
    state.windows_to_string.return_value = "Finder"
    state.active_window_to_string.return_value = "Finder"
    mocker.patch.object(
        server,
        "desktop",
        mocker.MagicMock(async_get_state=mocker.AsyncMock(return_value=state)),
    )

    result = await server.state_tool(use_vision=True)

    assert len(result) == 1, "no image should be attached when capture failed"
    assert "Screenshot capture failed" in result[0]
    assert "Label: 0 Button" in result[0]
