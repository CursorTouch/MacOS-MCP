"""Character-range access to text controls.

This is the macOS counterpart to the Windows Text Object Model (TOM) /
UI Automation's TextPattern. There is no single COM-style interface here:
out of process, the equivalent surface is the Accessibility API's
*parameterized* attributes, which take an argument and so can express
ranges rather than just whole-element values.

    TOM                            AX equivalent
    ---------------------------    ------------------------------
    ITextDocument                  the AXTextArea / AXTextField
    ITextRange                     CFRange (kAXValueCFRangeType)
    ITextRange::GetText            AXStringForRange
    ITextFont / ITextPara          AXAttributedStringForRange
    Expand(tomLine)                AXRangeForLine / AXLineForIndex
    Expand(tomWord)-ish            AXStyleRangeForIndex
    SetRange / Select              AXSelectedTextRange (settable)
    GetPoint                       AXBoundsForRange
    RangeFromPoint                 AXRangeForPosition

Support is uneven and cannot be inferred from the role, so every accessor
degrades to None/"" rather than raising. Measured against live apps:
TextEdit's AXTextArea advertises 11 parameterized attributes and Chrome's
AXWebArea advertises 44, but Chrome's omnibox AXTextField advertises only
6 -- it has AXStringForRange but no AXBoundsForRange, so text reads fine
there while range geometry comes back as a degenerate rectangle. Partial
support is the normal case, not the exception.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from .core import (
    GetAttribute,
    GetParameterizedAttribute,
    GetParameterizedAttributeNames,
    MakeCFRange,
    ParseCFRange,
    Rect,
    SetAttribute,
)
from .enums import Attribute, AXValueType

if TYPE_CHECKING:
    from .controls import Control

logger = logging.getLogger(__name__)

# Attributes that must be advertised for range access to be meaningful.
_CORE_RANGE_ATTRIBUTES = (Attribute.StringForRange, Attribute.BoundsForRange)


def _parse_cg_rect(value: Any) -> Optional[Rect]:
    """Unbox an AXValue holding a CGRect into a Rect."""
    if value is None:
        return None
    origin = getattr(value, "origin", None)
    size = getattr(value, "size", None)
    if origin is not None and size is not None:
        return Rect.from_position_size(origin.x, origin.y, size.width, size.height)
    try:
        from ApplicationServices import AXValueGetValue

        success, raw = AXValueGetValue(value, AXValueType.CGRect, None)
        if success and raw is not None and raw is not value:
            return _parse_cg_rect(raw)
    except Exception:
        pass
    return None


@dataclass(frozen=True)
class TextRange:
    """A character range within a text control, plus the operations on it.

    Immutable: navigation methods return a new TextRange rather than mutating,
    which differs from TOM's ITextRange but avoids the aliasing surprises that
    come with a live cursor object.
    """

    control: "Control"
    location: int
    length: int

    # -- geometry -----------------------------------------------------------

    @property
    def end(self) -> int:
        return self.location + self.length

    def __len__(self) -> int:
        return self.length

    def __repr__(self) -> str:
        return f"TextRange(location={self.location}, length={self.length})"

    # -- reading ------------------------------------------------------------

    @property
    def text(self) -> str:
        """The plain text in this range, or "" if unsupported."""
        value = GetParameterizedAttribute(
            self.control.Element,
            Attribute.StringForRange,
            MakeCFRange(self.location, self.length),
        )
        return str(value) if value is not None else ""

    @property
    def attributed_text(self) -> Optional[Any]:
        """The NSAttributedString for this range, carrying font/style runs.

        This is the closest analogue to TOM's ITextFont/ITextPara: the
        formatting arrives as attribute runs on the string rather than as a
        separate interface.
        """
        return GetParameterizedAttribute(
            self.control.Element,
            Attribute.AttributedStringForRange,
            MakeCFRange(self.location, self.length),
        )

    @property
    def bounds(self) -> Optional[Rect]:
        """Screen-coordinate bounds of this range.

        This is what turns a text offset into something clickable.
        """
        return _parse_cg_rect(
            GetParameterizedAttribute(
                self.control.Element,
                Attribute.BoundsForRange,
                MakeCFRange(self.location, self.length),
            )
        )

    # -- navigation (TOM's Expand) ------------------------------------------

    def expand_to_line(self) -> "TextRange":
        """Widen to the full line containing this range's start."""
        line = GetParameterizedAttribute(
            self.control.Element, Attribute.LineForIndex, self.location
        )
        if line is None:
            return self
        parsed = ParseCFRange(
            GetParameterizedAttribute(
                self.control.Element, Attribute.RangeForLine, int(line)
            )
        )
        if parsed is None:
            return self
        return TextRange(self.control, parsed[0], parsed[1])

    def expand_to_style(self) -> "TextRange":
        """Widen to the surrounding run of uniform styling."""
        parsed = ParseCFRange(
            GetParameterizedAttribute(
                self.control.Element, Attribute.StyleRangeForIndex, self.location
            )
        )
        if parsed is None:
            return self
        return TextRange(self.control, parsed[0], parsed[1])

    # -- writing ------------------------------------------------------------

    def select(self) -> bool:
        """Make this range the control's selection."""
        return SetAttribute(
            self.control.Element,
            Attribute.SelectedTextRange,
            MakeCFRange(self.location, self.length),
        )

    def replace(self, text: str) -> bool:
        """Replace this range's contents.

        Prefers AXReplaceRangeWithText where advertised; otherwise selects the
        range and writes through AXSelectedText, which is more widely
        implemented but clobbers the user's selection as a side effect.
        """
        if Attribute.ReplaceRangeWithText in GetParameterizedAttributeNames(
            self.control.Element
        ):
            result = GetParameterizedAttribute(
                self.control.Element,
                Attribute.ReplaceRangeWithText,
                [MakeCFRange(self.location, self.length), text],
            )
            if result is not None:
                return True
        if not self.select():
            return False
        return SetAttribute(self.control.Element, Attribute.SelectedText, text)


class TextRangeMixin:
    """Range-based text access, mixed into Control.

    Kept separate from Control's own surface because none of it is meaningful
    for the majority of elements, and because every method here has to assume
    the app may implement none of it.
    """

    @property
    def SupportsTextRanges(self) -> bool:
        """Whether this element advertises usable range attributes."""
        advertised = set(GetParameterizedAttributeNames(self.Element))
        return any(name in advertised for name in _CORE_RANGE_ATTRIBUTES)

    @property
    def ParameterizedAttributes(self) -> List[str]:
        """Everything this element advertises; useful for probing an unknown app."""
        return GetParameterizedAttributeNames(self.Element)

    def MakeTextRange(self, location: int, length: int) -> TextRange:
        """Construct a range against this control without validating it."""
        return TextRange(self, location, length)

    @property
    def FullTextRange(self) -> Optional[TextRange]:
        """The whole document, or None if the length is unknown."""
        count = GetAttribute(self.Element, Attribute.NumberOfCharacters)
        if count is None:
            return None
        return TextRange(self, 0, int(count))

    @property
    def SelectionRange(self) -> Optional[TextRange]:
        """The current selection. A caret is a zero-length range at its offset."""
        parsed = ParseCFRange(GetAttribute(self.Element, Attribute.SelectedTextRange))
        if parsed is None:
            return None
        return TextRange(self, parsed[0], parsed[1])

    def LineRange(self, line: int) -> Optional[TextRange]:
        """The range covering a zero-based line index."""
        parsed = ParseCFRange(
            GetParameterizedAttribute(self.Element, Attribute.RangeForLine, int(line))
        )
        if parsed is None:
            return None
        return TextRange(self, parsed[0], parsed[1])

    def RangeAtPoint(self, x: float, y: float) -> Optional[TextRange]:
        """Hit-test a screen point to a character range."""
        from ApplicationServices import AXValueCreate
        from CoreFoundation import CGPoint

        point = AXValueCreate(AXValueType.CGPoint, CGPoint(float(x), float(y)))
        parsed = ParseCFRange(
            GetParameterizedAttribute(self.Element, Attribute.RangeForPosition, point)
        )
        if parsed is None:
            return None
        return TextRange(self, parsed[0], parsed[1])

    def TextAround(self, before: int = 200, after: int = 200) -> str:
        """Read the text surrounding the caret.

        The common agent question -- "what is the user looking at right now?" --
        answered without a screenshot. Clamped to the document bounds, since
        asking for a range past the end fails outright on some apps rather
        than truncating.
        """
        selection = self.SelectionRange
        if selection is None:
            return ""
        count = GetAttribute(self.Element, Attribute.NumberOfCharacters)
        total = int(count) if count is not None else selection.end + after

        start = max(0, selection.location - before)
        end = min(total, selection.end + after)
        if end <= start:
            return ""
        return TextRange(self, start, end - start).text

    def _line_table(self, total: int) -> List[Tuple[int, int]]:
        """Return (location, length) for each line, or [] if lines aren't exposed.

        Built once and reused for every word. Resolving a word's line by
        arithmetic against this table costs nothing, whereas asking the app
        per word (AXLineForIndex + AXRangeForLine) would add two round-trips
        each -- and AX calls are the dominant cost of a whole-document walk.
        """
        lines: List[Tuple[int, int]] = []
        offset = 0
        while offset < total:
            parsed = ParseCFRange(
                GetParameterizedAttribute(self.Element, Attribute.RangeForLine, len(lines))
            )
            if parsed is None:
                return []
            location, length = parsed
            if length <= 0 or location + length <= offset:
                break  # not advancing; bail rather than spin
            lines.append((location, length))
            offset = location + length
        return lines

    def _split_by_line(
        self, location: int, length: int, lines: List[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """Clip a range to each line it touches.

        AXBoundsForRange collapses a multi-line range into a single union
        rectangle spanning both lines and the full column width, which is
        useless as a bounding box. Splitting first yields one tight rect per
        line, matching what UIA's GetBoundingRectangles returns natively.
        """
        if not lines:
            return [(location, length)]
        end = location + length
        segments = [
            (max(location, line_start), min(end, line_start + line_length))
            for line_start, line_length in lines
            if line_start < end and line_start + line_length > location
        ]
        return [(start, stop - start) for start, stop in segments if stop > start] or [
            (location, length)
        ]

    def _document_font_size(self) -> Optional[float]:
        """Font size in points, read once from the start of the document.

        Font size is virtually always uniform within a control, so this is
        read once rather than per word.
        """
        attributed = TextRange(self, 0, 1).attributed_text
        if attributed is None or not hasattr(attributed, "attributesAtIndex_effectiveRange_"):
            return None
        try:
            attributes, _ = attributed.attributesAtIndex_effectiveRange_(0, None)
            font = attributes.get("AXFont")
            size = font.get("AXFontSize") if font else None
            return float(size) if size is not None else None
        except Exception:
            return None

    @staticmethod
    def _shrink_to_font_size(rect: Rect, font_size: float) -> Rect:
        """Trim a line-height rect down to the glyphs, anchored to the baseline.

        AXBoundsForRange reports the full line box, which is taller than the
        text: an 11pt font in TextEdit yields a 13pt-tall rect. The bottom
        edge tracks the baseline/descent closely and the extra leading sits
        above it, so shrink from the top. AX geometry is in points, the same
        unit as the font size, so no DPI conversion is needed.
        """
        if font_size <= 0 or font_size >= (rect.bottom - rect.top):
            return rect
        return Rect(
            left=rect.left,
            top=rect.bottom - font_size,
            right=rect.right,
            bottom=rect.bottom,
        )

    def WordBoundingBoxes(
        self, shrink_to_font: bool = True
    ) -> Optional[List[Tuple[str, List[Rect]]]]:
        """Return (word, bounding boxes) for every word in the control's text.

        The macOS counterpart to UIA's GetAllWordBoundingBoxes. macOS has no
        TextUnit.Word -- there is no ExpandToEnclosingUnit for plain text
        controls -- so words are tokenised here as whitespace-delimited runs
        and mapped back to character ranges. That keeps trailing punctuation
        attached ("dog." is one token), which is what you want for a clickable
        target rather than a linguistic word.

        Args:
            shrink_to_font: trim each rect from the line box down to the
                glyph height. Set False to keep the raw line-height rects.

        Returns:
            One entry per word, each with one Rect per line it occupies --
            normally a single Rect, two when a word wraps. None if the
            control does not expose its text at all.
        """
        full = self.FullTextRange
        if full is None:
            return None
        # Without AXBoundsForRange there is no geometry to report. Apps that
        # lack it still answer the call -- Chrome's omnibox returns a
        # degenerate Rect(0, 900, 0, 900) -- and handing back a zero-area box
        # whose centre is a real screen coordinate invites a misdirected
        # click. Report "unsupported" instead of fabricating a target.
        if Attribute.BoundsForRange not in GetParameterizedAttributeNames(self.Element):
            return None
        text = full.text
        if not text:
            return None

        lines = self._line_table(len(text))
        font_size = self._document_font_size() if shrink_to_font else None

        words: List[Tuple[str, List[Rect]]] = []
        for match in re.finditer(r"\S+", text):
            rects: List[Rect] = []
            for location, length in self._split_by_line(
                match.start(), match.end() - match.start(), lines
            ):
                rect = TextRange(self, location, length).bounds
                if rect is None:
                    continue
                # A collapsed rect is not a location, whatever the app says.
                if rect.right <= rect.left or rect.bottom <= rect.top:
                    continue
                if font_size is not None:
                    rect = self._shrink_to_font_size(rect, font_size)
                rects.append(rect)
            if rects:
                words.append((match.group(), rects))
        return words
