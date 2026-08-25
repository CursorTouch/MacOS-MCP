import errno
import logging
import tempfile

from macos_mcp.ax import core


def test_screencapture_tempfile_enospc_is_capture_failure(mocker, caplog):
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
