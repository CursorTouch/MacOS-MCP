# macOS Accessibility (`ax`) Module

A Pythonic interface to the macOS Accessibility (AX) framework. Wraps native `AXUIElement`, `Quartz CGEvent`, and `NSWorkspace` APIs into typed Python classes with IntelliSense support.

**Import:**

```python
import macos_mcp.ax as ax
```

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Entry Points](#entry-points)
5. [Control Hierarchy](#control-hierarchy)
6. [Control (Base Class)](#control-base-class)
7. [ApplicationControl](#applicationcontrol)
8. [WindowControl](#windowcontrol)
9. [Typed Control Subclasses](#typed-control-subclasses)
10. [Fluent Child Discovery](#fluent-child-discovery)
11. [Element Search](#element-search)
12. [Geometry Types](#geometry-types)
13. [Mouse Functions](#mouse-functions)
14. [Keyboard Functions](#keyboard-functions)
15. [Screen Functions](#screen-functions)
16. [Workspace: Application Management](#workspace-application-management)
17. [Workspace: File & URL Operations](#workspace-file--url-operations)
18. [Workspace: Icons & File Info](#workspace-icons--file-info)
19. [Workspace: Desktop & Notifications](#workspace-desktop--notifications)
20. [Patterns](#patterns)
21. [Events](#events)
22. [Enums Reference](#enums-reference)
23. [Low-Level Functions](#low-level-functions)
24. [Common Recipes](#common-recipes)

---

## Prerequisites

- **macOS** with Accessibility permissions enabled
- **Python 3.10+** with `pyobjc` installed
- Grant your terminal/IDE accessibility access:
  `System Settings > Privacy & Security > Accessibility`

Check programmatically:

```python
ax.IsAccessibilityEnabled()           # Returns True/False
ax.IsAccessibilityEnabledWithPrompt() # Prompts user if not enabled
```

---

## Architecture

```
ax/
├── __init__.py    # Public API re-exports (import macos_mcp.ax as ax)
├── enums.py       # Constants: Role, Subrole, Attribute, Action, Notification, KeyCode
├── core.py        # Low-level: AXUIElement access, CGEvent input, NSWorkspace operations
├── controls.py    # Control classes: Control, ApplicationControl, WindowControl, etc.
├── patterns.py    # Interaction patterns: InvokePattern, ValuePattern, ScrollPattern, etc.
└── events.py      # Event observation: EventObserver, AppObserver
```

**Layering:**

```
┌──────────────────────────────────────────┐
│  Your Code / MCP Server                  │
├──────────────────────────────────────────┤
│  controls.py   (Control, WindowControl)  │  ← Object-oriented, typed, IntelliSense
│  patterns.py   (ValuePattern, etc.)      │
│  events.py     (EventObserver)           │
├──────────────────────────────────────────┤
│  core.py       (GetAttribute, Click)     │  ← Functional, low-level
│  enums.py      (Role, Attribute, Action) │
├──────────────────────────────────────────┤
│  pyobjc: ApplicationServices, Quartz,    │  ← Native macOS frameworks
│          Cocoa (NSWorkspace)             │
└──────────────────────────────────────────┘
```

---

## Quick Start

```python
import macos_mcp.ax as ax

# Get the frontmost application
app = ax.GetFrontmostApplication()
print(app.Name)                    # "Google Chrome"
print(app.BundleIdentifier)       # "com.google.Chrome"
print(app.IsActive)               # True

# Get its focused window
window = app.FocusedWindow
print(window.Name)                 # "GitHub - Google Chrome"
print(window.BoundingRectangle)    # Rect(left=0, top=25, right=1440, bottom=900)

# Find and click a button
btn = window.ButtonControl(title="Submit")
btn.Click()

# Type into a text field
search = window.TextFieldControl(title="Search")
search.Click()
ax.TypeText("hello world")

# Keyboard shortcut
ax.HotKey('command', 'c')  # Cmd+C
```

---

## Entry Points

These are the main functions you use to get started:

| Function | Returns | Description |
|----------|---------|-------------|
| `ax.GetFrontmostApplication()` | `ApplicationControl` | The currently active app |
| `ax.GetForegroundControl()` | `WindowControl` | The focused window |
| `ax.GetFocusedControl()` | `Control` | The focused UI element |
| `ax.GetRunningApplications()` | `list[ApplicationControl]` | All running apps |

---

## Control Hierarchy

```
macOS AX Element Tree
─────────────────────
AXApplication  (ApplicationControl)
├── AXMenuBar  (Control)
│   └── AXMenuBarItem  (MenuBarItemControl)
│       └── AXMenu → AXMenuItem  (MenuItemControl)
├── AXWindow  (WindowControl)
│   ├── AXToolbar  (Control)
│   ├── AXGroup  (GroupControl)
│   │   ├── AXButton  (ButtonControl)
│   │   ├── AXTextField  (TextFieldControl)
│   │   ├── AXCheckBox  (CheckBoxControl)
│   │   └── AXStaticText  (StaticTextControl)
│   ├── AXScrollArea  (ScrollAreaControl)
│   │   └── AXTable / AXList / AXOutline
│   │       └── AXRow / AXCell
│   └── AXWebArea  (WebAreaControl)
│       └── AXGroup → AXLink, AXButton, etc.
└── AXExtrasMenuBar  (Control)
```

---

## Control (Base Class)

Every UI element is wrapped as a `Control`. All typed subclasses inherit from it.

### Identity Properties

```python
ctrl.Role              # "AXButton"
ctrl.Subrole           # "AXCloseButton" or None
ctrl.RoleDescription   # "button"
ctrl.Name              # Title/Description/Value (first non-empty)
ctrl.Title             # AXTitle
ctrl.Description       # AXDescription
ctrl.Value             # AXValue (text content, checkbox state, slider value)
ctrl.ValueString       # str(Value) or ""
ctrl.Identifier        # AXIdentifier (developer-assigned ID)
ctrl.Label             # Combines Title + Description + Value
ctrl.Help              # AXHelp tooltip text
ctrl.URL               # AXURL
ctrl.Document          # AXDocument
```

### State Properties

```python
ctrl.IsEnabled         # Is the element enabled?
ctrl.IsFocused         # Does it have keyboard focus?
ctrl.IsSelected        # Is it selected?
ctrl.IsExpanded        # Is it expanded (disclosure triangles, outlines)?
ctrl.IsMain            # Is this the main window?
ctrl.IsMinimized       # Is the window minimized?
ctrl.IsFullScreen      # Is the window fullscreen?
ctrl.IsModal           # Is it a modal dialog?
ctrl.IsInteractive     # Has interactive actions (Press, Increment, etc.)?
ctrl.IsScrollable      # Has scroll bars?
ctrl.IsContainer       # Is it a container role (Group, ScrollArea, etc.)?
```

### Geometry Properties

```python
ctrl.Position           # Point(x, y) — screen coordinates
ctrl.ElementSize        # Size(width, height)
ctrl.BoundingRectangle  # Rect(left, top, right, bottom) with .width, .height, .center
ctrl.Center             # Point(cx, cy) — center of the element
```

### Navigation Properties

```python
ctrl.Parent              # Parent Control
ctrl.Window              # Containing WindowControl
ctrl.TopLevelUIElement   # Top-level Control (usually window or app)
ctrl.GetChildren()       # List[Control] — all children
ctrl.ChildCount          # int — number of children
ctrl.GetFirstChildControl()  # First child
ctrl.GetLastChildControl()   # Last child
```

### Application-Level Properties (on base Control)

```python
ctrl.FocusedWindow       # WindowControl — focused window
ctrl.MainWindow          # WindowControl — main window
ctrl.Windows             # List[WindowControl] — all windows
ctrl.MenuBar             # Control — application menu bar
ctrl.ExtrasMenuBar       # Control — status bar items
```

### Text Properties

```python
ctrl.NumberOfCharacters   # int
ctrl.SelectedText         # str
ctrl.SelectedTextRange    # range
ctrl.VisibleCharacterRange # range
ctrl.PlaceholderValue     # Placeholder text in text fields
```

### Table/List Properties

```python
ctrl.Rows                # List[Control]
ctrl.VisibleRows         # List[Control]
ctrl.SelectedRows        # List[Control]
ctrl.Columns             # List[Control]
ctrl.HorizontalScrollBar # Control
ctrl.VerticalScrollBar   # Control
```

### Actions

```python
ctrl.Press()             # AXPress (click)
ctrl.Confirm()           # AXConfirm
ctrl.Cancel()            # AXCancel
ctrl.Increment()         # AXIncrement
ctrl.Decrement()         # AXDecrement
ctrl.ShowMenu()          # AXShowMenu (right-click context menu)
ctrl.Pick()              # AXPick
ctrl.Raise()             # AXRaise (bring window to front)
ctrl.SetFocus()          # Set keyboard focus
ctrl.HasAction(name)     # Check if an action is available
ctrl.PerformAction(name) # Perform any action by name
ctrl.ActionNames         # List of all available actions
```

### Mouse Interactions

```python
ctrl.Click()             # Left click at center
ctrl.DoubleClick()       # Double click at center
ctrl.RightClick()        # Right click at center
ctrl.MiddleClick()       # Middle click at center
ctrl.MoveCursorToCenter() # Move mouse to center
ctrl.WheelDown(clicks=3) # Scroll down
ctrl.WheelUp(clicks=3)   # Scroll up
ctrl.DragTo(target)       # Drag to another Control, Point, or (x, y) tuple
```

### Keyboard Interactions

```python
ctrl.SendKeys(text)      # Click element, then type text
```

### Raw Attribute Access

```python
ctrl.AttributeNames      # List of all supported attribute names
ctrl.GetAttributeValue(name)       # Get raw AX attribute value
ctrl.SetAttributeValue(name, val)  # Set raw AX attribute value
ctrl.IsAttributeSettable(name)     # Check if attribute is writable
```

---

## ApplicationControl

Extends `Control` with process-level metadata from `NSRunningApplication`.

### AX Properties (inherited + overridden with proper types)

```python
app.FocusedWindow       # WindowControl
app.MainWindow          # WindowControl
app.Windows             # List[WindowControl]
app.FocusedUIElement    # Control
app.IsApplicationRunning # bool
app.EnhancedUserInterface # bool (get/set — enables deeper tree in some apps)
```

### NSRunningApplication Properties

```python
app.PID                  # int — process identifier
app.BundleIdentifier     # str — "com.apple.Safari"
app.BundleURL            # str — "file:///Applications/Safari.app/"
app.ExecutableURL        # str — path to the binary
app.LocalizedName        # str — "Safari" (display name)
app.Icon                 # NSImage — app icon
app.LaunchDate           # NSDate — when launched
app.IsActive             # bool — is it frontmost?
app.IsHidden             # bool — is it hidden?
app.IsFinishedLaunching  # bool — has it finished launching?
app.IsTerminated         # bool — has it been terminated?
app.ActivationPolicy     # int — 0=Regular, 1=Accessory, 2=Prohibited
app.ExecutableArchitecture # int — CPU arch (arm64, x86_64)
app.OwnsMenuBar          # bool — does it own the menu bar?
```

### NSRunningApplication Methods

```python
app.Activate()           # Bring to front
app.Hide()               # Hide (Cmd+H)
app.Unhide()             # Show
app.Terminate()          # Graceful quit
app.ForceTerminate()     # Force quit (no save prompts)
```

---

## WindowControl

Extends `Control` with window management methods.

### Window Actions

```python
window.Close()           # Close via close button
window.Minimize()        # Minimize to Dock
window.Unminimize()      # Restore from Dock
window.Restore()         # Alias for Unminimize
window.Zoom()            # Zoom (maximize) via zoom button
window.Maximize()        # Alias for Zoom
window.FullScreen()      # Toggle fullscreen
window.SetActive()       # Bring to front + raise
window.MoveToCenter()    # Center on screen
window.Resize(w, h)      # Resize to width x height
window.MoveWindowTo(x, y) # Move to screen position
```

### Window Properties

```python
window.DefaultButton     # Control — default button (dialog)
window.CancelButton      # Control — cancel button (dialog)
```

---

## Typed Control Subclasses

Each AX role maps to a typed subclass with role-specific methods:

| Class | Role | Extra Methods |
|-------|------|---------------|
| `ButtonControl` | AXButton | (inherits Press) |
| `CheckBoxControl` | AXCheckBox | `.IsChecked`, `.Toggle()`, `.Check()`, `.Uncheck()` |
| `RadioButtonControl` | AXRadioButton | `.IsSelected`, `.Select()` |
| `TextFieldControl` | AXTextField | `.Text` (get/set), `.SetText()`, `.Clear()`, `.AppendText()` |
| `TextAreaControl` | AXTextArea | (inherits from TextFieldControl) |
| `ComboBoxControl` | AXComboBox | `.Text` (get/set), `.SetText()`, `.Clear()` |
| `PopUpButtonControl` | AXPopUpButton | `.SelectedItem`, `.Select()` |
| `SliderControl` | AXSlider | `.SliderValue` (get/set), `.Min`, `.Max`, `.Percentage` |
| `MenuItemControl` | AXMenuItem | `.KeyboardShortcut`, `.Invoke()` |
| `MenuBarItemControl` | AXMenuBarItem | `.Open()` |
| `TabControl` | AXTab | `.Select()` |
| `ListControl` | AXList | `.SelectedItems` |
| `TableControl` | AXTable | `.RowCount`, `.ColumnCount`, `.SelectedRowIndices`, `.SelectRow()` |
| `OutlineControl` | AXOutline | `.SelectedItems` |
| `ScrollAreaControl` | AXScrollArea | `.ScrollToTop()`, `.ScrollToBottom()`, `.ScrollByPage()` |
| `GroupControl` | AXGroup | (container) |
| `ImageControl` | AXImage | `.ImageDescription` |
| `LinkControl` | AXLink | `.URL`, `.Navigate()` |
| `ProgressIndicatorControl` | AXProgressIndicator | `.ProgressValue`, `.Min`, `.Max`, `.IsIndeterminate` |
| `StaticTextControl` | AXStaticText | `.Text` |
| `WebAreaControl` | AXWebArea | `.URL`, `.DocumentTitle`, `.LoadingProgress` |
| `DisclosureTriangleControl` | AXDisclosureTriangle | `.IsExpanded`, `.Toggle()`, `.Expand()`, `.Collapse()` |
| `DockItemControl` | AXDockItem | (inherits Press) |
| `CellControl` | AXCell | `.RowIndex`, `.ColumnIndex` |
| `RowControl` | AXRow / AXOutlineRow | `.Index`, `.IsSelected`, `.Select()`, `.DisclosureLevel` |

---

## Fluent Child Discovery

Every `Control` has typed finder methods that return the correct subclass:

```python
# These return typed controls with IntelliSense
window.ButtonControl(title="Save")           # -> ButtonControl
window.TextFieldControl(title="Username")    # -> TextFieldControl
window.CheckBoxControl(title="Remember me")  # -> CheckBoxControl
window.SliderControl(title="Volume")         # -> SliderControl
window.MenuItemControl(title="Copy")         # -> MenuItemControl
window.LinkControl(title="Learn more")       # -> LinkControl
window.TabControl(title="General")           # -> TabControl
window.TableControl()                        # -> TableControl
window.ListControl()                         # -> ListControl
window.GroupControl(identifier="main")       # -> GroupControl
window.ImageControl(title="Logo")            # -> ImageControl
window.WebAreaControl()                      # -> WebAreaControl
# ... and all other typed controls
```

Parameters for all finders:

```python
window.ButtonControl(
    title="Save",           # Match AXTitle (substring)
    identifier="save-btn",  # Match AXIdentifier
    predicate=lambda c: c.IsEnabled,  # Custom filter
    max_depth=25,           # Search depth
)
```

---

## Element Search

For more flexible searching:

```python
# Find first match
btn = window.FindFirst(role=ax.Role.Button, title="OK")

# Find all matches
all_links = window.FindAll(role=ax.Role.Link)

# With custom predicate
enabled_buttons = window.FindAll(
    role=ax.Role.Button,
    predicate=lambda c: c.IsEnabled
)

# Search by subrole
close_btn = window.FindFirst(subrole=ax.Subrole.CloseButton)

# Search by identifier
sidebar = window.FindFirst(identifier="sidebar-container")
```

---

## Geometry Types

```python
# Rect — bounding rectangle
rect = ctrl.BoundingRectangle
rect.left, rect.top, rect.right, rect.bottom  # edges
rect.width, rect.height                        # computed
rect.center                                    # (cx, cy) tuple
rect.intersects(other_rect)                    # bool
rect.intersection(other_rect)                  # Rect or None
Rect.from_position_size(x, y, w, h)           # factory

# Point — 2D position
pos = ctrl.Position      # Point(x=100, y=200)
pos.x, pos.y

# Size — 2D dimensions
size = ctrl.ElementSize  # Size(width=800, height=600)
size.width, size.height
```

---

## Mouse Functions

Low-level mouse input (screen coordinates):

```python
ax.Click(x, y)              # Left click
ax.RightClick(x, y)         # Right click
ax.MiddleClick(x, y)        # Middle click
ax.DoubleClick(x, y)        # Double click
ax.DragTo(x1, y1, x2, y2)  # Drag from (x1,y1) to (x2,y2)
ax.MoveTo(x, y)             # Move cursor
ax.SetCursorPos(x, y)       # Alias for MoveTo
ax.GetCursorPos()            # Returns (x, y)

# Scrolling
ax.WheelDown(clicks=3)      # Scroll down
ax.WheelUp(clicks=3)        # Scroll up
ax.WheelLeft(clicks=3)      # Scroll left
ax.WheelRight(clicks=3)     # Scroll right
```

---

## Keyboard Functions

```python
# Type text (supports Unicode — Hindi, Chinese, emoji, etc.)
ax.TypeText("Hello, world!")
ax.TypeText("नमस्ते")         # Hindi
ax.TypeText("你好世界")        # Chinese

# Keyboard shortcuts
ax.HotKey('command', 'c')       # Cmd+C
ax.HotKey('command', 'shift', 'z')  # Cmd+Shift+Z
ax.HotKey('command', 'a')       # Cmd+A (select all)

# Low-level key events
ax.KeyPress(ax.KeyCode.Return)  # Press Enter
ax.KeyDown(ax.KeyCode.Shift)    # Hold Shift
ax.KeyUp(ax.KeyCode.Shift)      # Release Shift

# Key names for HotKey:
# command/cmd, shift, option/alt, control/ctrl, fn
# return/enter, tab, space, escape/esc, delete/backspace
# left, right, up, down, home, end, pageup, pagedown
# f1-f20, a-z, 0-9, and symbols: = - [ ] ' ; \ , / . `
```

---

## Screen Functions

```python
ax.GetScreenSize()         # (width, height) — virtual screen (all displays)
ax.GetMainDisplaySize()    # (width, height) — main display only
ax.GetDisplayCount()       # Number of active displays
ax.GetDisplayBounds()      # List[Rect] — bounds of each display
ax.GetDPIScale()           # 2.0 for Retina, 1.0 for standard

# Screenshots
cg_image = ax.CaptureScreen()       # Capture entire screen
pil_image = ax.CGImageToPIL(cg_image)  # Convert to PIL Image
pil_image.save("screenshot.png")
```

---

## Workspace: Application Management

```python
# Launch & activate
ax.LaunchApplication("Safari")
ax.ActivateApplication(pid)

# Query
ax.GetApplicationPathByName("Safari")    # "/Applications/Safari.app"
ax.GetApplicationPathByBundleID("com.apple.Safari")  # URL string
ax.GetMenuBarOwningApplication()         # PID of menu bar owner

# Global actions
ax.HideOtherApplications()              # Option+Cmd+H
```

---

## Workspace: File & URL Operations

```python
# Open files
ax.OpenFile("/path/to/document.pdf")              # Default app
ax.OpenFile("/path/to/file.txt", "TextEdit")       # Specific app

# Open URLs
ax.OpenURL("https://apple.com")
ax.OpenURL("mailto:user@example.com")

# Finder
ax.SelectFileInFinder("/path/to/file.txt")   # Reveal in Finder

# File operations
ax.RecycleFiles(["/path/to/file1", "/path/to/file2"])  # Move to Trash
ax.DuplicateFiles(["/path/to/file"])                    # Duplicate
ax.IsFilePackage("/Applications/Safari.app")            # True
```

---

## Workspace: Icons & File Info

```python
# Icons (returns NSImage)
icon = ax.GetIconForFile("/path/to/file.pdf")
icon = ax.GetIconForFileType("pdf")          # By extension
icon = ax.GetIconForFileType("public.image") # By UTI
icon = ax.GetIconForFiles([path1, path2])    # Composite icon

# File information
info = ax.GetFileInfo("/path/to/file.pdf")
# {'application': '/Applications/Preview.app', 'type': 'pdf'}

ax.GetLocalizedDescriptionForType("public.jpeg")  # "JPEG image"
```

---

## Workspace: Desktop & Notifications

```python
# Desktop wallpaper
ax.GetDesktopImageURL()                    # Current wallpaper URL
ax.SetDesktopImage("/path/to/image.jpg")   # Set wallpaper
ax.SetDesktopImage("/path/to/image.jpg", screen_index=1)  # Second display

# Notification center (for workspace events)
nc = ax.GetWorkspaceNotificationCenter()
# Use with NSWorkspaceDidActivateApplicationNotification, etc.
```

---

## Patterns

Patterns provide specialized interfaces for specific interaction types:

```python
from macos_mcp.ax import GetPattern, InvokePattern, ValuePattern

# InvokePattern — for clickable elements
pattern = GetPattern(button.Element, InvokePattern)
pattern.Invoke()  # Click

# ValuePattern — for text fields, sliders
pattern = GetPattern(text_field.Element, ValuePattern)
pattern.Value = "new text"
print(pattern.IsReadOnly)

# RangeValuePattern — for sliders, progress bars
pattern = GetPattern(slider.Element, RangeValuePattern)
print(pattern.Value, pattern.Minimum, pattern.Maximum)
pattern.Increment()
pattern.Decrement()

# TogglePattern — for checkboxes, switches
pattern = GetPattern(checkbox.Element, TogglePattern)
print(pattern.IsOn)
pattern.Toggle()

# ExpandCollapsePattern — for disclosure triangles
pattern = GetPattern(triangle.Element, ExpandCollapsePattern)
pattern.Expand()
pattern.Collapse()

# ScrollPattern — for scroll areas
pattern = GetPattern(scroll_area.Element, ScrollPattern)
print(pattern.VerticalScrollPercent)
pattern.ScrollByPage('down')

# SelectionPattern — for lists, tables
pattern = GetPattern(list_ctrl.Element, SelectionPattern)
selected = pattern.SelectedChildControls

# WindowPattern — for windows
pattern = GetPattern(window.Element, WindowPattern)
pattern.Minimize()
pattern.Raise()

# TextPattern — for text elements
pattern = GetPattern(text_area.Element, TextPattern)
print(pattern.Text)
print(pattern.SelectedText)
print(pattern.NumberOfCharacters)
```

---

## Events

Observe accessibility events across applications:

```python
observer = ax.EventObserver(debounce_interval=0.05)

# Set callbacks
def on_focus(element, notification, pid):
    ctrl = ax.CreateControl(element)
    print(f"Focus: {ctrl.Role} '{ctrl.Name}' in PID {pid}")

def on_structure(element, notification, pid):
    print(f"Structure: {notification} in PID {pid}")

def on_property(element, notification, pid):
    print(f"Property: {notification} in PID {pid}")

observer.on_focus_changed = on_focus
observer.on_structure_changed = on_structure
observer.on_property_changed = on_property

# Start/stop
observer.start()
# ... your app runs ...
observer.stop()

# Or use as context manager
with ax.EventObserver() as obs:
    obs.on_focus_changed = on_focus
    import time; time.sleep(30)  # Listen for 30 seconds
```

### Notification Categories

| Callback | Notifications |
|----------|---------------|
| `on_focus_changed` | FocusedUIElementChanged, FocusedWindowChanged, MainWindowChanged |
| `on_structure_changed` | Created, UIElementDestroyed, WindowCreated, MenuOpened, MenuClosed, RowCountChanged |
| `on_property_changed` | ValueChanged, TitleChanged, SelectedTextChanged, SelectedChildrenChanged, Moved, Resized, ... |

---

## Enums Reference

### Role (element types)

```python
ax.Role.Button           # "AXButton"
ax.Role.TextField        # "AXTextField"
ax.Role.CheckBox         # "AXCheckBox"
ax.Role.Window           # "AXWindow"
ax.Role.Application      # "AXApplication"
ax.Role.WebArea          # "AXWebArea"
ax.Role.Link             # "AXLink"
ax.Role.StaticText       # "AXStaticText"
ax.Role.Image            # "AXImage"
ax.Role.Table            # "AXTable"
ax.Role.List             # "AXList"
ax.Role.ScrollArea       # "AXScrollArea"
ax.Role.Group            # "AXGroup"
ax.Role.MenuItem         # "AXMenuItem"
ax.Role.Slider           # "AXSlider"
ax.Role.Tab              # "AXTab"
ax.Role.PopUpButton      # "AXPopUpButton"
ax.Role.ComboBox         # "AXComboBox"
# ... and many more
```

### Action

```python
ax.Action.Press          # "AXPress"
ax.Action.Increment      # "AXIncrement"
ax.Action.Decrement      # "AXDecrement"
ax.Action.Confirm        # "AXConfirm"
ax.Action.Cancel         # "AXCancel"
ax.Action.ShowMenu       # "AXShowMenu"
ax.Action.Pick           # "AXPick"
ax.Action.Raise          # "AXRaise"
```

### Attribute

```python
ax.Attribute.Role        # "AXRole"
ax.Attribute.Title       # "AXTitle"
ax.Attribute.Value       # "AXValue"
ax.Attribute.Description # "AXDescription"
ax.Attribute.Children    # "AXChildren"
ax.Attribute.Position    # "AXPosition"
ax.Attribute.Size        # "AXSize"
ax.Attribute.Focused     # "AXFocused"
ax.Attribute.Enabled     # "AXEnabled"
# ... 80+ attributes defined
```

### Notification

```python
ax.Notification.FocusedUIElementChanged   # Focus changed
ax.Notification.WindowCreated             # New window
ax.Notification.ValueChanged              # Value changed
ax.Notification.TitleChanged              # Title changed
ax.Notification.UIElementDestroyed        # Element removed
# ... 30+ notifications defined
```

### KeyCode

```python
ax.KeyCode.A             # 0x00
ax.KeyCode.Return        # 0x24
ax.KeyCode.Space         # 0x31
ax.KeyCode.Escape        # 0x35
ax.KeyCode.Command       # 0x37
ax.KeyCode.Shift         # 0x38
ax.KeyCode.Option        # 0x3A
ax.KeyCode.LeftArrow     # 0x7B
ax.KeyCode.F1            # 0x7A
# ... full keyboard
```

---

## Low-Level Functions

For when you need direct AXUIElement access:

```python
# Element creation
root = ax.GetRootControl()       # System-wide element
elem = ax.ControlFromPID(pid)    # AXUIElement for a PID

# Attribute access (on raw AXUIElementRef)
value = ax.GetAttribute(element, ax.Attribute.Title)
ax.SetAttribute(element, ax.Attribute.Value, "text")
names = ax.GetAttributeNames(element)
settable = ax.IsAttributeSettable(element, ax.Attribute.Value)

# Batch attribute access (performance)
values = ax.GetMultipleAttributeValues(element, [
    ax.Attribute.Role, ax.Attribute.Title, ax.Attribute.Value
])

# Actions
actions = ax.GetActionNames(element)
ax.PerformAction(element, ax.Action.Press)
desc = ax.GetActionDescription(element, ax.Action.Press)

# Geometry
pos = ax.GetPosition(element)    # (x, y) or None
size = ax.GetSize(element)       # (w, h) or None
rect = ax.GetRect(element)       # Rect or None
pid = ax.GetElementPid(element)  # int or None

# Hit testing
elem = ax.ElementAtPosition(app_element, x, y)

# Timeouts
ax.SetMessagingTimeout(element, 5.0)  # 5 second timeout
```

---

## Common Recipes

### Iterate all visible windows

```python
for app in ax.GetRunningApplications():
    if app.ActivationPolicy == 0:  # Regular apps only
        for win in app.Windows:
            rect = win.BoundingRectangle
            if rect:
                print(f"{app.LocalizedName}: {win.Name} ({rect.width}x{rect.height})")
```

### Click a menu item

```python
app = ax.GetFrontmostApplication()
menu_bar = app.MenuBar
file_menu = menu_bar.MenuBarItemControl(title="File")
file_menu.Press()
import time; time.sleep(0.3)
save_item = file_menu.MenuItemControl(title="Save")
save_item.Press()
```

### Fill a form

```python
window = ax.GetForegroundControl()
window.TextFieldControl(title="Username").SendKeys("john")
window.TextFieldControl(title="Password").SendKeys("secret123")
window.CheckBoxControl(title="Remember me").Check()
window.ButtonControl(title="Sign In").Click()
```

### Take a screenshot and find element at point

```python
import macos_mcp.ax as ax

# Screenshot
img = ax.CGImageToPIL(ax.CaptureScreen())
img.save("screen.png")

# Find element at (500, 300)
root = ax.GetRootControl()
elem = ax.ElementAtPosition(root, 500, 300)
if elem:
    ctrl = ax.CreateControl(elem)
    print(f"{ctrl.Role}: {ctrl.Name}")
```

### Watch for focus changes

```python
def on_focus(element, notification, pid):
    ctrl = ax.CreateControl(element)
    app_name = ctrl.Name or "Unknown"
    print(f"[{notification}] {ctrl.Role}: {app_name}")

with ax.EventObserver() as obs:
    obs.on_focus_changed = on_focus
    import time
    time.sleep(60)  # Watch for 1 minute
```

### Open a file and wait for the app

```python
import time

ax.OpenFile("/Users/me/Documents/report.pdf")
time.sleep(2)

app = ax.GetFrontmostApplication()
print(f"Opened in: {app.LocalizedName}")
window = app.FocusedWindow
print(f"Window: {window.Name}")
print(f"Size: {window.BoundingRectangle}")
```

---

## System Info

```python
ax.GetMacOSVersion()       # "macOS 15.3"
ax.GetDefaultLanguage()    # "en-US"

# Execute shell commands
output, code = ax.ExecuteCommand("ls -la /tmp")
output, code = ax.ExecuteCommand('tell application "Finder" to activate', mode='osascript')
```
