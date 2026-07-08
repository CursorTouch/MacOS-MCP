"""
macOS permission checker for Accessibility and Screen Recording.
"""

import subprocess
import logging
import sys
from typing import Tuple

logger = logging.getLogger(__name__)


def check_accessibility_permission(prompt: bool = False) -> bool:
    """
    Check if Accessibility permission is granted.

    Args:
        prompt: If True, ask macOS to prompt the user for consent and
            auto-register this process in the Accessibility list via
            AXIsProcessTrustedWithOptions. This avoids requiring the user to
            manually locate and add the running interpreter binary (e.g. a
            uv-managed Python symlink) with the System Settings "+" picker,
            which can appear greyed out / unselectable for such binaries.

    Returns:
        True if permission is granted, False otherwise.
    """
    try:
        from ApplicationServices import AXIsProcessTrusted, AXIsProcessTrustedWithOptions

        if prompt:
            from CoreFoundation import kCFBooleanTrue

            options = {"AXTrustedCheckOptionPrompt": kCFBooleanTrue}
            return AXIsProcessTrustedWithOptions(options)

        return AXIsProcessTrusted()
    except Exception as e:
        logger.error(f"Failed to check Accessibility permission: {e}")
        return False


def check_screen_recording_permission() -> bool:
    """
    Check if Screen Recording permission is granted.

    Returns:
        True if permission is granted, False otherwise.
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get version'],
            capture_output=True,
            timeout=2,
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        logger.warning(f"Could not verify Screen Recording permission: {e}")
        return False


def request_permissions() -> Tuple[bool, bool]:
    """
    Request missing permissions.

    For Accessibility, this first tries AXIsProcessTrustedWithOptions with the
    prompt flag set, which asks macOS to show its native consent dialog and
    auto-register the running process in the Accessibility list. This is more
    reliable than requiring the user to manually add the process via the
    System Settings "+" file picker, which can reject or grey out binaries
    like uv-managed Python interpreters (symlinks into ~/.local/share/uv/...).

    Returns:
        Tuple of (accessibility_granted, screen_recording_granted)
    """
    accessibility_ok = check_accessibility_permission(prompt=True)
    screen_recording_ok = check_screen_recording_permission()

    if not accessibility_ok or not screen_recording_ok:
        missing = []
        if not accessibility_ok:
            missing.append("Accessibility")
        if not screen_recording_ok:
            missing.append("Screen Recording")

        logger.warning(
            f"Missing permissions: {', '.join(missing)}. "
            "Opening System Preferences. Please grant permissions and restart."
        )

        # Open System Preferences to Privacy & Security
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ],
            timeout=5,
        )

    return accessibility_ok, screen_recording_ok


def validate_permissions() -> None:
    """
    Validate that all required permissions are granted.

    When launched as a subprocess by a parent that already holds TCC grants
    (e.g. Claude Desktop), AXIsProcessTrusted() returns False for the child
    binary even though AX calls succeed via inheritance.  Setting
    MACOS_MCP_SKIP_PERMISSION_CHECK=1 downgrades the failure to a warning so
    the server starts instead of exiting.
    """
    import os

    skip = os.environ.get("MACOS_MCP_SKIP_PERMISSION_CHECK", "0") == "1"

    accessibility_ok, screen_recording_ok = request_permissions()

    if not accessibility_ok or not screen_recording_ok:
        missing = []
        if not accessibility_ok:
            missing.append("Accessibility")
        if not screen_recording_ok:
            missing.append("Screen Recording")

        msg = (
            f"Required permissions not granted: {', '.join(missing)}. "
            "Please enable them in System Preferences > Privacy & Security and restart the MCP server."
        )
        if skip:
            logger.warning(msg + " (continuing anyway — MACOS_MCP_SKIP_PERMISSION_CHECK=1)")
        else:
            logger.error(msg)
            sys.exit(1)
