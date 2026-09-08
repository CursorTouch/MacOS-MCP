"""Tests for resolving running applications without an active run loop.

NSWorkspace only refreshes its application list from notifications delivered on
a run loop. This process never runs one, so anything reading that list has to
drain the queued sources first or it sees whatever was running at first read.
"""

import pytest
from unittest.mock import MagicMock

from macos_mcp.ax import core as ax_core
from macos_mcp.ax.controls import ApplicationControl


@pytest.mark.unit
class TestDrainRunLoop:
    def test_pumps_the_run_loop_without_blocking(self, mocker):
        """One non-blocking pass, which is all NSWorkspace needs to catch up."""
        run_in_mode = mocker.patch("macos_mcp.ax.core.CFRunLoopRunInMode")

        ax_core._DrainRunLoop()

        run_in_mode.assert_called_once()
        _mode, timeout, return_after_source = run_in_mode.call_args[0]
        assert timeout == 0  # must never block the caller
        assert return_after_source is True


@pytest.mark.unit
class TestGetRunningApplicationsRaw:
    def test_drains_before_reading_the_list(self, mocker):
        """The refresh has to happen before NSWorkspace is asked, not after."""
        calls = []
        mocker.patch(
            "macos_mcp.ax.core._DrainRunLoop",
            side_effect=lambda: calls.append("drain"),
        )
        workspace = MagicMock()
        workspace.runningApplications.side_effect = lambda: calls.append("read") or []
        nsworkspace = MagicMock()
        nsworkspace.sharedWorkspace.return_value = workspace
        mocker.patch("macos_mcp.ax.core.NSWorkspace", nsworkspace)

        ax_core.GetRunningApplicationsRaw()

        assert calls == ["drain", "read"]


@pytest.mark.unit
class TestApplicationControlBundleIdentifier:
    def test_resolves_from_pid_not_the_workspace_list(self, mocker):
        """A process missing from the stale list still resolves by PID."""
        mocker.patch("macos_mcp.ax.controls.GetElementPid", return_value=4321)
        running_app = MagicMock()
        running_app.bundleIdentifier.return_value = "com.example.launched"
        ns_running_application = MagicMock()
        ns_running_application.runningApplicationWithProcessIdentifier_.return_value = (
            running_app
        )
        mocker.patch("Cocoa.NSRunningApplication", ns_running_application)
        workspace = MagicMock()
        workspace.runningApplications.return_value = []  # stale: app not listed
        nsworkspace = MagicMock()
        nsworkspace.sharedWorkspace.return_value = workspace
        mocker.patch("macos_mcp.ax.core.NSWorkspace", nsworkspace)

        control = ApplicationControl(pid=4321)

        assert control.BundleIdentifier == "com.example.launched"
        ns_running_application.runningApplicationWithProcessIdentifier_.assert_called_once_with(
            4321
        )
        workspace.runningApplications.assert_not_called()


@pytest.mark.unit
class TestGetRunningApplicationByBundleId:
    """Several processes can share a bundle id -- Chrome runs a headless twin
    (--no-startup-window) next to the browser -- and the caller wants the one
    the user can see. The twin still has a menu bar, so picking it makes a
    scan return menus and nothing else."""

    def _running(self, pid, policy, bundle_id="com.google.Chrome"):
        app = MagicMock()
        app.processIdentifier.return_value = pid
        app.activationPolicy.return_value = policy
        app.bundleIdentifier.return_value = bundle_id
        return app

    def _on_screen(self, pid, layer=0):
        window = MagicMock()
        window.pid = pid
        window.is_application = layer == 0
        return window

    def _resolve(self, mocker, running, on_screen):
        mocker.patch("macos_mcp.ax.core.GetRunningApplicationsRaw", return_value=running)
        mocker.patch("macos_mcp.ax.core.GetOnScreenWindows", return_value=on_screen)
        control = mocker.patch("macos_mcp.ax.controls.ApplicationControl")
        ax_core.GetRunningApplicationByBundleId("com.google.Chrome")
        return control.call_args.kwargs["pid"]

    def test_prefers_the_process_with_windows_on_screen(self, mocker):
        headless, browser = self._running(90506, 0), self._running(1686, 0)
        assert self._resolve(mocker, [headless, browser], [self._on_screen(1686)]) == 1686

    def test_falls_back_to_activation_policy(self, mocker):
        prohibited, regular = self._running(90506, 2), self._running(1686, 0)
        assert self._resolve(mocker, [prohibited, regular], []) == 1686

    def test_single_match_skips_the_window_server(self, mocker):
        mocker.patch(
            "macos_mcp.ax.core.GetRunningApplicationsRaw",
            return_value=[self._running(1686, 0), self._running(7, 0, "com.other")],
        )
        on_screen = mocker.patch("macos_mcp.ax.core.GetOnScreenWindows")
        control = mocker.patch("macos_mcp.ax.controls.ApplicationControl")

        ax_core.GetRunningApplicationByBundleId("com.google.Chrome")

        assert control.call_args.kwargs["pid"] == 1686
        on_screen.assert_not_called()

    def test_none_when_absent(self, mocker):
        mocker.patch("macos_mcp.ax.core.GetRunningApplicationsRaw", return_value=[])
        assert ax_core.GetRunningApplicationByBundleId("com.google.Chrome") is None
