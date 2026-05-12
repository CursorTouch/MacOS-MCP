"""Tests for desktop/config.py module."""

import pytest
from macos_mcp.desktop.config import (
    BROWSER_BUNDLE_IDS,
    EXCLUDED_BUNDLE_IDS,
    SYSTEM_UI_BUNDLE_IDS,
)


@pytest.mark.unit
class TestBrowserBundleIds:
    """Tests for BROWSER_BUNDLE_IDS constant."""

    def test_common_browsers_included(self):
        """Test that common browsers are included."""
        assert "com.apple.Safari" in BROWSER_BUNDLE_IDS
        assert "com.google.Chrome" in BROWSER_BUNDLE_IDS
        assert "org.mozilla.firefox" in BROWSER_BUNDLE_IDS
        assert "com.microsoft.edgemac" in BROWSER_BUNDLE_IDS

    def test_other_browsers_included(self):
        """Test that other browsers are included."""
        assert "com.brave.Browser" in BROWSER_BUNDLE_IDS
        assert "com.operasoftware.Opera" in BROWSER_BUNDLE_IDS
        assert "com.vivaldi.Vivaldi" in BROWSER_BUNDLE_IDS
        assert "company.thebrowser.Browser" in BROWSER_BUNDLE_IDS  # Arc

    def test_is_set(self):
        """Test that BROWSER_BUNDLE_IDS is a set."""
        assert isinstance(BROWSER_BUNDLE_IDS, set)

    def test_not_empty(self):
        """Test that BROWSER_BUNDLE_IDS is not empty."""
        assert len(BROWSER_BUNDLE_IDS) > 0


@pytest.mark.unit
class TestExcludedBundleIds:
    """Tests for EXCLUDED_BUNDLE_IDS constant."""

    def test_finder_excluded(self):
        """Test that Finder is in excluded list."""
        assert "com.apple.finder" in EXCLUDED_BUNDLE_IDS

    def test_is_set(self):
        """Test that EXCLUDED_BUNDLE_IDS is a set."""
        assert isinstance(EXCLUDED_BUNDLE_IDS, set)

    def test_not_empty(self):
        """Test that EXCLUDED_BUNDLE_IDS is not empty."""
        assert len(EXCLUDED_BUNDLE_IDS) > 0


@pytest.mark.unit
class TestSystemUiBundleIds:
    """Tests for SYSTEM_UI_BUNDLE_IDS constant."""

    def test_dock_included(self):
        """Test that Dock is included."""
        assert "com.apple.dock" in SYSTEM_UI_BUNDLE_IDS

    def test_control_center_included(self):
        """Test that Control Center is included."""
        assert "com.apple.controlcenter" in SYSTEM_UI_BUNDLE_IDS

    def test_menu_bar_included(self):
        """Test that Menu bar extras are included."""
        assert "com.apple.systemuiserver" in SYSTEM_UI_BUNDLE_IDS

    def test_spotlight_included(self):
        """Test that Spotlight is included."""
        assert "com.apple.Spotlight" in SYSTEM_UI_BUNDLE_IDS

    def test_is_set(self):
        """Test that SYSTEM_UI_BUNDLE_IDS is a set."""
        assert isinstance(SYSTEM_UI_BUNDLE_IDS, set)

    def test_not_empty(self):
        """Test that SYSTEM_UI_BUNDLE_IDS is not empty."""
        assert len(SYSTEM_UI_BUNDLE_IDS) > 0

    def test_no_duplicates(self):
        """Test that there are no duplicates in system UI bundle IDs."""
        # Since it's a set, no duplicates are possible, but verify length
        bundle_list = list(SYSTEM_UI_BUNDLE_IDS)
        assert len(bundle_list) == len(set(bundle_list))


@pytest.mark.unit
class TestBundleIdIsolation:
    """Tests for isolation between bundle ID sets."""

    def test_no_overlap_browsers_and_excluded(self):
        """Test that browser and excluded IDs don't overlap."""
        overlap = BROWSER_BUNDLE_IDS & EXCLUDED_BUNDLE_IDS
        assert len(overlap) == 0

    def test_no_overlap_system_ui_and_excluded(self):
        """Test that system UI and excluded IDs don't overlap."""
        overlap = SYSTEM_UI_BUNDLE_IDS & EXCLUDED_BUNDLE_IDS
        assert len(overlap) == 0
