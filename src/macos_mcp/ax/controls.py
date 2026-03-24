"""
Control classes wrapping macOS AXUIElementRef.
Provides a Pythonic, object-oriented interface to accessibility elements
with typed subclasses for specific control types.

Equivalent to the Windows UIA controls.py module, adapted for macOS.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, List, Optional, Union

from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
    AXUIElementCopyAttributeValue,
    AXUIElementSetAttributeValue,
    AXUIElementPerformAction,
    AXUIElementCopyAttributeNames,
    AXUIElementCopyActionNames,
    AXUIElementIsAttributeSettable,
    AXUIElementGetAttributeValueCount,
    kAXErrorSuccess,
)

from .enums import (
    Role,
    Subrole,
    Attribute,
    Action,
    AXError,
    ActivationPolicyNames,
)

from .core import (
    Rect,
    Point,
    Size,
    GetAttribute,
    SetAttribute,
    GetAttributeNames,
    GetActionNames,
    PerformAction,
    GetChildren as _GetChildren,
    GetPosition,
    GetSize,
    GetRect,
    GetChildCount,
    IsAttributeSettable,
    GetElementPid,
    GetScreenSize,
    GetForegroundWindowPID,
    ActivateApplication,
    Click as _Click,
    RightClick as _RightClick,
    DoubleClick as _DoubleClick,
    MiddleClick as _MiddleClick,
    TypeText as _TypeText,
    WheelDown as _WheelDown,
    WheelUp as _WheelUp,
    DragTo as _DragTo,
    MoveTo as _MoveTo,
)

logger = logging.getLogger(__name__)


class Control:
    """
    Base Control class wrapping a macOS AXUIElementRef.
    Equivalent to Windows UIA Control class.

    Provides property-based access to accessibility attributes,
    child navigation, element search, action execution,
    mouse/keyboard interaction, and fluent chaining for child discovery.

    Supports lazy element resolution: construct with search parameters
    and the actual AX element is found on first property access.

    Usage:
        # Direct wrapping
        ctrl = Control(element=some_ax_ref)

        # From PID
        app = Control(pid=12345)

        # Deferred search (lazy)
        btn = Control(searchFromControl=window, role=Role.Button, title="Save")
        btn.Click()  # element is found here
    """

    def __init__(
        self,
        element=None,
        pid: Optional[int] = None,
        searchFromControl: Optional[Control] = None,
        role: Optional[str] = None,
        title: Optional[str] = None,
        subrole: Optional[str] = None,
        identifier: Optional[str] = None,
        predicate: Optional[Callable[[Control], bool]] = None,
        searchDepth: int = 25,
        searchInterval: float = 0.5,
        foundIndex: int = 1,
    ):
        """
        Create a Control from an AXUIElement, application PID, or search parameters.

        Args:
            element: An AXUIElementRef to wrap directly.
            pid: Process ID to create an application element from.
            searchFromControl: Parent Control to search from (enables lazy resolution).
            role: AXRole to match when searching.
            title: AXTitle substring to match when searching.
            subrole: AXSubrole to match when searching.
            identifier: AXIdentifier to match when searching.
            predicate: Custom filter function for searching.
            searchDepth: Maximum tree depth for search.
            searchInterval: Seconds between search retries.
            foundIndex: 1-based index for multiple matches (1 = first match).
        """
        if element is not None:
            self._element = element
            self._element_direct_assign = True
        elif pid is not None:
            self._element = AXUIElementCreateApplication(pid)
            self._element_direct_assign = True
        elif searchFromControl is None and role is None and title is None:
            self._element = AXUIElementCreateSystemWide()
            self._element_direct_assign = True
        else:
            self._element = None
            self._element_direct_assign = False

        # Store search parameters for lazy resolution
        self._searchFromControl = searchFromControl
        self._searchRole = role
        self._searchTitle = title
        self._searchSubrole = subrole
        self._searchIdentifier = identifier
        self._searchPredicate = predicate
        self._searchDepth = searchDepth
        self._searchInterval = searchInterval
        self._foundIndex = foundIndex

    @property
    def Element(self):
        """
        Get the underlying AXUIElementRef.
        Triggers lazy search if element was not directly assigned.
        """
        if self._element is None:
            self.Refind()
        return self._element

    # =========================================================================
    # Lazy Search: Exists / Refind
    # =========================================================================

    def Exists(self, maxSearchSeconds: float = 5.0, searchIntervalSeconds: float = 0.5) -> bool:
        """
        Check if this control exists by searching for it.
        Retries up to maxSearchSeconds.

        Args:
            maxSearchSeconds: Maximum time to search.
            searchIntervalSeconds: Time between retries.

        Returns:
            True if the control was found.
        """
        if self._element is not None and self._element_direct_assign:
            return True

        if self._searchFromControl is None:
            return self._element is not None

        # Ensure parent exists first
        if self._searchFromControl._element is None:
            if not self._searchFromControl.Exists(maxSearchSeconds, searchIntervalSeconds):
                return False

        start_time = time.monotonic()
        while True:
            found = self._search_for_element()
            if found is not None:
                self._element = found
                return True
            remaining = start_time + maxSearchSeconds - time.monotonic()
            if remaining > 0:
                time.sleep(min(remaining, searchIntervalSeconds))
            else:
                return False

    def Refind(self, maxSearchSeconds: float = 5.0, raiseException: bool = True) -> bool:
        """
        Re-find this control, clearing any cached element.

        Args:
            maxSearchSeconds: Maximum time to search.
            raiseException: If True, raise LookupError on timeout.

        Returns:
            True if found.
        """
        self._element = None
        if not self.Exists(maxSearchSeconds, self._searchInterval):
            if raiseException:
                desc = self._get_search_description()
                raise LookupError(f'Find Control Timeout({maxSearchSeconds}s): {desc}')
            return False
        return True

    def _search_for_element(self):
        """Perform a single search attempt using stored search parameters."""
        parent = self._searchFromControl
        if parent is None:
            return None

        parent_element = parent.Element
        if parent_element is None:
            return None

        results = []
        _find_recursive_raw(
            parent_element, results,
            self._searchRole, self._searchSubrole,
            self._searchTitle, self._searchIdentifier,
            self._searchPredicate, self._searchDepth, 0,
            find_first=(self._foundIndex <= 1),
        )

        idx = self._foundIndex - 1  # convert to 0-based
        if idx < len(results):
            return results[idx]
        return None

    def _get_search_description(self) -> str:
        """Get a human-readable description of the search parameters."""
        parts = []
        if self._searchRole:
            parts.append(f'Role={self._searchRole!r}')
        if self._searchTitle:
            parts.append(f'Title={self._searchTitle!r}')
        if self._searchSubrole:
            parts.append(f'Subrole={self._searchSubrole!r}')
        if self._searchIdentifier:
            parts.append(f'Identifier={self._searchIdentifier!r}')
        if self._searchPredicate:
            parts.append('Predicate=<custom>')
        return '{' + ', '.join(parts) + '}' if parts else '{}'

    @staticmethod
    def _wrap(element) -> Control:
        """Wrap a raw AXUIElementRef in the appropriate typed Control subclass."""
        return CreateControl(element)

    # =========================================================================
    # Standard Properties
    # =========================================================================

    @property
    def Role(self) -> str:
        """Get the role of this element (e.g., 'AXButton', 'AXTextField')."""
        return GetAttribute(self.Element, Attribute.Role) or ''

    @property
    def Subrole(self) -> str:
        """Get the subrole of this element (e.g., 'AXCloseButton')."""
        return GetAttribute(self.Element, Attribute.Subrole) or ''

    @property
    def RoleDescription(self) -> str:
        """Get the localized role description (e.g., 'button', 'text field')."""
        return GetAttribute(self.Element, Attribute.RoleDescription) or ''

    @property
    def Title(self) -> str:
        """Get the title/label of this element."""
        return GetAttribute(self.Element, Attribute.Title) or ''

    @property
    def Name(self) -> str:
        """
        Get the display name of this element.
        Tries Title, then Description, then Value.
        """
        return self.Title or self.Description or ''

    @property
    def Label(self) -> str:
        """Get the human-readable label for this element (RoleDescription)."""
        return self.Title or self.Identifier or self.Description or self.Value or ''

    @property
    def Description(self) -> str:
        """Get the accessibility description of this element."""
        return GetAttribute(self.Element, Attribute.Description) or ''

    @property
    def Help(self) -> str:
        """Get the help text of this element."""
        return GetAttribute(self.Element, Attribute.Help) or ''

    @property
    def Value(self):
        """Get the value of this element (type varies by element)."""
        return GetAttribute(self.Element, Attribute.Value)

    @Value.setter
    def Value(self, value) -> None:
        """Set the value of this element."""
        SetAttribute(self.Element, Attribute.Value, value)

    @property
    def ValueString(self) -> str:
        """Get the value as a string."""
        val = self.Value
        return str(val) if val is not None else ''

    @property
    def Identifier(self) -> str:
        """Get the unique identifier (similar to Windows AutomationId)."""
        return GetAttribute(self.Element, Attribute.Identifier) or ''

    @property
    def IsEnabled(self) -> bool:
        """Check if this element is enabled."""
        val = GetAttribute(self.Element, Attribute.Enabled)
        return val is not False

    @property
    def IsFocused(self) -> bool:
        """Check if this element has keyboard focus."""
        val = GetAttribute(self.Element, Attribute.Focused)
        return val is True

    @IsFocused.setter
    def IsFocused(self, value: bool) -> None:
        """Set focus on this element."""
        SetAttribute(self.Element, Attribute.Focused, value)

    @property
    def IsHidden(self) -> bool:
        """Check if this element is hidden."""
        val = GetAttribute(self.Element, Attribute.Hidden)
        return val is True

    @property
    def IsSelected(self) -> bool:
        """Check if this element is selected."""
        val = GetAttribute(self.Element, Attribute.Selected)
        return val is True

    # =========================================================================
    # Geometry Properties
    # =========================================================================

    @property
    def Position(self) -> Optional[Point]:
        """Get the position of this element in screen coordinates."""
        pos = GetPosition(self.Element)
        if pos:
            return Point(x=pos[0], y=pos[1])
        return None

    @property
    def ElementSize(self) -> Optional[Size]:
        """Get the size of this element."""
        size = GetSize(self.Element)
        if size:
            return Size(width=size[0], height=size[1])
        return None

    @property
    def BoundingRectangle(self) -> Optional[Rect]:
        """
        Get the bounding rectangle of this element.
        Equivalent to Windows UIA BoundingRectangle property.
        """
        return GetRect(self.Element)

    @property
    def Center(self) -> Optional[Point]:
        """Get the center point of this element."""
        rect = self.BoundingRectangle
        if rect:
            cx, cy = rect.center
            return Point(x=cx, y=cy)
        return None

    # =========================================================================
    # Window Properties
    # =========================================================================

    @property
    def IsMain(self) -> bool:
        """Check if this window is the main window."""
        val = GetAttribute(self.Element, Attribute.Main)
        return val is True

    @property
    def IsMinimized(self) -> bool:
        """Check if this window is minimized."""
        val = GetAttribute(self.Element, Attribute.Minimized)
        return val is True

    @property
    def IsFullScreen(self) -> bool:
        """Check if this window is in fullscreen mode."""
        val = GetAttribute(self.Element, Attribute.FullScreen)
        if val is True:
            return True
        # Fallback check: subrole
        return self.Subrole == Subrole.FullScreenWindow

    @property
    def IsModal(self) -> bool:
        """Check if this window is modal."""
        val = GetAttribute(self.Element, Attribute.Modal)
        return val is True

    # =========================================================================
    # Navigation Properties
    # =========================================================================

    @property
    def Parent(self) -> Optional[Control]:
        """Get the parent element."""
        parent = GetAttribute(self.Element, Attribute.Parent)
        if parent:
            return CreateControl(parent)
        return None

    @property
    def Window(self) -> Optional[WindowControl]:
        """Get the containing window element."""
        window = GetAttribute(self.Element, Attribute.Window)
        if window:
            return CreateControl(window)  # type: ignore[return-value]
        return None

    @property
    def TopLevelUIElement(self) -> Optional[Control]:
        """Get the top-level UI element (typically a WindowControl or ApplicationControl)."""
        top = GetAttribute(self.Element, Attribute.TopLevelUIElement)
        if top:
            return CreateControl(top)
        return None

    @property
    def ChildCount(self) -> int:
        """Get the number of child elements."""
        return GetChildCount(self.Element)

    # =========================================================================
    # Child Access Methods
    # =========================================================================

    def GetChildren(self) -> List[Control]:
        """
        Get all child controls.
        Equivalent to Windows UIA GetChildren().
        """
        children = _GetChildren(self.Element)
        return [CreateControl(child) for child in children]

    def GetFirstChildControl(self) -> Optional[Control]:
        """Get the first child control."""
        children = _GetChildren(self.Element)
        if children:
            return CreateControl(children[0])
        return None

    def GetLastChildControl(self) -> Optional[Control]:
        """Get the last child control."""
        children = _GetChildren(self.Element)
        if children:
            return CreateControl(children[-1])
        return None

    # =========================================================================
    # Application-specific access
    # =========================================================================

    @property
    def FocusedWindow(self) -> Optional[WindowControl]:
        """Get the focused window of this application element."""
        window = GetAttribute(self.Element, Attribute.FocusedWindow)
        if window:
            return CreateControl(window)  # type: ignore[return-value]
        return None

    @property
    def MainWindow(self) -> Optional[WindowControl]:
        """Get the main window of this application element."""
        window = GetAttribute(self.Element, Attribute.MainWindow)
        if window:
            return CreateControl(window)  # type: ignore[return-value]
        return None

    @property
    def Windows(self) -> List[WindowControl]:
        """Get all windows of this application element."""
        windows = GetAttribute(self.Element, Attribute.Windows)
        if windows:
            return [CreateControl(w) for w in windows]  # type: ignore[misc]
        return []

    @property
    def MenuBar(self) -> Optional[Control]:
        """Get the menu bar of this application element."""
        menu_bar = GetAttribute(self.Element, Attribute.MenuBar)
        if menu_bar:
            return CreateControl(menu_bar)
        return None

    @property
    def ExtrasMenuBar(self) -> Optional[Control]:
        """Get the extras menu bar (status bar items) of this application element."""
        extras = GetAttribute(self.Element, Attribute.ExtrasMenuBar)
        if extras:
            return CreateControl(extras)
        return None

    # =========================================================================
    # Scroll-specific Properties
    # =========================================================================

    @property
    def HorizontalScrollBar(self) -> Optional[Control]:
        """Get the horizontal scroll bar."""
        sb = GetAttribute(self.Element, Attribute.HorizontalScrollBar)
        if sb:
            return CreateControl(sb)
        return None

    @property
    def VerticalScrollBar(self) -> Optional[Control]:
        """Get the vertical scroll bar."""
        sb = GetAttribute(self.Element, Attribute.VerticalScrollBar)
        if sb:
            return CreateControl(sb)
        return None

    @property
    def IsHorizontallyScrollable(self) -> bool:
        """Check if the element can scroll horizontally."""
        return self.HorizontalScrollBar is not None

    @property
    def IsVerticallyScrollable(self) -> bool:
        """Check if the element can scroll vertically."""
        return self.VerticalScrollBar is not None

    # =========================================================================
    # Table/Grid Properties
    # =========================================================================

    @property
    def Rows(self) -> List[Control]:
        """Get all rows (for tables/outlines)."""
        rows = GetAttribute(self.Element, Attribute.Rows)
        if rows:
            return [CreateControl(r) for r in rows]
        return []

    @property
    def VisibleRows(self) -> List[Control]:
        """Get visible rows."""
        rows = GetAttribute(self.Element, Attribute.VisibleRows)
        if rows:
            return [CreateControl(r) for r in rows]
        return []

    @property
    def Columns(self) -> List[Control]:
        """Get all columns."""
        cols = GetAttribute(self.Element, Attribute.Columns)
        if cols:
            return [CreateControl(c) for c in cols]
        return []

    @property
    def SelectedRows(self) -> List[Control]:
        """Get selected rows."""
        rows = GetAttribute(self.Element, Attribute.SelectedRows)
        if rows:
            return [CreateControl(r) for r in rows]
        return []

    # =========================================================================
    # Expand/Collapse Properties
    # =========================================================================

    @property
    def IsExpanded(self) -> bool:
        """Check if this element is expanded."""
        val = GetAttribute(self.Element, Attribute.Expanded)
        return val is True

    # =========================================================================
    # Text Properties
    # =========================================================================

    @property
    def NumberOfCharacters(self) -> int:
        """Get the number of characters in a text element."""
        val = GetAttribute(self.Element, Attribute.NumberOfCharacters)
        return val if val is not None else 0

    @property
    def SelectedText(self) -> str:
        """Get the selected text."""
        return GetAttribute(self.Element, Attribute.SelectedText) or ''

    @property
    def SelectedTextRange(self):
        """Get the selected text range."""
        return GetAttribute(self.Element, Attribute.SelectedTextRange)

    @property
    def VisibleCharacterRange(self):
        """Get the visible character range."""
        return GetAttribute(self.Element, Attribute.VisibleCharacterRange)

    @property
    def PlaceholderValue(self) -> str:
        """Get placeholder text (for text fields)."""
        return GetAttribute(self.Element, Attribute.PlaceholderValue) or ''

    # =========================================================================
    # Misc Properties
    # =========================================================================

    @property
    def URL(self) -> str:
        """Get the URL (for links and web elements)."""
        val = GetAttribute(self.Element, Attribute.URL)
        return str(val) if val else ''

    @property
    def Document(self) -> str:
        """Get the document path/URL."""
        val = GetAttribute(self.Element, Attribute.Document)
        return str(val) if val else ''

    # =========================================================================
    # Attribute Inspection
    # =========================================================================

    @property
    def AttributeNames(self) -> list[str]:
        """Get all attribute names supported by this element."""
        return GetAttributeNames(self.Element) or []

    @property
    def ActionNames(self) -> list[str]:
        """Get all action names supported by this element."""
        return GetActionNames(self.Element) or []

    def GetAttributeValue(self, attribute: str):
        """Get a specific attribute value by name."""
        return GetAttribute(self.Element, attribute)

    def SetAttributeValue(self, attribute: str, value) -> bool:
        """Set a specific attribute value by name."""
        return SetAttribute(self.Element, attribute, value)

    def IsAttributeSettable(self, attribute: str) -> bool:
        """Check if an attribute can be set."""
        return IsAttributeSettable(self.Element, attribute)

    # =========================================================================
    # Actions
    # =========================================================================

    def PerformAction(self, action: str) -> bool:
        """
        Perform an action on this element.
        Returns True if successful.
        """
        return PerformAction(self.Element, action)

    def Press(self) -> bool:
        """Perform AXPress action (click/activate)."""
        return self.PerformAction(Action.Press)

    def Confirm(self) -> bool:
        """Perform AXConfirm action."""
        return self.PerformAction(Action.Confirm)

    def Cancel(self) -> bool:
        """Perform AXCancel action."""
        return self.PerformAction(Action.Cancel)

    def Increment(self) -> bool:
        """Perform AXIncrement action."""
        return self.PerformAction(Action.Increment)

    def Decrement(self) -> bool:
        """Perform AXDecrement action."""
        return self.PerformAction(Action.Decrement)

    def ShowMenu(self) -> bool:
        """Perform AXShowMenu action (right-click menu)."""
        return self.PerformAction(Action.ShowMenu)

    def Pick(self) -> bool:
        """Perform AXPick action."""
        return self.PerformAction(Action.Pick)

    def Raise(self) -> bool:
        """Perform AXRaise action (bring to front)."""
        return self.PerformAction(Action.Raise)

    def SetFocus(self) -> bool:
        """Set focus to this element."""
        return SetAttribute(self.Element, Attribute.Focused, True)

    # =========================================================================
    # Search Methods
    # =========================================================================

    def FindAll(
        self,
        role: Optional[Role|str] = None,
        subrole: Optional[str] = None,
        title: Optional[str] = None,
        identifier: Optional[str] = None,
        predicate: Optional[Callable[[Control], bool]] = None,
        max_depth: int = 25,
    ) -> List[Control]:
        """
        Find all descendant controls matching the given criteria.
        Equivalent to Windows UIA FindAll().

        Args:
            role: Filter by AXRole.
            subrole: Filter by AXSubrole.
            title: Filter by AXTitle (substring match).
            identifier: Filter by AXIdentifier.
            predicate: Custom filter function.
            max_depth: Maximum search depth.

        Returns:
            List of matching typed Control objects.
        """
        raw_results = []
        _find_recursive_raw(
            self.Element, raw_results, role, subrole, title,
            identifier, predicate, max_depth, 0, find_first=False
        )
        return [CreateControl(elem) for elem in raw_results]

    def FindFirst(
        self,
        role: Optional[Role|str] = None,
        subrole: Optional[str] = None,
        title: Optional[str] = None,
        identifier: Optional[str] = None,
        predicate: Optional[Callable[[Control], bool]] = None,
        max_depth: int = 25,
    ) -> Optional[Control]:
        """
        Find the first descendant control matching the given criteria.
        Equivalent to Windows UIA FindFirst().
        """
        raw_results = []
        _find_recursive_raw(
            self.Element, raw_results, role, subrole, title,
            identifier, predicate, max_depth, 0, find_first=True
        )
        return CreateControl(raw_results[0]) if raw_results else None

    def HasAction(self, action: str) -> bool:
        """Check if this element supports a specific action."""
        return action in self.ActionNames

    # =========================================================================
    # Mouse Actions
    # =========================================================================

    def Click(self, ratioX: float = 0.5, ratioY: float = 0.5, waitTime: float = 0.05) -> None:
        """
        Click this control at the given ratio position.

        Args:
            ratioX: Horizontal position ratio (0.0=left, 0.5=center, 1.0=right).
            ratioY: Vertical position ratio (0.0=top, 0.5=center, 1.0=bottom).
            waitTime: Delay after clicking.
        """
        point = self._get_click_point(ratioX, ratioY)
        if point:
            _Click(point[0], point[1], waitTime)

    def RightClick(self, ratioX: float = 0.5, ratioY: float = 0.5, waitTime: float = 0.05) -> None:
        """Right-click this control."""
        point = self._get_click_point(ratioX, ratioY)
        if point:
            _RightClick(point[0], point[1], waitTime)

    def DoubleClick(self, ratioX: float = 0.5, ratioY: float = 0.5, waitTime: float = 0.05) -> None:
        """Double-click this control."""
        point = self._get_click_point(ratioX, ratioY)
        if point:
            _DoubleClick(point[0], point[1], waitTime)

    def MiddleClick(self, ratioX: float = 0.5, ratioY: float = 0.5, waitTime: float = 0.05) -> None:
        """Middle-click this control."""
        point = self._get_click_point(ratioX, ratioY)
        if point:
            _MiddleClick(point[0], point[1], waitTime)

    def WheelDown(self, clicks: int = 3) -> None:
        """Scroll down on this control."""
        self.MoveCursorToCenter()
        _WheelDown(clicks)

    def WheelUp(self, clicks: int = 3) -> None:
        """Scroll up on this control."""
        self.MoveCursorToCenter()
        _WheelUp(clicks)

    def DragTo(
        self,
        target: Union[Control, Point, tuple],
        duration: float = 0.5,
        steps: int = 20,
    ) -> None:
        """
        Drag from this control's center to a target.

        Args:
            target: A Control (uses its center), a Point, or (x, y) tuple.
            duration: Duration of the drag in seconds.
            steps: Number of intermediate mouse move steps.
        """
        start = self.Center
        if not start:
            return

        if isinstance(target, Control):
            end = target.Center
            if not end:
                return
            end_x, end_y = end.x, end.y
        elif isinstance(target, Point):
            end_x, end_y = target.x, target.y
        elif isinstance(target, (tuple, list)) and len(target) >= 2:
            end_x, end_y = target[0], target[1]
        else:
            return

        _DragTo(start.x, start.y, end_x, end_y, duration, steps)

    def MoveCursorToCenter(self) -> None:
        """Move the mouse cursor to the center of this control."""
        center = self.Center
        if center:
            _MoveTo(center.x, center.y)

    def _get_click_point(self, ratioX: float = 0.5, ratioY: float = 0.5) -> Optional[tuple[float, float]]:
        """Calculate click coordinates from ratio position within bounding rect."""
        rect = self.BoundingRectangle
        if rect:
            x = rect.left + rect.width * ratioX
            y = rect.top + rect.height * ratioY
            return (x, y)
        return None

    # =========================================================================
    # Keyboard Actions
    # =========================================================================

    def SendKeys(self, text: str, interval: float = 0.01) -> None:
        """
        Focus this control and type text into it.

        Args:
            text: The text to type.
            interval: Delay between keystrokes in seconds.
        """
        self.SetFocus()
        _TypeText(text, interval)

    # =========================================================================
    # Fluent Chaining Methods
    # =========================================================================

    def ApplicationControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'ApplicationControl':
        """Find the first AXApplication child control."""
        return self.FindFirst(role=Role.Application, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def WindowControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'WindowControl':
        """Find the first AXWindow child control."""
        return self.FindFirst(role=Role.Window, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def ButtonControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'ButtonControl':
        """Find the first AXButton child control."""
        return self.FindFirst(role=Role.Button, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def CheckBoxControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'CheckBoxControl':
        """Find the first AXCheckBox child control."""
        return self.FindFirst(role=Role.CheckBox, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def RadioButtonControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'RadioButtonControl':
        """Find the first AXRadioButton child control."""
        return self.FindFirst(role=Role.RadioButton, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def TextFieldControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'TextFieldControl':
        """Find the first AXTextField child control."""
        return self.FindFirst(role=Role.TextField, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def TextAreaControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'TextAreaControl':
        """Find the first AXTextArea child control."""
        return self.FindFirst(role=Role.TextArea, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def ComboBoxControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'ComboBoxControl':
        """Find the first AXComboBox child control."""
        return self.FindFirst(role=Role.ComboBox, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def PopUpButtonControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'PopUpButtonControl':
        """Find the first AXPopUpButton child control."""
        return self.FindFirst(role=Role.PopUpButton, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def SliderControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'SliderControl':
        """Find the first AXSlider child control."""
        return self.FindFirst(role=Role.Slider, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def MenuItemControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'MenuItemControl':
        """Find the first AXMenuItem child control."""
        return self.FindFirst(role=Role.MenuItem, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def MenuBarItemControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'MenuBarItemControl':
        """Find the first AXMenuBarItem child control."""
        return self.FindFirst(role=Role.MenuBarItem, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def TabControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'TabControl':
        """Find the first AXTab child control (use AXTabGroup for tab groups)."""
        return self.FindFirst(role=Role.Tab, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def ListControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'ListControl':
        """Find the first AXList child control."""
        return self.FindFirst(role=Role.List, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def TableControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'TableControl':
        """Find the first AXTable child control."""
        return self.FindFirst(role=Role.Table, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def OutlineControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'OutlineControl':
        """Find the first AXOutline child control."""
        return self.FindFirst(role=Role.Outline, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def ScrollAreaControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'ScrollAreaControl':
        """Find the first AXScrollArea child control."""
        return self.FindFirst(role=Role.ScrollArea, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def GroupControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'GroupControl':
        """Find the first AXGroup child control."""
        return self.FindFirst(role=Role.Group, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def ImageControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'ImageControl':
        """Find the first AXImage child control."""
        return self.FindFirst(role=Role.Image, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def LinkControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'LinkControl':
        """Find the first AXLink child control."""
        return self.FindFirst(role=Role.Link, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def StaticTextControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'StaticTextControl':
        """Find the first AXStaticText child control."""
        return self.FindFirst(role=Role.StaticText, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def WebAreaControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'WebAreaControl':
        """Find the first AXWebArea child control."""
        return self.FindFirst(role=Role.WebArea, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def DisclosureTriangleControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'DisclosureTriangleControl':
        """Find the first AXDisclosureTriangle child control."""
        return self.FindFirst(role=Role.DisclosureTriangle, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def RowControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'RowControl':
        """Find the first AXRow child control."""
        return self.FindFirst(role=Role.Row, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def CellControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'CellControl':
        """Find the first AXCell child control."""
        return self.FindFirst(role=Role.Cell, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def DockItemControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'DockItemControl':
        """Find the first AXDockItem child control."""
        return self.FindFirst(role=Role.DockItem, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    def ProgressIndicatorControl(self, title=None, identifier=None, predicate=None, max_depth=25) -> 'ProgressIndicatorControl':
        """Find the first AXProgressIndicator child control."""
        return self.FindFirst(role=Role.ProgressIndicator, title=title, identifier=identifier, predicate=predicate, max_depth=max_depth)

    # =========================================================================
    # Representation
    # =========================================================================

    def __str__(self) -> str:
        role = self.Role
        name = self.Label
        rect = self.BoundingRectangle
        return f'Control(Role={role}, Name={name!r}, Rect={rect})'

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} Role={self.Role!r} Name={self.Label!r}>'

    def __eq__(self, other) -> bool:
        if isinstance(other, Control):
            return self._element == other._element
        return NotImplemented

    def __hash__(self):
        return hash(id(self._element))


# =============================================================================
# Typed Control Subclasses
# =============================================================================

class ApplicationControl(Control):
    """
    Control for AXApplication elements.

    Wraps both the AXUIElementRef (for accessibility tree access) and
    the NSRunningApplication (for process-level metadata like bundle ID,
    icon, launch date, hidden state, etc.).

    The NSRunningApplication is lazily resolved from the PID on first access.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ns_running_app = None  # Lazily resolved

    def _get_ns_running_app(self):
        """Lazily resolve the NSRunningApplication for this application's PID."""
        if self._ns_running_app is None:
            pid = GetElementPid(self.Element)
            if pid is not None:
                from Cocoa import NSWorkspace
                for app in NSWorkspace.sharedWorkspace().runningApplications():
                    if app.processIdentifier() == pid:
                        self._ns_running_app = app
                        break
        return self._ns_running_app

    def __str__(self) -> str:
        return (
            f"App(Name={self.Name!r}, Status={self.Status!r}, "
            f"Policy={self.ActivationPolicy!r})"
        )

    def __repr__(self) -> str:
        return self.__str__()

    # =========================================================================
    # Overridden base properties
    # =========================================================================

    @property
    def Name(self) -> str:
        """
        Get the display name of this application.
        Tries AX Title
        """
        name = self.Title
        return name if name else self.LocalizedName

    @property
    def IsMinimized(self) -> bool:
        """
        Check if this application's windows are all minimized.
        Returns True only when the application has at least one window
        and every window is minimized.  Returns False if there are no
        windows or any window is not minimized.
        """
        windows = self.Windows
        if not windows:
            return False
        return all(w.IsMinimized for w in windows)

    @property
    def IsFullScreen(self) -> bool:
        """
        Check if any of this application's windows are in fullscreen mode.
        Returns True if at least one window is fullscreen.
        Returns False if there are no windows or none are fullscreen.
        """
        windows = self.Windows
        if not windows:
            return False
        return any(w.IsFullScreen for w in windows)

    @property
    def Status(self) -> str:
        """
        Get a human-readable status summarizing the application's current state.

        Returns one of:
            'Active'     — Frontmost application with visible windows.
            'Fullscreen' — Frontmost application in fullscreen mode.
            'Visible'    — Has windows on screen but is not the frontmost app.
            'Hidden'     — Hidden via Cmd+H; windows are preserved but invisible.
            'Minimized'  — All windows are minimized to the Dock.
            'Windowless' — Running but has no windows (closed or never opened).
        """
        if self.IsHidden:
            return 'Hidden'
        windows = self.Windows
        if not windows:
            return 'Windowless'
        if all(w.IsMinimized for w in windows):
            return 'Minimized'
        if self.IsActive:
            if any(w.IsFullScreen for w in windows):
                return 'Fullscreen'
            return 'Active'
        return 'Visible'

    # =========================================================================
    # AX-based properties (accessibility tree)
    # =========================================================================

    @property
    def FocusedUIElement(self) -> Optional[Control]:
        """Get the currently focused UI element in this application."""
        elem = GetAttribute(self.Element, Attribute.FocusedUIElement)
        if elem:
            return CreateControl(elem)
        return None

    @property
    def FocusedWindow(self) -> Optional[WindowControl]:
        """Get the focused window of this application element."""
        window = GetAttribute(self.Element, Attribute.FocusedWindow)
        if window:
            return CreateControl(window)  # type: ignore[return-value]
        return None

    @property
    def MainWindow(self) -> Optional[WindowControl]:
        """Get the main window of this application element."""
        window = GetAttribute(self.Element, Attribute.MainWindow)
        if window:
            return CreateControl(window)  # type: ignore[return-value]
        return None

    @property
    def Windows(self) -> List[WindowControl]:
        """Get all windows of this application element."""
        windows = GetAttribute(self.Element, Attribute.Windows)
        if windows:
            return [CreateControl(w) for w in windows]  # type: ignore[misc]
        return []

    @property
    def IsApplicationRunning(self) -> bool:
        """Check if the application is running (AX attribute)."""
        val = GetAttribute(self.Element, Attribute.IsApplicationRunning)
        return val is True

    @property
    def EnhancedUserInterface(self) -> bool:
        """Get the enhanced user interface flag."""
        val = GetAttribute(self.Element, Attribute.Enhanced)
        return val is True

    @EnhancedUserInterface.setter
    def EnhancedUserInterface(self, value: bool) -> None:
        """Set the enhanced user interface flag (enables deeper tree access in some apps)."""
        SetAttribute(self.Element, Attribute.Enhanced, value)

    # =========================================================================
    # NSRunningApplication properties (process-level metadata)
    # =========================================================================

    @property
    def PID(self) -> Optional[int]:
        """Get the process identifier (PID) of this application."""
        return GetElementPid(self.Element)

    @property
    def BundleIdentifier(self) -> Optional[str]:
        """
        Get the CFBundleIdentifier of this application.
        Example: 'com.apple.Safari', 'com.google.Chrome'.
        """
        app = self._get_ns_running_app()
        if app:
            val = app.bundleIdentifier()
            return str(val) if val else None
        return None

    @property
    def BundleURL(self) -> Optional[str]:
        """
        Get the file URL to the application's .app bundle.
        Example: 'file:///Applications/Safari.app/'.
        """
        app = self._get_ns_running_app()
        if app:
            url = app.bundleURL()
            return str(url) if url else None
        return None

    @property
    def ExecutableURL(self) -> Optional[str]:
        """
        Get the file URL to the application's executable binary.
        Example: 'file:///Applications/Safari.app/Contents/MacOS/Safari'.
        """
        app = self._get_ns_running_app()
        if app:
            url = app.executableURL()
            return str(url) if url else None
        return None

    @property
    def LocalizedName(self) -> Optional[str]:
        """
        Get the localized display name of the application.
        Example: 'Safari', 'Google Chrome'.
        This is the user-facing name shown in the Dock and App Switcher.
        """
        app = self._get_ns_running_app()
        if app:
            val = app.localizedName()
            return str(val) if val else None
        return None

    @property
    def Icon(self):
        """
        Get the application icon as an NSImage.
        Can be converted to other formats using Cocoa APIs.

        Returns:
            NSImage or None.
        """
        app = self._get_ns_running_app()
        if app:
            return app.icon()
        return None

    @property
    def LaunchDate(self):
        """
        Get the date and time when the application was launched.

        Returns:
            NSDate or None.
        """
        app = self._get_ns_running_app()
        if app:
            return app.launchDate()
        return None

    @property
    def IsActive(self) -> bool:
        """
        Check if this application is the currently active (frontmost) application.

        Uses CGWindowListCopyWindowInfo (via GetForegroundWindowPID) instead of
        NSRunningApplication.isActive() because the latter relies on AppKit
        notifications delivered via NSRunLoop. Without an active event loop
        (e.g. Python scripts, notebooks), isActive() returns stale cached data.
        """
        pid = self.PID
        if pid is None:
            return False
        frontmost_pid = GetForegroundWindowPID()
        return pid == frontmost_pid

    @property
    def IsHidden(self) -> bool:
        """Check if this application is currently hidden."""
        app = self._get_ns_running_app()
        if app:
            return bool(app.isHidden())
        return False

    @property
    def IsFinishedLaunching(self) -> bool:
        """Check if the application has finished launching."""
        app = self._get_ns_running_app()
        if app:
            return bool(app.isFinishedLaunching())
        return False

    @property
    def IsTerminated(self) -> bool:
        """Check if the application has been terminated."""
        app = self._get_ns_running_app()
        if app:
            return bool(app.isTerminated())
        return False

    @property
    def ActivationPolicy(self) -> Optional[str]:
        """
        Get the activation policy of the application as a human-readable string.

        Returns:
            'Regular'    — appears in Dock and App Switcher (normal apps),
            'Accessory'  — does not appear in Dock, may show in App Switcher,
            'Prohibited' — does not appear in Dock or App Switcher (background agents),
            None if unavailable.
        """
        app = self._get_ns_running_app()
        if app:
            policy = int(app.activationPolicy())
            return ActivationPolicyNames.get(policy, f'Unknown({policy})')
        return None

    @property
    def ExecutableArchitecture(self) -> Optional[int]:
        """
        Get the executing processor architecture of the application.

        Common values:
            - 16777223 (0x01000007) = x86_64
            - 16777228 (0x0100000C) = arm64
        """
        app = self._get_ns_running_app()
        if app:
            return int(app.executableArchitecture())
        return None

    @property
    def OwnsMenuBar(self) -> bool:
        """Check if this application currently owns the menu bar."""
        app = self._get_ns_running_app()
        if app:
            return bool(app.ownsMenuBar())
        return False

    # =========================================================================
    # NSRunningApplication methods (process-level actions)
    # =========================================================================

    def Activate(self, ignoring_other_apps: bool = True) -> bool:
        """
        Activate (bring to front) this application.

        Args:
            ignoring_other_apps: If True, activates even if another app is active.

        Returns:
            True if activation was successful.
        """
        app = self._get_ns_running_app()
        if app:
            from Cocoa import NSApplicationActivateIgnoringOtherApps
            options = NSApplicationActivateIgnoringOtherApps if ignoring_other_apps else 0
            return bool(app.activateWithOptions_(options))
        return False

    def Hide(self) -> bool:
        """
        Hide this application (equivalent to Cmd+H).

        Returns:
            True if the application was successfully hidden.
        """
        app = self._get_ns_running_app()
        if app:
            return bool(app.hide())
        return False

    def Unhide(self) -> bool:
        """
        Unhide (show) this application if it was hidden.

        Returns:
            True if the application was successfully unhidden.
        """
        app = self._get_ns_running_app()
        if app:
            return bool(app.unhide())
        return False

    def Terminate(self) -> bool:
        """
        Request this application to quit gracefully.
        The application may prompt to save unsaved documents.

        Returns:
            True if the termination request was sent successfully.
        """
        app = self._get_ns_running_app()
        if app:
            return bool(app.terminate())
        return False

    def ForceTerminate(self) -> bool:
        """
        Force-quit this application immediately.
        Does not give the application a chance to save or clean up.
        Use with caution.

        Returns:
            True if the force termination was successful.
        """
        app = self._get_ns_running_app()
        if app:
            return bool(app.forceTerminate())
        return False


class WindowControl(Control):
    """
    Control for AXWindow elements.
    Provides window management methods similar to Windows UIA TopLevel mixin.
    """

    def Close(self) -> bool:
        """Close this window via the close button."""
        close_btn = GetAttribute(self.Element, Attribute.CloseButton)
        if close_btn:
            return PerformAction(close_btn, Action.Press)
        return False

    def Minimize(self) -> bool:
        """Minimize this window."""
        return SetAttribute(self.Element, Attribute.Minimized, True)

    def Unminimize(self) -> bool:
        """Restore this minimized window."""
        return SetAttribute(self.Element, Attribute.Minimized, False)

    def Restore(self) -> bool:
        """Restore from minimized state (alias for Unminimize)."""
        return self.Unminimize()

    def Zoom(self) -> bool:
        """Zoom (maximize) this window via the zoom button."""
        zoom_btn = GetAttribute(self.Element, Attribute.ZoomButton)
        if zoom_btn:
            return PerformAction(zoom_btn, Action.Press)
        return False

    def Maximize(self) -> bool:
        """Maximize (zoom) this window. Alias for Zoom()."""
        return self.Zoom()

    def FullScreen(self) -> bool:
        """Toggle fullscreen mode via AXFullScreen attribute."""
        current = self.IsFullScreen
        return SetAttribute(self.Element, Attribute.FullScreen, not current)

    def SetActive(self, waitTime: float = 0.1) -> bool:
        """
        Bring this window's application to front and raise the window.

        Args:
            waitTime: Delay after activation.
        """
        pid = GetElementPid(self.Element)
        if pid:
            ActivateApplication(pid)
        self.Raise()
        time.sleep(waitTime)
        return True

    def MoveToCenter(self) -> bool:
        """Move this window to the center of the screen."""
        rect = self.BoundingRectangle
        if not rect:
            return False
        screen_w, screen_h = GetScreenSize()
        new_x = (screen_w - rect.width) / 2
        new_y = (screen_h - rect.height) / 2
        return SetAttribute(self.Element, Attribute.Position, (new_x, new_y))

    def Resize(self, width: float, height: float) -> bool:
        """
        Resize this window.

        Args:
            width: New width in points.
            height: New height in points.
        """
        return SetAttribute(self.Element, Attribute.Size, (width, height))

    def MoveWindowTo(self, x: float, y: float) -> bool:
        """
        Move this window to the specified screen position.

        Args:
            x: X coordinate.
            y: Y coordinate.
        """
        return SetAttribute(self.Element, Attribute.Position, (x, y))

    @property
    def DefaultButton(self) -> Optional[Control]:
        """Get the default button of this window/dialog."""
        btn = GetAttribute(self.Element, Attribute.DefaultButton)
        if btn:
            return CreateControl(btn)
        return None

    @property
    def CancelButton(self) -> Optional[Control]:
        """Get the cancel button of this window/dialog."""
        btn = GetAttribute(self.Element, Attribute.CancelButton)
        if btn:
            return CreateControl(btn)
        return None


class ButtonControl(Control):
    """Control for AXButton elements."""
    pass


class CheckBoxControl(Control):
    """Control for AXCheckBox elements."""

    @property
    def IsChecked(self) -> bool:
        """Check if the checkbox is checked."""
        val = self.Value
        return val == 1 or val is True

    def Toggle(self) -> bool:
        """Toggle the checkbox."""
        return self.Press()


class RadioButtonControl(Control):
    """Control for AXRadioButton elements."""

    @property
    def IsSelected(self) -> bool:
        """Check if this radio button is selected."""
        val = self.Value
        return val == 1 or val is True

    def Select(self) -> bool:
        """Select this radio button."""
        return self.Press()


class TextFieldControl(Control):
    """Control for AXTextField elements."""

    def SetText(self, text: str) -> bool:
        """Set the text value of this field."""
        return SetAttribute(self.Element, Attribute.Value, text)

    def GetText(self) -> str:
        """Get the text value of this field."""
        return self.ValueString

    @property
    def InsertionPoint(self) -> int:
        """Get the insertion point line number."""
        val = GetAttribute(self.Element, Attribute.InsertionPointLineNumber)
        return val if val is not None else 0

    def ClearText(self) -> bool:
        """Clear the text in this field."""
        return self.SetText('')


class TextAreaControl(TextFieldControl):
    """Control for AXTextArea elements (multi-line text)."""
    pass


class ComboBoxControl(Control):
    """Control for AXComboBox elements."""

    def SetText(self, text: str) -> bool:
        """Set the text value."""
        return SetAttribute(self.Element, Attribute.Value, text)

    def Expand(self) -> bool:
        """Expand the dropdown."""
        return self.Press()


class PopUpButtonControl(Control):
    """Control for AXPopUpButton elements (dropdown menus)."""

    def Open(self) -> bool:
        """Open the pop-up menu."""
        return self.Press()


class SliderControl(Control):
    """Control for AXSlider elements."""

    @property
    def SliderValue(self) -> float:
        """Get the slider value as a float."""
        val = self.Value
        try:
            return float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @SliderValue.setter
    def SliderValue(self, value: float) -> None:
        """Set the slider value."""
        SetAttribute(self.Element, Attribute.Value, value)

    @property
    def MinValue(self) -> float:
        """Get the minimum value."""
        val = GetAttribute(self.Element, Attribute.MinValue)
        return float(val) if val is not None else 0.0

    @property
    def MaxValue(self) -> float:
        """Get the maximum value."""
        val = GetAttribute(self.Element, Attribute.MaxValue)
        return float(val) if val is not None else 100.0


class MenuItemControl(Control):
    """Control for AXMenuItem elements."""

    @property
    def MenuItemCmdChar(self) -> str:
        """Get the command character shortcut."""
        return GetAttribute(self.Element, Attribute.MenuItemCmdChar) or ''

    def Select(self) -> bool:
        """Select this menu item."""
        return self.Press()


class MenuBarItemControl(Control):
    """Control for AXMenuBarItem elements."""

    def Open(self) -> bool:
        """Open this menu bar item."""
        return self.Press()


class TabControl(Control):
    """Control for AXTab elements."""

    def Select(self) -> bool:
        """Select this tab."""
        return self.Press()


class ListControl(Control):
    """Control for AXList elements."""

    @property
    def SelectedChildren(self) -> List[Control]:
        """Get selected children."""
        children = GetAttribute(self.Element, Attribute.SelectedChildren)
        if children:
            return [CreateControl(c) for c in children]
        return []


class TableControl(Control):
    """Control for AXTable elements."""

    @property
    def RowCount(self) -> int:
        """Get the number of rows."""
        val = GetAttribute(self.Element, Attribute.RowCount)
        return val if val is not None else 0

    @property
    def ColumnCount(self) -> int:
        """Get the number of columns."""
        val = GetAttribute(self.Element, Attribute.ColumnCount)
        return val if val is not None else 0

    @property
    def Header(self) -> Optional[Control]:
        """Get the table header."""
        header = GetAttribute(self.Element, Attribute.Header)
        if header:
            return CreateControl(header)
        return None


class OutlineControl(Control):
    """Control for AXOutline elements (tree views)."""

    @property
    def DisclosedRows(self) -> List[Control]:
        """Get disclosed (visible) rows."""
        rows = GetAttribute(self.Element, Attribute.DisclosedRows)
        if rows:
            return [CreateControl(r) for r in rows]
        return []


class ScrollAreaControl(Control):
    """Control for AXScrollArea elements."""

    @property
    def Contents(self) -> List[Control]:
        """Get the contents of the scroll area."""
        contents = GetAttribute(self.Element, Attribute.Contents)
        if contents:
            return [CreateControl(c) for c in contents]
        return []

    def GetScrollPosition(self) -> tuple[float, float]:
        """
        Get the scroll position as (horizontal_percent, vertical_percent).
        Values are 0.0 to 1.0.
        """
        h_pct = 0.0
        v_pct = 0.0
        h_bar = GetAttribute(self.Element, Attribute.HorizontalScrollBar)
        if h_bar:
            val = GetAttribute(h_bar, Attribute.Value)
            if val is not None:
                try:
                    h_pct = float(val)
                except (TypeError, ValueError):
                    pass
        v_bar = GetAttribute(self.Element, Attribute.VerticalScrollBar)
        if v_bar:
            val = GetAttribute(v_bar, Attribute.Value)
            if val is not None:
                try:
                    v_pct = float(val)
                except (TypeError, ValueError):
                    pass
        return (h_pct, v_pct)


class GroupControl(Control):
    """Control for AXGroup elements."""
    pass


class ImageControl(Control):
    """Control for AXImage elements."""

    @property
    def URL(self) -> str:
        """Get the image URL if available."""
        val = GetAttribute(self.Element, Attribute.URL)
        return str(val) if val else ''


class LinkControl(Control):
    """Control for AXLink elements."""

    @property
    def URL(self) -> str:
        """Get the link URL."""
        val = GetAttribute(self.Element, Attribute.URL)
        return str(val) if val else ''


class ProgressIndicatorControl(Control):
    """Control for AXProgressIndicator elements."""

    @property
    def ProgressValue(self) -> float:
        """Get the progress value."""
        val = self.Value
        try:
            return float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            return 0.0


class StaticTextControl(Control):
    """Control for AXStaticText elements."""

    @property
    def Text(self) -> str:
        """Get the text content."""
        return self.ValueString or self.Title


class WebAreaControl(Control):
    """Control for AXWebArea elements."""

    @property
    def URL(self) -> str:
        """Get the web page URL."""
        val = GetAttribute(self.Element, Attribute.URL)
        return str(val) if val else ''

    @property
    def Document(self) -> str:
        """Get the document URL."""
        val = GetAttribute(self.Element, Attribute.Document)
        return str(val) if val else ''


class DisclosureTriangleControl(Control):
    """Control for AXDisclosureTriangle elements."""

    @property
    def IsExpanded(self) -> bool:
        """Check if the disclosure is expanded."""
        val = self.Value
        return val == 1 or val is True

    def Toggle(self) -> bool:
        """Toggle the disclosure state."""
        return self.Press()


class DockItemControl(Control):
    """Control for AXDockItem elements."""
    pass


class CellControl(Control):
    """Control for AXCell elements."""

    @property
    def RowIndex(self) -> int:
        """Get the row index of this cell."""
        val = GetAttribute(self.Element, Attribute.Index)
        return val if val is not None else -1


class RowControl(Control):
    """Control for AXRow/AXOutlineRow elements."""

    @property
    def Index(self) -> int:
        """Get the row index."""
        val = GetAttribute(self.Element, Attribute.Index)
        return val if val is not None else -1

    @property
    def DisclosureLevel(self) -> int:
        """Get the outline disclosure level."""
        val = GetAttribute(self.Element, Attribute.DisclosureLevel)
        return val if val is not None else 0

    @property
    def IsDisclosed(self) -> bool:
        """Check if this outline row is disclosed (expanded)."""
        val = GetAttribute(self.Element, Attribute.Expanded)
        return val is True


# =============================================================================
# Control Factory
# =============================================================================

# Role to typed Control class mapping
_ROLE_TO_CONTROL_CLASS = {
    Role.Application: ApplicationControl,
    Role.Window: WindowControl,
    Role.Button: ButtonControl,
    Role.CheckBox: CheckBoxControl,
    Role.RadioButton: RadioButtonControl,
    Role.TextField: TextFieldControl,
    Role.TextArea: TextAreaControl,
    Role.ComboBox: ComboBoxControl,
    Role.PopUpButton: PopUpButtonControl,
    Role.Slider: SliderControl,
    Role.MenuItem: MenuItemControl,
    Role.MenuBarItem: MenuBarItemControl,
    Role.Tab: TabControl,
    Role.List: ListControl,
    Role.Table: TableControl,
    Role.Outline: OutlineControl,
    Role.ScrollArea: ScrollAreaControl,
    Role.Group: GroupControl,
    Role.Image: ImageControl,
    Role.Link: LinkControl,
    Role.ProgressIndicator: ProgressIndicatorControl,
    Role.StaticText: StaticTextControl,
    Role.WebArea: WebAreaControl,
    Role.DisclosureTriangle: DisclosureTriangleControl,
    Role.DockItem: DockItemControl,
    Role.Cell: CellControl,
    Role.Row: RowControl,
    Role.OutlineRow: RowControl,
}


def CreateControl(element) -> Control:
    """
    Create the appropriate typed Control subclass for an AXUIElement.
    Equivalent to Windows UIA Control.CreateControlFromElement().

    Args:
        element: An AXUIElementRef.

    Returns:
        A typed Control subclass (e.g., ButtonControl, TextFieldControl).
    """
    role = GetAttribute(element, Attribute.Role)
    control_class = _ROLE_TO_CONTROL_CLASS.get(role, Control)
    return control_class(element=element)


# =============================================================================
# Module-level Search Helper
# =============================================================================

def _find_recursive_raw(
    element: Any,
    results: list[Any],
    role: Optional[str],
    subrole: Optional[str],
    title: Optional[str],
    identifier: Optional[str],
    predicate: Optional[Callable[[Control], bool]],
    max_depth: int,
    current_depth: int,
    find_first: bool,
) -> None:
    """
    Recursive element search helper that collects raw AXUIElementRefs.
    Used by Control.FindAll/FindFirst and the lazy search system.
    The predicate receives a CreateControl-wrapped element for filtering.
    """
    if current_depth > max_depth:
        return
    if find_first and results:
        return

    children = _GetChildren(element)
    for child in children:
        if find_first and results:
            return

        # Read attributes for matching (lightweight; only wrap if predicate needed)
        child_role = GetAttribute(child, Attribute.Role) or ''
        child_subrole = GetAttribute(child, Attribute.Subrole) or '' if subrole else None
        child_title = GetAttribute(child, Attribute.Title) or '' if title else None
        child_identifier = GetAttribute(child, Attribute.Identifier) or '' if identifier else None

        # Apply filters
        match = True
        if role and child_role != role:
            match = False
        if match and subrole and child_subrole != subrole:
            match = False
        if match and title and title not in child_title:
            match = False
        if match and identifier and child_identifier != identifier:
            match = False
        if match and predicate:
            control = CreateControl(child)
            if not predicate(control):
                match = False

        if match and (role or subrole or title or identifier or predicate):
            results.append(child)
            if find_first:
                return

        # Recurse into children
        _find_recursive_raw(
            child, results, role, subrole, title,
            identifier, predicate, max_depth, current_depth + 1, find_first
        )
