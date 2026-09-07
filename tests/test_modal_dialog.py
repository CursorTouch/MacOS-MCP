"""Tests for modal dialog detection on ApplicationControl / WindowControl.

A dialog blocks its application in one of two shapes:

    sheet   -- an AXSheet child of the main window (save panels, Chrome's
               upload picker). AXModal is False on the window behind it.
    modal   -- a standalone AXWindow with AXModal True and AXMain False
               (NSAlert run modally, Finder's `display dialog`, Docker
               Desktop's restart alert). It is never MainWindow.

Confirmed against a live Finder `display dialog` and Docker Desktop alert:

    MainWindow: desktop
      window: AXDialog  main=False  modal=True
      window: (desktop) main=True   modal=False
"""

from unittest.mock import MagicMock

import pytest

from macos_mcp.ax import controls
from macos_mcp.ax.controls import ApplicationControl, WindowControl
from macos_mcp.ax.enums import Attribute


def _element():
    return MagicMock()


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
class TestApplicationModalDialog:
    def _app(self, mocker, main_window, windows, modal_flags):
        """modal_flags maps a window element to (AXModal, AXMinimized)."""
        app = ApplicationControl.__new__(ApplicationControl)
        mocker.patch.object(
            ApplicationControl, "MainWindow", new_callable=mocker.PropertyMock,
            return_value=main_window,
        )
        mocker.patch.object(
            ApplicationControl, "Windows", new_callable=mocker.PropertyMock,
            return_value=windows,
        )
        mocker.patch.object(
            controls,
            "GetMultipleAttributeValues",
            side_effect=lambda el, attrs: dict(
                zip((Attribute.Modal, Attribute.Minimized), modal_flags[id(el)])
            ),
        )
        return app

    def test_sheet_on_main_window_wins(self, mocker):
        sheet = MagicMock()
        main_window = MagicMock()
        main_window.Sheet = sheet
        app = self._app(mocker, main_window, [], {})

        assert app.ModalDialog is sheet

    def test_standalone_modal_window(self, mocker):
        main_window = MagicMock()
        main_window.Sheet = None
        main_window.Element = _element()
        dialog = MagicMock()
        dialog.Element = _element()
        app = self._app(
            mocker,
            main_window,
            [main_window, dialog],
            {id(main_window.Element): (False, False), id(dialog.Element): (True, False)},
        )

        assert app.ModalDialog is dialog

    def test_modal_window_without_main_window(self, mocker):
        """Docker Desktop: an accessory app whose only window is the alert."""
        dialog = MagicMock()
        dialog.Element = _element()
        app = self._app(mocker, None, [dialog], {id(dialog.Element): (True, False)})

        assert app.ModalDialog is dialog

    def test_minimized_modal_window_is_ignored(self, mocker):
        main_window = MagicMock()
        main_window.Sheet = None
        main_window.Element = _element()
        dialog = MagicMock()
        dialog.Element = _element()
        app = self._app(
            mocker,
            main_window,
            [main_window, dialog],
            {id(main_window.Element): (False, False), id(dialog.Element): (True, True)},
        )

        assert app.ModalDialog is None

    def test_none_when_nothing_blocks(self, mocker):
        main_window = MagicMock()
        main_window.Sheet = None
        main_window.Element = _element()
        app = self._app(
            mocker, main_window, [main_window], {id(main_window.Element): (False, False)}
        )

        assert app.ModalDialog is None
