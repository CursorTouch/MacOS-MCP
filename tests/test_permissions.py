"""Tests for permissions module."""

import pytest
from unittest.mock import patch, MagicMock
import subprocess
import sys


@pytest.mark.unit
class TestCheckAccessibilityPermission:
    """Tests for check_accessibility_permission function."""

    def test_permission_granted(self):
        """Test when accessibility permission is granted."""
        with patch("ApplicationServices.AXIsProcessTrusted", return_value=True):
            from macos_mcp.permissions import check_accessibility_permission

            assert check_accessibility_permission() is True

    def test_permission_denied(self):
        """Test when accessibility permission is denied."""
        with patch("ApplicationServices.AXIsProcessTrusted", return_value=False):
            from macos_mcp.permissions import check_accessibility_permission

            assert check_accessibility_permission() is False

    def test_permission_check_error(self):
        """Test when accessibility permission check fails."""
        with patch(
            "ApplicationServices.AXIsProcessTrusted",
            side_effect=Exception("Framework error"),
        ):
            from macos_mcp.permissions import check_accessibility_permission

            assert check_accessibility_permission() is False


@pytest.mark.unit
class TestCheckScreenRecordingPermission:
    """Tests for check_screen_recording_permission function."""

    def test_permission_granted(self, mocker):
        """Test when screen recording permission is granted."""
        mock_run = mocker.patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0),
        )
        from macos_mcp.permissions import check_screen_recording_permission

        result = check_screen_recording_permission()

        assert result is True
        mock_run.assert_called_once()

    def test_permission_denied(self, mocker):
        """Test when screen recording permission is denied."""
        mock_run = mocker.patch(
            "subprocess.run",
            return_value=MagicMock(returncode=1),
        )
        from macos_mcp.permissions import check_screen_recording_permission

        result = check_screen_recording_permission()

        assert result is False
        mock_run.assert_called_once()

    def test_permission_check_timeout(self, mocker):
        """Test when osascript times out."""
        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("osascript", 2),
        )
        from macos_mcp.permissions import check_screen_recording_permission

        result = check_screen_recording_permission()

        assert result is False

    def test_permission_check_error(self, mocker):
        """Test when osascript call fails."""
        mocker.patch(
            "subprocess.run",
            side_effect=Exception("Command not found"),
        )
        from macos_mcp.permissions import check_screen_recording_permission

        result = check_screen_recording_permission()

        assert result is False


@pytest.mark.unit
class TestRequestPermissions:
    """Tests for request_permissions function."""

    def test_both_permissions_granted(self, mocker):
        """Test when both permissions are already granted."""
        mocker.patch("macos_mcp.permissions.check_accessibility_permission", return_value=True)
        mocker.patch(
            "macos_mcp.permissions.check_screen_recording_permission", return_value=True
        )
        mock_open = mocker.patch("subprocess.run")

        from macos_mcp.permissions import request_permissions

        accessibility, screen_recording = request_permissions()

        assert accessibility is True
        assert screen_recording is True
        mock_open.assert_not_called()

    def test_accessibility_permission_missing(self, mocker):
        """Test when accessibility permission is missing."""
        mocker.patch("macos_mcp.permissions.check_accessibility_permission", return_value=False)
        mocker.patch(
            "macos_mcp.permissions.check_screen_recording_permission", return_value=True
        )
        mock_open = mocker.patch("subprocess.run")

        from macos_mcp.permissions import request_permissions

        accessibility, screen_recording = request_permissions()

        assert accessibility is False
        assert screen_recording is True
        mock_open.assert_called_once()

    def test_screen_recording_permission_missing(self, mocker):
        """Test when screen recording permission is missing."""
        mocker.patch("macos_mcp.permissions.check_accessibility_permission", return_value=True)
        mocker.patch(
            "macos_mcp.permissions.check_screen_recording_permission", return_value=False
        )
        mock_open = mocker.patch("subprocess.run")

        from macos_mcp.permissions import request_permissions

        accessibility, screen_recording = request_permissions()

        assert accessibility is True
        assert screen_recording is False
        mock_open.assert_called_once()

    def test_both_permissions_missing(self, mocker):
        """Test when both permissions are missing."""
        mocker.patch("macos_mcp.permissions.check_accessibility_permission", return_value=False)
        mocker.patch(
            "macos_mcp.permissions.check_screen_recording_permission", return_value=False
        )
        mock_open = mocker.patch("subprocess.run")

        from macos_mcp.permissions import request_permissions

        accessibility, screen_recording = request_permissions()

        assert accessibility is False
        assert screen_recording is False
        mock_open.assert_called_once()

    def test_open_settings_false_suppresses_system_preferences(self, mocker):
        """When open_settings=False, missing permissions must not pop System
        Preferences — used for MACOS_MCP_SKIP_PERMISSION_CHECK=1 so the
        server doesn't steal focus on every start when the check itself is
        known to be unreliable (e.g. under Claude Desktop's disclaimed
        subprocess launcher)."""
        mocker.patch("macos_mcp.permissions.check_accessibility_permission", return_value=False)
        mocker.patch(
            "macos_mcp.permissions.check_screen_recording_permission", return_value=False
        )
        mock_open = mocker.patch("subprocess.run")

        from macos_mcp.permissions import request_permissions

        accessibility, screen_recording = request_permissions(open_settings=False)

        assert accessibility is False
        assert screen_recording is False
        mock_open.assert_not_called()


@pytest.mark.unit
class TestValidatePermissions:
    """Tests for validate_permissions function."""

    def test_validation_succeeds(self, mocker):
        """Test validation when both permissions are granted."""
        mocker.patch("macos_mcp.permissions.request_permissions", return_value=(True, True))
        mock_exit = mocker.patch("sys.exit")

        from macos_mcp.permissions import validate_permissions

        validate_permissions()

        mock_exit.assert_not_called()

    def test_validation_fails_on_accessibility(self, mocker):
        """Test validation fails when accessibility permission is denied."""
        mocker.patch("macos_mcp.permissions.request_permissions", return_value=(False, True))
        mock_exit = mocker.patch("sys.exit")

        from macos_mcp.permissions import validate_permissions

        validate_permissions()

        mock_exit.assert_called_once_with(1)

    def test_validation_fails_on_screen_recording(self, mocker):
        """Test validation fails when screen recording permission is denied."""
        mocker.patch("macos_mcp.permissions.request_permissions", return_value=(True, False))
        mock_exit = mocker.patch("sys.exit")

        from macos_mcp.permissions import validate_permissions

        validate_permissions()

        mock_exit.assert_called_once_with(1)

    def test_validation_fails_on_both(self, mocker):
        """Test validation fails when both permissions are denied."""
        mocker.patch("macos_mcp.permissions.request_permissions", return_value=(False, False))
        mock_exit = mocker.patch("sys.exit")

        from macos_mcp.permissions import validate_permissions

        validate_permissions()

        mock_exit.assert_called_once_with(1)

    def test_validation_skip_env_warns_instead_of_exiting(self, mocker):
        """MACOS_MCP_SKIP_PERMISSION_CHECK=1 downgrades a failed check to a
        warning (server keeps starting) and must ask request_permissions to
        suppress the System Preferences popup, since the underlying
        AXIsProcessTrusted() check is known-unreliable in that scenario
        (disclaimed subprocess launcher, e.g. Claude Desktop)."""
        mock_request = mocker.patch(
            "macos_mcp.permissions.request_permissions", return_value=(False, False)
        )
        mock_exit = mocker.patch("sys.exit")
        mocker.patch.dict("os.environ", {"MACOS_MCP_SKIP_PERMISSION_CHECK": "1"})

        from macos_mcp.permissions import validate_permissions

        validate_permissions()

        mock_exit.assert_not_called()
        mock_request.assert_called_once_with(open_settings=False)


@pytest.mark.unit
class TestAccessibilityGuidance:
    """Tests for the Accessibility guidance text (#32).

    The failure path used to say only "grant Accessibility permission" without
    naming a target. The host app is already granted, nothing called
    "macos-mcp" ever appears in the list, and the interpreter cannot be added
    by hand, so the instruction was unfollowable. These tests pin the three
    facts that make it actionable again.
    """

    def test_guidance_names_the_running_interpreter(self):
        """The grant belongs to sys.executable, which the user cannot guess."""
        from macos_mcp.permissions import accessibility_guidance

        assert sys.executable in accessibility_guidance()

    def test_guidance_points_at_the_native_dialog(self):
        """Approving the native consent dialog is the reliable fix."""
        from macos_mcp.permissions import accessibility_guidance

        assert "control this computer" in accessibility_guidance()

    def test_guidance_warns_against_manual_picker_entry(self):
        """Adding the binary via the '+' picker is documented as not working."""
        from macos_mcp.permissions import accessibility_guidance

        guidance = accessibility_guidance()
        assert "Do not add the interpreter by hand" in guidance
        assert "greyed out" in guidance

    def test_fatal_message_includes_guidance(self, mocker, caplog):
        """The exit-path error names the process, not just the permission."""
        mocker.patch("macos_mcp.permissions.request_permissions", return_value=(False, True))
        mocker.patch("sys.exit")

        from macos_mcp.permissions import validate_permissions

        with caplog.at_level("ERROR"):
            validate_permissions()

        assert sys.executable in caplog.text

    def test_guidance_omitted_when_only_screen_recording_missing(self, mocker, caplog):
        """Screen Recording has no 'which process?' ambiguity, so stay quiet."""
        mocker.patch("macos_mcp.permissions.request_permissions", return_value=(True, False))
        mocker.patch("sys.exit")

        from macos_mcp.permissions import validate_permissions

        with caplog.at_level("ERROR"):
            validate_permissions()

        assert "Screen Recording" in caplog.text
        assert "control this computer" not in caplog.text
