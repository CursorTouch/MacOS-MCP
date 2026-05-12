"""Tests for desktop/views.py module."""

import pytest
from macos_mcp.desktop.views import Status, Size, Window, DesktopState
from macos_mcp.tree.views import BoundingBox


@pytest.mark.unit
class TestStatus:
    """Tests for Status enum."""

    def test_status_values(self):
        """Test all status enum values."""
        assert Status.ACTIVE.value == "Active"
        assert Status.FULLSCREEN.value == "Fullscreen"
        assert Status.VISIBLE.value == "Visible"
        assert Status.HIDDEN.value == "Hidden"
        assert Status.MINIMIZED.value == "Minimized"
        assert Status.WINDOWLESS.value == "Windowless"


@pytest.mark.unit
class TestSize:
    """Tests for Size dataclass."""

    def test_size_creation(self):
        """Test creating a Size instance."""
        size = Size(width=1920, height=1080)
        assert size.width == 1920
        assert size.height == 1080

    def test_size_to_string(self):
        """Test Size.to_string() method."""
        size = Size(width=1920, height=1080)
        assert size.to_string() == "(1920,1080)"

    def test_size_zero(self):
        """Test Size with zero dimensions."""
        size = Size(width=0, height=0)
        assert size.to_string() == "(0,0)"


@pytest.mark.unit
class TestWindow:
    """Tests for Window dataclass."""

    def test_window_creation(self):
        """Test creating a Window instance."""
        bbox = BoundingBox(left=0, top=0, right=800, bottom=600, width=800, height=600)
        window = Window(
            name="Test App",
            is_browser=False,
            status=Status.ACTIVE,
            bounding_box=bbox,
            pid=1234,
            bundle_id="com.example.app",
        )
        assert window.name == "Test App"
        assert window.is_browser is False
        assert window.status == Status.ACTIVE
        assert window.pid == 1234
        assert window.bundle_id == "com.example.app"

    def test_browser_window(self):
        """Test creating a browser window."""
        bbox = BoundingBox(left=0, top=0, right=1400, bottom=900, width=1400, height=900)
        window = Window(
            name="Safari",
            is_browser=True,
            status=Status.ACTIVE,
            bounding_box=bbox,
            pid=5678,
            bundle_id="com.apple.Safari",
        )
        assert window.is_browser is True
        assert window.bundle_id == "com.apple.Safari"


@pytest.mark.unit
class TestDesktopState:
    """Tests for DesktopState dataclass."""

    def test_desktop_state_creation(self, mock_window):
        """Test creating a DesktopState instance."""
        state = DesktopState(
            active_window=mock_window,
            windows=[mock_window],
        )
        assert state.active_window == mock_window
        assert len(state.windows) == 1
        assert state.screenshot is None
        assert state.tree_state is None

    def test_desktop_state_with_multiple_windows(self, mock_window, mock_browser_window):
        """Test DesktopState with multiple windows."""
        state = DesktopState(
            active_window=mock_window,
            windows=[mock_window, mock_browser_window],
        )
        assert len(state.windows) == 2
        assert state.windows[0] == mock_window
        assert state.windows[1] == mock_browser_window

    def test_windows_to_string_with_windows(self, mock_window, mock_browser_window):
        """Test windows_to_string with windows."""
        state = DesktopState(
            active_window=mock_window,
            windows=[mock_window, mock_browser_window],
        )
        result = state.windows_to_string()
        assert "Test Window" in result
        assert "com.example.app" in result
        assert "Safari" in result
        assert "com.apple.Safari" in result
        assert "Active" in result

    def test_windows_to_string_empty(self):
        """Test windows_to_string with no windows."""
        state = DesktopState(
            active_window=None,
            windows=[],
        )
        result = state.windows_to_string()
        assert result == "No open applications."

    def test_active_window_to_string_with_window(self, mock_window):
        """Test active_window_to_string with active window."""
        state = DesktopState(
            active_window=mock_window,
            windows=[mock_window],
        )
        result = state.active_window_to_string()
        assert "Test Window" in result
        assert "com.example.app" in result
        assert "Active" in result

    def test_active_window_to_string_no_window(self):
        """Test active_window_to_string with no active window."""
        state = DesktopState(
            active_window=None,
            windows=[],
        )
        result = state.active_window_to_string()
        assert result == "No focused window."

    def test_desktop_state_status_values(self):
        """Test DesktopState with different status values."""
        bbox = BoundingBox(left=0, top=0, right=800, bottom=600, width=800, height=600)
        statuses = [
            Status.ACTIVE,
            Status.FULLSCREEN,
            Status.VISIBLE,
            Status.HIDDEN,
            Status.MINIMIZED,
            Status.WINDOWLESS,
        ]
        for status in statuses:
            window = Window(
                name="Test",
                is_browser=False,
                status=status,
                bounding_box=bbox,
                pid=1000,
                bundle_id="com.test",
            )
            state = DesktopState(active_window=window, windows=[window])
            result = state.active_window_to_string()
            assert status.value in result
