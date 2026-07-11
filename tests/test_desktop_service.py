"""Tests for desktop/service.py module."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from macos_mcp.desktop.service import Desktop
from macos_mcp.desktop.views import Window, Status, DesktopState, Size
from macos_mcp.tree.views import BoundingBox, TreeState, Center


@pytest.mark.unit
class TestDesktopScreenSize:
    """Tests for Desktop.get_screen_size method."""

    def test_get_screen_size(self, mocker):
        """Test getting screen size."""
        mocker.patch("macos_mcp.desktop.service.ax.GetScreenSize", return_value=(1920, 1080))
        desktop = Desktop()
        size = desktop.get_screen_size()
        assert isinstance(size, Size)
        assert size.width == 1920
        assert size.height == 1080

    def test_get_screen_size_retina(self, mocker):
        """Test getting screen size for Retina display."""
        mocker.patch("macos_mcp.desktop.service.ax.GetScreenSize", return_value=(2560, 1600))
        desktop = Desktop()
        size = desktop.get_screen_size()
        assert size.width == 2560
        assert size.height == 1600


@pytest.mark.unit
class TestDesktopAppManagement:
    """Tests for Desktop.app method."""

    def test_app_launch_success(self, mocker):
        """Test launching an application."""
        mock_launch = mocker.patch("macos_mcp.desktop.service.ax.LaunchApplication", return_value=True)
        desktop = Desktop()
        result = desktop.app(mode="launch", name="Safari")
        assert "Launched Safari" in result
        mock_launch.assert_called_once_with("Safari")

    def test_app_launch_failure(self, mocker):
        """Test failing to launch an application."""
        mocker.patch("macos_mcp.desktop.service.ax.LaunchApplication", return_value=False)
        desktop = Desktop()
        result = desktop.app(mode="launch", name="NonExistentApp")
        assert "Failed to launch" in result

    def test_app_launch_no_name(self):
        """Test launching without app name."""
        desktop = Desktop()
        result = desktop.app(mode="launch", name=None)
        assert "App name or bundle ID required" in result

    def test_app_switch_success(self, mocker):
        """Test switching to an application."""
        mock_app = MagicMock()
        mock_app.PID = 1234
        mocker.patch("macos_mcp.desktop.service.ax.GetRunningApplicationByName", return_value=mock_app)
        mock_activate = mocker.patch("macos_mcp.desktop.service.ax.ActivateApplication")
        desktop = Desktop()
        result = desktop.app(mode="switch", name="Safari")
        assert "Switched to Safari" in result
        mock_activate.assert_called_once_with(1234)

    def test_app_switch_by_bundle_id(self, mocker):
        """Test switching to application by bundle ID."""
        mocker.patch("macos_mcp.desktop.service.ax.GetRunningApplicationByName", return_value=None)
        mock_app = MagicMock()
        mock_app.PID = 5678
        mocker.patch("macos_mcp.desktop.service.ax.GetRunningApplicationByBundleId", return_value=mock_app)
        mock_activate = mocker.patch("macos_mcp.desktop.service.ax.ActivateApplication")
        desktop = Desktop()
        result = desktop.app(mode="switch", name="com.apple.Safari")
        assert "Switched to com.apple.Safari" in result
        mock_activate.assert_called_once_with(5678)

    def test_app_switch_not_found(self, mocker):
        """Test switching to non-existent application."""
        mocker.patch("macos_mcp.desktop.service.ax.GetRunningApplicationByName", return_value=None)
        mocker.patch("macos_mcp.desktop.service.ax.GetRunningApplicationByBundleId", return_value=None)
        desktop = Desktop()
        result = desktop.app(mode="switch", name="NonExistentApp")
        assert "not found" in result

    def test_app_unknown_mode(self):
        """Test unknown app mode."""
        desktop = Desktop()
        result = desktop.app(mode="unknown_mode")
        assert "Unknown mode" in result


@pytest.mark.unit
class TestDesktopInput:
    """Tests for Desktop input methods."""

    def test_click_left(self, mocker):
        """Test left click."""
        mock_click = mocker.patch("macos_mcp.desktop.service.ax.Click")
        desktop = Desktop()
        desktop.click((100, 200), button="left", clicks=1)
        mock_click.assert_called_once_with(100, 200)

    def test_click_double(self, mocker):
        """Test double click."""
        mock_double_click = mocker.patch("macos_mcp.desktop.service.ax.DoubleClick")
        desktop = Desktop()
        desktop.click((100, 200), button="left", clicks=2)
        mock_double_click.assert_called_once_with(100, 200)

    def test_click_right(self, mocker):
        """Test right click."""
        mock_right_click = mocker.patch("macos_mcp.desktop.service.ax.RightClick")
        desktop = Desktop()
        desktop.click((100, 200), button="right")
        mock_right_click.assert_called_once_with(100, 200)

    def test_click_middle(self, mocker):
        """Test middle click."""
        mock_middle_click = mocker.patch("macos_mcp.desktop.service.ax.MiddleClick")
        desktop = Desktop()
        desktop.click((100, 200), button="middle")
        mock_middle_click.assert_called_once_with(100, 200)

    def test_click_move_only(self, mocker):
        """Test move without click."""
        mock_move = mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        desktop = Desktop()
        desktop.click((100, 200), clicks=0)
        mock_move.assert_called_once_with(100, 200)

    def test_move(self, mocker):
        """Test moving mouse."""
        mock_move = mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        desktop = Desktop()
        desktop.move((300, 400))
        mock_move.assert_called_once_with(300, 400)

    def test_drag(self, mocker):
        """Test dragging mouse."""
        mocker.patch("macos_mcp.desktop.service.ax.GetCursorPos", return_value=(100, 200))
        mock_drag = mocker.patch("macos_mcp.desktop.service.ax.DragTo")
        desktop = Desktop()
        desktop.drag((300, 400))
        mock_drag.assert_called_once_with(100, 200, 300, 400)

    def test_shortcut(self, mocker):
        """Test keyboard shortcut."""
        mock_hotkey = mocker.patch("macos_mcp.desktop.service.ax.HotKey")
        desktop = Desktop()
        desktop.shortcut("command+c")
        mock_hotkey.assert_called_once_with("command", "c")

    def test_shortcut_multiple_keys(self, mocker):
        """Test keyboard shortcut with multiple keys."""
        mock_hotkey = mocker.patch("macos_mcp.desktop.service.ax.HotKey")
        desktop = Desktop()
        desktop.shortcut("command+shift+s")
        mock_hotkey.assert_called_once_with("command", "shift", "s")


@pytest.mark.unit
class TestDesktopType:
    """Tests for Desktop.type method."""

    def test_type_text(self, mocker):
        """Test typing text."""
        mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        mocker.patch("macos_mcp.desktop.service.ax.Click")
        mock_type = mocker.patch("macos_mcp.desktop.service.ax.TypeText")
        mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        desktop.type((100, 200), "Hello World")
        mock_type.assert_called_once_with("Hello World")

    def test_type_with_clear(self, mocker):
        """Test typing with text cleared first."""
        mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        mocker.patch("macos_mcp.desktop.service.ax.Click")
        mock_hotkey = mocker.patch("macos_mcp.desktop.service.ax.HotKey")
        mock_type = mocker.patch("macos_mcp.desktop.service.ax.TypeText")
        mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        desktop.type((100, 200), "New Text", clear=True)
        # Should call HotKey for select all and delete
        assert mock_hotkey.call_count >= 2
        mock_type.assert_called_once_with("New Text")

    def test_type_with_caret_start(self, mocker):
        """Test typing with caret at start."""
        mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        mocker.patch("macos_mcp.desktop.service.ax.Click")
        mock_hotkey = mocker.patch("macos_mcp.desktop.service.ax.HotKey")
        mock_type = mocker.patch("macos_mcp.desktop.service.ax.TypeText")
        mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        desktop.type((100, 200), "Text", caret_position="start")
        mock_type.assert_called_once_with("Text")

    def test_type_with_enter(self, mocker):
        """Test typing with Enter key pressed."""
        mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        mocker.patch("macos_mcp.desktop.service.ax.Click")
        mock_type = mocker.patch("macos_mcp.desktop.service.ax.TypeText")
        mock_keypress = mocker.patch("macos_mcp.desktop.service.ax.KeyPress")
        mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        desktop.type((100, 200), "Text", press_enter=True)
        mock_type.assert_called_once_with("Text")
        mock_keypress.assert_called_once()


@pytest.mark.unit
class TestDesktopScroll:
    """Tests for Desktop.scroll method."""

    def test_scroll_vertical_down(self, mocker):
        """Test scrolling down."""
        mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        mock_wheel = mocker.patch("macos_mcp.desktop.service.ax.WheelDown")
        mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        result = desktop.scroll((100, 200), "vertical", "down", wheel_times=1)
        assert result is None
        mock_wheel.assert_called_once_with(1)

    def test_scroll_vertical_up(self, mocker):
        """Test scrolling up."""
        mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        mock_wheel = mocker.patch("macos_mcp.desktop.service.ax.WheelUp")
        mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        result = desktop.scroll((100, 200), "vertical", "up", wheel_times=1)
        assert result is None
        mock_wheel.assert_called_once_with(1)

    def test_scroll_horizontal_right(self, mocker):
        """Test scrolling right."""
        mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        mock_wheel = mocker.patch("macos_mcp.desktop.service.ax.WheelRight")
        mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        result = desktop.scroll((100, 200), "horizontal", "right")
        assert result is None
        mock_wheel.assert_called_once_with(1)

    def test_scroll_vertical_wrong_direction(self, mocker):
        """Test vertical scroll with wrong direction."""
        desktop = Desktop()
        result = desktop.scroll((100, 200), "vertical", "left")
        assert "Use direction 'up' or 'down'" in result

    def test_scroll_horizontal_wrong_direction(self, mocker):
        """Test horizontal scroll with wrong direction."""
        desktop = Desktop()
        result = desktop.scroll((100, 200), "horizontal", "up")
        assert "Use direction 'left' or 'right'" in result

    def test_scroll_multiple_times(self, mocker):
        """Test scrolling multiple times."""
        mocker.patch("macos_mcp.desktop.service.ax.MoveTo")
        mock_wheel = mocker.patch("macos_mcp.desktop.service.ax.WheelDown")
        mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        result = desktop.scroll((100, 200), "vertical", "down", wheel_times=3)
        assert result is None
        assert mock_wheel.call_count == 3

    def test_scroll_without_location(self, mocker):
        """Test scrolling at current position."""
        mock_wheel = mocker.patch("macos_mcp.desktop.service.ax.WheelDown")
        mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        result = desktop.scroll(None, "vertical", "down")
        assert result is None
        mock_wheel.assert_called_once_with(1)


@pytest.mark.unit
class TestDesktopUtility:
    """Tests for Desktop utility methods."""

    def test_wait(self, mocker):
        """Test wait method."""
        mock_sleep = mocker.patch("macos_mcp.desktop.service.time.sleep")
        desktop = Desktop()
        desktop.wait(5)
        mock_sleep.assert_called_once_with(5)

    def test_execute_command_shell(self, mocker):
        """Test executing shell command."""
        mock_exec = mocker.patch("macos_mcp.desktop.service.ax.ExecuteCommand", return_value=("output", 0))
        desktop = Desktop()
        result = desktop.execute_command("ls -la", mode="shell")
        assert result == ("output", 0)

    def test_execute_command_osascript(self, mocker):
        """Test executing osascript command."""
        mock_exec = mocker.patch("macos_mcp.desktop.service.ax.ExecuteCommand", return_value=("result", 0))
        desktop = Desktop()
        result = desktop.execute_command("get version", mode="osascript", timeout=5)
        assert result == ("result", 0)


@pytest.mark.unit
class TestDesktopNotify:
    """Tests for Desktop.notify method."""

    def test_notify_simple(self, mocker):
        """Test sending simple notification."""
        mocker.patch("subprocess.run", return_value=MagicMock(returncode=0))
        desktop = Desktop()
        result = desktop.notify("Test Message", title="Test Title")
        assert "Notification sent" in result

    def test_notify_with_subtitle(self, mocker):
        """Test sending notification with subtitle."""
        mock_run = mocker.patch("subprocess.run", return_value=MagicMock(returncode=0))
        desktop = Desktop()
        result = desktop.notify("Message", title="Title", subtitle="Subtitle")
        assert "Notification sent" in result
        # Verify osascript was called with subtitle
        call_args = mock_run.call_args[0][0]
        assert "subtitle" in call_args[2]

    def test_notify_failed(self, mocker):
        """Test when notification fails."""
        mocker.patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="Error message"))
        desktop = Desktop()
        result = desktop.notify("Message")
        assert "Failed to send notification" in result

    def test_notify_non_ascii(self, mocker):
        """Non-ASCII text must be emitted as raw UTF-8, not \\uXXXX escapes,
        since AppleScript string literals don't support unicode escapes."""
        mock_run = mocker.patch("subprocess.run", return_value=MagicMock(returncode=0))
        desktop = Desktop()
        result = desktop.notify("通知测试", title="タイトル")
        assert "Notification sent" in result
        call_args = mock_run.call_args[0][0]
        script = call_args[2]
        assert "通知测试" in script
        assert "タイトル" in script
        assert "\\u" not in script


@pytest.mark.unit
class TestDesktopScrape:
    """Tests for Desktop.scrape method."""

    def test_scrape_success(self, mocker):
        """Test scraping URL successfully."""
        mock_response = MagicMock()
        mock_response.text = "<html>Test content</html>"
        mocker.patch("macos_mcp.desktop.service.requests.get", return_value=mock_response)
        desktop = Desktop()
        result = desktop.scrape("https://example.com")
        assert "<html>Test content</html>" in result

    def test_scrape_connection_error(self, mocker):
        """Test scraping with connection error."""
        mocker.patch(
            "macos_mcp.desktop.service.requests.get",
            side_effect=Exception("Connection refused"),
        )
        desktop = Desktop()
        result = desktop.scrape("https://example.com")
        assert "Connection refused" in result

    def test_scrape_timeout(self, mocker):
        """Test scraping with timeout."""
        mocker.patch(
            "macos_mcp.desktop.service.requests.get",
            side_effect=TimeoutError("Request timeout"),
        )
        desktop = Desktop()
        result = desktop.scrape("https://example.com")
        assert "timeout" in result.lower()
