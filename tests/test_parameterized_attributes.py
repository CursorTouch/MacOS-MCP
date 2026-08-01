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

from macos_mcp.ax.enums import Attribute, TextAttribute

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


# Attributed-string keys carry the same trap as the parameterized attributes:
# Apple's constant is kAXFontTextAttribute, but the string it expands to is
# CFSTR("AXFont"). The "Text" belongs to the constant name, not the value.
TEXT_ATTRIBUTES = [
    TextAttribute.Font,
    TextAttribute.ForegroundColor,
    TextAttribute.BackgroundColor,
    TextAttribute.UnderlineColor,
    TextAttribute.StrikethroughColor,
    TextAttribute.Underline,
    TextAttribute.Strikethrough,
    TextAttribute.Shadow,
    TextAttribute.Superscript,
    TextAttribute.TextAlignment,
    TextAttribute.Attachment,
    TextAttribute.Link,
    TextAttribute.NaturalLanguage,
    TextAttribute.ReplacementString,
    TextAttribute.Misspelled,
    TextAttribute.MarkedMisspelled,
    TextAttribute.Autocorrected,
]

# Sub-keys of the nested AXFont dictionary rather than top-level attribute
# keys. These were always correct and must not be "fixed" alongside the rest.
FONT_SUBKEYS = [
    TextAttribute.FontFamily,
    TextAttribute.FontName,
    TextAttribute.FontSize,
    TextAttribute.VisibleName,
]


@pytest.mark.unit
class TestTextAttributeSpellings:
    """The 'Text' suffix belongs to the constant name, never to its value.

    Directly observed on a live AXTextArea containing styled text: AXFont,
    AXForegroundColor, AXBackgroundColor, AXUnderline, AXStrikethrough,
    AXSuperscript, AXLink, AXMisspelled, AXMarkedMisspelled and
    AXATextAlignmentValue. Not one carried the suffix.
    """

    def test_no_value_carries_the_text_suffix(self):
        offenders = [a for a in TEXT_ATTRIBUTES if a.endswith("Text")]
        assert offenders == [], (
            "these keys never appear in an AXAttributedStringForRange result, "
            f"so lookups against them always miss: {offenders}"
        )

    def test_all_values_keep_the_ax_prefix(self):
        assert all(a.startswith("AX") for a in TEXT_ATTRIBUTES + FONT_SUBKEYS)

    def test_no_duplicate_values(self):
        everything = TEXT_ATTRIBUTES + FONT_SUBKEYS
        assert len(set(everything)) == len(everything)

    @pytest.mark.parametrize(
        "attribute,expected",
        [
            # Observed directly against a live AXTextArea.
            (TextAttribute.Font, "AXFont"),
            (TextAttribute.ForegroundColor, "AXForegroundColor"),
            (TextAttribute.BackgroundColor, "AXBackgroundColor"),
            (TextAttribute.Underline, "AXUnderline"),
            (TextAttribute.Strikethrough, "AXStrikethrough"),
            (TextAttribute.Superscript, "AXSuperscript"),
            (TextAttribute.Link, "AXLink"),
            (TextAttribute.Misspelled, "AXMisspelled"),
            (TextAttribute.MarkedMisspelled, "AXMarkedMisspelled"),
            (TextAttribute.TextAlignment, "AXATextAlignmentValue"),
            # Same header pattern; not exercised by the sample document.
            (TextAttribute.UnderlineColor, "AXUnderlineColor"),
            (TextAttribute.StrikethroughColor, "AXStrikethroughColor"),
            (TextAttribute.Shadow, "AXShadow"),
            (TextAttribute.Attachment, "AXAttachment"),
            (TextAttribute.NaturalLanguage, "AXNaturalLanguage"),
            (TextAttribute.ReplacementString, "AXReplacementString"),
            (TextAttribute.Autocorrected, "AXAutocorrected"),
        ],
    )
    def test_exact_spelling(self, attribute, expected):
        assert attribute == expected

    @pytest.mark.parametrize(
        "attribute,expected",
        [
            (TextAttribute.FontFamily, "AXFontFamily"),
            (TextAttribute.FontName, "AXFontName"),
            (TextAttribute.FontSize, "AXFontSize"),
            (TextAttribute.VisibleName, "AXVisibleName"),
        ],
    )
    def test_font_subkeys_are_unchanged(self, attribute, expected):
        """These index into the nested AXFont dict and were already correct."""
        assert attribute == expected
