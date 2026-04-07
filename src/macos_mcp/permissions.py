"""
macOS permission checker for Accessibility and Screen Recording.
"""
import subprocess
import logging
import sys
from typing import Tuple

logger = logging.getLogger(__name__)


def check_accessibility_permission() -> bool:
    """
    Check if Accessibility permission is granted.

    Returns:
        True if permission is granted, False otherwise.
    """
    try:
        from ApplicationServices import AXIsProcessTrusted
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
            ["osascript", "-e", "tell application \"System Events\" to get version"],
            capture_output=True,
            timeout=2,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        logger.warning(f"Could not verify Screen Recording permission: {e}")
        return False


def request_permissions() -> Tuple[bool, bool]:
    """
    Request missing permissions by opening System Preferences.

    Returns:
        Tuple of (accessibility_granted, screen_recording_granted)
    """
    accessibility_ok = check_accessibility_permission()
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
            ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"],
            timeout=5
        )

    return accessibility_ok, screen_recording_ok


def validate_permissions() -> None:
    """
    Validate that all required permissions are granted.
    Exits with error code 1 if any permission is missing.
    """
    accessibility_ok, screen_recording_ok = request_permissions()

    if not accessibility_ok or not screen_recording_ok:
        missing = []
        if not accessibility_ok:
            missing.append("Accessibility")
        if not screen_recording_ok:
            missing.append("Screen Recording")

        logger.error(
            f"Required permissions not granted: {', '.join(missing)}. "
            "Please enable them in System Preferences > Privacy & Security and restart the MCP server."
        )
        sys.exit(1)
