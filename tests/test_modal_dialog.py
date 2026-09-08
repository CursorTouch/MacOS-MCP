"""Tests for dialog detection on ApplicationControl / WindowControl.

A dialog blocks its application in one of two shapes:

    sheet   -- an AXSheet child of a window (save panels, Chrome's upload
               picker). AXModal is False on the window behind it.
    modal   -- a standalone AXWindow with AXModal True and AXMain False
               (NSAlert run modally, Finder's `display dialog`, Docker
               Desktop's restart alert). It is never MainWindow.

Accessibility reports both the same whether the dialog floats over every
application or is buried behind them; only the window server's layer tells.
Confirmed live against three alerts open at once:

    Docker Desktop (accessory)  layer 8 whichever app is active  -> floating
    Finder "Empty Bin"          layer 8 while Finder is active, else 0
    Chrome "Leave site?"        layer 8 while Chrome is active, else 0
"""

from unittest.mock import MagicMock

import pytest

from macos_mcp.ax import controls
from macos_mcp.ax.controls import ApplicationControl, DialogInfo, WindowControl
from macos_mcp.ax.core import OnScreenWindow, Rect
from macos_mcp.ax.enums import Attribute, WindowLevel


def _element():
    return MagicMock()


def _rect(left, top, width, height):
    return Rect(left=left, top=top, right=left + width, bottom=top + height)


def _on_screen(pid, layer, z_index, bounds, name=""):
    return OnScreenWindow(
        window_id=z_index,
        pid=pid,
        owner_name=name,
        title="",
        layer=layer,
        z_index=z_index,
        bounds=bounds,
    )


def _window(bounds, modal=False, sheet=None):
    window = MagicMock(spec=WindowControl)
    window.BoundingRectangle = bounds
    window.IsModal = modal
    window.Sheet = sheet
    return window


@pytest.mark.unit
class TestWindowSheet:
    def test_returns_the_sheet_child(self, mocker):
        toolbar, sheet = _element(), _element()
        roles = {id(toolbar): "AXToolbar", id(sheet): "AXSheet"}
        mocker.patch.object(
            controls, "GetAttribute", side_effect=lambda el, attr: roles.get(id(el))
        )
        window = WindowControl(element=_element())
        mocker.patch.object(
            WindowControl,
            "GetChildren",
            return_value=[controls.Control(element=toolbar), controls.Control(element=sheet)],
        )

        assert window.Sheet.Element is sheet

    def test_none_without_sheet(self, mocker):
        toolbar = _element()
        mocker.patch.object(controls, "GetAttribute", return_value="AXToolbar")
        window = WindowControl(element=_element())
        mocker.patch.object(
            WindowControl, "GetChildren", return_value=[controls.Control(element=toolbar)]
        )

        assert window.Sheet is None


@pytest.mark.unit
class TestWindowModal:
    def test_is_modal_reads_axmodal(self, mocker):
        mocker.patch.object(controls, "GetAttribute", return_value=True)
        assert WindowControl(element=_element()).IsModal is True

    def test_is_modal_false_when_unsupported(self, mocker):
        mocker.patch.object(controls, "GetAttribute", return_value=None)
        assert WindowControl(element=_element()).IsModal is False


ALERT = _rect(802, 310, 260, 285)
MAIN = _rect(255, 36, 1031, 808)
OTHER = _rect(0, 30, 1120, 808)


@pytest.mark.unit
class TestApplicationDialog:
    def _app(self, mocker, pid, windows):
        app = ApplicationControl.__new__(ApplicationControl)
        mocker.patch.object(
            ApplicationControl, "PID", new_callable=mocker.PropertyMock, return_value=pid
        )
        mocker.patch.object(
            ApplicationControl,
            "Windows",
            new_callable=mocker.PropertyMock,
            return_value=windows,
        )
        return app

    def test_floating_alert_of_background_app(self, mocker):
        """Docker Desktop: modal-panel level while another app is active."""
        alert = _window(ALERT, modal=True)
        app = self._app(mocker, 10, [alert])
        screen = [
            _on_screen(10, WindowLevel.ModalPanel, 0, ALERT),
            _on_screen(20, WindowLevel.Normal, 1, OTHER),
        ]

        dialog = app._dialog(screen)

        assert dialog.window is alert
        assert dialog.floating is True
        assert dialog.frontmost is False
        assert dialog.reachable is True

    def test_buried_alert_of_background_app(self, mocker):
        """Finder "Empty Bin" after switching away: normal level, behind."""
        alert = _window(ALERT, modal=True)
        app = self._app(mocker, 10, [alert])
        screen = [
            _on_screen(20, WindowLevel.Normal, 0, OTHER),
            _on_screen(10, WindowLevel.Normal, 1, ALERT),
        ]

        dialog = app._dialog(screen)

        assert dialog.window is alert
        assert dialog.floating is False
        assert dialog.frontmost is False
        assert dialog.reachable is False

    def test_alert_of_frontmost_app(self, mocker):
        alert = _window(ALERT, modal=True)
        main = _window(MAIN)
        app = self._app(mocker, 10, [alert, main])
        screen = [
            _on_screen(10, WindowLevel.ModalPanel, 0, ALERT),
            _on_screen(10, WindowLevel.Normal, 1, MAIN),
            _on_screen(20, WindowLevel.Normal, 2, OTHER),
        ]

        dialog = app._dialog(screen)

        assert dialog.window is alert
        assert dialog.frontmost is True
        assert dialog.reachable is True

    def test_sheet_on_a_window(self, mocker):
        """Chrome's upload picker: AXModal stays False on the browser window."""
        sheet = MagicMock()
        main = _window(MAIN, sheet=sheet)
        app = self._app(mocker, 10, [main])
        screen = [_on_screen(10, WindowLevel.Normal, 0, MAIN)]

        dialog = app._dialog(screen)

        assert dialog.window is sheet
        assert dialog.floating is False
        assert dialog.frontmost is True

    def test_frame_match_tolerates_a_point(self, mocker):
        alert = _window(_rect(802.5, 310, 260, 285), modal=True)
        app = self._app(mocker, 10, [alert])
        screen = [_on_screen(10, WindowLevel.ModalPanel, 0, ALERT)]

        assert app._dialog(screen).window is alert

    def test_non_modal_window_is_not_a_dialog(self, mocker):
        """Chrome's browser window reports subrole AXDialog with AXModal False."""
        main = _window(MAIN)
        app = self._app(mocker, 10, [main])
        screen = [_on_screen(10, WindowLevel.Normal, 0, MAIN)]

        assert app._dialog(screen) is None

    def test_unmatched_on_screen_window_is_skipped(self, mocker):
        """A tooltip or popup has no AXWindow; the alert behind it is still found."""
        alert = _window(ALERT, modal=True)
        app = self._app(mocker, 10, [alert])
        screen = [
            _on_screen(10, WindowLevel.Normal, 0, _rect(1, 1, 50, 20)),
            _on_screen(10, WindowLevel.Normal, 1, ALERT),
        ]

        assert app._dialog(screen).window is alert

    def test_none_without_on_screen_windows(self, mocker):
        app = self._app(mocker, 10, [_window(ALERT, modal=True)])
        mocker.patch.object(ApplicationControl, "Windows", new_callable=mocker.PropertyMock)

        assert app._dialog([_on_screen(20, WindowLevel.Normal, 0, OTHER)]) is None
        ApplicationControl.Windows.assert_not_called()

    def test_dialog_property_reads_the_window_server(self, mocker):
        alert = _window(ALERT, modal=True)
        app = self._app(mocker, 10, [alert])
        mocker.patch.object(
            controls,
            "GetOnScreenWindows",
            return_value=[_on_screen(10, WindowLevel.ModalPanel, 0, ALERT)],
        )

        assert app.Dialog.window is alert


@pytest.mark.unit
class TestDialogInfo:
    def _info(self, window, floating=False, frontmost=False):
        return DialogInfo(MagicMock(), window, floating=floating, frontmost=frontmost)

    def test_title_prefers_axtitle(self):
        window = MagicMock()
        window.Title = "Save"
        assert self._info(window).title == "Save"

    def test_title_falls_back_to_heading(self, mocker):
        """Alert panels report no AXTitle; their first line of text is the heading."""
        window = MagicMock()
        window.Title = ""
        icon, heading = MagicMock(), MagicMock()
        window.GetChildren.return_value = [icon, heading]
        values = {
            id(icon.Element): {Attribute.Role: "AXImage"},
            id(heading.Element): {
                Attribute.Role: "AXStaticText",
                Attribute.Value: "Restart Docker Desktop",
            },
        }
        mocker.patch.object(
            controls, "GetMultipleAttributeValues", side_effect=lambda el, a: values[id(el)]
        )

        assert self._info(window).title == "Restart Docker Desktop"

    def test_title_placeholder_without_text(self, mocker):
        window = MagicMock()
        window.Title = ""
        window.GetChildren.return_value = []
        assert self._info(window).title == "Dialog"

    @pytest.mark.parametrize(
        "floating, frontmost, reachable",
        [(True, False, True), (False, True, True), (True, True, True), (False, False, False)],
    )
    def test_reachable(self, floating, frontmost, reachable):
        assert self._info(MagicMock(), floating, frontmost).reachable is reachable


@pytest.mark.unit
class TestGetDialogs:
    def test_probes_each_application_once_front_to_back(self, mocker):
        """Only owners of application-level windows are asked, and each once."""
        screen = [
            _on_screen(10, WindowLevel.ModalPanel, 0, ALERT),
            _on_screen(20, WindowLevel.Normal, 1, MAIN),
            _on_screen(20, WindowLevel.Normal, 2, OTHER),
            _on_screen(30, WindowLevel.Dock, 3, OTHER),
            _on_screen(40, WindowLevel.Normal - 100, 4, OTHER),
        ]
        mocker.patch.object(controls, "GetOnScreenWindows", return_value=screen)
        mocker.patch.object(controls, "SetMessagingTimeout")
        found = {10: MagicMock(spec=DialogInfo), 20: None}
        probed = []

        def _app(pid):
            app = MagicMock()
            app._dialog.side_effect = lambda seen: probed.append((pid, seen)) or found[pid]
            return app

        mocker.patch.object(controls, "ApplicationControl", side_effect=_app)

        dialogs = controls.GetDialogs()

        assert probed == [(10, screen), (20, screen)]
        assert dialogs == [found[10]]
