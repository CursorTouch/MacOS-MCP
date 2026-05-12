"""Tests for tree/views.py module."""

import pytest
import json
from macos_mcp.tree.views import (
    TreeState,
    BoundingBox,
    Center,
    TreeElementNode,
    ScrollElementNode,
    TextElementNode,
)


@pytest.mark.unit
class TestCenter:
    """Tests for Center dataclass."""

    def test_center_creation(self):
        """Test creating a Center instance."""
        center = Center(x=100, y=200)
        assert center.x == 100
        assert center.y == 200

    def test_center_to_string(self):
        """Test Center.to_string() method."""
        center = Center(x=100, y=200)
        assert center.to_string() == "(100,200)"

    def test_center_zero_coordinates(self):
        """Test Center with zero coordinates."""
        center = Center(x=0, y=0)
        assert center.to_string() == "(0,0)"

    def test_center_negative_coordinates(self):
        """Test Center with negative coordinates."""
        center = Center(x=-50, y=-100)
        assert center.to_string() == "(-50,-100)"


@pytest.mark.unit
class TestBoundingBox:
    """Tests for BoundingBox dataclass."""

    def test_bounding_box_creation(self):
        """Test creating a BoundingBox instance."""
        bbox = BoundingBox(left=0, top=0, right=800, bottom=600, width=800, height=600)
        assert bbox.left == 0
        assert bbox.top == 0
        assert bbox.right == 800
        assert bbox.bottom == 600
        assert bbox.width == 800
        assert bbox.height == 600

    def test_get_center(self):
        """Test BoundingBox.get_center() method."""
        bbox = BoundingBox(left=0, top=0, right=200, bottom=200, width=200, height=200)
        center = bbox.get_center()
        assert center.x == 100
        assert center.y == 100

    def test_get_center_with_offset(self):
        """Test BoundingBox.get_center() with offset coordinates."""
        bbox = BoundingBox(left=100, top=100, right=300, bottom=300, width=200, height=200)
        center = bbox.get_center()
        assert center.x == 200
        assert center.y == 200

    def test_xywh_to_string(self):
        """Test BoundingBox.xywh_to_string() method."""
        bbox = BoundingBox(left=10, top=20, right=110, bottom=120, width=100, height=100)
        assert bbox.xywh_to_string() == "(10,20,100,100)"

    def test_xyxy_to_string(self):
        """Test BoundingBox.xyxy_to_string() method."""
        bbox = BoundingBox(left=10, top=20, right=110, bottom=120, width=100, height=100)
        assert bbox.xyxy_to_string() == "(10,20,110,120)"

    def test_convert_xywh_to_xyxy(self):
        """Test BoundingBox.convert_xywh_to_xyxy() method."""
        bbox = BoundingBox(left=10, top=20, right=110, bottom=120, width=100, height=100)
        x1, y1, x2, y2 = bbox.convert_xywh_to_xyxy()
        assert x1 == 10
        assert y1 == 20
        assert x2 == 110
        assert y2 == 120

    def test_contains_fully_contained(self):
        """Test BoundingBox.contains() with fully contained box."""
        outer = BoundingBox(left=0, top=0, right=200, bottom=200, width=200, height=200)
        inner = BoundingBox(left=50, top=50, right=150, bottom=150, width=100, height=100)
        assert outer.contains(inner) is True

    def test_contains_equal_boxes(self):
        """Test BoundingBox.contains() with equal boxes."""
        bbox1 = BoundingBox(left=0, top=0, right=100, bottom=100, width=100, height=100)
        bbox2 = BoundingBox(left=0, top=0, right=100, bottom=100, width=100, height=100)
        assert bbox1.contains(bbox2) is True

    def test_contains_not_contained(self):
        """Test BoundingBox.contains() with non-contained box."""
        outer = BoundingBox(left=0, top=0, right=100, bottom=100, width=100, height=100)
        non_contained = BoundingBox(left=50, top=50, right=150, bottom=150, width=100, height=100)
        assert outer.contains(non_contained) is False

    def test_contains_partially_overlapping(self):
        """Test BoundingBox.contains() with partially overlapping boxes."""
        bbox1 = BoundingBox(left=0, top=0, right=100, bottom=100, width=100, height=100)
        bbox2 = BoundingBox(left=50, top=50, right=200, bottom=200, width=150, height=150)
        assert bbox1.contains(bbox2) is False


@pytest.mark.unit
class TestTreeElementNode:
    """Tests for TreeElementNode dataclass."""

    def test_tree_element_node_creation(self):
        """Test creating a TreeElementNode instance."""
        center = Center(x=100, y=200)
        bbox = BoundingBox(left=50, top=100, right=150, bottom=300, width=100, height=200)
        node = TreeElementNode(
            window_name="Test Window",
            control_type="Button",
            name="Click Me",
            center=center,
            bounding_box=bbox,
        )
        assert node.window_name == "Test Window"
        assert node.control_type == "Button"
        assert node.name == "Click Me"
        assert node.center == center
        assert node.bounding_box == bbox

    def test_tree_element_node_with_metadata(self):
        """Test TreeElementNode with metadata."""
        center = Center(x=100, y=200)
        bbox = BoundingBox(left=50, top=100, right=150, bottom=300, width=100, height=200)
        metadata = {"enabled": True, "visible": True}
        node = TreeElementNode(
            window_name="Test",
            control_type="Button",
            name="Test",
            center=center,
            bounding_box=bbox,
            metadata=metadata,
        )
        assert node.metadata == metadata


@pytest.mark.unit
class TestScrollElementNode:
    """Tests for ScrollElementNode dataclass."""

    def test_scroll_element_node_creation(self):
        """Test creating a ScrollElementNode instance."""
        center = Center(x=400, y=500)
        bbox = BoundingBox(left=0, top=0, right=800, bottom=600, width=800, height=600)
        node = ScrollElementNode(
            name="Scroll Area",
            control_type="ScrollArea",
            window_name="Main Window",
            center=center,
            bounding_box=bbox,
        )
        assert node.name == "Scroll Area"
        assert node.control_type == "ScrollArea"
        assert node.window_name == "Main Window"
        assert node.center == center
        assert node.bounding_box == bbox

    def test_scroll_element_node_to_row(self):
        """Test ScrollElementNode.to_row() method."""
        center = Center(x=400, y=500)
        bbox = BoundingBox(left=0, top=0, right=800, bottom=600, width=800, height=600)
        node = ScrollElementNode(
            name="Scroll",
            control_type="ScrollArea",
            window_name="Window",
            center=center,
            bounding_box=bbox,
            metadata={"scrollable": True},
        )
        row = node.to_row(0, 5)
        assert row[0] == 5
        assert row[1] == "Window"
        assert row[2] == "ScrollArea"


@pytest.mark.unit
class TestTextElementNode:
    """Tests for TextElementNode dataclass."""

    def test_text_element_node_creation(self):
        """Test creating a TextElementNode instance."""
        node = TextElementNode(text="Some text")
        assert node.text == "Some text"

    def test_text_element_node_empty(self):
        """Test TextElementNode with empty text."""
        node = TextElementNode(text="")
        assert node.text == ""


@pytest.mark.unit
class TestTreeState:
    """Tests for TreeState dataclass."""

    def test_tree_state_creation(self):
        """Test creating a TreeState instance."""
        state = TreeState()
        assert state.status is True
        assert state.root_node is None
        assert state.interactive_nodes == []
        assert state.scrollable_nodes == []
        assert state.dom_informative_nodes == []

    def test_tree_state_with_nodes(self):
        """Test TreeState with interactive nodes."""
        center = Center(x=100, y=200)
        bbox = BoundingBox(left=50, top=100, right=150, bottom=300, width=100, height=200)
        node = TreeElementNode(
            window_name="Test",
            control_type="Button",
            name="Click",
            center=center,
            bounding_box=bbox,
        )
        state = TreeState(interactive_nodes=[node])
        assert len(state.interactive_nodes) == 1
        assert state.interactive_nodes[0] == node

    def test_interactive_elements_to_string_with_nodes(self):
        """Test interactive_elements_to_string with nodes."""
        center = Center(x=100, y=200)
        bbox = BoundingBox(left=50, top=100, right=150, bottom=300, width=100, height=200)
        node = TreeElementNode(
            window_name="Test Window",
            control_type="Button",
            name="Click Me",
            center=center,
            bounding_box=bbox,
            metadata={"enabled": True},
        )
        state = TreeState(interactive_nodes=[node])
        result = state.interactive_elements_to_string()
        assert "# id|window|control_type|name|coords|metadata" in result
        assert "0|Test Window|Button|Click Me|(100,200)|" in result
        assert '"enabled": true' in result

    def test_interactive_elements_to_string_empty(self):
        """Test interactive_elements_to_string with no nodes."""
        state = TreeState(status=True, interactive_nodes=[])
        result = state.interactive_elements_to_string()
        assert result == "No elements found"

    def test_interactive_elements_to_string_status_unavailable(self):
        """Test interactive_elements_to_string when status is False."""
        state = TreeState(status=False, interactive_nodes=[])
        result = state.interactive_elements_to_string()
        assert "temporarily unavailable" in result

    def test_interactive_elements_to_string_multiple_nodes(self):
        """Test interactive_elements_to_string with multiple nodes."""
        center1 = Center(x=100, y=200)
        center2 = Center(x=300, y=400)
        bbox = BoundingBox(left=0, top=0, right=100, bottom=100, width=100, height=100)
        node1 = TreeElementNode(
            window_name="Window 1",
            control_type="Button",
            name="Button 1",
            center=center1,
            bounding_box=bbox,
        )
        node2 = TreeElementNode(
            window_name="Window 2",
            control_type="TextField",
            name="Input 1",
            center=center2,
            bounding_box=bbox,
        )
        state = TreeState(interactive_nodes=[node1, node2])
        result = state.interactive_elements_to_string()
        assert "0|Window 1|Button|Button 1|(100,200)|" in result
        assert "1|Window 2|TextField|Input 1|(300,400)|" in result

    def test_scrollable_elements_to_string_with_nodes(self):
        """Test scrollable_elements_to_string with nodes."""
        center = Center(x=400, y=500)
        bbox = BoundingBox(left=0, top=0, right=800, bottom=600, width=800, height=600)
        scroll_node = ScrollElementNode(
            name="Scroll Area",
            control_type="ScrollArea",
            window_name="Main Window",
            center=center,
            bounding_box=bbox,
            metadata={"scrollable": True},
        )
        state = TreeState(interactive_nodes=[], scrollable_nodes=[scroll_node])
        result = state.scrollable_elements_to_string()
        assert "# id|window|control_type|name|coords|metadata" in result
        assert "0|Main Window|ScrollArea|Scroll Area|(400,500)|" in result

    def test_scrollable_elements_to_string_with_interactive_base_index(self):
        """Test scrollable_elements_to_string base index calculation."""
        center1 = Center(x=100, y=200)
        center2 = Center(x=400, y=500)
        bbox = BoundingBox(left=0, top=0, right=100, bottom=100, width=100, height=100)
        interactive_node = TreeElementNode(
            window_name="Window",
            control_type="Button",
            name="Button",
            center=center1,
            bounding_box=bbox,
        )
        scroll_node = ScrollElementNode(
            name="Scroll",
            control_type="ScrollArea",
            window_name="Window",
            center=center2,
            bounding_box=bbox,
        )
        state = TreeState(interactive_nodes=[interactive_node], scrollable_nodes=[scroll_node])
        result = state.scrollable_elements_to_string()
        # Base index should be 1 (length of interactive_nodes)
        assert "1|Window|ScrollArea|Scroll|(400,500)|" in result

    def test_scrollable_elements_to_string_empty(self):
        """Test scrollable_elements_to_string with no nodes."""
        state = TreeState(status=True, scrollable_nodes=[])
        result = state.scrollable_elements_to_string()
        assert result == "No elements found"

    def test_scrollable_elements_to_string_status_unavailable(self):
        """Test scrollable_elements_to_string when status is False."""
        state = TreeState(status=False, scrollable_nodes=[])
        result = state.scrollable_elements_to_string()
        assert "temporarily unavailable" in result
