"""Tests for character-range text access (the macOS TOM/TextPattern analogue)."""

import pytest

from macos_mcp.ax.core import MakeCFRange, ParseCFRange, Rect
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


@pytest.mark.unit
class TestSplitByLine:
    """AXBoundsForRange collapses a multi-line range into one union rect
    spanning both lines and the full column width, so ranges are clipped to
    each line before asking for geometry."""

    LINES = [(0, 45), (45, 18)]

    def test_range_within_one_line_is_untouched(self):
        assert FakeControl()._split_by_line(4, 15, self.LINES) == [(4, 15)]

    def test_range_spanning_two_lines_is_split(self):
        assert FakeControl()._split_by_line(40, 11, self.LINES) == [(40, 5), (45, 6)]

    def test_range_spanning_many_lines_yields_one_segment_each(self):
        lines = [(0, 10), (10, 10), (20, 10), (30, 10)]
        assert FakeControl()._split_by_line(5, 20, lines) == [(5, 5), (10, 10), (20, 5)]

    def test_without_a_line_table_the_range_passes_through(self):
        """Apps that don't expose AXRangeForLine still get one box per word."""
        assert FakeControl()._split_by_line(40, 11, []) == [(40, 11)]

    def test_range_outside_every_line_falls_back_to_itself(self):
        assert FakeControl()._split_by_line(500, 3, self.LINES) == [(500, 3)]


@pytest.mark.unit
class TestShrinkToFontSize:
    """AXBoundsForRange reports the line box, which is taller than the glyphs."""

    def test_shrinks_from_the_top_anchored_to_the_baseline(self):
        rect = Rect(left=151, top=96, right=184, bottom=109)  # 13pt line box
        shrunk = TextRangeMixin._shrink_to_font_size(rect, 11.0)
        assert (shrunk.top, shrunk.bottom) == (98, 109)
        assert (shrunk.left, shrunk.right) == (151, 184)

    def test_no_op_when_font_is_taller_than_the_box(self):
        rect = Rect(left=0, top=0, right=10, bottom=10)
        assert TextRangeMixin._shrink_to_font_size(rect, 20.0) is rect

    def test_no_op_on_nonsense_font_size(self):
        rect = Rect(left=0, top=0, right=10, bottom=10)
        assert TextRangeMixin._shrink_to_font_size(rect, 0) is rect


@pytest.mark.unit
class TestWordBoundingBoxes:
    """Tests for the whole-document word walk."""

    @staticmethod
    def _setup(mocker, text, bounds=Rect(0, 0, 10, 10), advertises=None, lines=None):
        control = FakeControl()
        mocker.patch(
            "macos_mcp.ax.text.GetParameterizedAttributeNames",
            return_value=[Attribute.BoundsForRange] if advertises is None else advertises,
        )
        mocker.patch.object(
            type(control), "FullTextRange",
            property(lambda self: TextRange(self, 0, len(text))),
        )
        mocker.patch.object(type(control), "_line_table", lambda self, total: lines or [])
        mocker.patch.object(type(control), "_document_font_size", lambda self: None)
        mocker.patch.object(
            TextRange, "text", property(lambda self: text[self.location : self.end])
        )
        mocker.patch.object(TextRange, "bounds", property(lambda self: bounds))
        return control

    def test_returns_one_entry_per_whitespace_delimited_token(self, mocker):
        control = self._setup(mocker, "The quick brown fox")
        assert [word for word, _ in control.WordBoundingBoxes()] == [
            "The", "quick", "brown", "fox",
        ]

    def test_punctuation_stays_attached_to_the_token(self, mocker):
        """A clickable target, not a linguistic word: 'dog.' is one box."""
        control = self._setup(mocker, "the lazy dog.")
        assert [word for word, _ in control.WordBoundingBoxes()][-1] == "dog."

    def test_none_when_bounds_for_range_is_not_advertised(self, mocker):
        """Chrome's omnibox answers the call with Rect(0,900,0,900); handing
        back a zero-area box whose centre is a real screen coordinate would
        invite a misdirected click."""
        control = self._setup(mocker, "hello world", advertises=[Attribute.StringForRange])
        assert control.WordBoundingBoxes() is None

    def test_degenerate_rects_are_dropped(self, mocker):
        control = self._setup(mocker, "hello", bounds=Rect(0, 900, 0, 900))
        assert control.WordBoundingBoxes() == []

    def test_none_when_text_is_unavailable(self, mocker):
        control = self._setup(mocker, "")
        assert control.WordBoundingBoxes() is None

    def test_wrapped_word_gets_one_box_per_line(self, mocker):
        """A soft-wrapped token spans lines; each line needs its own rect."""
        text = "ab " + "X" * 19  # 22 chars: a short token, then one that wraps
        control = self._setup(mocker, text, lines=[(0, 12), (12, 10)])

        words = control.WordBoundingBoxes()

        assert [word for word, _ in words] == ["ab", "X" * 19]
        assert len(words[0][1]) == 1, "the short token sits on one line"
        assert len(words[1][1]) == 2, "the wrapped token should yield two boxes"

    def test_shrink_can_be_disabled(self, mocker):
        control = self._setup(mocker, "hi")
        called = []
        mocker.patch.object(
            type(control), "_document_font_size", lambda self: called.append(1) or 11.0
        )
        control.WordBoundingBoxes(shrink_to_font=False)
        assert not called, "font size must not be queried when shrinking is off"
