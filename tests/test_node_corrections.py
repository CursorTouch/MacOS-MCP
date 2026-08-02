"""Characterisation tests for _dom_correction / _desktop_correction.

These pin the *current* behaviour of the two node-correction passes before
they are refactored. They deliberately assert on the resulting contents of
`interactive_nodes`, which is the observable outcome either way, so the same
assertions survive a change in how the functions are invoked.

Both passes currently work by side effect: the caller appends a node, then
the correction pops that node back off and appends a replacement. The cases
worth pinning are the ones where the node count changes -- in particular a
link wrapping a rect-less heading, which pops without appending and so
removes the node entirely.
"""

import pytest

from macos_mcp.ax.core import Rect
from macos_mcp.tree.service import Tree
from macos_mcp.tree.views import BoundingBox, Center, TreeElementNode


def make_node(name="original", control_type="AXLink", metadata=None):
    return TreeElementNode(
        bounding_box=BoundingBox(left=0, top=0, right=10, bottom=10, width=10, height=10),
        center=Center(x=5, y=5),
        name=name,
        control_type=control_type,
        window_name="Win",
        metadata=metadata if metadata is not None else {"axidentifier": "orig"},
    )


def batch(role, label="", identifier="", rect=Rect(left=1, top=2, right=11, bottom=12)):
    """Shape returned by ax.GetTraversalBatch."""
    return {"role": role, "label": label, "identifier": identifier, "rect": rect}


def apply(correction, attrs, nodes, window_name="Win", window_box=None):
    """Run a correction over the tail of `nodes`, mirroring how the traversal
    now uses it: transform the node, then append only if it survives.

    Only the call shape changed in the refactor; every assertion below is
    unchanged from when these functions mutated the list directly.
    """
    node = nodes.pop()
    result = correction(attrs, node, window_name, window_box)
    if result is not None:
        nodes.append(result)
    return nodes


@pytest.fixture
def tree():
    return Tree()


@pytest.mark.unit
class TestDomCorrection:
    """Browser pass: an AXLink whose first child is an AXHeading is replaced
    by the heading itself."""

    def test_link_wrapping_heading_is_replaced(self, tree, mocker):
        mocker.patch(
            "macos_mcp.tree.service.ax.GetTraversalBatch",
            return_value=batch("AXHeading", label="Section title", identifier="h1"),
        )
        nodes = [make_node()]

        apply(tree._dom_correction, {"role": "AXLink", "children": ["<child>"]}, nodes)

        assert len(nodes) == 1
        assert nodes[0].control_type == "AXHeading"
        assert nodes[0].name == "Section title"
        assert nodes[0].metadata == {"axidentifier": "h1"}

    def test_heading_without_rect_drops_the_node_entirely(self, tree, mocker):
        """The pop is unconditional but the append is not, so the node
        disappears. Pinned because it is easy to lose in a refactor."""
        mocker.patch(
            "macos_mcp.tree.service.ax.GetTraversalBatch",
            return_value=batch("AXHeading", rect=None),
        )
        nodes = [make_node()]

        apply(tree._dom_correction, {"role": "AXLink", "children": ["<child>"]}, nodes)

        assert nodes == [], "a rect-less heading currently removes the node"

    def test_non_heading_child_leaves_the_node_untouched(self, tree, mocker):
        mocker.patch(
            "macos_mcp.tree.service.ax.GetTraversalBatch",
            return_value=batch("AXStaticText", label="not a heading"),
        )
        original = make_node()
        nodes = [original]

        apply(tree._dom_correction, {"role": "AXLink", "children": ["<child>"]}, nodes)

        assert nodes == [original]

    def test_link_without_children_is_untouched(self, tree):
        original = make_node()
        nodes = [original]

        apply(tree._dom_correction, {"role": "AXLink", "children": []}, nodes)

        assert nodes == [original]

    def test_other_roles_are_untouched(self, tree):
        original = make_node(control_type="AXButton")
        nodes = [original]

        apply(tree._dom_correction, {"role": "AXButton", "children": ["<child>"]}, nodes)

        assert nodes == [original]

    def test_bounding_box_is_clipped_to_the_window(self, tree, mocker):
        mocker.patch(
            "macos_mcp.tree.service.ax.GetTraversalBatch",
            return_value=batch("AXHeading", rect=Rect(left=0, top=0, right=1000, bottom=1000)),
        )
        window = BoundingBox(left=0, top=0, right=100, bottom=100, width=100, height=100)
        nodes = [make_node()]

        apply(tree._dom_correction, {"role": "AXLink", "children": ["<child>"]}, nodes, "Win", window
        )

        assert nodes[0].bounding_box.right <= 100
        assert nodes[0].bounding_box.bottom <= 100


@pytest.mark.unit
class TestDesktopCorrection:
    """Native pass: cells/groups take their label from the first descendant
    AXStaticText; window-control buttons get a human-readable name."""

    @staticmethod
    def _static_text(mocker, value, depth=1):
        """Mock the descend-until-AXStaticText walk."""
        import macos_mcp.ax as ax

        calls = {"n": 0}

        def fake(_element, _attributes):
            calls["n"] += 1
            if calls["n"] >= depth:
                return {ax.Attribute.Role: "AXStaticText", ax.Attribute.Value: value}
            return {ax.Attribute.Role: "AXGroup", ax.Attribute.Children: ["<deeper>"]}

        mocker.patch("macos_mcp.tree.service.ax.GetMultipleAttributeValues", side_effect=fake)

    @pytest.mark.parametrize("role", ["AXCell", "AXGroup"])
    def test_label_taken_from_descendant_static_text(self, tree, mocker, role):
        self._static_text(mocker, "Downloads")
        nodes = [make_node(control_type=role, metadata={"axidentifier": "keep"})]

        apply(tree._desktop_correction, {"role": role, "rect": Rect(0, 0, 10, 10), "children": ["<c>"]}, nodes)

        assert len(nodes) == 1
        assert nodes[0].name == "Downloads"
        assert nodes[0].control_type == role
        assert nodes[0].metadata == {"axidentifier": "keep"}, "metadata carries over"

    def test_static_text_found_several_levels_down(self, tree, mocker):
        self._static_text(mocker, "Deep", depth=3)
        nodes = [make_node(control_type="AXCell")]

        apply(tree._desktop_correction, {"role": "AXCell", "rect": Rect(0, 0, 10, 10), "children": ["<c>"]}, nodes)

        assert nodes[0].name == "Deep"

    def test_cell_without_static_text_is_untouched(self, tree, mocker):
        import macos_mcp.ax as ax

        mocker.patch(
            "macos_mcp.tree.service.ax.GetMultipleAttributeValues",
            return_value={ax.Attribute.Role: "AXGroup", ax.Attribute.Children: []},
        )
        original = make_node(control_type="AXCell")
        nodes = [original]

        apply(tree._desktop_correction, {"role": "AXCell", "rect": Rect(0, 0, 10, 10), "children": ["<c>"]}, nodes)

        assert nodes == [original]

    def test_cell_with_no_children_is_untouched(self, tree):
        original = make_node(control_type="AXCell")
        nodes = [original]

        apply(tree._desktop_correction, {"role": "AXCell", "rect": Rect(0, 0, 10, 10), "children": []}, nodes)

        assert nodes == [original]

    def test_empty_static_text_still_replaces(self, tree, mocker):
        """Guarded on `is not None`, so an empty string still counts."""
        self._static_text(mocker, "")
        nodes = [make_node(control_type="AXCell", name="before")]

        apply(tree._desktop_correction, {"role": "AXCell", "rect": Rect(0, 0, 10, 10), "children": ["<c>"]}, nodes)

        assert nodes[0].name == ""

    @pytest.mark.parametrize(
        "subrole,expected",
        [
            ("AXCloseButton", "Close Button"),
            ("AXMinimizeButton", "Minimize Button"),
            ("AXZoomButton", "Zoom Button"),
            ("AXFullScreenButton", "Full Screen Button"),
        ],
    )
    def test_window_control_buttons_get_readable_names(self, tree, subrole, expected):
        nodes = [make_node(control_type="AXButton", metadata={"axidentifier": "keep"})]

        apply(tree._desktop_correction, {"role": "AXButton", "subrole": subrole, "rect": Rect(0, 0, 10, 10)}, nodes)

        assert len(nodes) == 1
        assert nodes[0].name == expected
        assert nodes[0].control_type == "AXButton"
        assert nodes[0].metadata == {"axidentifier": "keep"}

    def test_ordinary_button_is_untouched(self, tree):
        original = make_node(control_type="AXButton")
        nodes = [original]

        apply(tree._desktop_correction, {"role": "AXButton", "subrole": "AXSomethingElse", "rect": Rect(0, 0, 10, 10)}, nodes)

        assert nodes == [original]

    def test_unrelated_role_is_untouched(self, tree):
        original = make_node(control_type="AXSlider")
        nodes = [original]

        apply(tree._desktop_correction,
              {"role": "AXSlider", "subrole": "", "rect": Rect(0, 0, 10, 10)}, nodes)

        assert nodes == [original]


@pytest.mark.unit
class TestOnlyTheLastNodeIsTouched:
    """Both passes reach into a list they do not own and mutate its tail.

    This is the coupling the refactor removes: nothing in the signature says
    the node of interest must be last.
    """

    def test_earlier_nodes_are_preserved(self, tree, mocker):
        mocker.patch(
            "macos_mcp.tree.service.ax.GetTraversalBatch",
            return_value=batch("AXHeading", label="Heading"),
        )
        earlier = make_node(name="earlier")
        nodes = [earlier, make_node(name="target")]

        apply(tree._dom_correction, {"role": "AXLink", "children": ["<child>"]}, nodes)

        assert nodes[0] is earlier
        assert nodes[1].name == "Heading"
