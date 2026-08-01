"""Tests for character-range text access (the macOS TOM/TextPattern analogue)."""

import pytest

from macos_mcp.ax.core import MakeCFRange, ParseCFRange
from macos_mcp.ax.enums import Attribute
from macos_mcp.ax.text import TextRange, TextRangeMixin


class FakeControl(TextRangeMixin):
    """Stands in for a Control; only .Element is ever touched."""

    def __init__(self, element="<element>"):
        self.Element = element


# Attribute name spellings are pinned by tests/test_parameterized_attributes.py.


@pytest.mark.unit
class TestCFRangeMarshalling:
    """Tests for boxing/unboxing CFRange through AXValue."""

    def test_round_trip_through_axvalue(self):
        assert ParseCFRange(MakeCFRange(4, 15)) == (4, 15)

    def test_zero_length_range_survives(self):
        """A caret is a zero-length range and must not be mistaken for absent."""
        assert ParseCFRange(MakeCFRange(83, 0)) == (83, 0)

    def test_parses_plain_tuple(self):
        """PyObjC hands back a bare 2-tuple rather than a .location object."""
        assert ParseCFRange((7, 3)) == (7, 3)

    def test_parses_object_with_location_and_length(self):
        class Raw:
            location, length = 5, 9

        assert ParseCFRange(Raw()) == (5, 9)

    def test_none_is_not_a_range(self):
        assert ParseCFRange(None) is None


@pytest.mark.unit
class TestTextRange:
    """Tests for the range object itself."""

    def test_end_and_len(self):
        r = TextRange(FakeControl(), 10, 5)
        assert r.end == 15
        assert len(r) == 5

    def test_text_reads_string_for_range(self, mocker):
        get = mocker.patch("macos_mcp.ax.text.GetParameterizedAttribute", return_value="quick brown fox")
        assert TextRange(FakeControl(), 4, 15).text == "quick brown fox"
        assert get.call_args[0][1] == Attribute.StringForRange

    def test_text_is_empty_when_unsupported(self, mocker):
        mocker.patch("macos_mcp.ax.text.GetParameterizedAttribute", return_value=None)
        assert TextRange(FakeControl(), 4, 15).text == ""

    def test_bounds_returns_none_when_unsupported(self, mocker):
        mocker.patch("macos_mcp.ax.text.GetParameterizedAttribute", return_value=None)
        assert TextRange(FakeControl(), 4, 15).bounds is None

    def test_expand_to_line_widens_to_the_line(self, mocker):
        def fake(_element, attribute, _param):
            return {Attribute.LineForIndex: 1, Attribute.RangeForLine: (45, 18)}.get(attribute)

        mocker.patch("macos_mcp.ax.text.GetParameterizedAttribute", side_effect=fake)
        expanded = TextRange(FakeControl(), 50, 0).expand_to_line()
        assert (expanded.location, expanded.length) == (45, 18)

    def test_expand_to_line_is_identity_when_unsupported(self, mocker):
        """Degrade to self rather than raising, so callers can chain freely."""
        mocker.patch("macos_mcp.ax.text.GetParameterizedAttribute", return_value=None)
        original = TextRange(FakeControl(), 50, 3)
        assert original.expand_to_line() == original

    def test_select_sets_the_selection_range(self, mocker):
        setter = mocker.patch("macos_mcp.ax.text.SetAttribute", return_value=True)
        assert TextRange(FakeControl(), 4, 15).select() is True
        assert setter.call_args[0][1] == Attribute.SelectedTextRange

    def test_replace_prefers_replace_range_with_text(self, mocker):
        mocker.patch(
            "macos_mcp.ax.text.GetParameterizedAttributeNames",
            return_value=[Attribute.ReplaceRangeWithText],
        )
        call = mocker.patch("macos_mcp.ax.text.GetParameterizedAttribute", return_value=True)
        setter = mocker.patch("macos_mcp.ax.text.SetAttribute")

        assert TextRange(FakeControl(), 4, 15).replace("turtle") is True
        assert call.call_args[0][1] == Attribute.ReplaceRangeWithText
        setter.assert_not_called()

    def test_replace_falls_back_to_selection(self, mocker):
        """Without AXReplaceRangeWithText, select then write AXSelectedText."""
        mocker.patch("macos_mcp.ax.text.GetParameterizedAttributeNames", return_value=[])
        setter = mocker.patch("macos_mcp.ax.text.SetAttribute", return_value=True)

        assert TextRange(FakeControl(), 4, 15).replace("turtle") is True
        assert [c[0][1] for c in setter.call_args_list] == [
            Attribute.SelectedTextRange,
            Attribute.SelectedText,
        ]


@pytest.mark.unit
class TestTextRangeMixin:
    """Tests for the accessors mixed into Control."""

    def test_supports_text_ranges_detects_capability(self, mocker):
        mocker.patch(
            "macos_mcp.ax.text.GetParameterizedAttributeNames",
            return_value=[Attribute.StringForRange],
        )
        assert FakeControl().SupportsTextRanges is True

    def test_supports_text_ranges_false_when_nothing_advertised(self, mocker):
        mocker.patch("macos_mcp.ax.text.GetParameterizedAttributeNames", return_value=[])
        assert FakeControl().SupportsTextRanges is False

    def test_full_text_range_spans_the_document(self, mocker):
        mocker.patch("macos_mcp.ax.text.GetAttribute", return_value=83)
        full = FakeControl().FullTextRange
        assert (full.location, full.length) == (0, 83)

    def test_full_text_range_none_when_length_unknown(self, mocker):
        mocker.patch("macos_mcp.ax.text.GetAttribute", return_value=None)
        assert FakeControl().FullTextRange is None

    def test_selection_range_reads_selected_text_range(self, mocker):
        mocker.patch("macos_mcp.ax.text.GetAttribute", return_value=(4, 15))
        selection = FakeControl().SelectionRange
        assert (selection.location, selection.length) == (4, 15)

    def test_text_around_clamps_at_document_start(self, mocker):
        """Asking past the start must clamp, since some apps fail outright."""
        control = FakeControl()
        mocker.patch.object(
            type(control), "SelectionRange", property(lambda self: TextRange(self, 2, 0))
        )
        mocker.patch("macos_mcp.ax.text.GetAttribute", return_value=83)
        captured = {}

        def fake(_element, _attribute, param):
            captured["range"] = ParseCFRange(param)
            return "clamped"

        mocker.patch("macos_mcp.ax.text.GetParameterizedAttribute", side_effect=fake)
        control.TextAround(before=500, after=10)

        assert captured["range"][0] == 0, "must not request a negative location"

    def test_text_around_clamps_at_document_end(self, mocker):
        control = FakeControl()
        mocker.patch.object(
            type(control), "SelectionRange", property(lambda self: TextRange(self, 80, 0))
        )
        mocker.patch("macos_mcp.ax.text.GetAttribute", return_value=83)
        captured = {}

        def fake(_element, _attribute, param):
            captured["range"] = ParseCFRange(param)
            return "clamped"

        mocker.patch("macos_mcp.ax.text.GetParameterizedAttribute", side_effect=fake)
        control.TextAround(before=10, after=500)

        location, length = captured["range"]
        assert location + length <= 83, "must not read past the end of the document"

    def test_text_around_empty_without_a_selection(self, mocker):
        control = FakeControl()
        mocker.patch.object(
            type(control), "SelectionRange", property(lambda self: None)
        )
        assert control.TextAround() == ""
