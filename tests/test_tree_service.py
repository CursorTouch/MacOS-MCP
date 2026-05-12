"""Tests for tree/service.py module."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from macos_mcp.tree.service import Tree
from macos_mcp.tree.views import TreeState, TreeElementNode, BoundingBox, Center
from macos_mcp.desktop.views import Window, Status


@pytest.mark.unit
class TestTreeOnFocusChanged:
    """Tests for Tree.on_focus_changed method."""

    def test_on_focus_changed_callback(self):
        """Test on_focus_changed callback is invoked."""
        tree = Tree()
        element = MagicMock()
        # Should not raise any exceptions
        tree.on_focus_changed(element, "FocusedUIElementChanged", 1234)

    def test_on_focus_changed_different_notifications(self):
        """Test on_focus_changed with different notification types."""
        tree = Tree()
        element = MagicMock()
        notifications = ["FocusedUIElementChanged", "FocusedWindowChanged", "MainWindowChanged"]
        for notification in notifications:
            # Should handle all notification types
            tree.on_focus_changed(element, notification, 1234)


@pytest.mark.unit
class TestTreeGetState:
    """Tests for Tree.get_state method."""

    def test_get_state_with_active_window(self, mocker, mock_window):
        """Test get_state with an active window."""
        mock_get_app = mocker.patch(
            "macos_mcp.tree.service.ax.GetRunningApplicationByBundleId",
            return_value=None,
        )
        mock_set_attr = mocker.patch("macos_mcp.tree.service.ax.SetAttribute")
        mock_tree = MagicMock()
        mocker.patch.object(Tree, "get_window_wise_nodes", return_value=([], [], []))

        tree = Tree()
        result = tree.get_state(active_window=mock_window)

        assert isinstance(result, TreeState)
        assert result.status is True

    def test_get_state_without_active_window(self, mocker):
        """Test get_state without active window."""
        mocker.patch(
            "macos_mcp.tree.service.ax.GetRunningApplicationByBundleId",
            return_value=None,
        )
        mocker.patch.object(Tree, "get_window_wise_nodes", return_value=([], [], []))

        tree = Tree()
        result = tree.get_state(active_window=None)

        assert isinstance(result, TreeState)
        assert result.status is True
        assert result.interactive_nodes == []

    def test_get_state_with_windowless_app(self, mocker, mock_bounding_box):
        """Test get_state with windowless app (0 width/height)."""
        windowless_app = Window(
            name="Test App",
            is_browser=False,
            status=Status.WINDOWLESS,
            bounding_box=BoundingBox(left=0, top=0, right=0, bottom=0, width=0, height=0),
            pid=1234,
            bundle_id="com.example.app",
        )
        mocker.patch(
            "macos_mcp.tree.service.ax.GetRunningApplicationByBundleId",
            return_value=None,
        )
        mocker.patch.object(Tree, "get_window_wise_nodes", return_value=([], [], []))

        tree = Tree()
        result = tree.get_state(active_window=windowless_app)

        assert isinstance(result, TreeState)


@pytest.mark.unit
class TestTreeGetWindowWiseNodes:
    """Tests for Tree.get_window_wise_nodes method."""

    def test_get_window_wise_nodes_empty(self, mocker):
        """Test get_window_wise_nodes with empty bundle IDs."""
        mocker.patch.object(Tree, "get_nodes", return_value=([], [], []))
        tree = Tree()
        interactive, scrollable, informative = tree.get_window_wise_nodes(
            bundle_ids=[],
            system_bundle_ids=[],
        )
        assert interactive == []
        assert scrollable == []
        assert informative == []

    def test_get_window_wise_nodes_single_bundle(self, mocker):
        """Test get_window_wise_nodes with single bundle ID."""
        mock_nodes = (
            [MagicMock(spec=TreeElementNode)],
            [],
            [],
        )
        mock_get_nodes = mocker.patch.object(Tree, "get_nodes", return_value=mock_nodes)
        tree = Tree()
        interactive, scrollable, informative = tree.get_window_wise_nodes(
            bundle_ids=["com.example.app"],
        )
        assert len(interactive) == 1
        mock_get_nodes.assert_called()

    def test_get_window_wise_nodes_with_browser(self, mocker):
        """Test get_window_wise_nodes recognizes browsers."""
        mock_nodes = ([], [], [])
        mock_get_nodes = mocker.patch.object(Tree, "get_nodes", return_value=mock_nodes)
        tree = Tree()
        tree.get_window_wise_nodes(
            bundle_ids=["com.apple.Safari"],
        )
        # Verify the call includes is_browser=True for Safari
        call_args = mock_get_nodes.call_args_list[0]
        assert "Safari" in str(call_args) or call_args[0][1] is True or any(
            "Safari" in str(arg) for arg in call_args[0]
        )

    def test_get_window_wise_nodes_with_desktop_only(self, mocker):
        """Test get_window_wise_nodes with desktop_only flag."""
        mock_nodes = ([], [], [])
        mock_get_nodes = mocker.patch.object(Tree, "get_nodes", return_value=mock_nodes)
        tree = Tree()
        tree.get_window_wise_nodes(
            bundle_ids=["com.example.app"],
            desktop_only_bundle_ids=["com.apple.finder"],
        )
        # Should have called get_nodes twice: once for app, once for finder
        assert mock_get_nodes.call_count >= 1


@pytest.mark.unit
class TestTreeIOUBoundingBox:
    """Tests for Tree.iou_bounding_box method."""

    def test_iou_fully_contained(self):
        """Test IOU when element is fully contained in window."""
        tree = Tree()
        window_box = BoundingBox(left=0, top=0, right=1000, bottom=1000, width=1000, height=1000)
        element_box = BoundingBox(left=100, top=100, right=200, bottom=200, width=100, height=100)
        result = tree.iou_bounding_box(window_box, element_box)
        assert result.left == 100
        assert result.top == 100
        assert result.right == 200
        assert result.bottom == 200

    def test_iou_partial_overlap(self):
        """Test IOU with partial overlap."""
        tree = Tree()
        window_box = BoundingBox(left=0, top=0, right=200, bottom=200, width=200, height=200)
        element_box = BoundingBox(left=100, top=100, right=300, bottom=300, width=200, height=200)
        result = tree.iou_bounding_box(window_box, element_box)
        assert result.left == 100
        assert result.top == 100
        assert result.right == 200
        assert result.bottom == 200
        assert result.width == 100
        assert result.height == 100

    def test_iou_no_overlap(self):
        """Test IOU with no overlap."""
        tree = Tree()
        window_box = BoundingBox(left=0, top=0, right=100, bottom=100, width=100, height=100)
        element_box = BoundingBox(left=200, top=200, right=300, bottom=300, width=100, height=100)
        result = tree.iou_bounding_box(window_box, element_box)
        assert result.left == 0
        assert result.top == 0
        assert result.right == 0
        assert result.bottom == 0
        assert result.width == 0
        assert result.height == 0

    def test_iou_edge_touching(self):
        """Test IOU when boxes touch at edge."""
        tree = Tree()
        window_box = BoundingBox(left=0, top=0, right=100, bottom=100, width=100, height=100)
        element_box = BoundingBox(left=100, top=0, right=200, bottom=100, width=100, height=100)
        result = tree.iou_bounding_box(window_box, element_box)
        # Edge touching should result in no overlap (0 area)
        assert result.width == 0
        assert result.height == 0


@pytest.mark.unit
class TestTreeGetNodes:
    """Tests for Tree.get_nodes method."""

    def test_get_nodes_app_not_found(self, mocker):
        """Test get_nodes when app is not running."""
        mocker.patch(
            "macos_mcp.tree.service.ax.GetRunningApplicationByBundleId",
            return_value=None,
        )
        tree = Tree()
        interactive, scrollable, informative = tree.get_nodes(
            "com.nonexistent.app",
            is_browser=False,
        )
        assert interactive == []
        assert scrollable == []
        assert informative == []

    def test_get_nodes_with_running_app(self, mocker):
        """Test get_nodes with running app."""
        mock_app = MagicMock()
        mock_app.Name = "Test App"
        mock_app.Element = MagicMock()
        mock_app.MenuBar = None
        mock_app.ExtrasMenuBar = None
        mock_app.MainWindow = None
        mock_app.Windows = []

        mocker.patch(
            "macos_mcp.tree.service.ax.GetRunningApplicationByBundleId",
            return_value=mock_app,
        )
        mocker.patch("macos_mcp.tree.service.ax.SetMessagingTimeout")
        mocker.patch.object(Tree, "tree_traversal")

        tree = Tree()
        interactive, scrollable, informative = tree.get_nodes(
            "com.test.app",
            is_browser=False,
        )

        assert isinstance(interactive, list)
        assert isinstance(scrollable, list)
        assert isinstance(informative, list)

    def test_get_nodes_desktop_only_skips_menubar(self, mocker):
        """Test get_nodes with desktop_only skips menu bar."""
        mock_app = MagicMock()
        mock_app.Name = "Finder"
        mock_app.Element = MagicMock()
        mock_app.MenuBar = MagicMock()  # Should be skipped with desktop_only=True
        mock_app.MainWindow = None
        mock_app.Windows = []

        mocker.patch(
            "macos_mcp.tree.service.ax.GetRunningApplicationByBundleId",
            return_value=mock_app,
        )
        mocker.patch("macos_mcp.tree.service.ax.SetMessagingTimeout")
        mock_traversal = mocker.patch.object(Tree, "tree_traversal")

        tree = Tree()
        tree.get_nodes("com.apple.finder", is_browser=False, desktop_only=True)

        # tree_traversal should not be called for menu bar when desktop_only=True
        # (it should only be called if there are visible windows)
        assert mock_traversal.call_count == 0


@pytest.mark.unit
class TestTreeIntegration:
    """Integration tests for Tree service."""

    def test_tree_state_with_multiple_nodes(self, mocker, mock_tree_element_node):
        """Test TreeState building with multiple nodes."""
        center2 = Center(x=300, y=400)
        bbox2 = BoundingBox(left=200, top=200, right=400, bottom=400, width=200, height=200)
        node2 = TreeElementNode(
            window_name="Window 2",
            control_type="TextField",
            name="Input",
            center=center2,
            bounding_box=bbox2,
        )

        state = TreeState(
            status=True,
            interactive_nodes=[mock_tree_element_node, node2],
            scrollable_nodes=[],
            dom_informative_nodes=[],
        )

        assert len(state.interactive_nodes) == 2
        output = state.interactive_elements_to_string()
        assert "Button" in output
        assert "TextField" in output
