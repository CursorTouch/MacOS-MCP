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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional

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
