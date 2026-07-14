"""Tests for Mission Control / Spaces helpers in ax.core."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from macos_mcp.ax import core as ax_core


@pytest.mark.unit
class TestAddDesktopMatchers:
    def test_is_add_desktop_control_by_description(self):
        ctrl = SimpleNamespace(
            Description="add desktop",
            Title="",
            Help="",
            Identifier="",
            RoleDescription="",
        )
        assert ax_core._is_add_desktop_control(ctrl) is True

    def test_is_add_desktop_control_by_title_variant(self):
        ctrl = SimpleNamespace(
            Description="",
            Title="New Desktop",
            Help="",
            Identifier="",
            RoleDescription="",
        )
        assert ax_core._is_add_desktop_control(ctrl) is True

    def test_is_add_desktop_control_rejects_unrelated(self):
        ctrl = SimpleNamespace(
            Description="Finder",
            Title="Finder",
            Help="",
            Identifier="com.apple.finder",
            RoleDescription="application",
        )
        assert ax_core._is_add_desktop_control(ctrl) is False


@pytest.mark.unit
class TestCreateDesktopSpace:
    def test_ax_path_success(self, mocker):
        button = MagicMock()
        button.Press.return_value = True
        mocker.patch.object(ax_core, "OpenMissionControl")
        mocker.patch.object(ax_core, "FindAddDesktopButton", return_value=button)
        mocker.patch.object(ax_core, "CloseMissionControl")
        mocker.patch.object(ax_core, "time")
        # Simulate the space count increasing after activation.
        mocker.patch.object(ax_core, "_count_desktop_spaces", side_effect=[1, 2])

        ok, message = ax_core.CreateDesktopSpace(
            open_delay=0.1,
            close_after=True,
        )

        assert ok is True
        assert message == "Created new desktop space (2 total)."
        button.Press.assert_called_once()
        ax_core.OpenMissionControl.assert_called_once()
        ax_core.CloseMissionControl.assert_called()

    def test_ax_path_does_not_close_when_requested(self, mocker):
        button = MagicMock()
        button.Press.return_value = True
        mocker.patch.object(ax_core, "OpenMissionControl")
        mocker.patch.object(ax_core, "FindAddDesktopButton", return_value=button)
        mock_close = mocker.patch.object(ax_core, "CloseMissionControl")
        mocker.patch.object(ax_core, "time")
        mocker.patch.object(ax_core, "_count_desktop_spaces", side_effect=[1, 2])

        ok, _ = ax_core.CreateDesktopSpace(
            open_delay=0.1,
            close_after=False,
        )

        assert ok is True
        mock_close.assert_not_called()

    def test_ax_path_reports_failure_when_count_does_not_increase(self, mocker):
        button = MagicMock()
        button.Press.return_value = True
        mocker.patch.object(ax_core, "OpenMissionControl")
        mocker.patch.object(ax_core, "FindAddDesktopButton", return_value=button)
        mocker.patch.object(ax_core, "CloseMissionControl")
        mocker.patch.object(ax_core, "time")
        # Space count unchanged after activation -> creation could not be verified.
        mocker.patch.object(ax_core, "_count_desktop_spaces", side_effect=[2, 2])

        ok, message = ax_core.CreateDesktopSpace(
            open_delay=0.1,
            close_after=True,
        )

        assert ok is False
        assert "did not increase" in message

    def test_returns_error_when_button_missing(self, mocker):
        mocker.patch.object(ax_core, "OpenMissionControl")
        mocker.patch.object(ax_core, "FindAddDesktopButton", return_value=None)
        mocker.patch.object(ax_core, "CloseMissionControl")
        mocker.patch.object(ax_core, "time")

        ok, message = ax_core.CreateDesktopSpace(
            open_delay=0.1,
            close_after=True,
        )

        assert ok is False
        assert "Add Desktop" in message or "Accessibility" in message

    def test_activate_uses_click_when_press_fails(self, mocker):
        button = MagicMock()
        button.Press.return_value = False
        button.Click = MagicMock()
        assert ax_core._activate_add_desktop_button(button) is True
        button.Click.assert_called_once()
