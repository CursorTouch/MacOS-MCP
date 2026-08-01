"""Regression tests for parameterized attribute name spellings.

Apple's headers name these constants with a "Parameterized" suffix --
kAXStringForRangeParameterizedAttribute -- but the string that constant
expands to does not carry it: CFSTR("AXStringForRange"). enums.py used the
constant names as the values, so every parameterized call returned
kAXErrorParameterizedAttributeUnsupported (-25213).

Verified against live applications: neither TextEdit's AXTextArea (11
parameterized attributes advertised) nor Chrome's AXWebArea (44) exposes a
single name ending in "Parameterized".

The user-visible effect was that Control.GetTextFromMarkers -- the only
caller of any of these -- always returned "". Against the same live
AXWebArea it returns 0 characters with the old spellings and 23,114 with
the corrected ones.
"""

import pytest

from macos_mcp.ax.enums import Attribute

# Every parameterized attribute declared on Attribute. Kept as an explicit
# list so that adding one without checking its spelling fails here.
PARAMETERIZED_ATTRIBUTES = [
    Attribute.LineForIndex,
    Attribute.RangeForLine,
    Attribute.StringForRange,
    Attribute.RangeForPosition,
    Attribute.RangeForIndex,
    Attribute.BoundsForRange,
    Attribute.AttributedStringForRange,
    Attribute.RTFForRange,
    Attribute.StyleRangeForIndex,
    Attribute.StringForTextMarkerRange,
    Attribute.AttributedStringForTextMarkerRange,
    Attribute.BoundsForTextMarkerRange,
    Attribute.TextMarkerRangeForUnorderedTextMarkers,
]


@pytest.mark.unit
class TestParameterizedAttributeSpellings:
    """The suffix belongs to the constant name, never to its value."""

    def test_no_value_carries_the_parameterized_suffix(self):
        offenders = [a for a in PARAMETERIZED_ATTRIBUTES if a.endswith("Parameterized")]
        assert offenders == [], (
            "these values would fail with kAXErrorParameterizedAttributeUnsupported "
            f"(-25213) against every application: {offenders}"
        )

    def test_all_values_keep_the_ax_prefix(self):
        assert all(a.startswith("AX") for a in PARAMETERIZED_ATTRIBUTES)

    def test_no_duplicate_values(self):
        assert len(set(PARAMETERIZED_ATTRIBUTES)) == len(PARAMETERIZED_ATTRIBUTES)

    @pytest.mark.parametrize(
        "attribute,expected",
        [
            (Attribute.LineForIndex, "AXLineForIndex"),
            (Attribute.RangeForLine, "AXRangeForLine"),
            (Attribute.StringForRange, "AXStringForRange"),
            (Attribute.RangeForPosition, "AXRangeForPosition"),
            (Attribute.RangeForIndex, "AXRangeForIndex"),
            (Attribute.BoundsForRange, "AXBoundsForRange"),
            (Attribute.AttributedStringForRange, "AXAttributedStringForRange"),
            (Attribute.RTFForRange, "AXRTFForRange"),
            (Attribute.StyleRangeForIndex, "AXStyleRangeForIndex"),
            (Attribute.StringForTextMarkerRange, "AXStringForTextMarkerRange"),
            (
                Attribute.AttributedStringForTextMarkerRange,
                "AXAttributedStringForTextMarkerRange",
            ),
            (Attribute.BoundsForTextMarkerRange, "AXBoundsForTextMarkerRange"),
            (
                Attribute.TextMarkerRangeForUnorderedTextMarkers,
                "AXTextMarkerRangeForUnorderedTextMarkers",
            ),
        ],
    )
    def test_exact_spelling(self, attribute, expected):
        """Pin each value against the string in Apple's/WebKit's headers."""
        assert attribute == expected


@pytest.mark.unit
class TestTextMarkerAttributesUnchanged:
    """The non-parameterized marker attributes were already correct."""

    @pytest.mark.parametrize(
        "attribute,expected",
        [
            (Attribute.StartTextMarker, "AXStartTextMarker"),
            (Attribute.EndTextMarker, "AXEndTextMarker"),
            (Attribute.SelectedTextMarkerRange, "AXSelectedTextMarkerRange"),
        ],
    )
    def test_plain_marker_attributes(self, attribute, expected):
        assert attribute == expected
