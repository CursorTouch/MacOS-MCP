"""
Core macOS Accessibility API functions.
Provides low-level access to the AX framework, screen management,
mouse/keyboard input simulation, and window management.

Equivalent to the Windows UIA core.py module, adapted for macOS.
Uses native Quartz CGEvent APIs instead of pyautogui for input simulation.
"""

import time
import subprocess
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple, TYPE_CHECKING

import Quartz
from Quartz import (
    CGEventCreateMouseEvent,
    CGEventCreateKeyboardEvent,
    CGEventCreateScrollWheelEvent,
    CGEventPost,
    CGEventSetFlags,
    CGEventSetIntegerValueField,
    CGEventKeyboardSetUnicodeString,
    kCGHIDEventTap,
    kCGEventMouseMoved,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventLeftMouseDragged,
    kCGEventRightMouseDown,
    kCGEventRightMouseUp,
    kCGEventOtherMouseDown,
    kCGEventOtherMouseUp,
    kCGScrollEventUnitPixel,
    kCGScrollEventUnitLine,
    kCGMouseButtonLeft,
    kCGMouseButtonRight,
    kCGMouseButtonCenter,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskControl,
    CGMainDisplayID,
    CGDisplayPixelsWide,
    CGDisplayPixelsHigh,
    CGDisplayBounds,
    CGGetActiveDisplayList,
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGWindowListExcludeDesktopElements,
    kCGNullWindowID,
    CGRectInfinite,
    kCGWindowImageDefault,
    kCGWindowListOptionAll,
)
from Quartz.CoreGraphics import (
    CGImageGetWidth,
    CGImageGetHeight,
    CGImageGetBytesPerRow,
    CGDataProviderCopyData,
    CGImageGetDataProvider,
)
from ApplicationServices import (
    AXUIElementCreateSystemWide,
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXUIElementCopyAttributeValues,
    AXUIElementCopyAttributeNames,
    AXUIElementSetAttributeValue,
    AXUIElementPerformAction,
    AXUIElementGetAttributeValueCount,
    AXUIElementCopyActionNames,
    AXUIElementCopyActionDescription,
    AXUIElementIsAttributeSettable,
    AXUIElementCopyElementAtPosition,
    AXUIElementCopyMultipleAttributeValues,
    AXUIElementGetPid,
    AXUIElementSetMessagingTimeout,
    AXIsProcessTrusted,
    AXIsProcessTrustedWithOptions,
    kAXErrorSuccess,
    kAXCopyMultipleAttributeOptionStopOnError,
)
from Cocoa import NSWorkspace

if TYPE_CHECKING:
    from macos_mcp.ax.controls import ApplicationControl, Control, WindowControl

from .enums import (
    AXError,
    AXValueType,
    Attribute,
    KeyCode,
    KEY_NAME_TO_CODE,
    MODIFIER_KEY_MAP,
)

logger = logging.getLogger(__name__)

# Track messaging timeouts locally since macOS has no public getter API
_messaging_timeouts: dict[Any, float] = {}


# =============================================================================
# Geometry Data Classes
# =============================================================================

@dataclass
class Rect:
    """
    Rectangle representing a UI element's bounds.
    Equivalent to Windows UIA RECT.
    """
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def center(self) -> Tuple[float, float]:
        return (
            self.left + self.width / 2,
            self.top + self.height / 2,
        )

    @classmethod
    def from_position_size(cls, x: float, y: float, w: float, h: float) -> 'Rect':
        return cls(left=x, top=y, right=x + w, bottom=y + h)

    def intersects(self, other: 'Rect') -> bool:
        return not (
            self.right < other.left or
            self.left > other.right or
            self.bottom < other.top or
            self.top > other.bottom
        )

    def intersection(self, other: 'Rect') -> Optional['Rect']:
        new_left = max(self.left, other.left)
        new_top = max(self.top, other.top)
        new_right = min(self.right, other.right)
        new_bottom = min(self.bottom, other.bottom)
        if new_left < new_right and new_top < new_bottom:
            return Rect(left=new_left, top=new_top, right=new_right, bottom=new_bottom)
        return None

    def __str__(self) -> str:
        return f'Rect(left={int(self.left)}, top={int(self.top)}, right={int(self.right)}, bottom={int(self.bottom)})'


@dataclass
class Point:
    """A 2D point in screen coordinates."""
    x: float
    y: float

    def __str__(self) -> str:
        return f'({int(self.x)}, {int(self.y)})'


@dataclass
class Size:
    """A 2D size."""
    width: float
    height: float

    def __str__(self) -> str:
        return f'({int(self.width)}, {int(self.height)})'


# =============================================================================
# AX Client Singleton
# =============================================================================

class _AXClient:
    """
    Singleton providing access to the macOS Accessibility API.
    Equivalent to Windows UIA _AutomationClient.
    """
    _instance: Optional['_AXClient'] = None

    @classmethod
    def instance(cls) -> '_AXClient':
        """Get or create the singleton AX client instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._system_wide = AXUIElementCreateSystemWide()
        self._is_trusted = AXIsProcessTrusted()
        if not self._is_trusted:
            logger.warning(
                "Accessibility access is not granted. "
                "Enable it in System Settings > Privacy & Security > Accessibility."
            )

    @property
    def system_wide(self):
        """Get the system-wide accessibility element."""
        return self._system_wide

    @property
    def is_trusted(self) -> bool:
        """Check if the process has accessibility permissions."""
        return self._is_trusted


# =============================================================================
# Element Creation Functions
# =============================================================================

def GetRootControl() -> Any:
    """
    Get the system-wide root accessibility element.
    Equivalent to Windows UIA GetRootControl().
    """
    return _AXClient.instance().system_wide


def ControlFromPID(pid: int) -> Any:
    """
    Create an accessibility element for the application with the given PID.
    Equivalent to Windows UIA ControlFromHandle().
    """
    return AXUIElementCreateApplication(pid)


def IsAccessibilityEnabled() -> bool:
    """Check if accessibility access has been granted for this process."""
    return AXIsProcessTrusted()


def IsAccessibilityEnabledWithPrompt() -> bool:
    """
    Check if accessibility access has been granted, prompting the user if not.
    Opens the System Settings > Privacy & Security > Accessibility pane
    if the process is not yet trusted.

    Returns True if the process is trusted.
    """
    from CoreFoundation import CFDictionaryCreate, kCFBooleanTrue
    options = {
        'AXTrustedCheckOptionPrompt': kCFBooleanTrue,
    }
    return AXIsProcessTrustedWithOptions(options)


# =============================================================================
# Attribute Access Helpers
# =============================================================================

def GetAttribute(element: Any, attribute: str) -> Optional[Any]:
    """
    Get an attribute value from an AXUIElement.
    Returns None if the attribute is not available or an error occurs.
    """
    try:
        error, value = AXUIElementCopyAttributeValue(element, attribute, None)
        if error == kAXErrorSuccess:
            return value
    except Exception:
        pass
    return None


def SetAttribute(element: Any, attribute: str, value: Any) -> bool:
    """
    Set an attribute value on an AXUIElement.
    Returns True if successful.
    """
    try:
        error = AXUIElementSetAttributeValue(element, attribute, value)
        return error == kAXErrorSuccess
    except Exception:
        return False


def IsAttributeSettable(element: Any, attribute: str) -> bool:
    """Check if an attribute can be set on an element."""
    try:
        error, settable = AXUIElementIsAttributeSettable(element, attribute, None)
        if error == kAXErrorSuccess:
            return bool(settable)
    except Exception:
        pass
    return False


def GetAttributeNames(element: Any) -> list[str]:
    """Get all attribute names supported by an element."""
    try:
        error, names = AXUIElementCopyAttributeNames(element, None)
        if error == kAXErrorSuccess and names:
            return list(names)
    except Exception:
        pass
    return []


def GetActionNames(element: Any) -> list[str]:
    """Get all action names supported by an element."""
    try:
        error, names = AXUIElementCopyActionNames(element, None)
        if error == kAXErrorSuccess and names:
            return list(names)
    except Exception:
        pass
    return []


def PerformAction(element: Any, action: str) -> bool:
    """
    Perform an action on an AXUIElement.
    Returns True if successful.
    """
    try:
        error = AXUIElementPerformAction(element, action)
        return error == kAXErrorSuccess
    except Exception:
        return False


def GetChildCount(element: Any) -> int:
    """Get the number of children of an element."""
    try:
        error, count = AXUIElementGetAttributeValueCount(element, Attribute.Children, None)
        if error == kAXErrorSuccess:
            return count
    except Exception:
        pass
    return 0


def GetChildren(element: Any) -> list[Any]:
    """Get child elements of an accessibility element."""
    try:
        error, count = AXUIElementGetAttributeValueCount(element, Attribute.Children, None)
        if error != kAXErrorSuccess or count == 0:
            return []
        error, children = AXUIElementCopyAttributeValue(element, Attribute.Children, None)
        if error == kAXErrorSuccess and children:
            return list(children)
    except Exception:
        pass
    return []


def GetPosition(element: Any) -> Optional[Tuple[float, float]]:
    """Get the position (x, y) of an accessibility element in screen coordinates."""
    error, pos_val = AXUIElementCopyAttributeValue(element, Attribute.Position, None)
    if error != kAXErrorSuccess or pos_val is None:
        return None

    # Try standard attribute access (bridged CGPoint/NSPoint)
    if hasattr(pos_val, 'x') and hasattr(pos_val, 'y'):
        return (pos_val.x, pos_val.y)

    # Try AXValueGetValue for proper AXValueRef extraction
    try:
        from ApplicationServices import AXValueGetValue
        success, point = AXValueGetValue(pos_val, AXValueType.CGPoint, None)
        if success and point is not None:
            if hasattr(point, 'x') and hasattr(point, 'y'):
                return (point.x, point.y)
    except Exception:
        pass

    # Try AXValue string parsing (fallback)
    if hasattr(pos_val, 'getValue_size_type_') or str(pos_val).startswith('<AXValue'):
        desc = str(pos_val)
        try:
            match = re.search(r'x[:=]\s*([-\d\.]+).*?y[:=]\s*([-\d\.]+)', desc, re.IGNORECASE)
            if match:
                return (float(match.group(1)), float(match.group(2)))
        except Exception:
            pass

    # Try generic sequence access
    try:
        if len(pos_val) == 2:
            return (pos_val[0], pos_val[1])
    except Exception:
        pass

    return None


def GetSize(element: Any) -> Optional[Tuple[float, float]]:
    """Get the size (width, height) of an accessibility element."""
    error, size_val = AXUIElementCopyAttributeValue(element, Attribute.Size, None)
    if error != kAXErrorSuccess or size_val is None:
        return None

    # Try standard attribute access (bridged CGSize/NSSize)
    if hasattr(size_val, 'width') and hasattr(size_val, 'height'):
        return (size_val.width, size_val.height)

    # Try AXValueGetValue for proper AXValueRef extraction
    try:
        from ApplicationServices import AXValueGetValue
        success, size = AXValueGetValue(size_val, AXValueType.CGSize, None)
        if success and size is not None:
            if hasattr(size, 'width') and hasattr(size, 'height'):
                return (size.width, size.height)
    except Exception:
        pass

    # Try generic sequence access
    try:
        if len(size_val) == 2:
            return (size_val[0], size_val[1])
    except Exception:
        pass

    # Try AXValue string parsing (fallback)
    if hasattr(size_val, 'getValue_size_type_') or str(size_val).startswith('<AXValue'):
        desc = str(size_val)
        try:
            match = re.search(r'w(idth)?[:=]\s*([-\d\.]+).*?h(eight)?[:=]\s*([-\d\.]+)', desc, re.IGNORECASE)
            if match:
                return (float(match.group(2)), float(match.group(4)))
        except Exception:
            pass

    return None


def GetRect(element: Any) -> Optional[Rect]:
    """Get the bounding rectangle of an accessibility element."""
    pos = GetPosition(element)
    size = GetSize(element)
    if pos and size:
        return Rect.from_position_size(pos[0], pos[1], size[0], size[1])
    return None


def ElementAtPosition(application, x: float, y: float):
    """
    Get the accessibility element at the specified screen coordinates.
    Wraps AXUIElementCopyElementAtPosition.

    Args:
        application: An AXUIElementRef (typically system-wide or application element).
        x: X coordinate in screen space.
        y: Y coordinate in screen space.

    Returns:
        The AXUIElementRef at the position, or None if not found.
    """
    try:
        error, element = AXUIElementCopyElementAtPosition(application, x, y, None)
        if error == kAXErrorSuccess and element:
            return element
    except Exception:
        pass
    return None


def GetElementPid(element: Any) -> Optional[int]:
    """
    Get the process ID of the application that owns the given element.
    Wraps AXUIElementGetPid.

    Args:
        element: An AXUIElementRef.

    Returns:
        The PID of the owning application, or None on error.
    """
    try:
        error, pid = AXUIElementGetPid(element, None)
        if error == kAXErrorSuccess:
            return pid
    except Exception:
        pass
    return None


def GetMultipleAttributeValues(
    element: Any,
    attributes: Sequence[str],
    stop_on_error: bool = False,
) -> dict[str, Any]:
    """
    Get multiple attribute values in a single call for better performance.
    Wraps AXUIElementCopyMultipleAttributeValues.

    Args:
        element: An AXUIElementRef.
        attributes: List of attribute name strings (e.g., [Attribute.Role, Attribute.Title]).
        stop_on_error: If True, stops fetching when an error is encountered.

    Returns:
        Dictionary mapping attribute names to their values.
        Attributes with errors are omitted.
    """
    try:
        options = kAXCopyMultipleAttributeOptionStopOnError if stop_on_error else 0
        error, values = AXUIElementCopyMultipleAttributeValues(
            element, attributes, options, None
        )
        if error == kAXErrorSuccess and values:
            result = {}
            for attr, val in zip(attributes, values):
                # AXUIElementCopyMultipleAttributeValues returns kAXErrorSuccess
                # per-attribute errors are represented as AXError values in the array
                if not isinstance(val, int) or val >= 0:
                    result[attr] = val
            return result
    except Exception:
        pass
    return {}


def GetAttributeValues(
    element: Any, attribute: str, index: int, max_values: int
) -> list[Any]:
    """
    Get a range of values for an array attribute (paginated access).
    Wraps AXUIElementCopyAttributeValues.

    Args:
        element: An AXUIElementRef.
        attribute: Attribute name (e.g., Attribute.Children).
        index: Starting index.
        max_values: Maximum number of values to return.

    Returns:
        List of attribute values, or empty list on error.
    """
    try:
        error, values = AXUIElementCopyAttributeValues(
            element, attribute, index, max_values, None
        )
        if error == kAXErrorSuccess and values:
            return list(values)
    except Exception:
        pass
    return []


def GetActionDescription(element: Any, action: str) -> str:
    """
    Get a localized description of a specific action.
    Wraps AXUIElementCopyActionDescription.

    Args:
        element: An AXUIElementRef.
        action: Action name (e.g., Action.Press).

    Returns:
        Localized description string, or empty string on error.
    """
    try:
        error, description = AXUIElementCopyActionDescription(element, action, None)
        if error == kAXErrorSuccess and description:
            return str(description)
    except Exception:
        pass
    return ''


def SetMessagingTimeout(element: Any, timeout: float) -> bool:
    """
    Set the messaging timeout for an accessibility element.
    Controls how long the API waits for a response from the target application.
    Wraps AXUIElementSetMessagingTimeout.

    Args:
        element: An AXUIElementRef.
        timeout: Timeout in seconds (0 resets to default).

    Returns:
        True if successful.
    """
    try:
        error = AXUIElementSetMessagingTimeout(element, timeout)
        if error == kAXErrorSuccess:
            _messaging_timeouts[id(element)] = timeout
            return True
    except Exception:
        pass
    return False


def GetMessagingTimeout(element: Any) -> Optional[float]:
    """
    Get the current messaging timeout for an accessibility element.
    Note: macOS has no public API to retrieve this value, so we return
    the last value set via SetMessagingTimeout, or None if never set.

    Args:
        element: An AXUIElementRef.

    Returns:
        Timeout in seconds, or None if not previously set.
    """
    return _messaging_timeouts.get(id(element))


# =============================================================================
# Screen Functions
# =============================================================================

def GetScreenSize() -> Tuple[int, int]:
    """
    Get the combined resolution of all active displays (virtual screen size).
    Returns (width, height).
    Equivalent to Windows GetSystemMetrics.
    """
    try:
        max_displays = 32
        res = CGGetActiveDisplayList(max_displays, None, None)
        if res and res[1]:
            display_ids = res[1]
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')
            for display_id in display_ids:
                bounds = CGDisplayBounds(display_id)
                x = bounds.origin.x
                y = bounds.origin.y
                w = bounds.size.width
                h = bounds.size.height
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x + w)
                max_y = max(max_y, y + h)
            return (int(max_x - min_x), int(max_y - min_y))
    except Exception as e:
        logger.warning(f"Failed to calculate virtual screen size: {e}")

    # Fallback to main display
    main_display = CGMainDisplayID()
    width = CGDisplayPixelsWide(main_display)
    height = CGDisplayPixelsHigh(main_display)
    return (width, height)


def GetMainDisplaySize() -> Tuple[int, int]:
    """Get the resolution of the main display. Returns (width, height)."""
    main_display = CGMainDisplayID()
    return (CGDisplayPixelsWide(main_display), CGDisplayPixelsHigh(main_display))


def GetDisplayCount() -> int:
    """Get the number of active displays."""
    try:
        res = CGGetActiveDisplayList(32, None, None)
        if res and res[1]:
            return len(res[1])
    except Exception:
        pass
    return 1


def GetDisplayBounds() -> list[Rect]:
    """Get the bounding rectangles of all active displays."""
    rects = []
    try:
        res = CGGetActiveDisplayList(32, None, None)
        if res and res[1]:
            for display_id in res[1]:
                bounds = CGDisplayBounds(display_id)
                rects.append(Rect(
                    left=bounds.origin.x,
                    top=bounds.origin.y,
                    right=bounds.origin.x + bounds.size.width,
                    bottom=bounds.origin.y + bounds.size.height,
                ))
    except Exception:
        pass
    return rects


def GetDPIScale() -> float:
    """
    Get the DPI scale factor of the main display.
    Returns 2.0 for Retina displays, 1.0 for standard.
    """
    try:
        main_display = CGMainDisplayID()
        pixel_width = CGDisplayPixelsWide(main_display)
        bounds = CGDisplayBounds(main_display)
        point_width = bounds.size.width
        if point_width > 0:
            return round(pixel_width / point_width, 1)
    except Exception:
        pass
    return 1.0


# =============================================================================
# Screenshot Functions
# =============================================================================

def CaptureScreen(rect=None):
    """
    Capture a screenshot of the screen.
    Returns a CGImage, or None on failure.

    Args:
        rect: Optional Quartz CGRect to capture. If None, captures entire screen.
    """
    try:
        capture_rect = rect if rect is not None else CGRectInfinite
        cg_image = Quartz.CGWindowListCreateImage(
            capture_rect,
            kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID,
            kCGWindowImageDefault,
        )
        return cg_image
    except Exception as e:
        logger.error(f"Screenshot capture failed: {e}")
        return None


def CGImageToPIL(cg_image):
    """
    Convert a CGImage to a PIL Image.
    Requires Pillow to be installed.
    """
    from PIL import Image
    width = CGImageGetWidth(cg_image)
    height = CGImageGetHeight(cg_image)
    bytes_per_row = CGImageGetBytesPerRow(cg_image)
    pixel_data = CGDataProviderCopyData(CGImageGetDataProvider(cg_image))
    return Image.frombuffer(
        "RGBA", (width, height), pixel_data, "raw", "BGRA", bytes_per_row, 1
    )


# =============================================================================
# Mouse Functions
# =============================================================================

def GetCursorPos() -> Tuple[int, int]:
    """
    Get the current mouse cursor position.
    Returns (x, y) in screen coordinates.
    """
    event = Quartz.CGEventCreate(None)
    point = Quartz.CGEventGetLocation(event)
    return (int(point.x), int(point.y))


def SetCursorPos(x: int, y: int) -> None:
    """
    Move the mouse cursor to the specified position.
    Equivalent to Windows SetCursorPos.
    """
    event = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, event)


def MoveTo(x: int, y: int) -> None:
    """Move the mouse cursor to the specified coordinates."""
    SetCursorPos(x, y)


def Click(x: int, y: int, waitTime: float = 0.05) -> None:
    """
    Perform a left mouse click at the specified coordinates.
    Equivalent to Windows UIA Click().
    """
    event_down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (x, y), kCGMouseButtonLeft)
    event_up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (x, y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, event_down)
    time.sleep(waitTime)
    CGEventPost(kCGHIDEventTap, event_up)


def RightClick(x: int, y: int, waitTime: float = 0.05) -> None:
    """Perform a right mouse click at the specified coordinates."""
    event_down = CGEventCreateMouseEvent(None, kCGEventRightMouseDown, (x, y), kCGMouseButtonRight)
    event_up = CGEventCreateMouseEvent(None, kCGEventRightMouseUp, (x, y), kCGMouseButtonRight)
    CGEventPost(kCGHIDEventTap, event_down)
    time.sleep(waitTime)
    CGEventPost(kCGHIDEventTap, event_up)


def MiddleClick(x: int, y: int, waitTime: float = 0.05) -> None:
    """Perform a middle mouse click at the specified coordinates."""
    event_down = CGEventCreateMouseEvent(None, kCGEventOtherMouseDown, (x, y), kCGMouseButtonCenter)
    event_up = CGEventCreateMouseEvent(None, kCGEventOtherMouseUp, (x, y), kCGMouseButtonCenter)
    CGEventPost(kCGHIDEventTap, event_down)
    time.sleep(waitTime)
    CGEventPost(kCGHIDEventTap, event_up)


def DoubleClick(x: int, y: int, waitTime: float = 0.05) -> None:
    """Perform a double left-click at the specified coordinates."""
    event_down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (x, y), kCGMouseButtonLeft)
    CGEventSetIntegerValueField(event_down, Quartz.kCGMouseEventClickState, 2)
    event_up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (x, y), kCGMouseButtonLeft)
    CGEventSetIntegerValueField(event_up, Quartz.kCGMouseEventClickState, 2)
    CGEventPost(kCGHIDEventTap, event_down)
    time.sleep(waitTime)
    CGEventPost(kCGHIDEventTap, event_up)


def DragTo(start_x: int, start_y: int, end_x: int, end_y: int,
           duration: float = 0.5, steps: int = 20) -> None:
    """
    Perform a mouse drag from start to end position.
    """
    # Mouse down at start
    event_down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (start_x, start_y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, event_down)
    time.sleep(0.05)

    # Smooth drag
    step_delay = duration / steps
    for i in range(1, steps + 1):
        progress = i / steps
        cx = start_x + (end_x - start_x) * progress
        cy = start_y + (end_y - start_y) * progress
        event_drag = CGEventCreateMouseEvent(None, kCGEventLeftMouseDragged, (cx, cy), kCGMouseButtonLeft)
        CGEventPost(kCGHIDEventTap, event_drag)
        time.sleep(step_delay)

    # Mouse up at end
    event_up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (end_x, end_y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, event_up)


def WheelDown(clicks: int = 1, interval: float = 0.05) -> None:
    """
    Scroll down by the specified number of clicks.
    Equivalent to Windows mouse_event with WHEEL.
    """
    for _ in range(clicks):
        event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 1, -3)
        CGEventPost(kCGHIDEventTap, event)
        time.sleep(interval)


def WheelUp(clicks: int = 1, interval: float = 0.05) -> None:
    """Scroll up by the specified number of clicks."""
    for _ in range(clicks):
        event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 1, 3)
        CGEventPost(kCGHIDEventTap, event)
        time.sleep(interval)


def WheelLeft(clicks: int = 1, interval: float = 0.05) -> None:
    """Scroll left by the specified number of clicks."""
    for _ in range(clicks):
        event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 2, 0, 3)
        CGEventPost(kCGHIDEventTap, event)
        time.sleep(interval)


def WheelRight(clicks: int = 1, interval: float = 0.05) -> None:
    """Scroll right by the specified number of clicks."""
    for _ in range(clicks):
        event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 2, 0, -3)
        CGEventPost(kCGHIDEventTap, event)
        time.sleep(interval)


# =============================================================================
# Keyboard Functions
# =============================================================================

def KeyDown(key_code: int, flags: int = 0) -> None:
    """
    Press a key down.

    Args:
        key_code: Virtual key code from KeyCode class.
        flags: Modifier flags from EventFlag class (0 = no modifiers).
    """
    event = CGEventCreateKeyboardEvent(None, key_code, True)
    # Always set flags explicitly — CGEventCreateKeyboardEvent(None, ...)
    # inherits the current system modifier state, so we must override it
    # even when flags=0 to prevent stale modifiers from leaking through.
    CGEventSetFlags(event, flags)
    CGEventPost(kCGHIDEventTap, event)


def KeyUp(key_code: int, flags: int = 0) -> None:
    """Release a key."""
    event = CGEventCreateKeyboardEvent(None, key_code, False)
    # Always clear/set flags explicitly to prevent modifier leakage.
    CGEventSetFlags(event, flags)
    CGEventPost(kCGHIDEventTap, event)


def KeyPress(key_code: int, flags: int = 0, waitTime: float = 0.05) -> None:
    """Press and release a key."""
    KeyDown(key_code, flags)
    time.sleep(waitTime)
    KeyUp(key_code, flags)


def HotKey(*keys: str, waitTime: float = 0.05) -> None:
    """
    Press a keyboard shortcut using key names.
    Example: HotKey('command', 'c') for Cmd+C.

    Args:
        keys: Key names (e.g., 'command', 'shift', 'a').
        waitTime: Delay between key down and key up.
    """
    # Build modifier flags and find the main key
    flags = 0
    main_key_code = None

    for key in keys:
        key_lower = key.lower().strip()
        if key_lower in MODIFIER_KEY_MAP:
            flags |= MODIFIER_KEY_MAP[key_lower]
        elif key_lower in KEY_NAME_TO_CODE:
            main_key_code = KEY_NAME_TO_CODE[key_lower]
        else:
            logger.warning(f"Unknown key: {key}")

    if main_key_code is not None:
        KeyPress(main_key_code, flags, waitTime)
    elif flags:
        # Only modifiers pressed (e.g., just pressing Command)
        # Press and release each modifier
        for key in keys:
            key_lower = key.lower().strip()
            if key_lower in KEY_NAME_TO_CODE:
                KeyDown(KEY_NAME_TO_CODE[key_lower])
        time.sleep(waitTime)
        for key in reversed(keys):
            key_lower = key.lower().strip()
            if key_lower in KEY_NAME_TO_CODE:
                KeyUp(KEY_NAME_TO_CODE[key_lower])


def _release_modifiers() -> None:
    """
    Release all modifier keys to ensure a clean keyboard state.

    This prevents stale modifier flags (e.g. from a preceding HotKey call)
    from leaking into subsequent key events. Sends explicit key-up events
    for Command, Shift, Option, and Control on both left and right sides.
    """
    modifier_keycodes = [
        KeyCode.Command, KeyCode.Shift, KeyCode.Option, KeyCode.Control,
        KeyCode.RightCommand, KeyCode.RightShift, KeyCode.RightOption, KeyCode.RightControl,
    ]
    for kc in modifier_keycodes:
        event = CGEventCreateKeyboardEvent(None, kc, False)
        CGEventSetFlags(event, 0)
        CGEventPost(kCGHIDEventTap, event)


def TypeText(text: str, interval: float = 0.01) -> None:
    """
    Type a string of text using native CGEvent keyboard events.
    Uses CGEventKeyboardSetUnicodeString for natural text input that
    supports all Unicode scripts (Hindi, Chinese, Arabic, etc.)
    without touching the system clipboard.

    Each character is typed as an individual key-down/key-up pair,
    simulating real keystrokes. For ASCII characters with known key
    codes, real virtual key events are generated. For all other
    characters (Unicode), CGEventKeyboardSetUnicodeString is used to
    inject the character directly into the keyboard event stream.

    Args:
        text: The text to type.
        interval: Delay between keystrokes in seconds.
    """
    if not text:
        return

    # Release all modifier keys before typing to ensure no stale
    # Command/Shift/Option/Control state leaks into the key events.
    # This is critical after HotKey calls (e.g. Cmd+A for select-all)
    # which may leave the system thinking a modifier is still held.
    _release_modifiers()
    time.sleep(0.02)

    for char in text:
        _type_character(char, interval)


def _type_character(char: str, interval: float = 0.01) -> None:
    """
    Type a single character using CGEvent keyboard simulation.

    For ASCII characters with known virtual key codes, generates real
    key press events (most natural for applications). For everything
    else, uses CGEventKeyboardSetUnicodeString to inject the character
    natively without clipboard involvement.
    """
    key_lower = char.lower()
    if key_lower in KEY_NAME_TO_CODE:
        key_code = KEY_NAME_TO_CODE[key_lower]
        flags = 0
        # Apply shift for uppercase letters
        if char.isupper():
            flags = kCGEventFlagMaskShift
        KeyPress(key_code, flags, interval)
    elif char == ' ':
        KeyPress(KeyCode.Space, 0, interval)
    elif char == '\n':
        KeyPress(KeyCode.Return, 0, interval)
    elif char == '\t':
        KeyPress(KeyCode.Tab, 0, interval)
    else:
        # Unicode character — use CGEventKeyboardSetUnicodeString
        _type_unicode_char(char)
        time.sleep(interval)


def _type_unicode_char(char: str) -> None:
    """
    Type a Unicode character using CGEventKeyboardSetUnicodeString.

    This injects the character directly into the keyboard event stream
    without touching the clipboard. Works with any Unicode script:
    Devanagari (Hindi), CJK (Chinese/Japanese/Korean), Arabic, Cyrillic,
    emoji, and all other Unicode characters.

    The character is encoded as UTF-16 (macOS native UniChar format) and
    attached to a CGEvent keyboard event pair (key-down + key-up).
    """
    # Encode to UTF-16LE to get the UniChar representation
    # Each UniChar is 2 bytes; surrogate pairs (e.g. emoji) produce 2 UniChars
    utf16_bytes = char.encode('utf-16-le')
    utf16_length = len(utf16_bytes) // 2  # Number of UniChar code units

    # Key down event with the Unicode string attached
    # Use key code 0 as a placeholder — the actual character comes from
    # CGEventKeyboardSetUnicodeString, not from the virtual key code.
    event_down = CGEventCreateKeyboardEvent(None, 0, True)
    CGEventSetFlags(event_down, 0)  # Explicitly clear all modifier flags
    CGEventKeyboardSetUnicodeString(event_down, utf16_length, char)
    CGEventPost(kCGHIDEventTap, event_down)

    # Key up event (completes the keystroke pair)
    event_up = CGEventCreateKeyboardEvent(None, 0, False)
    CGEventSetFlags(event_up, 0)  # Explicitly clear all modifier flags
    CGEventPost(kCGHIDEventTap, event_up)


# =============================================================================
# Window Functions
# =============================================================================

def GetWindowList(on_screen_only: bool = True) -> list["ApplicationControl"]:
    """
    Get list of window info dictionaries from the window server.
    Returns raw CGWindowListCopyWindowInfo results.
    """
    options = kCGWindowListOptionOnScreenOnly if on_screen_only else kCGWindowListOptionAll
    if on_screen_only:
        options |= kCGWindowListExcludeDesktopElements
    window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
    return list(window_list) if window_list else []


def GetForegroundWindowPID() -> Optional[int]:
    """
    Get the PID of the frontmost application using CGWindowListCopyWindowInfo.
    More reliable than NSWorkspace when no NSRunLoop is active.
    Equivalent to Windows GetForegroundWindow().
    """
    window_list = CGWindowListCopyWindowInfo(
        kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
        kCGNullWindowID
    )
    if not window_list:
        return None

    for win_info in window_list:
        # Normal windows live at layer 0
        layer = win_info.get(Quartz.kCGWindowLayer, -1)
        if layer != 0:
            continue
        pid = win_info.get(Quartz.kCGWindowOwnerPID, 0)
        if pid:
            return pid
    return None


def _GetRunningApplicationsRaw() -> list[Any]:
    """Get all running applications from NSWorkspace (raw NSRunningApplication objects)."""
    return list(NSWorkspace.sharedWorkspace().runningApplications())


def _GetFrontmostApplicationRaw() -> Any:
    """Get the frontmost application from NSWorkspace (raw NSRunningApplication)."""
    return NSWorkspace.sharedWorkspace().frontmostApplication()


def ActivateApplication(pid: int) -> bool:
    """
    Activate (bring to front) an application by PID.
    """
    from Cocoa import NSApplicationActivateIgnoringOtherApps
    workspace = NSWorkspace.sharedWorkspace()
    for app in workspace.runningApplications():
        if app.processIdentifier() == pid:
            return app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    return False


def LaunchApplication(name: str) -> bool:
    """
    Launch an application by name.
    Returns True if successful.
    """
    try:
        subprocess.run(['open', '-a', name], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        pass

    # Fallback to NSWorkspace
    workspace = NSWorkspace.sharedWorkspace()
    return workspace.launchApplication_(name)


def HideOtherApplications() -> None:
    """
    Hide all applications except the current one.
    Equivalent to the Option+Cmd+H shortcut.
    """
    NSWorkspace.sharedWorkspace().hideOtherApplications()


def GetMenuBarOwningApplication() -> Optional[int]:
    """
    Get the PID of the application that currently owns the menu bar.

    Returns:
        PID of the menu bar owning application, or None.
    """
    try:
        app = NSWorkspace.sharedWorkspace().menuBarOwningApplication()
        if app:
            return app.processIdentifier()
    except Exception:
        pass
    return None


def GetApplicationPathByName(name: str) -> Optional[str]:
    """
    Get the full filesystem path of an application by its name.
    Example: GetApplicationPathByName('Safari') -> '/Applications/Safari.app'

    Args:
        name: Application name (e.g., 'Safari', 'Google Chrome').

    Returns:
        Full path to the .app bundle, or None if not found.
    """
    workspace = NSWorkspace.sharedWorkspace()
    path = workspace.fullPathForApplication_(name)
    return str(path) if path else None


def GetApplicationPathByBundleID(bundle_id: str) -> Optional[str]:
    """
    Get the full filesystem path of an application by its bundle identifier.
    Example: GetApplicationPathByBundleID('com.apple.Safari') -> '/Applications/Safari.app'

    Args:
        bundle_id: CFBundleIdentifier (e.g., 'com.apple.Safari').

    Returns:
        URL string to the .app bundle, or None if not found.
    """
    workspace = NSWorkspace.sharedWorkspace()
    try:
        url = workspace.URLForApplicationWithBundleIdentifier_(bundle_id)
        return str(url) if url else None
    except Exception:
        return None


# =============================================================================
# Workspace: File & URL Operations
# =============================================================================

def OpenFile(path: str, application: Optional[str] = None) -> bool:
    """
    Open a file, optionally with a specific application.
    If no application is specified, the default handler is used.

    Args:
        path: Full path to the file to open.
        application: Optional application name (e.g., 'TextEdit').

    Returns:
        True if the file was opened successfully.
    """
    workspace = NSWorkspace.sharedWorkspace()
    if application:
        return bool(workspace.openFile_withApplication_(path, application))
    return bool(workspace.openFile_(path))


def OpenURL(url_string: str) -> bool:
    """
    Open a URL with the default handler application.
    Works with http/https URLs, mailto: links, custom URL schemes, etc.

    Args:
        url_string: URL to open (e.g., 'https://apple.com', 'mailto:user@example.com').

    Returns:
        True if the URL was opened successfully.
    """
    from Cocoa import NSURL
    workspace = NSWorkspace.sharedWorkspace()
    url = NSURL.URLWithString_(url_string)
    if url:
        return bool(workspace.openURL_(url))
    return False


def SelectFileInFinder(path: str) -> bool:
    """
    Reveal and select a file in Finder.
    Equivalent to right-click -> 'Show in Finder'.

    Args:
        path: Full path to the file to reveal.

    Returns:
        True if the file was revealed successfully.
    """
    workspace = NSWorkspace.sharedWorkspace()
    return bool(workspace.selectFile_inFileViewerRootedAtPath_(path, ''))


def RecycleFiles(paths: Sequence[str]) -> bool:
    """
    Move files to the Trash.

    Args:
        paths: List of full file paths to trash.

    Returns:
        True if the operation was initiated (actual completion is async).
    """
    from Cocoa import NSURL
    workspace = NSWorkspace.sharedWorkspace()
    urls = [NSURL.fileURLWithPath_(p) for p in paths]
    try:
        workspace.recycleURLs_completionHandler_(urls, None)
        return True
    except Exception:
        return False


def DuplicateFiles(paths: Sequence[str]) -> bool:
    """
    Duplicate files in the Finder.

    Args:
        paths: List of full file paths to duplicate.

    Returns:
        True if the operation was initiated (actual completion is async).
    """
    from Cocoa import NSURL
    workspace = NSWorkspace.sharedWorkspace()
    urls = [NSURL.fileURLWithPath_(p) for p in paths]
    try:
        workspace.duplicateURLs_completionHandler_(urls, None)
        return True
    except Exception:
        return False


def IsFilePackage(path: str) -> bool:
    """
    Check if a path points to a file package (e.g., .app bundle, .pages document).

    Args:
        path: Full path to check.

    Returns:
        True if the path is a file package.
    """
    workspace = NSWorkspace.sharedWorkspace()
    return bool(workspace.isFilePackageAtPath_(path))


# =============================================================================
# Workspace: Icons
# =============================================================================

def GetIconForFile(path: str) -> Optional[Any]:
    """
    Get the icon for a file at the given path.

    Args:
        path: Full path to the file.

    Returns:
        NSImage of the file's icon, or None on error.
    """
    try:
        workspace = NSWorkspace.sharedWorkspace()
        return workspace.iconForFile_(path)
    except Exception:
        return None


def GetIconForFileType(file_type: str) -> Optional[Any]:
    """
    Get the icon for a file type or UTI.

    Args:
        file_type: File extension (e.g., 'txt', 'pdf') or UTI
                   (e.g., 'public.image', 'com.adobe.pdf').

    Returns:
        NSImage for the file type, or None on error.
    """
    try:
        workspace = NSWorkspace.sharedWorkspace()
        return workspace.iconForFileType_(file_type)
    except Exception:
        return None


def GetIconForFiles(paths: Sequence[str]) -> Optional[Any]:
    """
    Get a composite icon representing multiple files.

    Args:
        paths: List of full file paths.

    Returns:
        NSImage composite icon, or None on error.
    """
    try:
        workspace = NSWorkspace.sharedWorkspace()
        return workspace.iconForFiles_(paths)
    except Exception:
        return None


# =============================================================================
# Workspace: File Information
# =============================================================================

def GetFileInfo(path: str) -> Optional[dict[str, Any]]:
    """
    Get information about a file (associated application and file type).

    Args:
        path: Full path to the file.

    Returns:
        Dictionary with 'application' (path to default app) and 'type' (file type string),
        or None on error.
    """
    workspace = NSWorkspace.sharedWorkspace()
    try:
        success, app_path, file_type = workspace.getInfoForFile_application_type_(
            path, None, None
        )
        if success:
            return {
                'application': str(app_path) if app_path else None,
                'type': str(file_type) if file_type else None,
            }
    except Exception:
        pass
    return None


def GetLocalizedDescriptionForType(uti: str) -> Optional[str]:
    """
    Get a human-readable description for a Uniform Type Identifier (UTI).
    Example: GetLocalizedDescriptionForType('public.jpeg') -> 'JPEG image'

    Args:
        uti: Uniform Type Identifier string.

    Returns:
        Localized description string, or None.
    """
    try:
        workspace = NSWorkspace.sharedWorkspace()
        desc = workspace.localizedDescriptionForType_(uti)
        return str(desc) if desc else None
    except Exception:
        return None


# =============================================================================
# Workspace: Desktop Wallpaper
# =============================================================================

def GetDesktopImageURL(screen_index: int = 0) -> Optional[str]:
    """
    Get the URL of the current desktop wallpaper image.

    Args:
        screen_index: Index of the screen (0 = main display).

    Returns:
        File URL string of the wallpaper, or None.
    """
    from Cocoa import NSScreen
    workspace = NSWorkspace.sharedWorkspace()
    try:
        screens = NSScreen.screens()
        if screens and screen_index < len(screens):
            url = workspace.desktopImageURLForScreen_(screens[screen_index])
            return str(url) if url else None
    except Exception:
        pass
    return None


def SetDesktopImage(path: str, screen_index: int = 0) -> bool:
    """
    Set the desktop wallpaper image.

    Args:
        path: Full path to the image file.
        screen_index: Index of the screen (0 = main display).

    Returns:
        True if the wallpaper was set successfully.
    """
    from Cocoa import NSScreen, NSURL
    workspace = NSWorkspace.sharedWorkspace()
    try:
        screens = NSScreen.screens()
        if screens and screen_index < len(screens):
            url = NSURL.fileURLWithPath_(path)
            success, error = workspace.setDesktopImageURL_forScreen_options_error_(
                url, screens[screen_index], {}, None
            )
            return bool(success)
    except Exception:
        pass
    return False


# =============================================================================
# Workspace: Notification Center
# =============================================================================

def GetWorkspaceNotificationCenter() -> Any:
    """
    Get the NSWorkspace notification center for observing workspace events.

    Use this to subscribe to events like:
        - NSWorkspaceDidActivateApplicationNotification
        - NSWorkspaceDidDeactivateApplicationNotification
        - NSWorkspaceDidLaunchApplicationNotification
        - NSWorkspaceDidTerminateApplicationNotification
        - NSWorkspaceActiveSpaceDidChangeNotification
        - NSWorkspaceDidWakeNotification
        - NSWorkspaceWillSleepNotification
        - NSWorkspaceDidMountNotification
        - NSWorkspaceDidUnmountNotification

    Returns:
        NSNotificationCenter for the shared NSWorkspace.
    """
    return NSWorkspace.sharedWorkspace().notificationCenter()


# =============================================================================
# System Info Functions
# =============================================================================

def GetMacOSVersion() -> str:
    """Get the macOS version string (e.g., 'macOS 15.3')."""
    try:
        result = subprocess.run(['sw_vers', '-productVersion'], capture_output=True, text=True)
        version = result.stdout.strip()
        name_result = subprocess.run(['sw_vers', '-productName'], capture_output=True, text=True)
        name = name_result.stdout.strip()
        return f"{name} {version}"
    except Exception:
        return "macOS"


def GetDefaultLanguage() -> str:
    """Get the default system language."""
    try:
        result = subprocess.run(
            ['defaults', 'read', '-g', 'AppleLanguages'],
            capture_output=True, text=True
        )
        langs = result.stdout.strip()
        if langs.startswith('('):
            first_lang = langs.split(',')[0].strip('() "')
            return first_lang
        return "en-US"
    except Exception:
        return "en-US"


def ExecuteCommand(command: str, mode: str = 'shell', timeout: int = 10) -> Tuple[str, int]:
    """
    Execute a command in shell or osascript mode.

    Args:
        command: Command to execute.
        mode: 'shell' for bash, 'osascript' for AppleScript.
        timeout: Timeout in seconds.

    Returns:
        Tuple of (output, return_code).
    """
    import os
    env = os.environ.copy()
    try:
        if mode == 'osascript':
            result = subprocess.run(
                ['osascript', '-e', command],
                capture_output=True, text=True, timeout=timeout, env=env
            )
        else:
            result = subprocess.run(
                command, shell=True,
                capture_output=True, text=True, timeout=timeout, env=env
            )
        output = result.stdout or result.stderr or ''
        return (output.strip(), result.returncode)
    except subprocess.TimeoutExpired:
        return (f"Command timed out after {timeout} seconds", -1)
    except Exception as e:
        return (str(e), -1)


# =============================================================================
# High-level Convenience Functions (Control-based)
# =============================================================================

def GetFrontmostApplication() -> Optional["ApplicationControl"]:
    """
    Get the frontmost application as an ApplicationControl.
    Returns a fully-typed Control that supports .FocusedWindow, .Windows,
    .Title, .FindFirst(), fluent chaining, etc.

    Uses CGWindowListCopyWindowInfo (window server) instead of
    NSWorkspace.frontmostApplication() because NSWorkspace relies on
    AppKit notifications delivered via NSRunLoop. Without an active
    event loop (e.g. Python scripts, notebooks), NSWorkspace returns
    stale cached data and won't reflect focus changes.

    Returns:
        ApplicationControl or None.
    """
    from .controls import ApplicationControl
    pid = GetForegroundWindowPID()
    if pid:
        return ApplicationControl(pid=pid)
    return None


def GetForegroundControl() -> Optional["WindowControl"]:
    """
    Get the foreground window as a typed Control (typically WindowControl).

    Returns:
        WindowControl or None.
    """
    from .controls import ApplicationControl
    pid = GetForegroundWindowPID()
    if pid:
        app = ApplicationControl(pid=pid)
        return app.FocusedWindow
    return None


def GetFocusedControl() -> Optional["Control"]:
    """
    Get the currently focused UI element as a typed Control.

    Returns:
        A typed Control subclass or None.
    """
    from .controls import ApplicationControl
    pid = GetForegroundWindowPID()
    if pid:
        app = ApplicationControl(pid=pid)
        return app.FocusedUIElement
    return None


def GetRunningApplications(
    policy: Optional[str] = None,
    status: Optional[str] = None,
) -> list["ApplicationControl"]:
    """
    Get running applications as ApplicationControl objects with optional filtering.

    String filters support combining multiple values with '+' for OR logic.

    Args:
        policy: Filter by activation policy.
            'Regular'              — Normal apps (Dock + App Switcher).
            'Accessory'            — Menu bar items, helpers (no Dock icon).
            'Prohibited'           — Background agents/daemons.
            'Regular+Accessory'    — Combine with '+' for OR matching.
            None                   — Return all (default).
        status: Filter by current status.
            'Active'               — Frontmost app with visible windows.
            'Visible'              — Has windows on screen, not frontmost.
            'Hidden'               — Hidden via Cmd+H.
            'Minimized'            — All windows minimized.
            'Windowless'           — Running but no windows.
            'Active+Visible'       — Combine with '+' for OR matching.
            None                   — Return all (default).

    Returns:
        List of ApplicationControl matching the filters.
    """
    from .controls import ApplicationControl
    raw_apps = NSWorkspace.sharedWorkspace().runningApplications()
    apps = [ApplicationControl(pid=a.processIdentifier()) for a in raw_apps]

    if policy is not None:
        policies = {p.strip() for p in policy.split('+')}
        apps = [a for a in apps if a.ActivationPolicy in policies]
    if status is not None:
        statuses = {s.strip() for s in status.split('+')}
        apps = [a for a in apps if a.Status in statuses]

    return apps


def GetRunningApplicationByName(name: str) -> Optional["ApplicationControl"]:
    """
    Get a running application by its display name (case-insensitive exact match).

    Args:
        name: Application name (e.g., 'Dock', 'Safari', 'Google Chrome').

    Returns:
        ApplicationControl if found, None otherwise.
    """
    from .controls import ApplicationControl
    name_lower = name.strip().lower()
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        local_name = app.localizedName()
        if local_name and str(local_name).lower() == name_lower:
            return ApplicationControl(pid=app.processIdentifier())
    return None


def GetRunningApplicationByBundleId(bundle_id: str) -> Optional["ApplicationControl"]:
    """
    Get a running application by its bundle identifier (exact match).

    Args:
        bundle_id: CFBundleIdentifier (e.g., 'com.apple.dock', 'com.apple.Safari').

    Returns:
        ApplicationControl if found, None otherwise.
    """
    from .controls import ApplicationControl
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        bid = app.bundleIdentifier()
        if bid and str(bid) == bundle_id:
            return ApplicationControl(pid=app.processIdentifier())
    return None
