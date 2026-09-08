from macos_mcp.tree.views import BoundingBox
from macos_mcp.tree.views import TreeState
from dataclasses import dataclass
from PIL.Image import Image
from typing import Union
from enum import Enum


class Status(Enum):
    ACTIVE = "Active"  # Frontmost app with visible windows
    FULLSCREEN = "Fullscreen"  # Frontmost app in fullscreen mode
    VISIBLE = "Visible"  # Has windows on screen, not frontmost
    HIDDEN = "Hidden"  # Hidden via Cmd+H
    MINIMIZED = "Minimized"  # All windows minimized to Dock
    WINDOWLESS = "Windowless"  # Running but no windows


@dataclass
class Size:
    width: int
    height: int

    def to_string(self):
        return f"({self.width},{self.height})"


@dataclass
class Dialog:
    """The sheet or modal dialog currently blocking an application."""

    title: str
    # False when the dialog sits behind other applications' windows: an
    # ordinary alert drops to the normal window level as soon as its app is
    # no longer active. The app must be switched to before the dialog's
    # controls can be used.
    reachable: bool

    def to_string(self) -> str:
        line = f'dialog: "{self.title}"'
        if not self.reachable:
            line += " (behind other windows; switch to the app to reach it)"
        return line


@dataclass
class Window:
    name: str
    is_browser: bool
    status: Status
    bounding_box: BoundingBox
    pid: int
    bundle_id: str
    dialog: Dialog | None = None

    def to_string(self) -> str:
        line = f"{self.name} ({self.bundle_id}) - {self.status.value}"
        if self.dialog:
            line += f" - {self.dialog.to_string()}"
        return line


@dataclass
class DesktopState:
    active_window: Window | None
    windows: list[Window]
    screenshot: Union[Image, bytes, None] = None
    tree_state: TreeState | None = None

    def windows_to_string(self) -> str:
        """Format windows list for display."""
        if not self.windows:
            return "No open applications."
        return "\n".join(w.to_string() for w in self.windows)

    def active_window_to_string(self) -> str:
        """Format active window for display."""
        if self.active_window is None:
            return "No focused window."
        return self.active_window.to_string()
