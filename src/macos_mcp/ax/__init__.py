"""
macOS Accessibility (AX) module.
Provides a unified, Pythonic interface to the macOS Accessibility API.

This module is the macOS equivalent of the Windows UIA module.
It wraps the native AXUIElement framework into clean Python classes
with consistent patterns for element discovery, property access,
action execution, and event observation.

Structure:
    - enums: Constants (Roles, Subroles, Attributes, Actions, Notifications, KeyCodes)
    - core: Low-level functions (element creation, screen/mouse/keyboard, window management)
    - controls: Control classes wrapping AXUIElementRef (ButtonControl, TextFieldControl, etc.)
    - patterns: Interaction patterns (InvokePattern, ValuePattern, ScrollPattern, etc.)
    - events: Event observation (EventObserver, AppObserver)

Usage:
    import macos_mcp.ax as ax

    # High-level entry -- returns ApplicationControl
    app = ax.GetFrontmostApplication()
    print(app.Title)

    # Fluent chaining for child discovery
    window = app.FocusedWindow
    window.TextFieldControl(title="Search").SendKeys("hello")
    window.ButtonControl(title="Submit").Click()

    # Window management
    window.SetActive()
    window.MoveToCenter()
    window.Maximize()

    # Direct interactions on any control
    btn = window.FindFirst(role=ax.Role.Button, title="OK")
    btn.Click()
    btn.DoubleClick()
    btn.RightClick()

    # Low-level operations still available
    width, height = ax.GetScreenSize()
    ax.Click(100, 200)
    ax.TypeText("hello world")
"""

# Enums - Constants
from .enums import (
    AXError,
    AXErrorNames,
    AXValueType,
    Role,
    RoleNames,
    Subrole,
    SubroleNames,
    Attribute,
    Action,
    ActionNames,
    Notification,
    NotificationNames,
    NotificationKey,
    FOCUS_NOTIFICATIONS,
    STRUCTURE_NOTIFICATIONS,
    PROPERTY_NOTIFICATIONS,
    ALL_NOTIFICATIONS,
    KeyCode,
    KEY_NAME_TO_CODE,
    MouseEventType,
    MouseButton,
    EventFlag,
    MODIFIER_KEY_MAP,
    Orientation,
    SortDirection,
    Units,
    TextAttribute,
    ActivationPolicy,
    ActivationPolicyNames,
)

# Core - Functions
from .core import (
    # Data types
    Rect,
    Point,
    Size,
    # AX client
    _AXClient,
    GetRootControl,
    ControlFromPID,
    IsAccessibilityEnabled,
    IsAccessibilityEnabledWithPrompt,
    # Attribute access
    GetAttribute,
    SetAttribute,
    IsAttributeSettable,
    GetAttributeNames,
    GetActionNames,
    PerformAction,
    GetChildCount,
    GetChildren,
    # Geometry
    GetPosition,
    GetSize,
    GetRect,
    ElementAtPosition,
    GetElementPid,
    GetMultipleAttributeValues,
    GetAttributeValues,
    GetActionDescription,
    SetMessagingTimeout,
    GetMessagingTimeout,
    # Screen
    GetScreenSize,
    GetMainDisplaySize,
    GetDisplayCount,
    GetDisplayBounds,
    GetDPIScale,
    CaptureScreen,
    CGImageToPIL,
    # Mouse
    GetCursorPos,
    SetCursorPos,
    MoveTo,
    Click,
    RightClick,
    MiddleClick,
    DoubleClick,
    DragTo,
    WheelDown,
    WheelUp,
    WheelLeft,
    WheelRight,
    # Keyboard
    KeyDown,
    KeyUp,
    KeyPress,
    HotKey,
    TypeText,
    # Application & Window (high-level, returns Control objects)
    GetForegroundWindowPID,
    GetFrontmostApplication,
    GetForegroundControl,
    GetFocusedControl,
    GetRunningApplications,
    GetRunningApplicationByName,
    GetRunningApplicationByBundleId,
    ActivateApplication,
    LaunchApplication,
    HideOtherApplications,
    GetMenuBarOwningApplication,
    GetApplicationPathByName,
    GetApplicationPathByBundleID,
    # Workspace: File & URL Operations
    OpenFile,
    OpenURL,
    SelectFileInFinder,
    RecycleFiles,
    DuplicateFiles,
    IsFilePackage,
    # Workspace: Icons
    GetIconForFile,
    GetIconForFileType,
    GetIconForFiles,
    # Workspace: File Information
    GetFileInfo,
    GetLocalizedDescriptionForType,
    # Workspace: Desktop Wallpaper
    GetDesktopImageURL,
    SetDesktopImage,
    # Workspace: Notification Center
    GetWorkspaceNotificationCenter,
    # System
    GetMacOSVersion,
    GetDefaultLanguage,
    ExecuteCommand,
)

# Controls - Element wrappers
from .controls import (
    Control,
    CreateControl,
    ApplicationControl,
    WindowControl,
    ButtonControl,
    CheckBoxControl,
    RadioButtonControl,
    TextFieldControl,
    TextAreaControl,
    ComboBoxControl,
    PopUpButtonControl,
    SliderControl,
    MenuItemControl,
    MenuBarItemControl,
    TabControl,
    ListControl,
    TableControl,
    OutlineControl,
    ScrollAreaControl,
    GroupControl,
    ImageControl,
    LinkControl,
    ProgressIndicatorControl,
    StaticTextControl,
    WebAreaControl,
    DisclosureTriangleControl,
    DockItemControl,
    CellControl,
    RowControl,
)

# Patterns - Interaction patterns
from .patterns import (
    InvokePattern,
    ValuePattern,
    RangeValuePattern,
    TogglePattern,
    ExpandCollapsePattern,
    ScrollPattern,
    SelectionPattern,
    WindowPattern,
    TextPattern,
    GetPattern,
)

# Events - Observation system
from .events import (
    EventObserver,
    AppObserver,
)
