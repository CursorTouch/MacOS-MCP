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


def accessibility_guidance() -> str:
    """Explain *which* process needs the Accessibility grant.

    "Grant Accessibility permission" is not actionable on its own: the grant
    belongs to the interpreter running this server, which the user never named
    and cannot see. The MCP host (Claude Desktop, etc.) is a separate identity,
    so granting the host does nothing, and nothing called "macos-mcp" ever
    appears in the Accessibility list. Naming the binary and pointing at the
    native consent dialog turns a dead end into a followable instruction (#32).
    """
    return (
        f"The grant belongs to the process running this server -- {sys.executable} -- "
        "not to the app that launched it, so granting the MCP host (e.g. Claude "
        "Desktop) has no effect and no entry named 'macos-mcp' will ever appear. "
        "On startup macOS should show a native '... would like to control this "
        "computer' dialog; approving it registers this exact process and is the "
        "reliable fix. Do not add the interpreter by hand in System Settings > "
        "Privacy & Security > Accessibility -- uv-managed Python binaries are "
        "commonly greyed out in the '+' picker, and a manual entry breaks on the "
        "next uv update."
    )


def request_permissions(open_settings: bool = True) -> Tuple[bool, bool]:
    """
    Request missing permissions.

    For Accessibility, this first tries AXIsProcessTrustedWithOptions with the
    prompt flag set, which asks macOS to show its native consent dialog and
    auto-register the running process in the Accessibility list. This is more
    reliable than requiring the user to manually add the process via the
    System Settings "+" file picker, which can reject or grey out binaries
    like uv-managed Python interpreters (symlinks into ~/.local/share/uv/...).

    Args:
        open_settings: If True (default), open System Preferences to the
            Privacy & Security pane when permissions are missing. Set to
            False to suppress this — e.g. when the check itself is expected
            to be unreliable (MACOS_MCP_SKIP_PERMISSION_CHECK=1), where
            popping System Preferences on every server start would just
            steal focus without being actionable.

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

        # Only Accessibility has the "which process?" ambiguity worth explaining.
        detail = f" {accessibility_guidance()}" if not accessibility_ok else ""

        if open_settings:
            logger.warning(
                f"Missing permissions: {', '.join(missing)}. "
                "Opening System Preferences. Please grant permissions and restart."
                f"{detail}"
            )

            # Open System Preferences to Privacy & Security
            subprocess.run(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
                ],
                timeout=5,
            )
        else:
            logger.warning(f"Missing permissions: {', '.join(missing)}.{detail}")

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

    accessibility_ok, screen_recording_ok = request_permissions(open_settings=not skip)

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
        if not accessibility_ok:
            msg += f" {accessibility_guidance()}"
        if skip:
            logger.warning(msg + " (continuing anyway — MACOS_MCP_SKIP_PERMISSION_CHECK=1)")
        else:
            logger.error(msg)
            sys.exit(1)
