"""Shared fixtures and configuration for tests."""

import pytest
from unittest.mock import Mock, MagicMock
from macos_mcp.desktop.views import Window, Status
from macos_mcp.tree.views import TreeState, TreeElementNode, Center, BoundingBox


@pytest.fixture
def mock_bounding_box():
    """Create a mock bounding box."""
    return BoundingBox(left=0, top=0, right=800, bottom=600, width=800, height=600)


@pytest.fixture
def mock_window(mock_bounding_box):
    """Create a mock window."""
    return Window(
        name="Test Window",
        is_browser=False,
        status=Status.ACTIVE,
        bounding_box=mock_bounding_box,
        pid=1234,
        bundle_id="com.example.app",
    )


@pytest.fixture
def mock_browser_window(mock_bounding_box):
    """Create a mock browser window."""
    return Window(
        name="Safari",
        is_browser=True,
        status=Status.ACTIVE,
        bounding_box=mock_bounding_box,
        pid=5678,
        bundle_id="com.apple.Safari",
    )


@pytest.fixture
def mock_center():
    """Create a mock center point."""
    return Center(x=100, y=200)


@pytest.fixture
def mock_tree_element_node(mock_center, mock_bounding_box):
    """Create a mock tree element node."""
    return TreeElementNode(
        window_name="Test Window",
        control_type="Button",
        name="Click Me",
        center=mock_center,
        bounding_box=mock_bounding_box,
        metadata={},
    )


@pytest.fixture
def mock_tree_state(mock_tree_element_node):
    """Create a mock tree state."""
    return TreeState(
        status=True,
        root_node=None,
        dom_node=None,
        interactive_nodes=[mock_tree_element_node],
        scrollable_nodes=[],
        dom_informative_nodes=[],
    )
