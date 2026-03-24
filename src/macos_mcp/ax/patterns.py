"""
macOS Accessibility action-based patterns.
Wraps AXUIElement actions and attributes into pattern-like interfaces
similar to Windows UIA patterns (InvokePattern, ValuePattern, etc.).

On macOS, there are no formal COM pattern interfaces like Windows UIA.
Instead, patterns are logical groupings of related AX actions and attributes
that provide a consistent interaction API.
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from .core import (
    GetAttribute,
    SetAttribute,
    PerformAction,
    IsAttributeSettable,
)
from .enums import (
    Action,
    Attribute,
)

if TYPE_CHECKING:
    from .controls import Control

logger = logging.getLogger(__name__)


class InvokePattern:
    """
    Pattern for invoking (pressing/clicking) elements.
    Equivalent to Windows UIA InvokePattern.

    Applies to: Buttons, links, menu items, and other clickable elements.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    def Invoke(self) -> bool:
        """
        Invoke the element (press/click).
        Returns True if successful.
        """
        return PerformAction(self._element, Action.Press)

    @staticmethod
    def IsSupported(element: Any) -> bool:
        """Check if the element supports the Invoke pattern."""
        from .core import GetActionNames
        actions = GetActionNames(element)
        return Action.Press in actions


class ValuePattern:
    """
    Pattern for getting and setting element values.
    Equivalent to Windows UIA ValuePattern.

    Applies to: Text fields, text areas, sliders, combo boxes.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    @property
    def Value(self):
        """Get the current value."""
        return GetAttribute(self._element, Attribute.Value)

    @Value.setter
    def Value(self, value) -> None:
        """Set the value."""
        SetAttribute(self._element, Attribute.Value, value)

    @property
    def IsReadOnly(self) -> bool:
        """Check if the value is read-only."""
        return not IsAttributeSettable(self._element, Attribute.Value)

    def SetValue(self, value) -> bool:
        """Set the value and return success status."""
        return SetAttribute(self._element, Attribute.Value, value)

    @staticmethod
    def IsSupported(element: Any) -> bool:
        """Check if the element supports the Value pattern."""
        from .core import GetAttributeNames
        return Attribute.Value in GetAttributeNames(element)


class RangeValuePattern:
    """
    Pattern for elements with numeric range values.
    Equivalent to Windows UIA RangeValuePattern.

    Applies to: Sliders, progress indicators, level indicators.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    @property
    def Value(self) -> float:
        """Get the current value."""
        val = GetAttribute(self._element, Attribute.Value)
        try:
            return float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @Value.setter
    def Value(self, value: float) -> None:
        """Set the value."""
        SetAttribute(self._element, Attribute.Value, value)

    @property
    def Minimum(self) -> float:
        """Get the minimum value."""
        val = GetAttribute(self._element, Attribute.MinValue)
        try:
            return float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @property
    def Maximum(self) -> float:
        """Get the maximum value."""
        val = GetAttribute(self._element, Attribute.MaxValue)
        try:
            return float(val) if val is not None else 100.0
        except (TypeError, ValueError):
            return 100.0

    def Increment(self) -> bool:
        """Increment the value."""
        return PerformAction(self._element, Action.Increment)

    def Decrement(self) -> bool:
        """Decrement the value."""
        return PerformAction(self._element, Action.Decrement)

    @staticmethod
    def IsSupported(element: Any) -> bool:
        """Check if the element supports the RangeValue pattern."""
        from .core import GetActionNames
        actions = GetActionNames(element)
        return Action.Increment in actions or Action.Decrement in actions


class TogglePattern:
    """
    Pattern for toggling elements (checkboxes, switches).
    Equivalent to Windows UIA TogglePattern.

    Applies to: Checkboxes, toggle switches.
    """

    def __init__(self, element):
        self._element = element

    @property
    def ToggleState(self) -> int:
        """
        Get the current toggle state.
        Returns: 0 = off, 1 = on, 2 = indeterminate.
        """
        val = GetAttribute(self._element, Attribute.Value)
        if val is None:
            return 0
        if val is True or val == 1:
            return 1
        if val == 2:
            return 2  # indeterminate
        return 0

    @property
    def IsOn(self) -> bool:
        """Check if the toggle is on."""
        return self.ToggleState == 1

    def Toggle(self) -> bool:
        """Toggle the state."""
        return PerformAction(self._element, Action.Press)

    @staticmethod
    def IsSupported(element: Any) -> bool:
        """Check if the element supports the Toggle pattern."""
        from .core import GetAttribute as _GetAttr
        role = _GetAttr(element, Attribute.Role)
        return role in ('AXCheckBox', 'AXToggle', 'AXSwitch')


class ExpandCollapsePattern:
    """
    Pattern for expanding/collapsing elements.
    Equivalent to Windows UIA ExpandCollapsePattern.

    Applies to: Disclosure triangles, outline rows, combo boxes.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    @property
    def IsExpanded(self) -> bool:
        """Check if the element is expanded."""
        val = GetAttribute(self._element, Attribute.Expanded)
        if val is not None:
            return val is True
        # Fallback: check Value for disclosure triangles
        val = GetAttribute(self._element, Attribute.Value)
        return val == 1 or val is True

    def Expand(self) -> bool:
        """Expand the element."""
        if not self.IsExpanded:
            return PerformAction(self._element, Action.Press)
        return True

    def Collapse(self) -> bool:
        """Collapse the element."""
        if self.IsExpanded:
            return PerformAction(self._element, Action.Press)
        return True

    @staticmethod
    def IsSupported(element: Any) -> bool:
        """Check if the element supports the ExpandCollapse pattern."""
        from .core import GetAttributeNames
        attrs = GetAttributeNames(element)
        return Attribute.Expanded in attrs


class ScrollPattern:
    """
    Pattern for scrolling elements.
    Equivalent to Windows UIA ScrollPattern.

    Applies to: Scroll areas, lists, tables.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    @property
    def HorizontalScrollPercent(self) -> float:
        """Get horizontal scroll position (0.0 to 100.0)."""
        h_bar = GetAttribute(self._element, Attribute.HorizontalScrollBar)
        if h_bar:
            val = GetAttribute(h_bar, Attribute.Value)
            if val is not None:
                try:
                    return float(val) * 100.0
                except (TypeError, ValueError):
                    pass
        return 0.0

    @property
    def VerticalScrollPercent(self) -> float:
        """Get vertical scroll position (0.0 to 100.0)."""
        v_bar = GetAttribute(self._element, Attribute.VerticalScrollBar)
        if v_bar:
            val = GetAttribute(v_bar, Attribute.Value)
            if val is not None:
                try:
                    return float(val) * 100.0
                except (TypeError, ValueError):
                    pass
        return 0.0

    @property
    def HorizontallyScrollable(self) -> bool:
        """Check if horizontal scrolling is possible."""
        return GetAttribute(self._element, Attribute.HorizontalScrollBar) is not None

    @property
    def VerticallyScrollable(self) -> bool:
        """Check if vertical scrolling is possible."""
        return GetAttribute(self._element, Attribute.VerticalScrollBar) is not None

    def ScrollByPage(self, direction: str) -> bool:
        """
        Scroll by one page in the given direction.

        Args:
            direction: 'up', 'down', 'left', or 'right'.
        """
        action_map = {
            'up': Action.ScrollUpByPage,
            'down': Action.ScrollDownByPage,
            'left': Action.ScrollLeftByPage,
            'right': Action.ScrollRightByPage,
        }
        action = action_map.get(direction.lower())
        if action:
            return PerformAction(self._element, action)
        return False

    @staticmethod
    def IsSupported(element: Any) -> bool:
        """Check if the element supports the Scroll pattern."""
        h_bar = GetAttribute(element, Attribute.HorizontalScrollBar)
        v_bar = GetAttribute(element, Attribute.VerticalScrollBar)
        return h_bar is not None or v_bar is not None


class SelectionPattern:
    """
    Pattern for elements with selectable children.
    Equivalent to Windows UIA SelectionPattern.

    Applies to: Lists, tables, tab groups.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    @property
    def SelectedChildren(self) -> list[Any]:
        """Get the currently selected children as raw elements."""
        children = GetAttribute(self._element, Attribute.SelectedChildren)
        return list(children) if children else []

    @property
    def SelectedChildControls(self) -> list["Control"]:
        """Get the currently selected children as Control objects."""
        from .controls import Control
        children = GetAttribute(self._element, Attribute.SelectedChildren)
        if children:
            return [Control(element=c) for c in children]
        return []

    @staticmethod
    def IsSupported(element: Any) -> bool:
        """Check if the element supports the Selection pattern."""
        from .core import GetAttributeNames
        return Attribute.SelectedChildren in GetAttributeNames(element)


class WindowPattern:
    """
    Pattern for window management.
    Equivalent to Windows UIA WindowPattern.

    Applies to: Windows.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    @property
    def IsMinimized(self) -> bool:
        """Check if the window is minimized."""
        val = GetAttribute(self._element, Attribute.Minimized)
        return val is True

    @property
    def IsFullScreen(self) -> bool:
        """Check if the window is fullscreen."""
        val = GetAttribute(self._element, Attribute.FullScreen)
        return val is True

    @property
    def IsModal(self) -> bool:
        """Check if the window is modal."""
        val = GetAttribute(self._element, Attribute.Modal)
        return val is True

    def Close(self) -> bool:
        """Close the window."""
        close_btn = GetAttribute(self._element, Attribute.CloseButton)
        if close_btn:
            return PerformAction(close_btn, Action.Press)
        return False

    def Minimize(self) -> bool:
        """Minimize the window."""
        return SetAttribute(self._element, Attribute.Minimized, True)

    def Restore(self) -> bool:
        """Restore a minimized window."""
        return SetAttribute(self._element, Attribute.Minimized, False)

    def Raise(self) -> bool:
        """Bring the window to front."""
        return PerformAction(self._element, Action.Raise)

    @staticmethod
    def IsSupported(element: Any) -> bool:
        """Check if the element supports the Window pattern."""
        from .core import GetAttribute as _GetAttr
        role = _GetAttr(element, Attribute.Role)
        return role == 'AXWindow'


class TextPattern:
    """
    Pattern for text content access.
    Equivalent to Windows UIA TextPattern.

    Applies to: Text fields, text areas, static text.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    @property
    def Text(self) -> str:
        """Get the full text content."""
        val = GetAttribute(self._element, Attribute.Value)
        return str(val) if val is not None else ''

    @property
    def SelectedText(self) -> str:
        """Get the currently selected text."""
        return GetAttribute(self._element, Attribute.SelectedText) or ''

    @property
    def SelectedTextRange(self):
        """Get the selected text range."""
        return GetAttribute(self._element, Attribute.SelectedTextRange)

    @property
    def NumberOfCharacters(self) -> int:
        """Get the total number of characters."""
        val = GetAttribute(self._element, Attribute.NumberOfCharacters)
        return val if val is not None else 0

    @property
    def VisibleCharacterRange(self):
        """Get the visible character range."""
        return GetAttribute(self._element, Attribute.VisibleCharacterRange)

    @property
    def InsertionPointLineNumber(self) -> int:
        """Get the line number of the insertion point."""
        val = GetAttribute(self._element, Attribute.InsertionPointLineNumber)
        return val if val is not None else 0

    @staticmethod
    def IsSupported(element: Any) -> bool:
        """Check if the element supports the Text pattern."""
        from .core import GetAttributeNames
        attrs = GetAttributeNames(element)
        return Attribute.NumberOfCharacters in attrs or Attribute.SelectedText in attrs


# =============================================================================
# Pattern Factory
# =============================================================================

def GetPattern(element, pattern_class):
    """
    Get a pattern for an element if supported.

    Args:
        element: AXUIElementRef.
        pattern_class: Pattern class (e.g., InvokePattern, ValuePattern).

    Returns:
        Pattern instance if supported, None otherwise.
    """
    if pattern_class.IsSupported(element):
        return pattern_class(element)
    return None
